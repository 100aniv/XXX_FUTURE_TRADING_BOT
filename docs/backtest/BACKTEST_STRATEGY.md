# 🎯 백테스트 & 튜닝 전략

**작성일**: 2025-10-18  
**목표**: 하루 10% 수익 달성을 위한 체계적 튜닝

---

## 🚨 **현재 상태 - 중요!**

### ❌ **문제점 발견**

```python
# ensemble_bot.py (라인 88-91)
CFG = {
    "weight_trend": 2.5,        # TREND만
    "weight_reversion": 2.0,    # REVERSION만
    "weight_breakout": 2.2,     # BREAKOUT만
}

# ❌ SCALPING, DAYTRADE, SWING 빠짐!
```

**현재: 3개 전략만 사용**
- ✅ TREND
- ✅ REVERSION
- ✅ BREAKOUT
- ❌ SCALPING (없음)
- ❌ DAYTRADE (없음)
- ❌ SWING (없음)

---

## 📊 **6개 전략으로 확장 필요**

### 수정 필요: ensemble_bot.py

```python
CFG = {
    # 6개 전략 가중치
    "weight_trend": 2.5,        # TREND: 4h 추세 추종
    "weight_reversion": 2.0,    # REVERSION: 15m 평균회귀
    "weight_breakout": 2.2,     # BREAKOUT: 1h 돌파
    "weight_scalping": 1.8,     # SCALPING: 1m 초단타 ⭐ 추가
    "weight_daytrade": 2.3,     # DAYTRADE: 15m 단타 ⭐ 추가
    "weight_swing": 2.1,        # SWING: 1h 스윙 ⭐ 추가
    
    # ...
}
```

---

## 🎯 **백테스트 전략 (단계별)**

### **Phase 1: 개별 전략 튜닝 (6주)**

각 전략을 독립적으로 최적화

#### Week 1-6: 개별 전략 백테스트

| 주차 | 전략 | 타임프레임 | 목표 승률 | 목표 RR | 일일 목표 |
|------|------|-----------|----------|---------|----------|
| 1주 | SCALPING | 1m | 50-55% | 1.5 | 3-5% |
| 2주 | DAYTRADE | 15m | 55-60% | 1.8 | 4-6% |
| 3주 | REVERSION | 15m | 55-62% | 1.6 | 3-5% |
| 4주 | SWING | 1h | 60-68% | 2.0 | 3-4% |
| 5주 | TREND | 4h | 60-70% | 2.2 | 2-4% |
| 6주 | BREAKOUT | 1h | 58-65% | 2.0 | 3-5% |

#### 튜닝 파라미터 (각 전략)

```bash
# 백테스트 반복
for RR in [1.5, 1.8, 2.0, 2.2, 2.5]:
    for ATR_MULT_SL in [1.0, 1.2, 1.5]:
        for RISK_PER_TRADE in [0.01, 0.015, 0.02]:
            # 백테스트 실행
            backtest(RR, ATR_MULT_SL, RISK_PER_TRADE)
            # 결과 기록
            save_results(winrate, sharpe, max_dd, daily_avg)
```

#### 최적화 목표

```python
# 각 전략의 최적 파라미터 찾기
{
    "winrate": 최대화 (> 55%),
    "sharpe": 최대화 (> 1.5),
    "max_drawdown": 최소화 (< 10%),
    "daily_pnl": 최대화 (> 3%)
}
```

---

### **Phase 2: 앙상블 가중치 튜닝 (2주)**

6개 전략 통합 최적화

#### Week 7: 가중치 그리드 서치

```python
# 가중치 조합 테스트
weights_grid = {
    "scalping": [1.5, 1.8, 2.0, 2.2],
    "daytrade": [2.0, 2.2, 2.5, 2.8],
    "reversion": [1.8, 2.0, 2.2],
    "swing": [1.8, 2.0, 2.2],
    "trend": [2.2, 2.5, 2.8],
    "breakout": [2.0, 2.2, 2.5]
}

best_combination = grid_search(weights_grid)
```

#### Week 8: 앙상블 파라미터 튜닝

```bash
# 튜닝 파라미터
THETA_LONG: [0.10, 0.12, 0.15, 0.18, 0.20]
THETA_SHORT: [0.10, 0.12, 0.15, 0.18, 0.20]
CONSENSUS_BONUS: [0.1, 0.15, 0.2, 0.25]
HTF_REGIME_BONUS: [0.15, 0.2, 0.25]
```

---

### **Phase 3: 통합 테스트 (1주)**

#### Week 9: 전체 시스템 백테스트

```bash
# 3개월 데이터 백테스트
- 기간: 2024-07-01 ~ 2024-10-01
- 전략: 6개 동시 실행
- 목표: 일일 평균 8-12%
```

---

## 📋 **롱/숏 임계값 (Threshold) 설정**

### 현재 설정

```python
"theta_long": 0.15,   # 15% 이상 → LONG
"theta_short": 0.15,  # 15% 이상 → SHORT
```

### 임계값 의미

```
앙상블 점수: -1.0 ~ +1.0

┌─────────────┬─────────────┬─────────────┐
│   SHORT     │    HOLD     │    LONG     │
│ < -0.15     │ -0.15~0.15  │   > 0.15    │
└─────────────┴─────────────┴─────────────┘
```

### 임계값별 특성

| THETA | 거래 빈도 | 승률 기대 | 수익 기대 | 리스크 |
|-------|----------|----------|----------|--------|
| 0.08 | 매우 높음 | 낮음 (52%) | 낮음 | 높음 |
| 0.12 | 높음 | 보통 (55%) | 보통 | 보통 |
| **0.15** | **중간** | **높음 (58%)** | **높음** | **중간** ⭐ |
| 0.18 | 낮음 | 높음 (62%) | 중간 | 낮음 |
| 0.25 | 매우 낮음 | 매우 높음 (68%) | 낮음 | 매우 낮음 |

### 하루 10% 목표 권장 설정

```bash
# 공격적 (많은 거래)
THETA_LONG=0.10
THETA_SHORT=0.10

# 균형 (추천)
THETA_LONG=0.12
THETA_SHORT=0.12

# 보수적 (적은 거래, 높은 승률)
THETA_LONG=0.15
THETA_SHORT=0.15
```

---

## 🔧 **백테스트 실행 방법**

### 1. 개별 전략 백테스트

```bash
# 스캘핑 전략 백테스트
python backtest.py \
  --strategy scalping \
  --config config_scalp.txt \
  --start 2024-07-01 \
  --end 2024-10-01 \
  --output results/scalping_bt.json

# 파라미터 스위프
./run_param_sweep.sh scalping
```

### 2. 앙상블 백테스트

```bash
# 6개 전략 통합
python backtest_ensemble.py \
  --weights "2.0,2.3,2.0,2.1,2.5,2.2" \
  --theta-long 0.12 \
  --theta-short 0.12 \
  --start 2024-07-01 \
  --end 2024-10-01
```

### 3. 결과 분석

```bash
# 성과 리포트 생성
python analyze_results.py \
  --input results/*.json \
  --output report.html
```

---

## 📊 **백테스트 체크리스트**

### Phase 1: 개별 전략 (각 전략마다)

- [ ] 3개월 데이터 수집
- [ ] RR 파라미터 스위프 (1.5-3.0)
- [ ] ATR_MULT_SL 스위프 (1.0-2.0)
- [ ] RISK_PER_TRADE 스위프 (0.01-0.03)
- [ ] 최적 조합 선택
- [ ] 승률/샤프/MDD 기록
- [ ] config 파일 업데이트

### Phase 2: 앙상블

- [ ] 6개 전략 가중치 그리드 서치
- [ ] THETA 임계값 튜닝
- [ ] 보너스/패널티 파라미터 튜닝
- [ ] 3개월 통합 백테스트
- [ ] 일일 평균 수익 10% 달성 확인

### Phase 3: 검증

- [ ] Out-of-sample 테스트 (최근 1개월)
- [ ] 다양한 시장 상황 테스트
- [ ] 슬리피지/수수료 반영
- [ ] 최악 시나리오 시뮬레이션
- [ ] Paper Trading 1주일

---

## 🎯 **최종 목표 설정**

### 하루 10% 달성 조건

```python
# 필요 조건
{
    "total_trades_per_day": 30-50,      # 충분한 거래 기회
    "avg_winrate": 0.56,                # 56% 승률
    "avg_rr": 2.0,                      # RR 2.0
    "max_drawdown": "< 8%",             # 최대 낙폭 8% 이하
    "sharpe_ratio": "> 1.8",            # 샤프 비율 1.8+
    "slippage_impact": "< 0.5%/day"     # 슬리피지 영향 0.5% 이하
}
```

### 전략별 기여도 (예상)

| 전략 | 거래/일 | 승률 | RR | 일일 기여 | 자본 배분 |
|------|--------|------|----|-----------| ----------|
| Scalping | 15회 | 52% | 1.5 | 2.5% | 20% |
| Daytrade | 12회 | 58% | 2.0 | 3.0% | 25% |
| Reversion | 8회 | 60% | 1.8 | 2.0% | 15% |
| Swing | 5회 | 65% | 2.2 | 1.5% | 15% |
| Trend | 3회 | 68% | 2.5 | 1.0% | 15% |
| Breakout | 7회 | 62% | 2.0 | 2.0% | 10% |
| **Total** | **50회** | **58%** | **2.0** | **12%** | **100%** |

---

## ⚠️ **주의사항**

1. **과최적화 방지**
   - Train/Test 분리 (70%/30%)
   - Walk-forward 분석
   - Out-of-sample 검증

2. **현실적 가정**
   - 슬리피지: 0.05%
   - 수수료: 0.04% (Maker+Taker)
   - 체결 지연: 1-3초

3. **리스크 관리**
   - 일일 손실 한도: 5%
   - 연속 손실 시 중단
   - 변동성 급등 시 축소

---

**Last Updated:** 2025-10-18  
**Next Step:** ensemble_bot.py에 6개 전략 추가
