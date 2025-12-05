# PHASE27-5: Signal Parity 초기 발견사항

**작성일**: 2025-12-04  
**상태**: 🔴 **CRITICAL ISSUE FOUND**  
**요약**: Offline Scan ↔ Engine Replay 신호 수 극단적 차이 발견

---

## Executive Summary

**핵심 발견**:
- **Offline Scan**: 5,741개 신호 (30일, 하루 평균 191.4개)
- **Engine Replay**: **0개 신호** (30일, 전체 기간 동안 "no_signals")
- **Signal Parity**: ❌ **100% 차이 (FAIL)**

**판정**: **CRITICAL - 파이프라인 정합성 문제**

---

## 1. 실행 결과

### 1.1 Offline Signal Scan (PHASE27-4)

**파일**: `docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json`

```json
{
  "scan_result": {
    "total_bars": 8612,
    "warmup_skipped": 50,
    "evaluated_bars": 8562,
    "signals_true": 5741,
    "signals_false": 2821,
    "long_signals": 2798,
    "short_signals": 2943
  }
}
```

**결과**:
- ✅ 5,741개 신호 발생
- ✅ LONG/SHORT 균형 (48.7% / 51.3%)
- ✅ 하루 평균 191.4개 신호

### 1.2 Engine Replay (PHASE27-5)

**실행**: `python scripts/research/phase27_5_btc5m_baseline_engine_replay.py`

**로그 출력**:
```
2025-12-04 22:04:03,891 [INFO] ✅ Trading Engine 종료: 총 캔들=8,821개, 진입 거래=0건, 종료 거래=0건, 활성 포지션=0개
2025-12-04 22:04:03,954 [WARNING] ⚠️  검증 실패: 거래 데이터 없음
2025-12-04 22:04:04,092 [WARNING] ⚠️  TradeActivityTracker Summary 파일 없음
```

**결과**:
- ❌ **0개 신호** (전체 기간)
- ❌ TradeActivityTracker Summary 파일 미생성
- ❌ 로그에서 "no_signals" 반복

---

## 2. 문제 분석

### 2.1 Signal Parity 실패

| 항목 | Offline Scan | Engine Replay | 차이 |
|------|--------------|---------------|------|
| **총 신호 수** | 5,741 | 0 | **100%** ❌ |
| **LONG 신호** | 2,798 | 0 | **100%** ❌ |
| **SHORT 신호** | 2,943 | 0 | **100%** ❌ |
| **평가 캔들 수** | 8,562 | 8,821 | +3.0% |

**판정**: **FAIL - 허용 범위(±10%) 초과**

### 2.2 가능한 원인

#### 원인 1: Ensemble 로직 차이

**Offline Scan**:
- 전략 `signal_logic()` 직접 호출
- Ensemble 우회

**Engine Replay**:
- Ensemble V2 사용 (`ensemble.enabled: true`)
- Ensemble이 모든 신호를 "skip: no_signals"로 처리

**가설**: Ensemble V2가 단일 전략 신호를 잘못 처리하고 있을 가능성

#### 원인 2: Config 파라미터 전달 실패

**Offline Scan**:
```python
# 파라미터 직접 전달
params = {
    'rsi_long_threshold': 42,
    'rsi_short_threshold': 58,
    ...
}
signal = signal_logic(df, params)
```

**Engine Replay**:
```yaml
# Config YAML을 통한 전달
strategies:
  btc5m_baseline_v1:
    rsi_long_threshold: 42
    ...
```

**가설**: Config 파라미터가 전략에 제대로 전달되지 않았을 가능성

#### 원인 3: Indicator 계산 차이

**Offline Scan**:
```python
df = add_indicators(df, ema_fast=20, rsi_len=14, use_adx=True, adx_period=14)
```

**Engine Replay**:
- Engine이 `add_indicators()` 호출
- 파라미터가 다르게 전달되었을 가능성

**가설**: ADX 또는 다른 지표 계산 결과가 다를 가능성

#### 원인 4: Data Loading 차이

**Offline Scan**:
- CSV 직접 로드
- `timestamp` → `time` 컬럼 정규화

**Engine Replay**:
- Backtest Adapter 사용
- 데이터 로딩 방식이 다를 가능성

**가설**: 데이터 형식 또는 기간 필터링 차이

#### 원인 5: TradeActivityTracker 미통합

**발견**:
- Engine의 `run()` 함수에 `activity_tracker` 파라미터 존재
- `run_v2()`에서 이를 생성/전달하지 않음

**영향**:
- Drop-off 분석 불가
- Summary JSON 미생성

---

## 3. 진단 계획

### 3.1 즉시 조사 항목

1. **Ensemble V2 로직 확인**:
   - `strategies/ensemble.py` 코드 리뷰
   - 단일 전략 처리 로직 확인
   - "skip: no_signals" 발생 조건 확인

2. **Config 파라미터 전달 확인**:
   - Engine 로그에서 전략 파라미터 출력 확인
   - `load_strategies()` 함수 디버깅

3. **Indicator 계산 비교**:
   - Offline Scan과 Engine Replay의 첫 100개 캔들 지표 값 비교
   - ADX, RSI, BB 값 일치 여부 확인

4. **Data Loading 확인**:
   - Backtest Adapter가 로드한 데이터 확인
   - 기간 필터링 정상 여부 확인

### 3.2 단기 해결 방안

**Option A: Ensemble 우회**:
```yaml
# Config 수정
ensemble:
  enabled: false  # Ensemble 비활성화

strategy:
  selector: btc5m_baseline_v1  # 단일 전략 직접 사용
```

**Option B: TradeActivityTracker 통합**:
```python
# execution/engine.py 수정
def run_v2(...):
    # TradeActivityTracker 생성
    if config.get('trade_activity_tracker', {}).get('enabled'):
        from metrics.trade_activity_tracker import TradeActivityTracker
        tracker = TradeActivityTracker(run_id=config['run_id'])
    else:
        tracker = None
    
    # run() 호출 시 전달
    run(..., activity_tracker=tracker)
```

**Option C: 간단한 디버그 스크립트**:
- Offline Scan과 동일한 방식으로 Engine 없이 신호만 확인
- Ensemble 로직을 직접 호출하여 차이 확인

---

## 4. 다음 단계

### 4.1 긴급 조치

1. **Ensemble 비활성화 테스트**:
   - Config에서 `ensemble.enabled: false` 설정
   - Engine Replay 재실행
   - 신호 발생 여부 확인

2. **전략 파라미터 로그 확인**:
   - Engine 로그에서 "PHASE23-1 DEBUG" 출력 확인
   - 파라미터가 제대로 전달되었는지 확인

3. **간단한 디버그 스크립트 작성**:
   - Ensemble 로직만 테스트
   - 단일 전략 신호 → Ensemble 입력 → 출력 확인

### 4.2 중기 조치

1. **TradeActivityTracker 통합**:
   - Engine에 TradeActivityTracker 생성/전달 로직 추가
   - Summary JSON 생성 확인

2. **Signal Parity 재검증**:
   - Ensemble 문제 해결 후 재실행
   - ±10% 이내 달성 여부 확인

3. **실행 보고서 작성**:
   - 문제 원인 및 해결 방법 문서화
   - PHASE27-5 최종 판정

---

## 5. 임시 판정

**PHASE27-5 Status**: 🔴 **BLOCKED**

**사유**:
- Signal Parity 100% 차이 (허용: ±10%)
- Engine Replay 0개 신호 (Offline Scan 5,741개)
- TradeActivityTracker 미작동

**다음 작업**:
1. Ensemble 비활성화 테스트
2. 전략 파라미터 전달 확인
3. 문제 원인 파악 및 수정

---

**작성일**: 2025-12-04  
**상태**: 🔴 **CRITICAL ISSUE**  
**다음 단계**: Ensemble 비활성화 테스트 및 원인 파악
