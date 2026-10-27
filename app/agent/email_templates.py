from decimal import Decimal


def _format_amount(amount, currency):
    if amount is None:
        return f"{currency} amount"

    amount = Decimal(str(amount))

    if currency == "USD":
        return f"${amount:,.2f}"

    return f"{currency} {amount:,.2f}"

def build_email(
    action,
    invoice_id,
    amount,
    currency,
    client_name="Customer",
    due_date="the due date",
    days_overdue=0,
    is_overdue=False,
    sender_name="PaidPilot",
):
    formatted_amount = _format_amount(amount, currency)

    if action == "FRIENDLY_REMINDER":
        if is_overdue:
            return {
                "subject": f"Payment overdue: Invoice {invoice_id}",
                "body": (
                    f"Hi {client_name},\n\n"
                    f"Hope you're doing well. I wanted to follow up regarding "
                    f"invoice {invoice_id} for {formatted_amount}, which is "
                    f"{days_overdue} days overdue.\n\n"
                    f"Please arrange the payment at your earliest convenience. "
                    f"If you've already arranged payment, please ignore this email.\n\n"
                    f"If there is any issue affecting the payment, please let "
                    f"me know.\n\n"
                    f"Thank you,\n"
                    f"{sender_name}"
                ),
            }

        return {
            "subject": f"Quick reminder: Invoice {invoice_id}",
            "body": (
                f"Hi {client_name},\n\n"
                f"Hope you're doing well! Just a gentle reminder that "
                f"invoice {invoice_id} for {formatted_amount} "
                f"is due on {due_date}.\n\n"
                f"Please arrange payment by the due date.\n\n"
                f"If you've already arranged payment, please ignore this. "
                f"Thanks so much!\n\n"
                f"{sender_name}"
            ),
        }

    if action == "FIRM_REMINDER":
        return {
            "subject": f"Payment reminder: Invoice {invoice_id}",
            "body": (
                f"Hi {client_name},\n\n"
                f"This is a reminder regarding invoice {invoice_id} "
                f"for {formatted_amount}, which is due on {due_date}.\n\n"
                f"Please make sure the payment is arranged by the due date.\n\n"
                f"If there is an issue affecting payment, "
                f"please reply to this email and let me know.\n\n"
                f"{sender_name}"
            ),
        }

    if action == "PAYMENT_PLAN":
        if is_overdue:
            return {
                "subject": f"Let's sort out Invoice {invoice_id}",
                "body": (
                    f"Hi {client_name},\n\n"
                    f"I understand things can get tight. Invoice "
                    f"{invoice_id} for {formatted_amount} is currently "
                    f"{days_overdue} days overdue.\n\n"
                    f"I'm happy to discuss a payment plan that "
                    f"works for you.\n\n"
                    f"Please reply to this email and let me know "
                    f"what payment schedule would work best.\n\n"
                    f"{sender_name}"
                ),
            }

        return {          
            "subject": f"Friendly Follow-up on Invoice {invoice_id}",
            "body": (
                f"Hi {client_name},\n\n"
                f"I wanted to follow up regarding Invoice "
                f"{invoice_id} for {formatted_amount}, which is due on "
                f"{due_date}.\n\n"
                f"Based on your previous payment history, we would "
                f"appreciate it if you could arrange the payment by "
                f"the due date.\n\n"
                f"Please let me know if you have any questions or "
                f"need any information from my side.\n\n"
                f"Thank you,\n"
                f"{sender_name}"
            ),

        }

    if action == "DO_NOTHING":
        return {
            "subject": "",
            "body": "",
        }

    raise ValueError(f"Unknown email action: {action}")