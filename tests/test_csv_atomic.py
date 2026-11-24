"""평가 #16: 실제 CLI 결과와 기존 거래 파일의 바이트를 함께 확인한다."""

import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from budget_app.cli import main
from budget_app.repositories import Storage
from budget_app.services import CSV_COLUMNS, BudgetService


MIXED = Path(__file__).parent / "fixtures" / "mixed_import.csv"
GOOD = ("2026-09-12", "expense", "food", "5500", "학생식당 점심", "school,meal")


class CsvAtomicTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.storage = Storage(self.root / "ledger")
        self.service = BudgetService(self.storage)
        self.original = self.service.add_transaction(
            date="2026-09-01", transaction_type="income", category="salary", amount=100000, memo="기존 거래"
        )
        self.service.set_budget("2026-09", 50000)
        self.ledger = self.storage.transactions.path
        self.before = self.ledger.read_bytes()
        self.source = self.root / "input.csv"

    def write_csv(self, *rows: tuple[str, ...]) -> Path:
        with self.source.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)
            writer.writerows(rows)
        return self.source

    def run_import(self, source: Path, *options: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--data-dir", str(self.storage.data_dir), "import", "--from", str(source), *options])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_atomic_mixed_rolls_back_even_valid_prefix_and_suffix(self) -> None:
        before_all = {path: path.read_bytes() for path in self.storage.data_dir.glob("*.jsonl")}
        with patch("budget_app.repositories.os.replace", wraps=os.replace) as commit:
            code, output, error = self.run_import(MIXED, "--atomic")
            commit.assert_not_called()
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("전체 롤백: imported=0", error)
        self.assertIn("3행: 금액은 양수 정수", error)
        self.assertNotIn("Traceback", error)
        self.assertEqual(before_all, {path: path.read_bytes() for path in self.storage.data_dir.glob("*.jsonl")})

    def test_default_commits_both_valid_rows_and_reports_bad_row(self) -> None:
        code, output, error = self.run_import(MIXED)
        self.assertEqual((code, error), (0, ""))
        self.assertIn("imported=2, skipped=1", output)
        self.assertIn("3행: 금액은 양수 정수", output)
        self.assertEqual([tx.memo for tx in self.storage.transactions.iter_transactions()],
                         ["기존 거래", "학생식당 점심", "용돈"])

    def test_atomic_success_publishes_once_and_preserves_original_prefix(self) -> None:
        source = self.write_csv(GOOD, (*GOOD[:4], '쉼표, 따옴표 "와"\n두 번째 줄', "x,y"))
        # A valid manually written final JSONL record need not end with a newline.
        self.ledger.write_bytes(self.before.rstrip(b"\n"))
        with patch("budget_app.repositories.os.replace", wraps=os.replace) as commit:
            code, output, error = self.run_import(source, "--atomic")
        self.assertEqual((code, error), (0, ""))
        self.assertIn("imported=2, skipped=0", output)
        commit.assert_called_once()
        self.assertTrue(self.ledger.read_bytes().startswith(self.before))
        transactions = list(self.storage.transactions.iter_transactions())
        self.assertEqual(len(transactions), 3)
        self.assertEqual(transactions[0], self.original)
        self.assertEqual(transactions[-1].memo, '쉼표, 따옴표 "와"\n두 번째 줄')
        self.assertEqual(transactions[-1].tags, ("x", "y"))

    def test_reports_all_bad_rows_using_physical_csv_lines(self) -> None:
        source = self.write_csv((*GOOD[:4], "두 줄\n메모", ""), (*GOOD[:3], "x", "", ""),
                                (GOOD[0], "expense", "unregistered", "1", "", ""))
        code, _, error = self.run_import(source, "--atomic")
        self.assertEqual(code, 2)
        self.assertIn("4행: 금액이 정수가 아닙니다.", error)
        self.assertIn("5행: 등록되지 않은 카테고리", error)
        self.assertEqual(self.ledger.read_bytes(), self.before)

    def test_broken_quoting_after_valid_row_never_commits(self) -> None:
        self.write_csv(GOOD)
        with self.source.open("a", encoding="utf-8", newline="") as file:
            file.write('2026-09-13,expense,food,100,"unterminated\n')
        code, _, error = self.run_import(self.source, "--atomic")
        self.assertEqual(code, 2)
        self.assertIn("3행: CSV 구문 오류", error)
        self.assertEqual(self.ledger.read_bytes(), self.before)

    def test_wrong_header_and_ragged_row_do_not_commit(self) -> None:
        self.source.write_text("date,amount\n2026-09-12,100\n", encoding="utf-8")
        code, _, error = self.run_import(self.source, "--atomic")
        self.assertEqual(code, 2)
        self.assertIn("헤더(1행)", error)
        code, _, error = self.run_import(self.write_csv(GOOD, (*GOOD, "extra")), "--atomic")
        self.assertEqual(code, 2)
        self.assertIn("3행: 열 수", error)
        self.assertEqual(self.ledger.read_bytes(), self.before)

    def test_header_only_is_a_successful_no_op(self) -> None:
        with patch("budget_app.repositories.os.replace", wraps=os.replace) as commit:
            self.assertEqual(self.service.import_csv(self.write_csv(), atomic=True), (0, 0, ()))
            commit.assert_not_called()
        self.assertEqual(self.ledger.read_bytes(), self.before)

    def test_invalid_utf8_is_a_file_error_with_no_partial_commit(self) -> None:
        self.write_csv(GOOD, (*GOOD[:4], "가" * 10000, ""), GOOD)
        with self.source.open("ab") as file:
            file.write(b"\xff\n")
        code, output, error = self.run_import(self.source, "--atomic")
        self.assertEqual((code, output), (3, ""))
        self.assertNotIn("Traceback", error)
        self.assertEqual(self.ledger.read_bytes(), self.before)

    def test_failed_fsync_or_replace_keeps_bytes_and_removes_temporary_file(self) -> None:
        source = self.write_csv(GOOD, GOOD)
        original_files = set(self.storage.data_dir.iterdir())
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation):
                with patch(f"budget_app.repositories.os.{operation}", side_effect=OSError("test write failure")):
                    code, output, error = self.run_import(source, "--atomic")
                self.assertEqual(code, 3)
                self.assertEqual(output, "")
                self.assertNotIn("Traceback", error)
                self.assertEqual(self.ledger.read_bytes(), self.before)
                self.assertEqual(set(self.storage.data_dir.iterdir()) - {self.storage.data_dir / "app.log"},
                                 original_files)

    def test_new_ids_avoid_existing_and_not_yet_committed_rows(self) -> None:
        old = self.original.id.removeprefix("TX-").lower()
        # Regenerate on both an existing ID and the first staged row's ID.
        hx = ["1" * 12, "2" * 12, "3" * 12]
        a, b = [value for value in hx if value != old][:2]
        ids = [SimpleNamespace(hex=value) for value in (old, a, a, b)]
        with patch("budget_app.services.uuid.uuid4", side_effect=ids):
            self.assertEqual(self.service.import_csv(self.write_csv(GOOD, GOOD), atomic=True), (2, 0, ()))
        self.assertEqual(len({tx.id for tx in self.storage.transactions.iter_transactions()}), 3)


if __name__ == "__main__":
    unittest.main()
