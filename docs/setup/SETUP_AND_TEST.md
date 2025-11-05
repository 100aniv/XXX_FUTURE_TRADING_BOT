# 🚀 시스템 설정 및 테스트 가이드

**목적**: 실제로 동작하는지 확인하고 문제점 찾기

---

## ✅ **1단계: Conda 가상환경 설정 (5분)**

```bash
# 스크립트 실행
setup_conda_env.bat

# 확인
conda activate trading_bot
python --version
pip list
```

---

## ✅ **2단계: 환경 변수 설정 (3분) ⭐ 중요!**

### **API 키 설정**

```bash
# 1. env.example을 복사
copy env.example .env

# 2. .env 파일 수정
notepad .env
```

### **.env 파일 예시** (백테스트용)

```ini
# 전략 & 모드
STRATEGY_SELECTOR=scalping
TRADING_MODE=backtest

# 데이터베이스
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db

# Binance API (백테스트는 불필요, Live는 필수!)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here

# 리스크
EQUITY_USDT=10000
RISK_PER_TRADE=0.01
MAX_POSITIONS=5
```

---

## ✅ **3단계: PostgreSQL 시작**

```bash
# PostgreSQL만 시작
docker-compose up -d postgres

# 확인
docker ps
```

---

## ✅ **4단계: 시그널 봇 테스트**

```bash
conda activate trading_bot
python telegram_signal_bot.py
```

**확인:**
- [ ] 봇 시작됨
- [ ] Telegram 연결 성공
- [ ] 에러 없음

---

## ✅ **5단계: Trading Manager 테스트**

```bash
conda activate trading_bot
python trading_manager.py
```

**확인:**
- [ ] "Trading Bot 시작" 출력
- [ ] 신호 조회 시도
- [ ] 에러 없음

---

## ❌ **알려진 문제점**

### **1. 앙상블 결정에 entry/sl/tp 없음**

trading_manager.py 라인 218:
```python
logger.warning("⚠️  앙상블 결정은 entry/sl/tp 계산 필요")
return None
```

**해결:** 개별 전략 사용 (scalping, trend 등)

### **2. PositionTracker 미사용**

trading_executor.py에서 초기화만 되고 실제 사용 안함

**필요:** execute_order 후 position_tracker.add_position() 호출

---

## 📝 **다음 단계**

1. 위 테스트 순서대로 실행
2. 문제점 기록
3. 수정 후 재테스트
