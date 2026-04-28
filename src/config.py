import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_env: str = "development"
    allow_insecure_defaults: bool = True

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
    access_token_expire_minutes: int = 15
    jwt_issuer: str = "sgf-api"
    jwt_audience: str = "sgf-web"
    jwt_cookie_name: str = "sgf_access_token"

    # CORS
    cors_origins: str = "*"
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "Authorization,Content-Type,Accept,Origin,X-Requested-With"

    # Extracción de facturas (Google Gemini). Opcional: si está vacío se usa solo OCR + regex.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    return_raw_text_in_upload: bool = False
    max_upload_pages: int = 20
    max_upload_pixels: int = 25000000

    # Runtime behavior toggles
    seed_demo_data: bool = True
    enable_mock_checkout: bool = True
    auto_migrate_on_startup: bool = True
    enable_openapi: bool = True
    trusted_hosts: str = "localhost,127.0.0.1,test,api"
    require_https_redirect: bool = False
    login_rate_limit_window_seconds: int = 300
    login_rate_limit_max_attempts: int = 8

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def cors_allow_methods_list(self) -> list[str]:
        return [m.strip().upper() for m in self.cors_allow_methods.split(",") if m.strip()]

    @property
    def cors_allow_headers_list(self) -> list[str]:
        return [h.strip() for h in self.cors_allow_headers.split(",") if h.strip()]

    @property
    def trusted_hosts_list(self) -> list[str]:
        hosts = [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]
        return hosts or ["*"]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def cors_allow_any(self) -> bool:
        return "*" in self.cors_origins_list

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_env(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def security_guards(self) -> "Settings":
        if not self.allow_insecure_defaults and (
            self.secret_key == "dev-secret-key-change-in-production"
            or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY insegura: defina una clave fuerte de al menos 32 caracteres.")
        if self.is_production and (
            self.secret_key == "dev-secret-key-change-in-production"
            or len(self.secret_key) < 32
        ):
            raise ValueError("Producción requiere SECRET_KEY segura (>=32 caracteres y no default).")
        if self.is_production and self.enable_mock_checkout:
            raise ValueError("ENABLE_MOCK_CHECKOUT debe estar en false en producción.")
        if self.is_production and self.seed_demo_data:
            raise ValueError("SEED_DEMO_DATA debe estar en false en producción.")
        if self.is_production and self.enable_openapi:
            raise ValueError("ENABLE_OPENAPI debe estar en false en producción.")
        return self


settings = Settings()
