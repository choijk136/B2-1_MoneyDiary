"""외부 라이브러리 없는 콘솔 출력 포맷터."""

from __future__ import annotations

from collections.abc import Iterable

from .models import Transaction


def format_transactions(transactions: Iterable[Transaction]) -> str:
    rows = list(transactions)
    if not rows:
        return "데이터 없음"
    headers = ("ID", "날짜", "타입", "카테고리", "금액", "메모", "태그")
    values = [
        (
            tx.id,
            tx.date,
            tx.type,
            tx.category,
            f"{tx.amount:,}",
            tx.memo,
            ",".join(tx.tags),
        )
        for tx in rows
    ]
    widths = [max(len(headers[index]), *(len(row[index]) for row in values)) for index in range(len(headers))]

    def render(row: tuple[str, ...]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip()

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join((render(headers), separator, *(render(row) for row in values)))

