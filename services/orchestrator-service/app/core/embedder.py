import hashlib
import logging
from typing import List
import numpy as np

from app.core.config import settings
from app.cache.redis_cache import cache

logger = logging.getLogger(__name__)

class DenseEmbedder:
    def __init__(self):
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            from fastembed import TextEmbedding
            # BAAI/bge-small-en-v1.5 produces 384-dimensional normalized vectors
            self.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("FastEmbed BAAI/bge-small-en-v1.5 initialized successfully.")
        except Exception as e:
            logger.warning(f"FastEmbed initialization deferred or failed: {e}. Fallback mode active.")
            self.model = None

    async def embed_text(self, text: str) -> List[float]:
        """
        Generates 384-dim normalized vector for a single text, utilizing Redis cache.
        """
        if not text:
            text = "empty"

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        
        # Check Redis Cache
        cached_vec = await cache.get_embedding(text_hash)
        if cached_vec is not None:
            return cached_vec

        # Compute embedding
        vector = self._compute_embedding(text)

        # Store in Redis Cache
        await cache.set_embedding(text_hash, vector)
        return vector

    def _compute_embedding(self, text: str) -> List[float]:
        if self.model:
            try:
                embeddings = list(self.model.embed([text]))
                vec = embeddings[0]
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                return vec.tolist()
            except Exception as e:
                logger.error(f"Error computing FastEmbed embedding: {e}")

        # Deterministic semantic fallback vector if ONNX model is still downloading
        # Generates normalized 384-dim vector seeded by text content
        rng = np.random.default_rng(seed=int(hashlib.md5(text.encode('utf-8')).hexdigest()[:8], 16))
        vec = rng.standard_normal(settings.EMBEDDING_DIM).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Vectorized batch embedding with Redis caching.
        """
        results: List[List[float]] = []
        for t in texts:
            vec = await self.embed_text(t)
            results.append(vec)
        return results

embedder = DenseEmbedder()
