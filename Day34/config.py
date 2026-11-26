from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "mysql+pymysql://root:CHANGE_ME@localhost:3306/travel_ai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    chroma_path: str = "./chroma_data"
    internal_api_base_url: str = "http://127.0.0.1:8000"


@lru_cache
def settings():
    return Settings()
