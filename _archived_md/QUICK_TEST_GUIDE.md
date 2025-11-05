# 🚀 빠른 테스트 가이드

**통합 트레이딩 시스템 v2.0 - 테스트 방법**

---

## 📋 테스트 종류

1. **Paper Trading** (가상 거래) - 추천! ⭐
2. **Backtest** (과거 데이터)
3. **Live Trading** (실제 거래)

---

## 1️⃣ Paper Trading (실시간 가상 거래)

### **특징**
- ✅ 실제 시장 가격 사용
- ✅ 실제 계좌 연결 (API 키 필요)
- ✅ 실제 잔고 확인
- ❌ 실제 주문은 보내지 않음 (시뮬레이션)

### **준비**

1. **바이낸스 API 키 생성**
   - 읽기 전용 권한 또는 거래 권한 (선택)
   - 출금 권한은 비활성화

2. **`.env` 파일 생성:**

```bash
# Database
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db

# Strategy & Mode
STRATEGY_SELECTOR=ensemble  # 또는 trend, reversion, breakout, scalping, daytrade, swing
TRADING_MODE=paper  # ⭐ 가상 거래

# Binance API (Paper도 필요!) ⭐
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# Risk
EQUITY_USDT=10000
RISK_PER_TRADE=0.01

# Symbols
SYMBOLS=BTCUSDT,ETHUSDT
TIMEFRAME=5m
LOOKBACK=400

# Telegram (선택)
ENABLE_TELEGRAM=false
```

### **실행**

#### 로컬 (Python)
```bash
# 가상환경 활성화
.\trading_bot_env\Scripts\activate

# 실행
python main.py
```

#### Docker
```bash
# DB 시작
docker-compose up -d postgres_db

# 메인 봇 시작
docker-compose up -d future_trading_bot

# 로그 확인
docker logs -f xxx_trading_bot_future_trading_bot
```

### **확인**

```bash
# 실시간 로그
tail -f logs/application/2025-10-19.log
tail -f logs/trading/2025-10-19.log

# DB 확인
docker exec -it xxx_trading_bot_postgres_db psql -U trading_user -d trading_db

# 신호 확인
SELECT * FROM monitoring.signals ORDER BY created_at DESC LIMIT 10;

# 거래 확인
SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 10;
```

---

## 2️⃣ Backtest (과거 데이터)

### **데이터 다운로드**

```bash
# 과거 데이터 다운로드 (7일~3개월 권장)
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# 데이터 병합
python backtest/data_downloader.py --merge
```

### **백테스트 실행**

```bash
# 단일 전략
python run_backtest.py --strategy ensemble --start 2024-07-01 --end 2024-10-17

# 모든 전략 비교
python run_backtest.py --strategy all --start 2024-07-01 --end 2024-10-17

# 자본금 설정
python run_backtest.py --strategy scalping --capital 50000
```

### **결과 확인**

```bash
# 결과 파일
ls -l results/
ls -l reports/

# HTML 리포트 (브라우저에서 열기)
open reports/ensemble_backtest_20251019_*.html
```

---

## 3️⃣ Live Trading (실제 거래)

### **⚠️ 경고**

- **반드시 Paper Trading 테스트 후 진행!**
- **소액으로 시작!**
- **API 키 보안 주의!**

### **준비**

1. 바이낸스 API 키 생성
   - Futures Trading 권한만 활성화
   - 출금 권한은 비활성화

2. `.env` 파일 수정:

```bash
# Mode 변경
TRADING_MODE=live  # ⚠️ 실제 거래

# API 키 추가
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# 리스크 낮게 설정
EQUITY_USDT=1000  # 소액으로 시작
RISK_PER_TRADE=0.005  # 0.5%
MAX_CONCURRENT_POSITIONS=2
```

### **실행**

```bash
python main.py
```

### **모니터링**

```bash
# 실시간 로그
tail -f logs/trading/2025-10-19.log

# 포지션 확인
SELECT * FROM trading.positions WHERE status = 'OPEN';

# 오늘 거래 내역
SELECT * FROM trading.trades 
WHERE created_at >= CURRENT_DATE 
ORDER BY created_at DESC;

# 오늘 손익
SELECT 
  SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
  SUM(pnl) as total_pnl
FROM trading.trades 
WHERE created_at >= CURRENT_DATE;
```

---

## 🔍 문제 해결

### Q: "DB 연결 실패"

```bash
# Docker DB 시작
docker-compose up -d postgres_db

# 연결 확인
docker exec -it xxx_trading_bot_postgres_db pg_isready -U trading_user

# 포트 확인
netstat -ano | findstr :5433  # Windows
lsof -i :5433  # Linux/Mac
```

### Q: "신호가 생성되지 않습니다"

```bash
# 로그 확인
tail -f logs/signals/2025-10-19.log

# WebSocket 연결 확인
grep "WebSocket" logs/application/2025-10-19.log

# 버퍼 확인 (최소 50개 캔들 필요)
```

### Q: "백테스트 데이터가 없습니다"

```bash
# 데이터 다운로드
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# 데이터 확인
ls -l data/
```

---

## ✅ 체크리스트

### Paper Trading 시작 전
- [ ] `.env` 파일 생성
- [ ] `TRADING_MODE=paper` 설정
- [ ] PostgreSQL 실행 중
- [ ] 가상환경 활성화

### Backtest 실행 전
- [ ] 과거 데이터 다운로드
- [ ] `data/` 폴더에 CSV 파일 확인
- [ ] 백테스트 기간 설정

### Live Trading 시작 전
- [ ] Paper Trading 최소 1주일 테스트
- [ ] API 키 생성 (거래 권한만)
- [ ] 리스크 낮게 설정
- [ ] 소액으로 시작

---

## 📊 성능 평가

### 좋은 결과
```
✅ 승률 > 50%
✅ RR > 1.5
✅ Sharpe > 1.0
✅ 최대 손실 < 10%
```

### 주의 필요
```
⚠️ 승률 < 40%
⚠️ 연속 손실 > 5회
⚠️ 일일 손실 > 3%
```

---

**작성일**: 2025-10-19  
**버전**: v2.0
