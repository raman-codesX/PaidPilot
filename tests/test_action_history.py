from app.db.models import ActionHistory


def test_action_history_model():
    history = ActionHistory(
        invoice_id=1,
        customer_email="customer@example.com",
        action="FRIENDLY_REMINDER",
        subject="Payment reminder",
        body="Please arrange payment.",
        status="SENT",
    )

    assert history.invoice_id == 1
    assert history.customer_email == "customer@example.com"
    assert history.action == "FRIENDLY_REMINDER"
    assert history.status == "SENT"