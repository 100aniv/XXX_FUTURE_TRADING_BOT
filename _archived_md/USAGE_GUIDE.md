# 🚀 사용 가이드

**작성일**: 2025-10-19  
**버전**: v2.0

---

## 📊 **통합 구조**

### **단일 진입점: main.py**

```
python main.py

↓ .env의 TRADING_MODE 확인

├─ backtest  → 백테스트 실행
├─ paper     → Paper Trading (실시간 가상 거래)
└─ live      → Live Trading (실제 거래)
```

---

## 🎯 **모드별 사용법**

### **1️⃣ 백테스트 모드**

**목적**: 과거 데이터로 전략 검증 및 파라미터 튜닝

**.env 설정**:
```bash
TRADING_MODE=backtest

# 백테스트 기간
BACKTEST_START_DATE=2024-07-01
BACKTEST_END_DATE=2024-10-17

# 초기 자본
EQUITY_USDT=10000
```

**실행**:
```bash
python main.py
```

**동작**:
- ✅ **6개 전략 모두 자동 실행** (scalping, daytrade, swing, trend, reversion, breakout)
- ✅ 각 전략별 최적 파라미터 적용
- ✅ 비교 테이블 출력
- ✅ 최고 성과 전략 추천

**출력 예시**:
```
전략          거래수      승률       수익률        샤프     MDD      PF
--------------------------------------------------------------------------------
SCALPING        45     62.2%      12.50%      1.85    4.2%    1.89
DAYTRADE        38     60.5%      15.30%      2.10    3.8%    2.15
SWING           28     64.3%      18.20%      2.35    5.1%    2.42
TREND           22     68.2%      22.50%      2.80    4.5%    2.85
REVERSION       40     55.0%       8.50%      1.45    6.2%    1.52
BREAKOUT        32     59.4%      14.80%      2.05    5.5%    1.98
--------------------------------------------------------------------------------

🏆 최고 성과 전략: TREND
   승률: 68.18%
   수익률: 22.50%
   샤프 비율: 2.80
```

**결과**:
- `results/strategy_comparison_YYYYMMDD_HHMMSS.json` 저장
- 6개 전략 상세 지표 포함

---

### **2️⃣ Paper Trading 모드**

**목적**: 실시간 시뮬레이션 (실제 API 연결, 주문은 시뮬레이션)

**.env 설정**:
```bash
TRADING_MODE=paper

# Binance API (필수!)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# 전략 선택
STRATEGY_SELECTOR=ensemble

# 심볼 (자동 로드)
SYMBOLS=
SYMBOL_MODE=top50

# 초기 자본
EQUITY_USDT=10000
```

**실행**:
```bash
python main.py
```

**동작**:
- 실시간 가격 수신 (WebSocket)
- 전략 신호 생성
- 가상 포지션 관리
- DB에 기록

---

### **3️⃣ Live Trading 모드**

**목적**: 실제 거래 실행 ⚠️

**.env 설정**:
```bash
TRADING_MODE=live

# Binance API (필수!)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# 전략 선택
STRATEGY_SELECTOR=ensemble

# 리스크 (신중하게!)
EQUITY_USDT=10000
RISK_PER_TRADE=0.005  # 0.5%로 낮춤
DAILY_LOSS_LIMIT_PCT=0.02  # 2%
```

**실행**:
```bash
python main.py
```

**주의**:
- ⚠️ **실제 돈이 움직입니다!**
- Paper Trading 검증 후 사용
- 소액으로 시작
- 일일 손실 한도 설정 필수

---

## 📋 **워크플로우**

### **Step 1: 백테스트로 검증**
```bash
# .env
TRADING_MODE=backtest
STRATEGY_SELECTOR=scalping

# 실행
python main.py
```

**목표**:
- 승률 60% 이상
- Sharpe Ratio 1.5 이상
- MDD 10% 이하

---

### **Step 2: 파라미터 튜닝**

**전략 파일 수정** (`strategies/scalping.py`):
```python
# 조정 가능한 파라미터
RR = 1.5  # Risk/Reward
ATR_MULT_SL = 1.0  # 손절 거리
COOLDOWN = 3  # 재진입 대기
```

**재검증**:
```bash
python main.py  # TRADING_MODE=backtest
```

**반복**: 최적 파라미터 발견까지

---

### **Step 3: Paper Trading 실전 테스트**
```bash
# .env
TRADING_MODE=paper
STRATEGY_SELECTOR=scalping  # 백테스트 통과한 전략

# 실행
python main.py
```

**기간**: 최소 1주일

**모니터링**:
```bash
# DB 확인
docker exec -it trading_db_postgres psql -U trading_user -d trading_db

# 신호 확인
SELECT * FROM monitoring.signals ORDER BY created_at DESC LIMIT 10;

# 거래 확인
SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 10;
```

---

### **Step 4: Live Trading (선택)**
```bash
# .env
TRADING_MODE=live
EQUITY_USDT=100  # 소액으로 시작!

# 실행
python main.py
```

---

## 🔧 **전략별 추천 설정**

### **Scalping (1분봉)**
```bash
STRATEGY_SELECTOR=scalping
RISK_PER_TRADE=0.015
RR=1.5
ATR_MULT_SL=1.0
```

### **Daytrade (5분봉)**
```bash
STRATEGY_SELECTOR=daytrade
RISK_PER_TRADE=0.02
RR=2.0
ATR_MULT_SL=1.2
```

### **Swing (15분봉)**
```bash
STRATEGY_SELECTOR=swing
RISK_PER_TRADE=0.02
RR=2.2
ATR_MULT_SL=1.5
```

### **Trend (1시간봉)**
```bash
STRATEGY_SELECTOR=trend
RISK_PER_TRADE=0.025
RR=2.5
ATR_MULT_SL=1.5
```

### **Ensemble (통합)**
```bash
STRATEGY_SELECTOR=ensemble
RISK_PER_TRADE=0.02
RR=2.0
```

---

## 📊 **데이터 준비 (백테스트용)**

### **다운로드**:
```bash
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17
```

### **병합**:
```bash
python backtest/data_downloader.py --merge
```

### **확인**:
```bash
ls data/
# BTCUSDT_5m_2024-07-01_2024-10-17.csv 등 확인
```

---

## 🎨 **Docker 사용**

### **시작**:
```bash
docker-compose up -d
```

### **로그 확인**:
```bash
docker logs -f future_trading_bot
```

### **DB 접속**:
```bash
docker exec -it trading_db_postgres psql -U trading_user -d trading_db
```

### **중지**:
```bash
docker-compose down
```

---

## ⚙️ **주요 설정 요약**

| 설정 | backtest | paper | live |
|------|----------|-------|------|
| **TRADING_MODE** | `backtest` | `paper` | `live` |
| **Binance API** | 불필요 | **필수** | **필수** |
| **실제 거래** | ❌ | ❌ | ✅ |
| **실시간 데이터** | ❌ | ✅ | ✅ |
| **DB 저장** | ✅ | ✅ | ✅ |

---

## 🚨 **주의사항**

### **백테스트**
- ✅ 과거 데이터 필요
- ✅ 과최적화 주의
- ✅ 실전과 차이 있음

### **Paper Trading**
- ✅ API 키 필요 (읽기 권한)
- ✅ 실시간 테스트
- ✅ 슬리피지 시뮬레이션

### **Live Trading**
- ⚠️ **실제 돈 사용**
- ⚠️ Paper 검증 후 사용
- ⚠️ 소액으로 시작
- ⚠️ 손실 한도 설정 필수

---

## 📞 **문제 해결**

### **백테스트 데이터 없음**
```bash
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17
python backtest/data_downloader.py --merge
```

### **DB 연결 실패**
```bash
docker-compose up -d
# DB가 시작될 때까지 대기 (10초)
```

### **API 키 오류**
- `.env` 파일 확인
- Binance에서 API 키 재생성
- IP 화이트리스트 확인

---

**작성자**: AI Assistant  
**최종 업데이트**: 2025-10-19
