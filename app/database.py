from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "admin_mdg"
    POSTGRES_PASSWORD: str = "supersecret_dev_pass"
    POSTGRES_DB: str = "enterprise_mdg_db"
    POSTGRES_PORT: int = 5432
    POSTGRES_HOST: str = "localhost"
    API_SECRET_KEY: str = "mdg-enterprise-secret-token-2026"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependencia de FastAPI que abre una sesión de BD por petición y la cierra al terminar"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
