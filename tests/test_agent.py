import unittest
from unittest.mock import patch

from app.agent.graph import recommend_action, recommend_action_from_invoice


class TestAgentRecommendation(unittest.TestCase):

    def test_high_risk_recommends_payment_plan(self):
        result = recommend_action(
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertEqual(result["action"], "PAYMENT_PLAN")
        self.assertTrue(result["allowed"])
        self.assertTrue(result["requires_human_approval"])

    def test_low_risk_recommends_do_nothing(self):
        result = recommend_action(
            late_probability=0.20,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertEqual(result["action"], "DO_NOTHING")

    def test_paid_invoice_recommends_do_nothing(self):
        result = recommend_action(
            late_probability=0.90,
            invoice_status="PAID",
            reminder_count=0,
        )

        self.assertEqual(result["action"], "DO_NOTHING")
        self.assertTrue(result["allowed"])

    def test_reminder_limit_blocks_friendly_reminder(self):
        result = recommend_action(
            late_probability=0.60,
            invoice_status="SENT",
            reminder_count=3,
        )

        self.assertEqual(result["action"], "FRIENDLY_REMINDER")
        self.assertFalse(result["allowed"])

    @patch(
        "app.agent.graph.predict_late_payment",
        return_value={"late_probability": 0.9, "risk_level": "HIGH"},
    )
    def test_recommendation_uses_policy_without_rag(self, mock_prediction):
        result = recommend_action_from_invoice(
            invoice_amount=1500,
            previous_invoices=0,
            previous_late_payments=0,
            previous_late_rate=0,
            avg_previous_delay=0,
            invoice_status="SENT",
            reminder_count=0,
        )

        mock_prediction.assert_called_once()
        self.assertEqual(result["action"], "PAYMENT_PLAN")
        self.assertEqual(result["late_probability"], 0.9)
        self.assertEqual(result["risk_level"], "HIGH")
        self.assertNotIn("customer_context", result)

    def test_recommendation_includes_reason(self):
        result = recommend_action(
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertTrue(result["recommendation_reason"])
        self.assertEqual(result["action"], "PAYMENT_PLAN")


if __name__ == "__main__":
    unittest.main()
