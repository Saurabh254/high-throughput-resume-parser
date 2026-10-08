from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.endpoints import router as api_router
from app.cache.redis_cache import cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure Redis connection check
    await cache.get_client()
    yield
    # Shutdown: clean up redis
    await cache.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    redis_client = await cache.get_client()
    redis_alive = False
    if redis_client:
        try:
            redis_alive = await redis_client.ping()
        except Exception:
            redis_alive = False

    return {
        "status": "healthy",
        "service": "ingestion-service",
        "redis_connected": bool(redis_alive),
        "llm_provider": settings.LLM_PROVIDER
    }
