# 🤖 트레이딩 봇 사양 (D+2 구현 예정)

**작성일**: 2025-10-14  
**버전**: v1.0

---

## 🎯 핵심 기능

### **1. 전략 선택 (4가지)**

트레이딩 봇은 신호 소스를 선택할 수 있습니다:

| 전략 ID | 설명 | 소스 |
|---------|------|------|
| **ensemble** (기본) | 통합(앙상블) 신호 - 3전략 가중치 합산 | `trading.decisions` |
| **scalping** | 스캘핑 전략만 | `monitoring.signals` (strategy_id='scalping') |
| **daytrade** | 단타 전략만 | `monitoring.signals` (strategy_id='daytrade') |
| **swing** | 스윙 전략만 | `monitoring.signals` (strategy_id='swing') |

#### **환경변수 설정**
```bash
STRATEGY_SELECTOR=ensemble   # 기본값 (추천)
# 또는
STRATEGY_SELECTOR=scalping
STRATEGY_SELECTOR=daytrade
STRATEGY_SELECTOR=swing
```

---

### **2. 매매 모드 (3가지)**

| 모드 | 설명 | 실제 주문 | 용도 |
|------|------|-----------|------|
| **BACKTEST** | 백테스팅 | ❌ | 과거 데이터로 전략 검증 |
| **DRY_RUN** | 드라이런 (페이퍼 트레이딩) | ❌ | 실시간이지만 가상 매매 |
| **LIVE** | 실전 매매 | ✅ | 실제 주문 실행 (위험!) |

#### **환경변수 설정**
```bash
TRADING_MODE=DRY_RUN   # 기본값 (안전)
# 또는
TRADING_MODE=BACKTEST
TRADING_MODE=LIVE      # ⚠️ 주의: 실제 돈 사용!
```

---

## 📋 실행 예시

### **예시 1: 앙상블 + 드라이런 (기본, 안전)**
```bash
STRATEGY_SELECTOR=ensemble
TRADING_MODE=DRY_RUN
```
- 통합 신호를 받아서
- 가상 매매 (실제 주문 없음)

### **예시 2: 스캘핑만 + 실전**
```bash
STRATEGY_SELECTOR=scalping
TRADING_MODE=LIVE
```
- 스캘핑 전략 신호만 받아서
- **실제 매매 실행** (위험!)

### **예시 3: 단타 + 백테스트**
```bash
STRATEGY_SELECTOR=daytrade
TRADING_MODE=BACKTEST
START_DATE=2025-01-01
END_DATE=2025-10-14
```
- 단타 전략으로
- 과거 데이터 시뮬레이션

---

## 🔄 런타임 전환

### **텔레그램 명령어로 전환 (예정)**
```
/set_strategy ensemble   # 전략 전환
/set_strategy scalping

/set_mode DRY_RUN        # 모드 전환
/set_mode LIVE
```

### **전환 시 동작**
- **전략 전환**: 다음 신호부터 새 전략 적용
- **모드 전환**: 
  - `LIVE` → `DRY_RUN`: 즉시 적용, 기존 포지션 유지
  - `DRY_RUN` → `LIVE`: 경고 후 확인 필요

---

## ⚠️ 안전 가이드

### **LIVE 모드 사용 전 체크리스트**
- [ ] `DRY_RUN`에서 최소 1주일 테스트
- [ ] 일손실 한도 설정 확인 (`MAX_DAILY_LOSS`)
- [ ] API 키 권한 확인 (필요한 권한만)
- [ ] 초기 자본 소액으로 시작
- [ ] 긴급 중단 명령 테스트 (`/stop`)

### **권장 순서**
1. ✅ **BACKTEST**: 과거 데이터로 전략 검증
2. ✅ **DRY_RUN**: 실시간이지만 가상 매매 (1-2주)
3. ✅ **LIVE (소액)**: 실제 매매 (소액으로 시작)
4. ✅ **LIVE (전액)**: 안정성 확인 후 전액 투입

---

## 🔧 환경변수 전체 예시

```bash
# .env.trading_bot

# === 전략 선택 ===
STRATEGY_SELECTOR=ensemble   # ensemble | scalping | daytrade | swing

# === 매매 모드 ===
TRADING_MODE=DRY_RUN        # BACKTEST | DRY_RUN | LIVE

# === 백테스트 설정 (BACKTEST 모드 전용) ===
BACKTEST_START_DATE=2025-01-01
BACKTEST_END_DATE=2025-10-14
BACKTEST_INITIAL_CAPITAL=10000

# === 리스크 관리 ===
MAX_DAILY_LOSS=-0.03        # 일손실 -3% 도달 시 중단
MAX_CONSECUTIVE_LOSSES=3    # 연속 3회 손실 시 쿨다운
RISK_PER_TRADE=0.01         # 거래당 리스크 1%

# === Binance API ===
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# === PostgreSQL ===
DATABASE_URL=postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db

# === Telegram ===
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 📊 예상 구조

```
future_alarm_bot/
├── telegram_signal_bot.py      # 모니터링 봇 (현재)
├── ensemble_bot.py             # 통합 봇 (D+1)
├── trading_bot.py              # 집행 봇 (D+2) ⭐
├── init_db.sql
├── docker-compose.yml
└── .env.trading_bot
```

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14  
**구현 예정**: D+2 (모레)
