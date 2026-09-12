import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from budget_app.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = str(Path(self.temp_dir.name) / "data")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *arguments: str, inputs: list[str] | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["--data-dir", self.data_dir, *arguments]
        input_values = iter(inputs or [])
        with redirect_stdout(stdout), redirect_stderr(stderr), patch("builtins.input", side_effect=input_values):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_interactive_add_and_list(self) -> None:
        code, output, _ = self.run_cli(
            "add", inputs=["2024-01-15", "expense", "food", "15000", "점심", "meal"]
        )
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료] id=TX-", output)
        code, output, _ = self.run_cli("list", "--limit", "1")
        self.assertEqual(code, 0)
        self.assertIn("점심", output)

    def test_missing_id_returns_nonzero_without_traceback(self) -> None:
        code, _, error = self.run_cli("delete", "--id", "TX-NOTFOUND")
        self.assertNotEqual(code, 0)
        self.assertIn("[오류]", error)
        self.assertNotIn("Traceback", error)


if __name__ == "__main__":
    unittest.main()

