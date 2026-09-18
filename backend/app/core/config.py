import os
from pathlib import Path
from typing import List, Literal, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    Follows 12-factor app principles for centralized configuration.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", str(Path(__file__).resolve().parent.parent.parent.parent / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ---------------------------------------------------------
    # Application Metadata
    # ---------------------------------------------------------
    APP_NAME: str = "Confidence-Aware RAG System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ---------------------------------------------------------
    # CORS Settings
    # ---------------------------------------------------------
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # ---------------------------------------------------------
    # File Storage Paths
    # ---------------------------------------------------------
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR: Path = Field(default=Path("./data/uploads"))
    STORAGE_DIR: Path = Field(default=Path("./data/storage"))
    MAX_UPLOAD_SIZE_MB: int = 25

    # ---------------------------------------------------------
    # OCR Engine Configuration
    # ---------------------------------------------------------
    OCR_ENGINE: Literal["paddleocr", "tesseract", "auto"] = "auto"
    OCR_LANG: str = "en"
    TESSERACT_CMD: str = ""

    # ---------------------------------------------------------
    # Chunking Configuration
    # ---------------------------------------------------------
    CHUNK_MIN_TOKENS: int = 200
    CHUNK_MAX_TOKENS: int = 400
    CHUNK_OVERLAP_TOKENS: int = 50
    LOW_CONFIDENCE_THRESHOLD: float = 0.50

    # ---------------------------------------------------------
    # Embedding Model Configuration
    # ---------------------------------------------------------
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    DEVICE: Literal["cpu", "cuda", "mps"] = "cpu"

    # ---------------------------------------------------------
    # Vector Database & Retrieval Configuration
    # ---------------------------------------------------------
    VECTOR_STORE_TYPE: Literal["faiss", "memory"] = "faiss"
    TOP_K: int = 10
    TOP_N_EVIDENCE: int = 3

    # ---------------------------------------------------------
    # Scoring & Reranking Formula Weights
    # final_score = similarity * (SIMILARITY_WEIGHT + CONFIDENCE_WEIGHT * confidence)
    # ---------------------------------------------------------
    SIMILARITY_WEIGHT: float = 0.50
    CONFIDENCE_WEIGHT: float = 0.50
    EVIDENCE_CONFIDENCE_THRESHOLD: float = 0.60

    # ---------------------------------------------------------
    # LLM Provider Configuration
    # ---------------------------------------------------------
    LLM_PROVIDER: Literal["groq", "openai", "anthropic", "mock"] = "groq"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # API Keys
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ---------------------------------------------------------
    # MongoDB Atlas Database Configuration
    # ---------------------------------------------------------
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "confidence_rag"
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_MIN_POOL_SIZE: int = 5
    MONGODB_TIMEOUT_MS: int = 1500
    MONGODB_RETRY_WRITES: bool = True

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# Global singleton settings instance
settings = Settings()
settings.ensure_directories()
