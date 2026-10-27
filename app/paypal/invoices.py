import httpx
from datetime import datetime, timezone
from app.paypal.client import PayPalClient
from app.db.models import Invoice
from app.db.session import SessionLocal


class PayPalInvoiceService:

    def __init__(self):
        self.paypal = PayPalClient()
        self.base_url = self.paypal.base_url

    def create_invoice(
        self,
        recipient_email: str,
        amount: str,
        currency: str = "USD",
        description: str = "PaidPilot test invoice",
        due_date: str | None = None,
    ):
        token = self.paypal.get_access_token()

        url = f"{self.base_url}/v2/invoicing/invoices"

        payload = {
            "detail": {
                "invoice_number": f"PAIDPILOT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "currency_code": currency,
                "payment_term": (
                    {
                        "term_type": "DUE_ON_DATE_SPECIFIED",
                        "due_date": due_date,
                    }
                    if due_date
                    else {
                        "term_type": "DUE_ON_RECEIPT"
                    }
                ),

                "note": description,
            },
            "invoicer": {
                "name": {
                    "given_name": "PaidPilot",
                    "surname": "Demo",
                },
                "email_address": "sb-srouy53174164@business.example.com",
            },
            "primary_recipients": [
                {
                    "billing_info": {
                        "email_address": recipient_email
                    }
                }
            ],
            "items": [
                {
                    "name": description,
                    "quantity": "1",
                    "unit_amount": {
                        "currency_code": currency,
                        "value": amount,
                    },
                    "unit_of_measure": "AMOUNT",
                }
            ],
        }

        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
        )

        if not response.is_success:
            print("\n===== PAYPAL ERROR =====")
            print("Status:", response.status_code)
            print("Response:", response.text)
            print("========================\n")

        response.raise_for_status()

        data = response.json()

        invoice_id = None

        if data.get("id"):
            invoice_id = data["id"]

        elif data.get("href"):
            invoice_id = data["href"].rstrip("/").split("/")[-1]

        elif isinstance(data.get("links"), list):
            for link in data["links"]:
                if link.get("rel") == "self":
                    invoice_id = link["href"].rstrip("/").split("/")[-1]
                    break

        if not invoice_id:
            raise RuntimeError(
                f"PayPal created invoice but invoice ID could not be extracted: {data}"
            )

        data["id"] = invoice_id

        db = SessionLocal()

        try:
            invoice = Invoice(
                paypal_invoice_id=invoice_id,
                customer_email=recipient_email,
                amount=float(amount),
                currency=currency,
                status="DRAFT",
                issued_at=datetime.now(timezone.utc),
                due_at=datetime.fromisoformat(due_date) if due_date else None,
            )

            db.add(invoice)
            db.commit()

        finally:
            db.close()

        print("\n===== PAYPAL CREATE RESPONSE =====")
        print(data)
        print("==================================\n")

        return data

    def send_invoice(self, invoice_id: str):
        token = self.paypal.get_access_token()

        url = (
            f"{self.base_url}"
            f"/v2/invoicing/invoices/{invoice_id}/send"
        )

        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        if not response.is_success:
            print("\n===== PAYPAL SEND ERROR =====")
            print("Status:", response.status_code)
            print("Response:", response.text)
            print("=============================\n")

        response.raise_for_status()

        db = SessionLocal()

        try:
            invoice = (
                db.query(Invoice)
                .filter(Invoice.paypal_invoice_id == invoice_id)
                .first()
            )

            if invoice:
                invoice.status = "SENT"
                db.commit()

        finally:
            db.close()

        return response.json() if response.content else None