"""Run the presenter just as VS Code's integrated terminal would."""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PresenterTests(unittest.TestCase):
    def run_demo(self, *opts: str, keys: str = "") -> str:
        proc = subprocess.run([sys.executable, "-m", "scripts.demo_item1", *opts],
                              cwd=ROOT, input=keys, text=True, encoding="utf-8",
                              capture_output=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        return proc.stdout

    def test_seven_enters_complete_seven_independent_checks(self) -> None:
        out = self.run_demo(keys="\n" * 7)
        self.assertEqual(out.count("[확인 완료]"), 7)
        self.assertIn("135,000원 초과", out)
        last = out.split("[7/7]")[-1]
        for code in (0, 2, 3):
            self.assertIn(f"종료 코드: {code}", last)

    def test_selected_stage_and_quit(self) -> None:
        self.assertEqual(self.run_demo("--step", "5", "--auto", "--full").count("[확인 완료]"), 1)
        self.assertNotIn("$ python", self.run_demo(keys="q\n"))
