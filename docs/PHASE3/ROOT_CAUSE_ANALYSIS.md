# 근본 원인 분석 (Root Cause Analysis)

**작성일**: 2025-10-23  
**분석자**: Cascade AI  
**상태**: ✅ 확정

---

## 📊 증상 (Symptoms)

### 백테스트 결과 (10개 실험)

| 지표 | 목표 | 실제 | 차이 |
|------|------|------|------|
| 승률 | ≥50% | 24.8~25.8% | -50% |
| PF | ≥1.3 | 0.41~0.46 | -65% |
| MDD | ≤-20% | -848% ~ -1,568% | **78배 초과** |
| 거래수 | 적절 | 180~8,797건 | 과다 |

### 조정 시도 (모두 실패)

1. ✅ Exits 조정 (stop.k, trailing, TP 분할) → 효과 없음
2. ✅ Entries 조정 (volume_spike, min_rr) → 효과 없음
3. ✅ 조건 완화 (RSI 30→40, AND→OR) → 거래 49배 증가, MDD 악화
4. ✅ 데이터 기간 변경 (3개월→1년) → 동일 결과
5. ✅ 필터 비활성화 (MTF, volume) → 효과 없음

---

## 🔍 근본 원인 (Root Cause)

### **자본 업데이트 누락 (Compounding Capital Management Missing)**

**위치**: `execution/engine.py` Line 158-173

```python
# ❌ 현재 코드
for pos_id, position, reason in positions_to_close:
    pnl = calculate_pnl(position, current_price)
    close_trade_in_db(pos_id, current_price, pnl, reason, ts)
    
    risk.update_daily_pnl(pnl)  # ← 일일 PnL만 추적
    # ❌ equity 업데이트 없음!
    
    portfolio.remove_position(symbol=position['symbol'], position_id=pos_id)
    risk.remove_position(position['symbol'], position_value)
```

**결과**:
1. **자본 고정**: 초기 $10,000으로 고정, 손실 반영 안 됨
2. **포지션 사이즈 불변**: 자본 소진 후에도 동일 크기로 거래
3. **MDD 폭발**: 복리 효과 없음 → 연쇄 손실 가속
4. **리스크 관리 실패**: RPT 1% 계산이 항상 $10,000 기준

### 데이터 흐름 분석

```
[거래 종료]
   ↓
PnL 계산 ($-50)
   ↓
risk.update_daily_pnl()  ← 일일 손실만 추적
   ↓
❌ equity 업데이트 없음!
   ↓
[다음 거래]
   ↓
sizer.calculate()
   ↓
self.equity = $10,000  ← 여전히 초기값!
   ↓
position_size = $10,000 × 1% = $100  ← 고정!
```

**실제 상황**:
```
거래 1: $10,000 → $9,950 (PnL -$50)
거래 2: $10,000 → $9,900 (❌ 여전히 $10,000 기준!)
...
거래 100: $10,000 → $0 (자본 소진)
거래 101: $10,000 → -$100 (❌ 마이너스 자본에도 거래!)
...
거래 8,797: MDD -1,568% (❌ 폭발!)
```

---

## 🎯 해결 방법 (Solution)

### 1. PositionSizer에 update_equity() 추가

```python
class PositionSizer:
    def update_equity(self, new_equity: float):
        """자본 업데이트 (PnL 반영)"""
        old_equity = self.equity
        self.equity = max(0.0, new_equity)  # 음수 방지
        logger.info(f"💰 Equity 업데이트: ${old_equity:,.2f} → ${self.equity:,.2f}")
```

### 2. RiskManager에 update_equity() 추가

```python
class RiskManager:
    def update_equity(self, new_equity: float):
        """자본 업데이트 + 한도 재계산"""
        self.equity = max(0.0, new_equity)
        self.daily_loss_limit = self.daily_loss_limit_pct * self.equity
        logger.info(f"💰 Equity 업데이트: ${self.equity:,.2f}, DDL: ${self.daily_loss_limit:.2f}")
```

### 3. engine.py 수정

```python
# ✅ 수정된 코드
for pos_id, position, reason in positions_to_close:
    pnl = calculate_pnl(position, current_price)
    close_trade_in_db(pos_id, current_price, pnl, reason, ts)
    
    # ⭐ 자본 업데이트
    new_equity = portfolio.get_equity() + pnl
    portfolio.update_equity(new_equity)
    sizer.update_equity(new_equity)
    risk.update_equity(new_equity)
    
    risk.update_daily_pnl(pnl)
    portfolio.remove_position(symbol=position['symbol'], position_id=pos_id)
    risk.remove_position(position['symbol'], position_value)
```

---

## 📈 예상 효과

### Before (현재)
```
거래 100건 후:
- 실제 자본: $5,000 (50% 손실)
- 시스템 인식: $10,000 (초기값)
- 포지션 사이즈: $10,000 × 1% = $100 (과대)
- MDD: -1,568% (폭발)
```

### After (수정 후)
```
거래 100건 후:
- 실제 자본: $5,000 (50% 손실)
- 시스템 인식: $5,000 (정확)
- 포지션 사이즈: $5,000 × 1% = $50 (적정)
- MDD: 예상 -20% 이내 (정상)
```

---

## 🔗 관련 문서

- **TEST_SCENARIO.md**: Line 69-71 "SL/리스크 먼저 고정"
- **TUNING_BENCHMARK.md**: Line 69 "1트레이드 리스크: 0.25% ~ 0.75%"
- **execution/position_sizer.py**: Line 29-54 (PositionSizer 초기화)
- **execution/risk_manager.py**: Line 34-69 (RiskManager 초기화)
- **execution/portfolio_manager.py**: Line 247 (update_equity 이미 존재)

---

## ✅ 다음 단계

1. PositionSizer.update_equity() 구현
2. RiskManager.update_equity() 구현  
3. engine.py 거래 종료 로직 수정
4. EXP-A4-01 백테스트 실행
5. TEST_CHECKLIST.md 업데이트

---

**Last Updated**: 2025-10-23  
**Status**: ✅ 분석 완료, 수정 진행 중
