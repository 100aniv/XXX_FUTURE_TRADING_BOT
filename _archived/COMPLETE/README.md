# 📚 완전 문서 모음

**통합 트레이딩 시스템 v2.0 - 최종 문서**

**작성일**: 2025-10-19  
**상태**: ✅ 완성

---

## 📋 문서 목록

### **모듈별 문서**
- ✅ [collector.md](modules/collector.md) - 데이터 수집 모듈
- ✅ [indicators.md](modules/indicators.md) - 지표 계산 모듈
- ✅ [signals.md](modules/signals.md) - 신호 생성 모듈
- ✅ [strategies.md](modules/strategies.md) - 전략 모듈 (6개 + ensemble)
- ✅ [execution.md](modules/execution.md) - 매매 실행 모듈
- ✅ [common.md](modules/common.md) - 공통 모듈

---

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/yourname/future_alarm_bot.git
cd future_alarm_bot

# 가상환경
python -m venv trading_bot_env
.\trading_bot_env\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. DB 초기화

```bash
docker-compose up -d postgres
psql -U trading_user -d trading_db -f init_db.sql
```

### 3. 환경변수

`.env` 파일:
```bash
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db
STRATEGY_SELECTOR=ensemble
TRADING_MODE=paper
EQUITY_USDT=10000
RISK_PER_TRADE=0.01
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=5m
```

### 4. 실행

```bash
python main.py
```

---

## 🏗️ 전체 아키텍처

```
main.py
  ↓
collector → indicators → signals → strategies → execution
  ↓           ↓           ↓          ↓            ↓
WebSocket   EMA/RSI    신호생성    6개전략      주문실행
            MACD/BB               ensemble
```

---

## 📊 데이터 플로우

```
1. WebSocket 캔들 수신
   ↓
2. 지표 계산 (EMA, RSI, MACD, BB, ATR...)
   ↓
3. 6개 전략 신호 생성
   ↓
4. monitoring.signals 저장
   ↓
5. Ensemble 통합
   ↓
6. trading.decisions 저장
   ↓
7. Execution 실행
   ↓
8. trading.trades 저장
```

---

## 🎯 6개 전략

| 전략 | 타임프레임 | 특징 |
|------|-----------|------|
| Trend | 1h | 추세 추종 |
| Reversion | 5m | 평균 회귀 |
| Breakout | 15m | 변동성 돌파 |
| Scalping | 1m | 스캘핑 |
| Daytrade | 5m | 데이트레이딩 |
| Swing | 15m | 스윙 |

---

## 💼 Ensemble 통합

**가중치 공식**:
```python
weight = α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐
```

**최종 결정**:
```python
if score > 0.15:  LONG
elif score < -0.15:  SHORT
else:  FLAT
```

---

## 🛡️ 리스크 관리

- ✅ 일일 손실 한도 (3%)
- ✅ 동시 포지션 제한 (5개)
- ✅ 심볼별 노출 한도 (30%)
- ✅ Flash Guard (급등락 감지)

---

## 🎮 실행 모드

| 모드 | 설명 | 사용 |
|------|------|------|
| BACKTEST | 과거 데이터 | 전략 검증 |
| PAPER | 가상 거래 | 실전 전 테스트 |
| LIVE | 실제 거래 | 운영 |

---

## 📝 환경변수 전체 목록

```bash
# === Database ===
DATABASE_URL=postgresql://...

# === Trading ===
STRATEGY_SELECTOR=ensemble  # ensemble | trend | reversion | ...
TRADING_MODE=paper         # backtest | paper | live
EQUITY_USDT=10000
RISK_PER_TRADE=0.01        # 1%

# === Risk Management ===
DAILY_LOSS_LIMIT_PCT=0.03  # 3%
MAX_CONCURRENT_POSITIONS=5
MAX_EXPOSURE_PER_SYMBOL_PCT=0.3  # 30%

# === Symbols ===
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=5m
LOOKBACK=400

# === Strategy Parameters ===
RR=1.8
ATR_MULT_SL=1.2
MAX_LEVERAGE=10
MIN_LEVERAGE=2

# === Binance (LIVE only) ===
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# === Telegram (optional) ===
ENABLE_TELEGRAM=false
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
SYSTEM_NAME=TRADING

# === Filters ===
COOLDOWN_CANDLES=3
ENABLE_REGIME_ALERT=true
ENABLE_VOL_SPIKE_FILTER=true
ENABLE_MTF_CONFIRM=true
```

---

## 🔍 디버깅

### 로그 위치
```
logs/
├── application/  # 일반 로그
├── signals/      # 신호 생성
├── trading/      # 매매 실행
└── errors/       # 에러 전용
```

### DB 확인
```sql
-- 신호 확인
SELECT * FROM monitoring.signals ORDER BY created_at DESC LIMIT 10;

-- 결정 확인
SELECT * FROM trading.decisions ORDER BY created_at DESC LIMIT 10;

-- 거래 확인
SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 10;
```

---

## ⚠️ 주의사항

### LIVE 모드
1. **반드시 순서 준수**: BACKTEST → PAPER → LIVE
2. **소액으로 시작**: 처음엔 최소 금액
3. **API 키 보안**: `.env` 파일 절대 공개 금지
4. **거래 권한만**: API 키에 출금 권한 부여하지 마세요

### 리스크 설정
- `RISK_PER_TRADE`: 1% 이하 권장
- `DAILY_LOSS_LIMIT_PCT`: 3% 이하 권장
- 처음엔 보수적으로 설정

---

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📧 지원

- **Issues**: GitHub Issues
- **문서**: 이 문서 참고
- **로그**: `logs/` 폴더 확인

---

## 📚 추가 문서

### 프로젝트 루트
- [README.md](../../README.md) - 메인 README
- [SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md) - 전체 아키텍처

### docs/architecture/
- DB_SCHEMA_GUIDE.md - 데이터베이스 스키마
- EXECUTION_MODULE.md - Execution 모듈 상세

### docs/strategy/
- ENSEMBLE_ARCHITECTURE.md - Ensemble 상세
- 6_STRATEGY_SYSTEM.md - 6개 전략 시스템

---

## ✅ 체크리스트

### 시작 전
- [ ] Python 3.9+ 설치
- [ ] PostgreSQL 설치/Docker
- [ ] `.env` 파일 생성
- [ ] DB 스키마 초기화

### BACKTEST 모드
- [ ] 과거 데이터 다운로드
- [ ] 백테스트 실행
- [ ] 결과 분석

### PAPER 모드
- [ ] 실시간 연결 테스트
- [ ] 가상 거래 모니터링
- [ ] 1주일 이상 관찰

### LIVE 모드
- [ ] API 키 생성 (거래 권한만)
- [ ] 소액으로 시작
- [ ] 실시간 모니터링

---

**최종 업데이트**: 2025-10-19  
**버전**: v2.0  
**상태**: ✅ 완성
