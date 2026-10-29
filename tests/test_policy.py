import unittest

from app.agent.policy import evaluate_action


class TestCollectionPolicy(unittest.TestCase):

    def test_payment_plan_allowed_in_highest_risk_band(self):
        result = evaluate_action(
            action="PAYMENT_PLAN",
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertTrue(result["allowed"])

    def test_payment_plan_denied_outside_its_risk_band(self):
        result = evaluate_action(
            action="PAYMENT_PLAN",
            late_probability=0.80,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertFalse(result["allowed"])

    def test_reminder_limit_blocks_reminder(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.60,
            invoice_status="SENT",
            reminder_count=3,
        )

        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "Reminder limit reached.")

    def test_closed_invoice_blocks_contact(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.60,
            invoice_status="PAID",
            reminder_count=0,
        )

        self.assertFalse(result["allowed"])


if __name__ == "__main__":
    unittest.main()
