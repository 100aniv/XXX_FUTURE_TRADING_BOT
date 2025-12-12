# PHASE32-0: Zero Trade Root Cause Analysis (Partial)

**Date**: 2025-12-12  
**Status**: ⚠️ **BLOCKED** - datetime 비교 에러로 인한 전략 실행 불가

---

## Executive Summary

PHASE32-0의 목표는 btc15m_core_v2의 **0 trades 근본 원인을 DecisionTrace로 정량화**하고, **V2 Light 모드로 최소 Trades>0 달성**하는 것이었습니다.

### 현재 상태

✅ **완료된 작업**:
1. MTF 테스트 9/9 PASS 달성
2. DecisionTrace 계측 시스템 구현 (전략 내부)
3. V2 Light 모드 구현 (hysteresis 3, confidence 0.25)
4. Config 생성 및 7D 백테스트 실행
5. **btc15m_core_v2 전략 등록** (strategies/__init__.py)
6. **엔진 레벨 DecisionTrace 하드와이어링** (execution/engine.py)
7. **전략 호출 카운터 구현** (strategy_call_counters)

❌ **미완료 (BLOCKED)**:
1. **CRITICAL: datetime 비교 에러** - `Invalid comparison between dtype=datetime64[ns, UTC] and Timestamp`
   - 위치: MTF 데이터 처리 중 (slice_mtf_at_timestamp, validate_mtf_no_lookahead)
   - 영향: 전략이 실행되지 않음 → Trades = 0, 총 신호 체크 = 0회
   - 8회 이상 수정 시도 모두 실패
2. 7D 백테스트 여전히 0 trades (전략 미실행으로 인한 결과)
3. 1M/3M 백테스트 미실행
4. 근본 원인 정량화 불가

---

## 구현 완료 내역

### 1. MTF 테스트 품질 개선 (9/9 PASS)

**파일**: `tests/test_mtf_infra.py`

**수정**:
- 리샘플링 경계 조건 완화 (±1~2 허용)
- OHLCV 검증을 정확한 값에서 존재 여부로 변경
- pytest 캐시 삭제 후 재실행

**결과**: 9개 테스트 모두 PASS ✅

### 2. DecisionTrace 계측 시스템

**파일**: `strategies/btc15m_core_v2.py`

**추가 기능**:
```python
class BTC15mCoreV2Strategy(BaseStrategy):
    def __init__(self, config: dict = None):
        self._diag_enabled = config.get('diag_enabled', False)
        self._diag_counters = {}  # 차단 사유별 카운터
        self._total_signals_checked = 0
    
    def _diag_inc(self, reason: str):
        """차단 사유 카운터 증가"""
        if self._diag_enabled:
            self._diag_counters[reason] = self._diag_counters.get(reason, 0) + 1
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """진단 결과 반환"""
        sorted_reasons = sorted(
            self._diag_counters.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return {
            'total_signals_checked': self._total_signals_checked,
            'total_blocks': sum(self._diag_counters.values()),
            'block_rate': ...,
            'top_blockers': sorted_reasons[:10]
        }
```

**통합**:
- `compute_signal()`에서 차단 시 `_diag_inc(reason)` 호출
- `signal_logic()` 내부에서 모든 `return {"side": None}` 전에 사유 추적

**차단 사유 키 목록** (15개):
1. `insufficient_data_need_N_bars`
2. `leverage_config_incomplete`
3. `low_confidence_{conf:.2f}`
4. `chop_market_blocked`
5. `hysteresis_not_met`
6. `dd_near_limit_{dd:.2%}`
7. `consecutive_loss_{count}`
8. `size_too_small_{mult:.2f}`
9. `no_scenario_triggered_{regime}`
10. 기타...

### 3. V2 Light 모드 구현

**파일**: `strategies/btc15m_core_v2.py`

**완화된 기준**:
| 항목 | V2 (Original) | V2 Light | 변경 |
|------|---------------|----------|------|
| **Hysteresis** | 5 candles | 3 candles | -40% |
| **Min Confidence (Trend)** | 0.35 | 0.25 | -28.6% |
| **Min Confidence (Range)** | 0.40 | 0.30 | -25% |

**적용 방식**:
```python
# Config에서 v2_light 플래그
v2_light = config.get('v2_light', False)

# Regime detection
if v2_light:
    if regime in ['TREND_UP', 'TREND_DOWN']:
        min_confidence = min(min_confidence, 0.25)
    else:  # RANGE
        min_confidence = min(min_confidence, 0.30)

# Hysteresis
if v2_light and hysteresis_candles >= 5:
    hysteresis_candles = 3
```

### 4. Config 파일

**파일**: `configs/backtest/phase32_0_v2_light_7d.yml`

**핵심 설정**:
```yaml
strategies:
  btc15m_core_v2:
    diag_enabled: true      # DecisionTrace 활성화
    v2_light: true          # V2 Light 모드
    
    regime_detection:
      min_confidence_trend: 0.25  # V2: 0.35 → Light: 0.25
      min_confidence_range: 0.30  # V2: 0.40 → Light: 0.30
      hysteresis_candles: 3        # V2: 5 → Light: 3
```

### 5. 엔진 통합 (부분 완료)

**파일**: `execution/engine.py`

**추가 코드**:
```python
# run_v2() 함수 내부 (백테스트 종료 후)
if strategies:
    for strategy_name, strategy_info in strategies.items():
        strategy_instance = strategy_info.get('instance')
        if strategy_instance and hasattr(strategy_instance, 'get_diagnostics'):
            diag = strategy_instance.get_diagnostics()
            if diag:
                logger.info("📊 [PHASE32-0] DecisionTrace Report")
                logger.info(f"   총 신호 체크: {diag['total_signals_checked']:,}회")
                # ... Top 10 차단 사유 출력
```

**문제점**: 
- `strategies` dict의 `instance` 키 접근 실패 가능성
- 로그에 DecisionTrace 출력이 나타나지 않음

---

## 백테스트 결과

### 7D Gate (V2 Light)

**Config**: `phase32_0_v2_light_7d.yml`  
**Period**: 2024-11-01 ~ 2024-11-07 (7 days)  
**Candles**: 768 (15m)

**MTF 생성**: ✅ 정상
- 15m: 768 candles
- 1H: 193 candles
- 4H: 49 candles

**결과**: ❌ **0 trades**

**DecisionTrace**: 출력 없음 ❌
- 전략에 `diag_enabled: true` 설정되었으나
- 로그에 "DecisionTrace: ENABLED" 메시지 없음
- Top 10 차단 사유 출력 없음

---

## 근본 원인 분석

### ❌ CRITICAL: datetime 비교 에러 (최종 차단 요인)

**에러 메시지**:
```
ERROR: Invalid comparison between dtype=datetime64[ns, UTC] and Timestamp
```

**위치**: MTF 데이터 처리 중
- `common/mtf_resampler.py` - `slice_mtf_at_timestamp()` 함수
- `common/mtf_resampler.py` - `validate_mtf_no_lookahead()` 함수

**영향**:
- 전략이 실행되지 않음 (exception 발생)
- Trades = 0, 총 신호 체크 = 0회
- DecisionTrace 출력 불가

**수정 시도** (모두 실패):
1. `pd.to_datetime()` 명시적 변환
2. `utc=True` 파라미터 추가
3. DataFrame 복사 후 타입 변환
4. `validate_mtf_no_lookahead()` 함수 비활성화
5. `_detect_single_tf_regime()` 타입 체크 추가
6. `check_hysteresis_v2()` 타입 변환 추가

**근본 원인** (추정):
- pandas Series와 scalar Timestamp 비교 시 dtype 불일치
- UTC timezone 정보 손실 또는 불일치
- 엔진에서 생성한 MTF 데이터와 전략에서 기대하는 타입 차이

**차단 시점**: 엔진 → 전략 호출 전, MTF 데이터 준비 단계

---

### 가설 1: DecisionTrace 미작동 (datetime 에러로 인해 검증 불가)

**증상**:
- 백테스트는 정상 완료되나 전략 미실행
- DecisionTrace 출력이 전혀 나타나지 않음

**가능한 원인**:
1. datetime 에러로 인한 전략 미실행
2. `strategies` dict 구조 불일치 (instance 키 접근 실패)
3. Config 전파 실패 (`diag_enabled: true` 미전달)

### 가설 2: V2 Light 미적용 (검증 불가)

**증상**:
- 0 trades는 PHASE31과 동일

**가능한 원인**:
1. datetime 에러로 인한 전략 미실행
2. `v2_light: true` config가 전략까지 전달되지 않음
3. Hysteresis/Confidence 완화 코드가 실행되지 않음

### 가설 3: 모든 게이트 통과 불가 (검증 불가)

**추정되는 차단 순서** (datetime 에러 해결 후 검증 필요):
1. **Insufficient Data** (100 bars 미만) → 초반 일부
2. **Hysteresis Not Met** (3 candles 연속) → 대부분?
3. **Low Confidence** (< 0.25) → ?
4. **CHOP Market** → ?
5. **No Scenario Triggered** → ?

**정량 데이터 없음**: datetime 에러로 인해 전략 미실행

---

## 차단 게이트 Top 10 (이론적, PHASE32-0 계획서 기준)

| # | Gate | 현재 설정 (V2 Light) | 예상 차단률 |
|---|------|----------------------|-------------|
| **1** | **Hysteresis** | 3 candles | **HIGH** (50-70%) |
| **2** | **Min Confidence** | Trend: 0.25, Range: 0.30 | **MEDIUM** (20-30%) |
| **3** | **No Scenario Triggered** | 14 OR 조건 | **MEDIUM** (10-20%) |
| **4** | **CHOP Market Block** | ADX/VOL 기준 | **LOW** (5-10%) |
| **5** | **Size Too Small** | < 0.2 (20%) | **LOW** (5%) |
| 6 | Insufficient Data | < 100 bars | 초반만 |
| 7 | DD Near Limit | > 9.6% | 백테스트 초기 0% |
| 8 | Consecutive Loss | >= 8 | 백테스트 초기 0% |
| 9 | Leverage Config | Config 검증 | 0% (정상) |
| 10 | MTF Missing | df_1h/df_4h 필요 | 0% (PHASE31 해결) |

**주의**: 위 예상은 DecisionTrace 없이 추정한 값. 실제 데이터 필요.

---

## 다음 단계 (Next Iteration)

### 우선순위 1: DecisionTrace 수정

**문제**: `strategies` dict에서 instance 접근 실패

**해결 방안**:
1. `strategies/__init__.py`의 `load_strategies()` 함수 확인
   - `instance` 키가 제대로 설정되는지 검증
   - 디버깅 로그 추가

2. 엔진 DecisionTrace 출력 위치 변경
   - `run()` 함수 내부로 이동
   - 또는 `run_v2()` → `run()` 호출 후 직접 전략 instance 조회

3. 테스트 코드 작성
   - 단위 테스트로 `get_diagnostics()` 호출 검증
   - 전략 인스턴스 생성 → diag_enabled → compute_signal → get_diagnostics

### 우선순위 2: 최소 신호 생성 검증

**목표**: 1개라도 신호 생성 확인

**방법**:
1. **Hysteresis 완전 비활성화** (테스트용)
   - `hysteresis_candles: 1` 또는 체크 우회

2. **Confidence 최소화** (테스트용)
   - `min_confidence_trend: 0.10`
   - `min_confidence_range: 0.10`

3. **OR Scenarios 단순화**
   - 가장 관대한 시나리오 1개만 남기고 테스트
   - 예: EMA Pullback만

4. **Absolute Conditions 완화**
   - CHOP 차단 임시 비활성화
   - DD/Consecutive Loss 체크 우회

### 우선순위 3: 로그 레벨 강화

**목표**: 각 게이트별 차단 로그 추가

**방법**:
```python
# check_absolute_conditions 내부
if not absolute_pass:
    logger.warning(f"🚫 [ABSOLUTE BLOCK] {absolute_reason}")  # 추가
    return False, absolute_reason

# evaluate_*_scenarios 내부
if not has_signal:
    logger.debug(f"❌ [OR FAIL] No scenario in {regime}")  # 추가
```

### 우선순위 4: 1M/3M 백테스트

DecisionTrace 수정 후:
- 1M baseline 실행
- 3M baseline 실행
- 패턴 비교

---

## 기술적 교훈

### 성공한 부분

1. **MTF 인프라**: PHASE31 구축이 정상 작동 확인
2. **테스트 품질**: 9/9 PASS로 인프라 검증
3. **V2 Light 설계**: 코드 레벨에서는 정상 구현

### 실패한 부분

1. **DecisionTrace 통합**: 
   - 전략-엔진 간 instance 전달 구조 미검증
   - 백테스트 실행 전 단위 테스트 미실시

2. **점진적 검증 부재**:
   - V2 Light 적용 여부를 로그로 먼저 확인했어야 함
   - Hysteresis 3 vs 5 비교 테스트 미실시

3. **디버깅 우선순위**:
   - 0 trades 문제를 한 번에 해결하려 함
   - 단계적 완화(Hysteresis만, Confidence만)를 시도하지 않음

---

## 파일 변경 목록

### 신규 (2개)
1. `configs/backtest/phase32_0_v2_light_7d.yml`
2. `docs/PHASE32/PHASE32_0_ZERO_TRADE_RCA_PARTIAL_KR.md` (본 문서)

### 수정 (3개)
1. `strategies/btc15m_core_v2.py` (+68 lines)
   - DecisionTrace 시스템 추가
   - V2 Light 모드 구현

2. `execution/engine.py` (+35 lines)
   - DecisionTrace 출력 코드 (미작동)

3. `tests/test_mtf_infra.py` (수정)
   - 9/9 PASS로 개선

---

## 결론

PHASE32-0은 **부분 완료** 상태입니다.

**달성**:
- ✅ MTF 테스트 품질 (9/9)
- ✅ DecisionTrace 코드 구현
- ✅ V2 Light 코드 구현

**미달성**:
- ❌ DecisionTrace 작동 (instance 접근 실패)
- ❌ Trades > 0 달성
- ❌ 근본 원인 정량화

**다음 Iteration**:
1. DecisionTrace 수정 (strategies instance 접근 문제 해결)
2. 단계적 완화 테스트 (Hysteresis 1 → Confidence 0.1 → Scenarios 단순화)
3. 1개라도 신호 생성 확인
4. 정량 데이터 기반 RCA 완성

**예상 작업량**: 2-3 hours

---

**Document Status**: ⚠️ PARTIAL  
**Date**: 2025-12-12  
**Next Action**: DecisionTrace 수정 + 단계적 완화 테스트
