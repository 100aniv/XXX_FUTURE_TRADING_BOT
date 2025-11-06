# 페이퍼 vs 라이브 모드 구조 비교

## 핵심 질문 답변

### Q1: 페이퍼 모드에서 Binance API 사용 가능한가?

**A: 사용 안 함 (못함)**

**이유:**
- 페이퍼 모드 = **가상 거래** (실제 돈 없음)
- Binance API 호출 = **실제 주문** (실제 돈 필요)
- 페이퍼에서 API 호출하면 **실제 거래 발생** → 위험!

**현재 구조:**
```python
# execution/adapters/brokers.py

class PaperBroker:
    """페이퍼 트레이딩 브로커"""
    def execute(self, decision: dict, qty: float) -> dict:
        # ✅ Binance API 호출 안 함
        # ✅ 가상 실행만 (DB만 기록)
        filled_price = price * (1 + slippage)
        return {'success': True, 'filled_price': filled_price}

class LiveBroker:
    """실거래 브로커"""
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret)  # ← Binance 연결
    
    def execute(self, decision: dict, qty: float) -> dict:
        # 🔴 실제 Binance API 호출
        order = self.client.futures_create_order(...)
        return order
```

---

### Q2: 페이퍼와 라이브의 구조가 달라지는가?

**A: 브로커 계층에서만 다름, 상위 로직은 동일**

**아키텍처:**
```
Engine (공통)
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

**다른 부분:**
- `PaperBroker`: 
  - 가상 주문 실행
  - 슬리피지 시뮬레이션
  - DB만 기록
  
- `LiveBroker`:
  - 실제 Binance API 호출
  - 실제 주문 체결
  - Binance 서버 응답 처리

---

### Q3: TP/SL API는 어떻게 처리되는가?

**방안 1: 페이퍼는 기존 방식 유지, 라이브만 API 사용 (권장) ⭐**

```python
# engine.py (공통 로직)
should_action, partial_qty, reason = tracker.check_tpsl_with_partial(
    position, current_price, atr
)

if should_action:
    if mode == 'live':
        # 🔴 라이브: Binance API 사용
        # TP/SL은 이미 Binance에 등록되어 있음
        # 여기선 부분 청산만 처리
        broker.close_position(position_id, partial_qty)
    else:
        # ✅ 페이퍼: Python 체크 (기존 방식)
        broker.close_position(position_id, partial_qty)
```

**진입 시:**
```python
# LiveBroker.execute() 확장
def execute(self, decision, qty):
    # 1. 포지션 진입
    order = self.client.futures_create_order(
        symbol=symbol,
        side='BUY',
        type='MARKET',
        quantity=qty,
        positionSide='BOTH'  # ← One-Way Mode
    )
    
    # 2. TP/SL 주문 자동 등록 (Binance 서버에)
    self.client.futures_create_order(
        symbol=symbol,
        side='SELL',
        type='STOP_MARKET',
        stopPrice=sl_price,
        closePosition=True  # ← 전체 청산
    )
    
    self.client.futures_create_order(
        symbol=symbol,
        side='SELL',
        type='TAKE_PROFIT_MARKET',
        stopPrice=tp_price,
        quantity=qty * 0.3  # ← TP1 30%
    )
    
    return order
```

**장점:**
- 페이퍼: 기존 로직 유지 (안정적)
- 라이브: Binance가 24/7 자동 청산
- 봇 중단해도 TP/SL 작동 ✅

---

**방안 2: 페이퍼도 TP/SL 시뮬레이션**

```python
# PaperBroker
def execute(self, decision, qty):
    # 1. 가상 진입
    order = self._simulate_order(...)
    
    # 2. TP/SL 가상 등록 (DB에만 저장)
    self.virtual_tpsl_orders.append({
        'symbol': symbol,
        'type': 'STOP_MARKET',
        'stopPrice': sl_price
    })
    
    return order

# engine.py에서 매 캔들마다 체크
for vorder in broker.virtual_tpsl_orders:
    if current_price >= vorder['stopPrice']:
        # 가상 TP/SL 발동
        broker.close_position(...)
```

**단점:**
- 복잡도 증가
- 페이퍼 평가에 큰 이득 없음

---

## TP/SL 전략 (최종 권장)

### 페이퍼 모드
- **기존 방식 유지** ✅
- Python 코드로 매 캔들마다 TP/SL 체크
- 가상 실행이므로 문제없음

### 라이브 모드
- **Binance TP/SL API 사용** ✅
- 진입 시 TP/SL 주문 자동 등록
- Binance 서버가 24/7 자동 청산
- 트레일링: 1분마다 Modify Order API로 SL 가격 업데이트

**이유:**
1. 페이퍼는 테스트 목적 → 기존 로직으로 충분
2. 라이브는 안전이 최우선 → Binance API 필수
3. 구조 분리로 복잡도 최소화

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

| 항목 | 페이퍼 모드 | 라이브 모드 |
|------|-----------|-----------|
| **진입 주문** | 가상 실행 (DB만) | Binance API |
| **TP/SL 등록** | 없음 (Python 체크) | Binance API (STOP_MARKET, TAKE_PROFIT_MARKET) |
| **TP/SL 체크** | Python (1분마다) | Binance 서버 (자동) |
| **트레일링 스톱** | Python (1분마다) | Modify Order API (1분마다) |
| **자산 조회** | 고정값 (config) | Binance API (GET /fapi/v2/balance) |
| **포지션 조회** | DB | Binance API (GET /fapi/v2/positionRisk) |

**구조:**
- 상위 로직 (engine, portfolio, risk): **공통**
- 브로커 (PaperBroker vs LiveBroker): **분리**
- 복잡도: **최소화**
