from fastapi import APIRouter
from app.api.v1.endpoints import health, ingest, query, documents

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["Health & System"])
api_router.include_router(ingest.router, tags=["Document Ingestion"])
api_router.include_router(query.router, tags=["Confidence-Aware Query"])
api_router.include_router(documents.router, tags=["Document Management"])
