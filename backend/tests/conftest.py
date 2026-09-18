import sys
from pathlib import Path
import pytest
import mongomock

# Add workspace root and backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
backend_dir = root_dir / "backend"

for path in [str(root_dir), str(backend_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.core.config import settings
from app.database import mongodb_manager, create_indexes


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Automatically mock MongoDB and LLM provider for fast, deterministic, isolated tests."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    
    # Inject mongomock
    client = mongomock.MongoClient()
    mock_db = client["test_confidence_rag"]
    mongodb_manager.set_mock_database(mock_db)
    create_indexes(mock_db)
    
    yield mock_db
    
    try:
        mock_db.client.drop_database("test_confidence_rag")
    except Exception:
        pass
