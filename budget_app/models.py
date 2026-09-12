"""도메인 모델과 입력값 검증 함수."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from .errors import BudgetAppError

TRANSACTION_TYPES = {"income", "expense"}


def validate_date(value: str) -> str:
    """YYYY-MM-DD 형식의 실제 날짜인지 확인한다."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise BudgetAppError(
            "날짜 형식이 올바르지 않습니다.", "YYYY-MM-DD 형식의 실제 날짜를 입력하세요. 예: 2024-01-15"
        ) from exc
    return parsed.strftime("%Y-%m-%d")


def validate_month(value: str) -> str:
    """YYYY-MM 형식의 실제 연월인지 확인한다."""
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise BudgetAppError(
            "월 형식이 올바르지 않습니다.", "YYYY-MM 형식으로 입력하세요. 예: 2024-01"
        ) from exc
    return parsed.strftime("%Y-%m")


def validate_amount(value: int) -> int:
    """bool을 제외한 양수 정수인지 확인한다."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BudgetAppError("금액은 양수 정수여야 합니다.", "예: 15000")
    return value


def validate_type(value: str) -> str:
    """거래 타입을 검증한다."""
    if value not in TRANSACTION_TYPES:
        raise BudgetAppError(
            "거래 타입이 올바르지 않습니다.", "income 또는 expense 중 하나를 입력하세요."
        )
    return value


def normalize_category(value: str) -> str:
    """카테고리 이름의 공백과 금지 문자를 검증한다."""
    normalized = value.strip()
    if not normalized:
        raise BudgetAppError("카테고리 이름은 비워 둘 수 없습니다.", "한 글자 이상 입력하세요.")
    if any(char in normalized for char in "\r\n"):
        raise BudgetAppError("카테고리 이름에 줄바꿈을 사용할 수 없습니다.")
    return normalized


def parse_tags(value: str) -> list[str]:
    """쉼표 구분 태그를 중복 없이 정규화한다."""
    result: list[str] = []
    seen: set[str] = set()
    for raw_tag in value.split(","):
        tag = raw_tag.strip()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


@dataclass(frozen=True, slots=True)
class Transaction:
    """한 건의 수입 또는 지출."""

    id: str
    type: str
    date: str
    amount: int
    category: str
    memo: str = ""
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise BudgetAppError("거래 id는 비워 둘 수 없습니다.")
        validate_type(self.type)
        validate_date(self.date)
        validate_amount(self.amount)
        normalize_category(self.category)
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise BudgetAppError("태그는 비어 있지 않은 문자열이어야 합니다.")

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 딕셔너리로 변환한다."""
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Transaction:
        """저장된 딕셔너리를 검증하여 모델로 변환한다."""
        try:
            tags_value = data.get("tags", [])
            if not isinstance(tags_value, (list, tuple)):
                raise TypeError("tags must be a list")
            return cls(
                id=str(data["id"]),
                type=str(data["type"]),
                date=str(data["date"]),
                amount=int(data["amount"]),
                category=str(data["category"]),
                memo=str(data.get("memo", "")),
                tags=tuple(str(tag) for tag in tags_value),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BudgetAppError(
                "저장된 거래 데이터가 손상되었습니다.", "transactions.jsonl의 JSON 필드와 타입을 확인하세요."
            ) from exc


@dataclass(frozen=True, slots=True)
class MonthlySummary:
    """월별 집계 결과."""

    month: str
    transaction_count: int
    income: int
    expense: int
    balance: int
    category_expenses: tuple[tuple[str, int], ...]
    budget: int | None = None

    @property
    def budget_usage(self) -> float | None:
        if self.budget is None:
            return None
        return self.expense / self.budget * 100

    @property
    def is_over_budget(self) -> bool:
        return self.budget is not None and self.expense > self.budget

