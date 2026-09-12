import tempfile
import unittest
from pathlib import Path

from budget_app.repositories import Storage
from scripts.prepare_demo import DEMO_TRANSACTIONS, prepare_demo


class PrepareDemoTests(unittest.TestCase):
    def test_prepare_demo_is_repeatable_and_uses_fixed_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_dir = root / "demo_data"
            import_data_dir = root / "demo_imported"
            export_path = root / "demo_export.csv"

            prepare_demo(data_dir, import_data_dir, export_path)
            prepare_demo(data_dir, import_data_dir, export_path)

            storage = Storage(data_dir)
            transactions = list(storage.transactions.iter_transactions())
            self.assertEqual(len(transactions), len(DEMO_TRANSACTIONS))
            self.assertEqual(transactions[0].id, "TX-DEMO-001")
            self.assertEqual(transactions[-1].id, "TX-DEMO-006")
            self.assertEqual(storage.budgets.get("2026-09"), 800_000)
            self.assertEqual(list(Storage(import_data_dir).transactions.iter_transactions()), [])


if __name__ == "__main__":
    unittest.main()
