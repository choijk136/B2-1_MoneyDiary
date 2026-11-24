"""Catch a missing report/script or a stale performance snapshot without running a long benchmark."""

import hashlib
import json
import statistics
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = "docs/DESIGN_AND_PERFORMANCE.md"
RAW = "docs/evidence/profile-100k.json"
BENCHMARK = "scripts/benchmark_100k.py"


class PerformanceEvidenceTests(unittest.TestCase):
    def test_readme_points_to_shipped_report_raw_data_and_runner(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in (REPORT, RAW, BENCHMARK):
            with self.subTest(path=path):
                self.assertIn(f"({path})", readme)
                self.assertTrue((ROOT / path).is_file(), path)

    def test_recorded_100k_run_matches_samples_and_source_files(self) -> None:
        run = json.loads((ROOT / RAW).read_text(encoding="utf-8"))
        self.assertGreaterEqual(run["records"], 100_000)
        for sample in run["measurements"].values():
            self.assertEqual(len(sample["seconds"]), run["repeat"])
            self.assertEqual(statistics.median(sample["seconds"]), sample["median_s"])
        calls = run["cProfile"]["search_food"]["top_cumulative"]
        self.assertEqual(next(entry["calls"] for entry in calls if entry["function"].endswith("(from_dict)")),
                         run["records"])
        for path, measured in run["source_sha256"].items():
            with self.subTest(path=path):
                lf = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
                # Git may materialize text files with LF or CRLF on checkout.
                digests = {hashlib.sha256(content).hexdigest() for content in (lf, lf.replace(b"\n", b"\r\n"))}
                self.assertIn(measured, digests, "측정 대상이 바뀌었습니다. 보고서를 다시 생성하세요.")
