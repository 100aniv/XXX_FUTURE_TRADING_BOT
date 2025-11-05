# 🚀 자동매매 시스템 구현 계획

**작성일**: 2025-10-14  
**현재 상태**: 신호 모니터링 봇 (v13.3B)  
**최종 목표**: 통합 자동매매 시스템 + 웹 리포트

> ⚠️ **핵심 설계 원칙**: **멱등성(Idempotency)** - 중복 방지가 시스템 전체에 내장

> 📋 **상세 구현 계획**: [4DAY_IMPLEMENTATION_PLAN.md](./4DAY_IMPLEMENTATION_PLAN.md)

---

## 🔑 멱등성(Idempotency) 핵심
### **한 줄 정의**
같은 사건을 여러 번 처리하려고 해도 **결과가 1번만 반영**되도록 보장하는 고유 키.

### **예시**
- 동일 캔들(시간 끝), 동일 심볼, 동일 전략에서 발생한 신호/결정은 **딱 1건만** 기록/집행
- 봇 재시작, 네트워크 재시도 시에도 중복 없음

### **구현 방법**
```sql
-- 신호 멱등키
UNIQUE(strategy_id, symbol, timeframe, candle_closed_at)

-- 결정 멱등키
UNIQUE(symbol, timeframe, candle_closed_at)

-- UPSERT 패턴
INSERT INTO monitoring.signals(...)
VALUES(...)
ON CONFLICT (strategy_id, symbol, timeframe, candle_closed_at)
DO NOTHING;  -- 이미 있으면 무시
```

---

## 📊 최종 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONITORING LAYER (신호 생성)                  │
├─────────────────────────────────────────────────────────────────┤
│  [스캘핑 모니터]    [단타 모니터]    [스윙 모니터]              │
│       1m봇            5m봇           15m봇                      │
│        │               │               │                         │
│        └───────────────┴───────────────┘                         │
│                        │                                         │
│                        ▼                                         │
│              monitoring.signals (DB)                             │
│         (각 전략별 신호 저장 - 매매 안함)                        │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              ENSEMBLE LAYER (신호 통합/가중치)                   │
├─────────────────────────────────────────────────────────────────┤
│                   [통합(앙상블) 봇]                              │
│                                                                  │
│  • 3개 전략 신호 수집                                            │
│  • 가중치 계산 (성과 기반 + 레짐 적합도)                         │
│  • 최종 결정 생성 (LONG/SHORT/FLAT)                              │
│  • 멱등성 보장 (중복 방지)                                       │
│                        │                                         │
│                        ▼                                         │
│              trading.decisions (DB)                              │
│            (하나로 통합된 매매 결정)                             │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                EXECUTION LAYER (집행 전용)                       │
├─────────────────────────────────────────────────────────────────┤
│                   [트레이딩 봇]                                  │
│                                                                  │
│  • 통합 봇의 결정만 받아서 실행                                  │
│  • 리스크 가드 (일손실 한도, 연속손실 체크)                      │
│  • TP/SL 관리                                                    │
│  • 체결/청산 실행                                                │
│                        │                                         │
│                        ▼                                         │
│          trading.trades / positions (DB)                         │
│              (실제 거래 기록)                                    │
└─────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              REPORTING LAYER (성과 분석/웹)                      │
├─────────────────────────────────────────────────────────────────┤
│                  [웹 대시보드]                                   │
│                                                                  │
│  • 거래 내역 조회                                                │
│  • 일/주/월 성과 리포트                                          │
│  • 전략별 성과 비교                                              │
│  • 실시간 포지션 현황                                            │
│  • 리스크 메트릭 (Sharpe, Drawdown)                              │
│                                                                  │
│  ▶️ Grafana / Metabase / 커스텀 웹                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 데이터베이스 설계

### **주 데이터베이스: PostgreSQL**

#### 1. **monitoring.signals** (모니터링 신호)
```sql
CREATE TABLE IF NOT EXISTS monitoring.signals (
  signal_id      TEXT PRIMARY KEY,
  ts_utc         TIMESTAMPTZ NOT NULL,
  strategy_id    TEXT NOT NULL,          -- 'scalping' | 'daytrade' | 'swing'
  bot_id         TEXT NOT NULL,          -- 'scalp' | 'intraday' | 'swing'
  symbol         TEXT NOT NULL,
  timeframe      TEXT NOT NULL,
  direction      TEXT NOT NULL,          -- 'LONG' | 'SHORT' | 'FLAT'
  confidence     NUMERIC NOT NULL,       -- 0.0 ~ 1.0
  entry_price    NUMERIC NOT NULL,
  sl_price       NUMERIC,
  tp_price       NUMERIC,
  atr            NUMERIC,
  features       JSONB,                  -- RSI, MACD, 레짐 등
  created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_signals_strategy_ts ON monitoring.signals (strategy_id, ts_utc DESC);
```

#### 2. **trading.decisions** (통합 결정)
```sql
CREATE TABLE IF NOT EXISTS trading.decisions (
  decision_id    TEXT PRIMARY KEY,
  ts_utc         TIMESTAMPTZ NOT NULL,
  symbol         TEXT NOT NULL,
  timeframe      TEXT NOT NULL,
  chosen_side    TEXT NOT NULL,          -- 'LONG' | 'SHORT' | 'FLAT'
  chosen_size    NUMERIC NOT NULL,       -- 포지션 크기 (USDT)
  from_signals   JSONB NOT NULL,         -- 3전략 입력 스냅샷
  weights        JSONB NOT NULL,         -- 각 전략 가중치
  score          NUMERIC NOT NULL,       -- 최종 스코어
  reason         TEXT,                   -- 의사결정 근거
  unique_key     TEXT UNIQUE,            -- 멱등성 (symbol+candle_ts)
  created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_decisions_symbol_ts ON trading.decisions (symbol, ts_utc DESC);
```

#### 3. **trading.trades** (거래 기록)
```sql
CREATE TABLE IF NOT EXISTS trading.trades (
  trade_id       TEXT PRIMARY KEY,
  decision_id    TEXT REFERENCES trading.decisions(decision_id),
  symbol         TEXT NOT NULL,
  side           TEXT NOT NULL,          -- 'LONG' | 'SHORT'
  entry_price    NUMERIC NOT NULL,
  exit_price     NUMERIC,
  quantity       NUMERIC NOT NULL,
  leverage       INTEGER NOT NULL,
  sl_price       NUMERIC,
  tp_price       NUMERIC,
  ts_open        TIMESTAMPTZ NOT NULL,
  ts_close       TIMESTAMPTZ,
  pnl            NUMERIC,
  pnl_pct        NUMERIC,
  fees           NUMERIC,
  status         TEXT NOT NULL,          -- 'OPEN' | 'CLOSED'
  strategy_id    TEXT NOT NULL,
  exit_reason    TEXT,                   -- 'TP' | 'SL' | 'MANUAL'
  created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_trades_symbol_ts ON trading.trades (symbol, ts_open DESC);
CREATE INDEX idx_trades_status ON trading.trades (status, ts_open DESC);
```

#### 4. **reporting.strategy_performance** (전략 성과)
```sql
CREATE TABLE IF NOT EXISTS reporting.strategy_performance (
  as_of          TIMESTAMPTZ NOT NULL,
  strategy_id    TEXT NOT NULL,
  symbol         TEXT NOT NULL,
  winrate_30d    NUMERIC,                -- 승률 (30일)
  rr_mean_30d    NUMERIC,                -- 평균 R-multiple
  sharpe_30d     NUMERIC,                -- Sharpe Ratio
  n_trades_30d   INTEGER,                -- 거래 횟수
  latency_ms_p50 INTEGER,                -- 지연시간 중앙값
  PRIMARY KEY (as_of, strategy_id, symbol)
);
CREATE INDEX idx_perf_latest ON reporting.strategy_performance (strategy_id, symbol, as_of DESC);
```

#### 5. **reporting.daily_pnl** (일별 손익)
```sql
CREATE TABLE IF NOT EXISTS reporting.daily_pnl (
  date           DATE NOT NULL,
  strategy_id    TEXT NOT NULL,
  symbol         TEXT,
  pnl            NUMERIC NOT NULL,
  fees           NUMERIC NOT NULL,
  n_trades       INTEGER NOT NULL,
  win_trades     INTEGER NOT NULL,
  loss_trades    INTEGER NOT NULL,
  PRIMARY KEY (date, strategy_id, symbol)
);
```

### **보조 데이터베이스: Redis**
- **실시간 캐시**: 최신 가격, 포지션 현황
- **Pub/Sub**: 신호/결정 실시간 전파
- **Stream**: `decisions_stream`, `trades_stream`

---

## 🧠 통합(앙상블) 로직

### **가중치 계산 공식**
```python
raw_weight_s = (
    α * z(winrate_30d_s) +      # 승률 (표준화)
    β * z(rr_mean_30d_s) +      # 평균 R-multiple
    γ * z(sharpe_30d_s) +       # Sharpe Ratio
    δ * conf_s +                # 신호 확신도
    ε * regime_fit_s            # 레짐 적합도
)

# 초기 권장 파라미터
α = 0.4  # 승률 가중치
β = 0.2  # R-multiple 가중치
γ = 0.2  # Sharpe 가중치
δ = 0.15 # 확신도 가중치
ε = 0.05 # 레짐 적합도 가중치

# 정규화
w_s = max(0, raw_weight_s) / Σ_s max(0, raw_weight_s)
```

### **최종 결정**
```python
score_side = Σ_s (w_s * side_score_s)

# side_score_s:
#   LONG  = +conf_s
#   SHORT = -conf_s
#   FLAT  = 0

# 의사결정
if score_side > θ_long:
    chosen_side = 'LONG'
elif score_side < -θ_short:
    chosen_side = 'SHORT'
else:
    chosen_side = 'FLAT'

# 초기 임계값
θ_long = θ_short = 0.15

# 포지션 크기
size = base_size * clamp(|score_side|, min=0.3, max=1.0)
```

### **멱등성 보장**
```python
unique_key = f"{symbol}_{candle_close_time.isoformat()}"

# UPSERT로 중복 방지
INSERT INTO trading.decisions (decision_id, unique_key, ...)
VALUES (...)
ON CONFLICT (unique_key) DO NOTHING;
```

---

## 🎯 단계별 구현 계획

### **Phase 1: 데이터베이스 마이그레이션** 📊
- [ ] PostgreSQL 설치 및 설정
- [ ] 스키마 생성 (`monitoring`, `trading`, `reporting`)
- [ ] 현재 3개 봇에서 DB로 신호 저장하도록 수정
- [ ] Redis 설치 및 연동 (선택)

### **Phase 2: 통합(앙상블) 봇 개발** 🧠
- [ ] 3개 전략 신호 수집 로직
- [ ] 가중치 계산 엔진
- [ ] 최종 결정 생성 및 저장
- [ ] 멱등성 체크
- [ ] 텔레그램 알림 (결정 통지)

### **Phase 3: 트레이딩 봇 (집행 전용)** 💰
- [ ] Binance API 주문 실행 (`python-binance`)
- [ ] TP/SL 자동 관리
- [ ] 리스크 가드:
  - 일손실 한도 체크
  - 연속 손실 쿨다운
  - 포지션 중복 방지
- [ ] 거래 기록 저장 (`trading.trades`)
- [ ] 에러 핸들링 및 재시도

### **Phase 4: 성과 집계 및 리포팅** 📈
- [ ] 일별/전략별 성과 자동 계산
- [ ] `reporting.strategy_performance` 자동 갱신 (cron)
- [ ] Grafana 대시보드 구축:
  - 실시간 PnL 차트
  - 전략별 성과 비교
  - 거래 내역 테이블
  - 리스크 메트릭 (Sharpe, Max DD)
- [ ] 웹 리포트 페이지 (Flask/FastAPI)

### **Phase 5: 테스트 및 최적화** 🧪
- [ ] 백테스팅 (과거 데이터)
- [ ] 워크포워드 검증 (30일 학습 → 7일 운용)
- [ ] A/B 테스트 (앙상블 vs 단일 전략)
- [ ] 가중치 파라미터 튜닝
- [ ] 슬리피지/수수료 반영

### **Phase 6: 운영 및 모니터링** 🔍
- [ ] 알림 시스템 강화 (에러/경고/성과)
- [ ] 로그 중앙화 (ELK Stack 또는 CloudWatch)
- [ ] 헬스체크 및 자동 재시작
- [ ] 백업 및 재해복구 계획

---

## 🛠️ 기술 스택

### **Backend**
- **Python 3.11+**
- **PostgreSQL 15+** (주 데이터베이스)
- **Redis 7+** (캐시/Pub-Sub)
- **SQLAlchemy** (ORM)
- **Alembic** (마이그레이션)
- **python-binance** (거래소 API)

### **Frontend / Reporting**
- **Grafana** (실시간 대시보드)
- **Metabase** (비즈니스 리포트)
- **Flask/FastAPI** (커스텀 웹 페이지)

### **Infrastructure**
- **Docker + Docker Compose** (컨테이너화)
- **Nginx** (리버스 프록시)
- **systemd / cron** (스케줄링)

---

## 📁 예상 프로젝트 구조

```
future_trading_system/
├── monitoring_bots/           # 현재 3개 봇
│   ├── scalp_bot/
│   ├── intraday_bot/
│   └── swing_bot/
├── ensemble_bot/              # 통합 봇 (신규)
│   ├── ensemble_engine.py
│   ├── weight_calculator.py
│   └── decision_maker.py
├── trading_bot/               # 집행 봇 (신규)
│   ├── executor.py
│   ├── risk_guard.py
│   └── position_manager.py
├── database/
│   ├── models.py              # SQLAlchemy 모델
│   ├── migrations/            # Alembic
│   └── init_db.sql            # 스키마
├── reporting/
│   ├── performance_calc.py    # 성과 계산
│   ├── grafana_dashboards/    # 대시보드 JSON
│   └── web_app/               # Flask/FastAPI
├── config/
│   ├── database.env
│   ├── trading.env
│   └── ensemble.env
├── docker-compose.yml         # 전체 시스템
└── README.md
```

---

## ⚠️ 리스크 관리 규칙

### **리스크 가드**
1. **일손실 한도**: -5% 도달 시 당일 거래 중단
2. **연속 손실**: 3회 연속 손실 시 1시간 쿨다운
3. **포지션 크기**: 총 자산의 최대 20%
4. **레버리지 제한**: 최대 10x
5. **변동성 체크**: ATR 급등 시 레버리지 자동 감소

### **멱등성 및 중복 방지**
- 동일 캔들/심볼에 대해 **하나의 결정만** 생성
- `unique_key` 제약으로 DB 레벨에서 보장
- Redis 분산 락으로 동시성 제어

---

## 🎯 성공 지표 (KPI)

1. **Sharpe Ratio > 1.5**
2. **Max Drawdown < 15%**
3. **Win Rate > 50%**
4. **평균 R-multiple > 1.5**
5. **시스템 가동률 > 99.5%**
6. **주문 지연 < 200ms (P95)**

---

## 📚 참고 자료

- **Binance API Docs**: https://binance-docs.github.io/apidocs/futures/en/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/
- **Risk Management Best Practices**: TBD

---

## 🚀 최종 목표

**단순 알림 봇** → **통합 자동매매 시스템** → **웹 리포트 완성**

### **기대 효과**
- ✅ 3개 전략의 시너지 극대화
- ✅ 데이터 기반 의사결정
- ✅ 리스크 통제 강화
- ✅ 실시간 성과 모니터링
- ✅ 완전 자동화된 트레이딩 시스템

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14  
**버전**: v1.0
