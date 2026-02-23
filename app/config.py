from pydantic_settings import BaseSettings , SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    # Issue 5: No more hardcoded localhost in the logic
    BASE_URL: str = "http://localhost:8000" 
    APP_NAME: str = "Url Shortener"
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()