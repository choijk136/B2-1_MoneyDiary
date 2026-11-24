# 터미널 시연 가이드

[프로젝트 개요](../README.md) · [실제 실행 기록 바로 보기](#cli-실행-로그)

**직접 실행하려면** 예시 거래 6건으로 아래 순서를 따라가세요. **출력만 확인하려면** 하단의 실행 기록을 보세요. 하단 기록은 빈 가계부에서 거래 한 건만 사용해 추가·수정·삭제 전후를 비교한 별도 예시입니다.

## 시작 상태 만들기

Python 3.10 이상으로 저장소 루트에서 실행합니다. 아래 명령은 시연 폴더 `demo_data`, `demo_imported`의 가계부 파일을 초기화하고 이전 `demo_export.csv`를 제거합니다. 기본 `./data`에 기록한 개인 거래는 그대로입니다. 환경에서 Python 명령이 `python3`라면 아래의 `python`을 `python3`로 바꿔 주세요.

```bash
python -m scripts.prepare_demo
```

```bash
python -m budget_app --data-dir ./demo_data list --limit 6
```

```bash
python -m budget_app --data-dir ./demo_data summary --month 2026-09 --top 3
```

목록에는 `TX-DEMO-006`부터 `TX-DEMO-001`까지 6건이 나옵니다. 9월 수입 3,000,000원에서 지출 810,000원을 빼면 잔액은 2,190,000원입니다. 예산 800,000원보다 10,000원 더 썼다는 경고도 확인합니다.

## 기능별 시연

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

## CLI 실행 로그

아래는 같은 커피 지출을 4,500원에서 5,500원으로 정정하고 다른 가계부에 옮긴 실제 기록입니다. 하나의 블록에 `add`, `list`, `search`, `summary`, `export`, `import`, `update`, `delete`의 명령과 출력을 모두 담았습니다. 마지막 두 번의 조회에서 원본은 비고 복사본에는 거래가 남는지 비교할 수 있습니다. `$`는 셸 프롬프트이며 임시 경로와 ID는 실행할 때마다 달라집니다.

```console
$ demo=$(mktemp -d)
$ python -m budget_app --data-dir "$demo" category add --name cafe
[저장 완료] category=cafe
$ python -m budget_app --data-dir "$demo" budget set --month 2026-09 --amount 5000
[저장 완료] 2026-09 예산 5,000원
$ python -m budget_app --data-dir "$demo" add
날짜(YYYY-MM-DD): 2026-09-12
타입(income/expense): expense
카테고리: cafe
금액(양수 정수): 4500
메모(선택): 학교 앞 커피
태그(쉼표로 구분, 없으면 엔터): campus
[저장 완료] id=TX-6801E4721810
$ python -m budget_app --data-dir "$demo" list --limit 1
ID              | 날짜         | 타입      | 카테고리             | 금액              | 메모                       | 태그
----------------+------------+---------+------------------+-----------------+--------------------------+-------------------------
TX-6801E4721810 | 2026-09-12 | expense | cafe             | 4,500           | 학교 앞 커피                  | campus
$ tx=$(python -m budget_app --data-dir "$demo" list --limit 1 | awk 'END {print $1}')
$ python -m budget_app --data-dir "$demo" update --id "$tx" --amount 5500
[수정 완료] id=TX-6801E4721810
$ python -m budget_app --data-dir "$demo" search --category cafe --q 커피 --tag campus
ID              | 날짜         | 타입      | 카테고리             | 금액              | 메모                       | 태그
----------------+------------+---------+------------------+-----------------+--------------------------+-------------------------
TX-6801E4721810 | 2026-09-12 | expense | cafe             | 5,500           | 학교 앞 커피                  | campus
$ python -m budget_app --data-dir "$demo" summary --month 2026-09 --top 1
총 수입: 0원
총 지출: 5,500원
잔액: -5,500원
예산: 5,000원 (사용률 110.0%)
[경고] 예산을 500원 초과했습니다.

지출 TOP 1
1) cafe 5,500원
$ python -m budget_app --data-dir "$demo" export --month 2026-09 --out "$demo/sep.csv"
[완료] /tmp/tmp.heEqkIQaJm/sep.csv (1 records)
$ python -m budget_app --data-dir "$demo/copy" category add --name cafe
[저장 완료] category=cafe
$ python -m budget_app --data-dir "$demo/copy" import --from "$demo/sep.csv"
[완료] imported=1, skipped=0
$ python -m budget_app --data-dir "$demo" delete --id "$tx"
[삭제 완료] id=TX-6801E4721810
$ python -m budget_app --data-dir "$demo" list --limit 1
데이터 없음
$ python -m budget_app --data-dir "$demo/copy" list --limit 1
ID              | 날짜         | 타입      | 카테고리             | 금액              | 메모                       | 태그
----------------+------------+---------+------------------+-----------------+--------------------------+-------------------------
TX-1FDA046AF4A9 | 2026-09-12 | expense | cafe             | 5,500           | 학교 앞 커피                  | campus
```
