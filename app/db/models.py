from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.session import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    paypal_event_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    event_type = Column(
        String,
        nullable=False,
    )

    payload = Column(
        Text,
        nullable=False,
    )

    processed_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    paypal_invoice_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    customer_name = Column(
        String,
        nullable=True,
    )

    customer_email = Column(
        String,
        nullable=True,
        index=True,
    )

    amount = Column(
        Float,
        nullable=False,
    )

    currency = Column(
        String,
        nullable=False,
    )

    status = Column(
        String,
        nullable=False,
        default="SENT",
    )

    issued_at = Column(
        DateTime,
        nullable=True,
    )

    due_at = Column(
        DateTime,
        nullable=True,
    )

    paid_at = Column(
        DateTime,
        nullable=True,
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(String, unique=True, nullable=False, index=True)
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )
    action = Column(String, nullable=False)
    late_probability = Column(Float, nullable=False)
    draft_message = Column(Text, nullable=False)
    decision = Column(String, nullable=False)
    decided_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class ActionHistory(Base):
    __tablename__ = "action_history"

    id = Column(Integer, primary_key=True, index=True)

    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
        index=True,
    )

    customer_email = Column(
        String,
        nullable=True,
    )

    action = Column(
        String,
        nullable=False,
    )

    subject = Column(
        String,
        nullable=False,
    )

    body = Column(
        Text,
        nullable=False,
    )

    status = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )