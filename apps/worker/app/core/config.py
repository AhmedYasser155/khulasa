"""
core/config.py

Central settings, loaded from .env (searched up from wherever the
process starts, via find_dotenv, so this works whether you run things
from the repo root or from apps/worker).

extra="ignore" matters: without it, pydantic-settings raises a hard
error any time .env contains a variable not explicitly declared here
(exactly what just happened with GEMINI_API_KEY, added for one-off
model-comparison testing). Ignoring unknown vars means ad hoc .env
additions for quick tests don't break the whole app on next startup.
"""

from dotenv import load_dotenv, find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    # AI providers
    groq_api_key: str = ""
    llm_provider: str = "groq"
    gemini_api_key: str = ""  # used only in one-off comparison testing, not by the main pipeline


settings = Settings()