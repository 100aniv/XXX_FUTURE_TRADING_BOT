# 🚀 통합 트레이딩 시스템 v2.0

**Unified Trading System - 6 Strategies + Ensemble + Real-time Execution**

**버전**: v2.0 (2025-10-19)  
**상태**: ✅ 리팩토링 완료, 운영 준비 완료  
**모드**: BACKTEST / PAPER / LIVE

---

## 📋 목차

1. [시스템 개요](#-시스템-개요)
2. [핵심 기능](#-핵심-기능)
3. [빠른 시작](#-빠른-시작)
4. [시스템 아키텍처](#-시스템-아키텍처)
5. [모듈 구조](#-모듈-구조)
6. [설정 가이드](#-설정-가이드)
7. [실행 방법](#-실행-방법)
8. [문서](#-문서)

---

## 🎯 시스템 개요

**바이낸스 선물 트레이딩 자동화 시스템**

6개의 전략이 동시에 실시간 시장 데이터를 분석하여 신호를 생성하고,  
Ensemble(앙상블) 모듈이 가중치 기반으로 통합하여 최종 매매 결정을 내립니다.

### **핵심 원칙**
- ✅ **실시간 처리**: WebSocket → 신호 생성 → 통합 → 실행 (100ms 이내)
- ✅ **멱등성 보장**: 동일 입력 → 동일 출력, 중복 방지
- ✅ **모듈화**: 각 모듈 독립적 개발/테스트 가능
- ✅ **확장성**: 새로운 전략 추가 용이
- ✅ **리스크 관리**: 일일 손실 한도, 동시 포지션 제한

---

## 🎯 핵심 개념

**하나의 코드베이스, 세 가지 실행 모드**

```
main.py (단일 진입점)
  ├─ TRADING_MODE=backtest → 과거 데이터로 전략 검증
  ├─ TRADING_MODE=paper    → 실시간 모의 거래
  └─ TRADING_MODE=live     → 실제 거래
```

모든 모드는 **동일한 로직**을 사용합니다:
- ✅ 동일한 전략 코드 (`strategies/`)
- ✅ 동일한 지표 계산 (`indicators/`)
- ✅ 동일한 실행 엔진 (`execution/engine.py`)
- ✅ 동일한 리스크 관리 (`execution/risk_manager.py`)

**차이점은 데이터 소스와 주문 실행 방식뿐입니다.**

---

## ✨ 핵심 기능

### **1. 6개 전략 동시 운영**

| 전략 | 타임프레임 | 특징 | 강점 |
|------|-----------|------|------|
| **Trend** | 1h | EMA 크로스 + MACD | 추세장 |
| **Reversion** | 5m | RSI 극단 + BB | 횡보장 |
| **Breakout** | 15m | Donchian 돌파 | 변동성 구간 |
| **Scalping** | 1m | BB 터치 + EMA | 단기 수익 |
| **Daytrade** | 5m | 레짐 기반 | 균형잡힌 수익 |
| **Swing** | 15m | 추세장 | 안정적 수익 |

### **2. Ensemble 통합**
```
6개 전략 신호 →
  가중치 계산 (승률, RR, 샤프, 신뢰도, 레짐) →
    최종 결정 (LONG / SHORT / FLAT) →
      매매 실행
```

**가중치 공식**:
```python
weight = α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐적합도
```

### **3. 3가지 실행 모드**

| 모드 | 설명 | 용도 |
|------|------|------|
| **BACKTEST** | 과거 데이터 시뮬레이션 | 전략 검증 |
| **PAPER** | 실시간 가상 거래 | 실전 전 테스트 |
| **LIVE** | 실제 거래 실행 | 운영 |

### **4. 리스크 관리**
- ✅ 일일 손실 한도 (기본: 3%)
- ✅ 동시 포지션 제한 (기본: 5개)
- ✅ 심볼별 노출 한도 (기본: 30%)
- ✅ Flash Guard (급등락 감지 및 일시정지)

---

## 🚀 빠른 시작

### **1. 환경 준비**

```bash
# 저장소 클론
git clone https://github.com/yourname/future_alarm_bot.git
cd future_alarm_bot

# 가상환경 생성 및 활성화
python -m venv trading_bot_env
.\trading_bot_env\Scripts\activate  # Windows
# 🚀 통합 트레이딩 시스템 (Unified Trading System)_env/bin/activate  # Linux/Mac

# 패키지 설치
pip install -r requirements.txt
```

### **2. 데이터베이스 설정**

```bash
# Docker로 PostgreSQL 실행
docker-compose up -d postgres

# 스키마 초기화
psql -U trading_user -d trading_db -f init_db.sql
```

또는 Docker 없이:
```bash
# PostgreSQL 설치 후
createdb trading_db
psql trading_db < init_db.sql
```

### **3. 환경변수 설정**

`.env` 파일 생성:

```bash
# ============================================
# Database
# ============================================
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db

# ============================================
# Trading
# ============================================
STRATEGY_SELECTOR=ensemble  # ensemble | trend | reversion | breakout | scalping | daytrade | swing
TRADING_MODE=paper         # backtest | paper | live

# ============================================
# Risk Management
# ============================================
EQUITY_USDT=10000          # 계좌 자산 (USDT)
RISK_PER_TRADE=0.01        # 거래당 리스크 (1%)

# ============================================
# Trading Pairs
# ============================================
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=5m
LOOKBACK=400

# ============================================
# Binance API (LIVE 모드만 필요)
# ============================================
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret

# ============================================
# Telegram (선택)
# ============================================
ENABLE_TELEGRAM=false
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
SYSTEM_NAME=TRADING
```

### **4. 실행**

```bash
# 전체 시스템 실행
python main.py

# 또는 매매만 실행 (ensemble + execution)
python run_trading.py
```

---

## 🏗️ 시스템 아키텍처

### **전체 플로우**

```
┌──────────────────────────────────────────────────────┐
│ 1. collector/ (데이터 수집)                          │
│    WebSocket → 실시간 캔들 수신                      │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│ 2. indicators/ (지표 계산)                           │
│    EMA, RSI, MACD, BB, ATR, Stochastic, ADX...      │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│ 3. signals/ (신호 생성 프레임워크)                   │
│    - SignalGenerator: 전략 실행                      │
│    - 필터링: 쿨다운, 레짐, Flash Guard               │
│    - 검증 및 저장                                    │
└────────────────────┬─────────────────────────────────┘
                     ▼
┌──────────────────────────────────────────────────────┐
│ 4. strategies/ (전략 로직)                           │
│    trend, reversion, breakout, scalping,             │
│    daytrade, swing (각 전략 독립 실행)               │
└────────────────────┬─────────────────────────────────┘
                     ▼
          monitoring.signals (DB)
                     ▼
┌──────────────────────────────────────────────────────┐
│ 5. strategies/ensemble (통합)                        │
│    - 6개 신호 읽기                                    │
│    - 성과 기반 가중치 계산                            │
│    - 통합 점수 산출                                   │
│    - 최종 결정 (LONG/SHORT/FLAT)                     │
└────────────────────┬─────────────────────────────────┘
                     ▼
           trading.decisions (DB)
                     ▼
┌──────────────────────────────────────────────────────┐
│ 6. execution/ (매매 실행)                            │
│    - executor: 주문 실행                             │
│    - position_sizer: 포지션 크기 계산                │
│    - risk_manager: 리스크 체크                       │
│    - position_tracker: 포지션 추적                   │
│    - manager: 오케스트레이션                         │
└────────────────────┬─────────────────────────────────┘
                     ▼
            trading.trades (DB)
```

### **실시간 루프**

```python
while True:
    # 1. 캔들 수신 (WebSocket)
    candle = websocket_collector.receive()
    
    # 2. 6개 전략 신호 생성
    for strategy in [trend, reversion, breakout, scalping, daytrade, swing]:
        signal = strategy.signal_logic(df, config)
        save_to_monitoring_signals(signal)
    
    # 3. 주기적 실행 (5초마다)
    #    - Ensemble 통합
    ensemble.process_pending_signals()
    #    - 매매 실행
    execution_manager.process_trades(executor)
```

---

## 📂 모듈 구조

```
future_alarm_bot/
├── main.py                    # 메인 실행 파일 ⭐
├── run_trading.py             # 매매 실행 스크립트
├── init_db.sql                # DB 스키마
├── requirements.txt           # Python 패키지
├── docker-compose.yml         # Docker 설정
├── .env                       # 환경변수
│
├── collector/                 # 데이터 수집 📡
│   ├── websocket_collector.py  # WebSocket 실시간
│   └── rest_collector.py       # REST API 히스토리
│
├── indicators/                # 지표 계산 📊
│   └── technical_indicators.py # EMA, RSI, MACD, BB, ATR...
│
├── signals/                   # 신호 생성 프레임워크 🔔
│   ├── signal_generator.py     # 신호 생성 엔진
│   └── signal_storage.py       # DB 저장
│
├── strategies/                # 전략 로직 (6개 + ensemble) 🎯
│   ├── trend.py               # 추세 추종
│   ├── reversion.py           # 평균 회귀
│   ├── breakout.py            # 돌파 전략
│   ├── scalping.py            # 스캘핑
│   ├── daytrade.py            # 데이트레이딩
│   ├── swing.py               # 스윙
│   └── ensemble.py            # 앙상블 통합 ⭐
│
├── execution/                 # 매매 실행 💼
│   ├── executor.py            # 주문 실행
│   ├── position_sizer.py      # 포지션 크기 계산
│   ├── risk_manager.py        # 리스크 관리
│   ├── position_tracker.py    # 포지션 추적
│   └── manager.py             # 오케스트레이션
│
├── common/                    # 공통 모듈 🔧
│   ├── database.py            # PostgreSQL 연결
│   ├── logger.py              # 로깅
│   ├── config.py              # 설정 관리
│   ├── calculations.py        # 계산 함수
│   ├── messaging.py           # 텔레그램 알림
│   └── utils.py               # 유틸리티
│
├── backtest/                  # 백테스트 📈
│   ├── data_downloader.py
│   ├── backtest_engine.py
│   └── backtest_reporter.py
│
└── docs/                      # 문서 📚
    ├── COMPLETE/              # 최종 문서 모음 ⭐
    ├── architecture/          # 아키텍처
    ├── implementation/        # 구현 가이드
    ├── strategy/              # 전략 설명
    └── setup/                 # 설치 및 설정
```

---

## ⚙️ 설정 가이드

### **환경변수 상세**

| 변수 | 설명 | 기본값 | 예시 |
|------|------|--------|------|
| `STRATEGY_SELECTOR` | 전략 선택 | `ensemble` | `ensemble`, `trend`, `reversion` |
| `TRADING_MODE` | 거래 모드 | `paper` | `backtest`, `paper`, `live` |
| `EQUITY_USDT` | 계좌 자산 | `10000` | `10000`, `50000` |
| `RISK_PER_TRADE` | 거래당 리스크 | `0.01` | `0.005` (0.5%), `0.02` (2%) |
| `MAX_LEVERAGE` | 최대 레버리지 | `10` | `5`, `20` |
| `DAILY_LOSS_LIMIT_PCT` | 일일 손실 한도 | `0.03` | `0.02` (2%), `0.05` (5%) |
| `MAX_CONCURRENT_POSITIONS` | 최대 동시 포지션 | `5` | `3`, `10` |

### **전략 선택**

```bash
# 1. Ensemble (기본, 권장)
STRATEGY_SELECTOR=ensemble

# 2. 단일 전략
STRATEGY_SELECTOR=trend        # 추세장에 강함
STRATEGY_SELECTOR=reversion    # 횡보장에 강함
STRATEGY_SELECTOR=breakout     # 변동성 구간
```

### **모드 선택**

```bash
# 1. Backtest (과거 데이터)
TRADING_MODE=backtest

# 2. Paper (실시간 가상)
TRADING_MODE=paper

# 3. Live (실제 거래)
TRADING_MODE=live
BINANCE_API_KEY=your_key      # 필수
BINANCE_SECRET=your_secret    # 필수
```

---

## 🎮 실행 방법

### **1. 전체 시스템 (권장)**

```bash
python main.py
```

**동작**:
- WebSocket 연결
- 6개 전략 신호 생성
- Ensemble 통합
- 매매 실행

### **2. 매매만 실행**

```bash
python run_trading.py
```

**동작**:
- Ensemble 통합
- 매매 실행
(신호는 별도 프로세스에서 생성 중이어야 함)

### **3. 백테스트**

```bash
python run_backtest.py
```

**동작**:
- 과거 데이터 다운로드
- 백테스트 실행
- HTML 리포트 생성

### **4. Docker (운영 환경)**

```bash
# 전체 시스템 시작
docker-compose up -d

# 로그 확인
docker logs -f future_alarm_bot_main

# 중지
docker-compose down
```

---

## 📚 문서

### **최종 문서 (docs/COMPLETE/)**
- ✅ [README.md](docs/COMPLETE/README.md) - 전체 시스템 가이드
- ✅ [collector.md](docs/COMPLETE/modules/collector.md) - 데이터 수집 모듈
- ✅ [indicators.md](docs/COMPLETE/modules/indicators.md) - 지표 계산 모듈
- ✅ [signals.md](docs/COMPLETE/modules/signals.md) - 신호 생성 모듈
- ✅ [strategies.md](docs/COMPLETE/modules/strategies.md) - 전략 모듈
- ✅ [execution.md](docs/COMPLETE/modules/execution.md) - 매매 실행 모듈
- ✅ [common.md](docs/COMPLETE/modules/common.md) - 공통 모듈

### **아키텍처**
- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - 전체 시스템 아키텍처
- [docs/architecture/EXECUTION_MODULE.md](docs/architecture/EXECUTION_MODULE.md) - Execution 모듈
- [docs/architecture/DB_SCHEMA_GUIDE.md](docs/architecture/DB_SCHEMA_GUIDE.md) - DB 스키마

### **전략**
- [docs/strategy/ENSEMBLE_ARCHITECTURE.md](docs/strategy/ENSEMBLE_ARCHITECTURE.md) - Ensemble 설명
- [docs/strategy/6_STRATEGY_SYSTEM.md](docs/strategy/6_STRATEGY_SYSTEM.md) - 6개 전략 시스템

---

## 🛠️ 개발

### **테스트**

```bash
# 단위 테스트
pytest tests/

# 통합 테스트
python test_full_integration.py

# Execution 모듈 테스트
python test_execution_module.py
```

### **코드 스타일**

```bash
# Black 포맷팅
black .

# Flake8 린팅
flake8 .
```

---

## 📊 데이터베이스

### **스키마**

```sql
-- monitoring.signals (6개 전략 신호)
-- trading.decisions (앙상블 통합 결정)
-- trading.trades (거래 기록)
-- trading.positions (포지션 추적)
-- reporting.strategy_performance (전략 성과)
-- reporting.daily_pnl (일일 손익)
```

자세한 내용: [docs/architecture/DB_SCHEMA_GUIDE.md](docs/architecture/DB_SCHEMA_GUIDE.md)

---

## 🚨 주의사항

1. **LIVE 모드는 실제 돈을 사용합니다**
   - 반드시 BACKTEST → PAPER → LIVE 순서로 검증
   - 소액으로 시작

2. **API 키 보안**
   - `.env` 파일은 절대 공개하지 마세요
   - `.gitignore`에 포함되어 있는지 확인

3. **리스크 관리**
   - `RISK_PER_TRADE`는 1% 이하 권장
   - `DAILY_LOSS_LIMIT_PCT`는 3% 이하 권장

---

## 📝 라이선스

MIT License

---

## 🤝 기여

Issues 및 Pull Requests 환영합니다!

---

## 📧 문의

문제가 있으시면 Issue를 등록해주세요.

---

**작성일**: 2025-10-19  
**버전**: v2.0  
**상태**: ✅ 운영 준비 완료
