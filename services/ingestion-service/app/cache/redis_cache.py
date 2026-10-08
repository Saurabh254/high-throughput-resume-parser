import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class IngestionCache:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def get_client(self) -> Optional[redis.Redis]:
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2.0
                )
                await self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection unavailable: {e}. Running without cache.")
                self.redis_client = None
        return self.redis_client

    async def get_by_file_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        client = await self.get_client()
        if not client:
            return None
        try:
            val = await client.get(f"cache:file_hash:{file_hash}")
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Error reading file hash cache: {e}")
        return None

    async def set_by_file_hash(self, file_hash: str, data: Dict[str, Any], ttl: int = 604800) -> bool:
        client = await self.get_client()
        if not client:
            return False
        try:
            await client.setex(f"cache:file_hash:{file_hash}", ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.warning(f"Error setting file hash cache: {e}")
            return False

    async def get_by_text_hash(self, text_hash: str) -> Optional[Dict[str, Any]]:
        client = await self.get_client()
        if not client:
            return None
        try:
            val = await client.get(f"cache:parsed_text:{text_hash}")
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Error reading text hash cache: {e}")
        return None

    async def set_by_text_hash(self, text_hash: str, data: Dict[str, Any], ttl: int = 604800) -> bool:
        client = await self.get_client()
        if not client:
            return False
        try:
            await client.setex(f"cache:parsed_text:{text_hash}", ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.warning(f"Error setting text hash cache: {e}")
            return False

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

cache = IngestionCache()
