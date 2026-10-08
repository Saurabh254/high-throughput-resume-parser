from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import db
from app.cache.redis_cache import cache
from app.api.v1.endpoints import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB and Redis
    await db.connect()
    await cache.get_client()
    yield
    # Shutdown
    await db.close()
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
    pool = await db.get_pool()
    db_alive = pool is not None
    redis_client = await cache.get_client()
    redis_alive = redis_client is not None

    return {
        "status": "healthy" if db_alive and redis_alive else "degraded",
        "service": "orchestrator-service",
        "database_connected": db_alive,
        "redis_connected": redis_alive
    }
