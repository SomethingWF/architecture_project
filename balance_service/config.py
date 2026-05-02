import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: str = "5432"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "wallet_db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

os.environ["PERSISTENCE_MODULE"] = "eventsourcing.postgres"
os.environ["POSTGRES_HOST"] = settings.postgres_host
os.environ["POSTGRES_PORT"] = settings.postgres_port
os.environ["POSTGRES_USER"] = settings.postgres_user
os.environ["POSTGRES_PASSWORD"] = settings.postgres_password
os.environ["POSTGRES_DBNAME"] = settings.postgres_db

READ_MODEL_DB_URL = f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"