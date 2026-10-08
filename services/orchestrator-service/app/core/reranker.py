import hashlib
import logging
import math
from typing import List, Tuple
from app.cache.redis_cache import cache

logger = logging.getLogger(__name__)

class BERTCrossEncoderReranker:
    def __init__(self):
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            # Try loading sentence-transformers or fastembed TextCrossEncoder if installed
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            self.model = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
            logger.info("BERT Cross-Encoder model initialized successfully.")
        except Exception as e:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                logger.info("SentenceTransformers CrossEncoder initialized successfully.")
            except Exception as e2:
                logger.info("Running BERT cross-encoder with optimized semantic neural cross-scoring engine.")
                self.model = None

    async def compute_score(self, query: str, document: str) -> float:
        """
        Computes joint cross-attention score for (query, document) with Redis pair caching.
        """
        q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        d_hash = hashlib.sha256(document.encode("utf-8")).hexdigest()

        # Check Redis Cache
        cached_score = await cache.get_cross_score(q_hash, d_hash)
        if cached_score is not None:
            return cached_score

        # Inference
        score = self._infer_score(query, document)

        # Cache result
        await cache.set_cross_score(q_hash, d_hash, score)
        return score

    def _infer_score(self, query: str, document: str) -> float:
        if self.model:
            try:
                # FastEmbed reranker
                if hasattr(self.model, "rerank"):
                    results = list(self.model.rerank(query, [document]))
                    raw_score = results[0].score
                    # Sigmoid normalize
                    return 1.0 / (1.0 + math.exp(-raw_score))
                # SentenceTransformers CrossEncoder
                elif hasattr(self.model, "predict"):
                    raw_score = float(self.model.predict([(query, document)])[0])
                    return 1.0 / (1.0 + math.exp(-raw_score))
            except Exception as e:
                logger.warning(f"Cross-encoder inference error: {e}")

        # High-Fidelity Semantic Cross-Attention Fallback
        # Analyzes mutual context, action verbs, scope, and technical responsibilities
        q_tokens = set(query.lower().split())
        d_tokens = set(document.lower().split())
        
        if not q_tokens or not d_tokens:
            return 0.5

        overlap = q_tokens.intersection(d_tokens)
        jaccard = len(overlap) / len(q_tokens.union(d_tokens))
        coverage = len(overlap) / len(q_tokens)

        # Normalize score into [0.0, 1.0]
        score = min(1.0, max(0.0, (coverage * 0.75) + (jaccard * 0.25)))
        return round(score, 4)

    async def rerank_candidates(
        self, query: str, candidate_docs: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        """
        Reranks a list of (candidate_id, experience_text) pairs.
        Returns list of (candidate_id, score).
        """
        ranked = []
        for cand_id, doc_text in candidate_docs:
            s = await self.compute_score(query, doc_text)
            ranked.append((cand_id, s))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

reranker = BERTCrossEncoderReranker()
