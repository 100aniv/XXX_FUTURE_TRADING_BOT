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

**✅ 최종 방안(Option C): 서버측 SL + 로컬 TP/트레일링** ⭐

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
# - LiveBroker: 실제 API 청산 (reduceOnly/closePosition)
```

**진입 직후 (Broker 내부 구현): SL만 서버 등록**
```python
# LiveBroker.create_sl_order() - ✅ 2025-11-07 업데이트
def create_sl_order(self, position, sl_price, 
                    working_type='CONTRACT_PRICE',
                    price_protect='TRUE'):
    """SL 주문 등록 (Binance API, STOP_MARKET + closePosition)"""
    self.client.futures_create_order(
        symbol=position['symbol'],
        side=('SELL' if position['side']=='LONG' else 'BUY'),
        type='STOP_MARKET',
        stopPrice=sl_price,
        closePosition=True,
        positionSide='BOTH',
        workingType=working_type,      # ⭐ 추가: CONTRACT_PRICE (실시간)
        priceProtect=price_protect     # ⭐ 추가: Flash Crash/Pump 보호
    )
    return {'success': True}

# PaperBroker.create_sl_order() - ✅ 2025-11-07 업데이트 (파리티)
def create_sl_order(self, position, sl_price,
                    working_type='CONTRACT_PRICE',
                    price_protect='TRUE'):
    """SL 가상 등록 (시뮬레이션만, DB/메모리 저장)"""
    self.virtual_sl_orders[position['id']] = {
        'symbol': position['symbol'],
        'stopPrice': sl_price,
        'type': 'STOP_MARKET',
        'closePosition': True,
        'workingType': working_type,    # ⭐ 파리티 (사용 안 함)
        'priceProtect': price_protect   # ⭐ 파리티 (사용 안 함)
    }
    return {'success': True}

# 핵심: TP는 서버 미등록, PositionTracker가 부분청산을 트리거하고 broker.close_position으로 실행 ⭐
# 극단 손실 방지: PositionTracker.check_tpsl_with_partial() 내부에서 PNL -50% cutoff ⭐
```

**장점:**
- ✅ 페이퍼/라이브 동일한 로직 → 테스트 신뢰도 100%
- ✅ 라이브: Binance가 24/7 자동 청산
- ✅ 페이퍼: 동일한 조건으로 가상 시뮬레이션
- ✅ engine.py는 모드 무관 (깔끔한 구조)


---

## TP/SL 전략 (최종 확정: Option C) ⭐

### 통합 방식 (페이퍼/라이브 동일)

**1. 진입 시:**
```python
# engine.py (모드 무관)
broker.execute(decision, qty)        # 진입
broker.create_sl_order(position, sl_price)  # SL만 서버 등록
```

**2. TP/SL 체크 (매 캔들):**
```python
# engine.py (모드 무관)
should_action, qty, reason = tracker.check_tpsl_with_partial(position, price, atr)
if should_action:
    broker.close_position(position_id, qty, reason)  # 부분/전체 청산
```

**3. 트레일링 스톱:**
```python
# engine.py (모드 무관)
# TP2 이후 tracker가 새 SL을 계산하면 브로커에 업데이트 지시
if tracker_updated_sl:
    broker.update_sl_price(position_id, symbol, new_sl_price)  # 라이브: cancel&replace 또는 modify
```

**브로커별 실행:**
- **PaperBroker**: SL/TP 가상 관리, DB/메모리 업데이트
- **LiveBroker**: SL 서버등록(Stop-Market closePosition), TP는 로컬 신호에 따라 시장가 reduceOnly 청산

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
| **TP/SL 등록** | 가상 등록 (DB) | Binance API (SL만) | ✅ 100% |
| **TP/SL 체크** | tracker.check_tpsl() | tracker.check_tpsl() | ✅ 100% |
| **극단 손실 방지** | tracker (-50% cutoff) | tracker (-50% cutoff) | ✅ 100% |
| **One-Way Mode** | engine.py 강제 청산 | engine.py 강제 청산 | ✅ 100% |
| **workingType** | 파라미터 무의미 | CONTRACT_PRICE | ⚠️ 라이브만 |
| **priceProtect** | 파라미터 무의미 | TRUE | ⚠️ 라이브만 |
| **트레일링 스톱** | broker.update_sl_price() | broker.update_sl_price() | ✅ 100% |
| **자산 조회** | 고정값 (config) | Binance API | ⚠️ 다름 (필요 시 동기화) |
| **포지션 조회** | DB | Binance API + DB | ⚠️ 다름 (라이브는 이중 체크) |

**핵심:**
- 상위 로직 (engine, portfolio, risk): **100% 동일** ⭐
- TP/SL 계산/체크: **100% 동일** ⭐
- 극단 손실 방지: **100% 동일** ⭐ (position_tracker.py L198-207)
- One-Way Mode 강제: **100% 동일** ⭐ (engine.py L1043-1081)
- 브로커 메서드 시그니처: **100% 동일** ⭐
- 실행 방식만: **다름** (가상 vs 실제 API)
- Binance API 파라미터 (workingType, priceProtect): **라이브만 의미있음** ⚠️
- 페이퍼 테스트: **완전히 신뢰 가능** ✅
