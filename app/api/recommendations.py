
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import Invoice, ActionHistory 
from app.db.session import SessionLocal
from app.agent.graph import recommend_action_from_invoice
from app.agent.llm import generate_collection_recommendation
from app.agent.email_templates import build_email
from app.gmail.client import send_email

router = APIRouter(
    prefix="/api/recommendations",
    tags=["AI Recommendations"],
)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _history_for_invoice(invoice: Invoice, invoices: list[Invoice]) -> dict:
    email = (invoice.customer_email or "").strip().casefold()
    issued_at = _as_utc(invoice.issued_at)
    observed = []

    if email and issued_at:
        for prior in invoices:
            if prior.id == invoice.id:
                continue
            if (prior.customer_email or "").strip().casefold() != email:
                continue
            if (prior.status or "").upper() != "PAID":
                continue

            prior_issued_at = _as_utc(prior.issued_at)
            due_at = _as_utc(prior.due_at)
            paid_at = _as_utc(prior.paid_at)
            if not prior_issued_at or not due_at or not paid_at:
                continue
            if prior_issued_at < issued_at:
                observed.append((due_at, paid_at))

    late_delays = [
        (paid_at - due_at).total_seconds() / 86400
        for due_at, paid_at in observed
        if paid_at > due_at
    ]
    previous_count = len(observed)
    late_count = len(late_delays)

    return {
        "previous_invoices": previous_count,
        "previous_late_payments": late_count,
        "previous_late_rate": (
            late_count / previous_count if previous_count else 0.0
        ),
        "avg_previous_delay": (
            sum(late_delays) / late_count if late_count else 0.0
        ),
        "limited_history": previous_count == 0,
    }


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RecommendationRequest(BaseModel):
    invoice_id: int
    query: str = (
        "Assess payment risk and recommend an appropriate collection action."
    )

class EmailGenerationRequest(BaseModel):
    invoice_id: int
    action: str

class SendEmailRequest(BaseModel):
    invoice_id: int
    to: str
    subject: str
    body: str
    action: str

@router.post("")
def generate_recommendation(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == request.invoice_id
    ).first()

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    try:
        history = _history_for_invoice(invoice, db.query(Invoice).all())

        result = recommend_action_from_invoice(
            invoice_amount=invoice.amount,
            previous_invoices=history["previous_invoices"],
            previous_late_payments=history["previous_late_payments"],
            previous_late_rate=history["previous_late_rate"],
            avg_previous_delay=history["avg_previous_delay"],
            invoice_status=invoice.status.upper(),
            reminder_count=0,
            customer_id=None,
            customer_email=invoice.customer_email,
            query=request.query,
            invoice_reference=invoice.paypal_invoice_id,
            currency=invoice.currency,
            due_at=invoice.due_at,
        )

        return {
            "invoice_id": invoice.id,
            "paypal_invoice_id": invoice.paypal_invoice_id,
            "customer_email": invoice.customer_email,
            "amount": invoice.amount,
            "currency": invoice.currency,
            **result,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation generation failed: {error}",
        ) from error


@router.post("/email")
def generate_email(
    request: EmailGenerationRequest,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == request.invoice_id
    ).first()

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found",
        )

    try:
        history = _history_for_invoice(
            invoice,
            db.query(Invoice).all(),
        )

        # Reuse the same RAG context used by the recommendation agent.
        from app.rag.hybrid_retriever import retrieve_hybrid_context

        customer_context = retrieve_hybrid_context(
            customer_id=None,
            query=(
                "Review verified customer notes for payment timing, "
                "payment issues, or extension requests."
            ),
            customer_email=invoice.customer_email,
        )

        late_probability = 0.0

        # The recommendation endpoint already calculated the action,
        # but the email endpoint needs the risk probability again.
        from app.ml.predict import predict_late_payment

        prediction = predict_late_payment(
            invoice_amount=invoice.amount,
            previous_invoices=history["previous_invoices"],
            previous_late_payments=history["previous_late_payments"],
            previous_late_rate=history["previous_late_rate"],
            avg_previous_delay=history["avg_previous_delay"],
        )

        late_probability = prediction["late_probability"]

        is_overdue = bool(
            invoice.due_at and datetime.now() > invoice.due_at
        )

        email = build_email(
            action=request.action,
            invoice_id=invoice.id,
            amount=invoice.amount,
            currency=invoice.currency,
            client_name="Customer",
            due_date=(
                invoice.due_at.strftime("%Y-%m-%d")
                if invoice.due_at
                else "the due date"
            ),
            days_overdue=(
                max((datetime.now() - invoice.due_at).days, 0)
                if invoice.due_at
                else 0
            ),
            is_overdue=is_overdue,
            sender_name="PaidPilot",
        )

        return {
            "invoice_id": invoice.id,
            "recommendation_action": request.action,
            "customer_email": invoice.customer_email,
            "draft_message": email["body"],
            "subject": email["subject"],
            "reason": "",
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Email generation failed: {error}",
        ) from error

@router.post("/send-email")
def send_approved_email(
    request: SendEmailRequest,
    db: Session = Depends(get_db),
):
    try:
        send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
        )

        history = ActionHistory(
            invoice_id=request.invoice_id,
            customer_email=request.to,
            action=request.action,
            subject=request.subject,
            body=request.body,
            status="SENT",
        )

        db.add(history)
        db.commit()

        return {
            "sent": True,
            "to": request.to,
            "invoice_id": request.invoice_id,
        }

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Email sending failed: {error}",
        ) from error

@router.post("/portfolio")
def generate_portfolio_recommendations(
    db: Session = Depends(get_db),
):
    invoices = db.query(Invoice).order_by(Invoice.due_at.asc(), Invoice.id.asc()).all()
    open_invoices = [
        invoice for invoice in invoices
        if (invoice.status or "").upper() not in {"PAID", "VOID", "CANCELLED"}
    ]
    now = datetime.now(timezone.utc)
    recommendations = []

    for invoice in open_invoices:
        history = _history_for_invoice(invoice, invoices)

        due_at = _as_utc(invoice.due_at)
        overdue_days = (
            max(0, (now - due_at).days)
            if due_at is not None
            else 0
        )

        if history["previous_invoices"] == 0 and overdue_days == 0:
            continue
        item = {
            "recommendation_id": str(uuid4()),
            "invoice_id": invoice.id,
            "paypal_invoice_id": invoice.paypal_invoice_id,
            "customer_email": invoice.customer_email,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "issued_at": invoice.issued_at,
            "due_at": invoice.due_at,
            "overdue_days": overdue_days,
            **history,
        }

        try:
            result = recommend_action_from_invoice(
                invoice_amount=invoice.amount,
                previous_invoices=history["previous_invoices"],
                previous_late_payments=history["previous_late_payments"],
                previous_late_rate=history["previous_late_rate"],
                avg_previous_delay=history["avg_previous_delay"],
                invoice_status=(invoice.status or "").upper(),
                reminder_count=0,
                customer_id=None,
                customer_email=invoice.customer_email,
                invoice_reference=invoice.paypal_invoice_id,
                currency=invoice.currency,
                due_at=invoice.due_at,
                query=(
                    "Review verified customer notes for payment timing or an "
                    "extension request. Recommend an appropriate collection "
                    "draft consistent with the deterministic risk policy."
                ),
            )
            item.update(result)
        except Exception as error:
            item["recommendation_error"] = str(error)

        recommendations.append(item)

    return {
        "source": "local_database",
        "count": len(recommendations),
        "recommendations": recommendations,
    }
