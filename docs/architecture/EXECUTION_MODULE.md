# Execution Module Architecture

**작성일:** 2025-10-19  
**버전:** 1.0  
**상태:** ✅ 리팩토링 완료

---

## 📋 개요

`execution/` 모듈은 매매 실행 및 리스크 관리를 담당하는 핵심 모듈입니다.  
기존 `trading_executor.py`와 `trading_manager.py`를 리팩토링하여 생성되었습니다.

**핵심 원칙:**
- ✅ 단일 책임 원칙 (SRP)
- ✅ 순수 함수형 설계
- ✅ 모듈화 및 재사용성
- ✅ 테스트 용이성

---

## 🗂️ 모듈 구조

```
execution/
├── __init__.py                # 모듈 export
├── executor.py                # 주문 실행 엔진
├── position_sizer.py          # 포지션 크기 계산
├── risk_manager.py            # 리스크 관리
├── position_tracker.py        # 포지션 추적
└── manager.py                 # 매매 오케스트레이션
```

---

## 📦 모듈별 상세

### **1. executor.py - 주문 실행 엔진**

**클래스:** `TradingExecutor`

**책임:**
- 주문 실행 (BACKTEST/PAPER/LIVE 모드)
- Binance API 연동 (LIVE 모드)
- 슬리피지 시뮬레이션 (BACKTEST 모드)
- 재시도 로직 (LIVE 모드)

**주요 메서드:**
```python
class TradingExecutor:
    def __init__(mode, binance_api_key, binance_secret)
    def execute_order(signal: Dict) -> Optional[Dict]
    def _backtest_order(signal, qty) -> Dict
    def _paper_order(signal, qty) -> Dict
    def _live_order_with_retry(signal, qty) -> Optional[Dict]
    def get_mode() -> str
```

**사용 예시:**
```python
from execution import TradingExecutor

executor = TradingExecutor(mode='paper')

signal = {
    'symbol': 'BTCUSDT',
    'side': 'LONG',
    'entry_price': 67000.0,
    'sl_price': 66500.0,
    'tp_price': 68000.0,
    'confidence': 0.8
}

order = executor.execute_order(signal)
```

---

### **2. position_sizer.py - 포지션 크기 계산**

**클래스:** `PositionSizer`

**책임:**
- 리스크 기반 포지션 계산
- 신호 품질 가중치 적용
- 포지션 한도 체크

**주요 메서드:**
```python
class PositionSizer:
    def __init__()
    def calculate(signal: Dict) -> Tuple[float, Dict]
    def _calculate_quality_weight(signal: Dict) -> float
```

**계산 공식:**
```
기본 수량 = (계좌 잔고 × 리스크 비율) ÷ 스톱 거리
조정 수량 = 기본 수량 × 품질 가중치
최종 수량 = min(조정 수량, 최대 포지션 한도)
```

**품질 가중치:**
- confidence 0.5 → 가중치 0.7
- confidence 1.0 → 가중치 1.3
- 선형 맵핑

---

### **3. risk_manager.py - 리스크 관리**

**클래스:** `RiskManager`

**책임:**
- 일일 손실 한도 체크
- 동시 포지션 수 제한
- 심볼별 노출 한도
- Flash Guard (급등락 감지)

**주요 메서드:**
```python
class RiskManager:
    def __init__(config)
    def check_order(signal, qty) -> Tuple[bool, str]
    def flash_guard_update(symbol, price, ts_ms)
    def flash_guard_allowed(symbol, ts_ms) -> bool
    def add_position(symbol, position_value)
    def remove_position(symbol, position_value)
    def reset_daily()
```

**리스크 한도:**
- 일일 손실: 계좌의 3%
- 동시 포지션: 최대 5개
- 심볼별 노출: 계좌의 30%
- Flash Guard: 60초 내 3% 이상 변동 시 일시 보류

---

### **4. position_tracker.py - 포지션 추적**

**클래스:** `PositionTracker`

**책임:**
- 활성 포지션 추적
- TP/SL 터치 확인
- 부분 익절 (TP1 50%)
- Trail Stop 관리
- 일일 PnL 집계

**주요 메서드:**
```python
class PositionTracker:
    def __init__(mode)
    def track_new_position(symbol, side, entry, sl, tp, qty, timestamp)
    def check_tp_sl(symbol, price, timestamp, callback)
    def get_goal_progress() -> str
    def get_active_positions() -> Dict
    def get_daily_pnl() -> float
```

**TP/SL 로직:**
- TP1 (RR 1.0): 50% 부분 익절
- TP1 달성 후: SL을 진입가로 이동 (Trail Stop)
- TP2 (RR 2.0): 나머지 청산

---

### **5. manager.py - 매매 오케스트레이션**

**순수 함수들:** (클래스 없음)

**책임:**
- 신호/결정 조회
- 신호 → 주문 변환
- 주문 실행
- DB 저장

**주요 함수:**
```python
def fetch_ensemble_decisions() -> List[Dict]
def fetch_strategy_signals(strategy_id: str) -> List[Dict]
def fetch_signals(strategy: str) -> List[Dict]
def convert_to_order(signal, strategy) -> Optional[Dict]
def save_trade(signal, order, strategy)
def mark_as_executed(signal, strategy)
def process_trades(executor, strategy='ensemble')  # 메인 함수
```

**사용 예시:**
```python
from execution import TradingExecutor, manager

executor = TradingExecutor(mode='paper')

# 1 사이클 실행
manager.process_trades(executor, strategy='ensemble')
```

---

## 🔄 실행 흐름

```
run_trading.py
    ↓
main()
    ↓
TradingExecutor 초기화
    ↓
while 루프 시작
    ↓
manager.process_trades(executor, strategy)
    ↓
    ├─ fetch_signals(strategy)
    │   └─ DB에서 신호/결정 조회
    ↓
    ├─ convert_to_order(signal, strategy)
    │   └─ 신호 → 주문 형식 변환
    ↓
    ├─ executor.execute_order(order_signal)
    │   ├─ position_sizer.calculate(signal)
    │   ├─ risk_manager.check_order(signal, qty)
    │   ├─ _backtest_order() / _paper_order() / _live_order()
    │   └─ risk_manager.add_position(symbol, value)
    ↓
    ├─ save_trade(signal, order, strategy)
    │   └─ trading.trades 테이블에 저장
    ↓
    └─ mark_as_executed(signal, strategy)
        └─ trading.decisions 업데이트
```

---

## 🎯 전략 선택

환경 변수 `STRATEGY_SELECTOR`로 제어:

| 값 | 설명 | 테이블 |
|----|------|--------|
| **ensemble** | 앙상블 통합 결정 (기본) | `trading.decisions` |
| trend | TREND 단일 전략 | `monitoring.signals` |
| reversion | REVERSION 단일 전략 | `monitoring.signals` |
| breakout | BREAKOUT 단일 전략 | `monitoring.signals` |
| scalping | SCALPING 단일 전략 | `monitoring.signals` |
| daytrade | DAYTRADE 단일 전략 | `monitoring.signals` |
| swing | SWING 단일 전략 | `monitoring.signals` |

---

## ⚙️ 환경 변수

### **필수 설정**
```bash
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db
STRATEGY_SELECTOR=ensemble        # 전략 선택
TRADING_MODE=paper                # backtest | paper | live
```

### **리스크 설정**
```bash
EQUITY_USDT=10000                 # 계좌 잔고
RISK_PER_TRADE=0.01               # 거래당 리스크 (1%)
DAILY_LOSS_LIMIT_PCT=0.03         # 일일 손실 한도 (3%)
MAX_CONCURRENT_POSITIONS=5        # 동시 포지션 수
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3   # 심볼별 한도 (30%)
```

### **포지션 사이징**
```bash
QUALITY_WEIGHT_MIN=0.7            # 품질 가중치 최소
QUALITY_WEIGHT_MAX=1.3            # 품질 가중치 최대
MAX_POSITION_VALUE=5000           # 포지션 최대 가치
MIN_POSITION_VALUE=10             # 포지션 최소 가치
```

### **Flash Guard**
```bash
enable_flash_guard=false          # 급등락 감지 활성화
flash_window_sec=60               # 감지 윈도우 (초)
flash_pct=0.03                    # 변동률 임계값 (3%)
flash_pause_candles=3             # 보류 캔들 수
```

### **Live Trading 전용**
```bash
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret
```

---

## 📊 DB 스키마

### **trading.trades** (거래 결과)
```sql
CREATE TABLE trading.trades (
    trade_id UUID PRIMARY KEY,
    strategy_id VARCHAR(50),
    symbol VARCHAR(20),
    side VARCHAR(10),
    entry_price NUMERIC,
    quantity NUMERIC,
    ts_open TIMESTAMP,
    leverage INTEGER,
    status VARCHAR(20),
    created_at TIMESTAMP
);
```

### **trading.decisions** (앙상블 결정)
```sql
CREATE TABLE trading.decisions (
    decision_id UUID PRIMARY KEY,
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    candle_closed_at TIMESTAMP,
    chosen_side VARCHAR(10),
    final_score NUMERIC,
    executed_at TIMESTAMP,          -- 실행 완료 표시
    created_at TIMESTAMP
);
```

---

## 🧪 테스트

### **Import 테스트**
```python
from execution import TradingExecutor, PositionSizer, RiskManager, PositionTracker
from execution import manager

print("✅ Execution 모듈 로드 성공")
```

### **주문 실행 테스트**
```python
executor = TradingExecutor(mode='backtest')

signal = {
    'symbol': 'BTCUSDT',
    'side': 'LONG',
    'entry_price': 67000.0,
    'sl_price': 66500.0,
    'tp_price': 68000.0,
    'confidence': 0.8
}

order = executor.execute_order(signal)
assert order is not None
assert order['status'] == 'FILLED'
```

### **매매 오케스트레이션 테스트**
```python
from execution import TradingExecutor, manager

executor = TradingExecutor(mode='paper')
manager.process_trades(executor, strategy='daytrade')
```

---

## 🔄 리팩토링 이력

| 날짜 | 변경 사항 |
|------|-----------|
| 2025-10-19 | execution/ 모듈 생성 (Phase 1) |
| 2025-10-19 | 4개 파일 분할 완료 (Phase 2) |
| 2025-10-19 | manager.py 순수 함수화 (Phase 3) |
| 2025-10-19 | run_trading.py 재작성 (Phase 4) |
| 2025-10-19 | Import 경로 수정 (Phase 5) |
| 2025-10-19 | 문서 작성 완료 (Phase 6) |

---

## 📚 참고 문서

- [EXECUTION_MODULE_REFACTORING.md](../implementation/EXECUTION_MODULE_REFACTORING.md) - 리팩토링 체크리스트
- [TRADING_EXECUTOR.md](TRADING_EXECUTOR.md) - 기존 아키텍처 (Deprecated)
- [REFACTORING.md](REFACTORING.md) - 전체 리팩토링 가이드
- [PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md) - 프로젝트 구조

---

## 🚀 빠른 시작

### **1. 환경 설정**
```bash
cp env.example .env
# DATABASE_URL, STRATEGY_SELECTOR, TRADING_MODE 설정
```

### **2. 매매 실행**
```bash
python run_trading.py
```

### **3. 전략 변경**
```bash
# .env 파일 수정
STRATEGY_SELECTOR=ensemble  # or trend, reversion, etc.
TRADING_MODE=paper          # or backtest, live
```

---

**작성자:** Windsurf Cascade  
**최종 업데이트:** 2025-10-19 15:50  
**상태:** ✅ 완료
