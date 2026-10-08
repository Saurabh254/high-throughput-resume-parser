import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ATS Ingestion & LLM Parsing Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage & Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "heuristic") # heuristic, ollama, openai
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Orchestrator Service URL for auto-forwarding indexing
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8002")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
