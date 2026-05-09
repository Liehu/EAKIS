from __future__ import annotations

import hashlib
import logging
import math
import openai

from src.core.settings import get_settings
from src.shared.cache import TTLCache

logger = logging.getLogger("eakis.rag.embeddings")

_VECTOR_DIM = 128


class EmbeddingService:
    """Embedding generation with OpenAI API and deterministic fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.rag_embedding_model
        self._vector_size = settings.qdrant_vector_size
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url
        self._use_openai = bool(settings.openai_api_key and not settings.rag_use_stubs)
        self._cache = TTLCache()

    @property
    def vector_size(self) -> int:
        if self._use_openai:
            return self._vector_size
        return _VECTOR_DIM

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        cached_results: list[list[float] | None] = []
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            key = hashlib.md5(text.encode()).hexdigest()
            hit = self._cache.get(key)
            if hit is not None:
                cached_results.append(hit)
            else:
                cached_results.append(None)
                uncached_indices.append(i)
                uncached_texts.append(text)

        new_vectors: list[list[float]] = []
        if uncached_texts:
            if self._use_openai:
                new_vectors = await self._embed_openai(uncached_texts)
            else:
                new_vectors = self._embed_fallback(uncached_texts)

            for j, vec in enumerate(new_vectors):
                key = hashlib.md5(uncached_texts[j].encode()).hexdigest()
                self._cache.set(key, vec)

        results: list[list[float]] = []
        uncached_ptr = 0
        for cached in cached_results:
            if cached is not None:
                results.append(cached)
            else:
                results.append(new_vectors[uncached_ptr])
                uncached_ptr += 1

        return results

    async def embed_query(self, query: str) -> list[float]:
        vectors = await self.embed_texts([query])
        return vectors[0]

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        client = openai.AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        batch_size = 100
        all_vectors: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = await client.embeddings.create(input=batch, model=self._model)
            for item in response.data:
                all_vectors.append(item.embedding)

        return all_vectors

    def _embed_fallback(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vec = []
            for i in range(_VECTOR_DIM):
                byte_idx = (i * 4) % len(digest)
                val = int.from_bytes(digest[byte_idx : byte_idx + 4], "big")
                vec.append(val / (2**32 - 1))
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            vectors.append(vec)
        return vectors


class StubEmbeddingService:
    """Minimal embedding service for unit tests."""

    def __init__(self, vector_dim: int = _VECTOR_DIM) -> None:
        self._dim = vector_dim

    @property
    def vector_size(self) -> int:
        return self._dim

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._hash_vector(query)

    def _hash_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self._dim):
            byte_idx = (i * 4) % len(digest)
            val = int.from_bytes(digest[byte_idx : byte_idx + 4], "big")
            vec.append(val / (2**32 - 1))
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec
