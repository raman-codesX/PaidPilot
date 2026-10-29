import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def generate_ai_email(
    invoice_id: int,
    invoice_amount: float,
    currency: str,
    invoice_status: str,
    due_date: str | None,
    days_overdue: int,
    action: str,
    customer_name: str | None = None,
    customer_email: str | None = None,
) -> dict:
    """Generate a personalized customer-facing invoice email using Gemini."""

    allowed_actions = {
        "DO_NOTHING",
        "FRIENDLY_REMINDER",
        "FIRM_REMINDER",
        "PAYMENT_PLAN",
    }

    if action not in allowed_actions:
        raise ValueError("Unknown email action.")

    if action == "DO_NOTHING":
        raise ValueError("Cannot generate an email for DO_NOTHING.")

    customer_name_text = customer_name or "Customer"
    customer_email_text = customer_email or "not provided"

    prompt = f"""
You are an AI assistant helping a business owner write a professional
invoice follow-up email.

The business owner's deterministic policy has already selected this action:
{action}

The action is FINAL. Do not change or reinterpret it.

Invoice information:
- Invoice ID: {invoice_id}
- Amount: {invoice_amount} {currency}
- Status: {invoice_status}
- Due date: {due_date or "not provided"}
- Days overdue: {days_overdue}

Customer information:
- Customer name: {customer_name_text}
- Customer email: {customer_email_text}

Rules:
1. Write a concise, professional, natural email.
2. Personalize the email using the customer information when available.
3. Clearly acknowledge that the invoice is overdue when days overdue is greater than 0.
4. For FRIENDLY_REMINDER, use a polite and non-aggressive tone.
5. For FIRM_REMINDER, be clear and professional about requesting payment.
6. For PAYMENT_PLAN, politely discuss arranging a payment schedule.
7. Never invent payment dates, deadlines, penalties, fees, discounts, or promises.
8. Do not mention late-payment probability or internal risk scores.
9. Do not claim that an email was already sent.
10. Do not change the selected action.
11. Return only valid JSON.

Return exactly:
{{
    "subject": "email subject",
    "draft_message": "complete email body",
    "reason": "brief explanation of why this email fits the selected action"
}}
"""

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config={
            "max_output_tokens": 1000,
            "response_mime_type": "application/json",
        },
    )

    recommendation = json.loads(response.text)

    if not isinstance(recommendation, dict):
        raise ValueError("LLM response must be a JSON object.")

    required_keys = {
        "subject",
        "draft_message",
        "reason",
    }

    if not required_keys.issubset(recommendation):
        raise ValueError("LLM response is missing required fields.")

    if not all(
        isinstance(recommendation[key], str)
        for key in required_keys
    ):
        raise ValueError("LLM text fields must be strings.")

    return recommendation