import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_TITLE: str = "Async LangGraph Search Assistant"
    SEARXNG_URL: str = "http://localhost:8080/search"
    MAX_RETRY_COUNT: int = 3
    
    # LLM Provider Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Text Sanitization List
    # Pydantic v2 parses comma-separated environment strings into a list automatically
    BANNED_WORDS: list[str] = ["Jio Alert : SPAM\n", "SPAM:", "ALERT:"]

    # Pydantic v2 configuration strategy to auto-load local .env files
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Protects against server crash if extra fields exist in .env
    )

settings = Settings()
