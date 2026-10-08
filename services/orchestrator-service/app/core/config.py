import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ATS Orchestrator & Ranking Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://ats_user:ats_password@localhost:5432/ats_parser_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # ML Models
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
    EMBEDDING_DIM: int = 384
    RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "Xenova/ms-marco-MiniLM-L-6-v2")
    
    # ANN search limits
    DEFAULT_COARSE_TOP_K: int = 100
    QUERY_CACHE_TTL: int = 300 # seconds

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
