from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_NAME: str = "DEDC Survey API"
    ADMIN_ROLE_NAME: str = "Admin"
    PORTAL_COOKIE_SECURE: bool = False
    PRIVATE_STORAGE_DIR: str = "private/dedc"

    class Config:
        env_file = ".env"


settings = Settings()
