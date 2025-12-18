# PHASE35-4 ITER23 REPORT: Backtest Report & Metrics SSOT + DB Evidence Fix

**작성일**: 2025-12-18  
**담당**: Cascade AI  
**결과**: ⚠️ **PARTIAL PASS** (SSOT 수정 완료, trades=0 실제 확정)

---

## 📋 Executive Summary

### ITER23 Goals
| Goal | 설명 | 상태 |
|------|------|------|
| G1 | Report 경로 SSOT 단일화 | ✅ PASS |
| G2 | DB evidence 하드코딩 제거 | ✅ PASS |
| G3 | trades=0 착시 vs 실제 확정 | ✅ PASS (실제 0) |
| G4 | L0 vs L3 지표 차이 | ❌ FAIL (둘 다 0) |

### 핵심 발견
1. **ITER22 Report 경로 불일치 원인 확정**: `config["backtest"]["output_path"]`를 사용했지만 엔진은 `config["backtest"]["output_file"]`을 읽음
2. **ITER22 DB 연결 실패 원인 확정**: 
   - 비밀번호: `trading_pass` → 실제: `trading_pw_2024`
   - 포트: `5432` → 실제: `5433` (docker-compose 매핑)
3. **trades=0은 실제**: DB 쿼리 결과 0, report 미생성은 이 때문 (착시 아님)

---

## 🔧 구현 내용

### 1. Report 경로 SSOT 키 수정
```python
# ITER22 (잘못됨)
config["backtest"]["output_path"] = str(report_path)

# ITER23 (올바름 - 엔진이 읽는 키)
config["backtest"]["output_file"] = str(report_path)
```

### 2. DB 연결 SSOT (하드코딩 제거)
```python
# ITER22 (하드코딩 - 실패)
conn = psycopg2.connect(
    host="localhost",
    port=5432,  # 잘못됨 (실제: 5433)
    password="trading_pass"  # 잘못됨 (실제: trading_pw_2024)
)

# ITER23 (database.postgres 모듈 재사용)
from database.postgres import get_db_connection
with get_db_connection() as conn:
    # 자동으로 올바른 port/password 사용
```

### 3. Report 파일 Fallback 탐색
```python
def resolve_report_path(configured_path, run_dir):
    # 1. SSOT 경로 (configured_path) 확인
    # 2. Fallback 탐색: reports/backtest/, reports/, run_dir
    # 3. 전부 없으면 None (FAIL)
```

### 4. 방어적 Metrics 파싱
```python
def parse_metrics_defensive(report_data):
    # total_trades: total_trades, trades, summary.total_trades 등
    # loaded_candles: loaded_candles, bars, num_bars 등
```

---

## 📊 실행 결과

### L0_baseline
- **trial_id**: iter23_L0_baseline_8f4396f5
- **elapsed**: 845.92초
- **db_connection**: ✅ SUCCESS
- **db_trades**: 0
- **report_path**: None (trades=0으로 미생성)

### L3_aggressive
- **trial_id**: iter23_L3_aggressive_cc1153d6
- **elapsed**: 820.84초
- **db_connection**: ✅ SUCCESS
- **db_trades**: 0
- **report_path**: None (trades=0으로 미생성)

---

## 🔒 AC 체크리스트

| AC | 설명 | 상태 | 비고 |
|----|------|------|------|
| AC1 | Report 존재 | ❌ FAIL | trades=0으로 미생성 |
| AC2 | loaded_candles 유효 | ✅ PASS | 데이터는 로드됨 |
| AC3 | trades 파싱 | ❌ FAIL | report 없음 |
| AC4 | DB 연결 | ✅ **PASS** | SSOT 작동 확인 |
| AC5 | Metrics 차이 | ❌ FAIL | 둘 다 0 |

---

## 📁 산출물

- path: `scripts/phase35/run_iter23_report_metrics_ssot.py`
  raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/main/scripts/phase35/run_iter23_report_metrics_ssot.py

- path: `tests/test_phase35_iter23_report_metrics_contract.py`
  raw: https://raw.githubusercontent.com/100aniv/XXX_FUTURE_TRADING_BOT/main/tests/test_phase35_iter23_report_metrics_contract.py

- path: `artifacts/phase35/iter23/iter23_results.json`

---

## 📝 결론

### 판정: ⚠️ **PARTIAL PASS**

**성공 (ITER22 문제 해결)**:
1. ✅ Report 경로 SSOT 확정: `config["backtest"]["output_file"]`
2. ✅ DB 연결 SSOT 확정: `database.postgres.get_db_connection()` (port 5433, pw=trading_pw_2024)
3. ✅ trades=0 착시 vs 실제 확정: **실제 0** (DB 쿼리 결과)

**실패 원인 (전략 레벨)**:
- **trades=0이 실제**: 앙상블 전략이 신호를 생성하지 않음
- report_generator는 trades=0이면 리포트를 생성하지 않음 (설계상 정상)

---

## 🚀 NEXT: ITER24

**단일 액션**: 앙상블 전략의 신호 생성 실패 원인 분석

진단 방향:
1. DecisionTrace/SignalFlow에서 block_reason 분포 확인
2. sub-model별 FLAT 비율 확인
3. ensemble no_consensus 비율 확인
4. L4_ultra_debug (min_votes=1, confidence=0.1) 후보 추가 실행

목표:
- "파이프라인 정상 + 파라미터 과도"인지 "엔진/전략 결함"인지 확정
