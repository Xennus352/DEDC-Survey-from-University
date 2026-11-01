from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./survey.db"
    APP_NAME: str = "DEDC Survey API"

    class Config:
        env_file = ".env"


settings = Settings()
