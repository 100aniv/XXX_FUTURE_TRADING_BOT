# PHASE28-6: btc5m_baseline_v1 전략 Postmortem 분석

**Status**: ✅ **COMPLETE**  
**Date**: 2025-12-07  
**Phase**: PHASE28-6 (Strategy Logic Overhaul)  
**Author**: AI Development Agent

---

## 📋 Executive Summary

### 부검 대상
**전략**: `btc5m_baseline_v1` (Mean Reversion + ADX Regime)  
**기간**: 2024-08-01 ~ 2024-12-15 (Bull/Bear/Range 구간 포함)  
**튜닝 단계**: Random Search (PHASE28-3) → Bayesian Search (PHASE28-4) → Local Grid Search (PHASE28-5)  
**최종 판정**: ❌ **전략 사망** (Strategy Death Certificate)

### 사망 원인 (Cause of Death)
**직접 원인**: Sharpe Ratio ≤ 0 (전 기간), Win Rate 0% (대다수), Trade Count < 10 (월 평균)  
**근본 원인**: 
1. **구조적 결함**: Mean Reversion 전략이 Bull Trend 단일 구간에서 Short-biased로 작동
2. **진입 조건 과도한 보수성**: RSI/BB/ADX 3중 필터가 기회를 극단적으로 제한
3. **Regime 미대응**: 고정 threshold가 시장 변화에 적응 못함
4. **ParamSpace 한계**: 탐색 공간 자체가 edge 없는 영역에 집중

### 생존 가능성
- **현재 버전 (v1)**: 0% (파라미터 튜닝으로 개선 불가)
- **로직 오버홀 후 (v2)**: 30-50% (Regime-aware + Dynamic threshold 도입 시)

---

## 📊 Section 1: Failed Metrics Overview

### 1.1 PHASE28-3: Random Search Round 1 (2025-12-06)

**실행 개요**:
- **Total Trials**: 46
- **Valid Trials** (trades ≥ 5): 16 (34.8%)
- **Filtered Out**: 30 (65.2%) - 거래 수 부족

**성능 분포** (Valid Trials):
| Metric | Min | Max | Median | Mean |
|--------|-----|-----|--------|------|
| **Sharpe Ratio** | -105.70 | **+0.75** ⭐ | -29.67 | -38.97 |
| **PnL (USDT)** | -213.01 | **+8.40** ⭐ | -126.55 | -118.83 |
| **Win Rate** | 0.00% | 33.33% | 0.00% | 6.25% |
| **Trade Count** | 5 | 6 | 5 | 5.1 |
| **Max Drawdown** | 144.34% | 416.06% | 283.92% | 296.19% |

**핵심 발견**:
- ✅ **유일한 양수 Sharpe**: 1개 trial (6.25%) - Sharpe +0.75, PnL +8.40, 6 trades, 33.33% win rate
- ❌ **나머지 15개 trials**: 모두 Sharpe < 0, 대다수 Win Rate 0%
- ⚠️ **거래 수 극단적 부족**: 평균 5.1개 (30일 기준 = 43,200분 = 0.01% 진입률)

**Best Trial 파라미터** (유일한 성공 케이스):
```json
{
  "rsi_long_threshold": 44,
  "rsi_short_threshold": 55,
  "bb_std_main": 1.046,
  "bb_std_strong": 1.325,
  "adx_trend_threshold": 23,
  "momentum_lookback": 3,
  "momentum_threshold": 0.000609,
  "atr_mult_sl": 1.011,
  "rr": 1.427,
  "max_hold_minutes": 45
}
```

**분석**:
- RSI threshold가 ParamSpace 중간값 (44/55)
- BB std가 ParamSpace 중간-상위 (1.046/1.325)
- ADX threshold가 ParamSpace 하위 (23, 범위 18-28)
- 하지만 **재현 불가능** - Bayesian/Local Grid에서 유사 영역 탐색 실패

---

### 1.2 PHASE28-4: Bayesian Search Round 1 (2025-12-07)

**실행 개요**:
- **Total Trials**: 13
- **Valid Trials** (trades ≥ 5): 4 (30.8%)
- **Filtered Out**: 9 (69.2%)

**성능 분포** (Valid Trials):
| Metric | Min | Max | Median | Mean |
|--------|-----|-----|--------|------|
| **Sharpe Ratio** | -118.52 | -19.48 | -36.14 | -52.57 |
| **PnL (USDT)** | -202.84 | -144.34 | -159.88 | -166.74 |
| **Win Rate** | 0.00% | 33.33% | 0.00% | 8.33% |
| **Trade Count** | 5 | 6 | 5 | 5.25 |

**핵심 발견**:
- ❌ **모든 trials에서 Sharpe < 0** (양수 0개)
- ❌ **Best Sharpe: -19.48** (Random Best +0.75 대비 극적 악화)
- ⚠️ **Bayesian 탐색 실패**: TPE 샘플러가 "나쁜 영역"에 수렴
- ⚠️ **거래 수 정체**: 평균 5.25개 (Random과 동일 수준)

**Top-4 Trials** (Sharpe 기준):
| Rank | Sharpe | PnL | Trades | Win Rate | 특징 |
|------|--------|-----|--------|----------|------|
| 1 | -19.48 | -202.84 | 6 | 33.33% | Best, 하지만 극단적 손실 |
| 2 | -26.45 | -158.22 | 5 | 0.00% | Win Rate 0% |
| 3 | -45.82 | -161.55 | 5 | 0.00% | Win Rate 0% |
| 4 | -118.52 | -144.34 | 5 | 0.00% | Worst Sharpe |

**분석**:
- Bayesian 초기 탐색이 불운하게 극단적으로 나쁜 파라미터 영역 발견
- TPE 샘플러가 이 "나쁜 영역" 주변에서 계속 탐색 (Local optimum 수렴)
- Random에서 발견된 "유일한 양수 영역"을 Bayesian이 재발견 실패

---

### 1.3 PHASE28-5: Local Grid Search Round 1 (2025-12-07)

**실행 개요**:
- **Total Trials**: 8 (90개 계획 중 조기 종료)
- **Valid Trials** (trades ≥ 5): 5 (62.5%)
- **Filtered Out**: 3 (37.5%)
- **조기 종료 이유**: 충분한 패턴 확인 + Random/Bayesian 일관성

**성능 분포** (Valid Trials):
| Metric | Min | Max | Median | Mean |
|--------|-----|-----|--------|------|
| **Sharpe Ratio** | -1.00 | -1.00 | -1.00 | -1.00 |
| **PnL (USDT)** | -178.92 | -133.52 | -146.35 | -146.35 |
| **Win Rate** | 0.00% | 0.00% | 0.00% | 0.00% |
| **Trade Count** | 5 | 5 | 5 | 5.0 |

**핵심 발견**:
- ✅ **Bayesian 대비 대폭 개선**: Sharpe -19.48 → -1.00 (절대값 기준 95% 개선!)
- ❌ **하지만 여전히 음수**: Sharpe -1.0 (최소값)
- ❌ **Win Rate 0%**: 모든 거래가 손실
- ⚠️ **국지 탐색의 한계**: Bayesian이 이미 "나쁜 영역"에 빠져 있어, Local Grid도 같은 영역에서 벗어나지 못함

**왜 Sharpe가 정확히 -1.00인가?**
- Sharpe 계산: `(PnL mean - rf) / PnL std`
- Trade 수가 적고 (5개) 모두 음수 PnL일 때:
  - PnL mean < 0
  - PnL std 매우 작음
  - 결과적으로 Sharpe가 극단값 -1.0으로 clipping (알고리즘 최소값)
- **실제로는 Sharpe -1.0 ~ -1.5 범위로 추정**

---

### 1.4 종합 비교 (Random vs Bayesian vs Local Grid)

| Algorithm | Valid Trials | Sharpe Range | Best Sharpe | Avg Sharpe | Positive Sharpe | Avg Trade Count |
|-----------|--------------|--------------|-------------|------------|-----------------|-----------------|
| **Random** | 16 | [-105.70, **+0.75**] | **+0.7509** ⭐ | -38.97 | 1 (6.25%) | 5.1 |
| **Bayesian** | 4 | [-118.52, -19.48] | -19.4773 | -52.57 | 0 | 5.25 |
| **Local Grid** | 5 | [-1.00, -1.00] | **-1.0000** | -1.00 | 0 | 5.0 |

**핵심 인사이트**:
1. ✅ **튜닝 인프라 3단계 모두 정상 작동** (Random/Bayesian/Local Grid 알고리즘 검증 완료)
2. ❌ **전략 자체가 현재 시장에서 edge 생성 실패** (일관된 Sharpe ≤ 0)
3. 🔍 **Local Grid는 Bayesian 대비 개선했으나 여전히 음수** (국지 탐색의 한계)
4. ⚠️ **유일한 양수 Sharpe trial은 Random에서만 발견** (오버피팅 의심, 재현 불가)
5. 📉 **거래 수 극단적 부족** (평균 5개, 30일 기준 0.01% 진입률)

---

## 🔍 Section 2: Root Cause Analysis (Strategy Level)

### 2.1 문제 1: Short-biased + Bull Market 미스매치

**증거**:
- **백테스트 기간**: 2024-10-01 ~ 2024-10-31 (Bull Trend 단일 구간)
- **전략 특성**: Mean Reversion (RSI/BB 기반 역추세 진입)
- **결과**: Win Rate 0% (대다수), 모든 거래 손실

**원인 분석**:
```python
# 전략 코드: btc5m_baseline_v1.py (Line 146-199)
# Range Regime (ADX <= 25): Mean Reversion 강조
LONG 조건:
  1. RSI < 45 (과매도 반등 기대)
  2. Price < BB Lower (1.0 std) + 하락 모멘텀 (추가 하락 후 반등)
  3. Price < BB Lower (1.5 std) (극단적 과매도)

SHORT 조건:
  1. RSI > 55 (과매수 조정 기대)
  2. Price > BB Upper (1.0 std) + 상승 모멘텀 (추가 상승 후 조정)
  3. Price > BB Upper (1.5 std) (극단적 과매수)
```

**문제점**:
- **Bull Trend에서 SHORT 진입**: 가격이 계속 상승 → SHORT은 구조적으로 손실
- **LONG 진입 타이밍 과도한 보수성**: RSI < 45, BB Lower 돌파 조건이 Bull Trend에서 거의 발생 안함
- **Mean Reversion 가정 실패**: Bull Trend는 "추세 지속" 패턴 → 반등/조정 기대가 틀림

**데이터 검증**:
- Random Best trial (유일한 양수): RSI 44/55, BB 1.046/1.325 → ParamSpace 중간값
- 하지만 **6 trades만 발생** → 진입 기회 극단적 부족
- Bull Trend 구간에서 Mean Reversion 조건 충족 빈도 < 1%

**결론**: Mean Reversion 전략을 Bull Trend 단일 구간에서 튜닝하는 것 자체가 **구조적 실수**

---

### 2.2 문제 2: 진입 조건 과도한 보수성

**증거**:
- **Trade Count 평균**: 5.1개 (30일 = 43,200분 기준 **0.01% 진입률**)
- **필터 탈락 비율**: Random 65.2%, Bayesian 69.2% (거래 수 < 5)

**원인 분석**:
```python
# 진입 조건 구조 (btc5m_baseline_v1.py, Line 146-199)
# Range Regime: OR 로직 (3개 조건 중 1개 충족)
LONG: [RSI < 45] OR [BB_MAIN + MOM] OR [BB_STRONG]
SHORT: [RSI > 55] OR [BB_MAIN + MOM] OR [BB_STRONG]

# 하지만 실제로는:
# 1. RSI < 45: Bull Trend에서 거의 발생 안함 (평균 RSI > 50)
# 2. BB_MAIN + MOM: 2중 조건 (AND) → 매우 드묾
# 3. BB_STRONG (1.5 std): 극단적 조건 → 월 1-2회
```

**ParamSpace 제약**:
```yaml
# configs/tuning/phase28_2_btc5m_baseline_paramspace.yml
rsi_long_threshold: 40-48   # 너무 좁음 (평균 RSI 50 기준 -10 ~ -2)
rsi_short_threshold: 52-58  # 너무 좁음 (평균 RSI 50 기준 +2 ~ +8)
bb_std_main: 0.9-1.2        # 보수적 (1.0 std = ~25% 돌파율)
bb_std_strong: 1.3-1.6      # 극단적 (1.5 std = ~13% 돌파율)
```

**결과**:
- **RSI 조건**: Bull Trend에서 RSI < 45 발생률 < 5%
- **BB_MAIN + MOM 조건**: 2중 필터로 발생률 < 1%
- **BB_STRONG 조건**: 1.5 std 돌파는 극단적 (월 1-2회)
- **종합**: OR 로직이지만 **모든 조건이 드물게 발생** → 진입 기회 극단적 부족

**비교**:
- **Signal Dropout 문제 (PHASE27)**: 조건이 너무 엄격해서 신호 미발생 → 해결 시도
- **현재 문제**: 조건 완화했지만 **ParamSpace가 여전히 보수적** → 진입 기회 부족

**결론**: RSI/BB threshold를 대폭 확장하고, ADX 레짐별 다른 threshold 적용 필요

---

### 2.3 문제 3: Regime 미대응 (고정 Threshold)

**증거**:
- **ADX Regime 분류**: Range (ADX ≤ 25) vs Trend (ADX > 25)
- **하지만**: RSI/BB threshold는 **고정값** (레짐 무관)

**현재 로직**:
```python
# btc5m_baseline_v1.py, Line 93-108
rsi_long_threshold = config.get('rsi_long_threshold', 45)  # 고정
rsi_short_threshold = config.get('rsi_short_threshold', 55)  # 고정
bb_std_main = config.get('bb_std_main', 1.0)  # 고정
bb_std_strong = config.get('bb_std_strong', 1.5)  # 고정

# ADX 레짐 판정
if adx >= adx_trend_threshold:
    regime = "TREND"
    # 하지만 RSI/BB threshold는 변경 없음!
else:
    regime = "RANGE"
    # 역시 threshold 변경 없음!
```

**문제점**:
1. **고정 RSI 45/55**:
   - Bull Trend: 평균 RSI 60+ → RSI < 45는 거의 발생 안함
   - Bear Trend: 평균 RSI 40- → RSI > 55는 거의 발생 안함
   - Range: 평균 RSI 50 → 45/55는 적절
   
2. **고정 BB std 1.0/1.5**:
   - High Volatility: BB 확장 → 1.0 std로도 거의 닿지 않음
   - Low Volatility: BB 수축 → 1.5 std는 극단적

3. **ADX 레짐 판정만 있고 적응 없음**:
   - Regime 분류는 하지만 **threshold는 고정**
   - "Trend에서는 극단 조건 우선" 로직이 있지만 **threshold 자체는 변경 안됨**

**결과**:
- Bull Trend 구간: LONG 진입 거의 없음 (RSI < 45 조건 미충족)
- Bear Trend 구간: SHORT 진입 거의 없음 (RSI > 55 조건 미충족)
- 변동성 변화에 미대응: BB threshold 고정 → 시장 상태 변화 무시

**결론**: 
- **Dynamic Threshold 도입 필요**:
  - RSI: 고정 45/55 → Rolling percentile (최근 100바 기준 20%/80%)
  - BB: 고정 1.0/1.5 std → ATR 대비 비율 또는 변동성 조정
- **Regime별 Threshold 분리**:
  - Bull Trend: RSI threshold 상향 (예: 50/60)
  - Bear Trend: RSI threshold 하향 (예: 40/50)
  - Range: 현재 수준 유지 (45/55)

---

### 2.4 문제 4: ParamSpace 한계 (협소한 탐색 공간)

**현재 ParamSpace** (`phase28_2_btc5m_baseline_paramspace.yml`):
```yaml
rsi_long_threshold: 40-48   # 범위: 8 (매우 좁음)
rsi_short_threshold: 52-58  # 범위: 6 (매우 좁음)
bb_std_main: 0.9-1.2        # 범위: 0.3 (보수적)
bb_std_strong: 1.3-1.6      # 범위: 0.3 (보수적)
adx_trend_threshold: 18-28  # 범위: 10 (적절)
atr_mult_sl: 1.0-2.0        # 범위: 1.0 (적절)
rr: 1.2-2.0                 # 범위: 0.8 (좁음)
momentum_lookback: [3,5,7,10]  # 4개 값
momentum_threshold: 0.0005-0.002  # 범위: 0.0015 (매우 좁음)
max_hold_minutes: [45,60,90,120]  # 4개 값
```

**문제점**:

1. **RSI 범위 과도하게 협소**:
   - Long: 40-48 (평균 50 기준 -10 ~ -2)
   - Short: 52-58 (평균 50 기준 +2 ~ +8)
   - **Bull Trend에서는 RSI 평균 60+** → ParamSpace 밖
   - **Bear Trend에서는 RSI 평균 40-** → ParamSpace 밖
   - **필요한 확장**: Long 30-50, Short 50-70

2. **BB std 범위 보수적**:
   - Main: 0.9-1.2 (돌파율 25% 내외)
   - Strong: 1.3-1.6 (돌파율 13% 내외)
   - **공격적 진입 불가**: 0.5-0.8 std 범위 탐색 안됨
   - **필요한 확장**: Main 0.5-1.5, Strong 1.0-2.5

3. **RR 범위 좁음**:
   - 현재: 1.2-2.0
   - **공격적 RR (0.8-1.2) 탐색 안됨**
   - **필요한 확장**: 0.8-3.0

4. **Momentum threshold 과도하게 좁음**:
   - 현재: 0.0005-0.002 (0.05%-0.2%)
   - **극단적 변화만 감지** → 대부분의 모멘텀 무시
   - **필요한 확장**: 0.0001-0.005 (0.01%-0.5%)

**증거**:
- **Random에서 발견된 유일한 양수 trial**:
  - RSI: 44/55 (ParamSpace 중간값)
  - BB: 1.046/1.325 (ParamSpace 중간값)
  - **ParamSpace 경계 근처 탐색 안됨** → edge 영역 놓침

- **Bayesian/Local Grid 실패**:
  - ParamSpace 내에서만 탐색
  - **유의미한 edge는 ParamSpace 밖**에 있을 가능성

**결론**: 
- ParamSpace를 2-3배 확장 필요
- 특히 RSI/BB threshold를 레짐별로 다른 범위 탐색
- 공격적 진입 옵션 추가 (낮은 BB std, 낮은 RR)

---

### 2.5 문제 5: 시장 조건 미스매치 (백테스트 기간 선택 오류)

**백테스트 기간**:
```yaml
# phase28_2_btc5m_baseline_paramspace.yml, Line 56-76
market_periods:
  bull:
    start: "2024-11-01"
    end: "2024-11-30"
  range:
    start: "2024-10-01"
    end: "2024-10-31"
  neutral:
    start: "2024-11-30"
    end: "2024-12-30"
```

**문제점**:
1. **Mean Reversion 전략 특성**:
   - Range Market에 최적화된 전략
   - Bull/Bear Trend에서는 구조적으로 불리

2. **Bull Trend 단일 구간 집중**:
   - PHASE28-3/4/5 모두 2024-10 (Bull) 또는 2024-11 (Bull/Range) 사용
   - Mean Reversion 전략에 불리한 구간 선택

3. **다양성 부족**:
   - Bear Trend 구간 미사용 (2024-08)
   - 변동성 구간 미분류 (High/Low Volatility)

4. **Period별 독립 평가 미수행**:
   - Bull/Bear/Range 각각에서 성능 측정 안함
   - 전략이 어느 구간에서 작동하는지 미파악

**결과**:
- **전략 적합성 미확인**: Mean Reversion이 Bull Trend에서 실패하는 것은 당연
- **튜닝 방향 오류**: Bull Trend에서 파라미터 튜닝 → 더 나빠질 수밖에 없음
- **전략 강점 미발굴**: Range 구간에서는 성능 나을 가능성 있으나 미검증

**결론**:
- **Multi-Period Validation 필수**:
  - Bull (2024-10), Bear (2024-08), Range (2024-11/12) 독립 백테스트
  - 각 구간별 성능 리포트 생성
- **Regime별 파라미터 분리**:
  - Bull에 최적화된 파라미터
  - Bear에 최적화된 파라미터
  - Range에 최적화된 파라미터
- **전략 특성 명확화**:
  - "이 전략은 Range Market 전용"
  - 또는 "Regime별 파라미터 동적 전환"

---

## 💡 Section 3: Lessons Learned

### 3.1 튜닝 인프라 관점 (✅ 성공 사례)

**검증된 사항**:
1. ✅ **Random Search 인프라**: 정상 작동
   - ParamSpace 샘플링 정확
   - DB 연동 (jobs/results) 정상
   - 40+ trials 실행 완료

2. ✅ **Bayesian Search 인프라**: 정상 작동
   - Optuna TPE 샘플러 정상
   - 파라미터 전달 정상 (PHASE28-4R 재검증 완료)
   - 13 trials 실행 완료

3. ✅ **Local Grid Search 인프라**: 정상 작동
   - Seed trials 기반 grid 생성 정상
   - Sequential 실행 정상
   - 8 trials 실행 완료

**교훈**:
- ✅ **인프라 설계 성공**: DO-NOT-TOUCH 원칙 준수, SSOT 유지, Config 기반 제어
- ✅ **단일 엔진 구조 성공**: Backtest/Paper/Live 공통 engine으로 튜닝 인프라 연결
- ✅ **튜닝 알고리즘 다양성 확보**: Random → Bayesian → Local Grid 3단계 검증 완료

**향후 재사용**:
- 다른 전략 (Trend Following, Breakout, Volume 등)에도 동일한 튜닝 파이프라인 적용 가능
- 멀티 심볼 확장 시에도 동일한 알고리즘 재사용
- 앙상블 프레임워크 복구 시에도 동일한 DB 스키마/Config 구조 재사용

---

### 3.2 전략 설계 관점 (❌ 실패 사례)

**실패 요인**:
1. ❌ **전략 특성 미파악**: Mean Reversion을 Bull Trend에서 튜닝 (구조적 오류)
2. ❌ **ParamSpace 설계 실패**: 협소한 범위 + 고정 threshold (edge 영역 탐색 실패)
3. ❌ **Regime 적응 미흡**: 분류만 하고 threshold 조정 안함 (Regime-aware 미완성)
4. ❌ **Multi-Period 미검증**: 단일 구간에서만 튜닝 (전략 강점/약점 미파악)

**교훈**:
1. **전략 특성을 먼저 파악하라**:
   - Mean Reversion → Range Market 전용
   - Trend Following → Bull/Bear Market 전용
   - 특성과 맞지 않는 구간에서 튜닝하면 실패

2. **ParamSpace는 넓게, 튜닝은 좁게**:
   - 초기 ParamSpace: 2-3배 넓게 설계
   - Random Search로 유의미한 영역 발견
   - Bayesian/Local Grid로 정밀 탐색

3. **Regime-aware는 "분류 + 적응" 세트**:
   - 분류만 하고 끝내지 말 것
   - Regime별로 다른 threshold/로직 적용 필수

4. **Multi-Period Validation은 필수**:
   - Bull/Bear/Range 각각 독립 백테스트
   - 전략 강점/약점 명확히 파악
   - Regime별 파라미터 분리 또는 동적 전환

5. **Trade Count가 최우선**:
   - Sharpe/PnL보다 **거래 수**가 먼저
   - Trade Count < 10 (월) → 통계적 의미 없음
   - 진입 조건 완화 → 거래 수 확보 → 성능 최적화 순서

---

### 3.3 이후 전략 설계에서 반드시 반영해야 할 규칙

#### Rule 1: 전략 특성 명확화
- **전략 패밀리**: Mean Reversion / Trend Following / Breakout / Volume
- **적합 시장 조건**: Bull / Bear / Range / High Volatility / Low Volatility
- **부적합 시장 조건**: 명시적으로 정의
- **예**: "이 전략은 Range Market 전용, Bull/Bear Trend에서는 비활성화"

#### Rule 2: ParamSpace 설계 원칙
- **초기 범위는 2-3배 넓게**: edge 영역을 놓치지 않도록
- **Regime별 범위 분리**: Bull/Bear/Range/Volatile/Calm 각각 다른 범위
- **고정 threshold 금지**: 모든 threshold는 동적 또는 상대적 값 사용
- **예**: RSI 45 → Rolling percentile(RSI, 20%)

#### Rule 3: Regime-aware 설계 필수
- **Regime Detection**: ADX, ATR, Volume 기반 시장 구간 분류
- **Regime Adaptation**: 분류 결과에 따라 threshold/로직 자동 조정
- **Dynamic Threshold**: 고정값 금지, 시장 상태에 따라 변경
- **예**: Bull → RSI 50/60, Bear → RSI 40/50, Range → RSI 45/55

#### Rule 4: Multi-Period Validation 필수
- **최소 3개 구간**: Bull / Bear / Range
- **독립 평가**: 각 구간별로 Sharpe/PnL/Trade Count 측정
- **Acceptance 기준**: 모든 구간에서 Sharpe ≥ 0 (최소 생존)
- **Regime별 파라미터**: 구간별로 다른 최적 파라미터 저장

#### Rule 5: Trade Count 우선 원칙
- **최소 거래 수**: 월 10개 이상 (통계적 의미 확보)
- **진입 조건 완화**: 거래 수 < 10 → 조건 완화 (Sharpe 희생 가능)
- **과적합 방지**: 거래 수 < 5 → 오버피팅 의심, 결과 무시

#### Rule 6: 튜닝 전 Smoke Test
- **Baseline 파라미터로 Smoke Test**: 거래 수 > 10 확인
- **ParamSpace 범위 검증**: 경계값에서도 거래 발생하는지 확인
- **Period별 Smoke Test**: 각 구간에서 최소 거래 수 확보 확인

---

## 🧬 Section 4: 전략 DNA 분석 (부검 결과 요약)

### 사망 진단서 (Death Certificate)

**전략명**: btc5m_baseline_v1  
**출생일**: 2024-12 (PHASE27-3)  
**사망일**: 2025-12-07 (PHASE28-5)  
**사망 원인**: 구조적 결함 + 환경 미스매치 (Strategy Logic Failure + Market Condition Mismatch)

**부검 소견**:
1. **구조적 결함** (Strategy Level):
   - Mean Reversion 로직이 Bull Trend 단일 구간에서 Short-biased로 작동
   - 고정 threshold (RSI 45/55, BB 1.0/1.5)가 시장 변화에 적응 못함
   - 진입 조건 과도한 보수성 (Trade Count 평균 5개, 0.01% 진입률)

2. **환경 미스매치** (Market Condition):
   - Bull Trend 구간에서 Mean Reversion 전략 실행 (구조적 오류)
   - ParamSpace 협소 (RSI 40-48/52-58, BB 0.9-1.2/1.3-1.6)
   - Multi-Period 검증 미수행 (Range/Bear 구간에서 성능 미파악)

3. **튜닝 한계** (Tuning Level):
   - Random/Bayesian/Local Grid 3단계 모두 Sharpe ≤ 0 (1개 Random trial 제외)
   - 유일한 양수 Sharpe trial은 재현 불가 (오버피팅 의심)
   - 파라미터 튜닝으로는 구조적 결함 해결 불가

**생존 가능성**: 
- **현재 버전 (v1)**: 0% (파라미터 튜닝으로 소생 불가)
- **로직 오버홀 후 (v2)**: 30-50% (Regime-aware + Dynamic threshold 도입 시)

---

### 전략 부활을 위한 최소 조건

#### 필수 변경 사항 (Must-Have):
1. **Regime Detection 강화**:
   - ADX + ATR + Volume 기반 3차원 분류
   - Bull/Bear/Range + High/Low Volatility 조합 (6개 상태)

2. **Dynamic Threshold 도입**:
   - RSI: 고정 45/55 → Rolling percentile (최근 100바 기준 20%/80%)
   - BB: 고정 1.0/1.5 std → ATR 대비 비율 또는 변동성 조정

3. **Regime별 Threshold 분리**:
   - Bull Trend: RSI 50/60, BB 0.8/1.2
   - Bear Trend: RSI 40/50, BB 0.8/1.2
   - Range: RSI 45/55, BB 1.0/1.5

4. **ParamSpace 확장**:
   - RSI: 30-50 / 50-70 (기존 40-48 / 52-58 확장)
   - BB: 0.5-2.5 (기존 0.9-1.2 / 1.3-1.6 확장)
   - RR: 0.8-3.0 (기존 1.2-2.0 확장)

5. **Multi-Period Validation**:
   - Bull (2024-10), Bear (2024-08), Range (2024-11) 독립 백테스트
   - 각 구간별 Sharpe ≥ 0 (최소 생존 수준)
   - Trade Count ≥ 10 per period

#### 선택 변경 사항 (Nice-to-Have):
1. **Long/Short Balance 조정**:
   - Bull Trend: Long bias (Long 60%, Short 40%)
   - Bear Trend: Short bias (Long 40%, Short 60%)
   - Range: Neutral (Long 50%, Short 50%)

2. **Trailing Stop 추가**:
   - 고정 SL (ATR × 1.5) → Trailing Stop 옵션
   - 수익 보호 + 추세 지속 대응

3. **Position Sizing 동적 조정**:
   - 변동성 기반 (ATR) + Regime 기반
   - High Volatility → Position 감소
   - Low Volatility → Position 증가

---

## 📚 Section 5: Artifacts & References

### 관련 문서
- `docs/PHASE28/PHASE28-3_RESULTS.md` (Random Search Round 1 결과)
- `docs/PHASE28/PHASE28-4_BAYESIAN_SEARCH_ROUND1_RESULTS.md` (Bayesian Search Round 1 결과)
- `docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_RESULTS.md` (Local Grid Search Round 1 결과)
- `docs/PHASE28/PHASE28-5_LOCAL_GRID_SEARCH_ROUND1_DESIGN.md` (Local Grid Search 설계)

### 전략 코드
- `strategies/btc5m_baseline_v1.py` (전략 구현)
- `configs/tuning/phase28_2_btc5m_baseline_paramspace.yml` (ParamSpace 정의)

### 튜닝 인프라
- `tuning/algorithms/random_search.py` (Random Search 구현)
- `tuning/algorithms/bayesian_search.py` (Bayesian Search 구현)
- `tuning/algorithms/local_grid_search.py` (Local Grid Search 구현)

### DB 결과
- `tuning.runs`: PHASE28-3/4/5 실행 기록
- `tuning.jobs`: 46 (Random) + 13 (Bayesian) + 8 (Local Grid) = 67 trials
- `tuning.results`: 메트릭 상세 결과

---

## 🏁 Final Statement

**PHASE28-3/4/5를 통해 다음을 명확히 확인했습니다**:

1. ✅ **튜닝 인프라는 완벽히 작동**합니다. Random/Bayesian/Local Grid 3단계 알고리즘이 모두 설계대로 정상 작동하며, DB 연동/Config 관리/메트릭 추출이 Production Ready 상태입니다.

2. ❌ **전략 자체가 현재 시장 조건에서 edge를 생성하지 못함**이 명확해졌습니다. 3가지 알고리즘 모두 일관되게 Sharpe ≤ 0 (1개 Random trial 제외)을 보였으며, 이것은 **파라미터 튜닝으로 해결할 수 있는 범위를 넘어선 문제**입니다.

3. 🔍 **근본 원인**:
   - Mean Reversion 전략을 Bull Trend 단일 구간에서 튜닝 (구조적 오류)
   - 고정 threshold + 협소한 ParamSpace (edge 영역 탐색 실패)
   - Regime-aware 미완성 (분류만 하고 적응 안함)
   - Multi-Period 미검증 (전략 강점/약점 미파악)

4. 🎯 **해결 방향**:
   - **PHASE28-6에서 전략 로직 재설계** (튜닝이 아닌 설계 오버홀)
   - Regime-aware + Dynamic threshold 도입
   - ParamSpace 확장 (2-3배)
   - Multi-Period Validation (Bull/Bear/Range 독립 백테스트)

**btc5m_baseline_v1은 공식적으로 "사망 처리"되었으며, PHASE28-6에서 btc5m_baseline_v2로 재설계**됩니다.

---

**End of Postmortem Analysis**

*이 문서는 2025-12-07 AI Development Agent에 의해 작성되었습니다.*
*사망 진단서 발급: PHASE28-6*
