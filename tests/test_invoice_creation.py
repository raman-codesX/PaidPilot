from unittest.mock import patch, Mock

from app.paypal.invoices import PayPalInvoiceService


@patch("app.paypal.invoices.SessionLocal")
@patch("app.paypal.invoices.httpx.post")
@patch.object(PayPalInvoiceService, "__init__", lambda self: None)
def test_create_invoice_returns_paypal_and_local_invoice_ids(
    mock_post,
    mock_session_local,
):
    service = PayPalInvoiceService()

    service.paypal = Mock()
    service.paypal.get_access_token.return_value = "fake-token"
    service.base_url = "https://api-m.sandbox.paypal.com"

    response = Mock()
    response.is_success = True
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "id": "INV2-TEST-PAYPAL-ID"
    }

    mock_post.return_value = response

    db = mock_session_local.return_value


    def assign_local_id(invoice):
        invoice.id = 123


    db.add.side_effect = assign_local_id

    result = service.create_invoice(
        customer_name="Test Client",
        recipient_email="test@example.com",
        amount="100",
        due_date="2026-11-15",
    )

    assert result["id"] == "INV2-TEST-PAYPAL-ID"
    assert result["local_invoice_id"] is not None