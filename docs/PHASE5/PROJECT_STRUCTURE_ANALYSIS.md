# Future Alarm Bot - Complete Project Structure

최종 업데이트: 2025-10-30
상태: 전체 구조 분석 완료

---

## 1) 루트 레벨 구조

```
/future_alarm_bot/
├── [Configuration Files]
├── [Core Modules]
├── [Business Logic Modules]
├── [Infrastructure Modules]
├── [Data & Assets]
├── [Documentation]
├── [Testing & Scripts]
└── [Legacy/Archive]
```

---

## 2) 상세 디렉터리 구조 및 파일 목록

### 2.1 Configuration & Setup
```
configs/
├── breakout/
│   ├── breakout_logfix_20251026_173349/
│   ├── breakout_logfix_20251026_173539/
│   ├── breakout_smoke_20251026_084318/
│   └── [+18 configs]
├── daytrade/
│   ├── daytrade_smoke_20251026_084313/
│   ├── daytrade_smoke_20251026_215015/
│   ├── daytrade_v1/
│   └── [+21 configs]
├── reversion/
│   ├── reversion_smoke_20251026_084312/
│   ├── reversion_v1/
│   ├── reversion_v2_fixed_20251026_093205/
│   └── [+16 configs]
└── scalping/
    ├── scalping_baseline_5run_20251026_215522/
    ├── scalping_baseline_5run_v2_20251026_220121/
    ├── scalping_baseline_5run_v3_20251026_221216/
    └── [+25 configs]
```

### 2.2 Data Layer
```
data/
├── db/
│   └── trading.db
├── backtest_periods/
│   ├── BTCUSDT_15m_bear_2018.csv
│   ├── BTCUSDT_15m_covid_2020.csv
│   ├── BTCUSDT_15m_etf_anticip_24.csv
│   └── [+28 CSV files]
├── wfa_blocks/
│   ├── BTCUSDT_15m_2018_WFA01_OOS.csv
│   ├── BTCUSDT_15m_2018_WFA01_TRAIN.csv
│   └── [+154 CSV files]
└── [+17 additional CSV files]
```

### 2.3 Core Business Logic
```
strategies/
├── __init__.py
├── breakout.py
├── daytrade.py
├── ensemble.py
├── reversion.py
├── scalping.py
├── swing.py
└── trend.py
```

```
signals/
├── __init__.py
└── signal_generator.py
```

```
indicators/
├── __init__.py
└── core_indicators.py
```

### 2.4 Execution & Trading Engine
```
execution/
├── __init__.py
├── engine.py (38KB - main engine)
├── adapters/
│   ├── __init__.py
│   ├── brokers.py
│   ├── clocks.py
├── data_sources/
│   ├── __init__.py
│   ├── backtest.py
│   ├── live.py
├── executors/
│   ├── __init__.py
│   ├── live.py
│   ├── paper.py
│   ├── simulation.py
├── portfolio_manager.py
├── position_sizer.py
├── position_tracker.py
├── risk_manager.py
├── tp_manager.py
```

### 2.5 Data Collection Layer
```
collectors/
├── __init__.py
├── historical_collector.py
├── multi_historical_collector.py
├── rest_collector.py
├── websocket_collector.py
```

### 2.6 Common Utilities
```
common/
├── __init__.py
├── calculations.py
├── config_loader.py
├── config_validation.py
├── database.py
├── logger.py
├── messaging.py
├── performance.py
├── utils.py
```

### 2.7 Reporting & Analytics
```
reports/
├── __init__.py
├── backtest/
├── performance_reporter.py
├── results/
├── trading_reporter.py (24KB)
├── trades/
├── wfa_all_results_20251023_221154.json
├── wfa_results/
```

### 2.8 Testing Infrastructure
```
tests/
├── bat/
│   ├── test_backtest.bat
│   ├── test_paper.bat
├── integration/
│   └── test_trading_flow.py
├── scripts/
│   ├── analyze_backtest.py
│   ├── analyze_results.py
│   ├── check_config.py
│   ├── tune_scalping.py
│   ├── [+7 scripts]
├── check_signals.py
├── check_status.py
├── check_trades_table.py
├── test_collectors.py
├── test_db.py
├── test_db_check.py
├── test_fetch_signals.py
├── test_full_flow.py
├── test_refactoring.py
├── test_system.bat
├── test_system.py
├── test_trading.py
```

### 2.9 Logging & Monitoring
```
logs/
├── application/
├── errors/
├── performance/
├── signals/
├── [+7 subdirs]
```

### 2.10 Scripts & Tools
```
scripts/
├── tuning/
│   ├── tune_breakout.py
│   ├── tune_daytrade.py
│   ├── tune_reversion.py
│   ├── tune_scalping.py
│   ├── tune_swing.py
│   ├── tune_trend.py
├── add_indicators_to_wfa.py
├── analyze_wfa_results.py
├── apply_log_improvements.py
├── [+23 scripts]
```

### 2.11 Documentation
```
docs/
├── PHASE2/
├── PHASE3/
├── PHASE4/
├── PHASE5/
│   ├── REFACTORING_data_collector_v1.md
│   ├── REFACTORING_flow_guardian_gate.md
│   └── REFACTORING_monitoring_analytics.md
├── [+6 docs]
```

### 2.12 Legacy & Archives
```
_archived/
├── COMPLETE/
├── config_backups/
├── execution_old/
├── [+109 files]
```

```
_archived_md/
├── ANALYSIS.md
├── ARCHITECTURE_CHECKLIST.md
├── [+18 docs]
```

### 2.13 Container & Infrastructure
```
├── Dockerfile
├── Dockerfile.backtest
├── Dockerfile.ensemble
├── Dockerfile.trading
├── docker-compose.yml
├── requirements.txt
├── pgdata/ (PostgreSQL)
├── redisdata/ (Redis)

## 업데이트 (2025-11-03) — PR7-2: 앙상블 Paper 운용 가이드

- 기본 전략: 1컨테이너(앙상블 Paper)로 6전략 동시 실행 → 리소스/검증 효율 극대화
- 격리 필요 시: `docker compose --profile paper-<strategy> up -d`로 개별 전략만 실행/디버깅
- 검증 데이터: `monitoring.signals`(전략별 신호), `trading.decisions`(앙상블 결정)
- Paper 수용 기준: decisions 중심(6전략 모두 ≥1건 참여/기여), 포트폴리오/리스크 제약 로그 확인
- 거래 기록: `trading.trades`는 집행(Paper/LIVE) 시에만 사용. trial_id는 스키마에 없으며, 세그먼트는 `monitoring.gate_results.trial_id`로 관리

---

## 3) 주요 파일 크기 및 복잡도

### 대형 파일 (10KB+)
- `execution/engine.py`: 38KB (주 엔진)
- `reports/trading_reporter.py`: 24KB (리포팅)
- `execution/risk_manager.py`: 18KB (리스크 관리)
- `strategies/ensemble.py`: 20KB (앙상블 전략)
- `common/messaging.py`: 8KB (메시징)

### 중형 파일 (5-10KB)
- `execution/portfolio_manager.py`
- `execution/position_sizer.py`
- `execution/position_tracker.py`
- `execution/tp_manager.py`
- `signals/signal_generator.py`
- `collectors/websocket_collector.py`

---

## 4) 현재 아키텍처 패턴 분석

### 계층 분리 상태
- **✅ 잘 분리됨**: Data(Collection) → Business(Strategies/Signals) → Execution(Engine) → Infrastructure(DB/Logs)
- **✅ 모듈화**: 각 도메인별 디렉터리 (strategies/, execution/, collectors/, common/, reports/)
- **✅ 테스트 커버리지**: tests/에 풍부한 스크립트/배치 파일

### 문제점 식별
- **❌ 모니터링/애널리틱스 분산**: `common/performance.py`, `reports/`, `common/messaging.py`에 흩어짐
- **❌ 게이트 없음**: PAPER/LIVE 진입 전 엔드투엔드 검증 부재
- **❌ 인터페이스 계약 부족**: 모듈 간 호출이 타입 안정성 없이 직접 호출

### 리팩토링 기회
- **monitoring/**: `common/performance.py` + `common/messaging.py`의 모니터링 부분 통합
- **analytics/**: `reports/trading_reporter.py` + 메트릭 계산 로직 재구성
- **core/interfaces.py**: 프로토콜 정의로 모듈 간 계약 명시화
- **core/flow_guardian.py**: 엔드투엔드 게이트 추가

---

## 5) FlowGuardian 게이트 통합 포인트

### 기존 모듈 재사용 매핑
```python
# core/interfaces.py (새 파일, PR 제안)
class IDataSource(Protocol):
    def fetch(self, candle_range: Dict) -> pd.DataFrame: ...

class IStrategy(Protocol):
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Any]: ...

class IRisk(Protocol):
    def assess(self, order_intent: Dict, account: Dict) -> Dict[str, Any]: ...

class IBroker(Protocol):
    def dry_run(self, order_intent: Dict) -> Dict[str, Any]: ...

class IMetrics(Protocol):
    def compute(self, trade_log: Dict) -> Dict[str, Any]: ...
```

### 구체적 매핑
- **IDataSource**: `execution/data_sources/backtest.py::BacktestDataSource` 또는 `collectors/rest_collector.py::fetch_history`
- **IStrategy**: `signals/signal_generator.py::SignalGenerator` (단일 전략 모드)
- **IRisk**: `execution/risk_manager.py` 래핑
- **IBroker**: `execution/executors/simulation.py` 또는 `execution/executors/paper.py`
- **IMetrics**: `metrics/compute.py` (새 파일) + `reports/trading_reporter.py` 재사용

---

## 6) Monitoring/Analytics 리팩토링 포인트

### 대상 모듈 이동
```text
# Before
common/performance.py (모니터링 + 메트릭)
common/messaging.py (알림 + 로깅)
reports/trading_reporter.py (HTML/메트릭 계산)

# After
monitoring/
├── performance_monitor.py (← common/performance.py)
├── telemetry_profiler.py (심층 프로파일링)
└── __init__.py (FlowGuardian + 전역 모니터)
analytics/
├── trade_analyzer.py (거래 성과 분석)
├── strategy_evaluator.py (전략 비교)
└── report_generator.py (← reports/trading_reporter.py)
```

### 호환성 유지 전략
- `common/performance.py` → 동일 이름으로 re-export 제공
- `reports/trading_reporter.py` → `analytics/report_generator.py`에서 import/호출
- 점진적 마이그레이션: 기존 코드 수정 최소화

---

## 7) 다음 단계 권장사항

### 우선순위 1: FlowGuardian 게이트
1. `core/interfaces.py` PR 제안 (프로토콜 정의)
2. `core/flow_guardian.py` 구현 (상태머신 + selftest)
3. `engine/run.py` READY 검증 훅
4. `metrics/compute.py` 메트릭 계산
5. `tests/flow/test_flow_guardian.py` 회귀 테스트

### 우선순위 2: 모니터링/애널리틱스 통합
1. `monitoring/` 패키지 생성
2. `analytics/` 패키지 생성  
3. 기존 모듈 이관 (re-export로 호환성 유지)
4. `collectors/websocket_collector.py` + `execution/engine.py`에 emit_event 훅

### 안전성 확보
- 게이트 먼저 적용 → 리팩토링 중 오작동 구조적 차단
- 인터페이스 계약으로 타입 안전성 향상
- 테스트 피라미드 유지 (Unit → Contract → Flow/E2E)

---

상태: 프로젝트 구조 완전 분석 완료  
다음: GPT 컨설팅 후 구체적 리팩토링 계획 수립

## 업데이트 (2025-11-04) — PR7-4: Multi-TF Preload + FlowGuardian

### 요약
- 운영 기본을 "Multi-Timeframe Preload + 동일 TF WebSocket 구독"으로 전환합니다.
- 기존 Option A(1m 단일 구독 → 엔진 리샘플)는 "백업(fallback)" 경로로 유지합니다.

### 구조 관점 반영
- 2.5 Data Collection Layer: `websocket_collector.py`가 다중 TF 구독 지원, `rest_collector.py`로 각 TF 프리로드(REST) 표준화.
- 2.4 Execution & Trading Engine: 엔진 버퍼 키를 `(symbol, timeframe)`로 해석. 리샘플은 폴백/비상시에만 사용.
- 2.6 Common Utilities: `common/utils.make_streams`가 멀티 TF 스트림을 생성.
- 2.3 Core Business Logic: 전략 로직 변경 없음(게이트/데이터 경로만 개선).

### 설정 정책(config.yml)
- `flow_guardian.enabled: true`
- `flow_guardian.essential_strategies: [scalping, daytrade]`
- `flow_guardian.startup_bars: {3m:1000, 5m:1000, 15m:1000, 1h:300, 4h:200}`
- `strategies.*.min_bars_for_signal: 60`

### 수용 기준(불변)
- `tests/flow/test_flow_guardian.py` 통과, pre-commit(ruff/black/mypy/vulture, coverage>85%) 통과
- `logs/trial_0000.json` 생성, DB `score_total` == JSON `score_total`
- 시작 2~5분 내 6전략 READY → 앙상블 자동 집계 시작

### 운영 체크리스트(핵심 로그)
- `📥 Multi-TF Preload: ['3m','5m','15m','1h','4h']`
- `✅ [1h] ... 프리로드 완료`, `✅ [4h] ... 프리로드 완료`
- `✅ {strategy} READY ({tf}, {bars}개)` / 부족 시 `📥 On-demand backfill ...`
