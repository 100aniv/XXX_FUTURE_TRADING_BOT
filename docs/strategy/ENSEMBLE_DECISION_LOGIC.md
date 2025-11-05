# 🎯 앙상블 결정 로직 (조합형)

**작성일**: 2025-10-18  
**목적**: 6개 전략 신호를 가중치로 조합하여 최종 매매 결정

---

## 📊 **앙상블 유형**

### **조합형 (Weighted Ensemble) ✅ 현재 구조**

```
각 전략이 독립적으로 신호 생성
    ↓
앙상블 조화기가 가중치로 조합
    ↓
최종 매매 결정 (BUY/SELL/HOLD)
```

**특징:**
- ✅ 각 전략 독립 실행
- ✅ 성과 기반 가중치
- ✅ 컨텍스트 보정 (레짐, 변동성)
- ✅ 다양성 페널티 (상관 높으면 감점)

### **생성형 (Meta-Learning) ❌ 향후**

```
여러 시그널을 학습 데이터로 사용
    ↓
ML 모델이 새로운 전략 생성
    ↓
완전히 새로운 매매 로직
```

---

## 🧮 **가중치 계산 공식**

### **1. 성과 기반 가중치**

```python
base_weight = α × winrate + β × sharpe - γ × |maxDD|

α = 0.50  # 승률 가중치
β = 0.30  # 샤프비율 가중치
γ = 0.20  # 최대낙폭 페널티
```

**예시:**
```python
SCALPING:
- winrate: 0.61 (정규화 0.8)
- sharpe: 1.2 (정규화 0.7)
- maxDD: -0.08 (정규화 0.6)

base_weight = 0.50×0.8 + 0.30×0.7 - 0.20×0.6
            = 0.40 + 0.21 - 0.12
            = 0.49
```

---

### **2. 컨텍스트 보정**

```python
context_weight = ζ × context_F1 + η × regime_alignment

ζ = 0.30  # 컨텍스트 적합도
η = 0.20  # 레짐 정합성
```

**레짐 정합성:**
```python
def regime_alignment_bonus(side, regime):
    if side == "BUY" and regime == "상승장":
        return 1.0
    if side == "SELL" and regime == "하락장":
        return 1.0
    return 0.5  # 중립
```

---

### **3. 다양성 페널티 (상관 기반)**

```python
diversity_penalty = 1.0 - λ × avg_correlation

λ = 0.50  # 상관 페널티 강도
```

**예시:**
```python
SCALPING과 다른 활성 전략들의 평균 상관: 0.42

diversity_penalty = 1.0 - 0.50 × 0.42
                  = 1.0 - 0.21
                  = 0.79

최종 가중치 = base_weight × diversity_penalty
            = 0.49 × 0.79
            = 0.39
```

---

### **4. 최종 가중치 (안정화)**

```python
# EMA 평활화
stable_weight = α × new_weight + (1-α) × prev_weight
α = 0.2  # EMA 계수

# 바운딩
final_weight = clip(stable_weight, w_min=0.05, w_max=0.60)
```

---

## 🎯 **매수/매도 점수 계산**

### **전략별 기여**

```python
for each strategy:
    if side == "BUY":
        buy_score += weight × confidence
    if side == "SELL":
        sell_score += weight × confidence

net_score = buy_score - sell_score
```

### **예시 계산**

| 전략 | Side | Confidence | Weight | 기여 |
|------|------|-----------|--------|------|
| SCALPING | BUY | 0.78 | 0.15 | +0.117 |
| DAYTRADE | BUY | 0.65 | 0.22 | +0.143 |
| REVERSION | HOLD | 0.40 | 0.18 | 0 |
| SWING | BUY | 0.62 | 0.20 | +0.124 |
| TREND | SELL | 0.45 | 0.15 | -0.068 |
| BREAKOUT | BUY | 0.70 | 0.10 | +0.070 |

```python
buy_score = 0.117 + 0.143 + 0.124 + 0.070 = 0.454
sell_score = 0.068
net_score = 0.454 - 0.068 = 0.386
```

---

## 🔀 **의사결정 (Deadband)**

### **임계값 적용**

```python
deadband = 0.10  # 데드밴드

if abs(net_score) < deadband:
    action = "HOLD"
    size = 0.0
else:
    action = "BUY" if net_score > 0 else "SELL"
    
    # 유효 구간 정규화
    effective = (abs(net_score) - deadband) / (1.0 - deadband)
    size = clip(effective, 0.0, 1.0) × max_position
```

### **예시**

```python
net_score = 0.386
deadband = 0.10

effective = (0.386 - 0.10) / (1.0 - 0.10)
          = 0.286 / 0.90
          = 0.318

action = "BUY"
size = 0.318 × 1.0 = 0.318 (31.8% 포지션)
```

---

## 📋 **전체 흐름**

```
1. 신호 수집 (6개 전략)
    ↓
2. 성과 메트릭 로드 (30일 실적)
    ↓
3. 가중치 계산
   ├─ 성과 기반 (승률, 샤프, DD)
   ├─ 컨텍스트 보정 (레짐, 변동성)
   ├─ 다양성 페널티 (상관)
   └─ EMA 안정화
    ↓
4. 매수/매도 점수 계산
    ↓
5. 의사결정 (Deadband)
    ↓
6. 리스크 가드 (최종 검증)
    ↓
7. 주문 실행
```

---

## 🔧 **하이퍼파라미터**

### **기본값**

```python
HP = {
    # 성과 가중치
    "alpha": 0.50,      # 승률
    "beta": 0.30,       # 샤프
    "gamma": 0.20,      # DD 페널티
    
    # 컨텍스트
    "zeta": 0.30,       # 컨텍스트 F1
    "eta": 0.20,        # 레짐 정합
    
    # 다양성
    "lambda_div": 0.50, # 상관 페널티
    
    # 안정화
    "ema": 0.2,         # EMA 계수
    "w_min": 0.05,      # 최소 가중치
    "w_max": 0.60,      # 최대 가중치
    
    # 의사결정
    "deadband": 0.10,   # 데드밴드
    "max_position": 1.0 # 최대 포지션
}
```

### **튜닝 가이드**

| 파라미터 | 높이면 | 낮추면 |
|---------|--------|--------|
| **alpha** (승률) | 승률 높은 전략 선호 | 다른 요소 중시 |
| **lambda_div** | 다양성 강조 | 상관 무시 |
| **deadband** | 거래 적어짐 | 거래 많아짐 |
| **ema** | 변화 빠름 | 안정적 |

---

## 📊 **실전 예시**

### **시나리오: 상승장, 고변동성**

```python
context = {
    "regime": "상승장",
    "vol": "high",
    "tod": "london"
}

signals = [
    {"strategy": "SCALPING", "side": "BUY", "conf": 0.78},
    {"strategy": "DAYTRADE", "side": "BUY", "conf": 0.65},
    {"strategy": "REVERSION", "side": "HOLD", "conf": 0.40},
    {"strategy": "SWING", "side": "BUY", "conf": 0.62},
    {"strategy": "TREND", "side": "BUY", "conf": 0.82},
    {"strategy": "BREAKOUT", "side": "BUY", "conf": 0.88}
]

결과:
- buy_score: 0.65
- sell_score: 0.02
- net_score: 0.63
- action: BUY
- size: 0.59 (59% 포지션)
```

---

## 🚀 **구현 위치**

### **현재 ensemble_bot.py**

```python
# 기존 함수들
load_strategy_performance()   # 성과 로드
fetch_recent_signals()         # 신호 수집
calc_regime_fit()              # 레짐 적합도

# ⭐ 추가 필요
ensemble_decision()            # 조합형 결정 로직
calculate_weights()            # 가중치 계산
apply_diversity_penalty()      # 다양성 페널티
```

---

## 📚 **참고**

- [6개 전략 통합](./ENSEMBLE_6_STRATEGIES.md)
- [백테스트 전략](./BACKTEST_STRATEGY.md)
- [Trading Executor](./TRADING_EXECUTOR.md)

---

**Last Updated:** 2025-10-18  
**Status:** 설계 완료, 구현 대기
