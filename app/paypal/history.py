import json
from pathlib import Path

import httpx

from app.paypal.client import PayPalClient


class PayPalHistoryService:

    def __init__(self):
        self.paypal = PayPalClient()
        self.base_url = self.paypal.base_url

    def list_all_invoices(self):

        token = self.paypal.get_access_token()

        url = f"{self.base_url}/v2/invoicing/invoices"

        all_invoices = []
        page = 1

        while True:

            response = httpx.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                params={
                    "page": page,
                    "page_size": 100,
                    "total_required": "true",
                },
            )

            response.raise_for_status()

            data = response.json()

            invoices = data.get("items", [])

            all_invoices.extend(invoices)

            total_pages = data.get("total_pages", page)

            print(
                f"Fetched page {page}/{total_pages} "
                f"({len(invoices)} invoices)"
            )

            if page >= total_pages:
                break

            page += 1

        return all_invoices

    def clean_invoice(self, invoice):

        detail = invoice.get("detail", {})
        amount = invoice.get("amount", {})
        due_amount = invoice.get("due_amount", {})
        payments = invoice.get("payments", {})
        metadata = detail.get("metadata", {})

        recipient = invoice.get(
            "primary_recipients",
            [{}],
        )

        billing_info = {}

        if recipient:
            billing_info = recipient[0].get(
                "billing_info",
                {},
            )

        return {
            "invoice_id": invoice.get("id"),
            "status": invoice.get("status"),

            "invoice_number": detail.get(
                "invoice_number"
            ),

            "invoice_date": detail.get(
                "invoice_date"
            ),

            "create_time": metadata.get(
                "create_time"
            ),

            "currency": amount.get(
                "currency_code"
            ),

            "amount": amount.get(
                "value"
            ),

            "due_amount": due_amount.get(
                "value"
            ),

            "paid_amount": payments.get(
                "paid_amount",
                {},
            ).get(
                "value"
            ),

            "payment_term": detail.get(
                "payment_term"
            ),

            "recipient_email": billing_info.get(
                "email_address"
            ),
        }

    def save_clean_data(self, invoices):

        clean_invoices = [
            self.clean_invoice(invoice)
            for invoice in invoices
        ]

        output_path = Path("data/invoices.json")

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                clean_invoices,
                file,
                indent=2,
                ensure_ascii=False,
            )

        print(
            f"\nSaved {len(clean_invoices)} "
            f"invoices to {output_path}"
        )

        return clean_invoices


if __name__ == "__main__":

    service = PayPalHistoryService()

    invoices = service.list_all_invoices()

    clean_invoices = service.save_clean_data(
        invoices
    )

    print("\n===== CLEAN INVOICE DATA =====")

    for invoice in clean_invoices:
        print(
            invoice["invoice_id"],
            "|",
            invoice["status"],
            "|",
            invoice["amount"],
            invoice["currency"],
        )

    print("==============================")