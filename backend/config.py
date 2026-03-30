from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""
    database_url: str = ""
    frontend_url: str = "http://localhost:3000"
    secret_key: str = "change-me"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
