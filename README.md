# 나만의 용돈 기입장

수입과 지출을 기록하고, 이번 달에 얼마가 남았는지와 어디에 많이 썼는지를 터미널에서 확인하는 Python 가계부입니다. 거래 내역, 카테고리, 월 예산은 파일에 저장되어 프로그램을 다시 실행해도 그대로 남습니다.

## 주요 기능

| 작업 | 명령 | 할 수 있는 일 |
| --- | --- | --- |
| 거래 기록·조회 | `add`, `list` | 안내에 따라 거래를 입력하면 고유 ID가 발급됩니다. 목록은 최근 **등록한 순서**로 표시하며 `--limit`으로 건수를 정합니다. |
| 조건 검색 | `search` | 기간, 카테고리, 수입·지출 유형, 메모 키워드, 태그를 조합해 원하는 내역만 찾습니다. |
| 월별 결산 | `summary`, `budget set/get` | 월별 수입·지출·잔액과 지출 상위 카테고리를 확인합니다. 예산을 설정하면 사용률과 초과 금액도 표시합니다. |
| 거래 정정 | `update`, `delete` | `--id`로 대상을 고릅니다. 수정은 바꿀 항목만 옵션으로 지정하며, 없는 ID는 오류로 안내합니다. |
| 카테고리 관리 | `category add/list/remove` | 분류를 추가·조회·삭제합니다. 거래에서 사용 중인 카테고리는 삭제할 수 없습니다. |
| 파일 교환 | `export`, `import` | 월이나 기간을 지정해 CSV로 내보내거나, 기존 CSV의 거래를 가져옵니다. |

<a name="평가-시연-위에서부터-한-줄씩-실행"></a>

## 로컬 실행

**Python 3.10 이상**이면 됩니다. 외부 패키지 설치 없이 `README.md`가 있는 폴더에서 실행합니다. 환경에 따라 `python` 대신 `python3`를 사용하세요.

```bash
python -m budget_app --help
```

내 거래를 기록하려면 `python -m budget_app add`를 실행합니다. 기본 저장 위치는 `./data`입니다. 처음에는 기본 카테고리만 있고 거래가 없어, 목록에 ‘데이터 없음’이 나오는 것이 정상입니다. 다른 저장 위치는 아래처럼 **명령 앞에** `--data-dir`로 지정합니다.

### 예시 거래로 시작하기

첫 줄은 2026년 9월 거래 6건과 예산 800,000원을 준비합니다. 다시 실행하면 시연 폴더(`demo_data`, `demo_imported`)의 가계부 파일을 초기화하고 `demo_export.csv`를 지웁니다. 기본 `./data`에는 영향을 주지 않습니다.

```bash
python -m scripts.prepare_demo
```

```bash
python -m budget_app --data-dir ./demo_data list --limit 6
```

```bash
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
```

예시의 9월 수입은 **3,000,000원**, 지출은 **810,000원**, 잔액은 **2,190,000원**입니다. 지출이 예산을 10,000원 넘었다는 경고도 확인할 수 있습니다.

<details>
<summary>전체 시연 펼치기 · 검색부터 CSV 가져오기까지 한 줄씩 실행</summary>

위에서 예시 데이터를 준비한 뒤 아래 명령을 순서대로 한 번씩 실행합니다.

**1. 학교에서 쓴 점심값 찾기** — 기간·분류·유형·메모·태그에 모두 맞는 `TX-DEMO-003` 한 건이 나옵니다.

```bash
python -m budget_app --data-dir ./demo_data search --from 2026-09-01 --to 2026-09-30 --category food --type expense --q 점심 --tag school
```

**2. 예산 변경** — 9월 예산을 900,000원으로 올리면 같은 지출의 사용률은 90.0%가 되고 초과 경고가 사라집니다.

```bash
python -m budget_app --data-dir ./demo_data budget set --month 2026-09 --amount 900000
```

```bash
python -m budget_app --data-dir ./demo_data budget get --month 2026-09
```

```bash
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
```

**3. 카테고리 관리** — 아직 거래가 없는 `books`를 추가하고 목록에서 확인한 뒤 삭제합니다.

```bash
python -m budget_app --data-dir ./demo_data category add --name books
```

```bash
python -m budget_app --data-dir ./demo_data category list
```

```bash
python -m budget_app --data-dir ./demo_data category remove --name books
```

**4. 거래 추가** — `add`는 날짜 → 유형 → 카테고리 → 금액 → 메모 → 태그 순서로 묻습니다. 아래 한 줄은 macOS·Linux 터미널에서 여섯 답을 전달해 커피값 5,500원을 등록합니다. 직접 입력할 때는 `python -m budget_app --data-dir ./demo_data add`만 실행하세요. 두 방식 중 하나만 사용합니다.

```bash
printf '%s\n' 2026-09-12 expense food 5500 '커피' 'drink,cafe' | python -m budget_app --data-dir ./demo_data add
```

**5. 거래 수정·삭제** — 예시 거래의 고정 ID를 사용합니다. 목록에서 영화 지출이 75,000원으로 바뀌고 장보기 내역이 사라지는지 확인합니다.

```bash
python -m budget_app --data-dir ./demo_data update --id TX-DEMO-005 --amount 75000 --memo "영화 할인 적용"
```

```bash
python -m budget_app --data-dir ./demo_data delete --id TX-DEMO-006
```

```bash
python -m budget_app --data-dir ./demo_data list --limit 6
```

**6. CSV 내보내기·가져오기** — 9월 거래를 CSV로 만들고 비어 있는 별도 가계부로 옮깁니다. 내보낸 6건과 가져온 6건이 일치해야 합니다.

```bash
python -m budget_app --data-dir ./demo_data export --out ./demo_export.csv --month 2026-09
```

```bash
python -m budget_app --data-dir ./demo_imported import --from ./demo_export.csv
```

```bash
python -m budget_app --data-dir ./demo_imported list --limit 6
```

</details>

## 저장 파일과 CSV 형식

내부 저장 형식은 UTF-8 **JSONL**입니다. 한 줄이 하나의 JSON 객체여서 거래를 한 건씩 읽을 수 있고, 태그 여러 개를 배열로 저장할 수 있습니다.

| 기본 경로 | 저장 내용 |
| --- | --- |
| `data/transactions.jsonl` | 거래 ID, 유형, 날짜, 금액, 카테고리, 메모, 태그 |
| `data/categories.jsonl` | 등록된 카테고리 이름 |
| `data/budgets.jsonl` | 월(`YYYY-MM`)과 예산 금액 |

가져오기·내보내기에는 UTF-8 **CSV**를 사용합니다. 헤더에는 아래 여섯 열이 모두 필요합니다. 날짜는 `YYYY-MM-DD`, 유형은 `income` 또는 `expense`, 카테고리는 등록된 이름, 금액은 양의 정수입니다. 메모와 태그의 **값**은 비워도 됩니다. 여러 태그는 예시처럼 한 셀에 넣습니다.

```csv
date,type,category,amount,memo,tags
2026-09-05,expense,food,15000,학교 점심,"meal,school"
```

`export`에는 `--month` 또는 기간 조건(`--from`, `--to`)이 필요합니다. 기본 `import`는 값이 잘못된 행의 번호와 이유를 알리고 정상 행은 저장합니다. 한 행이라도 잘못됐을 때 전체를 취소하려면 `--atomic`을 붙입니다.

## 사용 기술과 프로젝트 구조

| 모듈 | 역할 |
| --- | --- |
| [cli.py](budget_app/cli.py) · [formatters.py](budget_app/formatters.py) | `argparse`로 명령과 옵션을 받고 결과를 표로 출력합니다. 각 명령은 `--help`를 지원합니다. |
| [models.py](budget_app/models.py) | `Transaction` 데이터클래스와 타입 힌트로 거래 구조를 정의하고 날짜·유형·금액을 검증합니다. |
| [services.py](budget_app/services.py) | 거래 수정, 조건 검색, 월별 집계, 예산 및 카테고리 규칙을 처리합니다. |
| [repositories.py](budget_app/repositories.py) | `yield`로 파일 전체를 메모리에 올리지 않고 거래를 읽습니다. 수정·삭제는 임시 파일을 완성한 뒤 원본과 교체합니다. |
| [decorators.py](budget_app/decorators.py) | `@safe_command`가 오류 원인과 힌트를 표시하고 명령 상태·실행 시간을 `app.log`에 기록합니다. 정상 종료 코드는 0, 오류는 0이 아닌 값입니다. |

## 테스트와 참고 자료

```bash
python -m unittest discover -v
```

[저장 방식 선택과 10만 건 성능 분석](docs/DESIGN_AND_PERFORMANCE.md) · [측정 원본](docs/evidence/profile-100k.json) · [벤치마크 스크립트](scripts/benchmark_100k.py)
