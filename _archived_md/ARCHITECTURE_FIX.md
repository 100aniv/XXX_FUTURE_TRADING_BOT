# 🏗️ 아키텍처 수정 사항

**작성일**: 2025-10-19  
**이슈**: 백테스트 vs 실전 모듈 불일치

---

## 🚨 **문제점**

### **Before (잘못된 구조)**

```
backtest/backtest_engine.py
  ├─ calculate_position_size()  ❌ 독자적
  ├─ calculate_fee()            ❌ 독자적  
  └─ Trade.close()              ❌ 독자적

execution/
  ├─ PositionSizer             ❌ 독자적
  └─ RiskManager               ❌ 독자적

→ 같은 기능을 2곳에서 구현
→ 수정 시 2곳 모두 수정 필요
→ 불일치 발생!
```

---

## ✅ **해결책**

### **After (올바른 구조)**

```
execution/ (공통 모듈)
  ├─ position_sizer.py    ⭐ 모든 모드 공통
  ├─ risk_manager.py      ⭐ 모든 모드 공통
  ├─ trade.py             ⭐ Trade 클래스 (PnL 계산)
  └─ executor.py          ⭐ 주문 실행 (모드별 분기)

backtest/backtest_engine.py
  └─ execution 모듈 사용!   ✅ 재사용

main.py
  └─ TRADING_MODE에 따라 분기
     ├─ backtest: 과거 데이터 + 시뮬레이션
     ├─ paper:    실시간 + 가상 주문
     └─ live:     실시간 + 실제 주문
```

---

## 🔧 **수정 내용**

### **1. backtest_engine.py**

```python
# Before
class BacktestEngine:
    def calculate_position_size(self, ...):
        # 독자적 로직
        ...

# After
class BacktestEngine:
    def __init__(self):
        self.position_sizer = PositionSizer()  # execution 모듈 사용!
        self.risk_manager = RiskManager()
```

### **2. 포지션 크기 계산**

```python
# Before (백테스트 독자적)
quantity = self.calculate_position_size(confidence, price, atr)

# After (execution 모듈 사용)
signal_for_sizer = {
    'entry_price': entry_price,
    'sl_price': sl_price,
    'confidence': confidence,
    'atr': atr,
}
quantity, metadata = self.position_sizer.calculate(signal_for_sizer)
```

### **3. PnL 계산**

```python
# Before (잘못된 계산)
gross_pnl = price_diff * self.quantity  # quantity가 USDT면 큰 오류!

# After (올바른 계산)
coins = self.quantity / self.entry_price  # 코인 개수 계산
gross_pnl = price_diff * coins
```

### **4. 수수료 계산**

```python
# Before (잘못된 계산)
fee = price * quantity * fee_rate  # quantity가 USDT면 큰 오류!

# After (올바른 계산)
fee = quantity * fee_rate  # quantity가 이미 USDT 금액
```

---

## 🎯 **이점**

1. ✅ **단일 진실의 원천** (Single Source of Truth)
   - 포지션 사이징 로직이 1곳에만 존재
   
2. ✅ **유지보수 용이**
   - 수정 시 1곳만 수정
   
3. ✅ **일관성 보장**
   - 백테스트 = Paper = Live 동일한 로직
   
4. ✅ **버그 감소**
   - 중복 코드 제거

---

## 📋 **체크리스트**

- [x] backtest_engine에서 execution 모듈 import
- [x] PositionSizer 사용
- [x] PnL 계산 수정
- [x] 수수료 계산 수정
- [ ] RiskManager 통합
- [ ] Trade 클래스 공통화
- [ ] 테스트 및 검증

---

## ⚠️ **주의사항**

### **quantity 단위 통일**

execution 모듈에서:
```python
# position_sizer.py
return quantity  # USDT 금액 또는 코인 개수?
```

**확인 필요**: execution 모듈이 quantity를 어떤 단위로 반환하는지 확인하고 통일!

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-10-19
