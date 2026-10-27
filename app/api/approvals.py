from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ApprovalDecision, Invoice
from app.db.session import SessionLocal


router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ApprovalDecisionRequest(BaseModel):
    recommendation_id: str = Field(min_length=1)
    invoice_id: int
    action: Literal["FRIENDLY_REMINDER", "FIRM_REMINDER", "PAYMENT_PLAN"]
    late_probability: float = Field(ge=0, le=1)
    draft_message: str = Field(min_length=1, max_length=5000)
    decision: Literal["APPROVED", "REJECTED"]


@router.post("")
def save_approval_decision(
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == request.invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if (invoice.status or "").upper() in {"PAID", "VOID", "CANCELLED"}:
        raise HTTPException(
            status_code=409,
            detail="Closed invoices cannot receive a collection decision.",
        )

    duplicate = (
        db.query(ApprovalDecision)
        .filter(ApprovalDecision.recommendation_id == request.recommendation_id)
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A decision is already saved for this recommendation.",
        )

    decision = ApprovalDecision(
        recommendation_id=request.recommendation_id,
        invoice_id=request.invoice_id,
        action=request.action,
        late_probability=request.late_probability,
        draft_message=request.draft_message,
        decision=request.decision,
    )
    db.add(decision)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A decision is already saved for this recommendation.",
        ) from None
    db.refresh(decision)

    return {
        "id": decision.id,
        "recommendation_id": decision.recommendation_id,
        "invoice_id": decision.invoice_id,
        "action": decision.action,
        "late_probability": decision.late_probability,
        "draft_message": decision.draft_message,
        "decision": decision.decision,
        "decided_at": decision.decided_at,
        "sent": False,
    }


@router.get("")
def list_approval_decisions(db: Session = Depends(get_db)):
    rows = (
        db.query(ApprovalDecision, Invoice)
        .join(Invoice, Invoice.id == ApprovalDecision.invoice_id)
        .order_by(ApprovalDecision.decided_at.desc())
        .all()
    )

    return {
        "source": "local_database",
        "count": len(rows),
        "decisions": [
            {
                "id": decision.id,
                "recommendation_id": decision.recommendation_id,
                "invoice_id": decision.invoice_id,
                "paypal_invoice_id": invoice.paypal_invoice_id,
                "customer_email": invoice.customer_email,
                "action": decision.action,
                "late_probability": decision.late_probability,
                "draft_message": decision.draft_message,
                "decision": decision.decision,
                "decided_at": decision.decided_at,
                "sent": False,
            }
            for decision, invoice in rows
        ],
    }
