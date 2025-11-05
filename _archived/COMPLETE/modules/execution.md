# 💼 Execution 모듈

**통합 매매 실행 모듈** - 단일 엔진 아키텍처

**경로**: `execution/`

**최종 업데이트**: 2025-10-19 20:50

---

## 개요

⭐ **단일 엔진 + 모드별 플러그인 구조**

모든 거래 모드(backtest/paper/live)에서 동일한 `TradingEngine`을 사용하고,
모드별로 데이터 소스와 실행기만 교체합니다.

### 구조
```
execution/
├── engine.py                   # ⭐ TradingEngine (통합 엔진)
├── data_sources/               # 데이터 소스 플러그인
│   ├── backtest.py            # CSV/Parquet 재생
│   └── live.py                # 실시간 시세
├── executors/                  # 주문 실행 플러그인
│   ├── simulation.py          # 백테스트 체결 (수수료+슬리피지)
│   ├── paper.py               # 가상 체결
│   └── live.py                # 실제 체결 (Binance SDK)
├── position_sizer.py           # 포지션 크기 계산
├── risk_manager.py             # 리스크 관리
├── executor_wrapper.py         # 하위 호환성 래퍼
└── manager.py                  # 하위 호환성 stub
```

---

## TradingEngine

**통합 거래 엔진 (모든 모드 공통)**

### 초기화
```python
from execution.engine import TradingEngine

# 백테스트 모드
engine = TradingEngine(
    mode='backtest',
    data_path='data/BTCUSDT_5m.csv',
    initial_capital=10000,
    fee_rate=0.0004,
    slippage_pct=0.0005
)

# 페이퍼/라이브 모드
engine = TradingEngine(
    mode='paper',  # or 'live'
    symbols=['BTCUSDT'],
    timeframe='5m',
    initial_capital=10000,
    fee_rate=0.0004,
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET')
)
```

### 백테스트 실행
```python
from strategies import scalping

# 전략 설정
strategy_config = {
    'rr': 1.5,
    'atr_mult_sl': 1.0,
    'risk_per_trade': 0.015,
    'min_leverage': 2,
    'max_leverage': 10,
    'cooldown_candles': 3,
}

# 백테스트 실행
trades, metrics = engine.run_backtest(scalping, strategy_config)

# metrics = {
#     'total_trades': 1388,
#     'win_rate': 0.388,
#     'total_return_pct': -99.84,
#     'sharpe_ratio': -1.04,
#     'max_drawdown_pct': 103.6,
#     'profit_factor': 0.82,
#     ...
# }
```

---

## PositionSizer

**포지션 크기 계산**

### calculate()
```python
from execution import PositionSizer

sizer = PositionSizer(
    equity_usdt=10000,
    risk_per_trade=0.01  # 1%
)

qty, metadata = sizer.calculate(
    symbol="BTCUSDT",
    side="LONG",
    entry=34250.0,
    sl=34000.0,
    quality_score=0.8  # 신호 품질
)

# qty = 0.4 (예시)
# metadata = {
#     "risk_usdt": 100.0,
#     "stop_distance": 250.0,
#     "position_value": 13700.0,
#     "quality_weight": 1.04
# }
```

---

## RiskManager

**리스크 체크**

### check_risk()
```python
from execution import RiskManager

risk_mgr = RiskManager(
    equity_usdt=10000,
    daily_loss_limit_pct=0.03  # 3%
)

allowed, reason = risk_mgr.check_risk(
    symbol="BTCUSDT",
    side="LONG",
    position_value=5000,
    current_positions=[...]
)

if allowed:
    # 거래 실행
else:
    print(f"거래 거부: {reason}")
```

**체크 항목**:
- ✅ 일일 손실 한도
- ✅ 동시 포지션 수
- ✅ 심볼별 노출 한도
- ✅ Flash Guard (급등락)

---

## PositionTracker

**포지션 추적**

### track()
```python
from execution import PositionTracker

tracker = PositionTracker(mode="paper")

# 포지션 시작
tracker.track(
    symbol="BTCUSDT",
    side="LONG",
    entry=34250.0,
    sl=34000.0,
    tp1=34500.0,
    tp2=34750.0,
    qty=0.1,
    timestamp=1698264600000
)

# TP/SL 체크
closed_positions = tracker.check_tp_sl(
    symbol="BTCUSDT",
    price=34510.0,  # 현재가
    timestamp=1698264700000,
    callback=close_position_callback
)
```

---

## manager.py

**오케스트레이션**

### process_trades()
```python
from execution import TradingExecutor
from execution import manager

executor = TradingExecutor(mode="paper")

# 주기적으로 실행
while True:
    manager.process_trades(
        executor,
        strategy="ensemble"  # 또는 "trend", "reversion" 등
    )
    time.sleep(5)
```

**동작**:
1. `trading.decisions`에서 미실행 결정 조회
2. 리스크 체크
3. 포지션 크기 계산
4. 주문 실행
5. `trading.trades`에 저장
6. 포지션 추적 시작

---

## 3가지 모드

### BACKTEST
- 과거 데이터 시뮬레이션
- 실제 API 호출 없음
- 즉시 체결

### PAPER
- 실시간 가상 거래
- 실제 API 호출 없음
- 실시간 가격으로 체결 시뮬레이션

### LIVE
- 실제 거래
- 바이낸스 API 호출
- 실제 주문 실행

---

## 사용 예시

### 전체 플로우

```python
from execution import TradingExecutor
from execution import manager
from common.database import get_db_connection

# 1. Executor 초기화
executor = TradingExecutor(
    mode="paper",
    binance_api_key=None,
    binance_secret=None
)

# 2. 주기적 실행
while True:
    try:
        manager.process_trades(executor, strategy="ensemble")
    except Exception as e:
        logger.error(f"Execution 실패: {e}")
    
    time.sleep(5)
```

---

## 주의사항

### LIVE 모드
- ⚠️ 실제 돈을 사용합니다
- 반드시 BACKTEST → PAPER → LIVE 순서로 검증
- API 키는 안전하게 보관
- 거래 권한만 부여 (출금 권한 제외)

### 리스크 관리
- `RISK_PER_TRADE`는 1% 이하 권장
- `DAILY_LOSS_LIMIT_PCT`는 3% 이하 권장
- 소액으로 시작

---

**최종 업데이트**: 2025-10-19
