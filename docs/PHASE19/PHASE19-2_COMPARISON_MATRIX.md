# PHASE19-2: Strategy Comparison Matrix
**작성일**: 2025-11-19  
**목적**: 7개 전략 비교 분석표

---

## 1. 핵심 특성 비교표

| 전략 | 성격 | Time Horizon | 신호빈도 | 타겟 RR | 주요 지표 | Regime 최적 |
|------|------|--------------|---------|---------|----------|-------------|
| **scalping** | momentum | ultra-short (1-5m) | 높음 | 1.3 | EMA Cross, RSI | Trending |
| **breakout** | breakout | short (15m-1h) | 중간 | 2-3 | Donchian, ATR | Breakout |
| **reversion** | counter-trend | short (5-30m) | 중간 | 1.5-2 | RSI, BB | Ranging |
| **trend** | trend-follow | mid (1-4h) | 낮음 | 2-3 | EMA 3선, MACD | Trending |
| **swing** | trend-follow | long (4h-1d) | 매우낮음 | 2-3 | EMA, BB, Donchian | Trending |
| **swing_bb** | mean-revert | long (5m 저빈도) | 극히낮음 | 기본 | BB Bounce, MACD Cross | Ranging |
| **daytrade** | trend-follow | short (15m-1h) | 중간 | 기본 | EMA, MACD, BB | Trending |

---

## 2. 변동성 & 거래량 민감도

| 전략 | 변동성 민감도 | Volume 민감도 | ATR 활용 | 저변동성 대응 |
|------|--------------|--------------|---------|-------------|
| **scalping** | 높음 (필수) | 중간 (선택) | SL 계산 | 신호 희박 |
| **breakout** | 매우높음 (필수) | 높음 (확인용) | 확대 감지 + SL | 무력화 |
| **reversion** | 중간 | 중간 (선택) | SL 조정 | BB 좁아져 신호↓ |
| **trend** | 낮음 | 낮음 | SL 계산 | 정렬 유지되면 OK |
| **swing** | 낮음 | 낮음 | SL 조정 | 장기라 무관 |
| **swing_bb** | 중간 | 높음 (필수) | SL 계산 | BB 좁아져 신호↓ |
| **daytrade** | 중간 | 중간 | SL 조정 | 신호 감소 |

**핵심 인사이트**:
- **breakout**은 ATR 확대 필수 → 변동성 급증 감지용
- **reversion**은 BB width 의존 → 저변동성 시 극단값 희박
- **scalping**은 Fresh Cross 조건으로 변동성 독립적이나 실제로는 신호빈도↓

---

## 3. Market Regime 적합성 매트릭스

| 전략 | Trending | Breakout | Ranging | Chaos | 비고 |
|------|----------|----------|---------|-------|------|
| **scalping** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | 추세 초기 최적 |
| **breakout** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | 돌파 전용 |
| **reversion** | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 역추세 전용 |
| **trend** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐ | 추세 추종 정석 |
| **swing** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | 장기 추세+돌파 |
| **swing_bb** | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | BB 반등 전용 |
| **daytrade** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | swing과 유사 |

**전략 조합 제안**:
- **Trending**: scalping + trend + swing (3개)
- **Breakout**: breakout + swing (2개)
- **Ranging**: reversion + swing_bb (2개)
- **Chaos**: reversion (1개, 극단 반등 노림)

---

## 4. Ensemble 기여도 & 상호보완성

| 전략 | Ensemble 역할 | 보완 전략 | 충돌 전략 | 독립성 |
|------|--------------|----------|----------|-------|
| **scalping** | Early Signal | trend, swing | reversion | 높음 |
| **breakout** | Breakout Detector | scalping | reversion | 높음 |
| **reversion** | Counter-Trend | scalping, breakout | trend, swing | 매우높음 |
| **trend** | Trend Confirmer | scalping | reversion | 중간 |
| **swing** | Long-Term Anchor | scalping, trend | reversion | 중간 |
| **swing_bb** | Low-Freq Specialist | reversion | trend, swing | 높음 |
| **daytrade** | Mid-Freq Trader | (swing과 중복) | reversion | 낮음 (중복) |

**상관관계**:
- **scalping ↔ trend**: 같은 방향, 타임프레임 다름 → 보완 ✅
- **scalping ↔ reversion**: 정반대 → 충돌 ❌ (Regime 기반 선택 필요)
- **breakout ↔ reversion**: 정반대 → 충돌 ❌
- **trend ↔ swing**: 거의 동일 → 중복 ⚠️ (타임프레임만 다름)
- **swing ↔ daytrade**: 로직 유사 → 중복 ⚠️

**최적 조합**:
1. **Trending 시장**: scalping + trend + breakout (초기+지속+돌파)
2. **Ranging 시장**: reversion + swing_bb (극단 반등)
3. **혼합 시장**: scalping + reversion (짧은 추세 vs 역추세 균형)

---

## 5. Multi-Symbol 확장 난이도

| 전략 | 확장 난이도 | 위험 요인 | 심볼 민감도 | 비고 |
|------|------------|----------|------------|------|
| **scalping** | 중간 | 거래비용 증가, 심볼별 변동성 차이 | 중간 | BTCUSDT 특화 조정 필요 |
| **breakout** | 낮음 | 심볼별 Donchian 길이 조정 필요 | 낮음 | 범용 가능 |
| **reversion** | 낮음 | 심볼별 RSI/BB 임계값 다름 | 중간 | 튜닝 필요 |
| **trend** | 매우낮음 | 거의 없음 | 낮음 | 범용 전략 |
| **swing** | 매우낮음 | 장기 홀딩으로 심볼 뉴스 리스크 | 낮음 | 안정적 확장 |
| **swing_bb** | 높음 | 신호 극히 희박, 심볼별 BB width 차이 큼 | 높음 | 확장 비추천 |
| **daytrade** | 낮음 | swing과 유사 | 낮음 | 범용 가능 |

**확장 우선순위**:
1. **trend** (범용성 최고)
2. **swing** (안정성)
3. **breakout** (조정 최소)
4. **daytrade** (범용)
5. **reversion** (튜닝 필요)
6. **scalping** (BTCUSDT 특화)
7. **swing_bb** (확장 부적합)

---

## 6. Score Factor Compatibility

| 전략 | momentum | volatility | volume | trend_strength | overbought_oversold | breakout_prob |
|------|----------|------------|--------|----------------|---------------------|---------------|
| **scalping** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **breakout** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| **reversion** | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **trend** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ |
| **swing** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| **swing_bb** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| **daytrade** | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ |

**Factor별 대표 전략**:
- **momentum**: scalping (higher_low 패턴)
- **volatility**: breakout (ATR 확대 감지)
- **volume**: breakout (거래량 급증)
- **trend_strength**: trend, swing (EMA 정렬)
- **overbought_oversold**: reversion (RSI 극단)
- **breakout_prob**: breakout (Donchian 돌파)

---

## 7. 전략별 Drawdown 패턴

| 전략 | DD 패턴 | 최악 시나리오 | 회복 속도 | 비고 |
|------|---------|--------------|----------|------|
| **scalping** | 작고 빈번 | Ranging 장기화 | 빠름 (추세 복귀) | Whipsaw 누적 |
| **breakout** | 중간, 돌발적 | False Breakout 연속 | 중간 | Bull/Bear Trap |
| **reversion** | 큼, 집중적 | 강한 추세 지속 | 느림 (Ranging 대기) | Knife Catching |
| **trend** | 큼, 점진적 | 추세 반전 늦은 감지 | 느림 | 정렬 붕괴 후 회복 대기 |
| **swing** | 매우큼 | 장기 추세 반전 | 매우느림 | 큰 SL로 DD 확대 |
| **swing_bb** | 작음 (신호 희박) | BB 좁아진 구간 장기화 | 빠름 (신호 희박) | Low Frequency |
| **daytrade** | 중간 | swing과 유사 | 중간 | swing과 동일 |

**DD 관리 전략**:
- **scalping**: Ranging 감지 시 일시 중단
- **breakout**: False Breakout 필터 강화 (ATR, Volume)
- **reversion**: 추세 필터 추가 (EMA context)
- **trend/swing**: 정렬 붕괴 즉시 청산

---

## 8. 중복성 분석 & 전략군 최적화

### 중복 전략 쌍
1. **trend ↔ swing**: EMA 정렬 + MACD 로직 거의 동일 (타임프레임만 다름)
2. **swing ↔ daytrade**: 로직 거의 동일 (타임프레임만 다름)

### 최적화 제안
**현재 7개 → 5개 코어 전략 제안**:
1. **scalping**: 초단기 모멘텀 (1-5m)
2. **breakout**: 돌파 전용 (15m-1h)
3. **reversion**: 역추세 (5-30m)
4. **trend**: 중기 추세 (1-4h)
5. **swing**: 장기 추세 (4h-1d)

**제거 후보**:
- **swing_bb**: 신호 극히 희박 (0.3건/일), 실용성 낮음
- **daytrade**: swing과 중복, 차별성 부족

**대안**: 
- swing_bb는 reversion에 통합 (BB 반등 패턴 옵션)
- daytrade는 swing의 15m-1h 모드로 통합

---

## 9. Timeframe Coverage Map

```
1m   3m   5m   15m  30m  1h   4h   1d
|----|----|----|----|----|----|----|----|
[====scalping====]
          [=======reversion========]
               [====breakout====]
               [====daytrade====]
                    [====trend====]
                         [======swing======]
     [swing_bb (5m 저빈도)]
```

**Coverage 분석**:
- **1-5m**: scalping 단독 커버 ✅
- **5-30m**: scalping, reversion, swing_bb 중복 ⚠️
- **15m-1h**: breakout, daytrade, trend 중복 ⚠️
- **1-4h**: trend, swing 중복 ⚠️
- **4h-1d**: swing 단독 커버 ✅

**최적화**: 타임프레임별 1개 전략만 활성화 or 중복 전략은 다른 Factor로 차별화

---

## Summary Table

| 항목 | 최고 | 최저 | 비고 |
|------|------|------|------|
| **신호 빈도** | scalping | swing, swing_bb | 타임프레임 의존 |
| **변동성 민감** | breakout | trend, swing | ATR 확대 필수 여부 |
| **Volume 의존** | breakout | trend | 거래량 급증 조건 |
| **Regime 의존** | reversion (Ranging) | trend (Trending) | 레짐 특화 전략 |
| **Multi-Symbol 확장** | trend | swing_bb | 범용성 차이 |
| **DD 크기** | swing | scalping, swing_bb | 타임프레임 비례 |
| **과최적화 위험** | swing_bb | trend | 파라미터 복잡도 |
