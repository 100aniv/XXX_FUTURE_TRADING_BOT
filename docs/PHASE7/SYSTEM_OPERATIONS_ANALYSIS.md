# Trading System Operations Analysis
# 트레이딩 시스템 운영 철학 및 모드별 동작 분석

**작성일**: 2025-11-11  
**목적**: Paper/Live 모드에서 프로그램 종료/재시작 시 포지션 및 Manager 상태 처리 전략 정의

---

## 📋 목차
1. [상용 시스템 표준](#상용-시스템-표준)
2. [현재 시스템 분석](#현재-시스템-분석)
3. [문제점 및 개선 방향](#문제점-및-개선-방향)
4. [권장 운영 전략](#권장-운영-전략)

---

## 🎯 상용 시스템 표준

### 1. Backtest 모드 (과거 데이터 시뮬레이션)

#### 목적
- 전략 검증, 파라미터 최적화
- 반복 가능한 테스트 환경 제공

#### 포지션 관리
```
시작:
  - 초기 자본 고정 (예: $50,000)
  - active_positions = {} (빈 상태)
  - 과거 데이터 처음부터 순차 처리

종료:
  - 모든 OPEN 포지션 강제 청산
  - 최종 결과(PnL, 승률, MDD) DB 저장
  - active_positions 초기화

재시작:
  - 항상 처음부터 시작
  - DB 포지션 복원 없음 (과거 run_id로 구분)
```

#### Manager 상태
```
RiskManager:
  - 초기화: active_positions_count = 0
  - 종료: 카운트 리셋
  - 재시작: 항상 0부터 시작

PortfolioManager:
  - 초기화: equity = config.initial_capital
  - 종료: 최종 equity DB 저장
  - 재시작: 다시 초기 자본으로 시작
```

**핵심**: Backtest는 독립적인 시뮬레이션 → 재현성 중요 → 상태 복원 불필요

---

### 2. Paper 모드 (실시간 가상 거래)

#### 목적
- Live 전 검증 환경
- 24/7 실시간 운영 (Live와 동일한 환경)
- 서버 재시작, 업데이트 등 중단 후 재개

#### 포지션 관리
```
시작:
  Case 1) 신규 시작:
    - initial_capital = $50,000
    - active_positions = {}
  
  Case 2) 재시작 (서버 업데이트, 재부팅 등):
    - DB에서 status='OPEN' AND mode='paper' 조회
    - active_positions 복원
    - equity = DB 마지막 값 OR 계산된 현재 equity

종료:
  - active_positions → DB에 OPEN 상태 유지
  - equity, daily_pnl → DB 저장
  - **포지션 청산 없음** (24/7 연속성 보장)

재시작:
  - DB에서 OPEN 포지션 복원
  - Manager 상태 동기화 필요
```

#### Manager 상태
```
RiskManager:
  - 초기화:
    - equity = DB 현재 equity
    - peak_equity = DB 최고 equity (MDD 계산용)
    - active_positions_count = DB OPEN 포지션 개수
  - 복원 필수: risk.add_position() 호출로 카운트 동기화

PortfolioManager:
  - 초기화:
    - total_equity = DB 현재 equity
    - daily_pnl = DB 오늘 누적 PnL
    - realized_pnl = DB 누적 realized
  - 복원 필수: portfolio.add_position() 호출로 노출 계산
```

**핵심**: Paper는 Live 시뮬레이션 → 연속성 중요 → 상태 복원 필수

**왜?**
1. 24/7 운영해야 Live와 동일한 환경
2. 서버 재시작 시 포지션 청산하면 Live와 다른 결과
3. 업데이트 후에도 기존 포지션 유지해야 실전 검증 가능

---

### 3. Live 모드 (실제 거래)

#### 목적
- 실제 자본으로 운영
- 거래소 포지션 관리

#### 포지션 관리
```
시작:
  - Binance API: GET /fapi/v2/positionRisk
  - 거래소에 OPEN 포지션 존재
  - active_positions 복원 (필수!)

종료:
  - **프로그램만 종료** (포지션은 거래소에 남음)
  - DB에 상태 동기화

재시작:
  - Binance API에서 포지션 조회
  - active_positions 복원
  - DB와 거래소 동기화
```

#### Manager 상태
```
RiskManager:
  - 초기화:
    - equity = Binance 계좌 잔고
    - active_positions_count = Binance OPEN 포지션 개수
  - 복원 필수: Binance 포지션과 동기화

PortfolioManager:
  - 초기화:
    - total_equity = Binance 잔고
    - unrealized_pnl = Binance 미실현 손익
  - 복원 필수: 거래소 상태 반영
```

**핵심**: Live는 거래소와 동기화 → 복원 필수 → 미복원 시 손실 위험

**왜?**
1. 거래소에 포지션이 존재하는데 프로그램이 모르면 위험
2. SL/TP 관리 불가 → 손실 확대
3. 포지션 카운트 불일치 → 중복 진입 또는 진입 차단

---

## 🔍 현재 시스템 분석

### 구현 상태

#### 1. **Backtest 모드**
```python
# main.py
if mode == "backtest":
    feed = HistoricalFeed(...)
    broker = BacktestBroker(...)
    run(feed, broker, ...)
```
- ✅ 포지션 복원 없음 (올바름)
- ✅ 초기 자본 고정
- ⚠️ 종료 시 명시적 청산 로직 없음 (feed 종료 시 자동 청산 추정)

#### 2. **Paper 모드**
```python
# engine.py 296-380줄
if mode == "paper":
    # DB에서 OPEN 포지션 복원
    cur.execute("SELECT * FROM trading.trades WHERE status='OPEN' AND mode='paper'")
    for row in rows:
        active_positions[trade_id] = {...}
        risk.add_position(...)  # ✅ 수정 완료
        portfolio.add_position(...)  # ✅ 수정 완료
```
- ✅ 포지션 복원 (올바름)
- ✅ Manager 동기화 (2025-11-11 수정 완료)
- ⚠️ Equity 복원 로직 불명확

#### 3. **Live 모드**
```python
# engine.py 382-443줄
elif mode == "live":
    # Binance API에서 포지션 조회
    positions_result = broker.get_positions()
    for pos in live_positions:
        active_positions[position_id] = {...}
        risk.add_position(...)  # ✅ 수정 완료
        portfolio.add_position(...)  # ✅ 수정 완료
```
- ✅ 포지션 복원 (올바름)
- ✅ Manager 동기화 (2025-11-11 수정 완료)
- ⚠️ Binance equity 동기화 필요

---

## ❌ 문제점 및 개선 방향

### 문제 1: Equity 복원 불완전

**현재 상태:**
```python
# execution/portfolio_manager.py 초기화
self.total_equity = initial_equity  # config.initial_capital
self.daily_pnl = 0.0
```

**문제:**
- Paper 재시작 시 equity가 초기 자본으로 리셋
- 실제로는 이전 PnL 누적되어야 함

**개선 방향:**
```python
# Paper 모드 재시작 시
if mode == "paper" and active_positions:
    # DB에서 현재 equity 조회
    cur.execute("SELECT current_equity FROM portfolio_state WHERE mode='paper' ORDER BY updated_at DESC LIMIT 1")
    last_equity = cur.fetchone()[0]
    portfolio.total_equity = last_equity
```

### 문제 2: RiskManager 상태 복원 불완전

**현재 상태:**
```python
# execution/risk_manager.py 초기화
self.peak_equity = self.equity
self.current_drawdown = 0.0
self.consecutive_losses = 0
```

**문제:**
- peak_equity 복원 안 됨 → MDD 계산 오류
- consecutive_losses 복원 안 됨 → 쿨다운 관리 오류

**개선 방향:**
```python
# Paper 모드 재시작 시
if mode == "paper":
    cur.execute("SELECT peak_equity, consecutive_losses FROM risk_state WHERE mode='paper' LIMIT 1")
    row = cur.fetchone()
    if row:
        risk.peak_equity = row[0]
        risk.consecutive_losses = row[1]
```

### 문제 3: DB 역할 혼재

**현재 상태:**
- `trading.trades`: 거래 기록 + 포지션 상태 (OPEN/CLOSED)
- `optuna.*`: 최적화 기록
- **portfolio_state, risk_state 테이블 없음**

**문제:**
- 포지션 상태(trades)는 복원하지만 Manager 상태는 복원 안 됨
- Equity, peak_equity, consecutive_losses 등 손실

**개선 방향:**
```sql
-- 새 테이블 추가
CREATE TABLE trading.portfolio_state (
    mode VARCHAR(10),
    current_equity NUMERIC,
    daily_pnl NUMERIC,
    realized_pnl NUMERIC,
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (mode, updated_at)
);

CREATE TABLE trading.risk_state (
    mode VARCHAR(10),
    peak_equity NUMERIC,
    consecutive_losses INT,
    in_cooldown BOOLEAN,
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (mode, updated_at)
);
```

---

## ✅ 권장 운영 전략

### A. **Backtest 모드**
```
시작:
  1. 초기 자본 고정
  2. active_positions = {}
  3. Manager 초기화

종료:
  1. 모든 OPEN 포지션 강제 청산
  2. 최종 결과 DB 저장
  3. 상태 초기화

재시작:
  1. 항상 처음부터 시작
  2. DB 복원 없음
```

### B. **Paper 모드** (수정 필요)
```
시작:
  Case 1) 신규 (--reset 옵션):
    1. initial_equity = config.initial_capital
    2. DB OPEN 포지션 삭제 OR 강제 청산
    3. Manager 초기화
    4. active_positions = {}
  
  Case 2) 재시작 (기본):
    1. DB에서 OPEN 포지션 복원
    2. active_positions 재구성
    3. risk.add_position() 호출
    4. portfolio.add_position() 호출
    5. DB에서 equity, peak_equity, consecutive_losses 복원
    6. Manager 상태 동기화

종료:
  1. 포지션 유지 (DB OPEN 상태)
  2. portfolio_state 저장
  3. risk_state 저장

재시작:
  1. 포지션 + Manager 상태 복원
```

### C. **Live 모드** (수정 필요)
```
시작:
  1. Binance API 포지션 조회
  2. active_positions 복원
  3. risk.add_position() 호출
  4. portfolio.add_position() 호출
  5. Binance 잔고로 equity 동기화
  6. Manager 상태 동기화

종료:
  1. 포지션 유지 (Binance에 존재)
  2. 상태 DB 저장

재시작:
  1. Binance 포지션 동기화
  2. Manager 상태 복원
```

---

## 🎯 결론

### 질문에 대한 답변

**Q1: 포지션 복원이 맞는 방향인가?**
- **Backtest**: ❌ 복원 불필요 (올바른 상태)
- **Paper**: ✅ 복원 필수 (Live 시뮬레이션)
- **Live**: ✅ 복원 필수 (거래소 동기화)

**Q2: 종료 시 포지션 청산이 맞지 않나?**
- **Backtest**: ✅ 청산 후 초기화 (권장)
- **Paper**: ❌ 청산하면 안 됨 (24/7 연속성)
- **Live**: ❌ 청산하면 안 됨 (거래소 포지션 유지)

**Q3: Manager 초기화가 필요없나?**
- **Backtest**: ✅ 항상 초기화
- **Paper**: ⚠️ 부분 복원 필요 (equity, peak_equity, consecutive_losses)
- **Live**: ⚠️ Binance 상태로 동기화

**Q4: DB는 기록용이 맞지 않나?**
- **현재**: trades (포지션 상태 + 기록) 혼재
- **권장**:
  - `trading.trades`: 거래 기록 (CLOSED만)
  - `trading.positions`: 현재 포지션 상태 (OPEN)
  - `trading.portfolio_state`: Portfolio Manager 상태
  - `trading.risk_state`: Risk Manager 상태

---

## 🚨 치명적 위험: TP 관리 방식

### 현재 시스템 (2025-11-11 분석)

```python
# 진입 시 (execution/engine.py 1410줄)
broker.create_sl_order(...)  # ✅ SL은 거래소에 등록

# TP 체크 (execution/engine.py 652줄)
should_action, partial_qty, reason, exit_price = tracker.check_tpsl_with_partial(...)
# ❌ TP는 프로그램 내부에서만 체크 (거래소 등록 안 됨!)
```

**결과:**
1. **SL**: ✅ 거래소 관리 → 프로그램 종료해도 안전
2. **TP**: 🚨 **프로그램 관리 → 종료 시 TP 미작동!**
3. **Trailing Stop**: 🚨 **프로그램 관리 → 종료 시 Trailing 중단!**

### 위험 시나리오

#### 시나리오 1: 네트워크 단절
```
1. BTCUSDT LONG @ $50,000
2. SL $49,500 (거래소) ✅
3. TP1 $51,000 (메모리) ❌
4. 프로그램 크래시
5. 가격 $51,500 도달 → TP 미작동
6. 가격 반전 → SL $49,500 터짐
7. 손실: $1,500 (이익 기회 + 손실)
```

#### 시나리오 2: Trailing Stop 실패
```
1. ETHUSDT LONG @ $2,000
2. SL $1,980 (거래소)
3. 가격 $2,050 → Trailing → SL $2,030 (메모리)
4. 프로그램 종료
5. 거래소 SL은 여전히 $1,980
6. 가격 반전 → $1,980 손실
7. 추가 손실: $50
```

### 상용 시스템 해결 방안

#### Option A: 거래소 주문 등록 (권장) ✅
```python
broker.create_sl_order(sl_price)  # SL
broker.create_tp_order(tp_price)  # TP (OCO)
```
- 장점: 24/7 안전
- 단점: 분할 TP 구현 복잡

#### Option B: 클라우드 이중화 ✅
```
Primary → Secondary (Failover < 10초)
```
- 장점: 유연한 로직
- 단점: 인프라 비용

#### Option C: 하이브리드 (추천) ⚠️
```python
broker.create_sl_order(sl_price)        # SL 거래소
broker.create_tp_order(tp1_price, 50%)  # TP1 거래소
# TP2, Trailing은 프로그램 관리
```
- 장점: 최소 수익 보장
- 단점: 비정상 종료 시 TP2 손실

---

## 📋 개선 작업 항목 (PR별 명확히 분리)

### ✅ PHASE7-2 (포지션 관리 개선) - 현재 PR
**완료:**
- [x] 포지션 복원 시 Manager 등록 (2025-11-11)
  - `RiskManager.active_positions_count` 동기화
  - `PortfolioManager.add_position()` 동기화

**진행:**
- [ ] **항목 8**: Manager 상태 완전 복원 ⚠️ 높은 우선순위
  - DB 테이블: portfolio_state, risk_state
  - Equity, peak_equity, consecutive_losses 복원
  - Paper 재시작 시 정확한 상태 이어가기

**연기 (PHASE7-3 이후):**
- [ ] **항목 7**: --reset 옵션 (초기화 vs 재시작)
  - Graceful Shutdown 로직과 통합 권장
  - 범위 확대 방지

### 📋 PHASE7-3 (운영 안정성) - 다음 PR
**Live 모드 준비:**
- [ ] **Graceful Shutdown**: 종료 시 안전한 청산
  - Signal handler (SIGTERM, SIGINT)
  - 신규 진입 중단 → OPEN 포지션 청산
  - Binance SL/TP 주문 취소 (Live)
  - 상태 저장 (DB + Redis)
  - **항목 7 통합**: --reset 옵션 구현

- [ ] **TP 거래소 등록**: 프로그램 종료 시 TP 안전 보장
  - LiveBroker.create_tp_order() 메서드
  - engine.py: 진입 시 TP1 50% 거래소 등록
  - TP2, Trailing은 프로그램 관리 (유연성)
  - **현재 위험**: SL만 거래소, TP는 메모리 🚨

- [ ] **State Recovery 강화**: 재시작 시 완전한 동기화
  - Binance 주문 ID 저장/복원
  - 주문 상태 확인 (SL/TP 활성화 여부)
  - 불일치 시 알림

- [ ] **Docker Healthcheck**: 연결 상태 모니터링
- [ ] **Monitoring Dashboard**: Grafana 기본 설정

### PHASE7-4 (전략 개선) 📋
- 백테스트 파이프라인
- 전략별 성과 분석
- 승률 50% 달성

### PHASE7-5 (Live 전환) 📋
- Paper/Live 파리티 검증
- 소액 테스트 ($100)
- 단계적 확장

---

## 🎯 최종 권장 사항

### 의도적 종료 (테스트 목적)
```bash
# Paper 초기화
docker-compose run --rm -e RESET_MODE=true trading_bot_paper_ensemble

# 동작:
1. DB OPEN 포지션 강제 청산
2. Equity → 초기 자본
3. 새 run_id 생성
4. 깨끗한 시작
```

### 운영 중 재시작 (24/7 연속성)
```bash
# Paper/Live 재시작 (기본)
docker-compose restart trading_bot_paper_ensemble

# 동작:
1. DB/API에서 포지션 복원
2. Manager 상태 복원 (equity, peak_equity 등)
3. 기존 상태 이어서 계속
```

### Live 초기화 (수동 필수)
```bash
# 1. Binance 앱에서 모든 포지션 수동 청산
# 2. 포지션 0개 확인
# 3. 프로그램 시작
python main.py --mode live

# --reset 옵션은 Live에서 금지
```

---

**참조 문서:**
- PHASE7-2_MASTER_PLAN.md (항목 7, 8)
- PHASE7-3_MASTER_PLAN.md (Graceful Shutdown, TP 거래소)
- CRITICAL_SYSTEM_ANALYSIS_2025-11-10.md
- .windsurfrules (단일 책임, 모듈 중복 금지)

**업데이트:** 2025-11-11 (상용 시스템 비교, TP 위험 분석, TO-BE 로드맵)
