import json
from pathlib import Path

from sentence_transformers import SentenceTransformer, util

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "customer_context.json"
)

MODEL_NAME = "all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


def retrieve_semantic_context(
    customer_id: str,
    query: str,
    max_results: int = 3,
    similarity_threshold: float = 0.35,
):
    """Retrieve relevant customer context using semantic similarity."""

    if max_results <= 0:
        return []

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("Similarity threshold must be between 0 and 1.")

    with DATA_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    customer_records = [
        record
        for record in records
        if record.get("customer_id") == customer_id
    ]

    if not customer_records:
        return []

    texts = [record["text"] for record in customer_records]

    query_embedding = model.encode(
        query,
        convert_to_tensor=True,
    )

    document_embeddings = model.encode(
        texts,
        convert_to_tensor=True,
    )

    similarities = util.cos_sim(
        query_embedding,
        document_embeddings,
    )[0]

    ranked_indexes = similarities.argsort(
        descending=True
    ).tolist()

    results = []

    for index in ranked_indexes:
        score = float(similarities[index])

        if score < similarity_threshold:
            continue

        record = customer_records[index]

        results.append(
            {
                "type": record["type"],
                "invoice_id": record["invoice_id"],
                "text": record["text"],
                "similarity": score,
            }
        )

        if len(results) >= max_results:
            break

    return results