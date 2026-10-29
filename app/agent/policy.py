RISK_BANDS = {
    # action: (lower_exclusive, upper_inclusive)
    "FRIENDLY_REMINDER": (0.40, 0.70),
    "FIRM_REMINDER": (0.70, 0.80),
    "PAYMENT_PLAN": (0.80, 1.00),
}
REMINDER_ACTIONS = {"FRIENDLY_REMINDER", "FIRM_REMINDER"}
MAX_REMINDERS = 3
NO_CONTACT_STATUSES = {"PAID", "VOID", "CANCELLED"}


def evaluate_action(
    action: str,
    late_probability: float,
    invoice_status: str,
    reminder_count: int,
):
    """Deterministic safety policy for PaidPilot."""

    def deny(reason):
        return {"allowed": False, "reason": reason}

    def allow(reason):
        return {"allowed": True, "reason": reason}

    # Validate inputs (fail closed)
    if not 0.0 <= late_probability <= 1.0:
        return deny("Late probability must be between 0 and 1.")
    if action != "DO_NOTHING" and action not in RISK_BANDS:
        return deny(f"Unknown action: {action}.")

    p = late_probability

    # Doing nothing is always safe for invoices we must not contact about.
    if invoice_status in NO_CONTACT_STATUSES:
        if action == "DO_NOTHING":
            return allow("Invoice is closed. No action needed.")
        return deny(f"Invoice status is {invoice_status}; do not contact customer.")

    # Low risk: 0% to 40%
    if action == "DO_NOTHING":
        if p > 0.40:
            return deny("Risk is above 40%; a collection action is needed.")
        return allow("Low-risk invoice. No collection action needed.")

    # Reminder limit always applies, including context-based exceptions.
    if action in REMINDER_ACTIONS and reminder_count >= MAX_REMINDERS:
        return deny("Reminder limit reached.")

    # Risk band check
    low, high = RISK_BANDS[action]
    if not (low < p <= high):
        return deny(
            f"{action} requires risk above {low:.0%} and up to {high:.0%}."
        )

    return allow("Action passed policy checks.")


if __name__ == "__main__":
    test_cases = [
        # (action, probability, status, reminders, expected_allowed)
        ("DO_NOTHING", 0.40, "SENT", 0, True),
        ("DO_NOTHING", 0.41, "SENT", 0, False),
        ("FRIENDLY_REMINDER", 0.40, "SENT", 0, False),
        ("FRIENDLY_REMINDER", 0.41, "SENT", 0, True),
        ("FRIENDLY_REMINDER", 0.70, "SENT", 0, True),
        ("FIRM_REMINDER", 0.70, "SENT", 0, False),
        ("FIRM_REMINDER", 0.80, "SENT", 0, True),
        ("FIRM_REMINDER", 0.80, "SENT", 3, False),
        ("PAYMENT_PLAN", 0.80, "SENT", 0, False),
        ("PAYMENT_PLAN", 0.81, "SENT", 0, True),
        ("FRIENDLY_REMINDER", 0.50, "PAID", 0, False),
        ("DO_NOTHING", 0.90, "PAID", 0, True),
        ("FIRM_REMNDER", 0.75, "SENT", 0, False),
    ]

    for action, p, status, count, expected in test_cases:
        result = evaluate_action(action, p, status, count)
        flag = "OK  " if result["allowed"] == expected else "FAIL"
        print(f"{flag} | {p:.0%} | {action:18} | {status:5} | {result}")
