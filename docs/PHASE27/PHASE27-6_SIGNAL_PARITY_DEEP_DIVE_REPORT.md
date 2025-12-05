# PHASE27-6: Signal Parity Deep Dive Report

**작성일**: 2025-12-05  
**상태**: 🔄 **IN PROGRESS** (Analyzer 완료, 신호 차이 원인 조사 중)  
**목표**: Offline Scan ↔ Engine Replay 신호 정합성 심층 분석 및 개선

---

## Executive Summary

**문제**: PHASE27-5A에서 신호 생성 복구 후에도 **19.6% 신호 수 차이** 존재 (허용: ±10%)  
**목표**: Bar-level 정합성 분석, LONG/SHORT/Regime 카운트 분리, 원인 규명  
**결과**: 
- ✅ Signal Parity Analyzer 구현 완료
- ✅ TradeActivityTracker에 LONG/SHORT/Regime 카운트 추가
- ✅ LONG/SHORT 비율 정합성 확인: 차이 **0.5%p** (매우 양호)
- ⚠️ **신호 수 차이 19.63% 지속** (허용 10% 초과)
- ⚠️ **Regime 분류 불일치**: Offline 73.5% RANGE vs Replay 100% RANGE

---

## 1. 문제 정의

### 1.1 AS-IS (PHASE27-5A 이후)

| 항목 | Offline Scan | Engine Replay | 차이 | 판정 |
|------|--------------|---------------|------|------|
| **평가 Bars** | 8,562 | 8,743 | +181 (+2.11%) | ⚠️ |
| **총 신호** | 5,741 (67.1%) | 6,868 (78.6%) | +1,127 (+19.63%) | ❌ |
| **LONG** | 2,798 (48.7%) | 3,378 (49.2%) | +580 (+0.5%p) | ✅ |
| **SHORT** | 2,943 | 3,490 | +547 | ✅ |
| **RANGE Regime** | 4,221 (73.5%) | 6,868 (100%) | +2,647 (+26.5%p) | ❌ |
| **TREND Regime** | 1,520 (26.5%) | 0 (0%) | -1,520 (-26.5%p) | ❌ |

**Acceptance 기준**:
- ✅ LONG/SHORT 비율: 차이 0.5%p (목표 ±5% 이내)
- ❌ 총 신호 수: 차이 19.63% (목표 ±10% 이내)
- ❌ Regime 분류: 26.5%p 차이

---

## 2. 구현 내용

### 2.1 Signal Parity Analyzer

**파일**: `scripts/research/phase27_6_signal_parity_analyzer.py`

**기능**:
- Aggregate 수준 정합성 분석 (총 신호 수, Bar 수, Signal Rate)
- LONG/SHORT/Regime 분리 통계
- Warmup/NaN 처리 방식 비교
- 자동 권장사항 생성

**출력**: `docs/PHASE27/phase27_6_signal_parity_analysis.json`

**테스트**: `tests/test_phase27_6_signal_parity_analyzer.py`
- Mock 데이터 기반 단위 테스트
- 실제 Summary 파일 통합 테스트
- 13개 테스트 전부 PASS

### 2.2 TradeActivityTracker 확장

**파일**: `metrics/trade_activity_tracker.py`

**변경 사항**:

```python
# BEFORE (PHASE27-0)
def record_strategy_signal(self, symbol: str, strategy_id: str, has_signal: bool):
    ...

# AFTER (PHASE27-6)
def record_strategy_signal(
    self,
    symbol: str,
    strategy_id: str,
    has_signal: bool,
    side: Optional[str] = None,      # NEW: LONG/SHORT
    regime: Optional[str] = None     # NEW: RANGE/TREND
):
    ...
    if has_signal:
        if side == "LONG":
            strategy_data["long_signals"] += 1
        elif side == "SHORT":
            strategy_data["short_signals"] += 1
        
        if "RANGE" in regime:
            strategy_data["regime_range"] += 1
        elif "TREND" in regime:
            strategy_data["regime_trend"] += 1
```

**Summary JSON 구조 변경**:

```json
{
  "totals": {
    "strategy_signals_total": 8743,
    "strategy_signals_true": 6868,
    "long_signals": 3378,          // NEW
    "short_signals": 3490,         // NEW
    "regime_range": 6868,          // NEW
    "regime_trend": 0              // NEW
  }
}
```

### 2.3 Engine Hook 업데이트

**파일**: `execution/engine.py`

**변경 위치**:
1. **Single Strategy Mode** (line 1661~1673)
2. **Ensemble Mode** (line 1354~1366)

**변경 내용**:

```python
# BEFORE
if activity_tracker:
    activity_tracker.record_strategy_signal(
        symbol=candle_symbol,
        strategy_id=strategy_id,
        has_signal=(signal is not None and signal.get('side') is not None)
    )

# AFTER
if activity_tracker:
    has_signal = (signal is not None and signal.get('side') is not None)
    side = signal.get('side') if has_signal else None
    regime = signal.get('metadata', {}).get('regime') if has_signal else None
    
    activity_tracker.record_strategy_signal(
        symbol=candle_symbol,
        strategy_id=strategy_id,
        has_signal=has_signal,
        side=side,      # NEW
        regime=regime   # NEW
    )
```

### 2.4 Signal Parity 테스트 업데이트

**파일**: `tests/test_phase27_5_signal_parity.py`

**변경 사항**:
- `test_long_short_ratio_parity()`: `totals.long_signals` 사용
- `test_regime_distribution_parity()`: `totals.regime_range`, `totals.regime_trend` 사용
- Tracker 업데이트 전/후 호환성 유지 (skip 로직)

---

## 3. 분석 결과

### 3.1 Aggregate Parity 분석

**Signal Count Parity**: ❌ FAIL
- Offline: 5,741개 신호 (67.1%)
- Replay: 6,868개 신호 (78.6%)
- 차이: +1,127개 (+19.63%)
- **원인 후보**:
  1. **Bar 수 차이 (+2.11%)**: Warmup 처리 방식 불일치
  2. **Indicator 계산 차이**: add_indicators() vs Offline Scan의 지표 계산
  3. **NaN 처리 차이**: Engine buffer의 NaN 제거 로직
  4. **Config Propagation**: 전략 파라미터 전달 방식 차이

**LONG/SHORT Ratio Parity**: ✅ PASS
- Offline: LONG 48.7% (2,798/5,741)
- Replay: LONG 49.2% (3,378/6,868)
- 차이: **0.5%p** (목표 ±5% 이내)
- **결론**: LONG/SHORT 비율은 거의 일치 → 신호 생성 로직 자체는 정상

**Regime Classification Parity**: ❌ FAIL
- Offline: RANGE 73.5% (4,221), TREND 26.5% (1,520)
- Replay: RANGE 100% (6,868), TREND 0% (0)
- 차이: **26.5%p**
- **원인 후보**:
  1. `adx_trend_threshold` 파라미터 불일치 (Offline: 25, Replay: 20)
  2. ADX 계산 결과 차이 (Offline vs Engine)
  3. Signal metadata의 `regime` 설정 방식 차이

### 3.2 Warmup/NaN 처리 분석

**Offline Scan**:
- 고정 50 bars warmup (hardcoded)
- `for i in range(min_bars, len(df))` 방식

**Engine Replay**:
- Indicator별 warmup 기간 (RSI: 14, ADX: 14 등)
- `min_bars_for_signal` config 사용 (50으로 설정)
- add_indicators() 내부 NaN 처리

**잠재적 문제**:
- add_indicators()가 indicator별로 다른 warmup을 적용할 수 있음
- NaN dropna() 처리 시점 차이
- Buffer 관리 방식 차이 (Engine은 rolling window)

---

## 4. 권장사항

### 우선순위 HIGH

#### 1. Signal Count Parity 수정
**문제**: 19.6% 차이 (허용: 10%)

**Action Items**:
1. Offline Scan과 Engine Replay의 **indicator 계산 경로 확인**
   - add_indicators() 함수의 warmup 처리 통일
   - NaN 처리 로직 일치 확인
2. **signal_logic()와 BaseStrategy.compute_signal() 동등성 검증**
   - 두 함수가 동일한 df를 받았을 때 같은 신호를 생성하는지 확인
   - Per-bar 로깅 추가하여 차이 발생 시점 특정
3. **Config 전달 방식 검증**
   - Offline Scan의 base_config와 Engine의 strategy params 일치 확인

### 우선순위 MEDIUM

#### 2. Bar Count Parity 개선
**문제**: 2.1% 차이 (8,562 vs 8,743)

**Action Items**:
1. Offline의 warmup (50 bars)와 Engine의 `min_bars_for_signal` 일치 확인
2. CSV 로딩 시 timestamp 변환 일관성 확인
3. Engine buffer의 데이터 범위 검증

#### 3. Regime Classification Parity 조사
**문제**: 26.5%p 차이 (Replay는 모든 신호가 RANGE)

**Action Items**:
1. **Offline vs Replay ADX 계산 결과 비교**
   - 동일 bar에서 ADX 값이 같은지 확인
   - Per-bar ADX 로깅 추가
2. **adx_trend_threshold 파라미터 일치 확인**
   - Offline: 25 (base_config)
   - Replay: 20 (phase27_5_baseline_replay_30d.yml)
   - **조치**: 두 값을 동일하게 맞춰서 재실행
3. **Signal metadata의 regime 설정 방식 검증**
   - btc5m_baseline_v1.py에서 regime 분류 로직 확인
   - Engine Hook에서 metadata.regime 추출 방식 검증

---

## 5. Known Issues

### 5.1 Regime 분류 100% RANGE 문제

**현상**: Engine Replay에서 모든 신호가 RANGE로 분류됨 (TREND 0개)

**가능한 원인**:
1. **Config 불일치**: 
   - Offline Scan: `adx_trend_threshold: 25`
   - Replay Config: `adx_trend_threshold: 20`
   - 하지만 threshold가 낮아지면 TREND가 더 많이 나와야 맞음 → 역설
2. **ADX 계산 차이**:
   - Offline Scan과 Engine의 add_indicators()가 다른 ADX 값 생성
   - Engine에서 ADX 컬럼이 없거나 NaN일 가능성
3. **Regime 설정 로직**:
   - `btc5m_baseline_v1.py`의 `signal_logic()`에서:
     ```python
     if use_adx and adx_col in df.columns:
         regime = "TREND" if adx >= adx_trend_threshold else "RANGE"
     else:
         regime = "RANGE (ADX OFF)"
     ```
   - Engine에서 ADX 컬럼을 찾지 못해 "RANGE (ADX OFF)"로 설정되었을 가능성

**임시 해결책**: Known Issue로 문서화, PHASE27-7에서 조사

### 5.2 신호 수 19.6% 차이

**현상**: Offline (5,741) vs Replay (6,868), +19.6%

**가능한 원인**:
1. **Warmup 처리**: Bar 수 차이 +2.1% (181개) → 신호 차이 일부 설명
2. **Indicator 계산**: add_indicators()와 Offline의 지표 계산 결과가 다를 수 있음
3. **NaN 처리**: Engine buffer의 NaN 제거 시점이 다를 수 있음

**다음 단계**: PHASE27-7에서 per-bar 로깅을 추가하여 정확한 차이 발생 지점 특정

---

## 6. Next Steps

### PHASE27-7 (제안)

**목표**: 신호 수 19.6% 차이 및 Regime 100% RANGE 원인 규명

**작업**:
1. **Per-bar 로깅 추가**:
   - Offline Scan과 Engine Replay에 per-bar signal 로깅
   - 동일 timestamp에서 신호 불일치 지점 특정
2. **ADX 계산 검증**:
   - add_indicators()와 Offline Scan의 ADX 계산 결과 비교
   - Per-bar ADX 값 로깅
3. **Config 통일**:
   - adx_trend_threshold를 25로 통일하여 재실행
   - 다른 파라미터도 완전 일치 확인
4. **Indicator 계산 경로 통일**:
   - Offline Scan도 add_indicators() 사용하도록 수정
   - 또는 Engine도 Offline과 동일한 방식 사용

### PHASE28 이후

**목표**: Signal Pipeline Production Ready

**전제 조건**:
- Signal Parity ±10% 달성
- Regime 분류 정합성 확보
- LONG/SHORT 비율 정합성 유지 (현재 0.5%p, 양호)

---

## 7. 부록

### 7.1 파일 변경 이력

**신규 파일**:
- `scripts/research/phase27_6_signal_parity_analyzer.py` (343 lines)
- `tests/test_phase27_6_signal_parity_analyzer.py` (403 lines)
- `docs/PHASE27/phase27_6_signal_parity_analysis.json` (자동 생성)
- `docs/PHASE27/PHASE27-6_SIGNAL_PARITY_DEEP_DIVE_REPORT.md` (이 문서)

**수정 파일**:
- `metrics/trade_activity_tracker.py`: LONG/SHORT/Regime 카운트 추가 (46 lines modified)
- `execution/engine.py`: Engine Hook 업데이트 (12 lines modified, 2 locations)
- `tests/test_phase27_5_signal_parity.py`: LONG/SHORT/Regime 테스트 업데이트 (34 lines modified)

### 7.2 실행 로그

**Engine Replay (PHASE27-6)**:
- 실행 시간: ~3분 30초
- Summary: `docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json`
- 결과:
  - Total calls: 8,743
  - Signals: 6,868 (78.6%)
  - LONG: 3,378 (49.2%)
  - SHORT: 3,490 (50.8%)
  - Regime RANGE: 6,868 (100%)
  - Regime TREND: 0 (0%)

**Signal Parity Analyzer**:
- 실행 시간: <1초
- 출력: `phase27_6_signal_parity_analysis.json`
- 권장사항: 3개 (HIGH: 1, MEDIUM: 2)

### 7.3 테스트 결과

**Analyzer 테스트**: 13/13 PASS
- TestExtractOfflineSignals: 3/3 PASS
- TestAnalyzeAggregateParity: 4/4 PASS
- TestAnalyzeWarmupNanHandling: 1/1 PASS
- TestGenerateRecommendations: 3/3 PASS
- TestRealDataIntegration: 2/2 PASS

**기존 테스트**: 
- `test_phase27_5_signal_parity.py`: LONG/SHORT 테스트 활성화 가능 (현재 skip)

---

## 결론

PHASE27-6에서 다음을 달성했습니다:

✅ **완료**:
1. Signal Parity Analyzer 구현 및 테스트
2. TradeActivityTracker LONG/SHORT/Regime 카운트 추가
3. Engine Hook 업데이트 (Ensemble + Single 모드)
4. LONG/SHORT 비율 정합성 확인 (0.5%p 차이, 매우 양호)

⚠️ **Known Issues** (PHASE27-7에서 해결 필요):
1. 신호 수 19.63% 차이 (목표: ±10%)
2. Regime 분류 100% RANGE (Offline 73.5% vs Replay 100%)

**다음 단계**: PHASE27-7에서 per-bar 로깅을 추가하여 정확한 차이 원인을 규명하고, Signal Parity ±10% 목표를 달성한 후 PHASE27을 완료합니다.

---

**작성**: Windsurf Cascade  
**검토 필요**: PHASE27-7 착수 전 Known Issues 우선순위 재검토
