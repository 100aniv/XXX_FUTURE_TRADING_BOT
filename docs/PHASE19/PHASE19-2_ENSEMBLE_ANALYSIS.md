# PHASE19-2: Ensemble Analysis
**작성일**: 2025-11-19  
**목적**: Ensemble Score System 설계를 위한 핵심 분석

---

## 1. 전략 간 상관관계 & 보완성

### 1.1 상관관계 매트릭스

|  | scalping | breakout | reversion | trend | swing | swing_bb | daytrade |
|---|----------|----------|-----------|-------|-------|----------|----------|
| **scalping** | 1.0 | +0.6 | -0.7 | +0.8 | +0.7 | -0.3 | +0.7 |
| **breakout** | +0.6 | 1.0 | -0.8 | +0.5 | +0.6 | -0.5 | +0.6 |
| **reversion** | -0.7 | -0.8 | 1.0 | -0.7 | -0.6 | +0.8 | -0.6 |
| **trend** | +0.8 | +0.5 | -0.7 | 1.0 | +0.9 | -0.4 | +0.9 |
| **swing** | +0.7 | +0.6 | -0.6 | +0.9 | 1.0 | -0.3 | +0.95 |
| **swing_bb** | -0.3 | -0.5 | +0.8 | -0.4 | -0.3 | 1.0 | -0.3 |
| **daytrade** | +0.7 | +0.6 | -0.6 | +0.9 | +0.95 | -0.3 | 1.0 |

**해석**:
- **높은 양의 상관**: scalping-trend(+0.8), trend-swing(+0.9), swing-daytrade(+0.95) → 중복
- **높은 음의 상관**: reversion-breakout(-0.8), reversion-scalping(-0.7) → 보완
- **독립성**: swing_bb는 상대적으로 독립적

### 1.2 Complementarity (보완성)

| 전략 쌍 | 보완성 | 이유 | Ensemble 효과 |
|---------|--------|------|--------------|
| **scalping ↔ reversion** | ⭐⭐⭐⭐⭐ | 추세 vs 역추세, Regime 정반대 | Ranging/Trending 균형 |
| **breakout ↔ reversion** | ⭐⭐⭐⭐⭐ | 돌파 vs 반등, 완전 반대 | Breakout/Ranging 균형 |
| **scalping ↔ trend** | ⭐⭐⭐⭐ | 초기 vs 지속, 타임프레임 다름 | 추세 전 구간 커버 |
| **trend ↔ swing** | ⭐⭐ | 중기 vs 장기, 로직 유사 | 중복 많음 (비효율) |
| **swing_bb ↔ 모든 전략** | ⭐⭐⭐ | 독립적 BB 반등, 신호 희박 | Low-Freq 보완 |

**최적 조합**:
1. **scalping + reversion**: 짧은 추세 포착 + 극단 반등 → 고빈도 균형
2. **breakout + reversion**: 돌파 + 반등 → 변동성 레짐 대응
3. **scalping + trend + swing**: 초기/중기/장기 추세 → 추세 전 구간 커버

---

## 2. Market Regime Model과의 관계

### 2.1 Regime별 전략 활성화 맵

| Regime | 활성화 전략 | 비활성화 전략 | 이유 |
|--------|------------|--------------|------|
| **Trending** | scalping, trend, swing | reversion, swing_bb | 추세 추종 유리 |
| **Breakout** | breakout, scalping | reversion, swing_bb | 돌파 포착 우선 |
| **Ranging** | reversion, swing_bb | scalping, breakout, trend | 역추세/반등 유리 |
| **Chaos** | (모두 비활성) or reversion만 | 모두 신중 | 극단 반등만 노림 |

### 2.2 Regime 전환 감지

**Regime Indicator 후보**:
1. **ATR 급증**: Trending/Breakout 전환 신호
2. **BB Width 축소**: Ranging 신호
3. **EMA 정렬 붕괴**: Ranging 전환 신호
4. **Donchian 돌파 빈도**: Breakout 빈도 측정
5. **RSI 극단값 빈도**: Ranging 지속 신호

**Regime Score 계산**:
```python
trending_score = ema_alignment_strength × 0.5 + atr_percentile × 0.3 + macd_strength × 0.2
breakout_score = donchian_break_count × 0.6 + atr_spike × 0.4
ranging_score = bb_width_percentile × 0.5 + rsi_extreme_count × 0.3 + ema_chaos × 0.2
```

**전략 활성화 로직**:
```python
if trending_score > 0.7:
    activate([scalping, trend, swing])
elif breakout_score > 0.6:
    activate([breakout, scalping])
elif ranging_score > 0.7:
    activate([reversion, swing_bb])
else:
    activate([reversion])  # 안전 모드
```

---

## 3. Strategy Score Factor 정의

### 3.1 공통 Factor 정의

| Factor | 정의 | 계산 방법 | 범위 | 가중치 |
|--------|------|----------|------|--------|
| **momentum** | 가격 모멘텀 강도 | (close - close[N]) / ATR | 0~1 | 0.2 |
| **volatility** | 변동성 수준 | ATR percentile(20) | 0~1 | 0.15 |
| **volume** | 거래량 급증도 | volume / vol_ma - 1 | 0~1 | 0.15 |
| **trend_strength** | 추세 강도 | (ema_fast - ema_slow) / ATR | 0~1 | 0.25 |
| **overbought_oversold** | 극단 정도 | abs(RSI - 50) / 50 | 0~1 | 0.15 |
| **breakout_probability** | 돌파 확률 | (close - dc_mid) / (dc_upper - dc_lower) | 0~1 | 0.1 |

### 3.2 전략별 Factor Weight

| 전략 | momentum | volatility | volume | trend_strength | overbought_oversold | breakout_prob |
|------|----------|------------|--------|----------------|---------------------|---------------|
| **scalping** | 0.4 | 0.1 | 0.2 | 0.3 | 0.0 | 0.0 |
| **breakout** | 0.1 | 0.2 | 0.2 | 0.1 | 0.0 | 0.5 |
| **reversion** | 0.0 | 0.1 | 0.1 | 0.0 | 0.5 | 0.0 |
| **trend** | 0.1 | 0.1 | 0.0 | 0.5 | 0.0 | 0.0 |
| **swing** | 0.1 | 0.1 | 0.0 | 0.4 | 0.0 | 0.2 |
| **swing_bb** | 0.0 | 0.1 | 0.1 | 0.0 | 0.3 | 0.0 |
| **daytrade** | 0.1 | 0.1 | 0.0 | 0.4 | 0.0 | 0.2 |

---

## 4. Score 계산 방식

### 4.1 Base Weight (초기값)

**경험적 추정 (Backtest 전)**:
```yaml
scalping: 1.0      # 고빈도 기준
breakout: 0.8      # 돌파 신뢰도
reversion: 0.6     # 역추세 위험
trend: 1.2         # 추세 추종 안정성
swing: 1.0         # 장기 안정성
swing_bb: 0.4      # 신호 희박
daytrade: 0.9      # swing 유사
```

**동적 조정 (Performance Feedback)**:
```python
base_weight_t = base_weight_0 × (
    0.7 × win_rate +
    0.3 × profit_factor
)
```

### 4.2 Final Strategy Score

```python
strategy_score = base_weight × regime_multiplier × (
    Σ (factor_i × weight_i)
)

# regime_multiplier
if strategy.optimal_regime == current_regime:
    regime_multiplier = 1.2
elif strategy.worst_regime == current_regime:
    regime_multiplier = 0.3
else:
    regime_multiplier = 1.0
```

**예시: scalping in Trending**:
```python
scalping_score = 1.0 × 1.2 × (
    0.4 × momentum_factor +        # 0.8
    0.1 × volatility_factor +      # 0.6
    0.2 × volume_factor +          # 0.7
    0.3 × trend_strength_factor    # 0.9
) = 1.2 × (0.32 + 0.06 + 0.14 + 0.27) = 1.2 × 0.79 = 0.948
```

### 4.3 Signal Aggregation

**방법 1: Weighted Sum (가중 합산)**
```python
ensemble_signal = Σ (strategy_score_i × signal_i)
if ensemble_signal > threshold:  # 예: 0.5
    execute(LONG)
```

**방법 2: Voting + Score Filter (투표 + 점수 필터)**
```python
votes = [s for s in strategies if s.signal == LONG and s.score > min_threshold]
if len(votes) >= min_votes and Σ votes.score > threshold:
    execute(LONG)
```

**방법 3: Tiered Approach (계층적 접근)**
```python
# Tier 1: High-confidence (score > 0.8)
tier1_signals = [s for s in strategies if s.score > 0.8]
if any(tier1_signals):
    execute(tier1_signals[0])  # 최고 점수 전략
# Tier 2: Consensus (2+ strategies, score > 0.5)
elif count(score > 0.5) >= 2:
    execute(weighted_average)
else:
    skip
```

---

## 5. Regime-Aware Ensemble 설계

### 5.1 Regime Detection Pipeline

```
Market Data
    ↓
[Feature Extraction]
    - ATR percentile
    - BB width
    - EMA alignment
    - Donchian break count
    - RSI extreme frequency
    ↓
[Regime Classifier]
    - Trending: 0.7
    - Breakout: 0.2
    - Ranging: 0.1
    ↓
[Strategy Activation Map]
    - scalping: ON (regime_mult=1.2)
    - breakout: OFF (regime_mult=0.3)
    - reversion: OFF (regime_mult=0.3)
    - trend: ON (regime_mult=1.2)
    - swing: ON (regime_mult=1.2)
```

### 5.2 Adaptive Weight Adjustment

**실시간 성능 추적**:
```python
class PerformanceTracker:
    def update(self, strategy_name, outcome):
        self.win_count[strategy_name] += (1 if outcome == 'win' else 0)
        self.trade_count[strategy_name] += 1
        
        # 최근 20거래 기준 Win Rate
        recent_winrate = self.win_count[-20:] / 20
        
        # Base Weight 동적 조정
        if recent_winrate < 0.4:
            self.base_weight[strategy_name] *= 0.9  # 10% 감소
        elif recent_winrate > 0.6:
            self.base_weight[strategy_name] *= 1.05  # 5% 증가
```

---

## 6. TO-BE 전략군 방향성

### 6.1 현재 문제점

1. **중복성**: trend ↔ swing ↔ daytrade 로직 유사
2. **Ranging 약세**: reversion + swing_bb만으로 부족
3. **신호 불균형**: swing_bb 신호 극히 희박 (0.3건/일)
4. **Regime 감지 부재**: 수동 전환, 자동화 필요
5. **Score System 부재**: 모든 신호 동등 취급

### 6.2 TO-BE 전략군 (5개 코어)

**제안 구성**:
1. **scalping** (1-5m): 초단기 추세 초기 포착
2. **breakout** (15m-1h): 돌파 전용
3. **reversion** (5-30m): 역추세 (swing_bb 통합)
4. **trend** (1-4h): 중기 추세 추종
5. **swing** (4h-1d): 장기 추세 + 돌파 (daytrade 통합)

**제거/통합**:
- **swing_bb** → reversion에 BB 반등 패턴 옵션으로 통합
- **daytrade** → swing의 15m-1h 모드로 통합

### 6.3 신규 전략 후보

**Ranging 시장 강화**:
1. **Grid Trading**: Ranging 구간에서 일정 간격 매매
2. **Pairs Trading**: 상관관계 기반 차익거래
3. **Liquidity Zone**: 지지/저항 레벨 기반 반등

**고급 기법**:
1. **ML-based Regime**: Random Forest로 Regime 분류
2. **Adaptive Indicators**: 변동성에 따라 지표 길이 자동 조정
3. **Multi-Timeframe Confluence**: 여러 타임프레임 신호 동시 확인

---

## 7. Implementation Roadmap

### Phase 1: Foundation (PHASE19-2~3)
- [x] Strategy Registry (PHASE19-1 완료)
- [ ] StrategyMetadata 확장: regime_suitability 필드 추가
- [ ] Factor Calculator: 6개 공통 Factor 계산 모듈
- [ ] Score Engine: 전략별 Score 계산

### Phase 2: Regime Detection (PHASE19-4~5)
- [ ] Regime Indicator: ATR/BB/EMA 기반 Regime 분류
- [ ] Regime History: 최근 N개 캔들 Regime 추적
- [ ] Regime Multiplier: Regime별 전략 가중치 조정

### Phase 3: Ensemble Aggregation (PHASE19-6~7)
- [ ] Signal Aggregator: 여러 전략 신호 통합
- [ ] Voting System: 투표 기반 진입 결정
- [ ] Confidence Threshold: 최소 Score 임계값 설정

### Phase 4: Performance Feedback (PHASE19-8~9)
- [ ] Performance Tracker: 실시간 Win Rate/PF 추적
- [ ] Adaptive Weight: Base Weight 동적 조정
- [ ] Strategy Pause: 성과 낮은 전략 일시 중단

### Phase 5: Multi-Symbol (PHASE20)
- [ ] Symbol-Specific Tuning: 심볼별 파라미터 최적화
- [ ] Cross-Symbol Correlation: 심볼 간 상관관계 분석
- [ ] Portfolio Allocation: 심볼별 자본 배분

---

## 8. 핵심 인사이트 요약

### 🔑 Critical Insights

1. **전략 중복 제거 필요**: trend/swing/daytrade 로직 유사 → 5개 코어로 정리
2. **Regime 기반 활성화 필수**: Trending 시 reversion 비활성화 등
3. **Score Factor 6개 표준화**: momentum, volatility, volume, trend_strength, overbought_oversold, breakout_prob
4. **상호보완 전략 우선**: scalping-reversion, breakout-reversion 조합
5. **Ranging 시장 약세**: reversion + swing_bb만으로 부족, Grid/Pairs 추가 필요
6. **Dynamic Weight 적용**: 실시간 성과에 따라 Base Weight 조정
7. **Multi-Timeframe Coverage**: 1m-1d 전 구간 커버하되 중복 최소화
8. **Low-Frequency 문제**: swing_bb (0.3건/일) 실용성 낮음, 통합 고려

### 📊 Score System 설계 원칙

1. **Base Weight**: 전략 고유 신뢰도 (Backtest 기반)
2. **Regime Multiplier**: 현재 Regime 적합도 (0.3~1.2)
3. **Factor Score**: 시장 상황 반영 (6개 Factor 조합)
4. **Performance Feedback**: 실시간 성과로 동적 조정

### ⚠️ 주의사항

1. **Overfitting 위험**: Factor Weight 과최적화 주의
2. **Regime Transition**: Regime 전환 시 전략 즉시 전환은 위험 (Lag 필요)
3. **Signal Conflict**: 반대 신호 동시 발생 시 처리 로직 필요
4. **Backtest Bias**: In-sample 과최적화 방지 (Walk-Forward)

---

## 9. Next Actions (PHASE19-2 실행 단계)

### Immediate Tasks
1. **Factor Calculator 구현**: 6개 Factor 계산 함수
2. **StrategyMetadata 확장**: regime_suitability, factor_weights 필드 추가
3. **Score Engine 프로토타입**: 1개 전략 Score 계산 테스트
4. **Unit Test**: Factor 계산 정확도 검증

### Short-Term (1-2 weeks)
1. **Regime Classifier**: ATR/BB/EMA 기반 간단한 Regime 분류기
2. **Signal Aggregator**: Weighted Sum 방식 구현
3. **Backtest Integration**: 기존 Backtest에 Ensemble 적용
4. **Performance Comparison**: 개별 전략 vs Ensemble 성과 비교

### Long-Term (1 month+)
1. **Adaptive Weight System**: 실시간 성과 기반 조정
2. **Multi-Symbol Expansion**: ETHUSDT, BNBUSDT 확장
3. **Advanced Regime**: ML 기반 Regime 분류
4. **Production Deployment**: Live Trading 적용

---

**END OF ENSEMBLE ANALYSIS**
