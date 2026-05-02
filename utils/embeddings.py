"""
utils/embeddings.py
Voyage AI embedding wrapper — 1024-dimensional vectors.
Used by reasoning_bank retrieval and claim variant similarity.
"""
import voyageai
from typing import List, Optional
from config.settings import settings
from utils.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential

log = get_logger(__name__)

_client: Optional[voyageai.Client] = None


def get_voyage_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def embed_text(text: str, input_type: str = "query") -> List[float]:
    """
    Embed a single text string.
    input_type: 'query' for retrieval queries, 'document' for storage.
    """
    client = get_voyage_client()
    result = client.embed(
        texts=[text],
        model="voyage-3",
        input_type=input_type,
    )
    return result.embeddings[0]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def embed_batch(texts: List[str], input_type: str = "document") -> List[List[float]]:
    """Embed a batch of texts."""
    client = get_voyage_client()
    result = client.embed(
        texts=texts,
        model="voyage-3",
        input_type=input_type,
    )
    return result.embeddings


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def rerank(query: str, documents: List[str], top_k: int = 5) -> List[dict]:
    """
    Rerank documents using Voyage AI rerank-2.
    Returns list of {index, relevance_score, document} dicts.
    """
    client = get_voyage_client()
    result = client.rerank(
        query=query,
        documents=documents,
        model="rerank-2",
        top_k=top_k,
    )
    return [
        {
            "index": r.index,
            "relevance_score": r.relevance_score,
            "document": documents[r.index],
        }
        for r in result.results
    ]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Local cosine similarity for threshold gates."""
    import numpy as np
    a, b = np.array(vec_a), np.array(vec_b)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
