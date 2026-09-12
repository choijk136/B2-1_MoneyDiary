"""JSONL 파일 저장소. 조회는 제너레이터로 한 줄씩 처리한다."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Generator, Iterable, Iterator
from pathlib import Path
from typing import Any

from .errors import BudgetAppError
from .models import Transaction, normalize_category, validate_amount, validate_month

DEFAULT_CATEGORIES = (
    "education",
    "food",
    "housing",
    "leisure",
    "medical",
    "other",
    "salary",
    "transport",
)


def _decode_json(line: str, source: Path) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise BudgetAppError(
            f"저장 파일의 JSON 형식이 손상되었습니다: {source}",
            "문제가 있는 줄을 백업한 뒤 올바른 JSON 객체로 수정하세요.",
        ) from exc
    if not isinstance(value, dict):
        raise BudgetAppError(
            f"저장 파일에 JSON 객체가 아닌 값이 있습니다: {source}", "각 줄을 JSON 객체로 저장해야 합니다."
        )
    return value


def _iter_lines_reverse(path: Path, block_size: int = 8192) -> Generator[str, None, None]:
    """파일 전체를 메모리에 올리지 않고 마지막 줄부터 읽는다."""
    with path.open("rb") as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        buffer = b""
        while position > 0:
            read_size = min(block_size, position)
            position -= read_size
            file.seek(position)
            buffer = file.read(read_size) + buffer
            lines = buffer.split(b"\n")
            buffer = lines[0]
            for line in reversed(lines[1:]):
                if line.strip():
                    yield line.decode("utf-8")
        if buffer.strip():
            yield buffer.decode("utf-8")


def _atomic_write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    """같은 디렉터리의 임시 파일을 fsync한 뒤 원자적으로 교체한다."""
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            for record in records:
                json.dump(record, temp_file, ensure_ascii=False, separators=(",", ":"))
                temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class TransactionRepository:
    """거래 JSONL 저장소."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, transaction: Transaction) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as file:
            json.dump(transaction.to_dict(), file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

    def iter_transactions(self, *, newest_first: bool = False) -> Iterator[Transaction]:
        """거래를 한 건씩 yield한다. 최신순은 파일을 뒤에서부터 읽는다."""
        if newest_first:
            lines: Iterable[str] = _iter_lines_reverse(self.path)
        else:
            lines = self.path.open("r", encoding="utf-8")
        try:
            for line in lines:
                if line.strip():
                    yield Transaction.from_dict(_decode_json(line, self.path))
        finally:
            close = getattr(lines, "close", None)
            if callable(close):
                close()

    def get(self, transaction_id: str) -> Transaction | None:
        return next((tx for tx in self.iter_transactions(newest_first=True) if tx.id == transaction_id), None)

    def contains_id(self, transaction_id: str) -> bool:
        return self.get(transaction_id) is not None

    def uses_category(self, category: str) -> bool:
        return any(tx.category == category for tx in self.iter_transactions())

    def update(self, transaction_id: str, transform: Callable[[Transaction], Transaction]) -> bool:
        found = False

        def changed_records() -> Iterator[dict[str, Any]]:
            nonlocal found
            for transaction in self.iter_transactions():
                if transaction.id == transaction_id:
                    found = True
                    transaction = transform(transaction)
                yield transaction.to_dict()

        _atomic_write_jsonl(self.path, changed_records())
        return found

    def delete(self, transaction_id: str) -> bool:
        found = False

        def remaining_records() -> Iterator[dict[str, Any]]:
            nonlocal found
            for transaction in self.iter_transactions():
                if transaction.id == transaction_id:
                    found = True
                    continue
                yield transaction.to_dict()

        _atomic_write_jsonl(self.path, remaining_records())
        return found


class CategoryStore:
    """카테고리 JSONL 저장소."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        if self.path.stat().st_size == 0:
            _atomic_write_jsonl(self.path, ({"name": name} for name in DEFAULT_CATEGORIES))

    def list(self) -> list[str]:
        result: list[str] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                data = _decode_json(line, self.path)
                try:
                    result.append(normalize_category(str(data["name"])))
                except KeyError as exc:
                    raise BudgetAppError(
                        "카테고리 저장 데이터가 손상되었습니다.", "categories.jsonl의 name 필드를 확인하세요."
                    ) from exc
        return sorted(set(result))

    def contains(self, category: str) -> bool:
        return normalize_category(category) in self.list()

    def add(self, category: str) -> bool:
        category = normalize_category(category)
        categories = self.list()
        if category in categories:
            return False
        categories.append(category)
        _atomic_write_jsonl(self.path, ({"name": name} for name in sorted(categories)))
        return True

    def remove(self, category: str) -> bool:
        category = normalize_category(category)
        categories = self.list()
        if category not in categories:
            return False
        _atomic_write_jsonl(self.path, ({"name": name} for name in categories if name != category))
        return True


class BudgetStore:
    """월 예산 JSONL 저장소."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def _iter_budgets(self) -> Iterator[tuple[str, int]]:
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                data = _decode_json(line, self.path)
                try:
                    month = validate_month(str(data["month"]))
                    amount = validate_amount(int(data["amount"]))
                except (KeyError, TypeError, ValueError) as exc:
                    raise BudgetAppError(
                        "예산 저장 데이터가 손상되었습니다.", "budgets.jsonl의 month와 amount 필드를 확인하세요."
                    ) from exc
                yield month, amount

    def get(self, month: str) -> int | None:
        month = validate_month(month)
        return next((amount for saved_month, amount in self._iter_budgets() if saved_month == month), None)

    def set(self, month: str, amount: int) -> None:
        month = validate_month(month)
        amount = validate_amount(amount)
        budgets = dict(self._iter_budgets())
        budgets[month] = amount
        _atomic_write_jsonl(
            self.path, ({"month": saved_month, "amount": budgets[saved_month]} for saved_month in sorted(budgets))
        )


class Storage:
    """세 개의 영구 저장소를 한 번에 구성한다."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.transactions = TransactionRepository(data_dir / "transactions.jsonl")
        self.categories = CategoryStore(data_dir / "categories.jsonl")
        self.budgets = BudgetStore(data_dir / "budgets.jsonl")

