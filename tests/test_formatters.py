import unittest

from budget_app.formatters import iter_transaction_lines
from budget_app.models import Transaction


class FormatterTests(unittest.TestCase):
    def test_empty_iterator_prints_data_absence(self) -> None:
        self.assertEqual(list(iter_transaction_lines(iter(()))), ["데이터 없음"])

    def test_formatter_consumes_transactions_incrementally(self) -> None:
        consumed: list[int] = []

        def transactions():
            for index in range(3):
                consumed.append(index)
                yield Transaction(
                    id=f"TX-{index}",
                    type="expense",
                    date="2024-01-01",
                    amount=1000,
                    category="food",
                )

        lines = iter_transaction_lines(transactions())
        self.assertEqual(consumed, [])
        self.assertIn("ID", next(lines))
        self.assertEqual(consumed, [0])
        list(lines)
        self.assertEqual(consumed, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
