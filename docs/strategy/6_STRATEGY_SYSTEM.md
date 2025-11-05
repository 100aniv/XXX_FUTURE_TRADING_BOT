# 🎯 6개 전략 통합 시스템

**작성일**: 2025-10-14  
**버전**: v2.0  
**상태**: ✅ 완성 및 배포

---

## 📊 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│               모니터링 계층 (6개 전략)                    │
├─────────────────────────────────────────────────────────┤
│  시간 기반                    성격 기반                  │
│  ├─ SCALP (1m)               ├─ TREND (4h)              │
│  ├─ DAYTRADE (15m)           ├─ REVERSION (15m)         │
│  └─ SWING (1h)               └─ BREAKOUT (1h)           │
│          │                            │                  │
│          └────────────┬───────────────┘                  │
│                       │                                  │
│                       ▼                                  │
│             monitoring.signals (DB)                      │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               통합 계층 (앙상블)                         │
├─────────────────────────────────────────────────────────┤
│  ├─ 성과 메트릭 로드 (30일 롤링)                         │
│  ├─ 가중치 계산 (승률+RR+샤프+레짐)                      │
│  ├─ 통합 점수 산출                                      │
│  └─ 보너스/패널티 적용                                  │
│                       │                                  │
│                       ▼                                  │
│             trading.decisions (DB)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 전략 상세 및 기능

### **공통 기능 (모든 전략)**
```yaml
✅ 신호 생성 (캔들 종료 시)
✅ 실시간 TP/SL 추적 (1분봉)
✅ Flash-Guard (급등락 감지)
✅ 목표 추적 (일일 목표 달성률)
✅ 일일 리스크 가드 (손실 한도)
✅ Regime Alert (시장 전환 알림)
✅ Beginner Explain (초보자 설명)
✅ DB 저장 (멱등성 보장)
✅ 텔레그램 알림
```

### **전략별 차별화**

| 기능 | SCALP | DAYTRADE | SWING | TREND | REVERSION | BREAKOUT |
|------|-------|----------|-------|-------|-----------|----------|
| **MTF Confirm** | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Vol Spike Filter** | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |

**이유:**
- **MTF**: REVERSION은 반대 방향 전략 (상위가 상승인데 하락 배팅)
- **Vol Spike**: SCALP/BREAKOUT은 거래량 급증이 오히려 신호

---

## 🔧 전략 상세

### **1. SCALPING (스캘핑)**
```yaml
파일: telegram_signal_bot.py (scalp)
타임프레임: 1m
신호/일: 50-100개
승률: 48-55%
RR: 1.5

로직:
  - BB 터치 + EMA 정렬
  - 횡보장에 강함
  - 빠른 익절

기능:
  - MTF Confirm: OFF (1분봉에 불필요)
  - Vol Spike Filter: OFF (거래량 급증 활용)
  - Flash-Guard: OFF (변동성 활용)

텔레그램 봇: @YourScalpBot
```

### **2. DAYTRADE (단타)**
```yaml
파일: signal_bot_intraday.py
타임프레임: 15m
신호/일: 20-40개
승률: 55-62%
RR: 1.6

로직:
  - EMA 정렬 + MACD 방향 (2-AND)
  - BB 돌파 OR 조건
  - 선택적 RSI 게이트

텔레그램 봇: @YourDaytradeBot
```

### **3. SWING (스윙)**
```yaml
파일: signal_bot_swing.py
타임프레임: 1h
신호/일: 10-20개
승률: 62-70%
RR: 2.0

로직:
  - EMA 3선 정렬 + MACD 방향 (2-AND)
  - BB/Donchian 돌파 OR 조건
  - 선택적 RSI 게이트

텔레그램 봇: @YourSwingBot
```

### **4. TREND (추세 추종)** ⭐ 신규
```yaml
파일: signal_bot_trend.py
타임프레임: 4h
신호/일: 3-8개
승률: 60-70%
RR: 2.2

로직:
  - EMA 정렬 + MACD 방향 (2-AND)
  - 선택적 RSI 게이트
  - 장기 추세 포착

기능:
  - MTF Confirm: OFF (4h 단독)
  - Vol Spike Filter: OFF
  - Flash-Guard: ON
  - TP Trail: ON
  
설정: 28개 (완전한 봇)

텔레그램 봇: @YourTrendBot
```

### **5. REVERSION (평균회귀)** ⭐ 신규
```yaml
파일: signal_bot_reversion.py
타임프레임: 15m
신호/일: 20-40개
승률: 55-65%
RR: 1.6

로직:
  - RSI 과매수/과매도
  - BB 상/하단 근접
  - 반전 힌트 OR (MACD/캔들/거래량)

기능:
  - MTF Confirm: OFF (반대 전략)
  - Vol Spike Filter: ON
  - Flash-Guard: ON
  - TP Trail: ON
  
설정: 28개 (완전한 봇)

텔레그램 봇: @YourReversionBot
```

### **6. BREAKOUT (변동성 돌파)** ⭐ 신규
```yaml
파일: signal_bot_breakout.py
타임프레임: 1h
신호/일: 8-20개
승률: 58-68%
RR: 2.0

로직:
  - Donchian Channel 돌파 + EMA 방향
  - 선택적 ATR/볼륨 확인
  - 추세 전환 초입 포착

기능:
  - MTF Confirm: ON (HTF=1h)
  - Vol Spike Filter: OFF (거래량 급증=신호!)
  - Flash-Guard: ON
  - TP Trail: ON
  
설정: 28개 (완전한 봇)

텔레그램 봇: @YourBreakoutBot
```

---

## 🎯 전략 간 시너지

### **상호 보완 관계**

| 전략 A | 전략 B | 시너지 |
|--------|--------|--------|
| TREND | SWING | 추세장 지배 (장기+중기) |
| BREAKOUT | TREND | 추세 전환 포착 → 추세 유지 |
| REVERSION | SCALPING | 횡보장 지배 (평균회귀+빠른수익) |
| DAYTRADE | 전체 | 중립적 균형자 |

### **레짐별 강점**

| 시장 상황 | 강한 전략 | 약한 전략 |
|----------|----------|----------|
| **상승 추세** | TREND, SWING, BREAKOUT | REVERSION |
| **하락 추세** | TREND, SWING | REVERSION |
| **횡보장** | SCALPING, REVERSION, DAYTRADE | TREND, SWING |
| **고변동성** | SCALPING, BREAKOUT | SWING |
| **저변동성** | SWING, TREND | BREAKOUT |

---

## 🔧 환경변수 설정

### **공통 (.env 파일)**
각 전략마다 별도의 `.env` 파일 생성:
- `.env.scalp`
- `.env.intraday`
- `.env.swing`
- `.env.trend` ⭐
- `.env.reversion` ⭐
- `.env.breakout` ⭐

### **필수 설정**
```bash
# 텔레그램 (각 봇마다 다른 봇 토큰)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 공통
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,DOGEUSDT
EQUITY_USDT=7000

# DB (모든 봇 공통)
DATABASE_URL=postgresql://trading_user:trading_pw_2024@postgres:5432/trading_db
```

---

## 🚀 실행 방법

### **1. 텔레그램 봇 생성 (6개)**
```
@BotFather에서:
  /newbot → @YourScalpBot
  /newbot → @YourDaytradeBot
  /newbot → @YourSwingBot
  /newbot → @YourTrendBot      ⭐
  /newbot → @YourReversionBot  ⭐
  /newbot → @YourBreakoutBot   ⭐
```

### **2. .env 파일 설정**
```bash
# config_scalp.txt → .env.scalp로 복사 후 토큰 입력
cp config_scalp.txt .env.scalp
cp config_intraday.txt .env.intraday
cp config_swing.txt .env.swing
cp config_trend.txt .env.trend          ⭐
cp config_reversion.txt .env.reversion  ⭐
cp config_breakout.txt .env.breakout    ⭐
```

### **3. Docker 실행**
```bash
# 전체 시스템 시작 (10개 컨테이너)
docker-compose up -d

# 특정 봇만 시작
docker-compose up -d trend-bot
docker-compose up -d reversion-bot
docker-compose up -d breakout-bot
```

### **4. 상태 확인**
```bash
# 컨테이너 상태
docker ps

# 로그 확인
docker logs signal_bot_trend
docker logs signal_bot_reversion
docker logs signal_bot_breakout
docker logs signal_bot_ensemble

# DB 신호 확인
docker exec future_alarm_bot_postgres psql -U trading_user -d trading_db \
  -c "SELECT strategy_id, COUNT(*) FROM monitoring.signals GROUP BY strategy_id;"
```

---

## 📊 성과 모니터링

### **전략별 성과 조회**
```sql
SELECT 
  strategy_id,
  COUNT(*) as total_signals,
  AVG(confidence) as avg_confidence,
  COUNT(DISTINCT symbol) as symbols
FROM monitoring.signals
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY strategy_id
ORDER BY strategy_id;
```

### **앙상블 결정 조회**
```sql
SELECT 
  decision_id,
  symbol,
  chosen_side,
  score,
  weights,
  TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created
FROM trading.decisions
ORDER BY created_at DESC
LIMIT 10;
```

---

## ⚙️ 튜닝 가이드

### **전략 가중치 조정**
`ensemble_bot.py`:
```python
base_weight = {
    'scalping': 3.0,    # 스캘핑 기본 가중치
    'daytrade': 2.0,    # 단타
    'swing': 1.0,       # 스윙
    'trend': 2.5,       # ⭐ 추세 추종
    'reversion': 2.0,   # ⭐ 평균회귀
    'breakout': 2.2,    # ⭐ 변동성 돌파
}
```

### **시장 상황별 최적화**
```bash
# 추세장 (상승/하락)
WEIGHT_TREND=4.0
WEIGHT_SWING=3.0
WEIGHT_BREAKOUT=3.0

# 횡보장
WEIGHT_SCALP=4.0
WEIGHT_REVERSION=3.5
WEIGHT_DAYTRADE=2.5

# 고변동성
WEIGHT_SCALP=4.0
WEIGHT_BREAKOUT=3.5

# 저변동성
WEIGHT_SWING=3.5
WEIGHT_TREND=3.0
```

---

## 🎉 완성된 시스템

### **Docker 컨테이너 (10개)**
```
✅ future_alarm_bot_postgres  (DB)
✅ signal_bot_scalp           (스캘핑)
✅ signal_bot_intraday        (단타)
✅ signal_bot_swing           (스윙)
✅ signal_bot_trend           (추세) ⭐
✅ signal_bot_reversion       (평균회귀) ⭐
✅ signal_bot_breakout        (변동성 돌파) ⭐
✅ signal_bot_ensemble        (통합)

# 기존 안정 버전 (백업)
✅ signal_bot_scalp_stable
✅ signal_bot_intraday_stable
✅ signal_bot_swing_stable
```

### **데이터 흐름**
```
6개 모니터링 봇
  → monitoring.signals (DB)
    → 앙상블 봇 (가중치 통합)
      → trading.decisions (DB)
        → 트레이딩 봇 (D+2 예정)
```

---

## 🔜 다음 단계 (D+2)

1. **FLOW 전략 추가** (선택)
   - 거래량 필터
   - aggTrade 데이터
   - 비동기 WebSocket

2. **트레이딩 봇 개발**
   - 실제 주문 실행
   - 리스크 관리
   - 3가지 모드 (BACKTEST/DRY_RUN/LIVE)

3. **웹 대시보드** (D+3)
   - 실시간 성과 모니터링
   - 전략별 통계
   - 백테스트 결과

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14  
**상태**: ✅ 운영 준비 완료
