from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_NAME: str = "DEDC Survey API"
    ADMIN_ROLE_NAME: str = "Admin"
    PORTAL_COOKIE_SECURE: bool = False
    PRIVATE_STORAGE_DIR: str = "private/dedc"
    DATABASE_CONNECT_TIMEOUT: int = 5
    DATABASE_POOL_TIMEOUT: int = 5
    DATABASE_READ_TIMEOUT: int = 5
    DATABASE_WRITE_TIMEOUT: int = 5
    METADATA_STORAGE: Literal['sql', 'private'] = 'sql'

    class Config:
        env_file = ".env"


settings = Settings()
