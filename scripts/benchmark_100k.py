"""10만 건 이상 데이터에서 주요 연산의 시간과 메모리를 재현 측정한다.

실행 예:
    python -m scripts.benchmark_100k --records 100000

테스트 데이터는 임시 폴더에 생성되며 실행 종료 후 자동 삭제된다.
외부 라이브러리는 사용하지 않는다.
"""

from __future__ import annotations

import argparse
import cProfile
import csv
import gc
import hashlib
import json
import platform
import pstats
import shutil
import statistics
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from budget_app.repositories import Storage
from budget_app.services import CSV_COLUMNS, BudgetService

ROOT = Path(__file__).resolve().parents[1]


def seed_transactions(path: Path, record_count: int) -> float:
    """벤치마크 준비 비용을 분리하기 위해 JSONL을 순차 생성한다."""
    categories = ("food", "transport", "housing", "education", "medical", "leisure", "other", "salary")
    started = time.perf_counter()
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for index in range(record_count):
            record = {
                "id": f"TX-{index:012d}",
                "type": "income" if index % 10 == 0 else "expense",
                "date": f"2024-{index // 28 % 12 + 1:02d}-{index % 28 + 1:02d}",
                "amount": (index % 100 + 1) * 100,
                "category": categories[index % len(categories)],
                "memo": f"benchmark transaction {index}",
                "tags": ["benchmark", f"group-{index % 10}"],
            }
            json.dump(record, file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
    return time.perf_counter() - started


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cpu_profile(operation: Callable[[], object]) -> dict:
    profiler = cProfile.Profile()
    profiler.runcall(operation)
    stats = pstats.Stats(profiler)
    entries = sorted(stats.stats.items(), key=lambda pair: -pair[1][3])
    return {
        "total_calls": stats.total_calls, "profile_seconds": stats.total_tt,
        "top_cumulative": [
            {"function": f"{Path(file).name}:{line}({name})", "calls": total,
             "self_s": own, "cumulative_s": cumulative}
            for (file, line, name), (_, total, own, cumulative, _) in entries[:18]
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="budget_app 100k performance benchmark")
    parser.add_argument("--records", type=int, default=100_000, help="생성할 거래 수 (기본값: 100000)")
    parser.add_argument("--repeat", type=int, default=3, help="벽시계 측정 반복 횟수 (기본값: 3)")
    parser.add_argument("--output", type=Path, help="동일한 JSON 결과를 저장할 경로 (선택)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.records < 100_000 or args.repeat < 1:
        raise SystemExit("--records >= 100000, --repeat >= 1 이어야 합니다.")

    with tempfile.TemporaryDirectory(prefix="budget-app-benchmark-") as directory:
        work = Path(directory)
        storage = Storage(work / "data")
        seed = work / "seed.jsonl"
        seed_seconds = seed_transactions(seed, args.records)
        service = BudgetService(storage)
        batch = work / "batch.csv"
        with batch.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_COLUMNS)
            writer.writerows(("2024-01-01", "expense", "food", 100, f"batch {i}", "") for i in range(1000))

        oldest = "TX-000000000000"
        january = sum(1 for i in range(args.records) if i // 28 % 12 == 0)
        cases: dict[str, tuple[Callable[[], object], object]] = {
            "list_20": (lambda: sum(1 for _ in service.list_transactions(20)), 20),
            "search_food": (lambda: sum(1 for _ in service.search_transactions(category="food")),
                            (args.records + 7) // 8),
            "summary_january": (lambda: service.monthly_summary("2024-01").transaction_count, january),
            "get_missing": (lambda: storage.transactions.get("TX-MISSING"), None),
            "update_oldest": (lambda: service.update_transaction(oldest, memo="updated").id, oldest),
            "delete_oldest": (lambda: storage.transactions.delete(oldest), True),
            "export_january": (lambda: service.export_csv(work / "export.csv", month="2024-01"), january),
            "import_atomic_1000": (lambda: service.import_csv(batch, atomic=True), (1000, 0, ())),
        }

        def reset() -> None:
            shutil.copyfile(seed, storage.transactions.path)
            gc.collect()

        measurements = {}
        profiles = {}
        for name, (operation, expected) in cases.items():
            seconds = []
            for _ in range(args.repeat):
                reset()  # not timed; even a mutating case always starts at the same fixture
                started = time.perf_counter()
                result = operation()
                seconds.append(time.perf_counter() - started)
                if result != expected:
                    raise RuntimeError(f"{name}: expected {expected!r}, got {result!r}")
            measurements[name] = {
                "seconds": seconds, "median_s": statistics.median(seconds), "result": expected,
            }
            if name in ("list_20", "search_food", "import_atomic_1000"):
                reset()
                tracemalloc.start()  # separate pass, not part of the latency sample
                try:
                    operation()
                    measurements[name]["peak_python_bytes"] = tracemalloc.get_traced_memory()[1]
                finally:
                    tracemalloc.stop()
            if name in ("search_food", "update_oldest"):
                reset()
                profiles[name] = cpu_profile(operation)

        sources = ("budget_app/models.py", "budget_app/repositories.py", "budget_app/services.py",
                   "scripts/benchmark_100k.py")
        report = {
            "environment": {"python": platform.python_version(), "platform": platform.platform()},
            "records": args.records, "fixture_bytes": seed.stat().st_size, "fixture_sha256": sha256(seed),
            "seed_seconds_excluded": seed_seconds, "repeat": args.repeat,
            "source_sha256": {name: sha256(ROOT / name) for name in sources},
            "measurements": measurements, "cProfile": profiles,
        }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
