# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    db_driver: str = "postgresql"
    db_user: str = "postgres"
    db_password: str = "root123"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: str = "autocare_db"

    @property
    def database_url(self) -> str:
        return f"{self.db_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # JWT
    SECRET_KEY: str = "dev_secret_key_123"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Upload
    upload_dir: str = "./app/uploads"
    max_upload_size: int = 5 * 1024 * 1024  # 5MB
    allowed_extensions: List[str] = ["jpg", "jpeg", "png", "gif"]
    
    # App
    debug: bool = True
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()