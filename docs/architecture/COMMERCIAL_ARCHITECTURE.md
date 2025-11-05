# 상용 트레이딩 봇 아키텍처 표준

**날짜:** 2025-10-19  
**참고:** 실제 상용 프로그램 구조 분석

---

## 📊 표준 아키텍처

### 알고리즘 트레이딩 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│                  Market Data Layer                       │
│  (Collector / Data Provider)                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Strategy Engine Layer                       │
│  (Individual Strategies)                                 │
│  ├── Strategy A → Signal                                │
│  ├── Strategy B → Signal                                │
│  └── Strategy C → Signal                                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            Portfolio Manager Layer ⭐                    │
│  (Signal Aggregation / Meta Strategy)                   │
│  ├── Signal Aggregation                                 │
│  ├── Position Sizing                                    │
│  └── Portfolio Risk                                     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Risk Manager Layer                          │
│  (Pre-Trade Risk Checks)                                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            Execution Engine Layer                        │
│  (Order Management / Broker API)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🏷️ 상용 프로그램 표준 용어

### 1. Market Data Layer
- **Collector** (우리 용어)
- **Data Provider** (상용 표준)
- **Market Data Feed**

### 2. Strategy Engine
- **Strategies** (우리 용어) ✅
- **Strategy Engine** (상용 표준)
- **Signal Generator**

### 3. Portfolio Manager ⭐
- **Ensemble** (우리 기존 용어) ❌
- **Portfolio Manager** (상용 표준) ✅
- **Strategy Orchestrator**
- **Decision Engine**
- **Signal Aggregator**

### 4. Risk Manager
- **Risk Manager** (우리 용어) ✅
- **Pre-Trade Risk Check**
- **Compliance Engine**

### 5. Execution Engine
- **Trading Executor** (우리 용어) ✅
- **Execution Engine** (상용 표준)
- **Order Management System (OMS)**

---

## 🎯 올바른 모듈 구조

### TO-BE (상용 표준 적용)

```python
project/
├── collector/              # Market Data Layer
│   ├── websocket_collector.py
│   └── rest_collector.py
│
├── strategies/             # Strategy Engine Layer
│   ├── scalping.py        # 개별 전략
│   ├── daytrade.py
│   ├── swing.py
│   ├── trend.py
│   ├── reversion.py
│   ├── breakout.py
│   └── portfolio_manager.py  # ⭐ Meta Strategy
│
├── signals/                # Signal Framework (Helper)
│   ├── signal_generator.py   # 신호 생성 프레임워크
│   └── signal_storage.py     # DB 저장
│
├── trading/                # Execution Layer
│   ├── risk_manager.py       # Pre-Trade Risk
│   ├── executor.py           # Order Execution
│   └── position_tracker.py   # Position Management
│
└── main.py                 # Orchestrator
```

---

## 💡 핵심 개념

### 1. signals/ ≠ 신호 생성

**signals/** 모듈은 "신호 생성 프레임워크"입니다.
- SignalGenerator 클래스 (재사용 가능한 프레임워크)
- 실제 신호 로직은 strategies/에 있음

### 2. strategies/ = 신호 생성 + 통합

**strategies/** 모듈은 두 가지 역할:
1. 개별 전략: 특정 조건 기반 신호 생성
2. **Portfolio Manager**: 여러 신호 통합 (Meta Strategy)

### 3. Portfolio Manager = 메타 전략

Portfolio Manager도 "전략"의 일종입니다.
- 개별 전략들의 신호를 입력으로 받음
- 가중치, 투표, 베이지안 등으로 통합
- 최종 거래 결정 생성

---

## 🔄 플로우 비교

### ❌ 기존 (잘못된 개념)

```
collector → signals → strategies → ensemble → trading
```

- signals가 신호 "생성"하는 것처럼 보임
- ensemble이 별도 레이어처럼 보임

### ✅ 상용 표준

```
collector → strategies (각각 신호) → portfolio_manager → trading
                                    (strategies 내부)
```

- strategies에서 신호 생성
- portfolio_manager도 strategies의 일부
- signals/는 헬퍼 프레임워크

---

## 📚 실제 상용 프로그램 사례

### 1. Freqtrade (오픈소스)
```python
freqtrade/
├── data/           # Data Provider
├── strategy/       # Strategy Engine
│   └── strategy.py  # 개별 전략들
├── optimize/       # Backtesting
└── rpc/            # API/Communication
```

### 2. QuantConnect (클라우드 플랫폼)
```
Algorithm
├── Universe Selection
├── Alpha Models (Strategies)
├── Portfolio Construction (Portfolio Manager)
├── Risk Management
└── Execution
```

### 3. AlgoTrader (Enterprise)
```
- Strategy Service
- Portfolio Service  ⭐
- Risk Service
- Order Service
```

---

## 🎓 참고 자료

- [Algorithmic Trading System Architecture - Stuart Gordon Reid](http://www.turingfinance.com/algorithmic-trading-system-architecture-post/)
- [High-frequency crypto trading bot architecture - Medium](https://medium.com/@kb.pcre/high-frequency-crypto-trading-bot-architecture-part-1-48b880bfc85f)
- [QuantConnect Documentation](https://www.quantconnect.com/docs/)
- [Freqtrade Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)

---

## 🚀 우리 프로젝트 적용 계획

### Phase 7: collector/ 모듈 분리
- WebSocket 데이터 수집 로직 분리

### Phase 8: main.py 생성
- 전체 시스템 오케스트레이션

### Phase 9: trading/ 모듈 리팩토링
- Risk Manager 분리
- Executor 정리
- Position Tracker 정리

### Phase 10: ensemble → portfolio_manager
- ensemble_bot.py → strategies/portfolio_manager.py
- 상용 표준 용어 적용

---

**Last Updated:** 2025-10-19  
**Author:** Cascade AI
