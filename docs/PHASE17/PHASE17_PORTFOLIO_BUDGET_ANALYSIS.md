# PHASE17: Portfolio Budget & Position Sizing 정밀 분석

**작성일**: 2025-01-XX  
**목적**: V4/V5/V5b Portfolio Budget 문제의 근본 원인 분석

---

## 📌 Executive Summary

### 핵심 문제
Position Sizer와 Portfolio Manager 사이에 Budget 정보 전달 없음 → Position Sizer가 Budget 무시하고 $10k-$15k 포지션 계산 → Portfolio Manager가 $12.5k Budget 초과 검증하여 BLOCK

### 근본 원인
1. Position Sizer: Budget을 전혀 알지 못함 (입력 파라미터 없음)
2. Portfolio Manager: Budget을 계산하지만 Position Sizer에 전달 안 함
3. Engine: Position Sizer 호출 시 Budget 정보 전달 안 함

---

## 🔍 1. 코드 흐름 분석

### Engine.py (Line 1150-1362)
```python
# STEP 1: Position Size 계산 (Budget 무지)
qty, meta = sizer.calculate(signal)  # ❌ available_budget 없음!

# STEP 2: Multi-position Scaling
scaled_risk = sizer.apply_multi_position_scaling(...)
qty = qty * risk_ratio

# STEP 3: Exposure Guard (심볼별 35% 한도)
exposure_decision = risk.check_symbol_exposure_with_adjustment(...)
if exposure_decision.decision == "ALLOW_REDUCED":
    qty = adjusted_qty  # 사이즈 축소

# STEP 4: Risk Manager 체크
allowed = risk.check_order(...)

# STEP 5: Portfolio Manager Budget 체크 (전략별 25% 한도)
can_open = portfolio.can_open_position(...)  # 🔴 여기서 BLOCK!
```

---

## 💰 2. Portfolio Budget 계산 (PortfolioManager)

### calculate_strategy_budget()
```python
budget = equity * budget_pct
# $50,000 * 0.25 = $12,500 (scalping 전략)
```

**Config** (`base.yml`):
```yaml
portfolio:
  budget:
    strategy_allocation:
      scalping: 0.25  # 25%
```

### can_open_position()
```python
strategy_exposure = sum(기존 포지션)  # $10,000
new_strategy_exposure = strategy_exposure + position_value  # $10,000 + $7,000
if new_strategy_exposure > strategy_budget:  # $17,000 > $12,500
    return False, "전략 예산 초과"
```

---

## 📏 3. Position Sizer 계산 (독립적!)

### calculate()
```python
base_qty = position_size(equity=$50k, risk_frac=0.003, ...)
position_value = base_qty * entry  # $9,000
if position_value > max_position_value:  # $15,000 체크
    position_value = max_position_value
# ❌ Strategy Budget ($12,500)는 전혀 고려 안 함!
```

---

## ⚖️ 4. Exposure Guard vs Portfolio Budget

| Guard | 범위 | 한도 | 결과 |
|-------|------|------|------|
| **Exposure Guard** | 심볼별 (BTCUSDT) | 35% ($17,500) | ✅ PASS |
| **Portfolio Budget** | 전략별 (scalping) | 25% ($12,500) | ❌ FAIL |

**충돌 발생**:
- Exposure Guard: $15,400 < $17,500 → ALLOW
- Portfolio Budget: $15,400 > $12,500 → BLOCK

---

## 🚨 5. 근본 원인 요약

### Position Sizer ↔ Portfolio Manager 단절
```
Position Sizer
├─ 입력: signal (entry, sl)
├─ 한도: max_position_notional ($15,000)
└─ ❌ Strategy Budget 정보 없음!

Portfolio Manager
├─ 계산: strategy_budget ($12,500)
└─ ❌ Position Sizer에 전달 안 함!

Engine
├─ sizer.calculate(signal)
└─ ❌ budget 정보 중간 전달 없음!
```

### SSOT 원칙 위반
```
✅ Portfolio Manager = Budget의 유일한 진실 소스
❌ Position Sizer = Budget 무시하고 독립적으로 계산
→ Single Source of Truth 원칙 위반!
```

---

## 💡 6. 해결 방향

### Option A (권장): Position Sizer에 budget 전달
```python
# Engine.py
available_budget = portfolio.get_available_budget(strategy)
qty, meta = sizer.calculate(signal, available_budget=available_budget)
```

### Option B: Portfolio Manager 참조
```python
class PositionSizer:
    def __init__(self, config, portfolio):
        self.portfolio = portfolio
```

### 기대 효과
- Position Sizer가 Budget 내에서만 크기 결정
- Portfolio Manager는 검증만 수행
- Budget 초과 BLOCK 발생률 90% 감소

---

**다음 작업**: TASK 2 - Portfolio Budget 재설계
