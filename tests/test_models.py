import unittest

from budget_app.errors import BudgetAppError
from budget_app.models import Transaction, parse_tags, validate_date, validate_month


class ModelTests(unittest.TestCase):
    def test_transaction_round_trip(self) -> None:
        transaction = Transaction(
            id="TX-1",
            type="expense",
            date="2024-01-15",
            amount=15000,
            category="food",
            memo="점심",
            tags=("meal",),
        )
        self.assertEqual(Transaction.from_dict(transaction.to_dict()), transaction)

    def test_invalid_date_is_rejected(self) -> None:
        with self.assertRaises(BudgetAppError):
            validate_date("2024-13-40")

    def test_invalid_month_is_rejected(self) -> None:
        with self.assertRaises(BudgetAppError):
            validate_month("2024-00")

    def test_non_positive_amount_is_rejected(self) -> None:
        with self.assertRaises(BudgetAppError):
            Transaction("TX-1", "expense", "2024-01-01", 0, "food")

    def test_invalid_type_is_rejected(self) -> None:
        with self.assertRaises(BudgetAppError):
            Transaction("TX-1", "out", "2024-01-01", 100, "food")

    def test_tags_are_trimmed_deduplicated_and_empty_removed(self) -> None:
        self.assertEqual(parse_tags(" meal,work, meal, "), ["meal", "work"])


if __name__ == "__main__":
    unittest.main()

