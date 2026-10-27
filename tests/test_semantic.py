import unittest

from app.rag.semantic_retriever import retrieve_semantic_context


class TestSemanticCustomerContextRetrieval(unittest.TestCase):

    def test_finds_semantically_related_context(self):
        results = retrieve_semantic_context(
            customer_id="CUST001",
            query="customer needs extra time to pay",
        )

        self.assertTrue(results)

        self.assertTrue(
            any(
                "extension" in item["text"].lower()
                for item in results
            )
        )

    def test_does_not_return_another_customer_context(self):
        results = retrieve_semantic_context(
            customer_id="CUST001",
            query="payment reminder",
        )

        self.assertTrue(
            all(
                item["invoice_id"] == "INV001"
                for item in results
            )
        )

    def test_unknown_customer_returns_empty(self):
        results = retrieve_semantic_context(
            customer_id="UNKNOWN",
            query="payment extension",
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()