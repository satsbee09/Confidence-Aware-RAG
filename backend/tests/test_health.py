import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint returns correct system metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == settings.APP_NAME
        assert data["version"] == settings.APP_VERSION
        assert data["status"] == "operational"
        assert data["api_v1"] == "/api/v1"


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /api/v1/health returns healthy status and active configuration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == settings.APP_NAME
        assert "components" in data
        assert data["components"]["api"] == "online"


@pytest.mark.asyncio
async def test_ready_endpoint():
    """Test /api/v1/ready probe returns ready boolean."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
