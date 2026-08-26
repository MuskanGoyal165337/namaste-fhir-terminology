from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        from pydantic import BaseSettings
        SettingsConfigDict = None
    except ImportError:
        # Minimal BaseSettings fallback using pydantic BaseModel
        from pydantic import BaseModel
        class BaseSettings(BaseModel):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
        SettingsConfigDict = None

class Settings(BaseSettings):
    APP_NAME: str = "AYUSH EMR Terminology Microservice"
    APP_ENV: str = "development"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    SECRET_KEY: str = "default_secret_key_change_in_production"
    
    # CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

    # Database
    POSTGRES_USER: str = "ayush_user"
    POSTGRES_PASSWORD: str = "ayush_password"
    POSTGRES_DB: str = "ayush_terminology_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://ayush_user:ayush_password@db:5432/ayush_terminology_db"

    # ABHA OAuth 2.0 Configuration
    # Set ABHA_INTROSPECT_URL to an empty string to use the Mock provider (test/dev mode).
    ABHA_INTROSPECT_URL: str = ""
    ABHA_CLIENT_ID: str = ""
    ABHA_CLIENT_SECRET: str = ""
    # Mock token accepted by MockABHAProvider (non-production use only)
    ABHA_MOCK_TOKEN: str = "test-mock-token"

    # WHO ICD-11 MMS API Configuration
    WHO_USE_MOCK: bool = True
    WHO_API_URL: str = "https://id.who.int/icd/release/11/mms"
    WHO_TOKEN_URL: str = "https://icdaccessmanagement.who.int/connect/token"
    WHO_CLIENT_ID: str = ""
    WHO_CLIENT_SECRET: str = ""

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """
        Normalize DATABASE_URL: Render and some cloud platforms supply the
        legacy 'postgres://' scheme, but SQLAlchemy 2.0 requires 'postgresql://'.
        """
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

@lru_cache()
def get_settings() -> Settings:
    return Settings()
