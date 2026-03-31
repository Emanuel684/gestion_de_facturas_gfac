import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Database (en Render: copiar Internal Database URL y usar variable DATABASE_URL)
    database_url: str = "postgresql+asyncpg://sgfuser:sgfpass@localhost:5433/sgf_db"

    @field_validator("database_url", mode="before")
    @classmethod
    def coerce_async_driver(cls, v: object) -> object:
        """Render/Neon suelen dar `postgresql://...`; SQLAlchemy async exige `postgresql+asyncpg://`."""
        if isinstance(v, str) and v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def reject_localhost_on_render(self) -> "Settings":
        if os.getenv("RENDER") == "true" and self.database_url:
            bad = "localhost" in self.database_url or "127.0.0.1" in self.database_url
            if bad:
                raise ValueError(
                    "DATABASE_URL en Render no puede ser localhost. "
                    "En el panel de tu PostgreSQL en Render, copia «Internal Database URL» "
                    "y pégala como DATABASE_URL en el Web Service (mismo equipo / región)."
                )
        return self

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Extracción de facturas (Google Gemini). Opcional: si está vacío se usa solo OCR + regex.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
