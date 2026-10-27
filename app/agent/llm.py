import json
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

def generate_collection_recommendation(
    late_probability: float,
    invoice_status: str,
    customer_context: list[dict],
    draft_action: str,
    invoice_reference: str | None = None,
    invoice_amount: float | None = None,
    currency: str | None = None,
    due_date: str | None = None,
    verified_extension: bool | None = None,
    extension_evidence: str = "",
) -> dict:
    """Ask the local LLM to classify context and draft for a selected action."""

    allowed_actions = {
        "DO_NOTHING",
        "FRIENDLY_REMINDER",
        "FIRM_REMINDER",
        "PAYMENT_PLAN",
    }
    if draft_action not in allowed_actions:
        raise ValueError("Unknown draft action.")

    amount_text = (
        str(invoice_amount) if invoice_amount is not None else "not provided"
    )

    context_text = json.dumps(
        customer_context,
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
You are an AI assistant helping a business owner communicate with customers about invoices.

The deterministic policy has already selected the action:
{draft_action}

The action is FINAL. You must NOT change, reinterpret, or recommend a different action.

Action rules:
- FRIENDLY_REMINDER: politely remind the customer about the invoice and request payment.
- FIRM_REMINDER: clearly and professionally request payment for an overdue invoice.
- PAYMENT_PLAN: politely discuss arranging a payment schedule. If verified customer context contains a specific requested schedule, use it. Otherwise, ask what payment schedule would work for the customer.
- DO_NOTHING: do not create a customer-facing message.

Invoice information:
- Invoice reference: {invoice_reference}
- Amount: {invoice_amount} {currency}
- Invoice status: {invoice_status}
- Due date: {due_date}

Verified customer context:
{customer_context}

Important rules:
1. Write ONLY the email body.
2. Do NOT include a greeting.
3. Do NOT include a sign-off.
4. Do NOT include a customer name or company name.
5. Do NOT use placeholders such as [Customer Name], [Your Name], or [Company Name].
6. The application will add the greeting and sign-off separately.
7. Write 2–4 natural, professional sentences.
8. Keep the message concise, around 40–70 words.
9. For PAYMENT_PLAN, ask about a suitable payment schedule unless verified customer context provides specific payment-plan terms.
10. Never invent payment dates, deadlines, penalties, fees, payment-plan terms, approvals, or promises.
11. Do not mention the late-payment probability.
12. Use only the verified customer context provided above.
13. Do not claim that an email was sent or that any action was completed.
14. If the invoice is overdue, clearly acknowledge that it is overdue.
15. Do not describe the action itself as an invoice status. For example, do not say the invoice is "in PAYMENT_PLAN status".
16. Return ONLY valid JSON.

Return exactly this JSON structure:
{{
  "reason": "brief explanation of why this message fits the selected action",
  "draft_message": "email body only",
  "extension_requested": false,
  "extension_evidence": ""
}}
"""

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config={
        "max_output_tokens": 200,
        },
    )

    text = response.text
    recommendation = json.loads(text)

    required_keys = {
        "reason",
        "draft_message",
        "extension_requested",
        "extension_evidence",
    }

    if not isinstance(recommendation, dict):
        raise ValueError("LLM response must be a JSON object.")

    if not required_keys.issubset(recommendation):
        raise ValueError("LLM response is missing required fields.")

    if not all(
        isinstance(recommendation[key], str)
        for key in {
            "reason",
            "draft_message",
            "extension_evidence",
        }
    ):
        raise ValueError("LLM text fields must be strings.")

    if isinstance(recommendation["extension_requested"], str):
        value = recommendation["extension_requested"].strip().lower()

        if value == "true":
            recommendation["extension_requested"] = True
        elif value == "false":
            recommendation["extension_requested"] = False
        else:
            raise ValueError("extension_requested must be a boolean.")

    if not isinstance(recommendation["extension_requested"], bool):
        raise ValueError("extension_requested must be a boolean.")
    
    if verified_extension is not None:
        recommendation["extension_requested"] = verified_extension
        recommendation["extension_evidence"] = (
            extension_evidence if verified_extension else ""
        )

    return recommendation
