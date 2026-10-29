from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Invoice, ActionHistory
from app.db.session import SessionLocal
from app.paypal.invoices import PayPalInvoiceService

router = APIRouter(prefix="/api", tags=["Dashboard"])

class CreateInvoiceRequest(BaseModel):
    customer_name: str
    recipient_email: str
    amount: str
    description: str = "PaidPilot test invoice"
    due_date: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()

    paid_statuses = {"PAID"}
    closed_statuses = {"PAID", "VOID", "CANCELLED"}

    outstanding_by_currency = defaultdict(float)

    for invoice in invoices:
        status = (invoice.status or "").upper()

        if status not in closed_statuses:
            outstanding_by_currency[invoice.currency] += (
                invoice.amount or 0
            )

    return {
        "source": "local_database",
        "total_invoices": len(invoices),
        "paid_invoices": sum(
            1 for invoice in invoices
            if (invoice.status or "").upper() in paid_statuses
        ),
        "outstanding_invoices": sum(
            1 for invoice in invoices
            if (invoice.status or "").upper() not in closed_statuses
        ),
        "overdue_invoices": sum(
            1 for invoice in invoices
            if invoice.due_at is not None
            and invoice.due_at < __import__("datetime").datetime.now()
            and (invoice.status or "").upper() not in closed_statuses
        ),
        "outstanding_by_currency": {
            currency: round(amount, 2)
            for currency, amount in outstanding_by_currency.items()
        },
    }


@router.get("/invoices")
def list_invoices(db: Session = Depends(get_db)):
    invoices = (
        db.query(Invoice)
        .order_by(Invoice.id.desc())
        .all()
    )

    return {
        "source": "local_database",
        "count": len(invoices),
        "invoices": [
            {
                "id": invoice.id,
                "paypal_invoice_id": invoice.paypal_invoice_id,
                "customer_email": invoice.customer_email,
                "amount": invoice.amount,
                "currency": invoice.currency,
                "status": invoice.status,
                "issued_at": invoice.issued_at,
                "due_at": invoice.due_at,
                "paid_at": invoice.paid_at,
            }
            for invoice in invoices
        ],
    }

@router.get("/clients")
def list_clients(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()

    clients = {}

    for invoice in invoices:
        email = invoice.customer_email

        if not email:
            continue

        if email not in clients:
            clients[email] = {
                "customer_email": email,
                "total_invoices": 0,
                "paid_invoices": 0,
                "outstanding_invoices": 0,
                "outstanding_amount": 0.0,
            }

        client = clients[email]
        client["total_invoices"] += 1

        status = (invoice.status or "").upper()

        if status == "PAID":
            client["paid_invoices"] += 1
        elif status not in {"VOID", "CANCELLED"}:
            client["outstanding_invoices"] += 1
            client["outstanding_amount"] += invoice.amount or 0

    return {
        "source": "local_database",
        "count": len(clients),
        "clients": list(clients.values()),
    }

@router.post("/invoices/create")
def create_invoice(request: CreateInvoiceRequest):
    service = PayPalInvoiceService()

    try:
        return service.create_invoice(
            customer_name=request.customer_name,
            recipient_email=request.recipient_email,
            amount=request.amount,
            description=request.description,
            due_date=request.due_date,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.post("/invoices/{invoice_id}/send")
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
):
    invoice = (
        db.query(Invoice)
        .filter(Invoice.id ==invoice_id)
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )
    service = PayPalInvoiceService()
    return service.send_invoice(invoice.paypal_invoice_id)

@router.get("/review-history")
def review_history(db: Session = Depends(get_db)):
    history = (
        db.query(ActionHistory)
        .order_by(ActionHistory.created_at.desc())
        .all()
    )

    return {
        "source": "local_database",
        "count": len(history),
        "history": [
            {
                "id": item.id,
                "invoice_id": item.invoice_id,
                "customer_email": item.customer_email,
                "action": item.action,
                "subject": item.subject,
                "body": item.body,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in history
        ],
    }