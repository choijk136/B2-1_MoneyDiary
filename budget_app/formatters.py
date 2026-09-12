"""외부 라이브러리 없는 스트리밍 콘솔 출력 포맷터."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .models import Transaction


HEADERS = ("ID", "날짜", "타입", "카테고리", "금액", "메모", "태그")
COLUMN_WIDTHS = (15, 10, 7, 16, 15, 24, 24)


def _fit(value: str, width: int) -> str:
    """고정 폭을 넘는 값은 생략 부호로 줄여 전체 결과 버퍼링을 피한다."""
    if len(value) > width:
        value = f"{value[: width - 1]}…"
    return value.ljust(width)


def _render_transaction(transaction: Transaction) -> str:
    values = (
        transaction.id,
        transaction.date,
        transaction.type,
        transaction.category,
        f"{transaction.amount:,}",
        transaction.memo,
        ",".join(transaction.tags),
    )
    return " | ".join(_fit(value, COLUMN_WIDTHS[index]) for index, value in enumerate(values)).rstrip()


def iter_transaction_lines(transactions: Iterable[Transaction]) -> Iterator[str]:
    """결과 전체를 list로 만들지 않고 화면에 표시할 줄을 하나씩 yield한다."""
    iterator = iter(transactions)
    try:
        first = next(iterator)
    except StopIteration:
        yield "데이터 없음"
        return

    yield " | ".join(_fit(header, COLUMN_WIDTHS[index]) for index, header in enumerate(HEADERS)).rstrip()
    yield "-+-".join("-" * width for width in COLUMN_WIDTHS)
    yield _render_transaction(first)
    for transaction in iterator:
        yield _render_transaction(transaction)
