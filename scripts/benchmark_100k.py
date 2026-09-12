"""10만 건 이상 데이터에서 주요 연산의 시간과 메모리를 재현 측정한다.

실행 예:
    python -m scripts.benchmark_100k --records 100000

테스트 데이터는 임시 폴더에 생성되며 실행 종료 후 자동 삭제된다.
외부 라이브러리는 사용하지 않는다.
"""

from __future__ import annotations

import argparse
import cProfile
import gc
import json
import platform
import pstats
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TypeVar

from budget_app.repositories import Storage
from budget_app.services import BudgetService

T = TypeVar("T")


def seed_transactions(path: Path, record_count: int) -> float:
    """벤치마크 준비 비용을 분리하기 위해 JSONL을 순차 생성한다."""
    categories = ("food", "transport", "housing", "education", "medical", "leisure", "other", "salary")
    started = time.perf_counter()
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for index in range(record_count):
            record = {
                "id": f"TX-{index:012d}",
                "type": "income" if index % 10 == 0 else "expense",
                "date": f"2024-01-{index % 28 + 1:02d}",
                "amount": (index % 100 + 1) * 100,
                "category": categories[index % len(categories)],
                "memo": f"benchmark transaction {index}",
                "tags": ["benchmark", f"group-{index % 10}"],
            }
            json.dump(record, file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
    return time.perf_counter() - started


def measure(name: str, operation: Callable[[], T]) -> tuple[str, float, float, T]:
    """단일 연산의 경과 시간과 tracemalloc 최대 메모리를 측정한다."""
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return name, elapsed, peak / 1024 / 1024, result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="budget_app 100k performance benchmark")
    parser.add_argument("--records", type=int, default=100_000, help="생성할 거래 수 (기본값: 100000)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.records < 100_000:
        raise SystemExit("--records는 평가 기준에 맞게 100000 이상이어야 합니다.")

    with tempfile.TemporaryDirectory(prefix="budget-app-benchmark-") as directory:
        data_dir = Path(directory) / "data"
        storage = Storage(data_dir)
        seed_seconds = seed_transactions(storage.transactions.path, args.records)
        service = BudgetService(storage)
        output_csv = Path(directory) / "export.csv"

        results = [
            measure("list(limit=20)", lambda: len(list(service.list_transactions(20)))),
            measure(
                "search(category=food)",
                lambda: sum(1 for _ in service.search_transactions(category="food")),
            ),
            measure("summary(month=2024-01)", lambda: service.monthly_summary("2024-01", 3).transaction_count),
            measure("get(missing-id)", lambda: storage.transactions.get("TX-NOT-FOUND") is None),
            measure(
                "update(oldest-id)",
                lambda: service.update_transaction("TX-000000000000", memo="updated").id,
            ),
            measure("delete(missing-id)", lambda: storage.transactions.delete("TX-NOT-FOUND")),
            measure("export(month=2024-01)", lambda: service.export_csv(output_csv, month="2024-01")),
        ]

        print(f"Python: {platform.python_version()}")
        print(f"Platform: {platform.platform()}")
        print(f"Records: {args.records:,}")
        print(f"JSONL size: {storage.transactions.path.stat().st_size / 1024 / 1024:.2f} MiB")
        print(f"Seed time (excluded): {seed_seconds:.3f} s")
        print()
        print(f"{'operation':28} {'seconds':>10} {'peak MiB':>10} {'result':>12}")
        print(f"{'-' * 28} {'-' * 10} {'-' * 10} {'-' * 12}")
        for name, elapsed, peak_mib, result in results:
            print(f"{name:28} {elapsed:10.3f} {peak_mib:10.2f} {str(result):>12}")

        print("\ncProfile: full-scan search(category=food), sorted by cumulative time")
        profiler = cProfile.Profile()
        profiler.enable()
        matched = sum(1 for _ in service.search_transactions(category="food"))
        profiler.disable()
        print(f"matched={matched:,}")
        pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(12)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
