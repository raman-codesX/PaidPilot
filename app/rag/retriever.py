import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "customer_context.json"


def retrieve_customer_context(
    customer_id: str,
    query: str,
    max_results: int = 3,
):
    """Retrieve relevant notes for a specific customer."""

    if max_results <= 0:
        return []

    with DATA_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    query_words = set(query.lower().split())
    matches = []

    for record in records:
        if record.get("customer_id") != customer_id:
            continue

        text = record.get("text", "")
        record_words = set(text.lower().split())
        score = len(query_words & record_words)

        if score > 0:
            matches.append((score, record))

    matches.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "type": record["type"],
            "invoice_id": record["invoice_id"],
            "text": record["text"],
        }
        for _, record in matches[:max_results]
    ]