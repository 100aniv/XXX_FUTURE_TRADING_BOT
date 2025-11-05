# 🏗️ 시스템 아키텍처 (최종)

**최종 업데이트**: 2025-10-19 20:51  
**상태**: 통합 엔진 완성 ✅

---

## 📊 전체 플로우

```
┌──────────────────────────────────────────────────────────────────────┐
│                           main.py                                     │
│                    (하나의 통합 프로그램)                             │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 1️⃣ collector/ (데이터 수집)                                          │
├──────────────────────────────────────────────────────────────────────┤
│ • WebSocketCollector                                                  │
│   - Binance Futures WebSocket 연결                                    │
│   - 실시간 캔들 데이터 수신 (5m, 15m, 1h, 4h)                        │
│                                                                        │
│ • RESTCollector (bootstrap_history)                                   │
│   - 초기 히스토리 데이터 로드                                         │
│   - lookback 기간 데이터 채우기                                       │
├──────────────────────────────────────────────────────────────────────┤
│ OUTPUT: 실시간 캔들 데이터 → signals/ 모듈                           │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2️⃣ indicators/ (지표 계산)                                           │
├──────────────────────────────────────────────────────────────────────┤
│ • calculate_all_indicators()                                          │
│   - EMA, SMA, Bollinger Bands                                         │
│   - RSI, Stochastic, MACD                                             │
│   - ATR, ADX, Volume                                                  │
│   - Support/Resistance                                                │
├──────────────────────────────────────────────────────────────────────┤
│ INPUT: 캔들 데이터 (OHLCV)                                           │
│ OUTPUT: 지표 dict → strategies/                                       │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3️⃣ signals/ (신호 생성 프레임워크)                                   │
├──────────────────────────────────────────────────────────────────────┤
│ • SignalGenerator                                                     │
│   - 캔들 데이터 + 지표 → 전략 실행                                   │
│   - 필터링 (쿨다운, 레짐, Flash Guard)                                │
│   - 검증 및 로깅                                                      │
│                                                                        │
│ • signal_storage                                                      │
│   - DB 저장 (monitoring.signals)                                      │
│   - 멱등성 보장                                                        │
├──────────────────────────────────────────────────────────────────────┤
│ INPUT: 캔들 + 지표                                                    │
│ OUTPUT: monitoring.signals 테이블                                     │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 4️⃣ strategies/ (전략 로직)                                           │
├──────────────────────────────────────────────────────────────────────┤
│ 개별 전략 (6개):                                                      │
│ • trend.py         - 추세 추종 전략                                   │
│ • reversion.py     - 평균 회귀 전략                                   │
│ • breakout.py      - 돌파 전략                                        │
│ • scalping.py      - 스캘핑 전략                                      │
│ • daytrade.py      - 데이트레이딩 전략                                │
│ • swing.py         - 스윙 전략                                        │
│                                                                        │
│ 통합 전략:                                                            │
│ • ensemble.py      - 6개 전략 신호 통합                               │
│   - process_pending_signals()                                         │
│   - 가중치 기반 점수 계산                                             │
│   - 최종 결정 (LONG/SHORT/FLAT)                                       │
├──────────────────────────────────────────────────────────────────────┤
│ INPUT: monitoring.signals (6개 전략 신호)                             │
│ OUTPUT: trading.decisions (통합 결정)                                 │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 5️⃣ execution/ (매매 실행) ⭐ 통합 엔진 구조                          │
├──────────────────────────────────────────────────────────────────────┤
│ • engine.py (TradingEngine) ⭐ 단일 엔진                              │
│   - 모든 모드(backtest/paper/live)에서 공통 사용                      │
│   - run_backtest() - 백테스트 실행                                    │
│   - 전략 로직 + 지표 계산 + 포지션 관리 통합                         │
│                                                                        │
│ • data_sources/ - 데이터 소스 플러그인                                │
│   - backtest.py: CSV/Parquet 재생                                     │
│   - live.py: 실시간 WebSocket/REST                                    │
│                                                                        │
│ • executors/ - 주문 실행 플러그인                                     │
│   - simulation.py: 백테스트 체결 (수수료+슬리피지)                    │
│   - paper.py: 가상 체결 (실시간 가격)                                 │
│   - live.py: 실제 체결 (Binance SDK)                                  │
│                                                                        │
│ • position_sizer.py (PositionSizer)                                   │
│   - 리스크 기반 포지션 크기 계산                                      │
│   - common.calculations 모듈 활용                                     │
│                                                                        │
│ • risk_manager.py (RiskManager)                                       │
│   - 일일 손실 한도 체크                                               │
│   - 동시 포지션 수 제한                                               │
│   - 포지션 추적 (update_trailing_stop, check_tpsl)                   │
│   - TP1/TP2 관리 및 트레일링 스탑                                     │
│                                                                        │
│ • executor_wrapper.py (TradingExecutor)                               │
│   - 실시간 모드용 래퍼 (manager가 사용)                               │
│   - executors/ 플러그인 선택                                          │
│                                                                        │
│ • manager.py (오케스트레이션)                                         │
│   - fetch_ensemble_decisions()                                        │
│   - process_trades()                                                  │
│   - save_trade()                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ INPUT: trading.decisions (미실행 결정)                                │
│ OUTPUT: trading.trades (거래 기록)                                    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 6️⃣ common/ (공통 모듈)                                               │
├──────────────────────────────────────────────────────────────────────┤
│ • database.py      - PostgreSQL 연결 관리                             │
│ • logger.py        - 타입별 로깅 (signals/trading/test/errors)       │
│ • config.py        - 환경변수 설정 로드 및 검증                       │
│ • calculations.py  - 공통 계산 함수 (TP, RR, 포지션 크기)            │
│ • messaging.py     - 텔레그램 알림 (선택적)                           │
│ • utils.py         - 유틸리티 함수                                    │
└──────────────────────────────────────────────────────────────────────┘

```

---

## 🗄️ 데이터베이스 스키마

```sql
-- ============================================
-- monitoring 스키마 (모니터링)
-- ============================================
monitoring.signals
├── signal_id (PK)
├── strategy_id (trend, reversion, breakout, scalping, daytrade, swing)
├── symbol
├── timeframe
├── direction (LONG/SHORT/FLAT)
├── entry_price, sl_price, tp_price
├── confidence, atr, leverage
├── features (JSONB) - 지표 데이터
└── created_at

-- ============================================
-- trading 스키마 (거래)
-- ============================================
trading.decisions
├── decision_id (PK)
├── symbol, timeframe
├── candle_closed_at
├── chosen_side (LONG/SHORT/FLAT)
├── chosen_size
├── score
├── weights (JSONB) - 전략별 가중치
├── from_signals (JSONB) - 참고 신호들
└── created_at

trading.trades
├── trade_id (PK)
├── decision_id (FK → decisions)
├── symbol, side
├── entry_price, sl_price, tp_price
├── qty, leverage
├── status (OPEN/TP1/TP2/CLOSED)
├── pnl
└── created_at, closed_at

trading.positions
├── position_id (PK)
├── trade_id (FK → trades)
├── symbol, side
├── entry_price, current_price
├── qty, unrealized_pnl
└── updated_at

-- ============================================
-- reporting 스키마 (리포팅)
-- ============================================
reporting.strategy_performance
├── strategy_id (PK)
├── total_trades, win_trades, loss_trades
├── winrate, rr_mean, sharpe
└── updated_at

reporting.daily_pnl
├── date (PK)
├── total_pnl, total_trades
├── best_strategy, worst_strategy
└── created_at
```

---

## 🔄 실행 플로우

### **실시간 루프 (main.py)**

```python
while True:
    # 1. 캔들 수신 (WebSocket)
    candle = websocket_collector.receive()
    
    # 2. 신호 생성 (6개 전략)
    signal = signal_generator.process_candle(candle)
    → monitoring.signals 저장
    
    # 3. 앙상블 통합 (주기적 or 이벤트 기반)
    ensemble.process_pending_signals()
    → trading.decisions 저장
    
    # 4. 매매 실행
    execution.manager.process_trades()
    → trading.trades 저장
    
    # 5. 포지션 추적
    risk_manager.check_tpsl()
    → trading.positions 업데이트
```

---

## 📦 모듈 의존성

```
main.py
├── collector/ (WebSocket, REST)
│   └── common/database, common/logger
│
├── signals/ (SignalGenerator)
│   ├── strategies/ (6개 전략)
│   ├── indicators/ (지표 계산)
│   └── common/ (전체)
│
├── strategies/ensemble (통합 결정)
│   └── common/database, common/logger
│
└── execution/ (매매 실행)
    ├── execution/engine (백테스트 전용)
    ├── execution/executor_wrapper (실시간용 래퍼)
    ├── execution/manager (실시간 오케스트레이션)
    ├── execution/position_sizer (포지션 계산)
    ├── execution/risk_manager (리스크 + 포지션 추적 통합)
    └── common/ (전체)
```

---

## 🎯 핵심 원칙

1. **단일 책임 원칙** - 각 모듈은 하나의 역할만
2. **의존성 역전** - 상위 모듈은 하위 모듈에 의존하지 않음
3. **순수 함수형** - 부작용 최소화, 테스트 용이
4. **멱등성 보장** - 동일 입력 → 동일 출력
5. **에러 핸들링** - 각 레이어에서 적절한 예외 처리

---

## 🚀 실행 방법

### **1. 신호 생성 봇 (기본)**
```bash
python main.py
```

### **2. 매매 실행 (ensemble + execution)**
```bash
python run_trading.py
```

### **3. Docker Compose (전체 시스템)**
```bash
docker-compose up -d
```

---

## 📝 환경변수 (필수)

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5433/trading_db

# Trading
STRATEGY_SELECTOR=ensemble  # ensemble | trend | reversion | ...
TRADING_MODE=paper         # backtest | paper | live
EQUITY_USDT=10000
RISK_PER_TRADE=0.01

# Binance (live 모드만)
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# Telegram (선택적)
ENABLE_TELEGRAM=false
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## ✅ 테스트 상태

```
✅ collector/ - WebSocket 연결, REST API
✅ indicators/ - 지표 계산
✅ signals/ - 신호 생성 및 저장
✅ strategies/ - 6개 전략 + ensemble
✅ execution/ - 매매 실행 엔진
✅ common/ - 공통 모듈

⏳ E2E 통합 테스트 (다음 단계)
```

---

## 🔗 참고 문서

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 프로젝트 구조
- [REFACTORING_COMPLETE.md](REFACTORING_COMPLETE.md) - 리팩토링 이력
- [docs/architecture/](docs/architecture/) - 아키텍처 문서
- [docs/implementation/](docs/implementation/) - 구현 가이드
