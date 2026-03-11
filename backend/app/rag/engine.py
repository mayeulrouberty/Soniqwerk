from __future__ import annotations
import math
from typing import Optional
from app.config import settings
from app.rag.embeddings import embed_query
from app.rag.collections import get_collection, VALID_COLLECTIONS

# Lazy-loaded reranker to avoid slow import at startup
_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _mmr_select(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int,
    lambda_mult: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance selection.
    lambda_mult=0.7 → 70% relevance, 30% diversity.
    """
    if not candidates:
        return []

    selected = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            cand = candidates[idx]
            relevance = _cosine_similarity(query_embedding, cand["embedding"])

            if not selected:
                mmr_score = relevance
            else:
                max_sim = max(
                    _cosine_similarity(cand["embedding"], candidates[s]["embedding"])
                    for s in selected
                )
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    return [candidates[i] for i in selected]


async def retrieve(
    query: str,
    categories: Optional[list[str]] = None,
    top_k: Optional[int] = None,
) -> list[dict]:
    """
    RAG retrieval pipeline:
    1. Embed query
    2. Fetch fetch_k candidates per collection (ChromaDB cosine)
    3. MMR selection for diversity
    4. Cross-encoder reranking (if use_reranker=True)
    5. Return top_k chunks with score, text, metadata

    Returns list of dicts:
    {
        "text": str,
        "metadata": dict,
        "score": float,      # similarity in [0, 1]
        "embedding": list[float]  # for MMR diversity computation
    }
    """
    k = top_k or settings.rag_top_k
    fetch_k = settings.rag_fetch_k
    search_cats = categories or list(VALID_COLLECTIONS)

    query_embedding = await embed_query(query)

    # 1. Fetch candidates from all collections
    all_candidates: list[dict] = []
    for category in search_cats:
        try:
            collection = get_collection(category)
            if collection.count() == 0:
                continue
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(fetch_k, collection.count()),
                include=["documents", "metadatas", "distances", "embeddings"],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            embeddings = results["embeddings"][0]

            for doc, meta, dist, emb in zip(docs, metas, dists, embeddings):
                # ChromaDB cosine distance ∈ [0, 2] → similarity ∈ [0, 1]
                score = float(1.0 - (dist / 2.0))
                all_candidates.append({
                    "text": doc,
                    "metadata": meta,
                    "score": score,
                    "embedding": list(emb),
                })
        except Exception:
            # Collection may not exist yet — skip silently
            continue

    if not all_candidates:
        return []

    # 2. MMR selection for diversity
    mmr_results = _mmr_select(
        query_embedding=query_embedding,
        candidates=all_candidates,
        top_k=min(k * 3, len(all_candidates)),  # Over-fetch for reranker
        lambda_mult=0.7,
    )

    # 3. Cross-encoder reranking
    if settings.use_reranker and len(mmr_results) > 1:
        reranker = _get_reranker()
        pairs = [[query, c["text"]] for c in mmr_results]
        scores = reranker.predict(pairs)
        for chunk, score in zip(mmr_results, scores):
            chunk["rerank_score"] = float(score)
        mmr_results.sort(key=lambda x: x.get("rerank_score", x["score"]), reverse=True)

    # 4. Return top_k, drop internal embedding field
    final = mmr_results[:k]
    for chunk in final:
        chunk.pop("embedding", None)
        chunk.pop("rerank_score", None)

    return final
