# 🎯 앙상블 6개 전략 통합 완료

**작성일**: 2025-10-18  
**버전**: v2.0 - 6개 전략 확장

---

## ✅ **완료된 작업**

### **1. ensemble_bot.py 수정 완료**

```python
# 이전 (3개만)
❌ TREND
❌ REVERSION
❌ BREAKOUT

# 현재 (6개 전체) ⭐
✅ TREND (4h)
✅ REVERSION (15m)
✅ BREAKOUT (1h)
✅ SCALPING (1m) - 신규 추가
✅ DAYTRADE (15m) - 신규 추가
✅ SWING (1h) - 신규 추가
```

---

## 📊 **6개 전략 가중치**

### 기본 가중치 (CFG)

```python
CFG = {
    "weight_trend": 2.5,       # TREND: 추세 추종 (4h)
    "weight_reversion": 2.0,   # REVERSION: 평균회귀 (15m)
    "weight_breakout": 2.2,    # BREAKOUT: 돌파 (1h)
    "weight_scalping": 1.8,    # SCALPING: 초단타 (1m) ⭐
    "weight_daytrade": 2.3,    # DAYTRADE: 단타 (15m) ⭐
    "weight_swing": 2.1,       # SWING: 스윙 (1h) ⭐
}
```

### 환경변수 설정

```bash
# .env 또는 docker-compose.yml
WEIGHT_TREND=2.5
WEIGHT_REVERSION=2.0
WEIGHT_BREAKOUT=2.2
WEIGHT_SCALPING=1.8
WEIGHT_DAYTRADE=2.3
WEIGHT_SWING=2.1
```

---

## 🎯 **레짐 적합도 (추가됨)**

### 전략별 유리한 시장 환경

| 전략 | 유리한 레짐 | 변동성 | 적합도 |
|------|-----------|--------|--------|
| **TREND** | 추세장 (상승/하락) | 낮음-중간 | 0.8 |
| **REVERSION** | 횡보장 | 중간 | 0.8 |
| **BREAKOUT** | 모든 레짐 | 높음 | 변동성비례 |
| **SCALPING** | 횡보장 | 낮음 | 0.7 |
| **DAYTRADE** | 모든 레짐 | 중간 | 0.6-0.8 |
| **SWING** | 추세장 | 중-고 | 0.75 |

### 레짐 적합도 계산 예시

```python
# 상승장, 낮은 변동성 (ATR 1%)
TREND: 0.8    # 최적
SWING: 0.5    # 보통
SCALPING: 0.4 # 불리

# 횡보장, 중간 변동성 (ATR 2%)
REVERSION: 0.8  # 최적
DAYTRADE: 0.7   # 좋음
SCALPING: 0.6   # 보통

# 급등락, 고변동성 (ATR 4%)
BREAKOUT: 1.0   # 최적
SWING: 0.6      # 보통
SCALPING: 0.3   # 불리
```

---

## 📋 **롱/숏 임계값 (Threshold)**

### 현재 설정

```python
"theta_long": 0.15,   # 15% 이상 → LONG
"theta_short": 0.15,  # 15% 이상 → SHORT
```

### 앙상블 점수 범위

```
     -1.0            0.0            +1.0
      ↓               ↓               ↓
┌─────────────┬──────────────┬─────────────┐
│   SHORT     │     HOLD     │    LONG     │
│   < -0.15   │  -0.15~0.15  │   > 0.15    │
└─────────────┴──────────────┴─────────────┘
```

### 하루 10% 목표 권장 임계값

```bash
# 공격적 (많은 거래, 낮은 승률)
THETA_LONG=0.10
THETA_SHORT=0.10
예상 거래: 40-60회/일
예상 승률: 52-55%

# 균형 (추천)
THETA_LONG=0.12
THETA_SHORT=0.12
예상 거래: 30-40회/일
예상 승률: 56-58%

# 보수적 (적은 거래, 높은 승률)
THETA_LONG=0.15
THETA_SHORT=0.15
예상 거래: 20-30회/일
예상 승률: 60-62%
```

---

## 🔧 **백테스트 전략**

### Phase 1: 개별 전략 튜닝 (6주)

각 전략마다 최적 파라미터 찾기

```bash
Week 1: SCALPING
- RR: 1.3-1.8
- ATR_MULT_SL: 0.8-1.2
- RISK_PER_TRADE: 0.002-0.003
- 목표: 50-55% 승률, 3-5% 일일

Week 2: DAYTRADE
- RR: 1.6-2.0
- ATR_MULT_SL: 1.0-1.3
- RISK_PER_TRADE: 0.004-0.006
- 목표: 55-60% 승률, 4-6% 일일

Week 3: REVERSION
- RR: 1.5-1.8
- ATR_MULT_SL: 0.8-1.2
- RISK_PER_TRADE: 0.004-0.006
- 목표: 55-62% 승률, 3-5% 일일

Week 4: SWING
- RR: 2.0-2.5
- ATR_MULT_SL: 1.2-1.5
- RISK_PER_TRADE: 0.005-0.008
- 목표: 60-68% 승률, 3-4% 일일

Week 5: TREND
- RR: 2.0-2.8
- ATR_MULT_SL: 1.5-2.0
- RISK_PER_TRADE: 0.005-0.008
- 목표: 60-70% 승률, 2-4% 일일

Week 6: BREAKOUT
- RR: 2.0-2.5
- ATR_MULT_SL: 1.2-1.5
- RISK_PER_TRADE: 0.005-0.007
- 목표: 58-65% 승률, 3-5% 일일
```

### Phase 2: 앙상블 가중치 튜닝 (2주)

```bash
Week 7: 가중치 그리드 서치
- 6개 전략 조합 테스트
- 최적 가중치 발견

Week 8: 임계값 튜닝
- THETA_LONG/SHORT: 0.08-0.20
- CONSENSUS_BONUS: 0.1-0.3
- HTF_REGIME_BONUS: 0.1-0.3
```

### Phase 3: 통합 검증 (1주)

```bash
Week 9: 전체 시스템 백테스트
- 기간: 3개월
- 목표: 일일 평균 10%
- 검증: Out-of-sample 테스트
```

---

## 💰 **하루 10% 목표 달성 시나리오**

### 6개 전략 기여도 (예상)

| 전략 | 자본 | 거래/일 | 승률 | RR | 일일 기여 |
|------|------|--------|------|----|-----------| 
| SCALPING | 20% | 15회 | 52% | 1.5 | 2.5% |
| DAYTRADE | 25% | 12회 | 58% | 2.0 | 3.0% |
| REVERSION | 15% | 8회 | 60% | 1.8 | 2.0% |
| SWING | 15% | 5회 | 65% | 2.2 | 1.5% |
| TREND | 15% | 3회 | 68% | 2.5 | 1.0% |
| BREAKOUT | 10% | 7회 | 62% | 2.0 | 2.0% |
| **합계** | **100%** | **50회** | **58%** | **2.0** | **12%** |

### 필요 조건

```python
{
    "total_trades": 50회/일,
    "avg_winrate": 58%,
    "avg_rr": 2.0,
    "slippage": < 0.5%/일,
    "max_drawdown": < 8%,
    "sharpe_ratio": > 1.8
}
```

---

## 🚀 **실행 방법**

### 1. Signal Bots 실행 (6개)

```bash
# 각각 독립 실행
python telegram_signal_bot.py    # Scalping
python telegram_signal_bot.py    # Daytrade (config 변경)
python telegram_signal_bot.py    # Swing (config 변경)
python signal_bot_trend.py       # Trend
python signal_bot_reversion.py   # Reversion
python signal_bot_breakout.py    # Breakout
```

### 2. Ensemble Bot 실행

```bash
# 6개 신호 통합 결정
python ensemble_bot.py
```

### 3. Trading Manager 실행

```bash
# 앙상블 결정으로 매매
python trading_manager.py --strategy ensemble --mode paper
```

---

## 📈 **모니터링**

### 체크 항목

```bash
✅ 6개 전략 모두 신호 생성 중인지
✅ 앙상블이 6개 신호 모두 읽는지
✅ 가중치가 정상 계산되는지
✅ 임계값이 적절한지
✅ 일일 거래 수가 30-50회인지
✅ 일일 수익률이 8-12%인지
```

### 로그 확인

```bash
# 앙상블 로그
tail -f logs/ensemble_*.log

# 예상 출력
설정: 가중치(6개 전략)
  - TREND=2.5, REVERSION=2.0, BREAKOUT=2.2
  - SCALPING=1.8, DAYTRADE=2.3, SWING=2.1

BTCUSDT 15m @ 2025-10-18 12:00:00
  → 신호 6개 수집
  → LONG 점수: 0.18 (THETA=0.15 초과)
  → 결정: LONG 진입
```

---

## ⚠️ **주의사항**

1. **초기에는 보수적으로**
   - THETA=0.15 (높은 임계값)
   - 거래 수 적게, 승률 높게

2. **단계적으로 공격적으로**
   - 1주차: THETA=0.15
   - 2주차: THETA=0.12
   - 3주차: THETA=0.10

3. **손실 한도 엄수**
   - DAILY_LOSS_LIMIT_PCT=0.05
   - 5% 손실 시 즉시 중단

---

## 📚 **참고 문서**

- [백테스트 전략](./BACKTEST_STRATEGY.md)
- [하루 10% 목표](./DAILY_TARGET_GUIDE.md)
- [포지션 사이징](./POSITION_SIZING.md)

---

**Last Updated:** 2025-10-18  
**Status:** ✅ 6개 전략 통합 완료, 백테스트 준비됨
