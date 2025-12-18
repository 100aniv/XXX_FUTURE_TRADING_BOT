# PHASE35-4 ITER26 REPORT: SignalProbe ↔ Engine 캔들 구간 SSOT 통합

**작성일**: 2025-12-18  
**담당**: Cascade AI  
**결과**: ⚠️ **PARTIAL PASS** (G1 달성, G2 미달성)

---

## 📋 Executive Summary

### ITER26 Goals vs Results

| Goal | 상태 | 비고 |
|------|------|------|
| G1: SignalProbe와 Engine 동일 캔들 구간 사용 | ✅ **PASS** | df에서 start/end 추출 → config 주입 |
| G2: E2E trades>0 + Report 생성 | ❌ FAIL | 신호 생성되지만 체결까지 안됨 |
| G3: 기존 모듈 최대 재사용 | ✅ **PASS** | signal_probe_iter24.load_candles 재사용 |

---

## 🔍 근본 원인 분석 (ROOT SCAN)

### SignalProbe vs Engine 캔들 로딩 차이

**ITER25까지의 문제**:
- SignalProbe: `HistoricalFeed(..., days=7)` → CSV tail 7일
- Engine: `HistoricalFeed(..., start_date, end_date)` → config 기반 날짜
- **두 방식이 완전히 다름** → 동일 캔들 구간 보장 안됨

**ITER26 해결책**:
1. SignalProbe 방식으로 df 로드 (`load_candles_ssot()`)
2. df에서 timestamp min/max 추출
3. Engine config에 동일 start_date/end_date 주입

### 날짜 포함 규칙 (SSOT)

`HistoricalFeed` (Line 128-132):
```python
if end_date:
    end_dt = pd.to_datetime(end_date, utc=True)
    end_dt_inclusive = end_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
```
→ **end_date는 inclusive** (해당 날짜 23:59:59까지 포함)

---

## 🔧 구현 내용 (STEP 3)

### ITER26 Runner (`run_iter26_e2e_same_window_as_signal_probe.py`)

**핵심 로직**:
```python
# 1. SignalProbe SSOT로 캔들 로딩
df = load_candles_ssot(symbol, timeframe, days=30)
df_range = extract_date_range_from_df(df)

# 2. Engine config에 동일 구간 주입
config["start_date"] = df_range["start_date"]
config["end_date"] = df_range["end_date"]
config["backtest"]["start_date"] = df_range["start_date"]
config["backtest"]["end_date"] = df_range["end_date"]
```

### L4_ULTRA_DEBUG_OVERRIDES (최종)

```python
L4_ULTRA_DEBUG_OVERRIDES = {
    "trend": {"adx_threshold": 0},
    "reversion": {"rsi_oversold": 49, "rsi_overbought": 51},
    "breakout": {"volume_threshold": 0.0},
    "regime_filter": {"enabled": False},
    "ensemble": {"min_votes": 1, "confidence_threshold": 0.0, "cooldown_bars": 0},
    "risk": {"cooldown_after_loss": 0, "max_trades_per_day": 1000},
    "execution": {"reject_cooldown_seconds": 0},
    "database": {"enabled": True}
}
```

### 디버깅 과정에서 발견된 문제들

1. **전략 params 미적용**: 루트 레벨만 오버라이드 → `strategies.xxx.params`에도 적용 필요
2. **Engine cooldown**: `execution.reject_cooldown_seconds` 기본값 60초 → 0으로 설정
3. **RiskManager 연속 손실 쿨다운**: 신호 생성 후에도 차단됨
4. **database.enabled**: 기본값 false → true로 설정 필요

---

## 📊 실행 결과 (STEP 5)

### 실행 환경

- Git commit: de16662b
- 데이터 구간: 2024-11-30 ~ 2024-12-30 (30일)
- 총 캔들: 2,892개
- 실행 시간: ~100초

### 신호 생성 확인

```
🔔 [BTCUSDT] 신호 생성: 1개 - phase35_ensemble_v1:LONG
✅ [BTCUSDT] 단일 신호 사용: LONG by phase35_ensemble_v1
```

→ **신호가 생성되고 있음!**

### 차단 로그

```
❌ [ENTRY BLOCK] reason=risk_check_failed detail="연속 손실 쿨다운 (4회, 29분 남음)"
```

→ 거래가 발생하고 손실이 났지만, DB에 기록되지 않음

### AC 체크 결과

| AC | 설명 | 상태 | 비고 |
|----|------|------|------|
| AC1 | DB 스키마 존재 | ✅ **PASS** | trading.trades 존재 |
| AC2 | trades>0 | ❌ FAIL | 0건 (DB 저장 안됨) |
| AC3 | Report 생성 | ❌ FAIL | trades=0으로 미생성 |
| AC4 | Artifacts 저장 | ✅ **PASS** | iter26_results.json |
| AC5 | df_range == Engine range | ✅ **PASS** | 동일 구간 확인 |

---

## 📁 산출물

1. `scripts/phase35/run_iter26_e2e_same_window_as_signal_probe.py` (신규)
2. `tests/test_phase35_iter26_ssot_contract.py` (신규)
3. `artifacts/phase35/iter26/iter26_results.json`
4. `artifacts/phase35/iter26/iter26_config.yaml`

---

## 📝 결론

### 판정: ⚠️ **PARTIAL PASS**

**✅ 성공 (G1: 캔들 구간 SSOT 통합)**:
1. SignalProbe와 Engine이 동일한 캔들 구간 사용
2. df에서 start/end 추출 → config 주입 로직 구현
3. Contract Tests 9/9 PASS

**❌ 실패 (G2: E2E trades>0)**:
- 신호가 생성되지만 DB에 기록되지 않음
- 원인: backtest 모드에서 거래 체결 후 DB 저장 경로 확인 필요
- RiskManager 연속 손실 쿨다운이 추가 차단

### ITER24 → ITER26 진전

| 항목 | ITER24 | ITER25 | ITER26 |
|------|--------|--------|--------|
| SignalProbe 신호 | ✅ LONG=372 | (미실행) | (days=30으로 확장) |
| DB 에러 | UndefinedTable | ✅ 해결 | ✅ 해결 |
| 캔들 구간 SSOT | ❌ 분리 | ❌ 분리 | ✅ **통합** |
| trades>0 | ❌ | ❌ | ❌ |

---

## 🚀 NEXT: ITER27

**목표**: E2E trades>0 달성

**조사 포인트**:
1. backtest 모드에서 broker.submit_order → fill → save_trade_to_db 경로 확인
2. RiskManager 연속 손실 쿨다운 완전 비활성화
3. SimBroker에서 실제 체결이 일어나는지 로깅 추가

**예상 해결책**:
- save_trade_to_db 호출 전 조건 확인
- SimBroker.fill() 로직 디버깅
- 또는 paper 모드로 전환하여 실제 체결 확인
