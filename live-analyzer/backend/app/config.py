import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    KITE_API_KEY: str = "your_kite_api_key"
    KITE_API_SECRET: str = "your_kite_api_secret"
    ENCRYPTION_KEY: str = "your_fernet_encryption_key_here"
    APP_PASSWORD_HASH: str = "your_bcrypt_hashed_password_here"
    BIND_IP: str = "127.0.0.1"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///./portfolio.db"
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
