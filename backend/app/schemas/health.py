from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Status of the application")
    app_name: str = Field(description="Name of the application")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment (dev/test/prod)")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        description="Current server UTC timestamp"
    )
    components: Dict[str, str] = Field(
        default_factory=dict, 
        description="Health status of downstream components (embedding, vector store, OCR)"
    )

class ReadyResponse(BaseModel):
    """Readiness probe schema for orchestrators (Kubernetes / Docker)."""
    ready: bool = Field(default=True, description="Whether the system is ready to accept traffic")
    details: Optional[Dict[str, Any]] = None
