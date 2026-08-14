"""Application settings, read once from the environment."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    APP_NAME = "Enterprise AI Automation Platform"
    VERSION = "1.0.0"
    API_PREFIX = "/api/v1"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # SQLite by default so the platform runs with no external services.
    # docker-compose overrides this with PostgreSQL.
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./platform.db")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    CORS_ORIGINS = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4.1-mini")

    # Integration credentials. Every adapter falls back to a sandbox
    # implementation when its credentials are absent, so the platform is
    # demoable without four enterprise tenants.
    CRM_API_KEY = os.getenv("CRM_API_KEY")
    CRM_BASE_URL = os.getenv("CRM_BASE_URL")
    ERP_API_KEY = os.getenv("ERP_API_KEY")
    ERP_BASE_URL = os.getenv("ERP_BASE_URL")
    GOOGLE_WORKSPACE_CREDENTIALS = os.getenv("GOOGLE_WORKSPACE_CREDENTIALS")
    MS365_CLIENT_ID = os.getenv("MS365_CLIENT_ID")
    MS365_CLIENT_SECRET = os.getenv("MS365_CLIENT_SECRET")
    MS365_TENANT_ID = os.getenv("MS365_TENANT_ID")

    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

    SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@nexgen.local")
    SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@12345")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.GEMINI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
