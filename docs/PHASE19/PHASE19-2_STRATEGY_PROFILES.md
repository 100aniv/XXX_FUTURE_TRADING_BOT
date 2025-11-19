# PHASE19-2: Strategy Profiles (Compact)
**작성일**: 2025-11-19  
**목적**: Ensemble Score System 설계를 위한 전략 프로파일

---

## 1. scalping (v3.0, 1-5m)

**진입**: Fresh EMA Cross (≤12 candles) + Price Align + Pattern A/B (Volume/Momentum)  
**청산**: RR 1.3, SL ATR×0.8, 30분 제한  
**지표**: EMA(8,21), RSI, ATR, Volume  
**장점**: 고빈도, 추세 초기 포착, Late Entry 방지  
**단점**: Ranging whipsaw, 거래비용 누적, 변동성 의존  
**레짐**: Trending ⭐⭐⭐⭐⭐ | Breakout ⭐⭐⭐ | Ranging ⭐ | Chaos ⭐⭐  
**역할**: Early Signal Provider, High Freq Anchor  
**Score Factor**: momentum(0.4), trend_strength(0.3), volume(0.2), freshness(0.1)

---

## 2. breakout (v1.0, 15m-1h)

**진입**: Donchian 돌파 + EMA Trend + ATR 확대(선택) + Volume Surge(선택)  
**청산**: RR 2-3, SL ATR배수 (변동성 조정)  
**지표**: Donchian, EMA(F/M/S), ATR, MACD, RSI, Volume  
**장점**: 추세 전환 포착, 명확한 트리거, 변동성 적응  
**단점**: False Breakout, 지연 진입, Ranging 취약  
**레짐**: Trending ⭐⭐⭐⭐ | Breakout ⭐⭐⭐⭐⭐ | Ranging ⭐ | Chaos ⭐⭐  
**역할**: Breakout Specialist, Volatility Detector  
**Score Factor**: breakout_prob(0.5), volatility(0.2), volume(0.2), ema_align(0.1)

---

## 3. reversion (v3.0, 5-30m)

**진입**: (RSI<35 + BB≤98%) + (MACD전환 OR 양봉 OR 거래량) 2단계  
**청산**: RR 1.5-2, SL ATR배수 (변동성 조정), BB 중심 조기청산  
**지표**: RSI, BB, MACD, EMA, Volume, ATR  
**장점**: 역추세 포착, 2단계 필터, Ranging 강점  
**단점**: 추세 시장 취약, Knife Catching, 반전 실패 위험  
**레짐**: Trending ⭐⭐ | Breakout ⭐ | Ranging ⭐⭐⭐⭐⭐ | Chaos ⭐⭐⭐  
**역할**: Counter-Trend Specialist, Ranging Anchor  
**Score Factor**: overbought_oversold(0.5), bb_distance(0.3), macd_reversal(0.1), volume(0.1)

---

## 4. trend (v1.0, 1-4h)

**진입**: EMA 3선 정렬 + MACD 방향 + RSI 40-70 (선택)  
**청산**: RR 2-3, SL ATR배수, 정렬 붕괴 시 청산  
**지표**: EMA(F/M/S), MACD, RSI, ATR  
**장점**: 추세 추종 전통, 명확한 신호, 중장기 안정, 과열 회피  
**단점**: 지연 진입, Ranging 무력, Whipsaw, 큰 DD  
**레짐**: Trending ⭐⭐⭐⭐⭐ | Breakout ⭐⭐⭐ | Ranging ⭐ | Chaos ⭐⭐  
**역할**: Trend Confirmer, Mid-Term Anchor  
**Score Factor**: trend_strength(0.5), macd_momentum(0.3), rsi_neutrality(0.1), persistence(0.1)

---

## 5. swing (v1.0, 4h-1d)

**진입**: EMA 정렬 + MACD + RSI≥35 + BB/Donchian 돌파(선택)  
**청산**: RR 2-3, SL ATR배수 (변동성 조정), 정렬 붕괴 시  
**지표**: EMA, MACD, RSI, BB, Donchian, ATR  
**장점**: 다목적(Pullback+Breakout), 장기 안정, 유연 조건  
**단점**: 지연 진입, 신호 희박, 큰 SL, Ranging 무력  
**레짐**: Trending ⭐⭐⭐⭐⭐ | Breakout ⭐⭐⭐⭐ | Ranging ⭐⭐ | Chaos ⭐⭐  
**역할**: Long-Term Anchor, Multi-Pattern Detector  
**Score Factor**: trend_strength(0.4), momentum(0.3), breakout_bonus(0.2), stability(0.1)

---

## 6. swing_bb (v1.0, 5m 저빈도)

**진입**: BB 반등(2캔들 패턴) + EMA 정렬 + MACD 크로스 + RSI + 거래량 (AND 구조)  
**청산**: RR 기본, SL ATR배수, BB 중심 회귀 시  
**지표**: BB, EMA, MACD, RSI, Volume, ATR  
**장점**: 정교한 필터, BB 반등 패턴, 조건 완화 파라미터  
**단점**: 신호 극히 희박(0.3건/일), 조건 복잡, 과최적화 위험  
**레짐**: Trending ⭐ | Breakout ⭐ | Ranging ⭐⭐⭐⭐⭐ | Chaos ⭐⭐  
**역할**: Low-Frequency Specialist, BB Bounce Detector  
**Score Factor**: bb_bounce_pattern(0.5), ema_align(0.2), macd_cross(0.2), volume(0.1)

---

## 7. daytrade (v1.0, 15m-1h)

**진입**: EMA 정렬 + MACD + RSI≥35 + BB 돌파(선택)  
**청산**: RR 기본, SL ATR배수 (변동성 조정)  
**지표**: EMA, MACD, RSI, BB, ATR  
**장점**: 단타 특화, 명확한 조건, 변동성 적응  
**단점**: swing과 유사(중복), 신호 빈도 중간, 차별성 부족  
**레짐**: Trending ⭐⭐⭐⭐ | Breakout ⭐⭐⭐ | Ranging ⭐⭐ | Chaos ⭐⭐  
**역할**: Mid-Frequency Trader (swing과 중복)  
**Score Factor**: trend_strength(0.4), momentum(0.3), breakout_bonus(0.2), timeframe_fit(0.1)

---

## 전략 간 차별성 요약

| 전략 | 핵심 차별 요소 | 타임프레임 | 신호 빈도 |
|------|---------------|-----------|----------|
| scalping | Fresh Cross 메커니즘 | 1-5m | 높음 |
| breakout | Donchian 돌파 | 15m-1h | 중간 |
| reversion | RSI+BB 2단계 역추세 | 5-30m | 중간 |
| trend | EMA 3선 정렬 추세 추종 | 1-4h | 낮음 |
| swing | 다목적 장기 | 4h-1d | 매우 낮음 |
| swing_bb | BB 반등 패턴 (저빈도) | 5m | 극히 낮음 |
| daytrade | swing 유사 (중복) | 15m-1h | 중간 |
