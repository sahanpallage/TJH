from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # RapidAPI Key for JSearch API
    RAPID_API_KEY: str = ""
    # RapidAPI Key for LinkedIn Scraper API (separate from JSearch)
    LINKEDIN_API_KEY: str = ""
    # TheirStack API Key
    THEIRSTACK_API_KEY: str = ""
    DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    MODEL_API_KEY: str = ""
    APIFY_API_KEY: str = ""
    
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

# Create a global settings instance
settings = Settings()

# Export individual variables for backward compatibility
RAPID_API_KEY = settings.RAPID_API_KEY
LINKEDIN_API_KEY = settings.LINKEDIN_API_KEY
THEIRSTACK_API_KEY = settings.THEIRSTACK_API_KEY
DATABASE_URL = settings.DATABASE_URL
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
MODEL_API_KEY = settings.MODEL_API_KEY
APIFY_API_KEY = settings.APIFY_API_KEY