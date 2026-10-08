import logging

import asyncpg
from app.core.config import settings
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        if self.pool is None:
            # Normalize database URL for asyncpg (strip +asyncpg if present)
            db_url = settings.DATABASE_URL.replace(
                "postgresql+asyncpg://", "postgresql://"
            )

            async def init_connection(conn):
                await register_vector(conn)

            try:
                self.pool = await asyncpg.create_pool(
                    dsn=db_url,
                    min_size=2,
                    max_size=20,
                    init=init_connection,
                    command_timeout=60,
                )
                logger.info(
                    "Successfully initialized PostgreSQL connection pool with pgvector support."
                )
            except Exception as e:
                logger.warning(f"Could not connect to PostgreSQL: {e}")
                self.pool = None

    async def get_pool(self) -> asyncpg.Pool | None:
        if self.pool is None:
            await self.connect()
        return self.pool

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None


db = DatabaseManager()
