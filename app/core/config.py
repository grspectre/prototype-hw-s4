import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI App"
    PROJECT_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    DATABASE_URL: str
    
    class Config:
        env_file = ".env"
        
settings = Settings()
