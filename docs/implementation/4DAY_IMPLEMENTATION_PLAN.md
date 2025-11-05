# 🗓️ 4일 구현 계획 (상세)

**작성일**: 2025-10-14  
**프로젝트**: 신호 모니터링 → 통합 자동매매 시스템

---

## 📅 일정 개요

| 일차 | 목표 | 핵심 작업 | 검증 기준 |
|------|------|-----------|-----------|
| **D+0 (오늘)** | 모니터링 튜닝 + DB 연동 | 신호 표준화, PostgreSQL 저장 | 재시작 후 중복 없음 |
| **D+1 (내일)** | 통합(앙상블) 봇 | 가중치 계산, 결정 생성 | 멱등성 보장, 3신호 통합 |
| **D+2 (모레)** | 트레이딩 집행 봇 | 주문 실행, 리스크 가드 | 중복 집행 없음, 손실 한도 |
| **D+3 (마지막)** | 웹 연동 + 대시보드 | API, Grafana/Metabase | 거래 내역 조회, 성과 분석 |

---

## 🌅 D+0 (오늘): 모니터링 봇 튜닝 + DB 연동

### ✅ **목표**
현재 3개 모니터링(스캘핑/단타/스윙) 출력 포맷 통일 + PostgreSQL 저장.  
재시작해도 초기화 안됨 (DB 영속).

### 📋 **구현 체크리스트**

#### 1. **출력 표준화**
- [ ] 필드 통일:
  ```python
  {
    "signal_id": "uuid4()",
    "strategy_id": "scalping|daytrade|swing",
    "symbol": "BTCUSDT",
    "timeframe": "1m|5m|15m",
    "candle_closed_at": "2025-10-14T12:00:00Z",
    "direction": "LONG|SHORT|FLAT",
    "confidence": 0.85,
    "features": {
      "rsi": 65,
      "macd": 0.5,
      "regime": "상승장",
      "atr": 120.5
    }
  }
  ```
- [ ] UPSERT로 멱등성 보장:
  ```sql
  INSERT INTO monitoring.signals(...)
  VALUES(...)
  ON CONFLICT (strategy_id, symbol, timeframe, candle_closed_at)
  DO NOTHING;
  ```

#### 2. **시간 동기화**
- [ ] 모든 캔들은 **닫힌 시점만** 기록 (미닫힘 금지)
- [ ] UTC 타임존 사용
- [ ] `candle_closed_at`은 정확히 캔들 종료 시각

#### 3. **로그/알림**
- [ ] 시작 시: "🚀 [STRATEGY] 봇 시작 + DB 연결 OK"
- [ ] 신호 생성: 로그만 (텔레그램 알림 선택)
- [ ] 오류 시: 쿨다운 + 재시도, 텔레그램 경고

#### 4. **Docker Compose**
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_pw
      POSTGRES_DB: core
      TZ: Asia/Seoul
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  monitor_scalping:
    build: .
    environment:
      DATABASE_URL: postgresql://app:app_pw@postgres:5432/core
      STRATEGY_ID: scalping
      BOT_NAME: SCALP
      TZ: Asia/Seoul
    depends_on:
      - postgres

  monitor_daytrade:
    build: .
    environment:
      DATABASE_URL: postgresql://app:app_pw@postgres:5432/core
      STRATEGY_ID: daytrade
      BOT_NAME: INTRA
      TZ: Asia/Seoul
    depends_on:
      - postgres

  monitor_swing:
    build: .
    environment:
      DATABASE_URL: postgresql://app:app_pw@postgres:5432/core
      STRATEGY_ID: swing
      BOT_NAME: SWING
      TZ: Asia/Seoul
    depends_on:
      - postgres
```

#### 5. **검증**
- [ ] 재시작 후 같은 캔들 입력 시 **중복 없음** (UNIQUE 제약)
- [ ] 기본 대시: 모니터링 입력 수/분당 건수
- [ ] PostgreSQL 쿼리로 신호 확인:
  ```sql
  SELECT strategy_id, symbol, timeframe, COUNT(*)
  FROM monitoring.signals
  WHERE created_at > now() - interval '1 hour'
  GROUP BY strategy_id, symbol, timeframe;
  ```

### 🎯 **수용 기준 (AC)**
1. ✅ 재시작해도 신호 카운트가 누적 유지
2. ✅ 동일 캔들·전략의 중복 입력 시 DB에 1건만 존재
3. ✅ 텔레그램 "부팅 완료" 알림 1회만

---

## 🧠 D+1 (내일): 통합(앙상블) 봇

### ✅ **목표**
3전략 신호를 묶어 **하나의 결정**을 `trading.decisions`에 기록.  
기본 가중식 적용 + 멱등키(심볼·타임프레임·캔들시각).

### 📋 **구현 체크리스트**

#### 1. **집계 윈도우**
- [ ] 같은 `symbol + timeframe + candle_closed_at`에 대해 3전략 신호 수집
- [ ] 타임 윈도우: ±2초 (캔들 닫힌 후 대기)
- [ ] 신호 수집 로직:
  ```python
  SELECT * FROM monitoring.signals
  WHERE symbol = 'BTCUSDT'
    AND timeframe = '15m'
    AND candle_closed_at = '2025-10-14T12:00:00Z'
  ORDER BY created_at DESC;
  ```

#### 2. **가중치 계산 (초기 파라미터)**
```python
# 가중치 공식
raw_weight_s = (
    α * z(winrate_30d_s) +      # 승률 (표준화)
    β * z(rr_mean_30d_s) +      # 평균 R-multiple
    γ * z(sharpe_30d_s) +       # Sharpe Ratio
    δ * conf_s +                # 신호 확신도
    ε * regime_fit_s            # 레짐 적합도
)

# 초기 권장 파라미터
α = 0.4   # 승률 가중치
β = 0.2   # R-multiple 가중치
γ = 0.2   # Sharpe 가중치
δ = 0.15  # 확신도 가중치
ε = 0.05  # 레짐 적합도 가중치

# 정규화
w_s = max(0, raw_weight_s) / Σ_s max(0, raw_weight_s)

# 최종 스코어
score_side = Σ_s (w_s * side_score_s)

# side_score_s 계산
# LONG  = +conf_s
# SHORT = -conf_s
# FLAT  = 0
```

#### 3. **의사결정**
```python
# 임계값
θ_long = 0.15
θ_short = 0.15

# 결정
if score_side > θ_long:
    chosen_side = 'LONG'
elif score_side < -θ_short:
    chosen_side = 'SHORT'
else:
    chosen_side = 'FLAT'

# 포지션 크기
size = base_size * clamp(|score_side|, min=0.3, max=1.0)
```

#### 4. **기록 (UPSERT)**
```sql
INSERT INTO trading.decisions(
  decision_id,
  symbol,
  timeframe,
  candle_closed_at,
  chosen_side,
  chosen_size,
  score,
  weights,
  from_signals,
  reason
)
VALUES(...)
ON CONFLICT(symbol, timeframe, candle_closed_at)
DO UPDATE SET
  chosen_side = EXCLUDED.chosen_side,
  score = EXCLUDED.score,
  weights = EXCLUDED.weights,
  reason = EXCLUDED.reason;
```

#### 5. **로그/사유**
- [ ] `from_signals`: 3전략 입력 스냅샷 (JSON)
- [ ] `weights`: 각 전략 가중치 (JSON)
- [ ] `reason`: 사람이 읽는 요약 (텍스트)
  ```
  "LONG 결정: Scalp(0.4, conf=0.85), Daytrade(0.35, conf=0.75), Swing(0.25, conf=0.70). 
   최종 스코어: +0.42 (임계값: 0.15). 레짐: 상승장."
  ```

### 🎯 **수용 기준 (AC)**
1. ✅ 동일 캔들에 결정이 **1건만** 존재 (멱등 보장)
2. ✅ 가중치/사유가 DB에 남음 (감사 추적 용이)
3. ✅ 통합 결정과 원천 신호 간 시간차 < 2초

---

## 💰 D+2 (모레): 트레이딩 집행 봇

### ✅ **목표**
**집행 전용**. 입력 소스 선택 가능 (기본 `ensemble`).  
주문·체결·손익 로깅과 **리스크 가드** 탑재.  
**3가지 모드**: BACKTEST / DRY_RUN / LIVE

### 📋 **구현 체크리스트**

#### 1. **전략 선택 (4가지)**
```python
# 환경변수
STRATEGY_SELECTOR = os.getenv("STRATEGY_SELECTOR", "ensemble")
# 선택 가능: ensemble, scalping, daytrade, swing

if STRATEGY_SELECTOR == "ensemble":
    # trading.decisions 구독 (통합 신호)
    source = "trading.decisions"
elif STRATEGY_SELECTOR in ["scalping", "daytrade", "swing"]:
    # monitoring.signals에서 strategy_id 필터 (단일 전략)
    source = "monitoring.signals"
    filter_strategy = STRATEGY_SELECTOR
```

#### 2. **매매 모드 (3가지)**
```python
# 환경변수
TRADING_MODE = os.getenv("TRADING_MODE", "DRY_RUN")
# BACKTEST: 과거 데이터로 시뮬레이션
# DRY_RUN: 실시간이지만 실제 주문 안함 (페이퍼 트레이딩)
# LIVE: 실제 매매 집행

if TRADING_MODE == "BACKTEST":
    # 과거 데이터 로드, 빠른 시뮬레이션
elif TRADING_MODE == "DRY_RUN":
    # 실시간 신호, 가상 주문, 실제 체결 없음
elif TRADING_MODE == "LIVE":
    # 실제 주문 실행 (위험!)
```

#### 2. **멱등 집행**
```python
# processed 플래그 또는 별도 테이블
CREATE TABLE IF NOT EXISTS trading.executions(
  execution_id TEXT PRIMARY KEY,
  decision_id TEXT REFERENCES trading.decisions(decision_id),
  signal_id TEXT,
  ts_executed TIMESTAMPTZ NOT NULL,
  trade_id TEXT,
  status TEXT NOT NULL  -- 'SUCCESS' | 'FAILED' | 'SKIPPED'
);

# 집행 전 체크
if already_processed(decision_id):
    logger.info(f"결정 {decision_id} 이미 처리됨, 스킵")
    return

# 집행 후 기록 (트랜잭션)
with db.begin():
    execute_order(...)
    mark_processed(decision_id)
```

#### 3. **리스크/가드**
- [ ] **일손실 한도**: -3% 도달 시 당일 거래 중단
  ```python
  if daily_pnl_pct < -0.03:
      send_alert("⛔ 일손실 한도 도달, 거래 중단")
      TRADING_ENABLED = False
  ```
- [ ] **연속 손실**: 3회 연속 손실 시 1시간 쿨다운
- [ ] **슬리피지 한도**: 예상가 대비 1% 이상 차이 시 거부
- [ ] **거래소 상태 체크**: API 정상 여부, 서킷브레이커
- [ ] **Kill-switch**: 긴급 중단 명령 (`/stop` 텔레그램 명령)

#### 4. **기록**
```sql
-- 거래 기록
INSERT INTO trading.trades(
  trade_id, ts_open, symbol, side, qty, entry_price, ...
) VALUES (...);

-- 포지션 업데이트
INSERT INTO trading.positions(...)
ON CONFLICT (symbol, side)
DO UPDATE SET qty = qty + EXCLUDED.qty, ...;
```

#### 5. **운영 전환**
```python
# 텔레그램 명령
/set_strategy swing   # 스윙 전략으로 전환
/set_strategy ensemble  # 앙상블로 복귀

# 전환 정책
close_on_switch = True   # 기존 포지션 청산 후 전환
# or
adopt_on_switch = True   # 기존 포지션 유지하고 새 신호부터 전환
```

### 🎯 **수용 기준 (AC)**
1. ✅ 중복 집행 없음 (같은 결정/신호 재집행 방지)
2. ✅ 일손실 한도 도달 시 자동 중지 + 텔레그램 알림
3. ✅ 전략 전환 시 오류 없이 다음 신호부터 반영
4. ✅ 체결 로그 완전성 (주문→체결→PnL 추적 가능)

---

## 🌐 D+3 (마지막): 웹 연동 + 대시보드

### ✅ **목표**
읽기 전용 API + 대시보드.  
**설정 이력 / 거래 내역 / 수익률 리포트** 가시화.

### 📋 **구현 체크리스트**

#### 1. **API (FastAPI 권장)**
```python
from fastapi import FastAPI
import psycopg2

app = FastAPI()

@app.get("/api/trades")
def get_trades(symbol: str = None, from_date: str = None):
    # trading.trades 조회
    ...

@app.get("/api/report/daily")
def daily_report(strategy_id: str = None):
    # reporting.daily_pnl 조회
    ...

@app.get("/api/decisions/latest")
def latest_decisions(symbol: str = None):
    # trading.decisions 최신 N건
    ...
```

#### 2. **대시보드 (Grafana/Metabase)**
- [ ] PostgreSQL read-only 계정 생성
  ```sql
  CREATE ROLE readonly WITH LOGIN PASSWORD 'readonly_pw';
  GRANT CONNECT ON DATABASE core TO readonly;
  GRANT USAGE ON SCHEMA monitoring, trading, reporting TO readonly;
  GRANT SELECT ON ALL TABLES IN SCHEMA monitoring, trading, reporting TO readonly;
  ```
- [ ] Grafana 데이터소스 추가
- [ ] 대시보드 패널:
  - **일별 PnL 차트**: 누적 수익률
  - **승률 게이지**: 30일 롤링
  - **전략별 비교**: Scalping vs Daytrade vs Swing vs Ensemble
  - **체결 지연 히스토그램**: P50, P95
  - **거래 내역 테이블**: 최신 100건

#### 3. **권한/로그**
```sql
-- 설정 변경 이력
CREATE TABLE IF NOT EXISTS config_changes(
  change_id TEXT PRIMARY KEY,
  ts_utc TIMESTAMPTZ NOT NULL,
  user_id TEXT,
  action TEXT NOT NULL,
  params JSONB
);
```

#### 4. **보안**
- [ ] API 토큰 인증 (Bearer Token)
- [ ] 역할 분리: viewer / operator / admin
- [ ] HTTPS (프로덕션)

### 🎯 **수용 기준 (AC)**
1. ✅ 지난 N일 성과·승률·거래내역이 그래프로 확인
2. ✅ 전략별 비교가 1클릭으로 가능
3. ✅ API 응답 < 200ms (캐시 필요 시 Redis 도입)
4. ✅ 모바일에서도 대시보드 접근 가능

---

## ✅ "빠짐없이" QA 체크리스트

### **DB 멱등성**
- [ ] UNIQUE 제약 동작 확인: 중복 입력 시 충돌 없이 1건 유지
- [ ] UPSERT 경로 테스트: 정상/네트워크 끊김/재시도

### **모니터링**
- [ ] 3종 출력 필드 동일
- [ ] 캔들 닫힌 시점만 기록

### **통합(앙상블)**
- [ ] 미수집 신호 폴백 (예: 둘만 도착 시 가중 정규화)
- [ ] 가중치 파라미터 튜닝 가능

### **집행**
- [ ] 중복 집행 방지 (`processed` 플래그)
- [ ] 리스크 가드: 일손실/연속손실/슬리피지/서킷브레이커
- [ ] 전략 전환 명령 `/set_strategy` 실시간 반영

### **영속성**
- [ ] 재시작 후 상태 일관 (포지션/미체결/결정 큐)

### **대시보드**
- [ ] 지표: 일PnL·승률·전략 비교·지연 P50/P95

---

## 🚀 결론

### **복잡도?**
오히려 **↓**. 책임 분리 + 멱등키 덕에 버그/중복집행 방지.

### **전략 선택?**
집행 봇에 **입력 소스 선택 스위치**만 넣으면 끝 (기본은 `ensemble`).

### **실행 순서**
1. **오늘**: 모니터링 튜닝 + DB 연동 깔끔히 마무리
2. **내일**: 통합(앙상블) 봇
3. **모레**: 집행 봇
4. **마지막**: 웹/대시보드

이 순서가 **가장 안전하고 빠릅니다**.

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14  
**버전**: v2.0 (멱등성 강조)
