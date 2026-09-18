from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter()

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Returns the overall operational health of the Confidence-Aware RAG service."
)
async def get_health() -> HealthResponse:
    """
    Returns system status, active configuration parameters, and component states.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        components={
            "api": "online",
            "ocr_engine": settings.OCR_ENGINE,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "vector_store": settings.VECTOR_STORE_TYPE,
            "llm_provider": settings.LLM_PROVIDER,
        }
    )

@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Kubernetes/Docker readiness probe confirming all internal directories and settings are available."
)
async def get_ready() -> ReadyResponse:
    """
    Checks if directories and essential configuration are loaded properly.
    """
    is_ready = settings.UPLOAD_DIR.exists() and settings.STORAGE_DIR.exists()
    return ReadyResponse(
        ready=is_ready,
        details={
            "upload_dir_exists": settings.UPLOAD_DIR.exists(),
            "storage_dir_exists": settings.STORAGE_DIR.exists(),
        }
    )
