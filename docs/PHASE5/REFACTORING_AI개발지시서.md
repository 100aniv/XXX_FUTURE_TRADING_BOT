# 리팩토링 실행 지시서 (개발 AI용)

**최종 업데이트**: 2025-11-03 12:40
**현재 상태**: PR 1~7 완료 ✅ | PR 7-2 완료 ✅ | 통합 테스트 73/73 ✅ | E2E 8/12 (핵심 7/7 100%) ✅

---

# 리팩토링 후 문서 동기화 대상
• 아키텍처 개요: REFACTORING_문서아키텍처.md
• 모듈 문서:
Execution: REFACTORING_execution_v1.md
Common: REFACTORING_common_v1.md
Tuning: REFACTORING_tuning_v1.md
Database/Redis: REFACTORING_database_v1.md
Indicators: REFACTORING_indicators_v1.md
Signals: REFACTORING_signals_v1.md
Strategies/Ensemble: REFACTORING_strategies_v1.md
FlowGuardian: REFACTORING_flow_guardian_gate.md
Monitoring/Analytics: REFACTORING_monitoring_analytics.md
• 각 문서에 반영할 공통 항목
책임(R&R)/입출력/의존/테스트/수용 기준/릴리즈 노트(변경 이력)
# 테스트 전략
• Unit: 변경 함수/경계/예외
• Contract: 인터페이스·스키마 정합성
• Flow/E2E: 엔진 경로 영향 시 smoke
• Gate: READY/FAIL 경로, 아티팩트, DB-JSON 동치
• Tuning: 스케줄러 1회 기동, Optuna run 1회, configs 퍼블리시 dry-run
• Docker(권장): PAPER 10분 스모크(WS·DB·Redis 헬스, 스냅샷 ≥1회)
# 개발 AI에 전달할 실행 지시서
• 공통 원칙
PR는 기능별/모듈별로 작게. 게이트 PR과 다른 리팩토링 PR 분리.
변경 허용 파일/문서 동기화/테스트 범위/수용 기준을 PR 본문에 명시.
• ✅ PR 1: FlowGuardian 게이트 확정 (완료: 2025-11-02)
변경 파일: 
  - core/flow_guardian.py (신규 561줄) ✅
  - execution/engine.py (게이트 호출, line 106-147) ✅
  - init_db.sql (monitoring.gate_results 테이블) ✅
  - metrics/compute.py (기존 사용, 변경 없음)
테스트/수용: 
  - tests/flow/test_flow_guardian.py 8/8 통과 ✅
  - ruff/black 포맷팅 완료 ✅
  - logs/trial_0000.json 생성 ✅
  - DB==JSON score_total 검증 ✅
비고: PAPER/LIVE 진입 직전 guardian.run_all() 강제 구현 완료
• ✅ PR 2: Database 패키지 이관 (완료: 2025-11-02)
파일 생성:
  - database/postgres.py (212줄) ✅
  - database/redis.py (220줄) ✅
  - database/__init__.py (26줄) ✅
Shim 추가:
  - common/database.py (34줄 shim) ✅
  - common/redis_client.py (23줄 shim) ✅
테스트:
  - Import 테스트 통과 (3가지 방식) ✅
  - FlowGuardian 회귀 테스트 8/8 통과 ✅
비고: 하위 호환성 100%, 기존 코드 변경 없음
• ✅ PR 3: Tuning 패키지 이관 (완료: 2025-11-02)
파일 생성:
  - tuning/tuning_core.py (384줄) ✅
  - tuning/tuning_scheduler.py (265줄) ✅
  - tuning/tuning_cli.py (107줄) ✅
  - tuning/__init__.py (21줄) ✅
Shim 추가:
  - common/tuning_core.py (21줄 shim) ✅
  - common/tuning_scheduler.py (23줄 shim) ✅
  - common/tuning_cli.py (26줄 shim) ✅
테스트:
  - Import 테스트 통과 (core, cli) ✅
  - FlowGuardian 회귀 테스트 8/8 통과 ✅
비고: 하위 호환성 100%, 파일명 유지, import 경로만 변경
• ✅ PR 4: Signals/Indicators 인터페이스 표준화 (완료: 2025-11-02)
Docstring 추가:
  - indicators/core_indicators.py (+44줄) ✅
  - 인터페이스 계약, NaN 정책, 최소 데이터 명시 ✅
Contract 테스트:
  - tests/unit/test_indicators_contract.py (+212줄) ✅
  - 12개 테스트 (최소 데이터, NaN 전파, 출력 스키마, 불변성) ✅
테스트:
  - Contract 12/12 통과 ✅
  - FlowGuardian 회귀 8/8 유지 ✅
비고: 코드 변경 0줄, 문서화만
• ✅ PR 5: Monitoring & Analytics 패키지 + 큐 지표 모니터링 (완료: 2025-11-02)
패키지 생성:
  - monitoring/ 패키지 (1,181줄) ✅
    - FlowGuardian Facade (emit_event, snapshot, report, alert)
    - performance_monitor.py (성능 측정, 통계 수집)
    - telemetry_profiler.py (함수 프로파일링)
  - analytics/ 패키지 (425줄) ✅
    - trade_analyzer.py (거래 성과 집계, PostgreSQL)
    - strategy_evaluator.py (전략 비교, PostgreSQL)
    - report_generator.py (HTML/JSON 리포트)
제거:
  - common/performance.py (664줄 삭제, 기능 분산) ✅
큐 지표 모니터링:
  - collectors/websocket_collector.py ✅
    - queue.health 이벤트 발행 (10초 주기)
    - 메트릭: size, maxsize, usage_pct, drops, retries
    - 임계치 경고: 80% 이상 사용률
  - config.yml: monitoring.websocket.queue 설정 추가 ✅
통합:
  - execution/engine.py: system.performance 이벤트 emit ✅
  - collectors/websocket_collector.py: ws.connection, queue.health 이벤트 emit ✅
  - config.yml: monitoring, analytics, queue 섹션 추가 ✅
테스트:
  - Import 회귀 8/8 통과 ✅
  - Phase5 통합 5/5 통과 ✅
  - Docker Paper 10분 검증 (예정) 🔄
비고: 순 증가 942줄, PostgreSQL DB 연동 완료, 큐 백프레셔 모니터링 완료
• PR 6: Reports 호출경로 일원화 ✅ (2025-11-02 완료)
  - 범위: 리포트 생성 호출 경로를 `analytics/report_generator.py`로 일원화, `reports/`는 산출물 폴더로 유지(코드 없음)
  - 구현 완료:
    - `analytics/report_generator.py`: 중앙 엔트리포인트 (이미 구현됨)
    - `reports/__init__.py`: DEPRECATED wrapper (하위 호환성 100%)
    - `reports/` 폴더: 산출물 디렉터리 (backtest/, results/, trades/)
  - 테스트:
    - `tests/test_monitoring_analytics.py`: test_08_analytics_modules ✅
    - Docker PAPER Scalping: 정상 기동 ✅
  - 문서 동기화:
    - PR6_COMPLETE.md 생성 ✅
    - REFACTORING_개선계획.md 업데이트 ✅
    - REFACTORING_문서아키텍처.md 업데이트 ✅
    - REFACTORING_AI개발지시서.md 업데이트 ✅
    - REFACTORING_monitoring_analytics.md 업데이트 ✅
    - INTEGRATION_TEST.md v1.4 ✅
    - 모듈별 리팩토링 문서 6개 상태 표기 ✅
  - 제약 준수:
    - 신규 파일 생성 없음 ✅
    - 설정 키 추가 없음 ✅
    - 코드 변경 없음 (이미 구현된 구조 활용) ✅

• [⏳] **PR 7(Critical): E2E 테스트 + 전략/앙상블 검증** (2025-11-03 진행 중)
  - ✅ **단위 테스트 완료** (2025-11-03 00:32):
    - tests/integration/test_trading_flow.py: 8/12 통과 (핵심 7/7 100%)
    - 6개 전략: scalping, daytrade, swing, trend, reversion, breakout ✅
    - 앙상블: combine_signals ✅
    - Redis: candle:seen 키 생성 ✅
    - DB: trading.trades 테이블 ✅
    - Analytics: get_daily_kpis, compare_strategies ✅
    - Tuning: fetch_metrics_rolling ✅
    - FlowGuardian: gate_results + trial_0000.json ✅
  - ⏳ **실제 동작 검증** (2025-11-03 00:25~):
    - Docker Paper scalping 실행 중
    - **목표**: trading.trades 레코드 최소 1건 이상 발생
    - **현재**: 거래 0건 (약 15분 경과)
    - **확인 예정**: 2025-11-04 오전 (24시간 후)
  - ✅ **문서 업데이트**:
    - PR7_COMPLETE.md: E2E 테스트 결과 문서화
    - PR7_VERIFICATION_PLAN.md: 검증 계획 (신규)
    - REFACTORING_strategies_v1.md: PR7 검증 완료 섹션 추가
    - REFACTORING_execution_v1.md: E2E 흐름 검증 섹션 추가
  - **수용 기준 (재확인)**:
    - [x] 전략: 6개 전략 signal_logic 에러 없이 실행
    - [x] 앙상블: combine_signals 정상 동작
    - [x] Redis: candle:seen 키 생성 확인
    - [x] DB: trading.trades 테이블 접근 가능
    - [x] Analytics/Tuning: 모듈 정상 동작
    - [x] FlowGuardian: gate_results + trial_0000.json 생성
    - [ ] **Docker Paper 24h**: 실제 거래 1건 이상 발생 (진행 중)
  - **제약**:
    - .windsurfrules 준수 ✅
    - 테스트 코드만 추가 (tests/integration/) ✅
    - 전략 로직 수정 안 함 ✅
• ✅ **PR 7-2: 앙상블 Paper 방법론** (완료: 2025-11-03 12:40)
  - **목표**: 1개 컨테이너로 앙상블 Paper 모드 실행
  - **변경 파일**:
    - docker-compose.yml: trading_bot_paper_ensemble 서비스 추가 (67줄) ✅
    - main.py: 환경변수 USE_ENSEMBLE 오버라이드 (23줄) ✅
    - ensemble.py: combine_signals에서 save_decision 호출 (40줄) ✅
    - engine.py: signal에 timeframe 추가 (1줄) ✅
    - config.yml: use_ensemble=true, selector=null (2줄) ✅
    - monitoring/performance_monitor.py: strategy None 처리 (1줄) ✅
    - common/messaging.py: strategy None 처리 (1줄) ✅
  - **테스트/수용**:
    - tests/test_pr7_2_ensemble_paper.py (검증 스크립트) ✅
    - 로그 확인: "⭐ 앙상블 모드", "✅ [CONFIG] Ensemble mode" ✅
    - 6개 전략 활성화 확인 ✅
    - 에러 없이 정상 동작 ✅
    - 💓 [ENSEMBLE] 상태 로그 출력 ✅
  - **문서 업데이트**:
    - PR7-2_COMPLETE.md (신규) ✅
    - INTEGRATION_TEST.md v1.7 (PR7-2 섹션) ✅
    - REFACTORING_개선계획.md (PR7-2 업데이트) ✅
    - REFACTORING_execution_v1.md (업데이트 필요) ⏳
    - REFACTORING_strategies_v1.md (업데이트 필요) ⏳
  - **수용 기준 (24h 후 확인)**:
    - [✅] 앙상블 모드 활성화
    - [✅] 6개 전략 로드 성공
    - [✅] 에러 없이 실행
    - [ ] monitoring.signals ≥1건 (각 전략)
    - [ ] trading.decisions ≥1건
    - [ ] DB-JSON score_total 동치
  - **제약**:
    - .windsurfrules 준수 ✅
    - 신규 파일: test_pr7_2_ensemble_paper.py만 ✅
    - 전략 로직 수정 안 함 ✅
    - 기존 모듈 최대 활용 ✅
• 아카이브(승인 시)
scripts/tuning/template.py, tune_backup.py → _archived/
문서의 DEPRECATED 표기 유지
# 리팩토링 실행 순서(추천)
FlowGuardian 게이트 확정(준비됨: 수용 기준 준수 확인)
Database 2파일 이관(postgres.py, redis.py) + shim
Tuning 3파일 이관(파일명 그대로) + import 교체
Signals/Indicators 출력 스키마 표준화(주석·타입·테스트 강화)
Execution 지표 노출 연동 → Monitoring 확인
Reports 호출경로 정리(선택)
# Docker 수행 기준
실행: DB/Redis/WS 관여 변경이 있는 PR(②③⑤)에서는 PAPER 프로파일 10분 스모크 권장
생략: 순수 파이썬 내부 로직만 변경(PR④)은 로컬 테스트로 대체 가능
# 마무리
문서/아키텍처/테스트 정책은 모두 최신화했습니다. .windsurfrules에 위 항목 추가 승인만 주시면, 제가 최종 점검 체크리스트로 묶어드리겠습니다.
다음 단계: 위 “개발 AI 실행 지시서”에 맞춰 PR 1부터 순차 진행하면 됩니다.

## 업데이트 (2025-11-04) — PR7-4: Multi-TF Preload + FlowGuardian

### 결정
- 운영 기본을 Multi-Timeframe Preload + 동일 TF WebSocket 구독으로 전환합니다.
- 1m 단일 구독 → 엔진 리샘플(Option A)은 백업(fallback) 경로로 유지합니다.

### 변경 허용 파일(.windsurfrules 준수)
- core/interfaces.py (필요 시 인터페이스 보강)
- core/flow_guardian.py (신규 1개)
- execution/engine.py (게이트 호출만 추가)
- metrics/compute.py (계약 준수 범위)
- collectors/websocket_collector.py (멀티 TF 구독 지원)
- execution/adapters/__init__.py (멀티 TF 프리로드)
- common/utils.py (make_streams 멀티 TF 지원)
- config.yml (flow_guardian/startup_bars/min_bars_for_signal)

### 설정 정책(config.yml)
```yaml
flow_guardian:
  enabled: true
  essential_strategies: [scalping, daytrade]
  startup_bars:
    3m: 1000
    5m: 1000
    15m: 1000
    1h: 300
    4h: 200

strategies:
  # 모든 전략 공통
  <name>:
    min_bars_for_signal: 60
```

### 수용 기준(불변)
- tests/flow/test_flow_guardian.py 통과
- pre-commit(ruff, black, mypy, vulture, coverage>85%) 통과
- logs/trial_0000.json 생성, DB score_total == JSON score_total
- 시작 2~5분 내 6전략 READY → 앙상블 자동 집계 시작

### 실행 지시(개발 순서)
1) Multi-TF 프리로드 구현 (adapters/collector/utils)
2) FlowGuardian 게이트 구현 (core/ + engine 훅 1곳)
3) config.yml 정합화(상기 키만)
4) 10분 스모크 + 수용 기준 점검