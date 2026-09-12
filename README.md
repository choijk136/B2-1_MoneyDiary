# 나만의 용돈 기입장

Python 3.10 이상과 표준 라이브러리만 사용하는 JSONL 기반 콘솔 가계부입니다. 거래 CRUD, 스트리밍 조회/검색, 월별 집계, 예산, 카테고리, CSV 가져오기·내보내기를 지원합니다.

> 저장 포맷 비교·선정 근거와 100,000건 실측 프로파일링 결과는 [`docs/DESIGN_AND_PERFORMANCE.md`](docs/DESIGN_AND_PERFORMANCE.md)에 정리했습니다.

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
python -m budget_app --data-dir ./demo_imported import --from ./demo_export.csv
```

```bash
python -m budget_app --data-dir ./demo_imported list --limit 10
```

첫 명령의 내보내기 건수와 두 번째 명령의 `imported` 건수가 일치하고, 마지막 목록에 CSV로 옮긴 거래가 표시됩니다.

### 9. 자동 테스트

```bash
python -m unittest discover -v
```

모든 테스트가 `OK`로 끝나면 전체 시연이 완료됩니다. 처음 상태로 되돌리려면 `python -m scripts.prepare_demo`를 다시 실행하면 됩니다.

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

내보내기는 `--month` 또는 기간 조건(`--from`, `--to`)을 하나 이상 요구합니다. `--month`와 기간 조건은 동시에 사용할 수 없습니다. 가져오기에서 잘못된 행은 건너뛰고 행 번호와 원인을 출력하며, 정상 행은 저장합니다.

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

## 테스트

표준 라이브러리 `unittest`만 사용합니다.

```bash
python -m unittest discover -v
```

모델 검증, 세 저장 파일 초기화, 역방향 스트리밍 순서, 출력의 점진적 소비, 원자적 수정/삭제, 검색 조합, 요약·예산, 사용 중 카테고리 보호, CSV 입출력, 대화형 CLI와 오류 종료 코드를 검사합니다.

10만 건 성능 측정은 다음 명령으로 재현할 수 있습니다.

```bash
python -m scripts.benchmark_100k --records 100000
```

실측 결과와 O(n) 검색, ID 인덱스 부재, 전체 파일 재작성 병목 및 인덱싱·청크화·멀티프로세싱 개선안은 [성능 분석 문서](docs/DESIGN_AND_PERFORMANCE.md)를 참고하세요.
