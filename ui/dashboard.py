import html
import os

import requests
import streamlit as st
from datetime import datetime, timedelta, timezone

API_URL = os.getenv("PAIDPILOT_API_URL", "http://127.0.0.1:8000").rstrip("/")
PAGES = ["Overview", "Recommendations", "Invoices", "Clients", "Review history"]
NO_CONTACT_STATUSES = {"PAID", "VOID", "CANCELLED"}

st.set_page_config(
    page_title="PaidPilot | Collections",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --pp-ink:#15352d; --pp-muted:#71817a; --pp-line:#dfe8e3;
            --pp-teal:#087e61; --pp-mint:#e5f5ee; --pp-warm:#fff3df;
            --pp-danger:#a8473f; }
    .stApp { background:#f5f8f6; color:var(--pp-ink); }
    [data-testid="stSidebar"] { background:#17332d; }
    [data-testid="stSidebar"] * { color:#e8f2ed; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { color:#d5e2dc; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#adc0b7; }
    [data-testid="stSidebar"] button { border-radius:9px; }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--pp-line);
       padding:16px 18px; border-radius:13px; box-shadow:0 2px 8px rgba(27,57,46,.035); }
    [data-testid="stMetricLabel"] { color:var(--pp-muted); }
    [data-testid="stMetricValue"] { color:var(--pp-ink); }
    h1,h2,h3 { color:var(--pp-ink); letter-spacing:-.025em; }
    h1 { font-size:1.9rem; font-weight:600; }
    h2 { font-size:1.25rem; font-weight:600; }
    h3 { font-size:1.03rem; font-weight:600; }
    .pp-muted { color:var(--pp-muted); font-size:.9rem; }
    .pp-kicker { color:var(--pp-teal); font-size:.75rem; font-weight:700;
                 letter-spacing:.08em; text-transform:uppercase; }
    .pp-card { background:#fff; border:1px solid var(--pp-line); border-radius:13px;
               padding:17px 19px; margin:0 0 12px; }
    .pp-card-head { display:flex; justify-content:space-between; align-items:flex-start;
                    gap:14px; flex-wrap:wrap; }
    .pp-client { font-size:1.05rem; font-weight:650; color:var(--pp-ink); }
    .pp-ref { color:var(--pp-muted); font-size:.8rem; margin-top:3px; }
    .pp-facts { display:flex; gap:8px 18px; flex-wrap:wrap; margin-top:13px;
                color:var(--pp-muted); font-size:.82rem; }
    .pp-facts strong { color:var(--pp-ink); font-weight:600; }
    .pp-badge { display:inline-block; padding:4px 9px; border-radius:99px;
                font-size:.75rem; font-weight:650; white-space:nowrap; }
    .pp-high { color:#a8473f; background:#fff0ed; }
    .pp-medium { color:#98610f; background:#fff3df; }
    .pp-low { color:#087e61; background:#e5f5ee; }
    .pp-action { color:var(--pp-teal); font-weight:650; }
    .pp-message { border-left:3px solid #8ed6b9; background:#f4faf6; color:#29483c;
                  padding:12px 14px; margin-top:14px; border-radius:0 9px 9px 0;
                  white-space:pre-wrap; line-height:1.55; }
    .pp-callout { background:#edf5f1; color:#496359; border-radius:10px; padding:12px 14px;
                  font-size:.85rem; }
    .pp-callout strong { color:var(--pp-ink); }
    .pp-approval { color:#087e61; font-size:.82rem; font-weight:600; }
    .pp-rejected { color:#a8473f; font-size:.82rem; font-weight:600; }
    div.stButton > button { border-radius:9px; font-weight:600; }
    div.stButton > button[kind="primary"] { background:#087e61; border-color:#087e61; }
    @media (max-width: 760px) {
      [data-testid="stMetric"] { padding:12px; }
      .pp-card { padding:14px; }
    }

    .pp-summary-card {
        background:#fff;
        border:1px solid var(--pp-line);
        border-radius:13px;
        padding:20px 21px;
        min-height:92px;
        margin-bottom:14px;
    }

    .pp-summary-label {
        color:var(--pp-muted);
        font-size:.85rem;
        margin-bottom:7px;
    }

    .pp-summary-value {
        color:var(--pp-ink);
        font-size:1.65rem;
        font-weight:700;
    }

    .pp-danger-text {
        color:#a8473f;
    }

    .pp-warm-text {
        color:#98610f;
    }

    .pp-approval-card {
        background:#fff;
        border:1px solid var(--pp-line);
        border-radius:13px;
        padding:18px 21px;
        margin-bottom:28px;
    }

    .pp-approval-number {
        color:var(--pp-teal);
        font-size:1.65rem;
        font-weight:700;
    }

    .pp-table-client {
        display:flex;
        flex-direction:column;
        gap:2px;
        padding:8px 0;
    }

    .pp-table-client strong {
        color:var(--pp-ink);
    }

    .pp-table-client span {
        color:var(--pp-muted);
        font-size:.78rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


def api_request(method, endpoint, payload=None, timeout=30):
    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json(), None
    except requests.HTTPError as error:
        try:
            detail = error.response.json().get("detail", error.response.text)
        except (ValueError, AttributeError):
            detail = str(error)
        return None, f"API error: {detail}"
    except requests.RequestException as error:
        return None, f"Could not connect to PaidPilot API at {API_URL}: {error}"


def get_data(key, endpoint):
    data_key = f"{key}_data"
    error_key = f"{key}_error"
    if data_key not in st.session_state:
        data, error = api_request("GET", endpoint)
        st.session_state[data_key] = data
        st.session_state[error_key] = error
    return st.session_state[data_key], st.session_state[error_key]


def get_recommendations(force=False):
    if force:
        st.session_state.pop("recommendations_data", None)
        st.session_state.pop("recommendations_error", None)
    if "recommendations_data" not in st.session_state:
        with st.spinner("Reviewing invoice history and preparing recommendations…"):
            data, error = api_request(
                "POST", "/api/recommendations/portfolio", timeout=900
            )
        st.session_state["recommendations_data"] = data
        print("DEBUG: recommendations_data received")
        st.session_state["recommendations_error"] = error
    return (
        st.session_state.get("recommendations_data"),
        st.session_state.get("recommendations_error"),
    )


def format_amount(amount, currency):
    try:
        formatted = f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        formatted = "—"
    return f"{formatted} {currency or ''}".strip()


def format_date(value):
    if not value:
        return "No date"

    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))

    return dt.strftime("%Y-%m-%d %H:%M")


def risk_class(level):
    return {
        "HIGH": "pp-high",
        "MEDIUM": "pp-medium",
        "LOW": "pp-low",
    }.get(str(level or "").upper(), "pp-medium")


def recommendation_label(action):
    return {
        "DO_NOTHING": "No action",
        "FRIENDLY_REMINDER": "Friendly reminder",
        "FIRM_REMINDER": "Firm reminder",
        "PAYMENT_PLAN": "Payment plan",
    }.get(action, str(action or "Recommendation"))


def render_recommendation_card(item, decisions_by_id):
    invoice_id = item.get("invoice_id")
    email = item.get("customer_email") or "Customer email unavailable"
    paypal_id = item.get("paypal_invoice_id") or f"Invoice {invoice_id}"
    amount = format_amount(item.get("amount"), item.get("currency"))
    action = item.get("action", "DO_NOTHING")

    recommendation_id = item.get(
        "recommendation_id",
        f"invoice-{invoice_id}",
    )

    payload = {
        "invoice_id": invoice_id,
        "action": action,
    }

    risk = float(item.get("late_probability") or 0)
    level = item.get("risk_level", "UNKNOWN")

    st.subheader(f"Invoice {invoice_id}")

    st.markdown(
        '<div class="pp-kicker">Review reminder</div>',
        unsafe_allow_html=True,
    )

    st.title("Review message")

    llm = item.get("llm_recommendation") or {}
    draft = str(llm.get("draft_message") or "").strip()
    subject = str(llm.get("subject") or "").strip()

    left, right = st.columns(2)

    with left:
        st.markdown(f"**{email}**")
        st.caption(f"To: {email}")

    with right:
        st.markdown(f"**Invoice #{invoice_id}**")
        st.caption(paypal_id)

    st.markdown("### Email")

    if draft:
        if subject:
            st.markdown(f"**Subject:** {subject}")

        st.markdown(
            """
            <style>
            textarea {
                color: #FFFFFF !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.text_area(
            "Message",
            value=draft,
            key=f"message-{recommendation_id}",
            height=220,
        )

        edit_col, send_col = st.columns(2)

        if edit_col.button(
            "Edit Message",
            key=f"edit-{recommendation_id}",
        ):
            st.session_state[f"editing-{recommendation_id}"] = True

        if send_col.button(
            "Send Message",
            type="primary",
            key=f"send-{recommendation_id}",
        ):
            edited_message = st.session_state.get(
                f"message-{recommendation_id}",
                draft,
            )

            send_response, send_error = api_request(
                "POST",
                "/api/recommendations/send-email",
                payload={
                    "invoice_id": item["invoice_id"],
                    "to": item["customer_email"],
                    "subject": subject,
                    "body": edited_message,
                    "action": item["action"],
                },
                timeout=30,
            )

            if send_error:
                st.error(f"Email sending failed: {send_error}")
            else:
                st.success("Message sent successfully.")

    else:
        if st.button(
            "Generate Email",
            type="primary",
            key=f"generate-email-{recommendation_id}",
        ):
            email_data, email_error = api_request(
                "POST",
                "/api/recommendations/email",
                payload=payload,
                timeout=30,
            )

            if email_error:
                st.error(f"Email generation failed: {email_error}")
            else:
                item["llm_recommendation"] = {
                    "draft_message": email_data.get(
                        "draft_message",
                        "",
                    ),
                    "subject": email_data.get(
                        "subject",
                        "",
                    ),
                    "reason": email_data.get(
                        "reason",
                        "",
                    ),
                }

                st.rerun()
    
    payload = {
        "recommendation_id": recommendation_id,
        "invoice_id": invoice_id,
        "action": action,
        "late_probability": risk,
        "draft_message": draft,
    }


    st.markdown("### Why this tone?")
    st.caption(
        f"PaidPilot selected **{recommendation_label(action)}** because "
        f"the predicted late-payment risk is **{risk:.0%} ({level})**."
    )

    st.markdown("### Client history")

    history = item.get("previous_invoices", 0)
    late = item.get("previous_late_payments", 0)

    st.write(
        f"**{history}** previous invoice(s) · "
        f"**{late}** late payment(s)"
    )

    if item.get("recommendation_error"):
        st.error(
            f"Could not generate this recommendation: "
            f"{item['recommendation_error']}"
        )
        return


    if action == "DO_NOTHING":
        st.info("No collection action is recommended.")
        return

    if not item.get("allowed"):
        st.warning(
            item.get(
                "policy_reason",
                "This action is not allowed by policy.",
            )
        )
        return

    with st.expander("Risk, history, and customer context"):
        st.markdown("### Payment history")

        history = item.get("previous_invoices", 0)
        late = item.get("previous_late_payments", 0)

        st.write(
            f"**{history}** completed invoice(s) · "
            f"**{late}** late payment(s)"
        )

        st.markdown("### Customer context")

        contexts = item.get("customer_context") or []

        if contexts:
            for context in contexts:
                st.caption(
                    f"{context.get('type', 'Context')}: "
                    f"{context.get('text', '')}"
                )
        else:
            st.info(
                "No verified customer context was matched to this invoice."
            )

        st.markdown("### Policy")

        st.caption(
            item.get(
                "policy_reason",
                "No policy details available.",
            )
        )


def save_decision(payload, decision):
    _, error = api_request(
        "POST", "/api/approvals", {**payload, "decision": decision}
    )
    if error:
        st.error(error)
        return
    st.session_state["approval_notice"] = (
        "Approval saved. The draft remains unsent."
        if decision == "APPROVED"
        else "Rejection saved. No message was sent."
    )
    st.session_state.pop("approvals_data", None)
    st.rerun()


def recommendation_decisions():
    print("DEBUG: loading approvals")
    approvals, error = get_data("approvals", "/api/approvals")
    print("DEBUG: approvals loaded")
    if error or not approvals:
        return {}, error
    return {
        item.get("recommendation_id"): item.get("decision")
        for item in approvals.get("decisions", [])
    }, None


def render_overview(summary, summary_error, recommendations, recommendation_error):
    if summary_error:
        st.error(summary_error)
        return

    if not summary:
        st.info("Dashboard data is not available yet.")
        return

    items = (recommendations or {}).get("recommendations", [])
    decisions_by_id, _ = recommendation_decisions()

    pending_items = [
        item for item in items
        if item.get("action") != "DO_NOTHING"
        and item.get("allowed")
        and not item.get("recommendation_error")
        and item.get("recommendation_id") not in decisions_by_id
    ]

    # Header
    header_col, button_col = st.columns([5, 1])

    with header_col:
        st.title("Dashboard")
        st.caption(
            f"{len(pending_items)} reminder(s) are waiting for your approval."
        )

    with button_col:
        st.write("")
        if st.button(
            "+ Add invoice",
            type="primary",
            use_container_width=True,
            on_click=lambda: st.session_state.update(
                {"workspace_page": "Invoices", "page": "Invoices"}
            ),
        ):
            st.rerun()

    # Summary values
    amounts = summary.get("outstanding_by_currency", {})
    outstanding_text = (
        " · ".join(
            f"{currency} {amount:,.2f}"
            for currency, amount in amounts.items()
        )
        if amounts
        else "0"
    )

    overdue_text = summary.get("overdue_invoices", 0)

    at_risk = sum(
        1
        for item in items
        if float(item.get("late_probability") or 0) >= 0.40
    )

    # Top summary cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="pp-summary-card">
                <div class="pp-summary-label">Outstanding</div>
                <div class="pp-summary-value">{html.escape(outstanding_text)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="pp-summary-card">
                <div class="pp-summary-label">Overdue</div>
                <div class="pp-summary-value pp-danger-text">{overdue_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="pp-summary-card">
                <div class="pp-summary-label">At-risk clients</div>
                <div class="pp-summary-value pp-warm-text">{at_risk}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Awaiting approval
    st.markdown(
        f"""
        <div class="pp-approval-card">
            <div class="pp-summary-label">Awaiting approval</div>
            <div class="pp-approval-number">{len(pending_items)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Invoices to follow up")

    if recommendation_error:
        st.error(recommendation_error)
        return

    if not pending_items:
        st.success("No invoices currently need a collection follow-up.")
        return

    selected = st.session_state.get("selected_recommendation")

    if selected:
        decisions_by_id, _ = recommendation_decisions()

        st.divider()
        st.subheader("Review recommendation")

        render_recommendation_card(selected, decisions_by_id)

        if st.button("Back to invoices to follow up"):
            st.session_state.pop("selected_recommendation", None)
            st.rerun()

        return

    ranked = sorted(
        pending_items,
        key=lambda item: (
            float(item.get("late_probability") or 0),
            int(item.get("overdue_days") or 0),
        ),
        reverse=True,
    )

    # Table header
    h1, h2, h3, h4, h5 = st.columns([2.2, 1.2, 1.3, 1.1, 1.3])

    h1.markdown("**CLIENT**")
    h2.markdown("**AMOUNT**")
    h3.markdown("**DUE**")
    h4.markdown("**LATE RISK**")
    h5.markdown("**ACTION**")

    for item in ranked:
        customer = item.get("customer_email") or "Unknown client"
        reference = item.get("paypal_invoice_id") or f"Invoice {item.get('invoice_id')}"
        amount = format_amount(item.get("amount"), item.get("currency"))
        due_date = format_date(item.get("due_at"))

        probability = float(item.get("late_probability") or 0)
        percentage = round(probability * 100)

        if probability >= 0.70:
            risk_text = f"High · {percentage}%"
            risk_class_name = "pp-high"
        elif probability >= 0.40:
            risk_text = f"Medium · {percentage}%"
            risk_class_name = "pp-medium"
        else:
            risk_text = f"Low · {percentage}%"
            risk_class_name = "pp-low"

        action = item.get("action", "DO_NOTHING")

        c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 1.3, 1.1, 1.3])

        with c1:
            st.markdown(
                f"""
                <div class="pp-table-client">
                    <strong>{html.escape(customer)}</strong>
                    <span>{html.escape(reference)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        c2.write(amount)
        c3.write(due_date)

        c4.markdown(
            f'<span class="pp-badge {risk_class_name}">{html.escape(risk_text)}</span>',
            unsafe_allow_html=True,
        )

        if c5.button(
            "Review draft",
            key=f"review-{item.get('recommendation_id')}",
            use_container_width=True,
        ):
            st.session_state["selected_recommendation"] = item
            st.rerun()


def render_recommendations(data, error):
    st.title("Recommendations")
    st.caption("AI-generated collection recommendations. Nothing is sent automatically.")

    if error:
        st.error(error)
        return

    if not data:
        st.info("No recommendation data loaded.")
        return

    recommendations = data.get("recommendations", [])

    st.write(f"**Open invoices:** {len(recommendations)}")

    if not recommendations:
        st.success("No open invoices need a collection recommendation.")
        return

    selected = st.session_state.get("selected_recommendation")

    if selected:
        decisions_by_id, _ = recommendation_decisions()

        st.divider()
        st.subheader("Review recommendation")

        render_recommendation_card(selected, decisions_by_id)

        if st.button("Back to recommendations"):
            st.session_state.pop("selected_recommendation", None)
            st.rerun()

        return

    for item in recommendations:
        invoice_id = item.get("invoice_id")
        customer = item.get("customer_email") or "Unknown customer"
        amount = format_amount(
            item.get("amount"),
            item.get("currency"),
        )
        risk = float(item.get("late_probability") or 0)
        risk_level = item.get("risk_level", "UNKNOWN")
        action = item.get("action", "DO_NOTHING")

        st.divider()

        st.subheader(f"Invoice #{invoice_id}")

        st.write(f"**Customer:** {customer}")
        st.write(f"**Amount:** {amount}")
        st.write(f"**Late-payment risk:** {risk:.0%} ({risk_level})")
        st.write(f"**Recommended action:** {recommendation_label(action)}")

        if action == "DO_NOTHING":
            st.info("No action recommended.")
            continue

        llm = item.get("llm_recommendation") or {}
        draft = str(llm.get("draft_message") or "").strip()

        if draft:
            st.write("**Draft message:**")
            st.text_area(
                "Email draft",
                draft,
                height=150,
                key=f"recommendation-draft-{invoice_id}",
            )

        if item.get("allowed"):
            st.success("Action allowed by policy.")
        else:
            st.warning(
                item.get(
                    "policy_reason",
                    "Action is not allowed by policy.",
                )
            )

        st.write(
            f"**Human approval required:** "
            f"{item.get('requires_human_approval', False)}"
        )


def render_invoices(data, error):
    title_col, button_col = st.columns([4, 1])

    with title_col:
        st.title("Invoices")
        st.caption("Invoice records currently stored in PaidPilot.")

    with button_col:
        st.write("")
        if st.button("+ Add invoice", type="primary", use_container_width=True):
            st.session_state["show_invoice_form"] = True
            st.rerun()

    if st.session_state.get("show_invoice_form", False):
        st.subheader("Create new invoice")

        customer_name = st.text_input(
            "Customer name",
            placeholder="e.g. Rahul Sharma",
        )

        customer_email = st.text_input(
            "Customer email",
            placeholder="e.g. rahul@example.com",
        )
    
        amount_col, date_col = st.columns(2)

        with amount_col:
            amount = st.number_input(
                "Amount (USD)",
                min_value=0.01,
                value=100.00,
                step=1.00,
            )

        with date_col:
            due_date = st.date_input("Due date")

        description = st.text_area(
            "Invoice Description",
            placeholder="What is this invoice for?",
        )

        form_col1, form_col2 = st.columns(2)

        with form_col1:
            if st.button(
                "Review invoice",
                type="primary",
                use_container_width=True,
        ):
                st.session_state["invoice_draft"] = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "amount": amount,
                    "due_date": due_date,
                    "description": description,
                }
                st.session_state["show_invoice_review"] = True
                st.rerun()

        with form_col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state["show_invoice_form"] = False
                st.rerun()

            if st.session_state.get("show_invoice_review", False):
                draft = st.session_state["invoice_draft"]

                st.divider()
                st.subheader("Review invoice")
                st.caption("Please confirm the invoice details before creating it.")

                st.write(f"**Customer:** {draft['customer_name']}")
                st.write(f"**Email:** {draft['customer_email']}")
                st.write(f"**Amount:** ${draft['amount']:.2f}")
                st.write(f"**Due date:** {draft['due_date']}")
                st.write(f"**Description:** {draft['description']}")

                review_col1, review_col2 = st.columns(2)

                with review_col1:
                    if st.button(
                        "Confirm & create",
                        type="primary",
                        use_container_width=True,
                    ):
                        payload = {
                            "recipient_email": draft["customer_email"],
                            "amount": str(draft["amount"]),
                            "description": draft["description"],
                            "due_date": str(draft["due_date"]),
                        }

                        response, error = api_request(
                            "POST",
                            "/api/invoices/create",
                            payload=payload,
                            timeout=60,
                        )

                        if error:
                            st.error(f"Could not create invoice: {error}")
                        else:
                            invoice_id = response.get("id")

                            send_response, send_error = api_request(
                                "POST",
                                f"/api/invoices/{invoice_id}/send",
                                timeout=60,
                            )

                            if send_error:
                                st.error(f"Invoice created, but could not send it: {send_error}")
                            else:
                                st.success(f"Invoice created and sent successfully: {invoice_id}")

                with review_col2:
                    if st.button("Edit", use_container_width=True):
                        st.session_state["show_invoice_review"] = False
                        st.rerun()

    if error:
        st.error(error)
        return
    invoices = (data or {}).get("invoices", [])
    if not invoices:
        st.info("No invoice records found. New PayPal invoices will appear here after they are stored by the backend.")
        return

    search_col, status_col = st.columns([2, 1])
    search = search_col.text_input("Search customer or invoice", key="invoice-search")
    statuses = sorted({str(item.get("status") or "UNKNOWN").upper() for item in invoices})
    status_filter = status_col.selectbox("Status", ["ALL"] + statuses)
    filtered = invoices
    if search:
        needle = search.casefold()
        filtered = [
            item for item in filtered
            if needle in str(item.get("paypal_invoice_id") or "").casefold()
            or needle in str(item.get("customer_email") or "").casefold()
        ]
    if status_filter != "ALL":
        filtered = [
            item for item in filtered
            if str(item.get("status") or "UNKNOWN").upper() == status_filter
        ]

    rows = [
        {
            "Invoice": item.get("paypal_invoice_id"),
            "Customer": item.get("customer_email") or "—",
            "Amount": format_amount(item.get("amount"), item.get("currency")),
            "Status": str(item.get("status") or "UNKNOWN").upper(),
            "Due date": format_date(item.get("due_at")),
        }
        for item in filtered
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(filtered)} of {len(invoices)} invoices")


def render_clients(data, error):
    st.title("Clients")
    st.caption("A directory built from customer emails on recorded invoices.")
    if error:
        st.error(error)
        return
    clients = (data or {}).get("clients", [])
    if not clients:
        st.info("No client records found yet. Client profiles appear when invoices include a customer email.")
        return
    total_invoices = sum(int(client.get("total_invoices", 0)) for client in clients)
    col1, col2 = st.columns(2)
    col1.metric("Clients", len(clients))
    col2.metric("Recorded invoices", total_invoices)
    rows = [
        {
            "Customer": client.get("customer_email"),
            "Invoices": client.get("total_invoices", 0),
            "Paid": client.get("paid_invoices", 0),
            "Open": client.get("outstanding_invoices", 0),
        }
        for client in clients
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_history(data, error):
    st.title("Review history")
    st.caption("Actual customer-facing actions sent by PaidPilot.")

    if error:
        st.error(error)
        return

    history = (data or {}).get("history", [])

    if not history:
        st.info("No customer-facing actions have been sent yet.")
        return

    for item in history:
        customer = item.get("customer_email") or "Customer email unavailable"
        action = recommendation_label(item.get("action"))
        status = item.get("status") or "UNKNOWN"

        title = (
            f"{action} · {customer} · "
            f"Invoice {item.get('invoice_id')}"
        )

        with st.expander(title):
            st.write(f"**Status:** {status}")
            st.write(f"**Action:** {action}")
            sent_at = item.get("created_at")
            st.write(
                f"**Sent:** {format_date(sent_at)}"
            )
            st.write(f"**Subject:** {item.get('subject') or ''}")

            st.markdown(
                f'<div class="pp-message">'
                f'{html.escape(item.get("body") or "")}'
                f'</div>',
                unsafe_allow_html=True,
            )

with st.sidebar:
    st.markdown("## PaidPilot")
    st.caption("AI collections workspace")
    page = st.radio(
        "Workspace",
        PAGES,
        key="workspace_page",
        label_visibility="collapsed",
    )

    st.session_state["page"] = page

    st.divider()
    st.caption("Human approval is required before any customer-facing action.")
    if st.button("Refresh analysis", use_container_width=True):
        for key in (
            "summary_data", "summary_error", "invoices_data", "invoices_error",
            "clients_data", "clients_error", "approvals_data", "approvals_error",
            "recommendations_data", "recommendations_error",
        ):
            st.session_state.pop(key, None)
        st.rerun()


recommendations_data = None
recommendations_error = None

if page == "Overview":
    recommendations_data, recommendations_error = get_recommendations()
    summary, summary_error = get_data("summary", "/api/dashboard/summary")
    render_overview(summary, summary_error, recommendations_data, recommendations_error)

elif page == "Recommendations":
    if st.button("Generate Recommendations", type="primary"):
        recommendations_data, recommendations_error = get_recommendations()
        render_recommendations(recommendations_data, recommendations_error)
    else:
        st.info("Click the button above to generate AI recommendations.")

elif page == "Invoices":
    invoice_data, invoice_error = get_data("invoices", "/api/invoices")
    render_invoices(invoice_data, invoice_error)

elif page == "Clients":
    client_data, client_error = get_data("clients", "/api/clients")
    render_clients(client_data, client_error)

elif page == "Review history":
    history_data, history_error = get_data(
        "review_history",
        "/api/review-history",
    )
    render_history(history_data, history_error)