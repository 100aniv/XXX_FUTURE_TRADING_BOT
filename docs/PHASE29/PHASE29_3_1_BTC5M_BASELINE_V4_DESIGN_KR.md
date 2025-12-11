# PHASE29-3.1: BTC 5m Baseline V4 전략 설계

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-3.1 |
| **작성일** | 2025-12-10 |
| **전략명** | btc5m_baseline_v4 |
| **컨셉** | Regime-Aware Hybrid (OR + Score + Multi-TP) |
| **상태** | 🔵 **DESIGN** → 🚧 **IMPLEMENTATION** |

---

## 🎯 1. 전략 개요

### 전략 컨셉

**Regime-Aware Hybrid Strategy: Trend Pullback + Range Mean Reversion**

- **Regime Detection**: V3 재사용 (ADX/DI 기반 Trend vs Range 분리)
- **진입 로직**: OR 기반 + **가중치 점수 합산** (AND 과잉 결합 회피)
- **TP/SL 구조**: Multi-TP 유지 (V3 재사용)
- **파라미터 관리**: 모든 파라미터 Config 외부화

### V2/V3 대비 차이점

| 항목 | V2 | V3 | **V4 (NEW)** |
|------|----|----|--------------|
| **진입 로직** | OR (RSI OR BB OR Volume) | AND (RSI AND BB AND EMA/ADX) | **OR + Score** (가중치 합산) |
| **신호 빈도** | 과다 (전환율 낮음) | 극소 (17건/월) | **조절 가능** (Threshold 튜닝) |
| **Win Rate** | < 45% | N/A (거래 부족) | **목표 ≥ 45%** |
| **Regime 분리** | 약함 | 명확 | **명확 (V3 재사용)** |
| **TP/SL** | 단일 TP | Multi-TP (1.2/3.0 ATR) | **Multi-TP (V3 재사용)** |

### 설계 철학

**"AND 과잉과 OR 과잉의 중간 지점"**

```
V2 (OR 과잉):
  if RSI < 30 OR Price < BB_Lower:
      → 신호 과다, Win Rate 낮음

V3 (AND 과잉):
  if RSI < 40 AND Price < BB_Lower AND ADX < 20:
      → 신호 극소, 17건/월

V4 (OR + Score):
  score = 0
  if RSI < 40: score += 3
  if Price < BB_Lower: score += 2
  if ADX < 20: score += 1
  
  if score >= 4:  # Threshold 조정 가능
      → 신호 빈도 조절, Win Rate 개선 가능
```

---

## 📊 2. Regime Detection 재사용 (V3)

### Regime Detection 로직

V3의 `detect_regime(df, config)` 함수를 **그대로 재사용**한다.

**근거**: PHASE29-2A 결과에서 Regime Detection은 정상 작동 확인
- Trend: 74.5%, Range: 25.5% ✅
- ADX/DI+/DI- 기반 탐지 정확

### Regime 분류

| Regime | Trend | ADX | 설명 |
|--------|-------|-----|------|
| **bull_high_vol** | BULL | ≥ 25 | 강한 상승 추세 |
| **bull_low_vol** | BULL | < 25 | 약한 상승 추세 |
| **bear_high_vol** | BEAR | ≥ 25 | 강한 하락 추세 |
| **bear_low_vol** | BEAR | < 25 | 약한 하락 추세 |
| **range_high_vol** | NEUTRAL | ≥ 20 & < 25 | 변동성 높은 횡보 |
| **range_low_vol** | NEUTRAL | < 20 | 변동성 낮은 횡보 |

### Regime별 전략 모드

- **Trend Mode**: Trend가 BULL/BEAR → Pullback 진입
- **Range Mode**: Trend가 NEUTRAL → Mean Reversion

---

## 🎯 3. 진입 로직 설계 (OR + Score)

### 3.1 Trend Mode: Pullback-in-Trend

**개념**: 추세 조정(Pullback) 구간에서 재진입

**진입 조건 (LONG 예시)**:

| 조건 | 가중치 | 설명 |
|------|--------|------|
| **RSI < rsi_threshold** | 3점 | 과매도 구간 (Pullback) |
| **Price < BB Main Lower** | 2점 | 볼린저 밴드 하단 (조정) |
| **EMA 20 < Price < EMA 5** | 2점 | EMA Pullback (추세 유지 중 조정) |
| **DI+ > DI-** | 1점 | Bull 방향 확인 |

**진입 Threshold**:
- `score >= trend_min_score` (기본값: 3)

**SHORT 조건**: 대칭 (RSI > threshold, Price > BB Upper, EMA 5 < Price < EMA 20, DI- > DI+)

**예상 신호 빈도 (추정)**:
- **score >= 3**: 중간 빈도 (1주 30~50건 예상)
- **score >= 4**: 낮은 빈도 (1주 10~20건 예상)
- **score >= 2**: 높은 빈도 (1주 60~100건 예상)

### 3.2 Range Mode: Mean Reversion

**개념**: 횡보 구간에서 밴드 경계 진입

**진입 조건 (LONG 예시)**:

| 조건 | 가중치 | 설명 |
|------|--------|------|
| **RSI < rsi_range_threshold** | 3점 | 과매도 (BB 하단과 일치 시 강함) |
| **Price < BB Main Lower** | 2점 | 밴드 하단 |
| **ADX < adx_range_threshold** | 1점 | Range 확인 (추세 약함) |

**진입 Threshold**:
- `score >= range_min_score` (기본값: 2)

**SHORT 조건**: 대칭 (RSI > threshold, Price > BB Upper, ADX < threshold)

**예상 신호 빈도 (추정)**:
- **score >= 2**: 중간 빈도 (1주 10~20건 예상, Range 비율 25% 고려)
- **score >= 3**: 낮은 빈도 (1주 5~10건 예상)

### 3.3 전체 신호 빈도 추정

**Regime 비율** (PHASE29-2A 기준):
- Trend: 74.5%
- Range: 25.5%

**예상 거래 건수** (1주일 기준):
- Trend 신호: 30~50건 (score >= 3)
- Range 신호: 10~20건 (score >= 2)
- **전체: 40~70건** ✅ (목표 20~60건 달성 가능)

**조정 가능성**:
- Threshold를 낮추면 신호 증가
- Threshold를 높이면 신호 감소
- 가중치 조정으로 조건 중요도 변경

---

## 🛡️ 4. TP/SL & 포지션 관리 (V3 재사용)

### 4.1 Multi-TP 구조

V3의 Multi-TP 구조를 **그대로 재사용**한다.

**Trend Mode**:
- **TP1**: entry ± (SL distance × 1.2), 60% 포지션 청산
- **TP2**: entry ± (SL distance × 3.0), 40% 포지션 청산
- **SL**: entry ± (ATR × 2.0)
- **홀드 타임**: 120분

**Range Mode**:
- **TP1**: entry ± (SL distance × 1.0), 60% 포지션 청산
- **TP2**: entry ± (SL distance × 2.0), 40% 포지션 청산
- **SL**: entry ± (ATR × 1.5)
- **홀드 타임**: 30분

### 4.2 BE (Break-Even) 이동

TP1 도달 시 SL을 Entry로 이동 (V3 구조 재사용)

### 4.3 Leverage 계산

V3의 ATR 기반 Leverage 계산 재사용:
```python
leverage = leverage_suggestion(
    atr_pct=atr_pct,
    min_leverage=config['leverage']['min'],
    max_leverage=config['leverage']['max']
)
```

---

## ⚙️ 5. Config 파라미터 목록

### 5.1 Regime Detection 파라미터

```yaml
# Regime 기준 (V3 재사용)
adx_trend_threshold: 25      # Trend vs Range 분류
adx_range_threshold: 20      # Range 확인 (낮을수록 Range)
```

### 5.2 Trend Mode 파라미터

```yaml
# 진입 조건 Threshold
trend_rsi_threshold: 45            # LONG RSI < threshold
trend_min_score: 3                 # 진입 최소 Score

# 가중치 (Score 계산용)
trend_weight_rsi: 3                # RSI 조건 가중치
trend_weight_bb: 2                 # BB 조건 가중치
trend_weight_ema: 2                # EMA Pullback 가중치
trend_weight_di: 1                 # DI+/DI- 가중치

# TP/SL
atr_mult_sl_trend: 2.0             # SL 거리 (ATR 배수)
tp1_mult_trend: 1.2                # TP1 거리 (SL 배수)
tp2_mult_trend: 3.0                # TP2 거리 (SL 배수)
tp1_size_pct: 0.6                  # TP1 포지션 비율 (60%)
tp2_size_pct: 0.4                  # TP2 포지션 비율 (40%)

# 홀드 타임
max_hold_minutes_trend: 120        # 최대 홀드 타임
```

### 5.3 Range Mode 파라미터

```yaml
# 진입 조건 Threshold
range_rsi_threshold: 40            # LONG RSI < threshold (V3보다 완화)
range_min_score: 2                 # 진입 최소 Score

# 가중치 (Score 계산용)
range_weight_rsi: 3                # RSI 조건 가중치
range_weight_bb: 2                 # BB 조건 가중치
range_weight_adx: 1                # ADX 조건 가중치

# TP/SL
atr_mult_sl_range: 1.5             # SL 거리 (ATR 배수)
tp1_mult_range: 1.0                # TP1 거리 (SL 배수)
tp2_mult_range: 2.0                # TP2 거리 (SL 배수)

# 홀드 타임
max_hold_minutes_range: 30         # 최대 홀드 타임
```

### 5.4 Global 파라미터

```yaml
# Filters (V3 재사용)
min_atr_pct: 0.0015                # 최소 ATR 0.15%
min_volume_ratio: 0.5              # 최소 Volume (MA20 대비)

# Short 허용
allow_short: true                  # SHORT 신호 허용 여부

# Leverage
leverage:
  min: 1
  max: 10
  default: 3
```

---

## 📈 6. 예상 신호 빈도 (로직 기반 추정)

### 6.1 Trend Mode 신호 빈도

**조건 조합 분석** (LONG 예시):

| 조건 조합 | Score | 예상 발생률 | 1주 예상 건수 |
|-----------|-------|-------------|---------------|
| RSI + BB + EMA | 7점 | 5% | 15~25건 |
| RSI + BB + DI | 6점 | 8% | 24~40건 |
| RSI + EMA + DI | 6점 | 6% | 18~30건 |
| BB + EMA + DI | 5점 | 4% | 12~20건 |
| RSI + BB | 5점 | 10% | 30~50건 |

**Threshold별 예상**:
- **score >= 5**: 30~50건/주 (중간)
- **score >= 4**: 40~60건/주 (중간~높음)
- **score >= 3**: 50~80건/주 (높음)

### 6.2 Range Mode 신호 빈도

**조건 조합 분석** (LONG 예시):

| 조건 조합 | Score | 예상 발생률 | 1주 예상 건수 |
|-----------|-------|-------------|---------------|
| RSI + BB + ADX | 6점 | 3% | 5~10건 |
| RSI + BB | 5점 | 6% | 10~15건 |
| RSI + ADX | 4점 | 4% | 7~12건 |
| BB + ADX | 3점 | 4% | 7~12건 |
| RSI 단독 | 3점 | 8% | 14~20건 |

**Threshold별 예상** (Range 비율 25% 고려):
- **score >= 4**: 7~12건/주 (낮음)
- **score >= 3**: 10~18건/주 (중간)
- **score >= 2**: 15~25건/주 (중간~높음)

### 6.3 전체 신호 빈도 (기본 설정)

**기본 Threshold** (trend_min_score=3, range_min_score=2):
- **Trend 신호**: 50~80건/주 (Trend 75%)
- **Range 신호**: 15~25건/주 (Range 25%)
- **전체**: **65~105건/주**

**1개월 예상**:
- **전체**: **260~420건/월** ✅ (목표 80~240건 초과)

**조정 방안**:
- Threshold를 올리면 신호 감소 (목표 범위 내로 조정 가능)
- 예: trend_min_score=4, range_min_score=3 → 40~70건/주

---

## 🎛️ 7. 튜닝 ParamSpace 초안 (PHASE29-4 준비)

### 7.1 Random Search ParamSpace

```yaml
# Trend Mode
trend_min_score: [2, 3, 4, 5]                    # Score Threshold
trend_rsi_threshold: [40, 45, 50]                # RSI Threshold
trend_weight_rsi: [2, 3, 4]                      # RSI 가중치
trend_weight_bb: [1, 2, 3]                       # BB 가중치
trend_weight_ema: [1, 2, 3]                      # EMA 가중치

# Range Mode
range_min_score: [1, 2, 3, 4]                    # Score Threshold
range_rsi_threshold: [35, 40, 45]                # RSI Threshold
range_weight_rsi: [2, 3, 4]                      # RSI 가중치
range_weight_bb: [1, 2, 3]                       # BB 가중치

# TP/SL
atr_mult_sl_trend: [1.5, 2.0, 2.5]              # Trend SL
atr_mult_sl_range: [1.0, 1.5, 2.0]              # Range SL
tp1_mult_trend: [1.0, 1.2, 1.5]                 # Trend TP1
tp2_mult_trend: [2.0, 3.0, 4.0]                 # Trend TP2

# Regime
adx_trend_threshold: [20, 25, 30]               # Trend 분류 기준
```

### 7.2 Bayesian Search 목표

**최적화 목표**:
- Primary: Win Rate ≥ 45%
- Secondary: Sharpe Ratio > 0, Profit Factor ≥ 1.2
- Constraint: 거래 건수 80~240건/월

**탐색 공간**:
- Threshold 조합 (Trend/Range 각각)
- 가중치 조합
- TP/SL 배수 조합

---

## 🚫 8. V2/V3 문제 회피 전략

### 8.1 V2 문제 (OR 과잉) 회피

**V2 문제**: OR만 사용 → 신호 과다, Win Rate < 45%

**V4 해결책**:
- Score Threshold 도입으로 신호 품질 필터링
- 단일 조건만 충족해도 진입하지 않음 (최소 score >= 2~3)

### 8.2 V3 문제 (AND 과잉) 회피

**V3 문제**: AND만 사용 → 교집합 극소, 17건/월

**V4 해결책**:
- OR 기반으로 여러 조건을 조합
- Score 합산으로 부분 충족 허용
- Threshold 튜닝으로 신호 빈도 조절

### 8.3 신호 빈도 보장

**최소 기준**: 1주 20~60건, 1개월 80~240건

**보장 메커니즘**:
1. **낮은 기본 Threshold**: trend_min_score=3, range_min_score=2
2. **넓은 조건 조합**: 각 Mode에 3~4개 조건
3. **Threshold 튜닝 가능**: Config로 외부화

---

## 📋 9. 다음 단계 (Implementation Checklist)

### Task 1: 코드 스켈레톤 구현 ✅
- [ ] `strategies/btc5m_baseline_v4.py` 생성
- [ ] BaseStrategy 상속
- [ ] `detect_regime()` V3 재사용
- [ ] `_calculate_trend_score()` 구현
- [ ] `_calculate_range_score()` 구현
- [ ] `signal_logic()` 메인 로직

### Task 2: Config 파일 생성 ✅
- [ ] `configs/backtest/phase29_3_1_btc5m_baseline_v4_day.yml`
- [ ] `configs/backtest/phase29_3_1_btc5m_baseline_v4_week.yml`
- [ ] `configs/tuning/btc5m_baseline_v4_paramspace.yml`

### Task 3: Unit Test 작성 ✅
- [ ] `tests/test_btc5m_baseline_v4.py`
- [ ] Config 파라미터 로드 테스트
- [ ] Score 계산 로직 테스트
- [ ] Regime Detection 테스트

### Task 4: 백테스트 실행 ✅
- [ ] 1일 스모크 백테스트 (신호 발생 확인)
- [ ] 1주일 백테스트 (Gate: 20~60건)
- [ ] 1개월 백테스트 (Gate: 80~240건)

### Task 5: 문서/ROADMAP 업데이트 ✅
- [ ] 백테스트 결과 정리
- [ ] PHASE_ROADMAP.md 업데이트
- [ ] git commit

---

## 📊 10. 예상 성능 (로직 기반 추정)

### 10.1 신호 품질 (V2 대비)

**V2**: OR만 → 단일 조건 충족 시 진입 → Win Rate < 45%

**V4**: OR + Score → 복수 조건 충족 시 진입 → **Win Rate ≥ 45% 예상**

### 10.2 신호 빈도 (V3 대비)

**V3**: AND만 → 모든 조건 충족 시 진입 → 17건/월

**V4**: OR + Score → 부분 조건 충족 시 진입 → **80~240건/월 예상**

### 10.3 Risk/Reward (Multi-TP)

**평균 RR** (Multi-TP 구조):
- Trend: (1.2 × 60% + 3.0 × 40%) = 1.92
- Range: (1.0 × 60% + 2.0 × 40%) = 1.40
- **전체 평균**: ≈ 1.75 ✅ (목표: ≥ 1.3)

---

## 📁 11. 참고 문서

- `docs/PHASE29/PHASE29_3_STRATEGY_REDESIGN_TODO.md`: V4 설계 원칙
- `docs/PHASE29/PHASE29_2C_BTC5M_BASELINE_V3_MONTH_BACKTEST_KR.md`: V3 실패 분석
- `strategies/btc5m_baseline_v3.py`: Regime Detection 재사용 (DEPRECATED)
- `common/registry/base_strategy.py`: BaseStrategy 인터페이스

---

**작성 완료**: 2025-12-10  
**다음 작업**: `strategies/btc5m_baseline_v4.py` 코드 구현
