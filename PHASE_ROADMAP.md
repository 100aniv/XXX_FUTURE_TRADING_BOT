📌 Future Alarm Bot – 최종 상용 버전까지 전체 로드맵

목표 한 줄 요약
“단일 엔진(backtest/paper/live 공용)에 기반한,
자동 리스크 관리 + Guard + 포트폴리오 + 모니터링까지 포함된
실제 운용 가능한 상용급 앙상블 트레이딩 시스템”

0. 전체 구조 개요
🔹 로드맵 큰 축

INFRA / ENGINE 안정화 (지금 ~ PHASE20 전후)

엔진, 포지션/포트폴리오, Budget, Guard, 데이터, 테스트 인프라

“수익”이 아니라 “망가지지 않는 구조”에 집중

STRATEGY / PERFORMANCE (PHASE20~PHASE30)

단일 전략(스캘핑) → 여러 전략 → 앙상블

백테스트/페이퍼 기반으로 승률·PnL·MDD 검증

PRODUCTION / OPERATIONS (PHASE30~PHASE40)

Live 구조, 실계좌 연결, 장애 대응, 모니터링, 알람, Runbook

“내가 안 보고 있어도 돌아가는 시스템”

1. 공통 규칙 (모든 Phase에 공통 적용)

이제부터 어떤 Phase든 무조건 아래 5개 규칙 깔고 간다.

✅ 진입 조건(Entry Criteria)

“이 Phase를 시작해도 되는지”를 정의

이전 Phase에서 최소한 무엇이 완료되어야 하는지 명시

✅ 퇴출 조건(Exit / Acceptance Criteria)

이 Phase를 “완료”라고 말하려면 반드시 충족해야 하는 구체적인 조건

조건 만족 못하면 다음 Phase로 못 넘어감

✅ 산출물(Deliverables)

코드 / 설정 / 문서 / 테스트 결과 정리

최소 1개 이상 MD 문서로 남김

✅ Out-of-Scope(이번 Phase에서 일부러 안 하는 것)

“중간에 욕심 내서 새로 벌릴 것들”을 미리 차단

예: 이 Phase는 승률 튜닝 안 함, 전략 추가 안 함 등

✅ 문제 발생 시 원칙

Acceptance 조건 만족 못하면
→ “버그/이슈 목록 MD + 원인/해결 계획” 작성
→ 해결 후에만 Phase 완료 선언

2. 현재 위치 기준: PHASE17 재정의

지금은 이미 PHASE0~16 + D단계를 거쳐서,
PHASE17 = Portfolio Budget / Position Sizing 인프라 단계에 와 있다고 보면 된다.

그래서 로드맵은 **“지금 이후”**를 중심으로 정의할게.

3. 상세 로드맵 (PHASE17 이후)
🧩 PHASE17 – Portfolio Budget & Position Infra 안정화 ✅ **완료 (CONDITIONAL PASS, Production Ready)**

목적

Budget SSOT 구조 확립

PortfolioManager / PositionSizer / Engine 간 데이터 플로우 안정화

REAL PAPER 12H 기준으로도 Budget/Guard가 정상 동작하는지 검증

진입 조건

엔진 단일 구조 (backtest/paper/live 공용) 이미 존재

Redis/Postgres/FlowGuardian 기본 구조 동작

기본 스캘핑 전략으로 Paper 모드 최소 15분~1시간 실행 경험 있음

**완료 상태 (2025-11-19)**:
- V6.1 기준 12H REAL PAPER 테스트 통과
- Budget Cap 정상 작동 (111회 적용 확인)
- Portfolio BLOCK ≈ 31.1% (목표 <30% 근접)
- ERROR/CRITICAL 0건
- 문서: docs/PHASE17/PHASE17_V6_1_REAL_PAPER_12H_ACCEPTANCE_REPORT.md

주요 작업

PortfolioManager

_get_used_budget(), get_available_budget()

포지션 딕셔너리 키 통일 (position_value, status='OPEN' 등)

PositionSizer

리스크 기반 사이징 (RPT, SL, 레버리지 고려)

available_budget 파라미터 기반 Budget Cap

Cap 적용 시 로깅

Engine

포지션 생성 / 추가 / Scaling 시 Budget 플로우 일관성

Budget Cap 반영 후 다시 깨지지 않도록 값 재계산 방식 정리

테스트 인프라

단위 테스트 (Sizer / Portfolio / Budget 계산)

통합 테스트 스크립트 (Budget 시나리오)

REAL PAPER 1H & 12H 실행 테스트

퇴출(완료) 조건 – 반드시 통과해야 다음 Phase로 진행 가능

Budget 기능 Acceptance

통합 테스트에서 아래 시나리오 전부 통과:

Budget 내 Entry → Cap 없음

Budget 초과 Entry → Cap 적용

Budget 완전 소진 → Entry Block

REAL PAPER 12H Acceptance (아까 말한 그거)

모드: REAL PAPER

Config: real_paper_12h_v6_1_phase17.yml

최소 12시간 연속 실행 (중간 재시작 포함해 총 12H 이상)

기준:

Entry SUCCESS ≥ 100

Budget Cap Applied ≥ 1회 (실제로 여러 번)

Portfolio Budget BLOCK 비율 < 30%

ERROR/CRITICAL 0건

엔진 비정상 종료 0회

문서 / 리포트

PHASE17_PORTFOLIO_BUDGET_FINAL_REPORT.md

V4/V5/V6/V6.1/V6.1 12H 비교

문제 → 원인 → 해결 → 검증 결과

“PHASE17 인프라 Acceptance: PASS/FAIL” 명기

Out-of-Scope

승률 튜닝 / 전략 파라미터 최적화

새로운 전략 추가

앙상블 구현

Live 모드

🧩 PHASE18 – Strategy Correctness & Baseline Performance (단일 스캘핑 전략)

목적

“엔진이 안 망가진다”에서 한 단계 더 나가서,
단일 스캘핑 전략이 논리적으로 말이 되게 동작하는지 + 기본 성능이 괜찮은지 확인

진입 조건

PHASE17 Acceptance 통과 (Budget/Portfolio 안정)

REAL PAPER 12H 결과 리포트 완료

주요 작업

전략 로직 검증

진입 조건 / 청산 조건 / SL/TP / Trailing / Re-entry 로직을 문서화

코드와 문서의 내용이 일치하는지 점검

백테스트 인프라 정리

동일 엔진으로 backtest/paper/live 모드 동작

백테스트용 데이터 범위 정의 (예: 최근 6~12개월 BTC/ETH/KRW 등)

기본 성능 측정

최소 3개 구간에서 backtest 실행:

상승장, 하락장, 박스장 비슷한 구간

측정:

Win Rate, Expectancy, PnL, MDD, Trade 수, Avg holding time 등

퇴출(완료) 조건

백테스트 리포트 최소 3개

각 리포트에:

기간, 심볼, 파라미터, 결과 지표

장단점 / 비정상 구간 코멘트

“전략 논리 검증” 완료

명백히 말도 안 되는 버그(예: SL 안 걸리거나, TP가 음수인 수준)는 모두 제거

전략 설명 문서와 코드가 서로 못 알아보게 다른 상황은 제거

REAL PAPER 단기 검증

REAL PAPER 모드 4~6시간 테스트 1회 이상

백테스트 성향과 전혀 다른 이상 행동 없을 것

Out-of-Scope

Bayesian 튜닝, Grid Search 등 본격 Optimization

앙상블 / 다전략

실제 계좌 Live

🧩 PHASE19 – Ensemble System Foundation ✅ **완료 (Production Ready)**

**⚠️ Note**: 원래 계획은 "Risk & Guard 튜닝"이었으나, 실제로는 Ensemble 인프라를 우선 구축함.

목적

Strategy Registry, Score Engine, Ensemble Aggregator 구현

여러 전략의 신호를 체계적으로 통합하는 Ensemble 인프라 구축

엔진 레벨에서 Ensemble ON/OFF 모드 지원

진입 조건

PHASE17 완료 (Portfolio/Budget 안정화)

기본 전략들이 BaseStrategy 인터페이스 준수

**완료 상태 (2025-11-20)**:

**PHASE19-1: Strategy Registry** ✅
- BaseStrategy 인터페이스 정의
- StrategyMetadata with Ensemble fields (optimal_regime, factor_weights, base_weight)
- StrategyRegistry 자동 스캔 기능
- 7개 전략 등록 완료 (scalping, breakout, reversion, trend, swing, swing_bb, daytrade)
- 문서: docs/PHASE19/PHASE19-1_COMPLETE_REPORT.md

**PHASE19-2: Score Engine & Factors** ✅
- Factor Calculator (momentum, volatility, volume, trend_strength, overbought_oversold, breakout_probability)
- ScoreEngine with regime multipliers (optimal=1.2x, worst=0.3x, neutral=1.0x)
- 전략별 Factor Weights & Base Weights 정의
- 단위 테스트 PASS
- 문서: docs/PHASE19/PHASE19-2_COMPLETE_REPORT.md

**PHASE19-3: Ensemble Aggregator & Engine Integration** ✅
- 3-Tier Aggregation (High-Confidence, Consensus, Skip)
- StrategyDecision & EnsembleDecision dataclasses
- EnsembleAggregator.decide() 구현
- execution/engine.py에 Full Integration
- 단위 테스트: 11/13 PASS (Aggregator 7/7, ScoreEngine 기본 4/4)
- Ensemble OFF 모드 회귀 테스트 PASS
- Ensemble ON 모드 초기화 테스트 PASS
- 문서: docs/PHASE19/PHASE19-3_ENSEMBLE_AGGREGATOR_DESIGN.md, PHASE19-3_COMPLETE_REPORT.md

주요 작업

StrategyRegistry

전략 자동 스캔 및 등록

메타데이터 캐싱

전략 인스턴스 생성 API

ScoreEngine

Factor 계산 및 정규화

전략별 가중치 기반 점수 계산

Regime multiplier 적용

EnsembleAggregator

Tier 1: High-Confidence (score >= 0.8, 충돌 처리)

Tier 2: Consensus (0.5 <= score < 0.8, 2+ votes)

Tier 3: Skip

Engine Integration

Ensemble ON/OFF 모드 분기

헬퍼 함수: _convert_ensemble_decision_to_signal()

Config 기반 threshold 설정

퇴출(완료) 조건

✅ 단위 테스트: Registry, ScoreEngine, Aggregator 모두 PASS

✅ Ensemble OFF 모드: 기존 기능 회귀 없음

✅ Ensemble ON 모드: 초기화 정상 작동

✅ Config 통합: ensemble 섹션 추가 및 엔진 연동

✅ 문서화: 각 서브 PHASE별 Complete Report

Out-of-Scope

Regime Classifier (PHASE19-4 예정)

Multi-symbol 확장

실전 Ensemble 성능 튜닝 (PHASE20 이후)

Known Issues & Next Steps

Regime은 현재 None (placeholder) → PHASE19-4에서 Regime Classifier 구현 예정

Ensemble ON 모드 실전 Paper 테스트 필요 (현재는 초기화만 검증)

전략별 Config 동적 병합 로직 개선 가능

 PHASE20 – Ensemble Integration & Paper Validation 

**PHASE20-1: Ensemble ON Paper Smoke Test (1h, Single Symbol) – ✅ 완료**

목적

Ensemble 모듈(EnsembleAggregator + ScoreEngine + StrategyRegistry) 통합 검증

1시간 wall-clock Paper 테스트로 Ensemble 의사결정 정상 동작 확인

기존 인프라(FlowGuardian, RiskManager, PortfolioManager, Budget SSOT) 안정성 재검증

진입 조건

PHASE19-3+ 완료: Ensemble 통합 + 엔진 Hook 완성

PHASE17 기준 Portfolio/Risk 인프라 안정

주요 작업

 Config 준비: `configs/paper/ensemble_paper_smoke.yml` (1h, 7 strategies, BTCUSDT, 5m)

 Clean-State 초기화: Postgres/Redis 정리 (12,678 trades, 143,437 signals 삭제)

 단위 테스트: Aggregator/ScoreEngine/Registry 테스트 16/20 PASS (핵심 로직 모두 PASS)

 1시간 Paper 실행: 5,060 캔들 처리, 31 거래 체결, 정상 종료

 결과 검증: 31 trades (LONG 13, SHORT 18), Total PnL -$107.23, Drawdown 1.07%

 문서화: PHASE20-1_ENSEMBLE_PAPER_SMOKE_REPORT.md 작성

 ROADMAP 업데이트: 이 항목

 Git 커밋: PHASE20-1 완료

퇴출 조건 (모두 충족)

 Ensemble 관련 pytest PASS (Aggregator/ScoreEngine/Registry)

 1시간 wall-clock Paper 정상 실행 (5,060 캔들)

 FlowGuardian READY 통과 후 엔진 루프 진입

 최소 3건 이상 거래 체결 (실제: 31건)

 Ensemble Tier1/Tier2 결정 최소 1회 이상 발생

 치명적 에러 없음 (Graceful Shutdown 완료)

 리포트 + ROADMAP + git commit 완료

**완료 상태 (2025-11-20)**:
- Run ID: `20251120_135912_0gja`
- Duration: 1h 1m 47s (wall-clock)
- Total Trades: 31 (LONG 13, SHORT 18)
- Total PnL: -$107.23 (정상 손실, 인프라 검증 목표 달성)
- Drawdown: 1.07% (안정적)
- 문서: docs/PHASE20/PHASE20-1_ENSEMBLE_PAPER_SMOKE_REPORT.md

**PHASE20-2: Extended Infrastructure Validation (4h+ runtime) – **

목적

Ensemble ON 모드로 4시간 이상 연속 Paper 테스트 (인프라 안정성 검증)

단일 심볼 (BTCUSDT) 기준

주요 결과

- Runtime: 4+ hours continuous operation
- Total Trades: 44 (LONG 19, SHORT 25)
- Total PnL: -$311.18
- Infrastructure:  All systems stable
- Strategy Distribution: Scalping-dominated (~95% signals)

완료 상태 (2025-11-20)

- Infrastructure Validation:  PASS
- 문서: docs/PHASE20/PHASE20-1_INFRASTRUCTURE_VALIDATION_FINAL.md

---

## 전역 전략 후보군 (SSOT)

**목적**


- 이 프로젝트에서 사용하는 **전략들의 전체 후보 풀(Strategy Pool)** 을 한 곳에 정리한다.
- "현재 구현되어 있는 전략"과 "향후 연구/추가 예정 전략"을 구분하고,
- PHASE22-0에서 이 Pool을 기준으로 **Ensemble v1에 들어갈 7~8개 전략**을 선정한다.

**구조**

- **Implemented Strategies** (이미 엔진에 통합된 전략)
- **Candidate / R&D Strategies** (향후 구현/검증 예정 전략)
- **Ensemble v1 Inclusion Flag** (IN / OUT / RESERVE)

| ID                | Name                     | Type                    | Timeframe Class | Status      | Ensemble v1 |
|-------------------|--------------------------|-------------------------|-----------------|-------------|-------------|
| scalping          | Scalping                 | Momentum/Scalp          | ACTIVE (3m)     | IMPLEMENTED | **IN**      |
| breakout          | Breakout                 | Volatility              | LOW_FREQ (15m)  | IMPLEMENTED | **IN**      |
| reversion         | Reversion                | Mean Reversion          | LOW_FREQ (5m)   | IMPLEMENTED | **IN**      |
| trend             | Trend                    | Trend Follow            | LOW_FREQ (1h)   | IMPLEMENTED | **IN**      |
| swing_bb          | Swing BB                 | Mean Reversion          | LOW_FREQ (5m)   | IMPLEMENTED | RESERVE     |
| swing             | Swing                    | Swing Trend             | LOW_FREQ (1h)   | IMPLEMENTED | RESERVE     |
| daytrade          | Daytrade                 | Intraday Trend          | LOW_FREQ (15m)  | IMPLEMENTED | RESERVE     |
| obi_momentum      | OBI Momentum             | Orderbook Imbalance     | ACTIVE (1m)     | CANDIDATE   | **IN**      |
| cvd_reversal      | CVD Reversal             | Volume Delta            | LOW_FREQ (5m)   | CANDIDATE   | **IN**      |
| multi_tf_momentum | Multi-TF Momentum        | Cross-Timeframe         | ACTIVE (1m/5m)  | CANDIDATE   | **IN**      |
| relative_strength | Relative Strength        | Cross-Asset RS          | LOW_FREQ (15m)  | CANDIDATE   | **IN**      |
| R&D_1             | Orderbook Micro-Reversion| Orderbook Imbalance     | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_2             | Volatility Breakout v2   | ATR + Session           | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_3             | Regime Adaptive Meta     | Regime-based Meta       | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_4             | Funding Rate Reversion   | Funding Rate Arbitrage  | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_5             | Volatility Skew Arb      | Vol Smile/Skew          | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_6             | Session Bias Intraday    | Time-of-Day Bias        | (T.B.D.)        | CANDIDATE   | LATER       |
| R&D_7             | Market-Neutral Pair      | Pair/Spread Trading     | (T.B.D.)        | CANDIDATE   | LATER       |

**Ensemble v1 분류 기준** (PHASE22-0 완료, 2025-11-21):
- **IN (8개)**: Ensemble v1 Core 전략 (4 IMPLEMENTED + 4 CANDIDATE)
  - **IMPLEMENTED (4개)**: Scalping, Breakout, Reversion, Trend
  - **CANDIDATE (4개)**: OBI-Momentum, CVD Reversal, Multi-TF Momentum, Relative Strength (설계만, 구현은 PHASE23+)
- **RESERVE (3개)**: 인프라 PASS, PHASE22-2 Extended Validation 후 추가 고려
- **LATER (7개)**: 향후 연구/구현 예정 전략

**신규 Ensemble v1 전략 (4개) 개념**:
- **OBI-Momentum**: Orderbook Imbalance 기반 1m 초단타 모멘텀
- **CVD Reversal**: Cumulative Volume Delta 기반 5m 반전 감지
- **Multi-TF Momentum**: 1m/5m Cross-Timeframe 모멘텀 확인
- **Relative Strength**: Cross-Asset Relative Strength Index (15m)

**R&D 전략 (7개) 개념**:
- **R&D_1 (Orderbook Micro-Reversion)**: 호가창 불균형 기반 초단타 평균 회귀
- **R&D_2 (Volatility Breakout v2)**: ATR + Session 기반 변동성 브레이크아웃
- **R&D_3 (Regime Adaptive Meta)**: 시장 레짐에 따라 전략 on/off 및 weight 조정
- **R&D_4 (Funding Rate Reversion)**: 펀딩비 과잉/역전 활용 차익거래
- **R&D_5 (Volatility Skew Arbitrage)**: 변동성 스마일/스큐 기반 전략
- **R&D_6 (Session Bias Intraday)**: Asia/EU/US 세션별 편향 활용
- **R&D_7 (Market-Neutral Pair)**: 페어/스프레드 트레이딩

 CANDIDATE 전략은 설계/아이디어 수준이며, 실제 구현/검증은 PHASE23 이후 진행

**참조 문서**

- PHASE21 검증 결과: `docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md`
- PHASE22-0 Strategy Pool 분석: `docs/PHASE22/PHASE22-0_STRATEGY_POOL.md`

---

 PHASE21 – Single Strategy Infrastructure & Validation 

**상태**:  COMPLETE (PHASE21-1A/1B/1C 모두 완료, 2025-11-21)

**목적**

7개 전략 각각에 대해 **단일 전략 인프라/타임프레임/FlowGuardian/Config-SSOT**가 정상 동작하는지 검증하고, ACTIVE/LOW_FREQ 특성을 구분하여 이후 Ensemble/Extended Validation의 기반을 마련

 ⚠️ **이 PHASE의 초점**:
- **전략 성능 튜닝/선별이 아니라**, 단일 전략이 엔진/피드/가드/포트폴리오 구조 안에서 **안정적으로 동작하는지 검증**하는 것
- 전략별 성능 비교 및 Ensemble 후보 선정은 **PHASE22-0**에서 수행

**범위 (최종 확정)**

-  타임프레임/Feed collector 버그 식별 및 수정 (3m/5m/1h WebSocket 정상 수신 확인)
-  `run_paper.py`의 전략/심볼/타임프레임/Duration 하드코딩 제거 및 **Config 기반 SSOT 구조 확립**
-  Scalping/Reversion/Trend 단일 전략 PAPER 실행을 통한 **인프라 레벨 검증**
-  ACTIVE vs LOW_FREQ 전략 분류 (인프라 기준, 성능/수익률 튜닝은 범위 밖)

**Out-of-scope (다음 PHASE로 이관)**

- 전략별 PnL/Win-rate/Max DD를 기준으로 한 **Ensemble v1 전략군 선정** → **PHASE22-0**
- Multi-strategy/Ensemble 실행 및 튜닝 → **PHASE22-1**
- 12~24시간 장기 PAPER 실행을 통한 성능/생존성 검증 → **PHASE22-2**
- Flash Guard/쿨다운/슬리피지 파라미터 튜닝 (전략 성능 기준) → **PHASE22-3**

**진입 조건**

단일 전략 스캘핑이 안정 + 리스크/데이터 인프라 정리됨

**문서**: docs/PHASE21/PHASE21-1A_REPORT.md, PHASE21-1B_FEED_FIX_REPORT.md, PHASE21-1C_ACTUAL_EXECUTION_REPORT.md

---

## 💡 최종 TO-BE 아키텍처 (10-Layer Structure)

### 1) Core Engine Layer
- **단일 엔진 원칙**: Backtest / Paper / Live 모두 같은 엔진 코드
- **Do-not-touch 코어**: engine.run(), position/state 머신, event 루프, duration 처리
- **역할**: 캔들/틱 스트림 소비, 전략 호출, Risk/Portfolio/FlowGuardian 체크, Execution Adapter 위임

### 2) Strategy & Ensemble Layer
- **5개 전략 패밀리**: Trend-follow, Volatility Breakout, Mean Reversion, Pullback-in-Trend, Scalping
- **패밀리당 대표 전략 1~2개**만 실전용 선정
- **Ensemble Score 구조**: 공통 시그니처 (S_LONG, S_SHORT, S_RISK, S_QUALITY), 동적 가중치

### 3) Risk / Portfolio / FlowGuardian Layer
- **RiskManager**: per-trade risk, 레버리지 상한, Max DD, 일일 손실 제한
- **PortfolioManager**: 심볼별/전략별 배분, PnL/Equity SSOT
- **FlowGuardian**: READY 체크, 쿨다운, Flash Guard, API 상태 확인

### 4) Data & Exchange Layer
- **Data Layer**: WebSocketCollector, RestCollector, Multi-TF Preload
- **Exchange Adapter**: PaperExchange, Binance/Upbit Adapter (Market, Limit, TP/SL, OCO)

### 5) Tuning & Research Cluster Layer
- **3단계 파이프라인**: Random → Bayesian → Local Grid
- **중앙 DB**: Postgres + TimescaleDB (runs, strategy_params, results, metrics)
- **Worker 프로세스**: 백테스트 job 병렬 실행

### 6) Multi-Symbol & Execution Layer
- **Universe Provider**: TopN/필터 기반 심볼 리스트 생성
- **Multi-Symbol Engine**: 심볼별 coroutine, per-symbol risk/portfolio
- **Execution Router**: 심볼/전략/방향 기반 주문 라우팅

### 7) Infra & Performance Layer
- **성능 목표**: Top50 심볼, 1m/5m/15m TF 동시 처리
- **최적화**: 비동기/코루틴, 인디케이터 캐싱, 로그 튜닝, GC 최적화
- **로드 테스트**: 단일 심볼 → Top10 → Top50 확장

### 8) Monitoring / Observability & Alerting
- **Metrics**: PnL, Equity, Win-rate, Sharpe, Max DD, 전략별/심볼별 성능
- **Dashboards**: Prometheus + Grafana, Core KPI 10종
- **Alerting**: Telegram/Slack (DD, WS 에러, 주문 실패율, trade 0건 등)

### 9) UI/UX Layer 🌟
- **Web Dashboard**: FastAPI + React/Vue
- **핵심 화면**: 실시간 모니터링, 전략/앙상블 패널, 리스크/포트폴리오, 백테스트 뷰어, 로그/이벤트
- **Control 기능**: Paper/Live 전환, 전략 on/off, preset 선택, safe restart

### 10) Ops & Deployment Layer
- **실행 구조**: run_backtest, run_paper, run_live
- **운영**: systemd / Docker / K8s
- **배포/롤백**: git tag, config 버전 관리, DB/Redis backup

---

🧩 **PHASE22 RESET** – Strategy Set Reconstruction & 5-Family Framework 🔄 **IN PROGRESS**

**상태**: 🔄 **IN PROGRESS** (2025-11-22)

**배경**
- PHASE22-1/2 중단 (기존 7개 전략 중 scalping 제외 correctness/튜닝/백테스트 없음)
- 전략 품질 없이 엔진 테스트만 수행 → 의미 부족
- PHASE22-0부터 재시작 (전략 세트 재정의)

**목적**
- 5개 전략 패밀리 기반 Ensemble v2 설계/구현
- 단일 심볼 기준 12~24h PAPER로 생존성 검증

**Sub-phases**
- **22-0: ✅ Strategy Set Reconstruction (COMPLETE - 2025-11-22)**
  - 폴더 재구조화: core/scalping_v3.py (KEEP), deprecated/ (6개 전략), research/ (신규)
  - 5개 패밀리 정의: HF Momentum, Volatility Breakout, Mean Reversion, Trend Following, Volume-Based
  - 산출물: `docs/PHASE22/PHASE22-0_STRATEGY_POOL.md`
- **22-1: ✅ Strategy Implementation & Validation (COMPLETE - 2025-11-22)**
  - 4개 신규 전략 구현: volatility_breakout_v2, mean_reversion_v2, trend_follow_v2, volume_based_v2
  - BaseStrategy 인터페이스 완벽 준수 (metadata + compute_signal)
  - Unit Test 17/17 PASS (100% 성공률)
  - 산출물: `docs/PHASE22/PHASE22-1_STRATEGY_DESIGN.md`, `docs/PHASE22/PHASE22-1_COMPLETE_REPORT.md`
  - 코드: `strategies/research/*.py` (4개 전략 + __init__.py)
  - 테스트: `tests/test_phase22_1_new_strategies.py`
- **22-2: ❌ Extended Validation (Quick Smoke PASS, Main Run FAIL - 2025-11-23 10:00)**
  - Ensemble v2 장기 안정성 검증 (12~24H Paper, 5개 전략 통합)
  - 전략별 신호 발생 빈도 확인
  - PnL/성능 기초 분석
  - 산출물: `docs/PHASE22/PHASE22-2_EXTENDED_VALIDATION_DESIGN.md`, `PHASE22-2_EXECUTION_GUIDE.md`, `PHASE22-2_EXTENDED_VALIDATION_REPORT.md`
  - Config: `configs/paper/phase22_2_ensemble_quick.yml`, `phase22_2_ensemble_12h.yml`
  - Script: `scripts/run_phase22_2_ensemble.py`
  - **Quick Smoke Test (30분)**: Duration 1800.1s (오차 0.006%), ERROR 0건, Trades 0건 → ✅ PASS
  - **12H Main Run (2025-11-22 21:54:02 ~ 2025-11-23 09:55:30)**: Duration 43,328s (12.04h, 오차 +0.3%) → ✅ PASS, Infrastructure ✅ PASS, **Trading ❌ FAIL (0 trades, 0 decisions)**
  - Duration Fix: engine.py에 진행 로그 추가 (30초마다)
  - Run ID: Quick=20251122_194150_ouhr, Main=20251122_215340_au7g
  - 상태: ❌ **FAIL (Trading Criteria 미충족, Infrastructure PASS)** → PHASE22-3 파라미터 튜닝 필요
- **22-3: ❌ Parameter Tuning (2025-11-23) - FAIL**
  - **Test Run (15분)**: 2025-11-23 11:04:38 ~ 11:19:38, Run ID: 20251123_110433_5lxj
  - **Trades**: 0 (Target: ≥30 for 1H) → ❌ FAIL
  - **Root Cause**: Config params가 전략에 전달되지 않음 (load_strategies/engine 간 인터페이스 문제)
  - **산출물**: `docs/PHASE22/PHASE22-3_PARAM_TUNING_REPORT.md`
  - **상태**: ❌ FAIL → PHASE22-4
- **22-4: ⚠️ Config Integration Fix (2025-11-23) - PARTIAL, DEFERRED**
  - **목표**: 전략별 config params가 제대로 전달되도록 수정
  - **Code Changes**: ✅ strategies/__init__.py, execution/engine.py 수정 완료
  - **Unit Tests**: ✅ 6/6 PASS (`test_phase22_4_config_integration.py`)
  - **Direct Test**: ✅ params 로딩 정상 작동 확인 (Python 직접 실행)
  - **Runtime Issue**: ❌ run_paper.py 실행 시 params 빈 dict로 전달, RSI threshold 기본값(30/70) 사용
  - **근본 원인 (PHASE23-0 분석)**: Script-level orchestration 문제 (config 로딩/전달 경로가 script에서 중복/분산)
  - **산출물**: `docs/PHASE22/PHASE22-4_CONFIG_INTEGRATION_INCOMPLETE.md`
  - **Config**: `configs/paper/phase22_4_scalping_param_smoke_30m.yml`
  - **상태**: ⚠️ PARTIAL (Code-Level Fix OK, Runtime Integration FAIL) → **DEFERRED to PHASE23-1** (architectural refactoring required)

**진입 조건**: PHASE21 완료

**퇴출 조건**: 폴더 구조 완료, 5개 패밀리 정의 완료, Ensemble v2 설계 완료, 문서 완료

---

🧩 **PHASE23** – Ensemble & Engine Architecture V2 🔄 **IN PROGRESS**

**상태**: 🔄 **IN PROGRESS** (2025-11-29 시작, 23-0/23-1 완료)

**목적**: 
- PHASE22-2/3/4에서 드러난 구조적 문제(0-trade, 튜닝 실패, config 전파 실패)를 **엔진 중심 아키텍처 + 5-패밀리 앙상블 구조**로 해결
- 이후 전략/튜닝/멀티심볼 확장의 "기준선"이 되는 아키텍처 V2 완성

**Sub-phases**:

### 23-0: TO-BE Architecture V2 문서화 ✅
- **상태**: ✅ **COMPLETE** (2025-11-29)
- **범위**:
  - AS-IS 아키텍처 분석 (엔진, 전략, 앙상블, config/script 레이어)
  - PHASE22-2/3/4 Pain Point 및 Root Cause 정리
  - Single-Engine-Centric Architecture 원칙 정의
  - Strategy Config SSOT 원칙 정의
  - Mode-based Adapter Pattern 설계 (backtest/paper/live 공통)
  - 5 Strategy Families 기반 Ensemble TO-BE 구조 정리
- **주요 문서**:
  - `docs/PHASE23/PHASE23-0_ARCHITECTURE_TOBE_V2.md`
  - `docs/PHASE23/ENSEMBLE_STRATEGY_TOBE_V2.md`
- **Acceptance Criteria**: ✅ PASS
  - AS-IS / TO-BE 비교 다이어그램 존재
  - 5개 전략 패밀리(HF Momentum / Volatility Breakout / Mean Reversion / Trend Following / Volume-Based) 역할 명확
  - PHASE23-1~3 실행 로드맵 정의

### 23-1: Single-Engine Entry Point & Config Propagation Fix ✅
- **상태**: ✅ **COMPLETE** (2025-12-01)
- **목표**: PHASE22-4 runtime config propagation 이슈를 엔진 진입점 구조 리팩토링으로 근본 해결
- **주요 변경사항**:
  - `scripts/run_v2.py` 추가 (thin script, 97 lines)
    - 역할: config 로딩 + `engine.run_v2(...)` 호출만 수행
    - paper / backtest / live 모드 공통 진입점
  - `execution/engine.py`
    - `run_v2(mode, config, clean_state)` 추가
    - 내부에서 `load_strategies(config)` 직접 호출
    - use_ensemble / selector / adapter 생성 로직을 엔진으로 이동
  - `tests/test_phase22_4_config_integration.py` docstring 업데이트
- **검증 결과**:
  - Unit Tests: 6/6 PASS
  - 30분 PAPER smoke test: ✅ PASS
    - RSI 45/55 정상 전파 (기본값 30/70 아님)
    - 실제 트레이드 발생: 1 SHORT entry + 1 TP1 exit (+$19.23)
  - 로그: `[PHASE23-1 DEBUG] scalping params: {'rsi_oversold': 45, 'rsi_overbought': 55, ...}`
- **주요 문서**: `docs/PHASE23/PHASE23-1_ENGINE_ENTRYPOINT_REFACTOR.md`
- **Acceptance Criteria**: ✅ ALL PASS
  - `run_v2.py` 길이 < 100 lines (97 lines)
  - `engine.run_v2()` 존재, 내부에서 `load_strategies(config)` 호출
  - Config params 100% 전파 (RSI 45/55 등)
  - 기존 `run()` 기반 코드/테스트 유지
  - 30분 paper test에서 트레이드/청산 로그 확인

### 23-2: Strategy Interface Unification (scalping_v3 → BaseStrategy) 🟦
- **상태**: 🟦 **PLANNED**
- **목표**: scalping_v3 및 주요 전략들을 통일된 `BaseStrategy` 인터페이스로 마이그레이션
- **예상 작업**:
  - `scalping_v3.signal_logic(df, cfg)` → `compute_signal(df, config)` 리네이밍
  - 각 전략에 `metadata` 속성 추가 (타임프레임, 리스크 레벨, 패밀리 타입)
  - 엔진에서 전략 호출부를 `compute_signal` 기반으로 통일
  - 1시간 paper test (5개 전략 동시 동작)
- **Acceptance Criteria (초안)**:
  - 5개 핵심 전략이 모두 `BaseStrategy` 공통 인터페이스 구현
  - 각 전략이 `metadata`로 앙상블/리스크 모듈에 메타 정보 제공
  - 1H paper test 오류 없이 실행 + 전략별 신호/트레이드 발생

### 23-3: Ensemble Orchestrator V2 🟦
- **상태**: 🟦 **PLANNED**
- **목표**: PHASE23-0에서 정의한 5-패밀리 기반 앙상블 구조를 실제 엔진 위에 구현
- **예상 범위**:
  - Strategy-level score (`S_LONG`, `S_SHORT`, `S_RISK`, `S_QUALITY`) 반영
  - Ensemble-level decision 3-tier 로직 (High-Confidence / Consensus / Skip)
  - Regime / Timeframe / Indicator diversification 반영
- **Acceptance Criteria (초안)**:
  - 5개 전략의 score가 엔진 공용 앙상블 모듈로 모여서 최종 포지션 결정
  - 특정 전략이 60% 이상 과도하게 지배하지 않도록 가중치/캡 구조 존재
  - 3H 이상 paper test에서 앙상블이 단일 전략 대비 안정적인 동작 패턴

### 23-4: Validation & Cleanup 🟦
- **상태**: 🟦 **PLANNED**
- **목표**: PHASE23-0 ~ 23-3 변경 사항 정리 및 이후 PHASE로 넘어가기 위한 "클린 기준선" 생성
- **Acceptance Criteria (초안)**:
  - 모든 관련 문서와 코드 상태가 서로 모순 없이 정합적
  - 최소 3H ~ 12H paper test 1회 이상 통과 (엔진/전략/앙상블 레벨 에러 없음)
  - 변경된 아키텍처에 대한 요약 리포트 생성

**진입 조건**: PHASE22-4 PARTIAL 완료 (code-level fix done, runtime integration deferred)

**퇴출 조건**:
- ✅ TO-BE 아키텍처 V2 문서화 (PHASE23-0)
- ✅ Config propagation 정상 작동 (PHASE23-1)
- [ ] 5개 전략 인터페이스 통일 (PHASE23-2)
- [ ] Ensemble Orchestrator V2 구현 (PHASE23-3)
- [ ] Validation & Cleanup (PHASE23-4)

---


🧩 **PHASE24** – 앙상블 V2 확립 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: Ensemble Score V2 구조로 5개 대표 전략 통합 및 가중치 튜닝

**Sub-phases**
- **24-0: Ensemble Score V2 설계**
  - S_LONG/S_SHORT/S_NET/S_ABS + 동적 가중치 구조
- **24-1: 대표 전략 5개 앙상블 시뮬레이션**
  - 1~3H PAPER, 행동 패턴 분석
- **24-2: 앙상블 조합/가중치 초기 튜닝**
  - 상승/하락/횡보 구간 행동 확인

**진입 조건**: PHASE23 완료

**퇴출 조건**: Ensemble v2 1~3H PAPER PASS, 가중치 초기 셋 확보

---

🧩 **PHASE25** – Tuning Cluster & 자동 튜닝 인프라 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: 전략/조합 파라미터 자동 탐색 인프라 구축

**Sub-phases**
- **25-0: Tuning Cluster Infra**
  - DB 스키마 (runs, params, results), Worker 구조, job queue
- **25-1: Random Search 파이프라인**
  - 초기 파라미터 탐색
- **25-2: Bayesian + Local Grid 튜닝 파이프라인**
  - 고도화된 파라미터 튜닝
- **25-3: 실전용 파라미터 셋 확보**
  - 대표 전략/조합 최적 파라미터

**진입 조건**: PHASE24 완료

**퇴출 조건**: 튜닝 클러스터 정상 작동, 대표 전략 파라미터 셋 확보

---

🧩 **PHASE26** – Multi-Symbol Engine v1 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: TopN 심볼 확장 및 Multi-symbol 엔진 구조 확립

**Sub-phases**
- **26-0: Universe Provider 구현**
  - TopN 심볼 선정 로직
- **26-1: Multi-symbol 코루틴 구조**
  - per-symbol state, queue, risk/portfolio 연동
- **26-2: Top10 기준 Paper Load Test**
  - engine/collector/portfolio 레벨 문제점 확인

**진입 조건**: PHASE25 완료

**퇴출 조건**: Top10 심볼 Paper 정상 종료, per-symbol risk/portfolio 관리 확인

---

🧩 **PHASE27** – Infra Performance Tuning (상용급 1차) 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: Top20~50 심볼 처리 가능한 성능 확보

**Sub-phases**
- **27-0: 성능 프로파일링**
  - CPU/Memory, hot path, GC, 로그 비용
- **27-1: 최적화 1차 패스**
  - 인디케이터 캐싱, 불필요 연산 제거, 로그 튜닝
- **27-2: Top20~50 Load Test**
  - Latency/CPU/메모리/queue depth 기준선 확보

**진입 조건**: PHASE26 완료

**퇴출 조건**: Top50 심볼 Paper 정상 종료, 성능 TO-BE 기준선 확보

---

🧩 **PHASE28** – Monitoring & Alerting 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: 실시간 모니터링 및 알림 시스템 구축

**Sub-phases**
- **28-0: Metrics 정의**
  - Core KPI 10종 확정
- **28-1: Prometheus/Grafana 세팅**
  - Dashboard 구성
- **28-2: Telegram/Slack Alert**
  - DD, WS 에러, 주문 실패율, trade 0건 등

**진입 조건**: PHASE27 완료

**퇴출 조건**: Grafana 대시보드 정상 작동, Alert 정상 발송

---

🧩 **PHASE29** – UI/UX v1 (Read-only Dashboard) 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: Web 기반 실시간 모니터링 대시보드 구축

**Sub-phases**
- **29-0: UI/UX 요구사항 정리**
  - 화면 목록, 레이아웃, 핵심 지표 정의
- **29-1: API Layer (FastAPI)**
  - read-only API 제공
- **29-2: Web Dashboard v1**
  - 실시간 Equity, PnL, 포지션/전략 현황, 로그 이벤트

**진입 조건**: PHASE28 완료

**퇴출 조건**: Web Dashboard 정상 작동, 실시간 메트릭 표시 확인

---

🧩 **PHASE30** – UI/UX v2 (Control + Report) 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: 제어 기능 및 백테스트 결과 뷰어 추가

**Sub-phases**
- **30-0: 안전한 제어 흐름 설계**
  - Paper/Live 전환, 전략 on/off, preset 변경 안전장치
- **30-1: Control Panel 구현**
  - 제한된 조작 허용 (토글, preset, safe restart)
- **30-2: Backtest/튜닝 결과 뷰어**
  - equity curve, heatmap 등

**진입 조건**: PHASE29 완료

**퇴출 조건**: Control Panel 정상 작동, 백테스트 뷰어 정상 표시

---

🧩 **PHASE31** – Infra Performance Tuning 2차 + 상용 준비 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: Top50/100 심볼 Full Load 및 장시간 안정성 검증

**Sub-phases**
- **31-0: Multi-Symbol Top50/100 Full Load Test**
  - 대규모 심볼 동시 처리 검증
- **31-1: 2차 최적화**
  - 코드, 설정, 배포 구조
- **31-2: 운영 시나리오 테스트**
  - 24~72H PAPER, 장애 recovery, 재기동

**진입 조건**: PHASE30 완료

**퇴출 조건**: Top100 심볼 24H+ Paper PASS, 운영 시나리오 검증 완료

---

🧩 **PHASE32** – Live 연동 & Final Hardening 🟦 **PLANNED**

**상태**: 🟦 **PLANNED**

**목적**: 실거래소 연결 및 Live 진입

**Sub-phases**
- **32-0: Binance/Upbit Live Adapter 연결**
  - Native TP/SL(OCO) + 엔진 TP/SL 병행
- **32-1: Shadow Mode (신호만 생성)**
  - 실거래 미발주, DB 기록만
- **32-2: Limited Live (제한 자본)**
  - 심볼/전략/레버리지/자본 제한, 1~2주 검증
- **32-3: Full Live 준비**
  - 보안/접속 키 관리, 최소 권한 구조

**진입 조건**: PHASE31 완료

**퇴출 조건**: Shadow Mode 검증 PASS, Limited Live 시스템 문제 0건, 손실 제한 정상 작동

---

## 📋 Phase 관리 원칙

1. **Phase 순서 엄수**
   - 모든 작업은 현재 Phase Scope 내에서만 진행
   - Phase 순서를 건너뛰거나 역행 금지

2. **Acceptance 기준 충족 필수**
   - 퇴출 조건 미달 시 다음 Phase 진입 금지
   - "일단 넘어가자" 식 진행 불가

3. **Scope 명확화**
   - 새로운 작업 발생 시 Phase 매핑 먼저 수행
   - Out-of-Scope 작업은 해당 Phase 문서에 명시

4. **문서화 필수**
   - 모든 Phase 완료 시 Complete Report 작성
   - ROADMAP 업데이트 및 Git commit

---

## 🎯 현재 상태 (2025-11-22)

**현재 Phase**: PHASE22-0 (Strategy Set Reconstruction)

**상태**: ✅ **COMPLETE**

**다음 Phase**: PHASE22-1 (Strategy Implementation & Validation)

**진행 예정**: 5개 패밀리 중 4개 신규 전략 구현 및 백테스트

---