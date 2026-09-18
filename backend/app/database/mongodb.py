import threading
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from loguru import logger

from app.core.config import settings


class MongoDBManager:
    """
    Singleton MongoDB connection manager providing pooled database access,
    connection validation, and graceful lifecycle management.
    """

    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._lock = threading.Lock()
        self._is_connected: bool = False
        self._last_attempt_time: float = 0.0
        self._reconnect_cooldown_sec: float = 30.0

    def connect(self, uri: Optional[str] = None, db_name: Optional[str] = None) -> bool:
        """
        Initialize and validate connection to MongoDB Atlas / Local MongoDB.
        Uses connection pooling and ping verification.
        """
        target_uri = uri or settings.MONGODB_URI
        target_db = db_name or settings.MONGODB_DATABASE

        with self._lock:
            if self._client is not None and self._is_connected:
                return True

            import time
            self._last_attempt_time = time.time()

            try:
                logger.info(f"Connecting to MongoDB database '{target_db}'...")
                self._client = MongoClient(
                    target_uri,
                    maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                    minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                    serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                    retryWrites=settings.MONGODB_RETRY_WRITES,
                    connect=True,
                )
                # Perform admin command ping to validate connection
                self._client.admin.command("ping")
                self._db = self._client[target_db]
                self._is_connected = True
                logger.info(f"Successfully connected to MongoDB database '{target_db}'.")
                return True
            except (ConnectionFailure, ServerSelectionTimeoutError) as err:
                self._is_connected = False
                logger.warning(
                    f"MongoDB connection failed: {err}. "
                    f"Ensure MONGODB_URI is reachable or check network/firewall access."
                )
                return False
            except Exception as e:
                self._is_connected = False
                logger.error(f"Unexpected error connecting to MongoDB: {e}")
                return False

    def ping(self) -> bool:
        """Ping MongoDB server to verify live connectivity."""
        if not self._client or not self._is_connected:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    @property
    def is_connected(self) -> bool:
        """Check if MongoDB is actively connected."""
        return self._is_connected and self._client is not None

    def get_database(self) -> Optional[Database]:
        """Get the connected MongoDB database instance with reconnect cooldown."""
        import time
        if not self._is_connected or self._db is None:
            now = time.time()
            if (now - self._last_attempt_time) > self._reconnect_cooldown_sec:
                self.connect()
        return self._db if self._is_connected else None

    def close(self) -> None:
        """Gracefully close MongoDB connection pool."""
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                    logger.info("Closed MongoDB connection pool.")
                except Exception as e:
                    logger.warning(f"Error closing MongoDB connection: {e}")
                finally:
                    self._client = None
                    self._db = None
                    self._is_connected = False

    def set_mock_database(self, mock_db: Database) -> None:
        """Inject a mock/in-memory database for testing."""
        with self._lock:
            self._db = mock_db
            self._client = getattr(mock_db, "client", None)
            self._is_connected = True


# Global singleton instance
mongodb_manager = MongoDBManager()


def get_mongodb() -> Optional[Database]:
    """Retrieve singleton MongoDB database instance."""
    return mongodb_manager.get_database()
