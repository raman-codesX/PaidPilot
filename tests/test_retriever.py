import unittest

from app.rag.retriever import retrieve_customer_context


class TestCustomerContextRetrieval(unittest.TestCase):

    def test_retrieves_matching_customer_context(self):
        results = retrieve_customer_context(
            customer_id="CUST001",
            query="payment extension",
        )

        self.assertTrue(results)
        self.assertTrue(
            any("extension" in item["text"].lower() for item in results)
        )

    def test_does_not_return_another_customer_context(self):
        results = retrieve_customer_context(
            customer_id="CUST001",
            query="payment reminder",
        )

        self.assertTrue(
            all(item["invoice_id"] == "INV001" for item in results)
        )

    def test_returns_empty_for_unknown_customer(self):
        results = retrieve_customer_context(
            customer_id="UNKNOWN",
            query="payment",
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()