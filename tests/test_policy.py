
import unittest

from app.agent.policy import evaluate_action


class TestExtensionPolicy(unittest.TestCase):

    def test_high_risk_friendly_reminder_allowed_with_extension(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
            extension_requested=True,
        )

        self.assertTrue(result["allowed"])

    def test_high_risk_friendly_reminder_denied_without_extension(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
            extension_requested=False,
        )

        self.assertFalse(result["allowed"])

    def test_paid_invoice_blocks_extension_exception(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.85,
            invoice_status="PAID",
            reminder_count=0,
            extension_requested=True,
        )

        self.assertFalse(result["allowed"])

    def test_reminder_limit_blocks_extension_exception(self):
        result = evaluate_action(
            action="FRIENDLY_REMINDER",
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=3,
            extension_requested=True,
        )

        self.assertFalse(result["allowed"])


if __name__ == "__main__":
    unittest.main()
