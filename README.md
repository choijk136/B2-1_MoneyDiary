# 나만의 용돈 기입장

Python 3.10 이상과 표준 라이브러리만 사용하는 JSONL 기반 콘솔 가계부입니다. 거래 CRUD, 스트리밍 조회/검색, 월별 집계, 예산, 카테고리, CSV 가져오기·내보내기를 지원합니다.

## 평가 #15 · #16 제출 근거

| 항목 | 이 버전에서 확인할 결과 | 근거 |
| --- | --- | --- |
| **#15 — 100k 병목 분석** | 실제 100,000건, 각 연산 3회 중앙값. 식비 검색 **0.500초**(거래 100,000건 변환), 가장 오래된 거래 한 건 수정 **2.393초**(200,000건 변환·100,000건 재작성). 보고서에 병목별 개선안과 검증 기준을 구분했습니다. | [측정 방법·수치·개선안](docs/DESIGN_AND_PERFORMANCE.md) · [개별 측정값과 cProfile 원본](docs/evidence/profile-100k.json) · [재현 스크립트](scripts/benchmark_100k.py) |
| **#16 — CSV 전체 롤백 옵션** | 같은 [정상–오류–정상 CSV](tests/fixtures/mixed_import.csv)에서 기본 모드는 **2건 저장·1건 건너뜀**, `--atomic`은 **0건 저장·종료 코드 2**. 기존 거래 파일이 한 바이트도 바뀌지 않는지 검사합니다. | [CSV 검증·모드 선택](budget_app/services.py#L194) · [임시 파일과 단일 교체](budget_app/repositories.py#L65) · [성공·실패 테스트](tests/test_csv_atomic.py) |

#15를 직접 측정하려면 다음 한 줄을 실행합니다. 임시 폴더에서 실행되므로 시연 데이터는 바뀌지 않습니다.

```bash
python -m scripts.benchmark_100k --records 100000 --repeat 3
```

#16을 시연하려면 다음 한 줄을 실행합니다. 테스트가 의도적인 오류를 확인하므로 정상 검증 결과는 `OK`입니다.

```bash
python -m unittest -v tests.test_csv_atomic
```

전체 검증은 `python -m unittest discover -v`입니다. [제출 근거 검사](tests/test_submission_evidence.py)는 긴 벤치마크를 다시 돌리지 않고도 README 링크의 대상 파일이 빠졌거나 측정 이후 코드가 달라졌는지 확인합니다.

## 평가 시연: 위에서부터 한 줄씩 실행

모든 명령은 **저장소 루트**에서 실행합니다. 시연 데이터는 기본 데이터(`./data`)와 분리된 `./demo_data`에 저장되므로 기존 자료에 영향을 주지 않습니다.

### 1. 예시 데이터 준비

아래 명령은 고정 ID를 가진 거래 6건, 기본 카테고리, 2026년 9월 예산을 생성합니다. 여러 번 실행해도 데이터가 중복되지 않으므로 시연 직전에 항상 먼저 실행합니다.

```bash
python -m scripts.prepare_demo
```

예상 결과:

```text
[시연 준비 완료]
- 예시 거래: 6건
- 월 예산: 2026-09 / 800,000원
- 데이터 폴더: demo_data
```

### 2. 도움말과 최신순 목록

```bash
python -m budget_app --help
```

```bash
python -m budget_app --data-dir ./demo_data list --limit 6
```

`TX-DEMO-006`부터 `TX-DEMO-001`까지 최신 등록순으로 출력됩니다. 저장소가 파일 끝에서부터 거래를 한 건씩 `yield`하는 스트리밍 동작입니다.

### 3. 복합 조건 검색

```bash
python -m budget_app --data-dir ./demo_data search --from 2026-09-01 --to 2026-09-30 --category food --type expense --q 점심 --tag school
```

모든 조건을 만족하는 `TX-DEMO-003 | 학교 점심` 한 건이 출력됩니다.

### 4. 월별 요약과 예산 초과 경고

```bash
python -m budget_app --data-dir ./demo_data budget get --month 2026-09
```

```bash
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
```

총수입 3,000,000원, 총지출 810,000원, 잔액 2,190,000원과 카테고리별 지출 TOP 3가 출력됩니다. 설정 예산 800,000원보다 10,000원 초과했으므로 경고도 표시됩니다.

### 5. 카테고리 추가·조회·삭제

```bash
python -m budget_app --data-dir ./demo_data category add --name books
```

```bash
python -m budget_app --data-dir ./demo_data category list
```

```bash
python -m budget_app --data-dir ./demo_data category remove --name books
```

사용하지 않는 `books` 카테고리가 추가되고 목록에 표시된 뒤 정상 삭제됩니다.

### 6. 대화형 거래 추가

```bash
python -m budget_app --data-dir ./demo_data add
```

프롬프트가 나타나면 다음 값을 한 줄씩 입력합니다.

```text
2026-09-12
expense
food
5500
커피
drink,cafe
```

`[저장 완료] id=TX-...`가 출력됩니다. ID는 중복을 방지하기 위해 자동 생성됩니다.

### 7. 고정 ID 거래 수정과 삭제

```bash
python -m budget_app --data-dir ./demo_data update --id TX-DEMO-005 --amount 75000 --memo "영화 할인 적용"
```

```bash
python -m budget_app --data-dir ./demo_data delete --id TX-DEMO-006
```

```bash
python -m budget_app --data-dir ./demo_data list --limit 10
```

목록에서 `TX-DEMO-005`의 금액과 메모가 바뀌고 `TX-DEMO-006`이 사라진 것을 확인합니다. 두 작업은 임시 파일을 `fsync`한 뒤 `os.replace`로 원자적으로 반영합니다.

### 8. CSV 내보내기와 가져오기

```bash
python -m budget_app --data-dir ./demo_data export --out ./demo_export.csv --month 2026-09
```

```bash
python -m budget_app --data-dir ./demo_imported import --from ./demo_export.csv --atomic
```

```bash
python -m budget_app --data-dir ./demo_imported list --limit 10
```

첫 명령의 내보내기 건수와 두 번째 명령의 `imported` 건수가 일치하고, 마지막 목록에 CSV로 옮긴 거래가 표시됩니다. 이 단계는 모든 행이 유효할 때만 저장하는 `--atomic` 모드를 사용합니다.

### 9. 초기화

처음 상태로 되돌리려면 `python -m scripts.prepare_demo`를 다시 실행하면 됩니다.

## 실행

저장소 루트에서 실행합니다. 외부 패키지 설치는 필요하지 않습니다.

```bash
python -m budget_app --help
python -m budget_app <command> --help
```

기본 저장 폴더는 `./data`입니다. 다른 폴더를 쓰려면 **명령 앞에** 전역 옵션을 지정합니다.

```bash
python -m budget_app --data-dir ./my_data list --limit 10
```

첫 실행 시 폴더와 저장 파일이 자동 생성됩니다. 카테고리 파일이 비어 있으면 `education`, `food`, `housing`, `leisure`, `medical`, `other`, `salary`, `transport`가 자동 등록됩니다.

## 주요 명령

### 거래 추가와 조회

`add`는 날짜, 타입, 카테고리, 금액, 메모, 태그를 순서대로 묻습니다. 잘못된 값은 안내 후 다시 입력받습니다.

```bash
python -m budget_app add
python -m budget_app list --limit 20
python -m budget_app search --from 2024-01-01 --to 2024-01-31
python -m budget_app search --category food --type expense --q 점심 --tag meal
```

`list`와 `search` 결과는 파일 끝부터 읽는 제너레이터를 사용해 최신 등록순으로 출력합니다. 출력 포맷터도 행을 하나씩 `yield`하므로 검색 결과 전체를 리스트로 적재하지 않습니다.

### 거래 수정과 삭제

수정 방식은 **옵션 기반**으로 고정했습니다. `--id`와 변경할 옵션을 하나 이상 입력합니다. `--memo ""` 또는 `--tags ""`로 값을 지울 수 있습니다.

```bash
python -m budget_app update --id TX-ABC123 --amount 18000 --memo "저녁"
python -m budget_app update --id TX-ABC123 --category transport --tags "bus,school"
python -m budget_app delete --id TX-ABC123
```

수정/삭제는 같은 폴더에 임시 파일을 완전히 기록하고 `fsync`한 뒤 `os.replace`로 원본을 원자적으로 교체합니다.

### 월별 요약과 예산

```bash
python -m budget_app budget set --month 2024-01 --amount 500000
python -m budget_app budget get --month 2024-01
python -m budget_app summary --month 2024-01 --top 3
```

요약에는 총수입, 총지출, 잔액, 지출 카테고리 TOP N이 출력됩니다. 예산이 있으면 사용률과 초과 경고도 표시됩니다.

### 카테고리

```bash
python -m budget_app category list
python -m budget_app category add
python -m budget_app category add --name books
python -m budget_app category remove --name books
```

거래에서 사용 중인 카테고리는 삭제할 수 없습니다. 먼저 해당 거래를 `update`해야 합니다.

### CSV 가져오기·내보내기

```bash
python -m budget_app import --from ./import.csv
python -m budget_app export --out ./export.csv --month 2024-01
python -m budget_app export --out ./export.csv --from 2024-01-01 --to 2024-01-31
```

내보내기는 `--month` 또는 기간 조건(`--from`, `--to`)을 하나 이상 요구합니다. `--month`와 기간 조건은 동시에 사용할 수 없습니다.

**CSV 가져오기 정책**

| 실행 모드 | 정상–오류–정상 예시에서의 실제 결과 |
| --- | --- |
| 기본 (옵션 없음) | 유효한 두 행은 저장합니다. `[완료] imported=2, skipped=1`과 `[건너뜀] 3행: 금액은 양수 정수여야 합니다.`를 출력합니다. |
| `--atomic` (전체 성공 또는 전체 롤백) | 정상 행도 원본에 즉시 추가하지 않습니다. 한 행이라도 잘못되면 `[오류] CSV 전체 롤백: imported=0`과 행 번호·원인을 출력하고 **종료 코드 2**를 반환합니다. 모두 유효하면 원본과 신규 거래를 합친 임시 파일을 한 번만 교체합니다. |

실제 CLI 확인: 고정 시연 거래 **6건**에 위 예시 CSV를 가져오자 원자 모드는 **6건 → 6건**이었고 전후 `transactions.jsonl`의 SHA-256이 동일했습니다(`f8eb47ae4ee8…`). 같은 초기 상태에서 기본 모드는 **6건 → 8건**이었습니다.

CSV는 한 번만 읽습니다. UTF-8 BOM과 인용된 줄바꿈을 지원하고, 여러 줄 레코드의 오류 번호는 원본의 **마지막 물리 줄**입니다. 따옴표가 닫히지 않아 레코드 경계를 알 수 없는 경우에는 읽기를 중단합니다. 이때 기본 모드는 앞서 저장한 행을 유지하고, 원자 모드는 앞선 행까지 반영하지 않습니다.

원자 모드는 원본과 **같은 디렉터리**에 임시 파일을 생성합니다. 기존 데이터를 복사한 뒤 검증된 행을 쓰고, CSV 끝까지 오류가 없을 때만 `flush → fsync → close → os.replace`로 공개합니다. 쓰기·교체 실패 시 CLI는 비정상 종료하고 원본 거래 파일은 그대로입니다. 적용 범위는 단일 작성자의 `transactions.jsonl`이며 명령 로그나 여러 프로세스 간 동시 쓰기까지 롤백하는 기능은 아닙니다.

CSV는 UTF-8, 헤더 포함 형식이며 스키마는 다음과 같습니다.

| column | required | 설명 |
| --- | --- | --- |
| `date` | Y | `YYYY-MM-DD` |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 양수 정수 |
| `memo` | N | 문자열 |
| `tags` | N | 쉼표로 구분한 문자열(CSV 규칙에 따라 따옴표 처리) |

## 저장 파일

세 데이터 파일은 모두 UTF-8 JSONL이며, 한 줄이 하나의 JSON 객체입니다.

| 파일 | JSON 필드 | 기록 방식 |
| --- | --- | --- |
| `data/transactions.jsonl` | `id`, `type`, `date`, `amount`, `category`, `memo`, `tags` | add는 append+fsync, update/delete는 원자적 재작성 |
| `data/categories.jsonl` | `name` | 원자적 재작성 |
| `data/budgets.jsonl` | `month`, `amount` | 원자적 재작성 |

`data/app.log`에는 데코레이터가 명령명, 성공/오류 상태, 실행 시간을 기록합니다. 데이터 파일을 직접 고치기 전에는 폴더 전체를 백업하는 것을 권장합니다.

## 구조와 설계

```text
budget_app/
├── cli.py           # argparse, 대화형 입력, 출력과 종료 코드
├── models.py        # dataclass와 값 검증
├── repositories.py  # JSONL 스트리밍, 파일 I/O와 원자적 교체
├── services.py      # CRUD, 검색, 집계, CSV 업무 규칙
├── decorators.py    # 공통 예외 처리, 실행 로그, 시간 측정
└── formatters.py    # 외부 라이브러리 없는 표 정렬
```

- `yield` 기반 저장소 API는 한 시점에 한 거래만 메모리에 유지합니다. 최신순 조회도 블록 단위 역방향 읽기라 파일 크기가 커져도 전체 파일을 읽지 않습니다.
- `@safe_command` 데코레이터가 예외를 원인·힌트·비정상 종료 코드로 변환하고 실행 로그/시간 측정을 분리합니다. 사용자에게 스택트레이스를 노출하지 않습니다.
- 공개 함수와 데이터 모델에 타입 힌트를 적용해 CLI·서비스·저장소 사이의 입출력 계약을 명확히 했습니다.
- 각 명령의 `--help`를 지원하며 옵션 이름은 `--limit`, `--from`처럼 이중 하이픈으로 통일했습니다.

