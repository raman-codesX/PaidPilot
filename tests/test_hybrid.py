import unittest

from app.rag.hybrid_retriever import retrieve_hybrid_context


class TestHybridCustomerContextRetrieval(unittest.TestCase):

    def test_finds_relevant_context(self):
        results = retrieve_hybrid_context(
            customer_id="CUST001",
            query="payment extension cash flow",
        )

        self.assertGreater(len(results), 0)

        self.assertEqual(
            results[0]["type"],
            "customer_note",
        )

    def test_unknown_customer_returns_empty(self):
        results = retrieve_hybrid_context(
            customer_id="UNKNOWN",
            query="payment extension",
        )

        self.assertEqual(results, [])

    def test_customer_isolation(self):
        results = retrieve_hybrid_context(
            customer_id="CUST001",
            query="payment reminder",
        )

        for result in results:
            self.assertNotEqual(
                result["invoice_id"],
                "INV002",
            )


if __name__ == "__main__":
    unittest.main()