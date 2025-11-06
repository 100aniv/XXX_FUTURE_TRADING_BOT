# 페이퍼 vs 라이브 모드 구조 비교

## 🎯 핵심 원칙

### ⭐ 로직은 100% 동일, 실행만 다름!

```
┌─────────────────────────────────────┐
│  동일한 로직 (공통)                    │
│  - TP/SL 계산                        │
│  - 진입/청산 기준                     │
│  - 리스크 관리                        │
│  - 포지션 추적                        │
└─────────────────────────────────────┘
              ↓
┌─────────────┴─────────────┐
│                           │
▼                           ▼
PaperBroker             LiveBroker
(가상 실행)              (실제 API)
```

**페이퍼 테스트가 의미있으려면:**
- ✅ 진입/청산 로직 동일
- ✅ TP/SL 계산 동일
- ✅ 리스크 체크 동일
- ✅ 포지션 추적 동일
- ⚠️ **실행 방식만 다름** (가상 vs 실제)

---

## Q1: 페이퍼 모드에서 Binance API 사용 가능한가?

**A: 사용 안 함 (못함)**

**이유:**
- 페이퍼 모드 = **가상 거래** (실제 돈 없음)
- Binance API 호출 = **실제 주문** (실제 돈 필요)
- 페이퍼에서 API 호출하면 **실제 거래 발생** → 위험!

**하지만 로직은 동일하게 시뮬레이션:**
```python
# execution/adapters/brokers.py

class PaperBroker:
    """페이퍼 트레이딩 브로커 - 가상 실행"""
    
    def execute(self, decision: dict, qty: float) -> dict:
        """가상 진입 (Binance API 호출 안 함)"""
        filled_price = price * (1 + slippage)
        return {'success': True, 'filled_price': filled_price}
    
    def create_tpsl_orders(self, position, tp_price, sl_price):
        """TP/SL 가상 등록 (Binance와 동일한 로직, 실행만 가상)"""
        # Binance API 호출 안 함, DB에만 저장
        self.virtual_tpsl_orders.append({
            'symbol': position['symbol'],
            'tp_price': tp_price,
            'sl_price': sl_price,
            'type': 'STOP_MARKET'  # ← Binance와 동일한 타입
        })
        return {'success': True}

class LiveBroker:
    """실거래 브로커 - 실제 API"""
    
    def execute(self, decision: dict, qty: float) -> dict:
        """실제 진입 (Binance API 호출)"""
        order = self.client.futures_create_order(...)
        return order
    
    def create_tpsl_orders(self, position, tp_price, sl_price):
        """TP/SL 실제 등록 (Binance API)"""
        # 실제 Binance API 호출
        self.client.futures_create_order(
            symbol=position['symbol'],
            side='SELL',
            type='STOP_MARKET',
            stopPrice=sl_price,
            closePosition=True
        )
        return {'success': True}
```

**핵심:**
- 로직: 동일 (`create_tpsl_orders` 메서드 시그니처 동일)
- 실행: 다름 (가상 vs 실제 API)

---

## Q2: 페이퍼와 라이브의 구조가 달라지는가?

**A: 브로커 계층에서만 다름, 상위 로직은 100% 동일** ⭐

**아키텍처:**
```
Engine (공통) ← 동일한 로직
  ↓
PortfolioManager (공통)
  ↓
RiskManager (공통)
  ↓
Broker (모드별 분기)
  ├─ PaperBroker  → 가상 실행
  └─ LiveBroker   → Binance API
```

**동일한 부분:**
- `engine.py`: 메인 루프, 신호 처리, TP/SL 체크
- `portfolio_manager.py`: 포지션 관리
- `risk_manager.py`: 리스크 검증
- `position_tracker.py`: TP/SL 계산

**다른 부분 (실행만):**
- `PaperBroker`: 
  - 가상 주문 실행
  - 슬리피지 시뮬레이션
  - DB만 기록
  - **동일한 TP/SL 로직 시뮬레이션** ⭐
  
- `LiveBroker`:
  - 실제 Binance API 호출
  - 실제 주문 체결
  - Binance 서버 응답 처리
  - **동일한 TP/SL 로직 실제 실행** ⭐

---

## Q3: TP/SL API는 어떻게 처리되는가?

**✅ 최종 방안: 페이퍼/라이브 동일한 로직, 실행만 다름** ⭐

```python
# engine.py (공통 로직 - 모드 무관) ⭐
should_action, partial_qty, reason = tracker.check_tpsl_with_partial(
    position, current_price, atr
)

if should_action:
    # 페이퍼/라이브 구분 없이 동일한 호출 ✅
    broker.close_position(position_id, partial_qty, reason)
    
# 브로커가 알아서 처리:
# - PaperBroker: 가상 청산
# - LiveBroker: 실제 API 청산
```

**진입 시 (Broker 내부 구현):**
```python
# LiveBroker.create_tpsl_orders()
def create_tpsl_orders(self, position, tp_prices, sl_price):
    """TP/SL 주문 등록 (실제 Binance API)"""
    # Binance 서버에 조건부 주문 등록
    self.client.futures_create_order(
        symbol=position['symbol'],
        side='SELL',
        type='STOP_MARKET',
        stopPrice=sl_price,
        closePosition=True
    )
    
    self.client.futures_create_order(
        symbol=position['symbol'],
        side='SELL',
        type='TAKE_PROFIT_MARKET',
        stopPrice=tp_prices[0],
        quantity=position['qty'] * 0.3
    )
    return {'success': True}

# PaperBroker.create_tpsl_orders()
def create_tpsl_orders(self, position, tp_prices, sl_price):
    """TP/SL 주문 등록 (가상, Binance와 동일한 로직)"""
    # DB에 가상 주문 저장 (Binance와 동일한 구조)
    self.virtual_tpsl_orders.append({
        'symbol': position['symbol'],
        'type': 'STOP_MARKET',
        'stopPrice': sl_price,
        'closePosition': True
    })
    
    self.virtual_tpsl_orders.append({
        'symbol': position['symbol'],
        'type': 'TAKE_PROFIT_MARKET',
        'stopPrice': tp_prices[0],
        'quantity': position['qty'] * 0.3
    })
    return {'success': True}

# 핵심: 메서드 시그니처 동일, 로직 동일, 실행만 다름! ⭐
```

**장점:**
- ✅ 페이퍼/라이브 동일한 로직 → 테스트 신뢰도 100%
- ✅ 라이브: Binance가 24/7 자동 청산
- ✅ 페이퍼: 동일한 조건으로 가상 시뮬레이션
- ✅ engine.py는 모드 무관 (깔끔한 구조)


---

## TP/SL 전략 (최종 확정) ⭐

### 통합 방식 (페이퍼/라이브 동일)

**1. 진입 시:**
```python
# engine.py (모드 무관)
broker.execute(decision, qty)  # 진입
broker.create_tpsl_orders(position, tp_prices, sl_price)  # TP/SL 등록
```

**2. TP/SL 체크 (매 캔들):**
```python
# engine.py (모드 무관)
should_close, qty, reason = tracker.check_tpsl(position, price)
if should_close:
    broker.close_position(position_id, qty, reason)
```

**3. 트레일링 스톱:**
```python
# engine.py (모드 무관)
if should_trail:
    broker.update_sl_price(position_id, new_sl_price)
```

**브로커별 실행:**
- **PaperBroker**: 가상 주문 관리, DB 업데이트
- **LiveBroker**: Binance API 호출

**장점:**
1. ✅ 로직 100% 동일 → 페이퍼 테스트 신뢰도 극대화
2. ✅ engine.py는 모드 무관 → 코드 간결
3. ✅ 라이브 안전성: Binance 24/7 자동 청산 + 봇 이중 체크
4. ✅ 페이퍼 정확성: 라이브와 동일한 조건 시뮬레이션

---

## PR10 범위 재확인

### 포트폴리오 API (자산 조회)

**라이브 모드에서만 필요:**
```python
# LiveBroker에 추가
def get_account_balance(self):
    """실시간 자산 조회 (라이브만)"""
    balance = self.client.futures_account_balance()
    return balance

def get_positions(self):
    """실시간 포지션 조회 (라이브만)"""
    positions = self.client.futures_position_information()
    return positions
```

**페이퍼 모드:**
- 고정값 사용 (`config.yml`: `capital.initial: 50000`)
- DB에서 PnL 계산하여 equity 업데이트

**PR10 범위:**
- ✅ LiveBroker에 메서드 추가 (준비)
- ❌ 실제 호출은 라이브 모드에서만
- ✅ 페이퍼는 기존 방식 유지

---

## 결론

| 항목 | 페이퍼 모드 | 라이브 모드 | 로직 동일? |
|------|-----------|-----------|-----------|
| **진입 주문** | 가상 실행 (DB만) | Binance API | ✅ 100% |
| **TP/SL 등록** | 가상 등록 (DB) | Binance API | ✅ 100% |
| **TP/SL 체크** | tracker.check_tpsl() | tracker.check_tpsl() | ✅ 100% |
| **트레일링 스톱** | broker.update_sl_price() | broker.update_sl_price() | ✅ 100% |
| **자산 조회** | 고정값 (config) | Binance API | ⚠️ 다름 (필요 시 동기화) |
| **포지션 조회** | DB | Binance API + DB | ⚠️ 다름 (라이브는 이중 체크) |

**핵심:**
- 상위 로직 (engine, portfolio, risk): **100% 동일** ⭐
- TP/SL 계산/체크: **100% 동일** ⭐
- 브로커 메서드 시그니처: **100% 동일** ⭐
- 실행 방식만: **다름** (가상 vs 실제 API)
- 페이퍼 테스트: **완전히 신뢰 가능** ✅
