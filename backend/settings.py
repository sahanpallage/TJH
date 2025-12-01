from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

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
    DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    MODEL_API_KEY: str = ""
    APIFY_API_KEY: str = ""
    APIFY_ACTOR_ID: str = "misceres~indeed-scraper"  # Default Apify Indeed scraper actor (format: username~actor-name)
    
    # API Authentication (for HR admins)
    API_KEY: str = ""  # API key for authenticating requests
    API_KEY_HEADER: str = "X-API-Key"  # Header name for API key
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60  # Requests per minute per IP
    RATE_LIMIT_PER_HOUR: int = 500  # Requests per hour per IP
    
    # Request Timeouts (in seconds)
    REQUEST_TIMEOUT_SECONDS: int = 10
    JSEARCH_TIMEOUT: int = 10
    INDEED_TIMEOUT: int = 120  # Apify can take longer
    LINKEDIN_TIMEOUT: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "json"  # "json" or "text"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production
    
    def validate_required(self) -> None:
        """Validate that required environment variables are set based on environment."""
        errors = []
        
        # Always required
        if not self.RAPID_API_KEY:
            errors.append("RAPID_API_KEY is required")
        if not self.SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        if not self.SUPABASE_KEY:
            errors.append("SUPABASE_KEY is required")
        
        # Required for production
        if self.ENVIRONMENT == "production":
            if not self.API_KEY:
                errors.append("API_KEY is required in production")
            if not self.APIFY_API_KEY:
                errors.append("APIFY_API_KEY is required for Indeed searches")
        
        if errors:
            raise ValueError(f"Missing required environment variables:\n" + "\n".join(f"  - {e}" for e in errors))

# Create a global settings instance
settings = Settings()

# Validate required settings (only in production or if explicitly enabled)
if os.getenv("VALIDATE_ENV", "false").lower() == "true" or settings.ENVIRONMENT == "production":
    try:
        settings.validate_required()
    except ValueError as e:
        import sys
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

# Export individual variables for backward compatibility
RAPID_API_KEY = settings.RAPID_API_KEY
LINKEDIN_API_KEY = settings.LINKEDIN_API_KEY
DATABASE_URL = settings.DATABASE_URL
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
MODEL_API_KEY = settings.MODEL_API_KEY
APIFY_API_KEY = settings.APIFY_API_KEY
APIFY_ACTOR_ID = settings.APIFY_ACTOR_ID