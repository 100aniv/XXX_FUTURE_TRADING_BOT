# 🚀 통합 트레이딩 시스템 사용 가이드

## 📌 **핵심 개념**

**하나의 진입점 (`main.py`), 세 가지 모드**

```
main.py
  ├─ TRADING_MODE=backtest → 과거 데이터로 전략 테스트
  ├─ TRADING_MODE=paper    → 실시간 모의 거래
  └─ TRADING_MODE=live     → 실제 거래 (주의!)
```

모든 모드는 **동일한 로직**을 사용합니다:
- 동일한 전략 코드 (`strategies/`)
- 동일한 지표 계산 (`indicators/`)
- 동일한 실행 엔진 (`execution/engine.py`)

**차이점은 데이터 소스와 주문 실행 방식뿐입니다.**

---

## 🏃 **빠른 시작**

### 1️⃣ **백테스트 (과거 데이터)**

```bash
# 환경변수 설정
export TRADING_MODE=backtest
export STRATEGY_SELECTOR=scalping  # 또는 all

# 실행
python main.py
```

또는 한 줄로:
```bash
TRADING_MODE=backtest STRATEGY_SELECTOR=all python main.py
```

**결과 위치**: `reports/backtest/backtest_YYYYMMDD_HHMMSS.json`

---

### 2️⃣ **페이퍼 트레이딩 (모의 거래)**

```bash
# .env 파일 설정
TRADING_MODE=paper
STRATEGY_SELECTOR=ensemble
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# 실행
python main.py
```

DB에서 실시간 신호 확인:
```sql
SELECT * FROM monitoring.signals ORDER BY created_at DESC LIMIT 10;
SELECT * FROM trading.decisions ORDER BY created_at DESC LIMIT 10;
SELECT * FROM trading.trades ORDER BY created_at DESC LIMIT 10;
```

---

### 3️⃣ **라이브 트레이딩 (실제 거래) ⚠️**

**주의: 실제 자금이 사용됩니다!**

```bash
# .env 파일 설정
TRADING_MODE=live
STRATEGY_SELECTOR=ensemble
BINANCE_API_KEY=your_real_key
BINANCE_SECRET=your_real_secret
EQUITY_USDT=1000  # 시작은 소액으로!

# 실행
python main.py
```

---

## 🐳 **Docker 사용 (권장)**

### 백테스트
```bash
# docker-compose.yml 또는 .env 파일에서:
TRADING_MODE=backtest
STRATEGY_SELECTOR=all

# 실행
docker-compose up -d
docker logs -f future_trading_bot
```

### 페이퍼 트레이딩
```bash
# docker-compose.yml 또는 .env 파일에서:
TRADING_MODE=paper
STRATEGY_SELECTOR=ensemble

# 실행
docker-compose up -d
docker logs -f future_trading_bot
```

### 라이브 트레이딩
```bash
# docker-compose.yml 또는 .env 파일에서:
TRADING_MODE=live
STRATEGY_SELECTOR=ensemble

# 실행
docker-compose up -d
docker logs -f future_trading_bot
```

---

## 📁 **프로젝트 구조**

```
future_alarm_bot/
├── main.py                      # ⭐ 단일 진입점
├── .env                         # 환경변수 설정
├── strategy_params.yaml         # 전략 파라미터
│
├── data/                        # 데이터
│   ├── backtest_config.yaml     # 백테스트 설정
│   └── historical/              # 과거 데이터 (CSV/Parquet)
│
├── common/                      # 공통 모듈
│   ├── config.py                # 설정 로더
│   ├── database.py              # DB 연결
│   ├── logger.py                # 로깅
│   └── calculations.py          # 공통 계산
│
├── indicators/                  # 지표 계산
│   ├── core_indicators.py       # EMA, RSI, MACD, BB, ATR, Donchian
│   └── __init__.py
│
├── strategies/                  # 전략 로직
│   ├── scalping.py              # 스캘핑
│   ├── daytrade.py              # 데이트레이딩
│   ├── swing.py                 # 스윙
│   ├── trend.py                 # 추세추종
│   ├── reversion.py             # 평균회귀
│   ├── breakout.py              # 돌파
│   └── ensemble.py              # 앙상블
│
├── execution/                   # ⭐ 통합 실행 엔진
│   ├── engine.py                # TradingEngine (모든 모드 공통)
│   ├── data_sources/            # 데이터 소스 어댑터
│   │   ├── backtest.py          # CSV 데이터
│   │   └── live.py              # WebSocket 데이터
│   ├── executors/               # 주문 실행 어댑터
│   │   ├── simulation.py        # 백테스트 체결
│   │   ├── paper.py             # 모의 체결
│   │   └── live.py              # 실제 체결
│   ├── position_sizer.py        # 포지션 크기 계산
│   └── risk_manager.py          # 리스크 관리
│
├── signals/                     # 신호 생성
│   ├── signal_generator.py
│   └── signal_storage.py
│
├── reports/                     # 리포트 생성
│   ├── backtest/                # 백테스트 결과
│   └── performance_reporter.py
│
└── tests/                       # 테스트 코드
```

---

## ⚙️ **환경변수 (.env)**

### 필수 설정
```bash
# 모드 선택
TRADING_MODE=backtest          # backtest | paper | live

# 전략 선택
STRATEGY_SELECTOR=ensemble     # ensemble | scalping | daytrade | swing | trend | reversion | breakout | all

# 데이터베이스
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db
```

### 리스크 관리
```bash
EQUITY_USDT=10000              # 초기 자본
RISK_PER_TRADE=0.01            # 거래당 리스크 (1%)
DAILY_LOSS_LIMIT_PCT=0.03      # 일일 손실 한도 (3%)
MAX_CONCURRENT_POSITIONS=5     # 최대 동시 포지션
```

### 바이낸스 API (paper/live 모드)
```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
```

### 백테스트 설정
```bash
BACKTEST_START_DATE=2024-07-01
BACKTEST_END_DATE=2024-10-17
```

---

## 📊 **전략 파라미터 (`strategy_params.yaml`)**

각 전략별 세부 설정:

```yaml
scalping:
  timeframe: "5m"
  rr: 1.5                      # Risk-Reward 비율
  atr_mult_sl: 1.0             # ATR 배수 (손절)
  atr_mult_tp: 1.5             # ATR 배수 (익절)
  risk_per_trade: 0.015        # 거래당 리스크
  cooldown_candles: 3          # 쿨다운 캔들 수
  enable_trailing_stop: true   # 트레일링 스탑 활성화
  # ... (기타 설정)

# 다른 전략들도 동일한 구조
```

---

## 📈 **결과 확인**

### 백테스트 결과
```bash
# JSON 파일
cat reports/backtest/backtest_20241019_223000.json

# 주요 메트릭
- total_trades: 총 거래 수
- win_rate: 승률
- profit_factor: 손익비
- sharpe_ratio: 샤프 비율
- max_drawdown_pct: 최대 낙폭
```

### 실시간 트레이딩 (DB)
```sql
-- 최근 신호
SELECT strategy_id, symbol, direction, confidence 
FROM monitoring.signals 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- 최근 거래
SELECT symbol, side, entry_price, sl_price, tp_price, status, pnl
FROM trading.trades
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;

-- 전략별 성과
SELECT strategy_id, COUNT(*) as trades, AVG(pnl) as avg_pnl
FROM trading.trades
WHERE status = 'CLOSED'
GROUP BY strategy_id;
```

---

## 🔧 **문제 해결**

### "데이터 파일 없음" 에러 (백테스트)
```bash
# 과거 데이터 다운로드
python scripts/download_historical_data.py --symbol BTCUSDT --interval 5m --start 2024-07-01 --end 2024-10-17
```

### DB 연결 실패
```bash
# DB 서비스 확인
docker ps | grep postgres

# DB 재시작
docker-compose restart db_postgres

# DB 로그 확인
docker logs trading_db_postgres
```

### "전략 로드 실패" 에러
```bash
# strategy_params.yaml 확인
cat strategy_params.yaml

# 문법 체크
python -c "import yaml; yaml.safe_load(open('strategy_params.yaml'))"
```

---

## 🎯 **다음 단계**

1. **백테스트로 전략 검증**
   ```bash
   TRADING_MODE=backtest STRATEGY_SELECTOR=all python main.py
   ```

2. **성과 좋은 전략 선택**
   - `reports/backtest/` 결과 확인
   - 승률, 손익비, 샤프비율 비교

3. **페이퍼 트레이딩으로 실전 검증**
   ```bash
   TRADING_MODE=paper STRATEGY_SELECTOR=선택한전략 python main.py
   ```

4. **최소 1-2주 모의 거래 후 라이브 전환**
   ```bash
   TRADING_MODE=live EQUITY_USDT=1000 python main.py
   ```

---

## ⚠️ **주의사항**

1. **라이브 모드는 신중하게!**
   - 반드시 페이퍼 트레이딩부터 시작
   - 최소 자본으로 시작 (1000 USDT 이하)
   - 손실 감당 가능한 범위 내에서만

2. **API 키 보안**
   - `.env` 파일을 Git에 커밋하지 마세요
   - API 키에 IP 화이트리스트 설정
   - Withdrawal 권한은 비활성화

3. **모니터링**
   - 로그 파일 주기적 확인 (`logs/`)
   - DB 테이블 모니터링
   - 텔레그램 알림 설정 권장

---

## 📚 **추가 문서**

- [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) - 시스템 아키텍처
- [BACKTEST_GUIDE.md](BACKTEST_GUIDE.md) - 백테스트 상세 가이드
- [strategy_params.yaml](strategy_params.yaml) - 전략 파라미터
- [data/backtest_config.yaml](data/backtest_config.yaml) - 백테스트 설정
