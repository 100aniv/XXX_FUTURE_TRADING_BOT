# PHASE25-0: Long-run PAPER Regression Harness - 설계 문서

**Date**: 2025-12-02  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE25-0 – Long-run PAPER Regression Harness (2H+ 최소)  
**Purpose**: 장시간 PAPER 테스트 자동화 하네스 구축 (6분 스모크와 별개)

---

## 1. 목적 (Purpose)

### 1.1 주요 목표
- **장시간 PAPER 테스트 표준화**: 최소 2H 이상 PAPER 실행을 자동화하는 하네스 구축
- **6분 스모크와 명확한 구분**: 개발/CI용 6분 테스트 vs 운영 안정성 검증용 2H+ 테스트
- **완전 자동화**: Pre-flight → Clean State → Run → Monitor → Post-run 분석까지 전체 플로우 자동화
- **"1조 버는 프로그램" 수준의 안정성 기준**: 실제 운영 환경에서 요구되는 장시간 안정성 검증

### 1.2 배경

**PHASE24 완료 상태** (Production Ready Infra Baseline 확립):
- ✅ PHASE24-0: Redis hardening (2H PAPER, Redis ERROR 0건)
- ✅ PHASE24-1: DB cleanup 안정성 + 통합 인프라 진단
- ✅ PHASE24-2: Env & Config Management (validator + .env.example)

**현재 Pain Points**:
1. **장기 테스트 표준화 부재**: 
   - 6분 스모크 테스트는 있으나, 이는 "빠른 회귀 검증"용
   - 실제 장시간 안정성 검증은 수동으로 수행 중
   - 2H/12H/24H 테스트가 각 PHASE마다 임시방편으로 실행됨

2. **자동화 부족**:
   - 실행 전 환경 정리, Pre-flight check, Clean State가 수동
   - 실행 중 로그 모니터링이 수동 (ERROR 발생 시 대응 지연)
   - 종료 후 메트릭 수집/분석이 수동

3. **Acceptance 기준 모호**:
   - "6분만 돌려도 되나?", "2H는 너무 긴가?" 같은 혼란
   - 명확한 장기 테스트 기준선이 없음

### 1.3 PHASE25-0이 해결하는 문제

**Before (AS-IS)**:
```
개발자가 수동으로:
1. Python 프로세스 종료
2. Docker 상태 확인
3. clean_state_complete.py 실행
4. infra diagnostics 실행
5. run_v2.py 실행 (duration 수동 지정)
6. 로그 파일 tail하며 ERROR 감시
7. 종료 후 DB/로그 수동 분석
8. 리포트 수동 작성
→ 총 소요 시간: 2H 실행 + 준비/분석 30분 = 2.5H
```

**After (TO-BE)**:
```
python scripts/infra/phase25_0_long_run_paper.py --config <CONFIG> --duration-hours 2.0
→ 자동으로 전체 플로우 수행 + 리포트/JSON 생성
→ 개발자는 결과만 확인
```

---

## 2. AS-IS 분석

### 2.1 현재 PAPER 실행 플로우

**개별 스크립트 실행** (PHASE24 기준):
1. `scripts/clean_state_complete.py`: DB/Redis 정리
2. `scripts/infra/phase24_1_infra_diagnostics.py`: 인프라 점검
3. `scripts/infra/env_config_validator.py`: Env/Config 검증
4. `scripts/run_v2.py --mode paper --config <CONFIG>`: PAPER 실행

**문제점**:
- 스크립트 간 연결이 없음 (각각 독립 실행)
- 중간에 실패해도 다음 단계로 넘어갈 수 있음
- 로그 모니터링이 수동
- 결과 분석이 수동

### 2.2 6분 vs 2H 테스트 혼용 문제

**6분 스모크 테스트** (PHASE24-1, PHASE24-2):
- 목적: 빠른 회귀 검증, CI용
- Config: `duration_hours: 0.1` (6분)
- 판정: 인프라 ERROR 0건 + 기본 트레이드 발생 확인

**2H 장기 테스트** (PHASE24-0):
- 목적: 실제 운영 안정성 검증
- Config: `duration_hours: 2.0`
- 판정: 장시간 ERROR 0건 + 충분한 트레이드 + Ensemble 작동 확인

**현재 문제**:
- 6분과 2H의 Acceptance 기준이 혼재
- "6분만 돌려도 PHASE 통과?" vs "2H는 너무 길어서 생략?" 같은 혼란
- **PHASE25-0의 핵심 원칙**: "6분은 스모크/개발용, 2H+는 Acceptance용"으로 명확히 구분

---

## 3. TO-BE 설계

### 3.1 Long-run PAPER Harness 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│ phase25_0_long_run_paper.py (Orchestrator)                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  STEP 1: 환경 정리                                           │
│    ├─ Python 프로세스 kill (run_v2, engine 관련)           │
│    └─ Docker 상태 확인 (trading_db_postgres, trading_redis)│
│                                                              │
│  STEP 2: Pre-flight Check                                   │
│    ├─ env_config_validator.py (환경변수 + Config 검증)      │
│    ├─ phase24_1_infra_diagnostics.py (DB/Redis/Engine)      │
│    └─ Exit code != 0이면 중단                                │
│                                                              │
│  STEP 3: Clean State                                        │
│    └─ clean_state_complete.py (DB/Redis 정리)               │
│                                                              │
│  STEP 4: Long-run 실행 (새 CMD 창)                         │
│    ├─ run_v2.py --mode paper --config <CONFIG>              │
│    ├─ --duration-hours <DURATION> (기본값: 2.0)            │
│    └─ 새 CMD 창에서 실행 (로그 별도 확인 가능)              │
│                                                              │
│  STEP 5: 실시간 모니터링                                     │
│    ├─ logs/application.log tail                             │
│    ├─ ERROR/CRITICAL 패턴 감시                              │
│    ├─ 발견 시: run_v2 kill + 에러 로그 저장 + FAIL          │
│    └─ wall-clock duration 추적                              │
│                                                              │
│  STEP 6: Post-run 분석                                      │
│    ├─ DB 쿼리 (trades, time range 기반)                    │
│    ├─ 로그 파싱 (Ensemble V2 aggregate, Tier/Skip)         │
│    └─ 메트릭 계산 (trade_count, active_positions, etc.)    │
│                                                              │
│  STEP 7: 결과 저장                                          │
│    ├─ MD 리포트: docs/PHASE25/PHASE25-0_LONG_RUN_PAPER_REPORT.md │
│    └─ JSON 요약: logs/phase25_0_long_run_summary.json       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 핵심 원칙

#### 원칙 1: 6분 vs 2H+ 명확한 구분
- **6분 스모크**: 개발/CI용, 빠른 회귀 검증
  - 목적: 코드 변경 후 기본 작동 확인
  - 판정: 인프라 ERROR 0건 + 최소 트레이드 발생
  - 실행: `pytest` or 수동 (`--duration-hours 0.1`)

- **2H+ Long-run**: Acceptance용, 실제 안정성 검증
  - 목적: PHASE 완료 조건, 운영 배포 전 필수 검증
  - 판정: 장시간 ERROR 0건 + 충분한 트레이드 + Ensemble 정상 작동
  - 실행: `phase25_0_long_run_paper.py` (자동화)

- **절대 금지**: "2H는 길어서 6분으로 대체"하는 행위
  - PHASE Acceptance에 2H+가 명시된 경우, 반드시 실행해야 함

#### 원칙 2: 완전 자동화
- 사용자는 단 1개 커맨드만 실행:
  ```bash
  python scripts/infra/phase25_0_long_run_paper.py --config <CONFIG> --duration-hours 2.0
  ```
- 환경 정리, Pre-flight, Clean State, Run, Monitor, 분석, 리포트까지 모두 자동

#### 원칙 3: 실시간 ERROR 감지 & 중단
- 로그 모니터링으로 ERROR/CRITICAL 발생 시:
  - 즉시 run_v2 프로세스 kill
  - 마지막 200줄 별도 저장
  - Long-run 전체를 FAIL로 마킹
  - 개발자는 에러 로그만 확인하면 됨

#### 원칙 4: 명확한 Exit Code
- **0**: Long-run PASS (모든 Acceptance 조건 충족)
- **1**: Long-run FAIL (하나라도 조건 미충족)
- CI/운영 파이프라인에서 자동 판정 가능

---

## 4. PHASE25-0 범위

### 4.1 IN SCOPE

1. **Long-run 오케스트레이터 스크립트**
   - 파일: `scripts/infra/phase25_0_long_run_paper.py`
   - 기능: 환경 정리 → Pre-flight → Clean State → Run → Monitor → 분석 → 리포트

2. **CLI 인터페이스**
   - `--config <PATH>`: PAPER config 파일 (필수)
   - `--duration-hours <FLOAT>`: 기본값 2.0 (최소 2H)
   - `--tag <STR>`: Run 태그 (선택)

3. **실시간 로그 모니터링**
   - `logs/application.log` tail
   - ERROR/CRITICAL 패턴 감지
   - 즉시 중단 + 에러 로그 저장

4. **Post-run 메트릭 수집**
   - DB 쿼리 (trades, time range 기반)
   - 로그 파싱 (Ensemble V2 aggregate, Tier/Skip)
   - 메트릭 계산: trade_count, entry_count, exit_count, active_positions, etc.

5. **결과 저장**
   - MD 리포트: `docs/PHASE25/PHASE25-0_LONG_RUN_PAPER_REPORT.md`
   - JSON 요약: `logs/phase25_0_long_run_summary.json`

6. **테스트**
   - 파일: `tests/test_phase25_0_long_run_paper.py`
   - 단위 테스트: 로그 파서, DB 메트릭 계산, duration 핸들링
   - 통합 스모크 테스트: 0.1h duration으로 전체 플로우 검증

7. **문서**
   - 설계 문서 (이 문서)
   - 실행 리포트 (`PHASE25-0_LONG_RUN_PAPER_REPORT.md`)
   - PHASE_ROADMAP.md 업데이트

8. **실제 2H Long-run 실행** (Acceptance 필수)
   - Config: 기존 `configs/paper/phase24_1_infra_ensemble_1h.yml` 복사 후 2H로 수정
   - 판정: ERROR/CRITICAL 0건 + Trade ≥ 50건 + Ensemble V2 정상

### 4.2 OUT OF SCOPE (PHASE25+로 유보)

1. **전략/파라미터 변경**: scalping_v3 등 기존 전략만 사용
2. **Ensemble 로직 변경**: ScoreEngineV2, AggregatorV2 그대로 유지
3. **튜닝**: 파라미터 탐색, 가중치 조정 (PHASE25-1+)
4. **멀티 심볼**: BTCUSDT 단일 심볼만 (PHASE26)
5. **DB schema migration**: run_id 컬럼 추가 (PHASE25+)
6. **run_v2.py 통합**: `--check-infra`, `--long-run` 옵션 (PHASE25+)

---

## 5. High-Level Flow

### 5.1 전체 플로우

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLI 파싱                                                 │
│    ├─ --config (필수)                                       │
│    ├─ --duration-hours (기본: 2.0, 최소: 2.0)              │
│    └─ --tag (선택)                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 환경 정리                                                │
│    ├─ Python 프로세스 kill (run_v2, engine 관련)          │
│    └─ Docker 상태 확인 (필요 시 기동 안내)                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Pre-flight Check                                         │
│    ├─ env_config_validator.py                               │
│    ├─ phase24_1_infra_diagnostics.py                        │
│    └─ Exit code != 0 → ABORT                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Clean State                                              │
│    └─ clean_state_complete.py                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Long-run 실행 (새 CMD 창)                               │
│    ├─ cmd /c start "LONG_RUN_PAPER" ...                    │
│    ├─ run_v2.py --mode paper --config <CONFIG>             │
│    └─ --duration-hours <DURATION>                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 실시간 모니터링 (주 프로세스)                            │
│    ├─ logs/application.log tail (30초마다)                 │
│    ├─ ERROR/CRITICAL 패턴 검색                             │
│    ├─ 발견 시: run_v2 kill + 에러 로그 저장 + FAIL         │
│    └─ wall-clock duration 추적                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. 정상 종료 대기                                           │
│    ├─ duration 경과 후 engine 로그 확인                     │
│    └─ "정상 종료" 메시지 없으면 FAIL                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Post-run 분석                                            │
│    ├─ DB 쿼리 (trades, time range)                         │
│    ├─ 로그 파싱 (Ensemble V2 aggregate)                    │
│    └─ 메트릭 계산                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. 결과 저장                                                │
│    ├─ MD 리포트                                             │
│    ├─ JSON 요약                                             │
│    └─ Exit code (0: PASS, 1: FAIL)                         │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 실시간 모니터링 상세

```python
# 의사코드
start_time = time.time()
target_duration_sec = duration_hours * 3600
log_file = "logs/application.log"
last_position = 0

while True:
    # 1. Wall-clock 체크
    elapsed = time.time() - start_time
    if elapsed >= target_duration_sec:
        # Duration 경과 → 정상 종료 확인
        check_normal_termination()
        break
    
    # 2. 로그 파일 tail
    new_lines = read_new_lines(log_file, last_position)
    last_position = current_position
    
    # 3. ERROR/CRITICAL 패턴 검색
    for line in new_lines:
        if "ERROR" in line or "CRITICAL" in line:
            # 즉시 중단
            kill_run_v2_process()
            save_error_log(last_200_lines)
            mark_as_FAIL()
            return 1
    
    # 4. 30초 대기
    time.sleep(30)
```

---

## 6. Metrics & Acceptance

### 6.1 Acceptance Criteria (PHASE25-0 완료 조건)

#### ✅ 필수 조건 (MUST PASS)

1. **Long-run 오케스트레이터 구현**
   - `scripts/infra/phase25_0_long_run_paper.py` 완성
   - CLI 인터페이스 구현 (--config, --duration-hours, --tag)
   - 환경 정리 → Pre-flight → Clean State → Run → Monitor → 분석 → 리포트 전체 플로우 동작

2. **테스트**
   - `tests/test_phase25_0_long_run_paper.py` 작성
   - 단위 테스트: 로그 파서, DB 메트릭, duration 핸들링
   - 통합 스모크 테스트: 0.1h duration으로 전체 플로우 검증
   - 모든 테스트 PASS

3. **실제 2H Long-run 실행** (핵심!)
   - Duration: **≥ 2.0 hours (wall-clock 기준)**
   - Infra: **ERROR/CRITICAL = 0건**
   - Trades: **≥ 50건** (프로젝트 상황에 맞게 조정 가능)
   - Active Positions: **= 0** (엔진 정상 종료 시점)
   - Ensemble V2: **Aggregate 평가 ≥ 1000회**
   - Config: `configs/paper/phase25_0_long_run_2h.yml` (새로 생성)

4. **결과 저장**
   - MD 리포트: `docs/PHASE25/PHASE25-0_LONG_RUN_PAPER_REPORT.md`
   - JSON 요약: `logs/phase25_0_long_run_summary.json`
   - 리포트에 Acceptance 조건 체크리스트 포함

5. **문서화**
   - 설계 문서 (이 문서) 완성
   - 실행 리포트 작성
   - PHASE_ROADMAP.md 업데이트 (PHASE25-0 ✅ COMPLETE)

6. **Git 커밋**
   - 의미 있는 커밋 메시지
   - 모든 산출물 포함

#### ⏸️ 선택 조건 (NICE TO HAVE)

1. **DB run_id 컬럼 추가**: PHASE25+로 유보 (현재는 time range 기반 필터)
2. **run_v2.py 통합**: `--long-run` 옵션 (PHASE25+)
3. **Dashboard 연동**: 메트릭을 Grafana에 전송 (PHASE28+)

### 6.2 메트릭 상세

**DB 메트릭** (trades 테이블):
- `trade_count`: 총 거래 건수
- `entry_count`: 진입 거래 건수
- `exit_count`: 청산 거래 건수
- `active_positions`: 활성 포지션 수 (종료 시점 = 0 필수)
- `time_range`: 실행 시작/종료 timestamp

**로그 메트릭** (application.log):
- `ensemble_aggregate_count`: Ensemble V2 aggregate 평가 횟수
- `tier1_count`: Tier1 (High-Confidence) 결정 횟수
- `tier2_count`: Tier2 (Consensus) 결정 횟수
- `skip_count`: Skip 결정 횟수
- `error_count`: ERROR 로그 횟수 (0 필수)
- `critical_count`: CRITICAL 로그 횟수 (0 필수)

**Duration 메트릭**:
- `target_duration_sec`: 목표 duration (초)
- `actual_duration_sec`: 실제 실행 duration (초)
- `duration_accuracy`: `actual / target` (0.98 ~ 1.02 허용)

---

## 7. 구현 설계

### 7.1 파일 구조

```
scripts/infra/
├── phase25_0_long_run_paper.py  (새로 생성)
│   ├── main()
│   ├── cleanup_environment()
│   ├── run_preflight_checks()
│   ├── run_clean_state()
│   ├── start_long_run()
│   ├── monitor_logs()
│   ├── analyze_results()
│   └── save_report()

tests/
├── test_phase25_0_long_run_paper.py  (새로 생성)
│   ├── test_duration_default()
│   ├── test_log_parser_error_detection()
│   ├── test_db_metrics_calculation()
│   └── test_integration_smoke()

configs/paper/
├── phase25_0_long_run_2h.yml  (새로 생성)
│   └── duration_hours: 2.0

docs/PHASE25/
├── PHASE25-0_LONG_RUN_PAPER_DESIGN.md  (이 문서)
└── PHASE25-0_LONG_RUN_PAPER_REPORT.md  (실행 후 생성)

logs/
└── phase25_0_long_run_summary.json  (실행 후 생성)
```

### 7.2 주요 함수 설계

**`cleanup_environment()`**:
```python
def cleanup_environment():
    """
    환경 정리
    - Python 프로세스 kill (run_v2, engine 관련)
    - Docker 상태 확인
    """
    # Windows: tasklist로 python 프로세스 검색
    # run_v2, engine, future_alarm_bot 관련 프로세스 kill
    
    # Docker 상태 확인
    # docker ps | grep trading_db_postgres, trading_redis
    # 없으면 안내 메시지
```

**`run_preflight_checks()`**:
```python
def run_preflight_checks() -> bool:
    """
    Pre-flight Check 실행
    Returns:
        bool: 모든 체크 PASS 여부
    """
    # 1. env_config_validator.py 실행
    # 2. phase24_1_infra_diagnostics.py 실행
    # 3. Exit code 확인
    # 하나라도 실패 시 False
```

**`start_long_run()`**:
```python
def start_long_run(config_path: str, duration_hours: float):
    """
    Long-run PAPER 실행 (새 CMD 창)
    Returns:
        subprocess.Popen: 실행 중인 프로세스
    """
    # Windows: cmd /c start "LONG_RUN_PAPER" cmd /k "<venv> && python scripts/run_v2.py ..."
    # Popen으로 프로세스 추적
```

**`monitor_logs()`**:
```python
def monitor_logs(target_duration_sec: float, process: subprocess.Popen) -> dict:
    """
    실시간 로그 모니터링
    Returns:
        dict: {
            'status': 'PASS' | 'FAIL',
            'error_lines': [...],
            'last_200_lines': [...]
        }
    """
    # logs/application.log tail
    # ERROR/CRITICAL 검색
    # 발견 시 process.kill() + FAIL
    # duration 경과 시 정상 종료 확인
```

**`analyze_results()`**:
```python
def analyze_results(start_time: datetime, end_time: datetime) -> dict:
    """
    Post-run 메트릭 수집
    Returns:
        dict: {
            'db_metrics': {...},
            'log_metrics': {...},
            'duration_metrics': {...}
        }
    """
    # DB 쿼리 (trades, time range)
    # 로그 파싱 (Ensemble V2 aggregate)
    # 메트릭 계산
```

**`save_report()`**:
```python
def save_report(metrics: dict, config_path: str, duration_hours: float):
    """
    MD 리포트 + JSON 요약 저장
    """
    # docs/PHASE25/PHASE25-0_LONG_RUN_PAPER_REPORT.md
    # logs/phase25_0_long_run_summary.json
```

---

## 8. Config 파일

### 8.1 새 Config 생성

**파일**: `configs/paper/phase25_0_long_run_2h.yml`

**기존 파일 복사 후 수정**:
- Source: `configs/paper/phase24_1_infra_ensemble_1h.yml`
- 변경사항:
  - `run_id`: `phase25_0_long_run_2h_<TIMESTAMP>`
  - `duration_hours`: 2.0 (현재 0.1 → 2.0으로 변경)
  - `comment`: "PHASE25-0: Long-run PAPER Regression (2H)"

---

## 9. 테스트 전략

### 9.1 Unit Tests

**파일**: `tests/test_phase25_0_long_run_paper.py`

**테스트 케이스**:
1. `test_duration_default()`: duration_hours 기본값이 2.0인지 확인
2. `test_duration_minimum()`: 2.0 미만 값 입력 시 경고 (Acceptance는 2.0 이상만 인정)
3. `test_log_parser_error_detection()`: 샘플 로그에서 ERROR/CRITICAL 정상 검출
4. `test_log_parser_normal()`: 정상 로그에서 PASS 판정
5. `test_db_metrics_calculation()`: 테스트 DB fixture로 메트릭 계산 검증
6. `test_integration_smoke()`: 0.1h duration으로 전체 플로우 검증 (CI용)

### 9.2 Integration Smoke Test

```python
def test_integration_smoke():
    """
    통합 스모크 테스트 (0.1h duration)
    
    목적: CI/단기 검증용
    주의: Acceptance용은 아님 (2H 실행 필수)
    """
    # phase25_0_long_run_paper.py 호출
    # --duration-hours 0.1 (6분)
    # 전체 플로우 정상 동작 확인
    # Exit code 0 확인
```

### 9.3 실제 2H Long-run (Acceptance 필수)

**별도 실행** (pytest가 아님):
```bash
python scripts/infra/phase25_0_long_run_paper.py \
    --config configs/paper/phase25_0_long_run_2h.yml \
    --duration-hours 2.0 \
    --tag "ACCEPTANCE_RUN"
```

**판정**:
- ERROR/CRITICAL: 0건
- Trade: ≥ 50건
- Active Positions: 0
- Ensemble Aggregate: ≥ 1000회
- Duration accuracy: 0.98 ~ 1.02

---

## 10. Out-of-Scope (PHASE25+로 유보)

### 10.1 명시적 제외 사항

1. **전략 변경**: scalping_v3 등 기존 전략만 사용
2. **Ensemble 로직 변경**: ScoreEngineV2, AggregatorV2 그대로
3. **튜닝**: 파라미터 탐색 (PHASE25-1+)
4. **멀티 심볼**: BTCUSDT만 (PHASE26)
5. **성능 최적화**: CPU/Memory 프로파일링 (PHASE27)
6. **DB schema migration**: run_id 컬럼 추가 (PHASE25+)
7. **run_v2.py 통합**: `--long-run` 옵션 (PHASE25+)

### 10.2 향후 통합 방안

**PHASE25-1+**:
- `run_v2.py --long-run` 옵션 추가
  - 내부에서 `phase25_0_long_run_paper.py` 호출
- DB run_id 컬럼 추가
  - 특정 run만 필터링 가능
- CI/CD 파이프라인 통합
  - 자동 Long-run 실행 + 결과 리포트

---

## 11. Dependencies

### 11.1 사전 조건
- **PHASE24 완료**: Redis hardening + DB cleanup + Env/Config validator
- **Python 가상환경**: trading_bot_env
- **Docker**: trading_db_postgres, trading_redis 정상 실행 중

### 11.2 필요 라이브러리
- `psycopg2`: DB 쿼리
- `redis`: Redis 연결
- `pyyaml`: Config 로딩
- `dotenv`: 환경변수 로딩
- 기타: 기존 requirements.txt에 모두 포함

---

## 12. Timeline & Milestones

### 12.1 예상 작업 시간
- **STEP 0 (Context Loading)**: 완료
- **STEP 1 (설계 문서)**: 현재
- **STEP 2 (오케스트레이터 구현)**: ~1H
- **STEP 3 (테스트 작성)**: ~40분
- **STEP 4 (ROADMAP 업데이트)**: ~10분
- **STEP 5 (실제 2H Long-run)**: ~2.5H (2H 실행 + 준비/분석)
- **STEP 6 (테스트 & 커밋)**: ~10분
- **Total**: ~4.5H (실제 2H 실행 포함)

### 12.2 Milestones
- [ ] STEP 1 완료: 설계 문서 작성
- [ ] STEP 2 완료: 오케스트레이터 구현
- [ ] STEP 3 완료: 테스트 작성 및 PASS
- [ ] STEP 4 완료: ROADMAP 업데이트
- [ ] STEP 5 완료: 실제 2H Long-run 실행 및 PASS
- [ ] STEP 6 완료: Git 커밋

---

**작성자**: Windsurf AI  
**작성일**: 2025-12-02  
**검토 대상**: PHASE24 완료 후 즉시 착수  
**핵심 원칙**: "6분은 스모크/개발용, 2H+는 Acceptance용" - 절대 혼용 금지
