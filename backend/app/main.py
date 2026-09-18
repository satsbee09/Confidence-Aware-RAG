from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router


import threading

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown events.
    """
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in {settings.APP_ENV} mode...")
    settings.ensure_directories()
    logger.info("Storage and upload directories verified.")

    # Initialize MongoDB Connection and Indexes
    try:
        from app.database import mongodb_manager, create_indexes
        connected = mongodb_manager.connect()
        if connected:
            db = mongodb_manager.get_database()
            if db is not None:
                create_indexes(db)
        else:
            logger.warning("Running with local cache fallback (MongoDB not connected).")
    except Exception as db_err:
        logger.warning(f"MongoDB startup note: {db_err}")

    def _warmup_background():
        try:
            from app.services.embedding_service import get_embedding_service
            from app.repositories.vector_store import get_vector_store
            logger.info("Pre-warming embedding model and vector index in background...")
            get_embedding_service()
            get_vector_store()
            logger.info("Embedding service and vector index pre-warmed.")
        except Exception as e:
            logger.warning(f"Embedding pre-warming note: {e}")

    threading.Thread(target=_warmup_background, daemon=True).start()
    yield
    # Shutdown
    logger.info("Shutting down service and cleaning up resources...")
    try:
        from app.database import mongodb_manager
        mongodb_manager.close()
    except Exception as close_err:
        logger.warning(f"Error during MongoDB cleanup: {close_err}")


def create_application() -> FastAPI:
    """
    Factory function to initialize and configure the FastAPI application instance.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "End-to-End Confidence-Aware RAG System for Noisy OCR-Based Indian Legal "
            "and Government Documents. Preserves and propagates OCR confidence scores "
            "through chunking, vector retrieval reranking, evidence analysis, and "
            "grounded answer generation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # ---------------------------------------------------------
    # CORS Middleware
    # ---------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=r"https?://.*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # Global Exception Handlers
    # ---------------------------------------------------------
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "path": request.url.path,
            },
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        from starlette.exceptions import HTTPException as StarletteHTTPException
        from fastapi import HTTPException as FastAPIHTTPException

        if isinstance(exc, (StarletteHTTPException, FastAPIHTTPException)):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing the request.",
                "path": request.url.path,
            },
        )


    # ---------------------------------------------------------
    # Root & Health Endpoints
    # ---------------------------------------------------------
    @application.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "operational",
            "docs_url": "/docs",
            "api_v1": settings.API_V1_STR,
        }

    @application.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    # ---------------------------------------------------------
    # Include API Routers
    # ---------------------------------------------------------
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
