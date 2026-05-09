from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Insider Risk Investigation Assistant"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./insider_risk.db"
    DEFAULT_SCORING_WINDOW_DAYS: int = 14
    ALERT_AUTO_CREATE_THRESHOLD: float = 40.0
    CASE_AUTO_CREATE_THRESHOLD: float = 60.0
    MAX_CSV_SIZE_MB: int = 50
    DEFAULT_ANALYST: str = "analyst@acme-corp.com"

    class Config:
        env_file = ".env"


settings = Settings()
