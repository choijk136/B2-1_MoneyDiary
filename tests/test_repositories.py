import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from budget_app.models import Transaction
from budget_app.repositories import DEFAULT_CATEGORIES, Storage


def sample_transaction(transaction_id: str, date: str = "2024-01-01") -> Transaction:
    return Transaction(transaction_id, "expense", date, 1000, "food")


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.temp_dir.name))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_three_storage_files_are_created(self) -> None:
        for name in ("transactions.jsonl", "categories.jsonl", "budgets.jsonl"):
            self.assertTrue((Path(self.temp_dir.name) / name).is_file())

    def test_default_categories_are_initialized(self) -> None:
        self.assertEqual(self.storage.categories.list(), sorted(DEFAULT_CATEGORIES))

    def test_reverse_generator_returns_latest_append_first(self) -> None:
        self.storage.transactions.append(sample_transaction("TX-1"))
        self.storage.transactions.append(sample_transaction("TX-2"))
        ids = [tx.id for tx in self.storage.transactions.iter_transactions(newest_first=True)]
        self.assertEqual(ids, ["TX-2", "TX-1"])

    def test_update_rewrites_selected_transaction(self) -> None:
        self.storage.transactions.append(sample_transaction("TX-1"))
        changed = self.storage.transactions.update(
            "TX-1", lambda transaction: replace(transaction, amount=2500)
        )
        self.assertTrue(changed)
        self.assertEqual(self.storage.transactions.get("TX-1").amount, 2500)  # type: ignore[union-attr]

    def test_delete_removes_selected_transaction(self) -> None:
        self.storage.transactions.append(sample_transaction("TX-1"))
        self.assertTrue(self.storage.transactions.delete("TX-1"))
        self.assertIsNone(self.storage.transactions.get("TX-1"))

    def test_budget_is_persistent_and_replaceable(self) -> None:
        self.storage.budgets.set("2024-01", 100000)
        self.storage.budgets.set("2024-01", 200000)
        reloaded = Storage(Path(self.temp_dir.name))
        self.assertEqual(reloaded.budgets.get("2024-01"), 200000)


if __name__ == "__main__":
    unittest.main()

