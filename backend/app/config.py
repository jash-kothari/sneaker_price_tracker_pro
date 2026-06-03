import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SoleSentry Pro"
    
    # Database Configurations
    # Default to postgresql+asyncpg for async operations, using docker DB container hostname by default
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@db:5432/solesentry"
    )
    
    # Sync DB URL for Alembic migrations (which runs synchronously)
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/solesentry"
    )
    
    # Redis Configurations
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN_PLACEHOLDER")
    
    # Price Check Scheduler Settings
    PRICE_CHECK_INTERVAL_SECONDS: int = int(os.getenv("PRICE_CHECK_INTERVAL_SECONDS", "300"))
    
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
