import json
import logging
import struct
from typing import Any

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class OrchestratorCache:
    def __init__(self):
        self.redis_client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis | None:
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False, # binary safe for packed vectors
                    socket_connect_timeout=2.0
                )
                assert self.redis_client is not None
                await self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis cache unavailable in orchestrator: {e}")
                self.redis_client = None
        return self.redis_client

    async def get_embedding(self, text_hash: str) -> list[float] | None:
        """Retrieves packed float32 vector from Redis."""
        client = await self.get_client()
        if not client:
            return None
        try:
            raw = await client.get(f"cache:embed:{text_hash}".encode())
            if raw:
                # Unpack 384 float32 values
                count = len(raw) // 4
                return list(struct.unpack(f"{count}f", raw))
        except Exception as e:
            logger.warning(f"Error reading vector from cache: {e}")
        return None

    async def set_embedding(self, text_hash: str, vector: list[float], ttl: int = 604800) -> bool:
        """Packs and saves float32 vector in Redis."""
        client = await self.get_client()
        if not client:
            return False
        try:
            packed = struct.pack(f"{len(vector)}f", *vector)
            await client.setex(f"cache:embed:{text_hash}".encode(), ttl, packed)
            return True
        except Exception as e:
            logger.warning(f"Error saving vector to cache: {e}")
            return False

    async def get_cross_score(self, jd_hash: str, exp_hash: str) -> float | None:
        """Retrieves cached BERT Cross-Encoder score."""
        client = await self.get_client()
        if not client:
            return None
        try:
            key = f"cache:cross:{jd_hash}:{exp_hash}".encode()
            raw = await client.get(key)
            if raw:
                return float(raw.decode())
        except Exception as e:
            logger.warning(f"Error reading cross-encoder cache: {e}")
        return None

    async def set_cross_score(self, jd_hash: str, exp_hash: str, score: float, ttl: int = 604800) -> bool:
        """Saves BERT Cross-Encoder score in Redis."""
        client = await self.get_client()
        if not client:
            return False
        try:
            key = f"cache:cross:{jd_hash}:{exp_hash}".encode()
            await client.setex(key, ttl, str(score).encode())
            return True
        except Exception as e:
            logger.warning(f"Error saving cross-encoder cache: {e}")
            return False

    async def get_query_cache(self, query_hash: str) -> dict[str, Any] | None:
        """Retrieves cached search query response."""
        client = await self.get_client()
        if not client:
            return None
        try:
            raw = await client.get(f"cache:query:{query_hash}".encode())
            if raw:
                return json.loads(raw.decode())
        except Exception as e:
            logger.warning(f"Error reading query cache: {e}")
        return None

    async def set_query_cache(self, query_hash: str, data: dict[str, Any], ttl: int = 300) -> bool:
        """Caches search query response."""
        client = await self.get_client()
        if not client:
            return False
        try:
            raw = json.dumps(data).encode()
            await client.setex(f"cache:query:{query_hash}".encode(), ttl, raw)
            return True
        except Exception as e:
            logger.warning(f"Error setting query cache: {e}")
            return False

    async def invalidate_query_cache(self):
        """Invalidates all cached search queries when new candidates are indexed."""
        client = await self.get_client()
        if not client:
            return
        try:
            keys = await client.keys(b"cache:query:*")
            if keys:
                await client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cached search queries.")
        except Exception as e:
            logger.warning(f"Error invalidating query cache: {e}")

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

cache = OrchestratorCache()
