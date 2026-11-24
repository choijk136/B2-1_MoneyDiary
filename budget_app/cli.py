"""argparse 기반 콘솔 인터페이스."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .decorators import safe_command
from .errors import BudgetAppError
from .formatters import iter_transaction_lines
from .models import normalize_category, validate_amount, validate_date, validate_type
from .repositories import Storage
from .services import BudgetService


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("정수를 입력하세요.") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("1 이상의 정수를 입력하세요.")
    return parsed


def _service(args: argparse.Namespace) -> BudgetService:
    return BudgetService(Storage(Path(args.data_dir)))


def _prompt_validated(prompt: str, validator: object) -> object:
    while True:
        value = input(prompt)
        try:
            return validator(value)  # type: ignore[operator]
        except BudgetAppError as exc:
            print(f"[오류] {exc.message}")
            print(f"[힌트] {exc.hint}")


@safe_command
def command_add(args: argparse.Namespace) -> int:
    service = _service(args)
    date = str(_prompt_validated("날짜(YYYY-MM-DD): ", validate_date))
    transaction_type = str(_prompt_validated("타입(income/expense): ", validate_type))
    while True:
        category = input("카테고리: ").strip()
        try:
            category = normalize_category(category)
            if not service.storage.categories.contains(category):
                raise BudgetAppError(
                    f"등록되지 않은 카테고리입니다: {category}",
                    "`category list`로 확인하거나 `category add`로 먼저 등록하세요.",
                )
            break
        except BudgetAppError as exc:
            print(f"[오류] {exc.message}")
            print(f"[힌트] {exc.hint}")

    def amount_validator(raw: str) -> int:
        try:
            return validate_amount(int(raw))
        except ValueError as exc:
            raise BudgetAppError("금액은 양수 정수여야 합니다.", "예: 15000") from exc

    amount = int(_prompt_validated("금액(양수 정수): ", amount_validator))
    memo = input("메모(선택): ")
    tags = input("태그(쉼표로 구분, 없으면 엔터): ")
    transaction = service.add_transaction(
        date=date,
        transaction_type=transaction_type,
        category=category,
        amount=amount,
        memo=memo,
        tags=tags,
    )
    print(f"[저장 완료] id={transaction.id}")
    return 0


@safe_command
def command_list(args: argparse.Namespace) -> int:
    for line in iter_transaction_lines(_service(args).list_transactions(args.limit)):
        print(line)
    return 0


@safe_command
def command_search(args: argparse.Namespace) -> int:
    results = _service(args).search_transactions(
        date_from=args.date_from,
        date_to=args.date_to,
        category=args.category,
        transaction_type=args.transaction_type,
        query=args.query,
        tag=args.tag,
    )
    for line in iter_transaction_lines(results):
        print(line)
    return 0


@safe_command
def command_summary(args: argparse.Namespace) -> int:
    summary = _service(args).monthly_summary(args.month, args.top)
    if summary.transaction_count == 0:
        print(f"{summary.month}: 데이터 없음")
        return 0
    print(f"총 수입: {summary.income:,}원")
    print(f"총 지출: {summary.expense:,}원")
    print(f"잔액: {summary.balance:,}원")
    if summary.budget is not None:
        print(f"예산: {summary.budget:,}원 (사용률 {summary.budget_usage:.1f}%)")
        if summary.is_over_budget:
            print(f"[경고] 예산을 {summary.expense - summary.budget:,}원 초과했습니다.")
    print(f"\n지출 TOP {args.top}")
    if not summary.category_expenses:
        print("지출 데이터 없음")
    for index, (category, amount) in enumerate(summary.category_expenses, start=1):
        print(f"{index}) {category} {amount:,}원")
    return 0


@safe_command
def command_budget_set(args: argparse.Namespace) -> int:
    _service(args).set_budget(args.month, args.amount)
    print(f"[저장 완료] {args.month} 예산 {args.amount:,}원")
    return 0


@safe_command
def command_budget_get(args: argparse.Namespace) -> int:
    amount = _service(args).storage.budgets.get(args.month)
    if amount is None:
        print(f"{args.month}: 설정된 예산 없음")
    else:
        print(f"{args.month} 예산: {amount:,}원")
    return 0


@safe_command
def command_category_add(args: argparse.Namespace) -> int:
    name = args.name if args.name is not None else input("카테고리명: ")
    _service(args).add_category(name)
    print(f"[저장 완료] category={name.strip()}")
    return 0


@safe_command
def command_category_list(args: argparse.Namespace) -> int:
    categories = _service(args).storage.categories.list()
    for category in categories:
        print(f"- {category}")
    return 0


@safe_command
def command_category_remove(args: argparse.Namespace) -> int:
    _service(args).remove_category(args.name)
    print(f"[삭제 완료] category={args.name.strip()}")
    return 0


@safe_command
def command_update(args: argparse.Namespace) -> int:
    changes = {
        key: value
        for key, value in {
            "date": args.date,
            "type": args.transaction_type,
            "category": args.category,
            "amount": args.amount,
            "memo": args.memo,
            "tags": args.tags,
        }.items()
        if value is not None
    }
    updated = _service(args).update_transaction(args.id, **changes)
    print(f"[수정 완료] id={updated.id}")
    return 0


@safe_command
def command_delete(args: argparse.Namespace) -> int:
    _service(args).delete_transaction(args.id)
    print(f"[삭제 완료] id={args.id}")
    return 0


@safe_command
def command_import(args: argparse.Namespace) -> int:
    imported, skipped, errors = _service(args).import_csv(Path(args.source), atomic=args.atomic)
    print(f"[완료] imported={imported}, skipped={skipped}")
    for error in errors:
        print(f"[건너뜀] {error}")
    return 0


@safe_command
def command_export(args: argparse.Namespace) -> int:
    count = _service(args).export_csv(
        Path(args.output), month=args.month, date_from=args.date_from, date_to=args.date_to
    )
    print(f"[완료] {args.output} ({count} records)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m budget_app", description="JSONL 파일 기반 용돈 기입장"
    )
    parser.add_argument("--data-dir", default="./data", help="저장 폴더 (기본값: ./data)")
    commands = parser.add_subparsers(dest="command", title="commands")

    add_parser = commands.add_parser("add", help="거래를 대화형으로 추가")
    add_parser.set_defaults(handler=command_add)

    list_parser = commands.add_parser("list", help="최신순 거래 목록")
    list_parser.add_argument("--limit", type=_positive_int, default=20, help="최대 출력 건수 (기본값: 20)")
    list_parser.set_defaults(handler=command_list)

    search_parser = commands.add_parser("search", help="조건으로 거래 검색")
    search_parser.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    search_parser.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    search_parser.add_argument("--category", help="카테고리")
    search_parser.add_argument("--type", dest="transaction_type", choices=("income", "expense"))
    search_parser.add_argument("--q", dest="query", help="메모 키워드")
    search_parser.add_argument("--tag", help="태그 완전 일치")
    search_parser.set_defaults(handler=command_search)

    summary_parser = commands.add_parser("summary", help="월별 요약")
    summary_parser.add_argument("--month", required=True, help="대상 월 YYYY-MM")
    summary_parser.add_argument("--top", type=_positive_int, default=3, help="지출 카테고리 순위 수")
    summary_parser.set_defaults(handler=command_summary)

    budget_parser = commands.add_parser("budget", help="월 예산 설정/조회")
    budget_commands = budget_parser.add_subparsers(dest="budget_command", required=True)
    budget_set = budget_commands.add_parser("set", help="예산 설정")
    budget_set.add_argument("--month", required=True, help="대상 월 YYYY-MM")
    budget_set.add_argument("--amount", required=True, type=_positive_int, help="양수 정수 금액")
    budget_set.set_defaults(handler=command_budget_set)
    budget_get = budget_commands.add_parser("get", help="예산 조회")
    budget_get.add_argument("--month", required=True, help="대상 월 YYYY-MM")
    budget_get.set_defaults(handler=command_budget_get)

    category_parser = commands.add_parser("category", help="카테고리 관리")
    category_commands = category_parser.add_subparsers(dest="category_command", required=True)
    category_add = category_commands.add_parser("add", help="카테고리 추가")
    category_add.add_argument("--name", help="생략하면 대화형 입력")
    category_add.set_defaults(handler=command_category_add)
    category_list = category_commands.add_parser("list", help="카테고리 목록")
    category_list.set_defaults(handler=command_category_list)
    category_remove = category_commands.add_parser("remove", help="카테고리 삭제")
    category_remove.add_argument("--name", required=True)
    category_remove.set_defaults(handler=command_category_remove)

    update_parser = commands.add_parser("update", help="옵션 기반 거래 수정")
    update_parser.add_argument("--id", required=True)
    update_parser.add_argument("--date")
    update_parser.add_argument("--type", dest="transaction_type", choices=("income", "expense"))
    update_parser.add_argument("--category")
    update_parser.add_argument("--amount", type=_positive_int)
    update_parser.add_argument("--memo", help="빈 문자열로 메모 삭제 가능")
    update_parser.add_argument("--tags", help="쉼표 구분, 빈 문자열로 태그 삭제 가능")
    update_parser.set_defaults(handler=command_update)

    delete_parser = commands.add_parser("delete", help="id로 거래 삭제")
    delete_parser.add_argument("--id", required=True)
    delete_parser.set_defaults(handler=command_delete)

    import_parser = commands.add_parser("import", help="CSV 거래 가져오기")
    import_parser.add_argument("--from", dest="source", required=True, help="입력 CSV 경로")
    import_parser.add_argument(
        "--atomic", action="store_true", help="전체 행이 유효한 경우에만 저장 (실패 시 전체 롤백)"
    )
    import_parser.set_defaults(handler=command_import)

    export_parser = commands.add_parser("export", help="조건에 맞는 거래를 CSV로 내보내기")
    export_parser.add_argument("--out", dest="output", required=True, help="출력 CSV 경로")
    export_parser.add_argument("--month", help="대상 월 YYYY-MM")
    export_parser.add_argument("--from", dest="date_from", help="시작일 YYYY-MM-DD")
    export_parser.add_argument("--to", dest="date_to", help="종료일 YYYY-MM-DD")
    export_parser.set_defaults(handler=command_export)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return int(handler(args))
    except KeyboardInterrupt:
        print("\n[오류] 사용자 요청으로 작업을 취소했습니다.", file=sys.stderr)
        return 130
