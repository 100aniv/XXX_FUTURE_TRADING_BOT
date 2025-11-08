# PR12: 포트폴리오 매니저 리팩토링 및 개선

## 🔍 **현상 분석**

### **문제점**

1. **PnL 관리 분산**
   - `RiskManager.current_daily_loss`: 일일 PnL 추적
   - `PortfolioManager.equity`: 총 자산만 추적
   - **문제**: PnL은 포트폴리오 수준 개념인데 리스크 매니저에 있음

2. **Equity 업데이트 중복**
   ```python
   # engine.py L554-558
   new_equity = portfolio.get_equity() + pnl
   portfolio.update_equity(new_equity)
   sizer.update_equity(new_equity)
   risk.update_equity(new_equity)
   ```
   **문제**: 3개 모듈이 동일한 equity를 각자 관리

3. **Daily PnL 리셋 미구현**
   ```python
   # risk_manager.py L391-394
   def reset_daily(self):
       """일일 리셋 (자정)"""
       self.current_daily_loss = 0.0
       self.consecutive_losses = 0
   ```
   **문제**: 메서드는 있지만 호출되지 않음

4. **Paper/Live 자산 조회 불일치**
   - **Paper**: 고정값 사용 (`config.yml`)
   - **Live**: Binance API 조회 (미구현)
   - **문제**: Live 모드에서 실제 자산 동기화 안 됨

5. **역할 불명확**
   - `PortfolioManager`: 포지션 exposure, 전략 예산
   - `RiskManager`: 가드 + PnL 추적 + equity 관리
   - **문제**: 경계가 불명확하고 책임이 섞임

---

## 🎯 **개선 목표**

### **1. 명확한 역할 분리**

```
PortfolioManager (포트폴리오 수준 관리)
├─ 자산 관리 (equity, balance, PnL)
├─ 포지션 관리 (exposure, 상관관계)
├─ 전략별 예산 배분
└─ Paper/Live 자산 동기화

RiskManager (리스크 가드만)
├─ Drawdown Guard
├─ Slippage Guard
├─ Extreme Loss Guard
└─ Daily Loss Limit
```

### **2. PnL 관리 통합**

- `PortfolioManager`로 이동:
  - `daily_pnl`: 일일 누적 손익
  - `total_pnl`: 전체 누적 손익
  - `realized_pnl`: 실현 손익
  - `unrealized_pnl`: 미실현 손익
  - `reset_daily()`: 자정 리셋

### **3. Equity 단일 소스**

- `PortfolioManager`만 equity 관리
- 다른 모듈은 `portfolio.get_equity()` 호출

### **4. Paper/Live 자산 조회 파리티**

```python
# LiveBroker (Binance API)
def get_account_balance(self) -> dict:
    """실시간 자산 조회"""
    return self.client.futures_account_balance()

def sync_equity_with_exchange(self) -> float:
    """거래소 자산과 동기화"""
    balance = self.get_account_balance()
    equity = balance['totalWalletBalance']
    return equity

# PaperBroker (가상)
def get_account_balance(self) -> dict:
    """가상 자산 조회 (로컬)"""
    return {'totalWalletBalance': self.equity}

def sync_equity_with_exchange(self) -> float:
    """가상 자산 반환 (동기화 불필요)"""
    return self.equity
```

---

## 📋 **개선 계획**

### **Phase 1: PortfolioManager 리팩토링**

#### **1.1 PnL 관리 통합**

```python
# execution/portfolio_manager.py

class PortfolioManager:
    def __init__(self, config: Dict):
        # 기존 코드...
        self.equity = config['capital']['initial']
        
        # ⭐ 신규: PnL 추적
        self.initial_equity = self.equity
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # 일일 리셋
        self.last_reset_date = datetime.now().date()
    
    def update_pnl(self, pnl: float, realized: bool = True):
        """PnL 업데이트"""
        if realized:
            self.realized_pnl += pnl
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            # Equity 업데이트
            self.equity += pnl
            logger.info(f"💰 PnL 업데이트: ${pnl:+,.2f}, Daily: ${self.daily_pnl:,.2f}, Total: ${self.total_pnl:,.2f}")
        else:
            self.unrealized_pnl = pnl
    
    def get_daily_pnl(self) -> float:
        """일일 누적 PnL 반환"""
        return self.daily_pnl
    
    def get_total_pnl(self) -> float:
        """전체 누적 PnL 반환"""
        return self.total_pnl
    
    def reset_daily(self):
        """일일 리셋 (자정)"""
        logger.info(f"📅 일일 PnL 리셋: ${self.daily_pnl:+,.2f} → $0.00")
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def check_and_reset_daily(self):
        """날짜 체크 및 자동 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.reset_daily()
```

#### **1.2 Equity 단일 소스**

```python
# execution/portfolio_manager.py

def update_equity(self, new_equity: float = None, pnl: float = None):
    """
    자본 업데이트 (단일 소스)
    
    Args:
        new_equity: 새로운 자본 (직접 설정)
        pnl: PnL (증감분)
    """
    if new_equity is not None:
        old_equity = self.equity
        self.equity = max(0.0, new_equity)
        logger.info(f"💰 Equity 설정: ${old_equity:,.0f} → ${new_equity:,.0f}")
    
    elif pnl is not None:
        self.update_pnl(pnl, realized=True)
    
    else:
        raise ValueError("new_equity or pnl must be provided")
```

#### **1.3 Paper/Live 자산 동기화**

```python
# execution/portfolio_manager.py

def sync_equity_with_broker(self, broker):
    """
    브로커와 자산 동기화 (Live 모드에서만 의미)
    
    Args:
        broker: PaperBroker 또는 LiveBroker
    """
    if hasattr(broker, 'sync_equity_with_exchange'):
        exchange_equity = broker.sync_equity_with_exchange()
        
        if abs(exchange_equity - self.equity) > 0.01:
            logger.warning(f"⚠️ 자산 불일치: Local=${self.equity:,.2f}, Exchange=${exchange_equity:,.2f}")
            self.equity = exchange_equity
            logger.info(f"✅ 자산 동기화: ${exchange_equity:,.2f}")
```

---

### **Phase 2: RiskManager 간소화**

#### **2.1 PnL 관련 제거**

```python
# execution/risk_manager.py

class RiskManager:
    def __init__(self, config: Dict, portfolio: PortfolioManager):
        # PnL 추적 제거
        # self.current_daily_loss = 0.0  # ← 제거
        # self.consecutive_losses = 0  # ← 제거
        
        # Portfolio 참조 추가
        self.portfolio = portfolio
        
        # 가드 설정만 유지
        self.max_drawdown_pct = config['risk']['max_drawdown_pct']
        self.max_slippage_pct = config['risk']['max_slippage_pct']
        self.extreme_loss_cutoff_pct = config['risk']['extreme_loss_cutoff_pct']
    
    def check_drawdown_guard(self, current_equity: float) -> bool:
        """Drawdown Guard (포트폴리오에서 equity 가져옴)"""
        initial = self.portfolio.initial_equity
        dd_pct = (current_equity - initial) / initial * 100
        
        if dd_pct < -self.max_drawdown_pct:
            logger.error(f"🚨 Drawdown Guard: {dd_pct:.2f}% < -{self.max_drawdown_pct:.2f}%")
            return False
        return True
    
    def check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 (포트폴리오에서 PnL 가져옴)"""
        daily_pnl = self.portfolio.get_daily_pnl()
        
        if self.daily_loss_limit and daily_pnl < -self.daily_loss_limit:
            logger.error(f"🚨 일일 손실 한도: ${daily_pnl:,.2f} < -${self.daily_loss_limit:,.2f}")
            return False
        return True
```

---

### **Phase 3: Engine 수정**

#### **3.1 PnL 업데이트 간소화**

```python
# execution/engine.py

# 기존 (중복)
new_equity = portfolio.get_equity() + pnl
portfolio.update_equity(new_equity)
sizer.update_equity(new_equity)
risk.update_equity(new_equity)

# 개선 (단일)
portfolio.update_equity(pnl=pnl)  # 포트폴리오만 업데이트
```

#### **3.2 일일 리셋 호출**

```python
# execution/engine.py (메인 루프 시작)

def run(config, mode='paper'):
    # ...
    
    # 포트폴리오 매니저 초기화
    portfolio = PortfolioManager(config)
    
    # 메인 루프
    while True:
        # 날짜 체크 및 자동 리셋
        portfolio.check_and_reset_daily()
        
        # ...
```

---

## 🔄 **Paper/Live 파리티**

### **자산 조회 파리티 보장**

| 항목 | Paper 모드 | Live 모드 | 파리티 |
|------|----------|-----------|--------|
| **Equity 관리** | PortfolioManager | PortfolioManager | ✅ 100% |
| **PnL 추적** | PortfolioManager | PortfolioManager | ✅ 100% |
| **자산 조회** | 로컬 (고정값) | Binance API | ✅ 로직 동일 |
| **동기화** | 불필요 | broker.sync_equity() | ✅ 메서드 동일 |
| **Daily 리셋** | check_and_reset_daily() | check_and_reset_daily() | ✅ 100% |

---

## 📋 **PR12 체크리스트 추가**

### **Phase 4: 포트폴리오 리팩토링 (신규)**

- [x] **⭐ PortfolioManager PnL 통합**
  - [x] `update_pnl()` 메서드 추가
  - [x] `get_daily_pnl()` 메서드 추가
  - [x] `get_total_pnl()` 메서드 추가
  - [x] `reset_daily()` 자동 호출 구현
  - [x] `check_and_reset_daily()` 메서드 추가

- [x] **⭐ 전략별 예산 관리**
  - [x] `config.yml`에 `portfolio.budget` 섹션 추가
  - [x] `strategy_allocation` 비율 설정 추가 (각 전략의 자산 사용 비율)
  - [x] `calculate_strategy_budget()` 메서드 구현 (동적 계산)
  - [x] `can_open_position()`에 전략 예산 검사 로직 추가

- [x] **⭐ RiskManager 간소화**
  - [x] PnL 관련 코드 제거
  - [x] Portfolio 참조로 대체
  - [x] 가드 로직만 유지

- [x] **⭐ Equity 단일 소스**
  - [x] PortfolioManager만 equity 관리
  - [x] PositionSizer equity 참조로 변경
  - [x] RiskManager equity 참조로 변경
  - [x] Engine 중복 코드 제거

- [x] **⭐ Paper/Live 자산 동기화**
  - [x] `LiveBroker.get_account_balance()` 구현
  - [x] `LiveBroker.sync_equity_with_exchange()` 구현
  - [x] `PaperBroker.get_account_balance()` 구현 (파리티)
  - [x] `PortfolioManager.sync_equity_with_broker()` 구현
  - [x] Engine에서 자동 동기화 호출 (Live 모드만)

---

## 🎯 **수용 기준**

### **리팩토링 수용 기준**
- [x] PnL 추적이 PortfolioManager로 통합됨
- [x] Equity 업데이트가 단일 소스로 관리됨
- [x] Daily PnL 리셋이 자정에 자동 실행됨
- [x] Paper/Live 자산 조회 로직이 동일함
- [x] RiskManager가 가드만 담당함
- [ ] 모든 테스트 통과 (pre-commit, coverage>85%)

### **Paper/Live 파리티 수용 기준**
- [x] PortfolioManager 로직 100% 동일
- [x] PnL 추적 로직 100% 동일
- [x] Daily 리셋 로직 100% 동일
- [x] 브로커 메서드 시그니처 100% 동일 (get_account_balance, sync_equity)
- [ ] Live 모드에서 Binance API 자산 조회 정상 작동 확인 필요
- [ ] Paper 모드에서 가상 자산 조회 정상 작동 확인 필요

---

## 📝 **관련 문서**

- `docs/PHASE6/PR12_MASTER_PLAN.md`: 메인 계획
- `docs/PHASE6/PR12_BINANCE_PARITY_CHECK.md`: API 파리티 검증
- `docs/PHASE6/PR10_PAPER_VS_LIVE_STRUCTURE.md`: Paper/Live 구조
- `docs/PHASE6/PR11_BINANCE_PARITY_CHECK.md`: PR11 파리티 검증

---

## 🚀 **다음 단계**

1. ✅ 현상 분석 완료
2. ✅ 개선 계획 수립
3. ✅ PortfolioManager 리팩토링
4. ✅ RiskManager 간소화
5. ✅ Engine 수정
6. ✅ Paper/Live 자산 동기화 구현
7. ✅ 포트폴리오 가드 구현 (전략 예산/상관관계)

### 전략별 예산 관리 (Strategy Budget Management)

#### 설정 방법

```yaml
# config.yml
portfolio:
  # 기타 포트폴리오 설정...
  
  # 전략별 예산 설정
  budget:
    default_allocation: 0.2    # 기본 배분 비율 (20%)
    strategy_allocation:       # 전략별 배분 비율
      ensemble_1_signals: 0.4  # 전체 자산의 40%까지 사용 가능
      ensemble_2_signals: 0.4  # 전체 자산의 40%까지 사용 가능
      ensemble_3_signals: 0.3  # 전체 자산의 30%까지 사용 가능
      scalping: 0.3            # 전체 자산의 30%까지 사용 가능
```

#### 동작 방식

1. **자산 할당 비율 계산**: 현재 자산(equity)에 비율을 곱하여 전략별 예산 계산
   - 예: 자산 $50,000 환경에서 ensemble_1_signals의 예산 = $50,000 × 0.4 = $20,000

2. **예산 사용 추적**: 현재 포지션들의 가치와 신규 포지션 가치를 합산하여 예산 초과 여부 검사

3. **유동적 예산 관리**: 자산(equity)이 변화되면 자동으로 전략별 예산도 동적 조정
   - 예산 = 현재 자산(equity) × 설정 비율

#### 구현 코드

```python
# execution/portfolio_manager.py
def calculate_strategy_budget(self, strategy_id: str) -> float:
    """⭐ PR12: 전략별 예산 한도 계산"""
    equity = self.equity  # 현재 자산
    
    # 전략별 예산 할당 비율 조회
    if strategy_id in self.strategy_budget:
        budget_pct = self.strategy_budget[strategy_id]
    else:
        # 기본 비율 사용
        budget_pct = self.default_budget_pct
        
    # 전략별 예산 = 자산 * 할당 비율
    budget = equity * budget_pct
    
    logger.info(f"💰 전략 예산: {strategy_id} = ${budget:,.2f} ({budget_pct*100:.1f}%)")
    return budget
```

#### 이점

1. **지나친 노출 방지**: 한 전략의 실패가 전체 포트폴리오에 미치는 영향 최소화
2. **리스크 분산**: 전체 자산을 다양한 전략에 고루 분포
3. **동적 조정**: 자산 변경에 따른 자동 조정 (PnL 증가 시 예산도 증가, PnL 감소 시 예산도 감소)

8. [ ] 테스트 및 검증
9. [x] PR12_MASTER_PLAN.md 업데이트

---

**🎯 목표: 명확한 역할 분리 + Paper/Live 파리티 100% 보장**
