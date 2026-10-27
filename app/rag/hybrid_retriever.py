
import json
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "customer_context.json"
)

MODEL_NAME = "all-MiniLM-L6-v2"


def tokenize(text: str) -> list[str]:
    """Simple lowercase tokenization for BM25."""
    return text.lower().split()


def retrieve_hybrid_context(
    customer_id: str | None,
    query: str,
    max_results: int = 3,
    semantic_weight: float = 0.5,
    customer_email: str | None = None,
) -> list[dict]:
    """Combine semantic and keyword search within one verified customer scope."""

    if max_results <= 0:
        return []

    if not 0.0 <= semantic_weight <= 1.0:
        raise ValueError("semantic_weight must be between 0 and 1.")

    with DATA_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    # Prefer an explicit email association for invoice-driven requests.
    # Legacy synthetic IDs remain available only to callers that have one.
    normalized_email = (customer_email or "").strip().casefold()
    if normalized_email:
        customer_records = [
            record
            for record in records
            if str(record.get("customer_email") or "").strip().casefold()
            == normalized_email
        ]
    elif customer_id:
        customer_records = [
            record
            for record in records
            if record.get("customer_id") == customer_id
        ]
    else:
        customer_records = []

    if not customer_records:
        return []

    texts = [record.get("text", "") for record in customer_records]

    # 1. Semantic search using Sentence Transformers + FAISS.
    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    semantic_scores, semantic_indexes = index.search(
        query_embedding,
        len(customer_records),
    )

    semantic_rank = {
        int(record_index): rank
        for rank, record_index in enumerate(semantic_indexes[0])
        if record_index >= 0
    }

    # 2. Keyword search using BM25.
    tokenized_texts = [tokenize(text) for text in texts]
    bm25 = BM25Okapi(tokenized_texts)
    bm25_scores = bm25.get_scores(tokenize(query))

    keyword_order = sorted(
        range(len(customer_records)),
        key=lambda i: bm25_scores[i],
        reverse=True,
    )

    keyword_rank = {
        record_index: rank
        for rank, record_index in enumerate(keyword_order)
    }

    # 3. Combine rankings using Reciprocal Rank Fusion (RRF).
    # RRF avoids directly mixing scores from different scales.
    rrf_k = 60
    combined = []

    for record_index, record in enumerate(customer_records):
        semantic_position = semantic_rank.get(record_index)
        keyword_position = keyword_rank.get(record_index)

        semantic_rrf = (
            1.0 / (rrf_k + semantic_position + 1)
            if semantic_position is not None
            else 0.0
        )
        keyword_rrf = (
            1.0 / (rrf_k + keyword_position + 1)
            if keyword_position is not None
            else 0.0
        )

        combined_score = (
            semantic_weight * semantic_rrf
            + (1.0 - semantic_weight) * keyword_rrf
        )

        combined.append(
            {
                "type": record["type"],
                "invoice_id": record["invoice_id"],
                "text": record["text"],
                "semantic_score": float(
                    semantic_scores[0][semantic_position]
                ) if semantic_position is not None else 0.0,
                "keyword_score": float(bm25_scores[record_index]),
                "hybrid_score": float(combined_score),
            }
        )

    combined.sort(
        key=lambda item: item["hybrid_score"],
        reverse=True,
    )

    return combined[:max_results]
