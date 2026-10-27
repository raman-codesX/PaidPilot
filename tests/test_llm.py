import json
import unittest
from unittest.mock import patch

from app.agent.llm import generate_collection_recommendation


class TestLLMRecommendation(unittest.TestCase):

    @patch("app.agent.llm.httpx.post")
    def test_llm_returns_extension_intent(self, mock_post):
        mock_response = mock_post.return_value
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "message": {
                "content": json.dumps({
                    "recommended_action": "FRIENDLY_REMINDER",
                    "reason": "The customer requested more time to pay.",
                    "draft_message": "Just checking in on the payment timeline.",
                    "extension_requested": True,
                    "extension_evidence": (
                        "Customer asked if they could pay next Friday."
                    ),
                })
            }
        }

        result = generate_collection_recommendation(
            late_probability=0.85,
            invoice_status="SENT",
            customer_context=[
                {
                    "type": "customer_note",
                    "text": (
                        "Customer asked if they could pay next Friday "
                        "because of cash-flow problems."
                    ),
                }
            ],
            draft_action="FRIENDLY_REMINDER",
        )

        self.assertTrue(result["extension_requested"])
        self.assertIn("next Friday", result["extension_evidence"])


if __name__ == "__main__":
    unittest.main()