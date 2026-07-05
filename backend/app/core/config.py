from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "FitNova AI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "fitnova"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info: Any) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        server = data.get("POSTGRES_SERVER", "localhost")
        user = data.get("POSTGRES_USER", "postgres")
        pw = data.get("POSTGRES_PASSWORD", "postgrespassword")
        db = data.get("POSTGRES_DB", "fitnova")
        port = data.get("POSTGRES_PORT", "5432")
        return f"postgresql://{user}:{pw}@{server}:{port}/{db}"

    # CORS Origins (JSON list or comma-separated string)
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str] | None) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    # Whisper Configuration
    WHISPER_MODEL: str = "base"
    WHISPER_MOCK: bool = False

    # Hugging Face Configuration
    HF_TOKEN: str | None = None

    # Diarization Configuration
    DIARIZATION_MOCK: bool = False
    PYANNOTE_CLUSTERING_THRESHOLD: float = 0.55
    DIARIZATION_NUM_SPEAKERS: int | None = 2
    DIARIZATION_STRATEGY: str = "hybrid"
    DIARIZATION_CHUNK_MAX_SECONDS: float = 5.0
    DIARIZATION_SILENCE_GAP_SECONDS: float = 0.4
    DIARIZATION_MIN_EMBEDDING_SECONDS: float = 0.5

    # LLM Settings
    LLM_PROVIDER: str = "groq"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
