# 🚀 배포 체크리스트 - 6개 전략 시스템

**마지막 업데이트**: 2025-10-15  
**상태**: ✅ 배포 준비 완료

---

## 📋 **사전 요구사항**

### **1. 시스템 환경**
- [x] Docker 설치 및 실행 중
- [x] Docker Compose 설치
- [x] 네트워크 연결 (바이낸스 API 접근)
- [x] Python 3.11+ (로컬 테스트용, 선택)

### **2. 텔레그램 봇 생성**
- [x] @BotFather에서 6개 봇 생성
  - [x] Scalping Bot (기존)
  - [x] Daytrade Bot (기존)
  - [x] Swing Bot (기존)
  - [x] Trend Bot (신규)
  - [x] Reversion Bot (신규)
  - [x] Breakout Bot (신규)
- [x] 각 봇의 TOKEN 저장
- [x] CHAT_ID 확인 (`/start` 후 `https://api.telegram.org/bot<TOKEN>/getUpdates`)

---

## ✅ **코드 검증 체크리스트**

### **필수 기능 (모든 봇 공통)**

| 기능 | telegram_signal_bot.py | signal_bot_trend.py | signal_bot_reversion.py | signal_bot_breakout.py |
|------|------------------------|---------------------|-------------------------|------------------------|
| **load_dotenv()** | ✅ | ✅ | ✅ | ✅ |
| **DB 연결** | ✅ | ✅ | ✅ | ✅ |
| **save_signal_to_db** | ✅ | ✅ | ✅ | ✅ |
| **ON CONFLICT 멱등성** | ✅ | ✅ | ✅ | ✅ |
| **텔레그램 전송** | ✅ | ✅ | ✅ | ✅ |
| **WebSocket** | ✅ | ✅ | ✅ | ✅ |
| **지표 계산** | ✅ | ✅ | ✅ | ✅ |
| **신호 생성 로직** | ✅ | ✅ | ✅ | ✅ |
| **로깅 (UTF-8)** | ✅ | ✅ | ✅ | ✅ |
| **에러 핸들링** | ✅ | ✅ | ✅ | ✅ |

---

## 🔧 **설정 파일 체크리스트**

### **Config 파일 (템플릿)**
- [x] config_scalp.txt
- [x] config_intraday.txt
- [x] config_swing.txt
- [x] config_trend.txt
- [x] config_reversion.txt
- [x] config_breakout.txt

### **.env 파일 (실제 사용)**
- [x] .env.scalp
- [x] .env.intraday
- [x] .env.swing
- [x] .env.trend
- [x] .env.reversion
- [x] .env.breakout

### **환경변수 필수 항목**
각 .env 파일에 다음 항목이 있어야 함:
```bash
# 필수
TELEGRAM_TOKEN=<YOUR_BOT_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
BOT_NAME=<SCALP|DAYTRADE|SWING|TREND|REVERSION|BREAKOUT>
STRATEGY_ID=<scalping|daytrade|swing|trend|reversion|breakout>
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT
TIMEFRAME=<1m|5m|15m|1h>
EQUITY_USDT=7000
RISK_PER_TRADE=<0.003-0.005>

# 선택 (전략별 상이)
RR=<1.5-2.0>
ATR_MULT_SL=<1.0-1.5>
MAX_LEVERAGE=<5-7>
MIN_LEVERAGE=2
LOOKBACK=400
```

---

## 🐳 **Docker 설정 체크리스트**

### **Dockerfile**
- [x] Python 3.11-slim 베이스
- [x] requirements.txt 복사
- [x] 모든 signal_bot_*.py 파일 복사
- [x] telegram_signal_bot.py 복사
- [x] UTF-8 인코딩 지원

### **docker-compose.yml**
- [x] PostgreSQL 컨테이너
- [x] 6개 전략 봇 컨테이너
  - [x] scalp-bot
  - [x] intraday-bot
  - [x] swing-bot
  - [x] trend-bot
  - [x] reversion-bot
  - [x] breakout-bot
- [x] ensemble-bot 컨테이너
- [x] 각 봇에 env_file 설정
- [x] DATABASE_URL 환경변수 설정
- [x] depends_on: postgres (healthcheck)
- [x] restart: unless-stopped
- [x] logs 볼륨 마운트

### **네트워크 설정**
- [x] bot-network 생성
- [x] 모든 컨테이너 동일 네트워크

---

## 🗄️ **데이터베이스 체크리스트**

### **스키마 생성**
- [x] monitoring 스키마
- [x] trading 스키마

### **테이블**
- [x] monitoring.signals
  - [x] UNIQUE (strategy_id, symbol, timeframe, candle_closed_at)
- [x] trading.decisions
- [x] trading.executions
- [x] trading.positions
- [x] trading.performance

### **인덱스**
- [x] monitoring.signals: (symbol, created_at)
- [x] monitoring.signals: (strategy_id, created_at)

---

## 🚀 **배포 절차**

### **1. 사전 준비**
```bash
# 저장소 클론 (또는 최신 pull)
git pull origin main

# 환경 확인
docker --version
docker-compose --version
```

### **2. 환경변수 설정**
```bash
# Config 파일에서 .env 파일 생성
cp config_trend.txt .env.trend
cp config_reversion.txt .env.reversion
cp config_breakout.txt .env.breakout

# 텔레그램 토큰 입력 (각 파일 편집)
# TELEGRAM_TOKEN=<YOUR_TOKEN>
# TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
```

### **3. Docker 빌드**
```bash
# 전체 빌드
docker-compose build --no-cache

# 특정 봇만 빌드
docker-compose build trend-bot reversion-bot breakout-bot
```

### **4. DB 초기화** (첫 실행 시)
```bash
# PostgreSQL 시작
docker-compose up -d postgres

# DB 생성 확인
docker exec future_alarm_bot_postgres psql -U trading_user -d trading_db -c "\dt monitoring.*"
```

### **5. 봇 시작**
```bash
# 전체 시작
docker-compose up -d

# 특정 봇만 시작
docker-compose up -d trend-bot reversion-bot breakout-bot ensemble-bot
```

### **6. 상태 확인**
```bash
# 컨테이너 상태
docker ps

# 로그 확인
docker logs signal_bot_trend --tail=50
docker logs signal_bot_reversion --tail=50
docker logs signal_bot_breakout --tail=50

# DB 신호 확인
docker exec future_alarm_bot_postgres psql -U trading_user -d trading_db \
  -c "SELECT strategy_id, COUNT(*) FROM monitoring.signals GROUP BY strategy_id;"
```

---

## 🔍 **검증 테스트**

### **1. 텔레그램 알림 테스트**
각 봇에서 다음 메시지가 와야 함:
```
🟢 [TREND] BTCUSDT — TREND 신호
💡 이유: EMA 상승 정렬 + MACD 양수
📍 진입가: 45000.00
🎯 목표가: 46500.00
🛑 손절가: 44000.00
⚡ 레버리지: 5x
```

### **2. DB 저장 테스트**
```sql
-- 최근 신호 확인
SELECT 
  strategy_id, 
  symbol, 
  direction, 
  confidence,
  TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM monitoring.signals
ORDER BY created_at DESC
LIMIT 20;
```

### **3. 멱등성 테스트**
```sql
-- 중복 체크 (같은 strategy_id, symbol, timeframe, candle_closed_at는 1개만)
SELECT 
  strategy_id, 
  symbol, 
  timeframe, 
  candle_closed_at,
  COUNT(*) as cnt
FROM monitoring.signals
GROUP BY strategy_id, symbol, timeframe, candle_closed_at
HAVING COUNT(*) > 1;
-- 결과: 0 rows (중복 없음)
```

### **4. WebSocket 연결 테스트**
```bash
# 로그에서 WebSocket 연결 확인
docker logs signal_bot_trend 2>&1 | grep "WebSocket"
# 출력: "WebSocket 연결 성공"
```

---

## 🚨 **트러블슈팅**

### **문제 1: 텔레그램 메시지 안옴**
```bash
# 로그 확인
docker logs signal_bot_trend 2>&1 | grep "TELEGRAM"

# 가능한 원인:
# 1. TELEGRAM_TOKEN 오류 → .env 파일 확인
# 2. CHAT_ID 오류 → getUpdates로 확인
# 3. 네트워크 차단 → 방화벽 확인
```

### **문제 2: DB 연결 실패**
```bash
# PostgreSQL 상태 확인
docker ps | grep postgres

# DB 로그 확인
docker logs future_alarm_bot_postgres

# 재시작
docker-compose restart postgres
```

### **문제 3: 신호 생성 안됨**
```bash
# 캔들 수신 확인
docker logs signal_bot_trend 2>&1 | grep "캔들"

# 바이낸스 연결 확인
docker logs signal_bot_trend 2>&1 | grep "Binance"
```

### **문제 4: 한글 깨짐**
```bash
# 로그 인코딩 확인
docker logs signal_bot_trend 2>&1 | head -20

# 해결: 모든 .py 파일 UTF-8 인코딩 확인
# -*- coding: utf-8 -*-
```

---

## 📊 **성과 모니터링**

### **일일 체크**
```sql
-- 오늘 신호 개수
SELECT 
  strategy_id,
  COUNT(*) as signals,
  COUNT(DISTINCT symbol) as symbols
FROM monitoring.signals
WHERE created_at >= CURRENT_DATE
GROUP BY strategy_id;
```

### **주간 체크**
```sql
-- 전략별 신뢰도 평균
SELECT 
  strategy_id,
  AVG(confidence) as avg_confidence,
  COUNT(*) as total_signals
FROM monitoring.signals
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY strategy_id;
```

---

## ✅ **최종 확인**

### **배포 전 체크리스트**
- [ ] 모든 .env 파일에 텔레그램 토큰 입력
- [ ] Docker 컨테이너 정상 실행 (`docker ps`)
- [ ] PostgreSQL 연결 성공 (로그 확인)
- [ ] 6개 봇 모두 WebSocket 연결 (`docker logs`)
- [ ] DB에 신호 저장됨 (SQL 확인)
- [ ] 텔레그램 알림 수신 (각 봇)
- [ ] 로그 파일 정상 생성 (`./logs/`)

### **배포 후 모니터링**
- [ ] 1시간 후: 신호 생성 확인
- [ ] 24시간 후: 일일 리포트 확인
- [ ] 7일 후: 주간 성과 분석

---

**작성자**: AI Assistant  
**버전**: 1.0  
**상태**: ✅ 검증 완료
