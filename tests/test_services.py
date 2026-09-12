import csv
import tempfile
import unittest
from pathlib import Path

from budget_app.errors import BudgetAppError
from budget_app.repositories import Storage
from budget_app.services import BudgetService


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.service = BudgetService(Storage(self.root / "data"))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add(self, **overrides: object):
        values = {
            "date": "2024-01-15",
            "transaction_type": "expense",
            "category": "food",
            "amount": 15000,
            "memo": "점심",
            "tags": "meal",
        }
        values.update(overrides)
        return self.service.add_transaction(**values)  # type: ignore[arg-type]

    def test_add_and_list_latest_first(self) -> None:
        first = self.add(date="2024-01-01")
        second = self.add(date="2024-01-02")
        self.assertEqual([tx.id for tx in self.service.list_transactions(2)], [second.id, first.id])

    def test_unknown_category_is_rejected(self) -> None:
        with self.assertRaises(BudgetAppError):
            self.add(category="unknown")

    def test_search_combines_filters(self) -> None:
        expected = self.add(memo="학교 점심", tags="meal,school")
        self.add(date="2024-02-01", memo="저녁", tags="meal")
        result = list(
            self.service.search_transactions(
                date_from="2024-01-01", date_to="2024-01-31", category="food", query="학교", tag="school"
            )
        )
        self.assertEqual([tx.id for tx in result], [expected.id])

    def test_summary_and_budget_warning_values(self) -> None:
        self.add(amount=60000)
        self.add(transaction_type="income", category="salary", amount=100000, memo="용돈")
        self.service.set_budget("2024-01", 50000)
        summary = self.service.monthly_summary("2024-01", 3)
        self.assertEqual((summary.income, summary.expense, summary.balance), (100000, 60000, 40000))
        self.assertTrue(summary.is_over_budget)
        self.assertEqual(summary.budget_usage, 120.0)

    def test_update_allows_clearing_optional_fields(self) -> None:
        transaction = self.add()
        updated = self.service.update_transaction(transaction.id, memo="", tags="")
        self.assertEqual(updated.memo, "")
        self.assertEqual(updated.tags, ())

    def test_delete_unknown_id_is_error(self) -> None:
        with self.assertRaises(BudgetAppError):
            self.service.delete_transaction("TX-NOTFOUND")

    def test_used_category_cannot_be_removed(self) -> None:
        self.add()
        with self.assertRaises(BudgetAppError):
            self.service.remove_category("food")

    def test_import_counts_valid_and_invalid_rows(self) -> None:
        source = self.root / "import.csv"
        with source.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(("date", "type", "category", "amount", "memo", "tags"))
            writer.writerow(("2024-01-01", "expense", "food", "1000", "점심", "meal"))
            writer.writerow(("bad-date", "expense", "food", "1000", "오류", ""))
        imported, skipped, errors = self.service.import_csv(source)
        self.assertEqual((imported, skipped, len(errors)), (1, 1, 1))

    def test_export_requires_filter_and_writes_schema(self) -> None:
        self.add()
        destination = self.root / "export.csv"
        count = self.service.export_csv(destination, month="2024-01")
        self.assertEqual(count, 1)
        with destination.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(tuple(rows[0]), ("date", "type", "category", "amount", "memo", "tags"))
        with self.assertRaises(BudgetAppError):
            self.service.export_csv(destination)


if __name__ == "__main__":
    unittest.main()

