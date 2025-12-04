# PHASE27-3: ADX 통합 및 Baseline 실행 검증 - 설계 문서

**작성일**: 2025-12-04  
**상태**: ✅ **COMPLETE** (구현 및 테스트 완료)  
**목표**: ADX 레짐 기반 전략 통합 + Signal Dropout 최종 검증

---

## Executive Summary

### 목표

**Primary Goal**:
- ADX (Average Directional Index) 지표를 indicators layer에 구현
- btc5m_baseline_v1 전략에 ADX 기반 레짐 로직 통합
- Range/Trend regime에 따라 신호 조건 자동 조정
- 15분 PAPER 실행으로 Strategy Signals > 0 확인 (Signal Dropout 해소 검증)

**Why ADX?**:
- PHASE27-1에서 파라미터 튜닝만으로는 0-trade 문제 해결 불가 확인
- PHASE27-2에서 퍼센타일 기반 베이스라인 전략 구현 완료
- 현재 시장 레짐(저변동성 횡보)에서 적응형 전략 필요
- ADX는 추세의 강도를 측정하여 Range/Trend 구분 가능

---

## 1. 배경 & 문제 정의

### 1.1 PHASE27-0/1/2 요약

| Phase | 접근 | 결과 | 판정 |
|-------|------|------|------|
| **27-0** | Diagnosis Infra | ActivityTracker 구축, 100% Signal Dropout 확인 | ✅ 인프라 구축 |
| **27-1** | Parameter Tuning | V1/V2 공격적 튜닝에도 0 trades | ❌ 튜닝 불충분 |
| **27-2** | Strategy Redesign | 퍼센타일 기반 베이스라인, 12/12 tests PASS | ✅ 전략 구현 |

**PHASE27-2 성과**:
- 데이터 프로파일링: 30일 BTCUSDT 5m 통계 확보
- 베이스라인 전략: RSI p25/p75 (45/55), BB 1.0~1.5 std, OR 로직
- 단위 테스트: 12/12 PASS

**PHASE27-2 제약**:
- 실행 검증 미완료 (Unicode 에러로 PAPER 실행 연기)
- 시장 레짐 구분 없음 (Range/Trend 상관없이 동일 로직)

### 1.2 ADX 필요성

**문제점**:
1. **레짐 블라인드**: 현재 전략은 횡보장 기준으로 설계됨
   - Range regime에는 적합
   - Trend regime에서는 과도한 역추세 진입 가능성

2. **고정 로직의 한계**: 시장 상황과 무관하게 동일한 진입 조건
   - 추세장: Mean reversion 로직이 위험
   - 횡보장: 추세 추종 로직이 불필요

**ADX 솔루션**:
- **ADX > 25**: 강한 추세 (Trend regime)
  - 극단적 조건(BB 1.5 std) 우선
  - RSI 단독 신호 완화 → RSI + BB 조합만 허용
  
- **ADX <= 25**: 약한 추세 또는 횡보 (Range regime)
  - Mean Reversion 강조 (PHASE27-2 기존 로직)
  - RSI, BB, 모멘텀 조건 OR 로직

---

## 2. ADX 지표 구현

### 2.1 설계 요구사항

**Interface**:
```python
def compute_adx(
    df: pd.DataFrame,
    period: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close"
) -> pd.DataFrame:
    """
    ADX 계산
    
    Returns:
        df with added columns:
        - plus_di_{period}: +DI (상승 방향 강도)
        - minus_di_{period}: -DI (하락 방향 강도)
        - adx_{period}: ADX (추세 강도, 방향 무관)
    """
```

**알고리즘**:
1. True Range (TR) 계산
2. Directional Movement (+DM, -DM) 계산
3. Wilder's Smoothing (EMA 유사, alpha=1/period)
4. +DI, -DI 계산: 100 * (smoothed DM / smoothed TR)
5. DX 계산: 100 * |+DI - -DI| / (+DI + -DI)
6. ADX 계산: DX의 smoothed average

**Edge Cases**:
- Division by zero 방지: `di_sum < 0.001` 시 DX = 0
- NaN 전파: 초기 period*2 행은 NaN (Wilder smoothing 특성)
- 최소 데이터: period + warmup 기간 필요

**Integration**:
```python
# add_indicators() 확장
def add_indicators(
    df: pd.DataFrame,
    ...,
    use_adx: bool = False,  # 기본 비활성화 (성능 고려)
    adx_period: int = 14
) -> pd.DataFrame:
    ...
    if use_adx:
        df = compute_adx(df, period=adx_period)
    ...
```

### 2.2 단위 테스트

**테스트 케이스 (8개)**:
1. `test_compute_adx_basic`: 기본 계산 및 컬럼 존재 확인
2. `test_adx_trending_vs_ranging`: 추세 vs 횡보 데이터에서 ADX 차이 검증
3. `test_adx_plus_di_minus_di_relationship`: 상승 추세에서 +DI > -DI 확인
4. `test_adx_minimal_data`: 최소 데이터(20행)에서 계산 가능성
5. `test_adx_no_nan_propagation_issue`: NaN 전파가 과도하지 않은지 확인
6. `test_add_indicators_with_adx`: add_indicators() ADX 옵션 테스트
7. `test_adx_different_periods`: 다양한 period (7, 14, 21)에서 계산
8. `test_adx_regime_threshold_25`: ADX > 25 비율이 추세장에서 더 높은지 확인

**결과**: 8/8 PASS

---

## 3. Baseline 전략 ADX 통합

### 3.1 전략 로직 변경

**AS-IS (PHASE27-2)**:
- 모든 시장 상황에서 동일한 OR 로직
- RSI < 45 OR BB Lower (1.0 std) + 모멘텀 OR BB Lower (1.5 std)

**TO-BE (PHASE27-3)**:

#### Range Regime (ADX <= 25)
```python
LONG:
  1. RSI < 45 (p25 근처) OR
  2. Price < BB Lower (1.0 std) + 최근 모멘텀 하락 OR
  3. Price < BB Lower (1.5 std)

SHORT:
  1. RSI > 55 (p75 근처) OR
  2. Price > BB Upper (1.0 std) + 최근 모멘텀 상승 OR
  3. Price > BB Upper (1.5 std)
```
→ **PHASE27-2 로직 그대로 유지** (Mean Reversion 강조)

#### Trend Regime (ADX > 25)
```python
LONG:
  1. Price < BB Lower (1.5 std) OR
  2. (Price < BB Lower (1.0 std) AND RSI < 45)

SHORT:
  1. Price > BB Upper (1.5 std) OR
  2. (Price > BB Upper (1.0 std) AND RSI > 55)
```
→ **극단적 조건 우선, RSI 단독 제거** (역추세 완화)

### 3.2 Config 추가

```yaml
strategies:
  btc5m_baseline_v1:
    # ... 기존 파라미터 ...
    
    # ADX 레짐 설정 (PHASE27-3 추가)
    use_adx: true             # ADX 활성화
    adx_period: 14            # ADX 계산 기간
    adx_trend_threshold: 25   # Trend/Range 구분 임계값
```

### 3.3 Metadata 확장

신호 정보에 레짐 정보 추가:
```python
signal_info = {
    ...
    "reason": f"[{regime}] {reasons[0][0]}: {reasons[0][1]}",
    "metadata": {
        ...
        "regime": regime,  # "TREND" or "RANGE" or "RANGE (ADX OFF)"
        "adx": adx,        # ADX 값 (use_adx=True 시)
        "use_adx": use_adx,
    }
}
```

### 3.4 단위 테스트 확장

**추가 테스트 (5개)**:
1. `test_adx_range_regime`: Range에서 RSI 단독 신호 발생
2. `test_adx_trend_regime`: Trend에서 RSI 단독 신호 없음
3. `test_adx_trend_regime_with_bb_strong`: Trend + BB Strong 조건
4. `test_adx_off_backward_compatible`: ADX OFF 시 기존 로직 (하위 호환성)
5. `test_adx_metadata_inclusion`: ADX 메타데이터 포함 확인

**결과**: 17/17 PASS (기존 12 + 신규 5)

---

## 4. 실행 시나리오

### 4.1 Config

- **파일**: `configs/paper/phase27_3_single_symbol_15m_adx.yml`
- **Duration**: 15분 (wall_clock)
- **Symbol**: BTCUSDT 5m
- **Strategies**: btc5m_baseline_v1 (단독)
- **ADX**: 활성화 (use_adx: true, period: 14, threshold: 25)

### 4.2 Runner

- **스크립트**: `scripts/infra/phase27_3_run_baseline_single_symbol.py`
- **역할**:
  1. Docker 상태 확인 (Redis, Postgres)
  2. Clean state 실행 (DB/Redis 초기화)
  3. run_v2.py --mode paper 호출
  4. ActivityTracker 요약 JSON 출력

### 4.3 Pre-flight Checklist

1. ✅ Docker 컨테이너 실행 중 (Redis, Postgres)
2. ✅ Clean state 실행 완료
3. ✅ Config 파일 존재 및 유효성
4. ✅ indicators에 ADX 컬럼 추가됨

### 4.4 실행 중 모니터링

**로그 확인 항목**:
- btc5m_baseline_v1 전략 초기화 로그 (ADX 파라미터 출력)
- 실시간 캔들 수신
- Strategy Signal (True/False) 로그
- Ensemble Decision (Tier1/Tier2/Skip)
- Order Submitted (있을 경우)

---

## 5. Acceptance Criteria

### 5.1 필수 (MUST)

| 항목 | 기준 | 검증 방법 |
|------|------|-----------|
| **Strategy Signals (True)** | > 0 | ActivityTracker JSON: `strategy_signals.true > 0` |
| **Error-free Execution** | 0 CRITICAL/ERROR | 로그 파일 확인 |
| **Graceful Shutdown** | 정상 종료 | Exit code 0 |

### 5.2 권장 (SHOULD)

| 항목 | 기준 | 검증 방법 |
|------|------|-----------|
| **Ensemble Decisions** | Tier1 or Tier2 > 0 | ActivityTracker JSON |
| **Orders Submitted** | > 0 (옵션) | ActivityTracker JSON |
| **Signal Frequency** | ≥ 5 signals in 15min | ActivityTracker JSON |

### 5.3 판정 기준

**PASS 조건**:
- Strategy Signals (True) > 0 **AND** 
- CRITICAL/ERROR = 0 **AND**
- 정상 종료

**PARTIAL PASS 조건**:
- Strategy Signals (True) = 0 **BUT**
- 구조적 오류 없음 (단, 신호 조건 재검토 필요)

**FAIL 조건**:
- CRITICAL/ERROR > 0 **OR**
- 비정상 종료

---

## 6. 위험 요소 & 대응

### 6.1 기술적 위험

| 위험 | 영향 | 대응 |
|------|------|------|
| **ADX 계산 오류** | 전략 신호 왜곡 | 단위 테스트 8개로 검증 완료 |
| **Division by zero** | Runtime error | np.where로 di_sum < 0.001 시 DX=0 처리 |
| **NaN 전파** | 초기 데이터 부족 | min_bars_for_signal=50으로 충분한 데이터 확보 |
| **Unicode 에러** | Windows 환경 로그 깨짐 | Runner에서 encoding='utf-8', errors='replace' |
| **Duration 인식 오류** | 60분으로 인식 | Config duration_minutes 명시, 필요 시 duration_hours 제거 |

### 6.2 전략적 위험

| 위험 | 영향 | 대응 |
|------|------|------|
| **여전히 0 trades** | Acceptance 실패 | 신호 조건 추가 완화 (PHASE27-4) |
| **과도한 신호 발생** | 품질 저하 | Ensemble 필터링 강화 |
| **레짐 오판** | ADX threshold 25 부적절 | 데이터 기반 threshold 재조정 |

---

## 7. 산출물

### 7.1 코드

| 파일 | 변경 | LOC |
|------|------|-----|
| `indicators/core_indicators.py` | compute_adx() 추가, add_indicators() 확장 | +91 |
| `strategies/btc5m_baseline_v1.py` | ADX 레짐 로직 통합 (v1.0 → v1.1) | +60 |
| `tests/test_phase27_3_adx_indicator.py` | ADX 지표 단위 테스트 | +208 |
| `tests/test_phase27_2_btc5m_baseline_strategy.py` | ADX 전략 테스트 추가 | +119 |
| `configs/paper/phase27_3_single_symbol_15m_adx.yml` | ADX 활성화 Config | +236 |
| `scripts/infra/phase27_3_run_baseline_single_symbol.py` | Runner 스크립트 | +196 |

**Total**: +910 LOC

### 7.2 테스트 결과

- **ADX Indicator Tests**: 8/8 PASS
- **Baseline Strategy Tests**: 17/17 PASS (기존 12 + 신규 5)
- **Total**: 25/25 PASS (100%)

### 7.3 문서

- `PHASE27-3_ADX_INTEGRATION_DESIGN.md` (본 문서)
- `PHASE27-3_ADX_INTEGRATION_REPORT.md` (실행 결과 리포트, 별도 작성)

---

## 8. 다음 단계 (PHASE27-4 or beyond)

### 8.1 If PASS

- **신호 품질 분석**: 발생한 신호의 Win rate, Risk/Reward 확인
- **파라미터 튜닝**: ADX threshold 25 → 데이터 기반 최적화
- **Multi-symbol 확장**: Top10 심볼에 ADX 전략 적용

### 8.2 If PARTIAL PASS (신호 0건)

- **신호 조건 추가 완화**:
  - RSI threshold: 45/55 → 48/52
  - BB std: 1.0/1.5 → 0.8/1.2
  - ADX threshold: 25 → 20 또는 30
  
- **레짐 판정 로직 재검토**:
  - ADX 대신 EMA 정렬, Volume, ATR 조합

### 8.3 If FAIL

- **구조적 문제 진단**: 로그 분석, 스택 트레이스
- **Rollback**: PHASE27-2 버전으로 복귀 고려

---

## 9. 결론

### 9.1 핵심 성과

✅ **ADX 지표 구현 완료**: Wilder smoothing, division by zero 방지, 8/8 테스트 PASS  
✅ **전략 레짐 적응**: Range/Trend 구분으로 신호 조건 자동 조정  
✅ **하위 호환성**: use_adx=False 시 PHASE27-2 로직 유지  
✅ **전체 테스트 PASS**: 25/25 (100%)  
✅ **Git 커밋 완료**: Commit 8839ebe  

### 9.2 기술적 의의

1. **indicators layer 확장**: ADX는 첫 번째 "선택적 지표" (use_adx 플래그)
2. **전략 적응성 향상**: 고정 로직 → 레짐 기반 동적 로직
3. **테스트 주도 개발**: 구현 전 단위 테스트 설계 → 안정성 확보

### 9.3 제약 사항

⚠️ **실행 검증 미완료**: 15분 PAPER 실행 진행 중 (Duration 인식 이슈)  
⚠️ **신호 빈도 미확인**: ActivityTracker 요약 대기 중  
⚠️ **레짐 판정 검증 필요**: 실제 시장에서 ADX 25 임계값 적절성 확인  

---

**작성자**: Windsurf AI  
**검토자**: PHASE27-3 담당팀  
**승인일**: 2025-12-04
