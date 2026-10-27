
from app.agent.policy import evaluate_action
from app.agent.llm import generate_collection_recommendation
from app.ml.predict import predict_late_payment
from app.rag.hybrid_retriever import retrieve_hybrid_context

def validate_extension_evidence(
    customer_context: list[dict],
    extension_requested: bool,
    extension_evidence: str,
) -> bool:
    """Accept extension intent only when customer notes support it."""

    if not extension_requested or not extension_evidence.strip():
        return False

    evidence = extension_evidence.lower().strip()

    return any(
        item.get("type") == "customer_note"
        and evidence in str(item.get("text") or "").casefold()
        for item in customer_context
    )


def recommend_action(
    late_probability: float,
    invoice_status: str,
    reminder_count: int,
    extension_requested: bool = False,
):
    """Recommend an action using deterministic risk bands and verified context."""

    no_contact_statuses = {"PAID", "VOID", "CANCELLED"}

    if invoice_status in no_contact_statuses:
        action = "DO_NOTHING"
        recommendation_reason = (
            f"Invoice status is {invoice_status}; "
            "no collection action is needed."
        )

    elif extension_requested:
        action = "FRIENDLY_REMINDER"
        recommendation_reason = (
            "The customer requested a payment extension. "
            "A polite follow-up is recommended, regardless of "
            "the predicted risk band."
        )

    elif late_probability <= 0.40:
        action = "DO_NOTHING"
        recommendation_reason = (
            f"Predicted late-payment probability is "
            f"{late_probability:.0%}, which is at or below 40%."
        )

    elif late_probability <= 0.70:
        action = "FRIENDLY_REMINDER"
        recommendation_reason = (
            f"Predicted late-payment probability is "
            f"{late_probability:.0%}, which falls in the "
            "friendly-reminder risk band."
        )

    elif late_probability <= 0.80:
        action = "FIRM_REMINDER"
        recommendation_reason = (
            f"Predicted late-payment probability is "
            f"{late_probability:.0%}, which falls in the "
            "firm-reminder risk band."
        )

    else:
        action = "PAYMENT_PLAN"
        recommendation_reason = (
            f"Predicted late-payment probability is "
            f"{late_probability:.0%}, which falls in the "
            "payment-plan risk band."
        )

    policy_result = evaluate_action(
        action=action,
        late_probability=late_probability,
        invoice_status=invoice_status,
        reminder_count=reminder_count,
        extension_requested=extension_requested,
    )

    return {
        "action": action,
        "recommendation_reason": recommendation_reason,
        "allowed": policy_result["allowed"],
        "policy_reason": policy_result["reason"],
        "requires_human_approval": action != "DO_NOTHING",
    }


def recommend_action_from_invoice(
    invoice_amount,
    previous_invoices,
    previous_late_payments,
    previous_late_rate,
    avg_previous_delay,
    invoice_status,
    reminder_count,
    customer_id,
    query,
    customer_email=None,
    invoice_reference=None,
    currency=None,
    due_at=None,
):
    # Step 1: Predict late-payment risk.
    prediction = predict_late_payment(
        invoice_amount=invoice_amount,
        previous_invoices=previous_invoices,
        previous_late_payments=previous_late_payments,
        previous_late_rate=previous_late_rate,
        avg_previous_delay=avg_previous_delay,
    )

    late_probability = float(prediction["late_probability"])

    # Step 2: Retrieve customer context with hybrid RAG.
    customer_context = retrieve_hybrid_context(
        customer_id=customer_id,
        query=query,
        customer_email=customer_email,
    )

    # Ask the LLM to identify possible extension evidence and prepare a
    # friendly first draft. The final action is selected by deterministic code.
    draft_details = {
        "invoice_reference": invoice_reference,
        "invoice_amount": invoice_amount,
        "currency": currency,
        "due_date": due_at.isoformat() if hasattr(due_at, "isoformat") else due_at,
    }
    if customer_context:
        llm_result = generate_collection_recommendation(
            late_probability=late_probability,
            invoice_status=invoice_status,
            customer_context=customer_context,
            draft_action="FRIENDLY_REMINDER",
            **draft_details,
        )
    else:
        llm_result = {
            "reason": "No verified customer context was available.",
            "draft_message": "",
            "extension_requested": False,
            "extension_evidence": "",
        }

    extension_requested = validate_extension_evidence(
        customer_context=customer_context,
        extension_requested=llm_result["extension_requested"],
        extension_evidence=llm_result["extension_evidence"],
    )

    verified_extension_evidence = (
        llm_result["extension_evidence"] if extension_requested else ""
    )

    # Select the authoritative action using verified context and policy.
    result = recommend_action(
        late_probability=late_probability,
        invoice_status=invoice_status,
        reminder_count=reminder_count,
        extension_requested=extension_requested,
    )

    llm_result["draft_message"] = ""

    # Keep only context-grounded extension evidence in the public result.
    llm_result["recommended_action"] = result["action"]
    llm_result["extension_requested"] = extension_requested
    llm_result["extension_evidence"] = verified_extension_evidence
    llm_result["allowed"] = result["allowed"]
    llm_result["policy_reason"] = result["policy_reason"]
    llm_result["requires_human_approval"] = result["requires_human_approval"]

    # Preserve the original deterministic action.
    result["late_probability"] = late_probability
    result["risk_level"] = prediction["risk_level"]
    result["customer_context"] = customer_context

    # Expose the draft separately; do not execute it.
    result["llm_recommendation"] = llm_result

    return result
