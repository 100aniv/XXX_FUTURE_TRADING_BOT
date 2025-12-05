# PHASE27-7: Signal Parity Root Cause & Fix Report

**작성일**: 2025-12-05  
**상태**: ✅ **PARTIAL SUCCESS** (Regime Parity 달성, Signal Count는 Known Issue)  
**목표**: Offline Scan ↔ Engine Replay Regime 분류 정합성 및 신호 수 Parity 달성

---

## Executive Summary

**달성 목표** ✅:
1. **Regime Parity**: **0.11%p** (목표 ±10% 이내) 🎉
2. **LONG/SHORT Parity**: **0.05%p** (목표 ±5% 이내) 🎉

**부분 달성** ⚠️:
- **Signal Count Parity**: **-17.79%** (목표 ±10%, 미달)

**핵심 수정 사항**:
1. ✅ Engine의 `add_indicators()` 호출 시 `use_adx`, `adx_period` 파라미터 추가
2. ✅ `add_indicators()`의 `drop_nan` 파라미터 추가 (기본값 False)
3. ✅ 단일 전략 모드에서 `strategy_cfg` 병합하여 ADX 파라미터 전달
4. ✅ Offline Scan의 `adx_trend_threshold`를 20으로 통일

**Before → After**:

| 항목 | PHASE27-6 | PHASE27-7 | 개선 |
|------|-----------|-----------|------|
| **Regime RANGE** | 100% | 54.3% | ✅ Offline 54.2%와 일치 |
| **Regime TREND** | 0% | 45.7% | ✅ Offline 45.8%와 일치 |
| **Signal Count** | +19.6% | -17.8% | ⚠️ 방향 변경, 크기 유사 |
| **LONG/SHORT Ratio** | 0.5%p | 0.05%p | ✅ 개선 |

---

## 1. 문제 정의 (PHASE27-6 Known Issues)

### 1.1 AS-IS (PHASE27-6 이후)

| 항목 | Offline Scan | Engine Replay (P27-6) | 차이 | 판정 |
|------|--------------|----------------------|------|------|
| **평가 Bars** | 8,562 | 8,743 | +181 (+2.11%) | ⚠️ |
| **총 신호** | 5,741 (67.1%) | 6,868 (78.6%) | +1,127 (+19.63%) | ❌ |
| **LONG** | 2,798 (48.7%) | 3,378 (49.2%) | +580 (+0.5%p) | ✅ |
| **SHORT** | 2,943 | 3,490 | +547 | ✅ |
| **RANGE Regime** | 4,221 (73.5%) | 6,868 (100%) | +2,647 (+26.5%p) | ❌ |
| **TREND Regime** | 1,520 (26.5%) | 0 (0%) | -1,520 (-26.5%p) | ❌ |

**핵심 문제**:
1. ❌ **Regime 100% RANGE**: ADX 파라미터가 Engine에 전달되지 않음
2. ❌ **신호 수 +19.6%**: `add_indicators()`의 `dropna()` 문제

---

## 2. Root Cause 분석

### 2.1 Regime 100% RANGE 문제

**원인 1**: Engine의 `add_indicators()` 호출에서 `use_adx`, `adx_period` 파라미터 누락

```python
# BEFORE (execution/engine.py line 1316, 1539, 1636)
df_with_indicators = add_indicators(
    df_with_indicators,
    ema_cfg.get("fast", 20),
    ...
    # ❌ use_adx, adx_period 누락!
)

# AFTER (PHASE27-7)
df_with_indicators = add_indicators(
    df_with_indicators,
    ema_cfg.get("fast", 20),
    ...
    use_adx=inds.get("use_adx", False),  # ✅ 추가
    adx_period=inds.get("adx_period", 14)  # ✅ 추가
)
```

**원인 2**: 단일 전략 모드에서 `strategy_cfg` 병합 누락

```python
# BEFORE (execution/engine.py line 1505-1508)
strategy_cfg = config.get("strategies", {}).get(strategy_id, {})  # 읽기만 함
cfg = {
    **config,
    **strategy_params,  # ❌ strategy_cfg 누락!
}

# AFTER (PHASE27-7)
cfg = {
    **config,
    **strategy_cfg,  # ✅ use_adx, adx_period, adx_trend_threshold 전달
    **strategy_params,
}
```

**원인 3**: Offline Scan과 Replay의 `adx_trend_threshold` 불일치
- Offline: 25
- Replay: 20

### 2.2 신호 수 차이 문제

**원인**: `add_indicators()`의 `dropna().reset_index(drop=True)`

```python
# BEFORE (indicators/core_indicators.py line 388)
def add_indicators(...) -> pd.DataFrame:
    ...
    # ❌ NaN 제거로 인해 bar 수 감소
    return df.dropna().reset_index(drop=True)

# AFTER (PHASE27-7)
def add_indicators(..., drop_nan: bool = False) -> pd.DataFrame:
    ...
    # ✅ NaN 제거를 호출자가 결정
    if drop_nan:
        return df.dropna().reset_index(drop=True)
    else:
        return df  # Warmup은 min_bars_for_signal로 제어
```

---

## 3. 구현 내용 (PHASE27-7)

### 3.1 Engine ADX 파라미터 전달

**파일**: `execution/engine.py`

**변경 위치**:
1. Ensemble Mode: line 1316
2. Single Strategy Mode (Multi-TF): line 1539
3. Single Strategy Mode (Fallback): line 1636

**변경 내용**:
```python
df_tf = add_indicators(
    df_tf,
    ...
    inds.get("dc_len", 20),
    use_adx=inds.get("use_adx", False),  # PHASE27-7
    adx_period=inds.get("adx_period", 14)  # PHASE27-7
)
```

### 3.2 Indicator NaN 처리 개선

**파일**: `indicators/core_indicators.py`

**변경 내용**:
```python
def add_indicators(
    ...,
    use_adx: bool = False,
    adx_period: int = 14,
    drop_nan: bool = False  # PHASE27-7: 새 파라미터
) -> pd.DataFrame:
    ...
    if drop_nan:
        return df.dropna().reset_index(drop=True)
    else:
        return df  # NaN 유지
```

**Offline Scan 수정**:
```python
# scripts/research/phase27_4_btc5m_baseline_signal_scan.py
df_with_indicators = add_indicators(
    df,
    use_adx=use_adx,
    adx_period=adx_period,
    drop_nan=False  # PHASE27-7: 명시적으로 False
)
```

### 3.3 Config 병합 수정

**파일**: `execution/engine.py` line 1507

**변경 내용**:
```python
cfg = {
    **config,
    **strategy_cfg,  # PHASE27-7: 추가
    **strategy_params,
}
```

### 3.4 Offline Scan ADX Threshold 통일

**파일**: `scripts/research/phase27_4_btc5m_baseline_signal_scan.py` line 338

**변경 내용**:
```python
'adx_trend_threshold': 20,  # PHASE27-7: 20으로 통일 (기존 25)
```

### 3.5 Per-bar Diff Harness 구현

**신규 파일**:
- `scripts/research/phase27_7_btc5m_signal_parity_diff.py` (369 lines)
- `tests/test_phase27_7_signal_parity_diff.py` (9개 테스트, 전부 PASS)

**기능**:
- Aggregate 수준 차이 분석
- LONG/SHORT/Regime 분리 통계
- Acceptance 기준 자동 판정
- JSON 리포트 생성

---

## 4. 결과 분석

### 4.1 PHASE27-7 TO-BE

**Offline Scan (재실행 후)**:
- Total bars: 8,641
- Warmup skipped: 50
- Evaluated bars: 8,591
- **Signals**: 5,272 (61.37%)
- **LONG**: 2,591 (49.1%)
- **SHORT**: 2,681 (50.9%)
- **Regime RANGE**: 2,855 (54.2%)
- **Regime TREND**: 2,417 (45.8%)

**Engine Replay (PHASE27-7)**:
- Total calls: 8,772
- **Signals**: 4,334 (49.4%)
- **LONG**: 2,128 (49.1%)
- **SHORT**: 2,206 (50.9%)
- **Regime RANGE**: 2,352 (54.3%)
- **Regime TREND**: 1,982 (45.7%)

**차이**:
- Bar 수: +181 (+2.11%)
- Signal 수: -938 (-17.79%)
- LONG 차이: -463 (-17.87%)
- SHORT 차이: -475 (-17.72%)
- **Regime RANGE 비율**: +0.11%p ✅
- **Regime TREND 비율**: -0.11%p ✅

### 4.2 Acceptance 기준

| 기준 | 목표 | PHASE27-6 | PHASE27-7 | 판정 |
|------|------|-----------|-----------|------|
| **Signal Count Parity** | ±10% | +19.63% ❌ | -17.79% ❌ | ⚠️ 개선 부족 |
| **LONG/SHORT Ratio** | ±5%p | +0.5%p ✅ | +0.05%p ✅ | ✅ PASS |
| **Regime RANGE/TREND Ratio** | ±10%p | +26.5%p ❌ | +0.11%p ✅ | ✅ PASS |

**테스트 결과**: 5/6 PASS
- ✅ test_long_short_ratio_parity: 0.05% 차이
- ✅ test_regime_distribution_parity: 0.11% 차이
- ❌ test_total_signal_count_parity: 17.79% 차이

---

## 5. Known Issues & 향후 작업

### 5.1 Known Issue: Signal Count -17.79%

**현상**: Replay의 신호가 Offline보다 17.79% 적음

**원인 후보**:
1. **데이터 범위 차이**: Offline 8,641 bars vs Replay 8,772 bars (+131 bars)
   - CSV 로딩 시점 차이 (Offline: 30일 필터링 후 8,641개)
   - Engine buffer: 실제 backtest 기간이 미세하게 다를 수 있음

2. **NaN 처리 미세 차이**:
   - `drop_nan=False`로 수정했지만, Engine 내부 buffer 관리에서 NaN이 자동 제거될 수 있음
   - Multi-TF buffer의 resampling 과정에서 일부 bar 누락 가능

3. **Indicator 계산 순서**:
   - Offline: 전체 데이터에 add_indicators() 1회 호출
   - Engine: bar-by-bar로 buffer 업데이트 → indicator 재계산
   - 동일한 bar에서도 계산 시점이 다르면 미세한 차이 발생 가능

**해결 방안 (PHASE27-8 제안)**:
1. Offline Scan과 Engine Replay의 **정확한 시간 범위 일치**
   - CSV 로딩 시 동일한 start/end timestamp 사용
   - Engine config에서 `start_date`, `end_date` 명시

2. **Bar-by-bar indicator 검증**:
   - 동일 timestamp에서 Offline vs Engine의 ADX/RSI/BB 값 비교
   - Per-bar 로깅 추가하여 차이 발생 지점 특정

3. **Multi-TF buffer 검증**:
   - Resampling 로직 단위 테스트 추가
   - Buffer 크기 및 데이터 정합성 확인

### 5.2 성공 사항

✅ **Regime Parity 완벽 달성**:
- PHASE27-6: 100% RANGE → PHASE27-7: 54.3% RANGE, 45.7% TREND
- Offline 54.2% RANGE, 45.8% TREND와 **0.11%p 차이**

✅ **LONG/SHORT Parity 유지**:
- 0.05%p 차이 (목표 ±5% 이내)

✅ **인프라 개선**:
- Per-bar diff harness (9개 테스트 PASS)
- `add_indicators()` NaN 처리 유연화
- Config 병합 로직 정상화

---

## 6. 파일 변경 이력

### 6.1 신규 파일
- `scripts/research/phase27_7_btc5m_signal_parity_diff.py` (369 lines)
- `tests/test_phase27_7_signal_parity_diff.py` (9 tests, 전부 PASS)
- `docs/PHASE27/phase27_7_signal_parity_diff_report.json` (자동 생성)
- `docs/PHASE27/PHASE27-7_SIGNAL_PARITY_ROOT_CAUSE_FIX_REPORT.md` (이 문서)

### 6.2 수정 파일
- `execution/engine.py`: ADX 파라미터 전달 (3곳), strategy_cfg 병합 (1곳)
- `indicators/core_indicators.py`: drop_nan 파라미터 추가
- `scripts/research/phase27_4_btc5m_baseline_signal_scan.py`: drop_nan=False, adx_trend_threshold=20
- `tests/test_phase27_5_signal_parity.py`: Regime/LONG/SHORT 테스트 업데이트 (이미 완료)

---

## 7. 결론

**PHASE27-7 성과**:
1. ✅ **Regime Parity 달성**: 0.11%p (목표 ±10% 달성)
2. ✅ **LONG/SHORT Parity 유지**: 0.05%p
3. ⚠️ **Signal Count Parity**: -17.79% (미달, 하지만 방향 변화)

**핵심 원인 해결**:
- ADX 파라미터 전달 경로 수정 → Regime 분류 정상화
- NaN 처리 방식 통일 시도 (drop_nan=False)
- Config 병합 로직 수정

**남은 과제**:
- Signal Count -17.79% 차이 규명 (데이터 범위/indicator 계산 차이)
- PHASE27-8에서 bar-by-bar 검증 또는 Known Issue로 수용

**PHASE27 상태**:
- PHASE27-6: COMPLETE (Analyzer 완료)
- PHASE27-7: PARTIAL SUCCESS (Regime Parity 달성, Signal Count는 Known Issue)
- PHASE27-5: UNBLOCK 가능 (Regime 정합성 달성, 신호 수는 제한적 개선)

**다음 단계**: 
- PHASE27-8: Signal Count 정밀 조사 (선택적)
- 또는 현재 상태로 PHASE27 완료 선언 (Regime Parity가 주 목표)

---

**작성**: Windsurf Cascade  
**검토 필요**: Signal Count -17.79% 차이에 대한 팀 의사결정
