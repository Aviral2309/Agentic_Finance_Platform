from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "WealthPilot"
    APP_ENV: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"

    DATABASE_URL: str = "postgresql://wealthpilot:wealthpilot_dev@localhost:5432/wealthpilot"
    REDIS_URL: str = "redis://localhost:6379/0"

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    GEMINI_API_KEY: str = ""
    NEWS_API_KEY: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
