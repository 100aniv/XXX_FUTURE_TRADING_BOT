# ⚡ 극단적 레버리지 전략 (Phase 2)

**작성일**: 2025-10-18  
**우선순위**: Phase 2 (백테스트 후)

---

## 🎯 **개념**

### **100% 먹는 신호 = 극단적 레버리지**

```
일반 신호 (60-80% 확신)
→ 2-10배 레버리지

극단적 신호 (95%+ 확신)
→ 50-200배 레버리지 ⚡
→ 적은 금액 (전체 자산의 1-2%)
```

---

## 📊 **조건**

### **극단적 레버리지 적용 조건**

```python
if (
    ensemble_confidence >= 0.95 AND
    all_6_strategies_agree AND
    regime_alignment >= 0.9 AND
    recent_winrate >= 0.85 AND
    volatility < threshold
):
    leverage = 50-200배
    position_size = 1-2% of equity
```

### **구체적 체크리스트**

1. **앙상블 확신도**: 95% 이상
2. **6개 전략 합의**: 모두 동일 방향
3. **레짐 정합**: 90% 이상
4. **최근 승률**: 85% 이상 (최근 20거래)
5. **변동성**: 낮음 (급변 시 제외)
6. **유동성**: 충분 (슬리피지 최소)

---

## 💰 **리스크 관리**

### **포지션 크기**

```python
# 극단적 레버리지 = 적은 금액
equity = 10,000 USDT
extreme_allocation = 1-2%  # 100-200 USDT

leverage = 100배
position_value = 200 USDT × 100 = 20,000 USDT

# 청산 위험
liquidation_distance = 1 / leverage = 1%
→ 1% 역행 시 청산
```

### **안전 장치**

```python
# 1. 최대 손실 제한
max_loss_per_extreme = 100 USDT (1%)

# 2. 일일 극단적 거래 한도
max_extreme_trades_per_day = 2

# 3. 연속 실패 시 중단
if consecutive_extreme_losses >= 2:
    disable_extreme_for_24h = True

# 4. 포지션 타임아웃
max_hold_time = 5분 (초단타)
```

---

## 🔍 **예시 시나리오**

### **Case 1: 완벽한 셋업**

```python
상황:
- BTCUSDT, 횡보장 → 돌파 직전
- 6개 전략 모두 BUY
- Ensemble confidence: 0.97
- 최근 20거래 승률: 88%
- ATR 1.2% (낮음)

실행:
- Leverage: 100배
- Position: 150 USDT (1.5%)
- Stop Loss: 0.5% (75 USDT 손실)
- Take Profit: 2% (3,000 USDT 수익)

결과:
- 위험: 75 USDT
- 보상: 3,000 USDT
- RR: 40:1 ⚡
```

### **Case 2: 거부 사례**

```python
상황:
- Ensemble confidence: 0.96 (높음)
- 하지만 변동성 급등 (ATR 4%)

결과:
❌ 극단적 레버리지 거부
✅ 일반 레버리지 적용 (5배)

이유: 변동성 높아 청산 위험
```

---

## 🧮 **백테스트 검증**

### **Phase 1: 조건 발견**

```bash
# 10년 데이터 백테스트
- 극단적 신호 발생 빈도: ?
- 실제 승률: ?
- 평균 RR: ?
- 청산 비율: ?
```

### **Phase 2: 최적화**

```bash
# 최적 조건 찾기
for confidence in [0.90, 0.92, 0.95, 0.98]:
    for leverage in [50, 75, 100, 150, 200]:
        for max_hold in [1분, 3분, 5분, 10분]:
            backtest(...)
            if sharpe > best_sharpe:
                save_best_params()
```

---

## ⚠️ **위험성**

### **청산 위험**

```
100배 레버리지:
- 1% 역행 → 청산
- 0.5% 역행 → 50% 손실
- 극도로 위험!

대책:
✅ 매우 적은 금액 (1-2%)
✅ 초단타 (1-5분)
✅ 즉시 익절 (2-5%)
```

### **슬리피지**

```
큰 레버리지 = 큰 포지션
→ 슬리피지 증가
→ 예상보다 나쁜 진입가

대책:
✅ 유동성 체크
✅ 호가창 깊이 확인
✅ 분할 진입
```

---

## 🚀 **구현 계획**

### **Phase 1: 백테스트 (현재)**

```bash
# 일반 레버리지만 사용
MIN_LEVERAGE=2
MAX_LEVERAGE=10
ENABLE_EXTREME_LEVERAGE=false
```

### **Phase 2: 극단적 신호 탐색 (3개월 후)**

```python
# 백테스트 결과 분석
extreme_signals = find_signals(
    confidence >= 0.95,
    all_agree = True,
    winrate >= 0.85
)

# 빈도 및 성과 분석
print(f"극단적 신호 발생: {len(extreme_signals)}회/년")
print(f"평균 승률: {극단적_승률}%")
print(f"평균 RR: {극단적_RR}")
```

### **Phase 3: 실전 적용 (6개월 후)**

```python
# 조건부 활성화
ENABLE_EXTREME_LEVERAGE=true
EXTREME_LEVERAGE_MAX=100  # 보수적 시작
EXTREME_CONFIDENCE_MIN=0.97  # 엄격한 조건
```

---

## 📋 **체크리스트**

### **백테스트 단계**

- [ ] 10년 데이터 수집
- [ ] 극단적 신호 빈도 측정
- [ ] 실제 승률 검증 (95%+ 확신 신호)
- [ ] 청산 비율 분석
- [ ] 최적 레버리지 발견 (50-200배 중)
- [ ] 슬리피지 영향 측정

### **Paper Trading 단계**

- [ ] 극단적 신호 실시간 추적
- [ ] 가상 실행 (DRY_RUN)
- [ ] 1개월 검증
- [ ] 안전 장치 테스트

### **Live 단계**

- [ ] 최소 금액으로 시작 (50 USDT)
- [ ] 1주일 모니터링
- [ ] 점진적 증가
- [ ] 일일 리뷰

---

## 💡 **결론**

### **극단적 레버리지는**

```
✅ 가능: 조건이 완벽할 때
✅ 수익: 극대화 (40:1 RR)
⚠️ 위험: 극대화 (1% 청산)
❌ 남용: 절대 금지

원칙:
1. 매우 적은 금액 (1-2%)
2. 초단타 (1-5분)
3. 엄격한 조건 (95%+ 확신)
4. 충분한 백테스트 검증
```

---

**Last Updated:** 2025-10-18  
**Status:** 설계 완료, Phase 2 구현 대기
