# 🎯 Trading Executor 설계 문서

**작성일**: 2025-10-16  
**버전**: v1.0  
**목적**: 매매 실행 모듈 설계 및 구현 가이드

---

## 📋 목차

1. [현재 상황 분석](#현재-상황-분석)
2. [설계 목표](#설계-목표)
3. [모듈 구조](#모듈-구조)
4. [Paper vs Live Trading](#paper-vs-live-trading)
5. [재사용 가능한 기존 코드](#재사용-가능한-기존-코드)
6. [신규 구현 필요 기능](#신규-구현-필요-기능)
7. [구현 순서](#구현-순서)
8. [API 설계](#api-설계)

---

## 📊 현재 상황 분석

### 전체 시스템 구조

```
┌──────────────────────────────────────────────┐
│  6개 Signal Bots (항상 실행)                  │
│  신호만 생성, 매매 안 함                      │
│  - TREND, REVERSION, BREAKOUT               │
│  - SCALPING, DAYTRADE, SWING                │
│  → monitoring.signals 저장                  │
└─────────────┬────────────────────────────────┘
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
┌───────────┐    ┌─────────────────────────────────┐
│ Ensemble  │    │  Trading Bot (사용자 선택!) ⭐   │
│ (통합)    │    │  매매 실행                       │
│ ↓         │    │                                 │
│decisions  │    │  사용자가 7개 중 1개 선택:       │
└────┬──────┘    │  ├─ ensemble (기본 추천) ✅      │
     │           │  ├─ trend (TREND만)             │
     │           │  ├─ reversion (REVERSION만)     │
     │           │  ├─ breakout (BREAKOUT만)       │
     │           │  ├─ scalping (SCALPING만)       │
     │           │  ├─ daytrade (DAYTRADE만)       │
     └───────────→  └─ swing (SWING만)             │
                 │                                 │
                 │  * 여러 Trading Bot 동시 실행 가능│
                 └─────────────────────────────────┘
```

**핵심:**
- Signal Bots: 6개 항상 실행 (신호 생성만)
- Trading Bot: **사용자가 전략 선택**
- 기본: ensemble (6개 통합)
- 선택: 개별 전략 (단일 전략만)
- 동시: 여러 Trading Bot으로 포트폴리오 구성 가능

### 기존 봇의 역할

**Signal Bots (6개)**
- ✅ WebSocket으로 실시간 데이터 수신
- ✅ 지표 계산 및 신호 생성
- ✅ DB 저장 (monitoring.signals)
- ✅ Paper Trading (가상 포지션 추적)

**Ensemble Bot (1개)**
- ✅ 6개 신호 통합 (항상 모두 사용)
- ✅ 가중치 합산 방식
  - 각 전략이 LONG/SHORT/FLAT 신호
  - 같은 방향끼리 가중치 * 신뢰도 합산
  - 최종 점수로 LONG/SHORT 결정
- ✅ 의사결정 저장 (trading.decisions)

**예시: Ensemble 작동**
```
입력 (6개 신호):
- TREND: LONG (가중치 2.5, 신뢰도 0.8) → 기여 2.0
- REVERSION: FLAT → 기여 0
- BREAKOUT: LONG (가중치 2.2, 신뢰도 0.7) → 기여 1.54
- SCALPING: SHORT (가중치 1.8, 신뢰도 0.6) → 기여 1.08
- DAYTRADE: LONG (가중치 2.0, 신뢰도 0.75) → 기여 1.5
- SWING: FLAT → 기여 0

계산:
LONG 점수 = 2.0 + 1.54 + 1.5 = 5.04
SHORT 점수 = 1.08

최종 결정: LONG (ensemble이 통합한 결정)
```

**Trading Bot (신규 구현 필요!) ⭐**
- ⏳ 전략 선택 (7개 중 1개)
- ⏳ 실제 주문 실행
- ⏳ 포지션 관리
- ⏳ 3가지 모드 (BACKTEST, PAPER, LIVE)

---

## 🎯 설계 목표

### 1. **전략 선택 시스템**
- 7가지 전략 중 선택 실행
- 기본: ensemble (6개 통합)
- 개별: trend, reversion, breakout, scalping, daytrade, swing
- 환경변수로 선택: `STRATEGY_SELECTOR=ensemble`

### 2. **3가지 매매 모드**
- BACKTEST: 과거 데이터로 전략 검증
- PAPER: 실시간 가상 매매
- LIVE: 실제 주문 실행
- 환경변수로 전환: `TRADING_MODE=backtest|paper|live`

### 3. **기존 로직 재사용**
- 검증된 TP/SL 추적 로직 활용
- PnL 계산 로직 유지
- 리스크 관리 로직 재사용

### 4. **안전성 우선**
- 이중 주문 방지
- 포지션 한도 체크
- 일손실 한도 적용

### 5. **유연성 & 확장성**
- 단일 전략 or 앙상블 선택
- 동시에 여러 봇 실행 가능 (멀티 전략)
- 포트폴리오 분산 지원

---

## 🏗️ 모듈 구조

### Trading Bot의 역할

```
┌──────────────┐
│ Signal Bots  │  신호만 생성
│ (6개)        │  → monitoring.signals
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Ensemble Bot │  통합 의사결정
│ (1개)        │  → trading.decisions
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Trading Bot (매매 실행) ⭐ 신규              │
├─────────────────────────────────────────────┤
│  전략 선택에 따라 입력 소스 다름:            │
│                                             │
│  ensemble → trading.decisions 읽기          │
│  개별전략 → monitoring.signals 읽기         │
│  (strategy_id 필터링)                       │
│                                             │
│  🔄 Process: 주문 실행 + 포지션 관리        │
│  💾 Output: trading.trades 저장            │
└─────────────────────────────────────────────┘
```

### 모듈 분리 (굵직하게만)

```python
trading_executor.py      # 매매 실행 + 포지션 관리 (핵심)
├─ OrderExecutor        # 주문 실행
│  ├─ backtest_order()  # Backtest (과거 데이터)
│  ├─ paper_order()     # Paper (실시간 가상)
│  └─ live_order()      # Live (실제 주문)
│
├─ PositionManager      # 포지션 관리
│  ├─ track_position()  # 포지션 추적
│  ├─ check_tp_sl()     # TP/SL 확인
│  └─ close_position()  # 포지션 청산
│
└─ RiskManager          # 리스크 관리
   ├─ check_daily_loss() # 일손실 한도
   ├─ check_position_limit() # 포지션 한도
   └─ validate_order()  # 주문 검증
```

**나중에 리팩토링 시 추가 분리 가능:**
- `pnl_tracker.py`: PnL 계산 전담
- `reporter.py`: 보고서/모니터링
- `account_manager.py`: 잔고 관리

---

## 🔄 3가지 매매 모드

### 비교표

| 항목 | BACKTEST | PAPER | LIVE |
|------|----------|-------|------|
| **데이터** | 과거 (DB/CSV) | 실시간 (WebSocket) | 실시간 (WebSocket) |
| **속도** | 빠름 (초~분) | 실시간 | 실시간 |
| **주문 실행** | 가상 (즉시) | 가상 (메모리) | 실제 (Binance API) |
| **포지션 추적** | ✅ 동일 로직 | ✅ 동일 로직 | ✅ 동일 로직 |
| **TP/SL 확인** | 과거 데이터 | 1분봉 시뮬레이션 | 1분봉 + 실제 주문 |
| **PnL 계산** | 가상 | 가상 | 실제 거래 내역 |
| **슬리피지** | 설정값 (0.05%) | 무시 | 실제 발생 |
| **네트워크 지연** | 없음 | 없음 | 있음 |
| **목적** | 전략 검증 & 튜닝 | 실전 전 최종 검증 | 실제 매매 |
| **기간** | 수개월~수년 | 1-2주 | 지속적 |

### 모드 전환

```python
# .env 파일
TRADING_MODE=backtest  # or 'paper' or 'live'

# 코드
executor = TradingExecutor(mode=os.getenv('TRADING_MODE', 'backtest'))
```

### 권장 순서

```
1. BACKTEST (3개월 이상)
   ├─ 승률/RR/샤프 측정
   ├─ 파라미터 최적화
   └─ 전략 선택
   
2. PAPER (1-2주)
   ├─ 실시간 검증
   ├─ 슬리피지 확인
   └─ 안정성 테스트
   
3. LIVE (소액 시작)
   ├─ 첫 1주: 최소 금액
   ├─ 검증 후: 점진적 증액
   └─ 지속 모니터링
```

---

## 📦 재사용 가능한 기존 코드

### telegram_signal_bot.py에서 추출

#### 1. **유틸리티 함수** (라인 213-266)

```python
# 라인 221-244: 텔레그램 알림
def tg(text: str):
    """텔레그램 메시지 전송"""
    # → 재사용 ✅

# 라인 246-253: 가격 반올림
def round_tick(price: float, symbol: str) -> float:
    """거래소 tick size에 맞게 가격 반올림"""
    # → 재사용 ✅

# 라인 255-260: 포지션 크기 계산
def position_size(entry: float, sl: float, equity: float, risk_frac: float):
    """리스크 기반 포지션 크기 계산"""
    # → 재사용 ✅

# 라인 262-266: 레버리지 제안
def leverage_suggestion(atr_pct: float) -> int:
    """ATR 기반 레버리지 제안"""
    # → 재사용 ✅
```

#### 2. **TP/SL 추적 로직** (라인 349-443)

```python
# 라인 358-362: TP 계산
def _tp_from_rr(I, rr):
    """RR 비율로 TP 가격 계산"""
    # → 재사용 ✅

# 라인 364-365: 포지션 저장
ACTIVE_SIG: Dict[str, Dict[str, Any]] = {}  # 활성 포지션
DAILY_PNL: float = 0.0                       # 일일 손익
# → 재사용 ✅

# 라인 366-371: 포지션 추적 시작
def track_new_signal(symbol: str, I: Dict, qty: float):
    """새 포지션 추적 시작"""
    # → 재사용 ✅ (Paper/Live 공통)

# 라인 373-442: TP/SL 터치 확인
def touch_check(symbol: str, price: float, ts_ms: int):
    """1분봉으로 TP/SL 터치 확인 및 청산"""
    # → 수정 후 재사용 ✅
    # Paper: 가상 청산
    # Live: 실제 청산 주문 실행
```

#### 3. **리스크 관리** (라인 540-570)

```python
# 라인 546-568: Flash Guard (급등락 감지)
def flash_guard_update(symbol: str, price: float, ts_ms: int):
    """급등락 감지 및 일시 정지"""
    # → 재사용 ✅

def flash_guard_allowed(symbol: str, ts_ms: int) -> bool:
    """신호 허용 여부 확인"""
    # → 재사용 ✅
```

#### 4. **일손실 한도** (라인 373-378)

```python
# 라인 374-377: 일자 변경 시 PnL 리셋
global DAILY_PNL, TODAY
today_now = time.strftime("%Y-%m-%d")
if today_now != TODAY:
    TODAY = today_now
    DAILY_PNL = 0.0
# → 재사용 ✅
```

---

## 🆕 신규 구현 필요 기능

### 1. **Binance API 연동**

```python
def live_order(self, signal: Dict) -> Dict:
    """
    실제 Binance Futures 주문 실행
    
    Args:
        signal: {
            'symbol': 'BTCUSDT',
            'side': 'LONG' or 'SHORT',
            'qty': 0.01,
            'entry_price': 67000.0,
            'sl_price': 66500.0,
            'tp_price': 68000.0,
            'leverage': 5
        }
    
    Returns:
        order: Binance 주문 응답
    """
    # Binance API 호출
    order = self.client.futures_create_order(
        symbol=signal['symbol'],
        side='BUY' if signal['side'] == 'LONG' else 'SELL',
        type='MARKET',
        quantity=signal['qty'],
        leverage=signal['leverage']
    )
    
    # TP/SL 주문 설정
    self._set_tp_sl_orders(order, signal)
    
    return order
```

### 2. **포지션 동기화**

```python
def sync_positions(self):
    """
    Binance 실제 포지션과 메모리 포지션 동기화
    - 시작 시 실행
    - 주기적 실행 (1분마다)
    """
    positions = self.client.futures_position_information()
    # 메모리 ACTIVE_SIG와 비교
    # 차이 있으면 경고 및 동기화
```

### 3. **주문 상태 확인**

```python
def check_order_status(self, order_id: str) -> str:
    """
    주문 상태 확인
    - FILLED: 체결 완료
    - PARTIALLY_FILLED: 부분 체결
    - CANCELED: 취소됨
    - REJECTED: 거부됨
    """
    order = self.client.futures_get_order(orderId=order_id)
    return order['status']
```

### 4. **에러 처리**

```python
def execute_with_retry(self, func, *args, max_retries=3):
    """
    네트워크 에러 시 재시도
    """
    for i in range(max_retries):
        try:
            return func(*args)
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"최종 실패: {e}")
                raise
            logger.warning(f"재시도 {i+1}/{max_retries}: {e}")
            time.sleep(2 ** i)  # 지수 백오프
```

### 5. **잔고 확인**

```python
def check_balance(self) -> float:
    """
    USDT 잔고 확인
    """
    account = self.client.futures_account()
    for asset in account['assets']:
        if asset['asset'] == 'USDT':
            return float(asset['availableBalance'])
    return 0.0
```

---

## 🚀 구현 순서

### Phase 1: **기본 구조 (1-2시간)**
1. `trading_executor.py` 파일 생성
2. `TradingExecutor` 클래스 기본 틀
3. Paper Trading 로직 이전 (기존 코드 복사)

### Phase 2: **Live Trading 추가 (2-3시간)**
1. Binance API 연동
2. 실제 주문 실행 함수
3. TP/SL 주문 설정
4. 에러 처리

### Phase 3: **통합 테스트 (1-2시간)**
1. Paper Mode 테스트
2. Live Mode 테스트 (소액)
3. 포지션 동기화 확인

### Phase 4: **Trading Bot 생성 및 통합 (2-3시간)**
1. `trading_bot.py` 생성 (신규 파일)
2. 전략 선택 로직 구현 (7개 중 선택)
3. docker-compose.yml 업데이트
4. 전체 파이프라인 테스트

**주의:** Signal Bots와 Ensemble Bot은 수정 안 함!

---

## 📘 API 설계

### TradingExecutor 클래스

```python
class TradingExecutor:
    """
    매매 실행 및 포지션 관리
    
    Attributes:
        mode (str): 'backtest' or 'paper' or 'live'
        client (BinanceClient): Binance API 클라이언트 (live 모드만)
        active_positions (dict): 활성 포지션 {key: position_data}
        daily_pnl (float): 일일 손익
    """
    
    def __init__(self, mode='backtest', binance_api_key=None, binance_secret=None):
        """
        초기화
        
        Args:
            mode: 'backtest' | 'paper' | 'live'
            binance_api_key: Binance API 키 (live 모드 필수)
            binance_secret: Binance Secret (live 모드 필수)
        """
        
    # ===== 주문 실행 =====
    def execute_signal(self, signal: Dict) -> bool:
        """신호를 받아서 주문 실행"""
        
    def _backtest_order(self, signal: Dict):
        """Backtest: 과거 데이터 시뮬레이션"""
        
    def _paper_order(self, signal: Dict):
        """Paper Trading: 실시간 가상 주문"""
        
    def _live_order(self, signal: Dict):
        """Live Trading: 실제 주문"""
        
    # ===== 포지션 관리 =====
    def track_position(self, signal: Dict, order: Dict):
        """포지션 추적 시작"""
        
    def check_tp_sl(self, symbol: str, price: float):
        """TP/SL 터치 확인"""
        
    def close_position(self, position_key: str, reason: str):
        """포지션 청산"""
        
    # ===== 리스크 관리 =====
    def validate_order(self, signal: Dict) -> bool:
        """주문 검증 (리스크 체크)"""
        
    def check_daily_loss_limit(self) -> bool:
        """일손실 한도 확인"""
        
    # ===== 유틸리티 =====
    def sync_positions(self):
        """Binance와 포지션 동기화"""
        
    def get_balance(self) -> float:
        """잔고 조회"""
```

---

## 🔐 환경변수

```bash
# .env 파일

# === 전략 선택 (7개 중 1개) ===
STRATEGY_SELECTOR=ensemble      # 기본: 앙상블 통합
# STRATEGY_SELECTOR=trend       # TREND만
# STRATEGY_SELECTOR=reversion   # REVERSION만
# STRATEGY_SELECTOR=breakout    # BREAKOUT만
# STRATEGY_SELECTOR=scalping    # SCALPING만
# STRATEGY_SELECTOR=daytrade    # DAYTRADE만
# STRATEGY_SELECTOR=swing       # SWING만

# === 매매 모드 (3가지) ===
TRADING_MODE=backtest           # backtest | paper | live
# TRADING_MODE=paper            # 실시간 가상 매매
# TRADING_MODE=live             # 실제 매매 (주의!)

# === Binance API (LIVE 모드 시 필수) ===
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret

# === 리스크 관리 ===
DAILY_RISK_LIMIT_PCT=0.03       # 일손실 한도 3%
MAX_POSITIONS=5                 # 최대 동시 포지션
RISK_PER_TRADE=0.01             # 거래당 리스크 1%

# === 기타 ===
ENABLE_FLASH_GUARD=true         # 급등락 감지
ENABLE_TP_TRAIL=true            # TP1 후 손절가 이동
```

### 전략 선택 예시

```bash
# 예시 1: 앙상블 (기본 추천)
STRATEGY_SELECTOR=ensemble
→ 6개 전략 통합, 가중치 적용, 안정적

# 예시 2: TREND만
STRATEGY_SELECTOR=trend
→ 1시간봉 추세 추종 전략만 실행

# 예시 3: 단타 집중
STRATEGY_SELECTOR=daytrade
→ 5분봉 단타 전략만 실행

# 예시 4: 멀티 전략 (docker-compose)
# 여러 봇을 동시 실행해서 포트폴리오 분산
trading-bot-1:
  STRATEGY_SELECTOR=ensemble
  CAPITAL_ALLOCATION=50%
  
trading-bot-2:
  STRATEGY_SELECTOR=trend
  CAPITAL_ALLOCATION=30%
  
trading-bot-3:
  STRATEGY_SELECTOR=scalping
  CAPITAL_ALLOCATION=20%
```

---

## 📊 DB 스키마 (trading.trades)

```sql
CREATE TABLE IF NOT EXISTS trading.trades (
    trade_id UUID PRIMARY KEY,
    strategy_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,           -- LONG | SHORT
    
    -- 진입
    entry_price NUMERIC(20,8),
    entry_qty NUMERIC(20,8),
    entry_time TIMESTAMP,
    entry_order_id VARCHAR(100),
    
    -- 청산
    exit_price NUMERIC(20,8),
    exit_qty NUMERIC(20,8),
    exit_time TIMESTAMP,
    exit_order_id VARCHAR(100),
    exit_reason VARCHAR(50),             -- TP1 | TP2 | SL | MANUAL
    
    -- 손익
    pnl NUMERIC(20,8),
    pnl_pct NUMERIC(10,4),
    
    -- 메타
    leverage INTEGER,
    trading_mode VARCHAR(10),            -- paper | live
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## ⚠️ 주의사항

### 1. **Paper → Live 전환 시**
- 소액으로 테스트
- 모든 기능 재검증
- 포지션 한도 낮게 설정

### 2. **API 에러 처리**
- 네트워크 타임아웃
- Rate Limit 초과
- 잔고 부족
- 주문 거부

### 3. **포지션 동기화**
- 시작 시 필수
- 주기적 확인 (1분)
- 불일치 시 경고

### 4. **리스크 관리**
- 일손실 한도 엄수
- 포지션 한도 준수
- 레버리지 제한

---

---

## 🎯 PositionTracker (포지션 추적)

**추가일**: 2025-10-17  
**목적**: Signal Bot에서 분리, Trading Bot 전용

### 책임

- TP/SL 터치 확인
- 부분 익절 (TP1 50%, TP2 나머지)
- Trail Stop (TP1 후 손절가 이동)
- 일일 PnL 집계
- 목표 달성률 계산

### 사용법

```python
from trading_bot import PositionTracker

# 초기화
tracker = PositionTracker(mode='paper')  # 'paper' | 'live' | 'backtest'

# 신호 발생 시 포지션 추적 시작
tracker.track_new_position(
    symbol="BTCUSDT",
    side="LONG",
    entry=50000.0,
    sl=49000.0,
    tp=52000.0,
    qty=0.01,
    timestamp=1700000000000
)

# 1분마다 TP/SL 체크
tracker.check_tp_sl(
    symbol="BTCUSDT",
    price=current_price,
    timestamp=current_ts,
    callback=telegram_alert  # 선택적
)

# 조회
active = tracker.get_active_positions()
pnl = tracker.get_daily_pnl()
progress = tracker.get_goal_progress()
```

### 설정

환경변수로 설정:
```bash
TP1_RR=1.0              # TP1 RR 비율
TP2_RR=2.0              # TP2 RR 비율
ENABLE_TP_TRAIL=true    # Trail Stop 활성화
TRAIL_AFTER_TP1=true    # TP1 후 손절가 이동
EQUITY_USDT=10000       # 자산
DAILY_GOAL_PCT=0.02     # 일일 목표 (2%)
```

### 상세 문서

- [리팩토링 가이드](./REFACTORING.md) ⭐ 신규

---

## 📚 참고 문서

- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)
- [CCXT Documentation](https://docs.ccxt.com/)
- [docs/DB_SCHEMA_GUIDE.md](./DB_SCHEMA_GUIDE.md)
- [docs/6_STRATEGY_SYSTEM.md](./6_STRATEGY_SYSTEM.md)
- [docs/REFACTORING.md](./REFACTORING.md) ⭐ 신규

---

**Last Updated:** 2025-10-17  
**Status:** ✅ PositionTracker 추가 완료
