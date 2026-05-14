from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Axxess
    axxess_base_url: str
    axxess_auth_url: str
    axxess_client_id: str
    axxess_client_secret: str
    axxess_account_id: str
    axxess_time_zone: str = "America/Chicago"

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # AI
    anthropic_api_key: str
    openai_api_key: str

    # App
    app_env: str = "development"
    secret_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
