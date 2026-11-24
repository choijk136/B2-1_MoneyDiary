"""항목 1 실습: Enter 한 번마다 독립된 임시 가계부에서 실제 CLI를 실행한다."""

import argparse
import csv
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from tempfile import TemporaryDirectory

from scripts.prepare_demo import prepare_demo

ROOT = Path(__file__).resolve().parents[1]
MONTH = "2026-09"
DATE = "2026-09-12"


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


class Stage:
    def __init__(self, path: Path, full: bool, show_codes: bool = False):
        self.path = path
        self.full = full
        self.show_codes = show_codes

    def cli(self, *args: str, book: str = "ledger", inputs: tuple[str, ...] = (),
            rc: int = 0, expect: tuple[str, ...] = ()) -> str:
        argv = ["-m", "budget_app", "--data-dir", book, *args]
        print("$", shlex.join(["python", *argv]))
        if inputs:
            print("  입력:", " → ".join(inputs))
        result = subprocess.run(
            [sys.executable, *argv], cwd=self.path,
            env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8"},
            input="\n".join(inputs) + ("\n" if inputs else ""), encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20,
        )
        output = result.stdout
        for line in output.splitlines():
            if not self.full and inputs:
                # Piped input puts prompts and the final status on the same line.
                positions = [line.find(mark) for mark in ("[저장 완료]", "[오류]") if mark in line]
                if positions:
                    line = line[min(positions):]
            if self.full or (line.strip() and not line.startswith(("ID ", "----"))):
                print(" ", line)
        if self.full or self.show_codes or rc != 0:
            print(f"  종료 코드: {result.returncode}")
        check(result.returncode == rc and "Traceback" not in output and all(s in output for s in expect),
              f"{args[0]} 결과가 예상과 다릅니다 (예상 종료 코드 {rc}).")
        return output

    def seed(self) -> None:
        prepare_demo(self.path / "ledger", self.path / "copy", self.path / "seed-export.csv")

    def add(self, category: str = "food") -> str:
        output = self.cli("add", inputs=(DATE, "expense", category, "8000", "학교 점심", "meal,school"))
        match = re.search(r"\[저장 완료\] id=(TX-[A-Z0-9]+)", output)
        if match is None:
            raise RuntimeError("생성된 거래 ID가 없습니다.")
        return match.group(1)


def commands(s: Stage) -> None:
    tx = s.add()
    s.cli("list", "--limit", "1", expect=(tx, "8,000"))
    s.cli("update", "--id", tx, "--amount", "9000", expect=("[수정 완료]", tx))
    s.cli("search", "--q", "점심", "--tag", "school", expect=(tx, "9,000"))
    s.cli("summary", "--month", MONTH, "--top", "1", expect=("총 지출: 9,000원",))
    s.cli("export", "--out", "lunch.csv", "--month", MONTH, expect=("(1 records)",))
    s.cli("import", "--from", "lunch.csv", book="copy", expect=("imported=1, skipped=0",))
    s.cli("delete", "--id", tx, expect=("[삭제 완료]", tx))
    s.cli("list", "--limit", "1", expect=("데이터 없음",))
    s.cli("list", "--limit", "1", book="copy", expect=("학교 점심", "9,000"))


def persistence(s: Stage) -> None:
    s.cli("category", "add", "--name", "campus")
    tx = s.add("campus")
    s.cli("budget", "set", "--month", MONTH, "--amount", "10000")
    print("  저장된 세 파일에서 직접 읽은 레코드:")
    for name, key, expected in (("transactions", "id", tx), ("categories", "name", "campus"),
                                ("budgets", "amount", 10000)):
        filename = f"{name}.jsonl"
        records = [json.loads(row) for row in (s.path / "ledger" / filename).read_text(encoding="utf-8").splitlines()]
        record = next((r for r in records if r.get(key) == expected), None)
        check(record is not None, f"{filename}: 저장 실패")
        print(f"  {filename}: {json.dumps(record, ensure_ascii=False)}")
    print("  새 Python 프로세스에서 다시 조회:")
    s.cli("search", "--category", "campus", expect=(tx, "8,000"))
    s.cli("category", "list", expect=("- campus",))
    s.cli("budget", "get", "--month", MONTH, expect=("10,000원",))


def categories(s: Stage) -> None:
    s.seed()
    s.cli("category", "add", "--name", "books", expect=("category=books",))
    s.cli("category", "list", expect=("- books",))
    s.cli("category", "remove", "--name", "books", expect=("[삭제 완료]",))
    print("  거래에 사용 중인 food는 삭제가 거부되어야 합니다.")
    s.cli("category", "remove", "--name", "food", rc=2, expect=("사용 중인", "[힌트]"))
    remaining = s.cli("category", "list", expect=("- food",))
    check("- books" not in remaining, "삭제한 카테고리가 남아 있습니다.")


def budget(s: Stage) -> None:
    s.seed()
    for amount, usage in (("900000", "90.0%"), ("675000", "120.0%")):
        s.cli("budget", "set", "--month", MONTH, "--amount", amount)
        s.cli("budget", "get", "--month", MONTH, expect=(f"{int(amount):,}원",))
        report = s.cli("summary", "--month", MONTH, "--top", "1", expect=("총 지출: 810,000원", usage))
        check(("135,000원 초과" in report) if amount == "675000" else ("[경고]" not in report),
              "예산 경고가 지출과 일치하지 않습니다.")


def csv_schema(s: Stage) -> None:
    s.add()
    s.cli("export", "--out", "sample.csv", "--month", MONTH, expect=("(1 records)",))
    path = s.path / "sample.csv"
    print("  sample.csv 실제 내용 (UTF-8):\n" + path.read_bytes().decode("utf-8").rstrip())
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    check(rows == [["date", "type", "category", "amount", "memo", "tags"],
                   [DATE, "expense", "food", "8000", "학교 점심", "meal,school"]], "CSV 스키마/값 불일치")
    s.cli("import", "--from", "sample.csv", book="copy", expect=("imported=1, skipped=0",))
    s.cli("search", "--tag", "school", book="copy", expect=("학교 점심", "8,000", "meal"))


def errors(s: Stage) -> None:
    print("  잘못된 날짜를 입력한 뒤 올바른 날짜로 재입력합니다.")
    s.cli("add", inputs=("2026-02-30", DATE, "expense", "food", "8000", "학교 점심", "meal"),
          expect=("[오류]", "[힌트]", "[저장 완료]"))
    print("  UTF-8이 아닌 CSV로 파일 오류를 재현합니다.")
    (s.path / "bad.csv").write_bytes(bytes([255, 255]))
    s.cli("import", "--from", "bad.csv", rc=3, expect=("[오류]", "[힌트]", "UTF-8"))


def exit_codes(s: Stage) -> None:
    s.cli("list", "--limit", "1", expect=("데이터 없음",))
    s.cli("delete", "--id", "TX-NOT-FOUND", rc=2, expect=("거래를 찾을 수 없습니다",))
    (s.path / "bad.csv").write_bytes(bytes([255, 255]))
    s.cli("import", "--from", "bad.csv", rc=3, expect=("[오류]",))


STEPS = (
    ("핵심 명령 8개", "원본에서 삭제해도 CSV로 옮긴 9,000원 거래는 복사본에 남습니다.", commands),
    ("재실행 후 데이터 유지", "거래·카테고리·예산을 파일과 새 프로세스 양쪽에서 확인합니다.", persistence),
    ("카테고리 관리", "사용하지 않는 books는 삭제되고 사용 중인 food는 보호됩니다.", categories),
    ("예산과 월별 결산", "같은 지출 810,000원으로 예산 이내와 초과를 비교합니다.", budget),
    ("CSV 형식과 왕복", "한글 메모와 두 태그가 UTF-8 CSV를 거쳐 보존됩니다.", csv_schema),
    ("오류 안내", "입력 오류와 파일 오류에서 원인·힌트가 나오고 스택트레이스는 없어야 합니다.", errors),
    ("프로세스 종료 코드", "실제 반환값: 정상 0, 없는 거래 2, 파일 오류 3.", exit_codes),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto", action="store_true", help="Enter 없이 리허설")
    parser.add_argument("--full", action="store_true", help="표 머리글·구분선·빈 줄까지 표시")
    parser.add_argument("--step", type=int, choices=range(1, 8), help="지정한 항목만 시연")
    args = parser.parse_args()
    print("용돈 기입장 | 항목 1 실전 시연\n각 명령은 새 Python 프로세스에서 실행합니다. 개인 데이터는 사용하지 않습니다.")
    try:
        for i, (title, goal, action) in enumerate(STEPS, 1):
            if args.step is not None and i != args.step:
                continue
            print(f"\n{'─' * 56}\n[{i}/7] {title}\n확인할 점: {goal}")
            if not args.auto and input("Enter: 실행  /  q: 종료 > ").strip().lower() == "q":
                return 0
            with TemporaryDirectory(prefix="moneydiary-stage-") as directory:
                action(Stage(Path(directory), args.full, show_codes=(i == 7)))
            print(f"[확인 완료] {title}")
    except (KeyboardInterrupt, EOFError):
        print("\n시연을 중단했습니다.")
        return 130
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"[시연 중단] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
