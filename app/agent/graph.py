
from app.agent.policy import evaluate_action
from app.ml.predict import predict_late_payment


def recommend_action(
    late_probability: float,
    invoice_status: str,
    reminder_count: int,
):
    """Recommend an action using deterministic risk bands and invoice status."""

    no_contact_statuses = {"PAID", "VOID", "CANCELLED"}

    if invoice_status in no_contact_statuses:
        action = "DO_NOTHING"
        recommendation_reason = (
            f"Invoice status is {invoice_status}; "
            "no collection action is needed."
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

    # Select the action using the model score and deterministic policy only.
    result = recommend_action(
        late_probability=late_probability,
        invoice_status=invoice_status,
        reminder_count=reminder_count,
    )

    # Preserve the original deterministic action.
    result["late_probability"] = late_probability
    result["risk_level"] = prediction["risk_level"]

    return result
