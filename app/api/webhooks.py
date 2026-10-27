import json
import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.models import Invoice, WebhookEvent
from app.db.session import SessionLocal
from app.paypal.client import PayPalClient


load_dotenv()

router = APIRouter()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/webhooks/paypal")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
):

    # Read the raw request body.
    raw_body = await request.body()

    # Parse JSON.
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return {
            "status": "invalid",
            "message": "Invalid JSON payload",
        }

    # Get PayPal credentials.
    paypal = PayPalClient()
    token = paypal.get_access_token()

    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID")

    # PayPal webhook signature verification payload.
    verification_payload = {
        "transmission_id": request.headers.get(
            "paypal-transmission-id"
        ),
        "transmission_time": request.headers.get(
            "paypal-transmission-time"
        ),
        "cert_url": request.headers.get(
            "paypal-cert-url"
        ),
        "auth_algo": request.headers.get(
            "paypal-auth-algo"
        ),
        "transmission_sig": request.headers.get(
            "paypal-transmission-sig"
        ),
        "webhook_id": webhook_id,
        "webhook_event": payload,
    }

    verification_url = (
        f"{paypal.base_url}"
        "/v1/notifications/verify-webhook-signature"
    )

    verification_response = httpx.post(
        verification_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=verification_payload,
    )

    verification_result = verification_response.json()

    print(
        "\n===== PAYPAL VERIFICATION ====="
    )
    print(
        "Verification:",
        verification_result,
    )
    print(
        "================================\n"
    )

    if (
        verification_result.get("verification_status")
        != "SUCCESS"
    ):
        return {
            "status": "rejected",
            "message": "Invalid PayPal webhook signature",
        }

    print(
        "\n===== PAYPAL WEBHOOK VERIFIED ====="
    )
    print(
        "Event:",
        payload.get("event_type"),
    )
    print(
        "Event ID:",
        payload.get("id"),
    )

    print(
        "Webhook resource:",
        payload.get("resource"),
    )
    print(
        "===================================\n"
    )

    paypal_event_id = payload.get("id")
    event_type = payload.get("event_type")

    if not paypal_event_id or not event_type:
        return {
            "status": "invalid",
            "message": "Missing PayPal event id or event type",
        }

    # Prevent duplicate webhook processing.
    existing_event = (
        db.query(WebhookEvent)
        .filter(
            WebhookEvent.paypal_event_id
            == paypal_event_id
        )
        .first()
    )

    if existing_event:
        return {
            "status": "duplicate",
            "message": "Webhook event already processed",
        }

    # Save webhook event.
    event = WebhookEvent(
        paypal_event_id=paypal_event_id,
        event_type=event_type,
        payload=json.dumps(payload),
    )

    db.add(event)

    # Process paid invoice.
    if event_type == "INVOICING.INVOICE.PAID":

        resource = payload.get(
            "resource",
            {},
        )

        paypal_invoice_id = (
            resource
            .get("invoice", {})
            .get("id")
        )

        print(
            "PayPal Invoice ID:",
            paypal_invoice_id,
        )

        if paypal_invoice_id:

            invoice = (
                db.query(Invoice)
                .filter(
                    Invoice.paypal_invoice_id
                    == paypal_invoice_id
                )
                .first()
            )

            if invoice:

                invoice.status = "PAID"

                invoice.paid_at = (
                    datetime.now(timezone.utc)
                )

                print(
                    "Invoice updated to PAID:",
                    paypal_invoice_id,
                )

            else:

                print(
                    "Invoice not found in database:",
                    paypal_invoice_id,
                )

    db.commit()

    db.refresh(event)

    return {
        "status": "received",
        "event_id": paypal_event_id,
        "event_type": event_type,
    }