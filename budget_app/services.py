"""가계부 유스케이스와 집계 로직."""

from __future__ import annotations

import csv
import uuid
from calendar import monthrange
from collections import defaultdict
from collections.abc import Callable, Generator, Iterator
from dataclasses import replace
from itertools import islice
from pathlib import Path

from .errors import BudgetAppError
from .models import (
    MonthlySummary,
    Transaction,
    normalize_category,
    parse_tags,
    validate_amount,
    validate_date,
    validate_month,
    validate_type,
)
from .repositories import Storage

CSV_COLUMNS = ("date", "type", "category", "amount", "memo", "tags")


class BudgetService:
    """CLI와 파일 저장소 사이의 업무 규칙을 담당한다."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def _require_category(self, category: str, known: set[str] | None = None) -> str:
        category = normalize_category(category)
        exists = category in known if known is not None else self.storage.categories.contains(category)
        if not exists:
            raise BudgetAppError(
                f"등록되지 않은 카테고리입니다: {category}",
                "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
            )
        return category

    @staticmethod
    def _new_id(is_used: Callable[[str], bool]) -> str:
        while True:
            transaction_id = f"TX-{uuid.uuid4().hex[:12].upper()}"
            if not is_used(transaction_id):
                return transaction_id

    def add_transaction(
        self,
        *,
        date: str,
        transaction_type: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: str = "",
    ) -> Transaction:
        transaction = Transaction(
            id=self._new_id(self.storage.transactions.contains_id),
            type=validate_type(transaction_type),
            date=validate_date(date),
            amount=validate_amount(amount),
            category=self._require_category(category),
            memo=memo.strip(),
            tags=tuple(parse_tags(tags)),
        )
        self.storage.transactions.append(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> Iterator[Transaction]:
        if limit <= 0:
            raise BudgetAppError("limit은 1 이상의 정수여야 합니다.", "예: --limit 20")
        yield from islice(self.storage.transactions.iter_transactions(newest_first=True), limit)

    def search_transactions(
        self,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
        transaction_type: str | None = None,
        query: str | None = None,
        tag: str | None = None,
    ) -> Iterator[Transaction]:
        if date_from:
            date_from = validate_date(date_from)
        if date_to:
            date_to = validate_date(date_to)
        if date_from and date_to and date_from > date_to:
            raise BudgetAppError("검색 시작일이 종료일보다 늦습니다.", "--from과 --to 순서를 확인하세요.")
        if category:
            category = normalize_category(category)
        if transaction_type:
            transaction_type = validate_type(transaction_type)
        lowered_query = query.casefold() if query else None

        for transaction in self.storage.transactions.iter_transactions(newest_first=True):
            if date_from and transaction.date < date_from:
                continue
            if date_to and transaction.date > date_to:
                continue
            if category and transaction.category != category:
                continue
            if transaction_type and transaction.type != transaction_type:
                continue
            if lowered_query and lowered_query not in transaction.memo.casefold():
                continue
            if tag and tag not in transaction.tags:
                continue
            yield transaction

    def update_transaction(self, transaction_id: str, **changes: object) -> Transaction:
        current = self.storage.transactions.get(transaction_id)
        if current is None:
            raise BudgetAppError(f"거래를 찾을 수 없습니다: {transaction_id}", "`list`에서 id를 확인하세요.")
        if not changes:
            raise BudgetAppError("수정할 항목이 없습니다.", "id 외에 변경할 옵션을 하나 이상 입력하세요.")

        normalized: dict[str, object] = {}
        if "date" in changes:
            normalized["date"] = validate_date(str(changes["date"]))
        if "type" in changes:
            normalized["type"] = validate_type(str(changes["type"]))
        if "category" in changes:
            normalized["category"] = self._require_category(str(changes["category"]))
        if "amount" in changes:
            amount = changes["amount"]
            if not isinstance(amount, int):
                raise BudgetAppError("금액은 양수 정수여야 합니다.")
            normalized["amount"] = validate_amount(amount)
        if "memo" in changes:
            normalized["memo"] = str(changes["memo"]).strip()
        if "tags" in changes:
            normalized["tags"] = tuple(parse_tags(str(changes["tags"])))

        updated = replace(current, **normalized)
        self.storage.transactions.update(transaction_id, lambda _transaction: updated)
        return updated

    def delete_transaction(self, transaction_id: str) -> None:
        if not self.storage.transactions.delete(transaction_id):
            raise BudgetAppError(f"거래를 찾을 수 없습니다: {transaction_id}", "`list`에서 id를 확인하세요.")

    def monthly_summary(self, month: str, top: int = 3) -> MonthlySummary:
        month = validate_month(month)
        if top <= 0:
            raise BudgetAppError("top은 1 이상의 정수여야 합니다.", "예: --top 3")
        income = 0
        expense = 0
        count = 0
        category_expenses: defaultdict[str, int] = defaultdict(int)
        for transaction in self.storage.transactions.iter_transactions():
            if not transaction.date.startswith(f"{month}-"):
                continue
            count += 1
            if transaction.type == "income":
                income += transaction.amount
            else:
                expense += transaction.amount
                category_expenses[transaction.category] += transaction.amount
        ranked = tuple(sorted(category_expenses.items(), key=lambda item: (-item[1], item[0]))[:top])
        return MonthlySummary(
            month=month,
            transaction_count=count,
            income=income,
            expense=expense,
            balance=income - expense,
            category_expenses=ranked,
            budget=self.storage.budgets.get(month),
        )

    def set_budget(self, month: str, amount: int) -> None:
        self.storage.budgets.set(month, amount)

    def add_category(self, category: str) -> None:
        if not self.storage.categories.add(category):
            raise BudgetAppError(f"이미 존재하는 카테고리입니다: {category}", "다른 이름을 입력하세요.")

    def remove_category(self, category: str) -> None:
        category = normalize_category(category)
        if self.storage.transactions.uses_category(category):
            raise BudgetAppError(
                f"사용 중인 카테고리는 삭제할 수 없습니다: {category}",
                "해당 거래의 카테고리를 update한 뒤 다시 삭제하세요.",
            )
        if not self.storage.categories.remove(category):
            raise BudgetAppError(f"존재하지 않는 카테고리입니다: {category}", "`category list`로 확인하세요.")

    def import_csv(self, source: Path, *, atomic: bool = False) -> tuple[int, int, tuple[str, ...]]:
        """기본은 행별 부분 반영, atomic=True는 transactions.jsonl 전체 성공 또는 무변경."""
        if not source.is_file():
            raise BudgetAppError(f"가져올 파일을 찾을 수 없습니다: {source}", "--from 경로를 확인하세요.")
        repository = self.storage.transactions
        errors: list[str] = []
        rows = self._csv_transactions(source, errors, atomic=atomic)
        try:
            if atomic:
                imported = repository.append_many_atomic(rows)
            else:
                imported = 0
                for transaction in rows:
                    repository.append(transaction)
                    imported += 1
        except BudgetAppError as exc:
            if not atomic:
                raise
            raise BudgetAppError(f"CSV 전체 롤백: imported=0\n{exc.message}", exc.hint) from exc
        finally:
            rows.close()
        return imported, len(errors), tuple(errors)

    def _csv_transactions(
        self, source: Path, errors: list[str], *, atomic: bool
    ) -> Generator[Transaction, None, None]:
        """같은 행 검증기를 두 모드가 공유한다. 행 번호는 원본 CSV의 마지막 물리 줄."""
        with source.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file, strict=True)
            try:
                columns = next(reader, [])
                missing = [name for name in CSV_COLUMNS if name not in columns]
                if missing or len(columns) != len(set(columns)):
                    reason = f"누락: {', '.join(missing)}" if missing else "열 이름 중복"
                    raise BudgetAppError(f"CSV 헤더(1행) 오류: {reason}", f"필수 헤더: {', '.join(CSV_COLUMNS)}")

                # One scan per batch; reserve new IDs as well (including uncommitted rows).
                used_ids = {tx.id for tx in self.storage.transactions.iter_transactions()}
                categories = set(self.storage.categories.list())
                for fields in reader:
                    if not fields:  # empty physical line, not a transaction
                        continue
                    try:
                        if len(fields) != len(columns):
                            raise BudgetAppError(f"열 수가 다릅니다: 예상 {len(columns)}, 실제 {len(fields)}")
                        row = dict(zip(columns, fields))
                        try:
                            amount = int(row["amount"])
                        except ValueError as exc:
                            raise BudgetAppError("금액이 정수가 아닙니다.") from exc
                        transaction = Transaction(
                            id=self._new_id(used_ids.__contains__),
                            type=row["type"].strip(), date=row["date"].strip(), amount=amount,
                            category=self._require_category(row["category"], categories),
                            memo=row["memo"].strip(), tags=tuple(parse_tags(row["tags"])),
                        )
                    except BudgetAppError as exc:
                        errors.append(f"{reader.line_num}행: {exc.message}")
                        continue
                    used_ids.add(transaction.id)
                    yield transaction
            except csv.Error as exc:
                raise BudgetAppError(
                    f"{reader.line_num}행: CSV 구문 오류: {exc}", "따옴표와 열 구분을 확인하세요."
                ) from exc
            if atomic and errors:
                raise BudgetAppError("\n".join(errors), "표시된 행을 고친 뒤 --atomic으로 다시 실행하세요.")

    def export_csv(
        self,
        destination: Path,
        *,
        month: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        if not month and not date_from and not date_to:
            raise BudgetAppError(
                "내보내기 조건이 필요합니다.", "--month 또는 --from/--to 조건을 하나 이상 입력하세요."
            )
        if month and (date_from or date_to):
            raise BudgetAppError("--month와 기간 조건은 함께 사용할 수 없습니다.", "조건 종류 하나만 선택하세요.")
        if month:
            month = validate_month(month)
            year, month_number = (int(part) for part in month.split("-"))
            last_day = monthrange(year, month_number)[1]
            date_from = f"{month}-01"
            date_to = f"{month}-{last_day:02d}"

        destination.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with destination.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for transaction in self.search_transactions(date_from=date_from, date_to=date_to):
                writer.writerow(
                    {
                        "date": transaction.date,
                        "type": transaction.type,
                        "category": transaction.category,
                        "amount": transaction.amount,
                        "memo": transaction.memo,
                        "tags": ",".join(transaction.tags),
                    }
                )
                count += 1
        return count
