"""평가 시연용 데이터를 항상 같은 상태로 준비한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from budget_app.models import Transaction
from budget_app.repositories import Storage
from budget_app.services import BudgetService


DEMO_TRANSACTIONS = (
    Transaction(
        id="TX-DEMO-001",
        type="income",
        date="2026-09-01",
        amount=3_000_000,
        category="salary",
        memo="9월 급여",
        tags=("salary",),
    ),
    Transaction(
        id="TX-DEMO-002",
        type="expense",
        date="2026-09-02",
        amount=650_000,
        category="housing",
        memo="월세",
        tags=("fixed",),
    ),
    Transaction(
        id="TX-DEMO-003",
        type="expense",
        date="2026-09-05",
        amount=15_000,
        category="food",
        memo="학교 점심",
        tags=("meal", "school"),
    ),
    Transaction(
        id="TX-DEMO-004",
        type="expense",
        date="2026-09-07",
        amount=20_000,
        category="transport",
        memo="교통카드 충전",
        tags=("bus", "school"),
    ),
    Transaction(
        id="TX-DEMO-005",
        type="expense",
        date="2026-09-10",
        amount=90_000,
        category="leisure",
        memo="영화와 저녁",
        tags=("weekend",),
    ),
    Transaction(
        id="TX-DEMO-006",
        type="expense",
        date="2026-09-11",
        amount=35_000,
        category="food",
        memo="장보기",
        tags=("grocery",),
    ),
)

DATA_FILENAMES = (
    "transactions.jsonl",
    "categories.jsonl",
    "budgets.jsonl",
    "app.log",
)


def reset_storage(data_dir: Path) -> Storage:
    """지정 폴더의 앱 데이터 파일만 초기화한다."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for filename in DATA_FILENAMES:
        (data_dir / filename).unlink(missing_ok=True)
    return Storage(data_dir)


def prepare_demo(data_dir: Path, import_data_dir: Path, export_path: Path) -> None:
    storage = reset_storage(data_dir)
    for transaction in DEMO_TRANSACTIONS:
        storage.transactions.append(transaction)
    BudgetService(storage).set_budget("2026-09", 800_000)

    reset_storage(import_data_dir)
    export_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="평가 시연용 고정 데이터를 준비합니다.")
    parser.add_argument("--data-dir", default="./demo_data", help="시연 데이터 폴더")
    parser.add_argument("--import-data-dir", default="./demo_imported", help="CSV 재가져오기 확인 폴더")
    parser.add_argument("--export", default="./demo_export.csv", help="시연 중 생성할 CSV 경로")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data_dir = Path(args.data_dir)
    prepare_demo(data_dir, Path(args.import_data_dir), Path(args.export))
    print("[시연 준비 완료]")
    print(f"- 예시 거래: {len(DEMO_TRANSACTIONS)}건")
    print("- 월 예산: 2026-09 / 800,000원")
    print(f"- 데이터 폴더: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
