# 나만의 용돈 기입장

수입과 지출을 기록하고, 한 달 동안 얼마를 썼고 얼마가 남았는지 확인하는 Python 콘솔 가계부입니다. 지출이 큰 카테고리를 찾아보고 월 예산을 넘으면 초과 금액도 확인할 수 있습니다.

<a name="cli-실행-로그"></a>

[한 줄씩 따라 하는 시연](docs/DEMO.md) · [실제 터미널 실행 기록](docs/DEMO.md#cli-실행-로그)

## 빠른 시작

Python **3.10 이상**이면 외부 패키지가 필요 없습니다. 저장소 루트에서 실행하세요. `python` 명령이 없다면 `python3`를 사용합니다. 첫 줄은 시연용 가계부(`demo_data`, `demo_imported`)를 초기화하고 이전 `demo_export.csv`를 지웁니다. 기본 가계부 `./data`는 바꾸지 않습니다.

```bash
python -m scripts.prepare_demo
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
```

예시 거래 6건의 9월 결산은 수입 **3,000,000원**, 지출 **810,000원**, 잔액 **2,190,000원**입니다. 예산은 800,000원이므로 10,000원 초과 경고가 표시됩니다.

내 거래는 `python -m budget_app add`로 기록합니다. 새 가계부에는 기본 카테고리만 있고 거래가 없어, 처음 `list`를 실행하면 ‘데이터 없음’이 나옵니다. 명령과 옵션은 `python -m budget_app --help` 또는 각 명령의 `--help`로 확인하세요.

## 주요 기능

| 작업 | 명령 | 동작 |
| --- | --- | --- |
| 거래 기록·정정 | `add` · `update` · `delete` | 대화형으로 입력하면 거래 ID가 발급됩니다. 수정·삭제는 `--id`로 대상을 지정하며, 수정할 필드만 옵션으로 전달합니다. 없는 ID는 오류로 안내합니다. |
| 조회·검색 | `list` · `search` | 최근 **등록 순서**로 표시합니다. 목록 건수는 `--limit`으로 정하고, 검색은 기간·카테고리·유형·메모·태그를 조합합니다. |
| 월별 결산·예산 | `summary` · `budget set/get` | 수입·지출·잔액과 지출 상위 카테고리를 계산합니다. 예산이 있으면 사용률과 초과 금액도 표시합니다. |
| 카테고리 관리 | `category add/list/remove` | 분류를 추가·조회·삭제합니다. 거래에서 사용 중인 카테고리는 삭제할 수 없습니다. |
| CSV 교환 | `export` · `import` | 월 또는 기간을 골라 내보내고, 다른 가계부로 가져온 건수와 건너뛴 건수를 확인합니다. |

<a name="평가-시연-위에서부터-한-줄씩-실행"></a>

<details>
<summary>핵심 명령 8개 직접 실행하기 (macOS·Linux)</summary>

첫 줄부터 순서대로 실행하면 됩니다. `printf`는 대화형 `add`에 여섯 개의 답을 차례로 건넵니다. 수정·삭제에는 고정된 예시 ID를 사용하므로 출력된 ID를 복사할 필요가 없습니다.

```bash
python -m scripts.prepare_demo
printf '%s\n' 2026-09-12 expense food 5500 '커피' 'drink,cafe' | python -m budget_app --data-dir ./demo_data add
python -m budget_app --data-dir ./demo_data list --limit 3
python -m budget_app --data-dir ./demo_data search --category food --q 점심 --tag school
python -m budget_app --data-dir ./demo_data update --id TX-DEMO-005 --amount 75000 --memo "영화 할인 적용"
python -m budget_app --data-dir ./demo_data delete --id TX-DEMO-006
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
python -m budget_app --data-dir ./demo_data export --out ./demo_export.csv --month 2026-09
python -m budget_app --data-dir ./demo_imported import --from ./demo_export.csv
```

이 순서대로 실행한 뒤의 9월 지출은 765,500원이고, 마지막 가져오기 결과는 `imported=6, skipped=0`입니다.

</details>

## 저장 형식

**내부 저장은 UTF-8 JSONL**입니다. 한 줄이 독립된 레코드라 거래 전체를 메모리에 올리지 않고 읽을 수 있고, 태그를 배열로 보존합니다. 기본 경로는 `./data`이며, 다른 가계부를 쓸 때는 `--data-dir`을 명령 앞에 둡니다.

| 파일 | 저장 내용 |
| --- | --- |
| `data/transactions.jsonl` | `id`, `type`, `date`, `amount`, `category`, `memo`, `tags` |
| `data/categories.jsonl` | 등록된 카테고리 이름(`name`) |
| `data/budgets.jsonl` | 예산을 적용할 월(`month`)과 금액(`amount`) |

**외부 교환은 UTF-8 CSV**입니다. 아래 여섯 열의 헤더가 필요합니다. 날짜는 `YYYY-MM-DD`, 유형은 `income` 또는 `expense`, 카테고리는 등록된 이름, 금액은 양의 정수입니다. 메모와 태그 값은 비워도 되며 여러 태그는 한 셀에 넣습니다.

```csv
date,type,category,amount,memo,tags
2026-09-05,expense,food,15000,학교 점심,"meal,school"
```

기본 `import`는 값이 잘못된 행의 번호·원인을 알려 주고 정상 행은 저장합니다. `--atomic`을 붙이면 한 행이라도 잘못됐을 때 신규 거래를 한 건도 반영하지 않습니다.

## 구현 구조

- [모델](budget_app/models.py) · [서비스](budget_app/services.py): `Transaction` 데이터클래스가 거래 필드와 값의 범위를 정의하고, 서비스가 검색·집계·예산 규칙을 처리합니다. 타입 힌트로 반환값이 거래 한 건인지 거래를 순회하는 `Iterator[Transaction]`인지 구분합니다.
- [저장소](budget_app/repositories.py): `yield`로 한 번에 한 건씩 읽습니다. 최신 목록은 파일 끝에서 필요한 만큼만 읽고, 수정·삭제는 임시 파일 기록을 마친 뒤 `os.replace()`로 원본을 교체합니다.
- [CLI](budget_app/cli.py) · [데코레이터](budget_app/decorators.py): `argparse`가 명령·옵션을 읽고, `@safe_command`가 실행 상태와 시간을 `app.log`에 남깁니다. 정상 종료 코드는 0이고, 처리 중 오류는 원인·해결 힌트와 0이 아닌 종료 코드로 전달합니다.

## 테스트와 설계 자료

전체 테스트는 `python -m unittest discover -v`로 실행합니다. [CSV 가져오기 테스트](tests/test_csv_atomic.py)에서는 부분 반영과 전체 롤백을 같은 입력으로 비교합니다.

[저장 형식 선택과 10만 건 병목·개선안](docs/DESIGN_AND_PERFORMANCE.md) · [측정 원본](docs/evidence/profile-100k.json) · [재현 스크립트](scripts/benchmark_100k.py)
