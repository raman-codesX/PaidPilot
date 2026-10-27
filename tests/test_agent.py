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

        self.assertEqual(
            result["action"],
            "PAYMENT_PLAN",
        )
        self.assertTrue(
            result["requires_human_approval"]
        )

    def test_low_risk_recommends_do_nothing(self):
        result = recommend_action(
            late_probability=0.20,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertEqual(
            result["action"],
            "DO_NOTHING",
        )

    def test_paid_invoice_recommends_do_nothing(self):
        result = recommend_action(
            late_probability=0.90,
            invoice_status="PAID",
            reminder_count=0,
        )

        self.assertEqual(
            result["action"],
            "DO_NOTHING",
        )
        
    def test_paid_invoice_blocks_contact(self):
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
        self.assertTrue(result["requires_human_approval"])

    @patch(
    "app.agent.graph.generate_collection_recommendation"
    )

    def test_agent_uses_ml_prediction(self, mock_llm):

        mock_llm.return_value = {
            "recommended_action": "PAYMENT_PLAN",
            "reason": "High predicted late-payment risk.",
            "draft_message": "Please let us know when payment can be arranged.",
            "extension_requested": False,
            "extension_evidence": "",
        }

        result = recommend_action_from_invoice(
            invoice_amount=1500,
            previous_invoices=5,
            previous_late_payments=4,
            previous_late_rate=0.8,
            avg_previous_delay=3.2,
            invoice_status="SENT",
            reminder_count=0,
            customer_id="CUST001",
            query="payment extension",
        )

        self.assertIn(
            result["action"],
            {
                "FRIENDLY_REMINDER",
                "FIRM_REMINDER",
                "PAYMENT_PLAN",
            },
        )

        self.assertIn("late_probability", result)
        self.assertIn("risk_level", result)


    
    def test_recommendation_includes_reason(self):
        result = recommend_action(
            late_probability=0.85,
            invoice_status="SENT",
            reminder_count=0,
        )

        self.assertIn("recommendation_reason", result)
        self.assertTrue(result["recommendation_reason"])
        self.assertEqual(result["action"], "PAYMENT_PLAN")

    @patch(
        "app.agent.graph.generate_collection_recommendation"
    )    

    def test_agent_includes_customer_context(self, mock_llm):

        mock_llm.return_value = {
            "recommended_action": "PAYMENT_PLAN",
            "reason": "High predicted late-payment risk.",
            "draft_message": "Please let us know when payment can be arranged.",
            "extension_requested": False,
            "extension_evidence": "",
        }

        result = recommend_action_from_invoice(
            invoice_amount=1500,
            previous_invoices=5,
            previous_late_payments=3,
            previous_late_rate=0.6,
            avg_previous_delay=5,
            invoice_status="SENT",
            reminder_count=0,
            customer_id="CUST001",
            query="payment extension",
        )

        self.assertIn("customer_context", result)
        self.assertTrue(result["customer_context"])
        self.assertTrue(
            any(
                "extension" in item["text"].lower()
                for item in result["customer_context"]
            )
        )

    @patch("app.agent.graph.retrieve_hybrid_context", return_value=[])
    @patch("app.agent.graph.generate_collection_recommendation")
    def test_policy_rejects_llm_action_outside_risk_band(self, mock_llm, mock_retriever):
        mock_llm.return_value = {
            "recommended_action": "FRIENDLY_REMINDER",
            "reason": "Follow up politely.",
            "draft_message": "Please let us know when payment can be arranged.",
            "extension_requested": False,
            "extension_evidence": "",
        }

        result = recommend_action_from_invoice(
            invoice_amount=1500,
            previous_invoices=5,
            previous_late_payments=3,
            previous_late_rate=0.6,
            avg_previous_delay=5,
            invoice_status="SENT",
            reminder_count=0,
            customer_id="CUST001",
            query="invoice status",
        )

        llm_result = result["llm_recommendation"]

        self.assertEqual(result["action"], "PAYMENT_PLAN")
        self.assertEqual(
            llm_result["recommended_action"],
            "PAYMENT_PLAN",
        )
        self.assertTrue(llm_result["allowed"])
        self.assertEqual(
            llm_result["policy_reason"],
            "Action passed policy checks.",
        )
        self.assertTrue(llm_result["requires_human_approval"])

    
    @patch("app.agent.graph.generate_collection_recommendation")
    def test_extension_context_allows_high_risk_friendly_reminder(self, mock_llm):
        mock_llm.return_value = {
            "recommended_action": "FRIENDLY_REMINDER",
            "reason": "The customer requested an extension.",
            "draft_message": "Just checking in on the payment timeline.",
            "extension_requested": True,
            "extension_evidence": (
                "Customer requested a short payment extension "
                "due to temporary cash-flow problems."
            ),
        }

        with patch(
            "app.agent.graph.predict_late_payment",
            return_value={
                "late_probability": 0.85,
                "risk_level": "HIGH",
            },
        ), patch(
            "app.agent.graph.retrieve_hybrid_context",
            return_value=[
                {
                    "type": "customer_note",
                    "invoice_id": "INV001",
                    "text": (
                        "Customer requested a short payment extension "
                        "due to temporary cash-flow problems."
                    ),
                }
            ],
        ):
            result = recommend_action_from_invoice(
                invoice_amount=1500,
                previous_invoices=5,
                previous_late_payments=4,
                previous_late_rate=0.8,
                avg_previous_delay=3.2,
                invoice_status="SENT",
                reminder_count=0,
                customer_id="CUST001",
                query="payment extension",
            )

        llm_result = result["llm_recommendation"]
        self.assertEqual(llm_result["recommended_action"], "FRIENDLY_REMINDER")
        self.assertTrue(llm_result["allowed"])
        self.assertIn("extension", llm_result["policy_reason"].lower())
        self.assertTrue(llm_result["requires_human_approval"])

    def test_extension_evidence_accepts_matching_customer_note(self):
        from app.agent.graph import validate_extension_evidence

        context = [
            {
                "type": "customer_note",
                "text": (
                    "Customer requested a short payment extension "
                    "due to temporary cash-flow problems."
                ),
            }
        ]

        result = validate_extension_evidence(
            customer_context=context,
            extension_requested=True,
            extension_evidence=(
                "Customer requested a short payment extension"
            ),
        )

        self.assertTrue(result)

    def test_extension_evidence_rejects_unsupported_claim(self):
        from app.agent.graph import validate_extension_evidence

        context = [
            {
                "type": "customer_note",
                "text": "Customer asked for an invoice copy.",
            }
        ]

        result = validate_extension_evidence(
            customer_context=context,
            extension_requested=True,
            extension_evidence=(
                "Customer requested a payment extension."
            ),
        )

        self.assertFalse(result)
        



if __name__ == "__main__":
    unittest.main()