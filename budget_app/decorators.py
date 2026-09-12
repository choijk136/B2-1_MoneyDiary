"""CLI 공통 관심사를 분리한 데코레이터."""

from __future__ import annotations

import csv
import functools
import json
import sys
import time
from argparse import Namespace
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .errors import BudgetAppError

Command = Callable[[Namespace], int]


def _write_log(data_dir: Path, command: str, elapsed: float, status: str) -> None:
    """로그 실패가 본 작업을 실패시키지 않도록 best-effort로 기록한다."""
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with (data_dir / "app.log").open("a", encoding="utf-8") as file:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            file.write(f"{timestamp}\t{command}\t{status}\t{elapsed:.6f}s\n")
    except OSError:
        pass


def safe_command(function: Command) -> Command:
    """실행 시간/로그/예외 메시지/종료 코드를 모든 명령에 공통 적용한다."""

    @functools.wraps(function)
    def wrapper(args: Namespace) -> int:
        started = time.perf_counter()
        status = "ok"
        try:
            return function(args)
        except BudgetAppError as exc:
            status = "domain_error"
            print(f"[오류] {exc.message}", file=sys.stderr)
            print(f"[힌트] {exc.hint}", file=sys.stderr)
            return 2
        except (OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
            status = "io_error"
            print(f"[오류] 파일을 처리할 수 없습니다: {exc}", file=sys.stderr)
            print("[힌트] 파일 경로, 권한, UTF-8 형식을 확인하세요.", file=sys.stderr)
            return 3
        except Exception as exc:  # CLI 경계에서 스택트레이스 노출 방지
            status = "unexpected_error"
            print(f"[오류] 명령을 완료하지 못했습니다: {exc}", file=sys.stderr)
            print("[힌트] 입력과 저장 파일을 확인한 뒤 다시 시도하세요.", file=sys.stderr)
            return 4
        finally:
            elapsed = time.perf_counter() - started
            _write_log(Path(args.data_dir), function.__name__, elapsed, status)

    return wrapper

