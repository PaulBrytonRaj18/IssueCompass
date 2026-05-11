from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent.parent.parent / ".env",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return ".env"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "OpenIssue"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://openissue:openissue@localhost:5432/openissue"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"
    GITHUB_GRAPHQL_URL: str = "https://api.github.com/graphql"

    # JWT
    SECRET_KEY: str = "change_this_in_production_use_random_string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Matching
    MATCH_SCORE_THRESHOLD: float = 0.3
    MAX_MATCHES_PER_USER: int = 50

    model_config = SettingsConfigDict(env_file=_find_env_file(), extra="ignore")

    @model_validator(mode="after")
    def validate_required(self):
        if not self.SECRET_KEY or self.SECRET_KEY == "change_this_in_production_use_random_string":
            raise ValueError("SECRET_KEY must be changed from the default in production")
        if not self.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN is required")
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
