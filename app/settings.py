"""Application settings and configuration."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Server settings
    port: int = 9000
    host: str = "0.0.0.0"
    debug: bool = False
    
    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    # API settings
    api_title: str = "Valuation API"
    api_description: str = "Deterministic valuation engine for financial instruments"
    api_version: str = "0.1.0"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
