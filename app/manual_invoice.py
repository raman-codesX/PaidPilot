from app.paypal.invoices import PayPalInvoiceService


service = PayPalInvoiceService()

invoice = service.create_invoice(
    recipient_email="sb-grmbh53192750@personal.example.com",
    amount="100.00",
    currency="USD",
    description="PaidPilot test invoice",
)

print("Invoice created!")

invoice_id = invoice.get("id")

print("Invoice ID:", invoice_id)

if not invoice_id:
    raise RuntimeError(
        "PayPal created the invoice but no invoice ID was returned."
    )

service.send_invoice(invoice_id)

print("Invoice sent successfully!")