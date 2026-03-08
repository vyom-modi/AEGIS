"""
AEGIS Configuration Module.

Loads environment variables and exposes typed settings.
All LLM and service configuration is centralized here.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- LLM ---
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""

    # --- Supabase ---
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # --- E2B Sandbox ---
    e2b_api_key: str = ""

    # --- LangSmith (optional) ---
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "aegis"

    # --- App ---
    app_name: str = "AEGIS"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
