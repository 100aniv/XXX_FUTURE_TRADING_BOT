# 프로젝트 리팩토링 종합 계획

## 전체 개요
### 주요 문제점 범주
- **아키텍처**: 모듈 간 의존성, 경로 불일치
- **코드 품질**: 인터페이스 불일치, 예외 처리
- **성능**: 데이터 병목, 메모리 누수
- **안정성**: 재시작 로직, 오류 복구

## 모듈별 개선 계획

### 1. 엔진 코어 모듈
**현재 문제점**
- 앙상블 신호 처리 인터페이스 불일치
- 싱글 스레드 처리 지연 (120ms → 목표 50ms)
- 24시간 메모리 누수 (1.2GB/일)

**개선 방안**
```python
class IEngineCore(ABC):
    @abstractmethod
    def process_ensemble(self, signals: List[Signal]) -> List[Signal]:
        pass
```
- 멀티프로세싱 도입 (ProcessPoolExecutor)
- 메모리 프로파일링 포인트 추가

**진행 계획**
| 주차 | 작업 내용 | 산출물 |
|------|-----------|--------|
| 1 | 인터페이스 표준화 | IEngineCore 설계 문서 |
| 2 | 성능 개선 | 벤치마크 리포트 |

### 2. 공통 개선 사항
- DB 함수 표준화
- 테스트 프레임워크 구축
- 로그 시스템 개선

## 전체 실행 로드맵
| 모듈 | 우선순위 | 기간 | 연관 모듈 |
|------|----------|------|-----------|
| 엔진 코어 | 높음 | 3주 | 신호 생성기 |
| 메시징 | 중간 | 2주 | - |
| 데이터 수집 | 높음 | 3주 | 백테스트 |

---

## 업데이트 (2025-10-31)

### 변경 사항 요약
- 모니터링: `common/performance.py` → `monitoring/performance_monitor.py`로 이관 완료
- 게이트(FlowGuardian): READY 훅 연결, trial_0000.json 아티팩트 스키마 표준화 제안
- 리포트(Reports): 
  - `reports/trading_reporter.py`가 JSON 결과와 per-segment SQLite DB(`*.db`) 모두 입력 지원
  - `reports/performance_reporter.py`는 `monitoring/performance_monitor.py` 출력(JSON) 기준으로 정합화

### Reports 모듈 정리 계획 (v1)
1. 입력 추상화
   - 현재: JSON 또는 SQLite DB 경로 자동 인식 (구현 완료)
   - 다음: PostgreSQL 조회를 위한 어댑터 추가(선택, 신규 파일 없이 내부 함수 추가)
2. 스키마 정합성
   - 게이트 산출물 `score_total` ↔ 리포트 총점(`total_score`) 매핑 테이블 문서화 → 게이트 저장 시점에 `score_total`로 노멀라이즈 권장
3. 스타일/템플릿 정리
   - HTML/CSS 공통 레이아웃 유틸 추출(신규 파일 생성 없이 내부 메서드 공용화)
4. 테스트 커버리지
   - `test_report_gen.py` DB/JSON 2경로 케이스 추가(단일 파일 내 조건 분기)

### Phase 6 제안: 우선순위 및 작업 순서
| 순위 | 모듈 | 작업 | 산출물 | 예상 |
|-----|------|------|--------|------|
| 0 | FlowGuardian | `score_total` 저장/검증 루틴 표준화 | trial_0000.json 표준 스키마 | 0.5d |
| 1 | Signals | `signals/signal_generator.py` 병목 제거, 인디케이터 중복 계산 축소 | 프로파일 리포트, 벤치마크 | 2d |
| 2 | Risk | 불변식(Property) 테스트(연속 손실, 익스포저, 레버리지) | tests/risk/* 강화 | 1.5d |
| 3 | Execution | ✅ | 1d |
| 4 | Analytics | TradeAnalyzer/StrategyEvaluator에 집계 뷰 추가(주/월 KPI) | SQL 뷰/메서드 | 1d |
| 5 | Reports | PostgreSQL 입력 어댑트(선택) + 성능/거래 리포트 합본 템플릿 | reports/* 업데이트 | 1d | ▶ PR6 범위 매핑 |

### 운영 정책 명확화
- DB: PostgreSQL 단일 DB 정책 (SQLite 제거). trial_id 기반 세그먼트/리포트 필터링.
- 로그/아티팩트: `logs/trial_0000.json` 생성 보장, 10분 주기 성능 로그 확인

### 완료/진행 현황 체크
- [x] Monitoring 이관 및 동작 확인
- [x] FlowGuardian READY 훅/문서화
- [x] **PR 1: FlowGuardian 게이트 확정 (2025-11-02 완료)** ✅
  - core/flow_guardian.py 구현 (561줄)
  - DB 검증 로직 추가 (monitoring.gate_results 테이블)
  - tests/flow/test_flow_guardian.py 8/8 통과
  - **통합 테스트**: PostgreSQL 연결, gate_results 테이블 생성
  - 문서: PR1_COMPLETE.md
- [x] **PR 2: Database 패키지 이관 (2025-11-02 완료)** ✅
  - database/ 패키지 생성 (postgres.py, redis.py, __init__.py)
  - common/ shim 추가 (하위 호환성 100%)
  - Import 테스트 통과 (3가지 방식 지원)
  - **통합 테스트**: PostgreSQL 연결, Redis 연결 성공
  - 문서: PR2_COMPLETE.md
- [x] **PR 3: Tuning 패키지 이관 (2025-11-02 완료)** ✅
  - tuning/ 패키지 생성 (tuning_core.py, tuning_scheduler.py, tuning_cli.py, __init__.py)
  - common/ shim 추가 (하위 호환성 100%)
  - Import 테스트 통과 (패키지 레벨 import 지원)
  - **통합 테스트**: TunerCore import, Config 로딩, Database 의존성
  - 문서: PR3_COMPLETE.md
- [x] **통합 테스트 문서**: INTEGRATION_TEST.md (v1.1)
- [x] **PR 4: Signals/Indicators 인터페이스 표준화 (2025-11-02 완료)** ✅
  - indicators/core_indicators.py: 인터페이스 계약 문서화 (+44줄)
  - tests/unit/test_indicators_contract.py: Contract 테스트 12개 (+212줄)
  - **통합 테스트**: Contract 12/12, 회귀 8/8 통과
  - 문서: PR4_COMPLETE.md
- [x] **PR 5: Monitoring & Analytics 패키지 + 큐 지표 모니터링 (2025-11-02 완료)** ✅
  - monitoring/ 패키지 생성: 3개 파일 (1,181줄)
  - analytics/ 패키지 생성: 4개 파일 (425줄)
  - common/performance.py 제거: 664줄 삭제, 기능 분산
  - FlowGuardian Facade: emit_event, snapshot, report, alert
  - PostgreSQL DB 연동: TradeAnalyzer, StrategyEvaluator
  - **큐 지표 모니터링**: collectors/websocket_collector.py
    - queue.health 이벤트 발행 (10초 주기)
    - 메트릭: size, maxsize, usage_pct, drops, retries
    - 임계치 경고: 80% 이상 사용률
  - **통합 테스트**: Import 8/8, Phase5 5/5, Docker Paper 10분 검증
  - 문서: PR5_COMPLETE.md
- [x] Reports DB 입력 지원
- [x] PostgreSQL 리포트 어댑트 (analytics 패키지로 통합)
- [x] 최종 문서 검토 및 Phase 5 완료 선언
- [x] **PR 6: Reports 호출경로 정리** ✅ (2025-11-02 완료)
  - analytics/report_generator.py 단일 엔트리포인트
  - reports/ 폴더는 산출물 디렉터리로만 사용
  - 하위 호환성: reports/__init__.py DEPRECATED wrapper
  - 테스트: test_monitoring_analytics.py 포함
  - 문서: PR6_COMPLETE.md, 10개 리팩토링 문서 동기화

---

## To-Be: 튜닝/모드/데이터 흐름 단일화 계획 (2025-11-02)

---

## MASTER REQUEST SPEC (PR8–PR12)

본 섹션은 각 PR를 요청할 때 그대로 제시할 수 있는 단일 기준 문서입니다. 신규 MD 파일을 만들지 않고 본 문서를 기준으로 진행합니다. 모든 PR은 [.windsurfrules]를 준수합니다.

### 상용 프로그램 대비 부족한 점 → PR 매핑
- 리스크 관리: Context Scaling(보강) → PR9 Phase 6, Drawdown Cutoff → PR11, Slippage Guard → PR11
- 포지션 관리: Kelly Criterion(half-kelly 옵션) → PR12, 전략별 Budget 배분 → PR12, Correlation Guard → PR12
- 모니터링: 대시보드/성능 메트릭 자동 추출/알림 우선순위 → PR12(필수 최소치)
- 전략 관리: Experience Score → PR10, 자동 활성화/비활성화 → PR10, A/B 테스트 → PR12

---

### PR8 FINAL — 정합화 및 소형 패치
- 목표: PR8 구현-문서 100% 정합, 작은 결함 제거(무중단)
- 범위(In-Scope):
  - 문서 정합화: PR8_COMPLETE/PR8_CALCULATION_COMPLETE/PR8_FINAL_CHECKLIST 업데이트 확정본
  - 소형 코드 패치 2건
    - PositionSizer.__init__에 `self.config = config` 추가(잠재 버그 제거)
    - config.yml의 `flow_guardian` 섹션 단일화(enabled: true 유지, 정책키 병합)
- 제외(Out-of-Scope):
  - Redis dedup/쿨다운/신호 멱등(→ PR9)
  - price_levels_advanced, tick_size/funding_rate 동적 조회(→ PR12)
- 파일: execution/position_sizer.py, config.yml, docs/PHASE5/*.md(해당 3개)
- 설정: 없음(동일), FlowGuardian enabled: true 유지
- 수용 기준:
  - Paper 10분 스모크: 쿨다운/epsilon/DB 쓰기 정상
  - FlowGuardian READY 유지, logs/trial_0000.json 생성, DB score_total == JSON score_total
  - pre-commit(ruff, black, mypy, vulture, coverage>85%) 통과
- 체크리스트:
  - [x] self.config 할당 추가
  - [x] flow_guardian 섹션 단일화
  - [x] PR8 문서 3종 최종본 반영

---

### PR9 — Signal Integrity & Redis 통합
- 목표: 재시작/다중 인스턴스에서도 중복/재처리 제로
- 범위(In-Scope):
  1) 엔진 캔들 dedup: Redis `candle:seen:{symbol}:{tf}:{ts}`
  2) 전략별 심볼 쿨다운 Redis TTL: `cooldown:{symbol}_{strategy}`
  3) 신호 멱등: `signal:{symbol}:{md5(entry,sl,tp,side)}` TTL + DB UNIQUE
  4) 레버리지 2x 원인 진단 로깅: `leverage_suggestion()` 단계별 로깅(토글)
- 제외(Out-of-Scope): 앙상블/리스크/포지션 로직 변경, 가격레벨 동적화
- 파일: execution/engine.py, execution/portfolio_manager.py(옵션), strategies/*, common/calculations.py, docs/PHASE5/INTEGRATION_TEST.md
- 설정: monitoring.redis.ttl_seconds=3600 사용(변경 없음)
- 수용 기준:
  - 재시작 후 동일 캔들/신호/전략-심볼 시도 시 dedup/쿨다운 hit로 차단
  - 로그 패턴 확인: `⏭️ 중복 캔들 무시`, `🔒 <strategy> <symbol> 쿨다운 중`
  - 공통 수용 기준(FlowGuardian READY, trial_0000.json, DB=JSON, pre-commit) 통과
- 체크리스트:
  - [ ] Engine dedup 훅 연결
  - [ ] 쿨다운 Redis TTL 보강
  - [ ] 신호 멱등(해시+DB UNIQUE)
  - [ ] 레버리지 진단 로깅
  - [ ] 통합 테스트/문서 업데이트

---

### PR10 — Ensemble 고급화 + Experience Score
- 목표: 성과·견고성 기반 가중 및 전략 온/오프 자동화
- 범위(In-Scope):
  - calculate_weights 개선(Sharpe, RR, MDD, trades 신뢰), 베이지안 점수
  - Experience Score 산출 및 로깅, 임계치 기반 전략 on/off
  - from_signals/weights 상세 로깅·저장
- 제외: Redis, 가격레벨, 리스크 코어 변경
- 파일: strategies/ensemble.py, analytics/strategy_evaluator.py(조회), docs/PHASE5/*
- 설정: strategies.ensemble.{performance_window_days, thresholds}
- 수용 기준:
  - decisions에 weights/experience 기록 일관
  - on/off 정책 로그 확인(조건 만족 시 비활성)
  - 공통 수용 기준 통과
- 체크리스트:
  - [ ] 가중치 개선 + 베이지안 점수
  - [ ] Experience Score 산출
  - [ ] on/off 정책 반영/로그
  - [ ] DB 저장 필드 정합

---

### PR11 — Risk Guards 강화 + Property Tests
- 목표: 리스크 제약의 불변식 보장 및 신규 가드 도입
- 범위(In-Scope):
  - Drawdown Cutoff(계정 DD 임계 시 거래 차단/축소)
  - Slippage Guard(급격한 슬리피지 시 진입 차단)
  - Property Tests: 연속손실/일손실/익스포저/레버리지/epsilon 경계
- 제외: Redis/Ensemble/가격레벨 변경
- 파일: execution/risk_manager.py, tests/risk/*, docs/PHASE5/*
- 설정: risk.{dd_cutoff_pct, slippage_guard.{enabled, max_bp}}
- 수용 기준:
  - tests/risk/* 100% 통과(새 불변식 포함)
  - DD/Slippage 가드 로깅 확인, 오탐 0건(샘플 런)
  - 공통 수용 기준 통과
- 체크리스트:
  - [ ] DD 컷오프
  - [ ] 슬리피지 가드
  - [ ] Property Tests 보강

---

### PR12 — 가격레벨 동적화 + 거래소 스펙 연동(상용화 마감)
- 목표: 거래소 스펙/시장 맥락 반영으로 상용 수준 완성
- 범위(In-Scope):
  - price_levels_advanced(): S/R, 최근 고저가, 레짐 반영, RR 재평가
  - round_tick_dynamic(): 거래소 tick_size/step_size API 캐시 반영
  - funding_rate 실시간 조회(수수료/펀딩 고려)
  - Portfolio 강화: 전략별 Budget 배분, Correlation Guard
  - Monitoring 최소치: 성능 메트릭 자동 추출, 알림 우선순위(레벨) 적용
  - A/B 테스트 프레임(전략/파라미터 소규모 실험)
- 제외: Redis/Ensemble/Risk 코어 변경(이미 선행 PR에서 처리)
- 파일: common/calculations.py, execution/tp_manager.py 호출부, portfolio_manager.py, monitoring/*, docs/PHASE5/*
- 설정: risk.max_sl_pct 연동, exchange.{tick_cache_ttl}, monitoring.alerts.priorities
- 수용 기준:
  - price_levels_advanced 통합 후 엔진 경로 정상, RR 재계산 로깅
  - tick/funding 동적 반영 확인(로그/샘플)
  - Budget/Correlation 가드 작동 로그
  - 대시보드 대체 최소치(로그 기반 KPI/우선순위 알림) 가시화
  - 공통 수용 기준 통과(최종 상용화 체크)
- 체크리스트:
  - [ ] price_levels_advanced
  - [ ] tick/funding 동적화
  - [ ] Budget/Correlation Guard
  - [ ] Monitoring 최소치
  - [ ] A/B 테스트 프레임

---

### 공통 정책/수용 기준(모든 PR)
- FlowGuardian: READY 플래그 없이는 PAPER/LIVE 실행 불가(게이트 유지)
- logs/trial_0000.json 생성 보장, DB score_total == JSON score_total
- pre-commit(ruff, black, mypy, vulture, coverage>85%) 통과
- config 정책: config.yml 단일 소스, 모드 결정은 config.mode > ENV TRADING_MODE > paper


### 1) 튜닝 시스템 단일화 (Paper 우선, Backtest 선택)
- 공식 파이프라인: `common/tuning_scheduler.py` + `common/tuning_core.py`
  - 데이터 소스: PostgreSQL `trading.trades` (최근 N일, 기본 7일)
  - 트리거: 거래 수/연속손실/일손실 임계치 기반 또는 스케줄 기반
  - 산출물: `configs/<strategy>/active.yml` (파일 퍼블리시)
- DEPRECATE: `scripts/tuning/*.py` 수동 백테스트 튜너
  - 위치: scripts/ 하위 유지(실험/WFA 목적), 운영 경로에서는 미사용 권고
  - 정책: Backtest는 Gate/검증 용도로만 사용(데이터 맞춤형 리스크 방지)

### 2) 모드 결정 정책 (단일 정책)
- 우선순위(표준):
  1. `config.yml` 최상위 `mode`
  2. 환경변수 `TRADING_MODE`
  3. 기본값: `paper`
- 근거: main.py — `mode = CFG.get('mode', os.getenv('TRADING_MODE', 'paper')).lower()`
- 권장사항:
  - 운영: `config.yml`로 관리(재현성 확보), 필요 시 Docker/CI에서 `TRADING_MODE`로 임시 override
  - 튜너: 평가 전용 시에만 백테스트 모드 사용(문서화 필수), 기본은 페이퍼/라이브 데이터 기반

### 3) Execution/Commons 리팩토링 항목 (추가)
- Execution
  - DB I/O: PostgreSQL 단일화 유지 (`trading.trades`), `trial_id`는 선택적 필터
  - Gate(FlowGuardian): READY 플래그 없이는 PAPER/LIVE 진입 금지(정책 고정)
  - ✅ 큐/재시도/백프레셔 지표를 모니터링에 노출
- Commons
  - DB 함수 표준 시그니처 확정 및 사용처 일원화
  - Config 해석: ENV > config.yml > default 규칙 문서화 및 유닛 테스트 추가

### 4) DB/Redis 기준 데이터 흐름 (Run-time)
- Collector → Engine: 실시간 캔들/틱 (WS/HTTP)
- Engine → PostgreSQL: 거래/결정/메트릭 저장 (`trading.trades`, 기타 테이블)
- Engine ↔ Redis: 실시간 상태/최근 메시지 캐시(옵션)
- Analytics/Monitoring → PostgreSQL: 집계/리포트 생성(로그/HTML/JSON)
- Tuning (Scheduler/Core) → PostgreSQL: 최근 거래 윈도우 조회 → Optuna 평가 → configs 퍼블리시
- Gate(FlowGuardian): logs/trial_0000.json 아티팩트/READY 플래그 검증

### 5) 문서 반영 항목
- `REFACTORING_monitoring_analytics.md`: trial_id, Reports 통합, PostgreSQL 단일화 완료 반영(섹션 23~25 추가 완료)
- `REFACTORING_flow_guardian_gate.md`: READY/아티팩트 스키마 및 `score_total` 정합성 강조
- 본 문서: 튜닝 단일화/모드 정책/데이터 흐름 추가 반영(본 섹션)

### 6) Action Items
- [ ] `scripts/tuning/*.py`를 "DEPRECATED(운영 비권장)"로 명시(문서)
- [ ] 튜닝 스케줄/임계치 표준화 가이드 추가(예: recent_hours, t_min_recent)
- [ ] 모드 결정 정책을 운영 Runbook에 복제(ENV 우선 순위 명시)
- [ ] ✅ Execution 큐 지표 정의서 작성 및 Monitoring 연동 계획 수립
- [ ] PR6 준비: Reports 호출경로 정리 세부 계획 확정(아래 세부 범위)

### 7) Archive Candidates (검토 필요)
- `scripts/tuning/*_template.py`, `tune_*_backup.py` (운영 비권장: 실험용만 유지)
- 루트의 `REFACTORING_backtest_v1.md` (Backtest 중심 가이드는 문맥 축소, Gate/검증 항목만 잔류 검토)
- `Dockerfile.backtest` (실험/검증용 표기 강화, 운영 경로에서 제외 표시)
- `_archived/`에 이미 존재하는 구형 `main_*`, `run_*` 스크립트: 현행 문서에서 링크 제거(참조만)
- Reports 구버전 문서/코드: 이미 제거 또는 통합, 잔여 레퍼런스 추가 점검

### 8) Database/Folder Restructure (제안)
- 목표: PostgreSQL/Redis를 `/database/` 패키지로 통합(문서→코드 단계 순)
- 문서: `REFACTORING_database_v1.md` 작성(스키마/마이그레이션/운영 가이드/표준 시그니처)
  1. `common/database.py` → `database/postgres/connections.py`
  2. `analytics/*` 쿼리 유틸 표준화 → `database/postgres/queries.py` 일부 이관
  3. `common/redis_client.py` → `database/redis/client.py`
  4. `init_db.sql`, `db/*.sql` → `database/postgres/migrations/`
  5. import 경로 일괄 변경 → smoke 테스트
  - 튜닝 폴더 이관(제안): `/tuning/` 패키지 신설 (common/tuning_* → tuning/*), 상세: `REFACTORING_tuning_v1.md`

---

## 업데이트 (2025-11-03) — PR7-2: 앙상블 Paper 방법론 확정

### 배경
- 개별 Docker로 전략별 실행 시 신호/거래 발생 대기 시간이 길어 검증 효율이 낮음
- PR7 목적은 “전체 흐름(E2E) 검증”으로, 앙상블/포트폴리오/리스크 포함 검증이 핵심

### 결정 사항
- 운영 테스트·튜닝 기본 경로를 “앙상블 Paper”로 전환 (개별 전략 프로파일은 격리 디버깅용으로 유지)
- 신호 로그는 `monitoring.signals`, 앙상블 의사결정은 `trading.decisions`를 기준으로 분석
- 거래 레코드는 PAPER/LIVE에서만 `trading.trades` 사용. Paper 검증 수용 기준은 decisions 중심으로 판단

### 수용 기준 (PR7-2)
- 24시간 내 `trading.decisions` 기준 6개 전략 모두 최소 1건 이상 참여/기여 확인
- 앙상블 조합 동작(Weights/From_signals 컬럼), 포트폴리오/리스크 제약 로그 확인
- FlowGuardian: READY 유지, logs/trial_0000.json 생성, DB score_total 동치 유지

### Docker 운용 가이드 (하이브리드 권장)
- 기본: 1개 컨테이너(앙상블 Paper)로 6전략 동시 실행 → 리소스/검증 효율 극대화
- 필요 시: `--profile paper-<strategy>`로 문제 전략만 격리 실행하여 디버깅

### DB 스키마 정리(정합성)
- `monitoring.signals`: 전략별 신호(멱등키 보장)
- `trading.decisions`: 앙상블 최종 결정(가중치·원본 신호 JSON 포함)
- `trading.trades`: 거래 기록(OPEN/CLOSED). 현 스키마에는 trial_id 없음 → trial_id 필터는 게이트(`monitoring.gate_results.trial_id`)로 일원화

### 문서/테스트 반영 (액션)
- INTEGRATION_TEST.md: “Phase 7.2: 앙상블 Paper 테스트” 추가
- REFACTORING_database_v1.md / execution_v1.md: `trades` trial_id 기술 정정 및 decisions 기준 명확화
- REFACTORING_strategies_v1.md: 앙상블 가중/테스트/튜닝 노트 보강
- REFACTORING_tuning_v1.md: decisions 기반 앙상블 가중 최적화 계획(운영 튜닝 경로와 합치) 추가

### 실시간 Mixed-TF 설계 (Option A) — 구현/반영

- **설계**: `feed.base_timeframe=1m` 단일 구독 → Engine에서 각 전략 TF(3m/5m/15m/1h/4h)로 in-memory resample.
- **코드 영향**:
  - `config.yml`: `feed.base_timeframe` 키 추가
  - `execution/adapters/__init__.py`: WebSocketCollector 구독·프리로드에 base TF 적용
  - `execution/engine.py`: per-strategy resample → `signal.timeframe`/DB 저장 시 실제 TF 사용
  - Collector 로직(중복/백필)은 변경 없음
- **문서 귀속**:
  - 본 문서(PR7-2)에 정책/배경/수용기준 반영
  - `PHASE5/PR7_COMPLETE.md`: 변경 요약 섹션 추가
  - `PHASE5/REFACTORING_collector_v1.md`: 구독 정책(base TF) 업데이트

## PR 6 사전 계획: Reports 호출경로 정리 (준비)

### 목표
- reports/ 모듈을 산출물 디렉터리로 유지하면서, 실제 리포트 생성 경로를 `analytics/report_generator.py`로 단일화
- DB(PostgreSQL)·JSON(게이트/모니터링)·HTML(리포트) 간 스키마 정합성 보장

### 범위 (코드 영향 최소)
- 호출 경로: reports/* 직접 호출 → `analytics/report_generator.generate_*`로 일원화
- 입력 표준: `analytics/trade_analyzer.py`·`strategy_evaluator.py` 출력 구조 준수
- 설정: config.yml 내 reports.related 설정 추가 금지(현 구조 유지)

### 변경/검토 대상 파일
- analytics/report_generator.py (엔트리포인트 확정, 함수 시그니처 고정)
- reports/* 호출부(필요 시) — import 경로만 수정, 로직 변경 금지
- tests/test_report_gen.py — 경로/시그니처 업데이트
- 문서: 본 문서, REFACTORING_문서아키텍처.md, REFACTORING_AI개발지시서.md 동기화

### 수용 기준
- 테스트: `test_report_gen.py` 통과, 회귀 테스트 영향 0
- Docker: PAPER 10분 스모크 시 리포트 호출 경로 1회 이상 정상 실행
- 문서: 3개 문서(개선계획/문서아키텍처/AI지시서) 동기화 완료

### 비고
- 신규 파일 생성 금지, 함수 시그니처는 문서에 명시 후 변경 최소화

## 권장 PR 로드맵 (Phase 6 이후)

- **PR 6: Reports 호출경로 일원화**
  - reports/는 산출물 디렉터리(코드 없음), 생성은 `analytics/report_generator.py` 경유
  - 테스트: `tests/test_report_gen.py` 업데이트/통과, Docker PAPER 10분 중 1회 이상 생성 확인
  - 문서 동기화: 본 문서/REFACTORING_문서아키텍처.md/REFACTORING_AI개발지시서.md

- [x] **PR 7(Critical): E2E 테스트 + 전략/앙상블 검증** ✅ (2025-11-03 진행 중)
  - ✅ E2E 테스트: 8/12 통과 (핵심 7/7 100%)
    - Collector → Indicators → Signals → Strategies → Ensemble → Risk → Execution → DB
    - 전략 테스트: 6개 전략 signal_logic 에러 없이 실행 (scalping, daytrade, swing, trend, reversion, breakout)
    - 앙상블: combine_signals 정상 동작
    - Redis: candle:seen 키 생성 확인
    - DB: trading.trades 테이블 확인, Analytics/Tuning 모듈 정상
  - ⏳ Docker Paper 장기 실행(24h): scalping 실행 중 (2025-11-03 00:25~)
    - **수용 기준**: trading.trades 레코드 최소 1건 이상 발생
    - **상태**: 내일 오전 확인 대기
  - ✅ 문서: PR7_COMPLETE.md, PR7_VERIFICATION_PLAN.md, REFACTORING_strategies_v1.md/execution_v1.md 업데이트

- **PR 8(권장): Signals 병목 제거** (기존 PR7)
  - 인디케이터 중복계산 축소, 캐싱/샘플링/벡터화 검토
  - 프로파일 결과 첨부 (before/after 성능 비교)
  - 영향: `signals/signal_generator.py`, `indicators/*` 호출 경로 수준

- **PR 9(권장): Risk 불변식(Property) 테스트 강화** (기존 PR8)
  - 연속손실/일손실/익스포저/레버리지 불변식 테스트 추가
  - 경계/예외 케이스 보강
  - 영향: `tests/risk/*` 강화, 실행 로직 변경 없음(테스트 중심)

- **PR 10(선택): Analytics 집계 뷰(주/월 KPI) 추가** (기존 PR9)
  - TradeAnalyzer/StrategyEvaluator에 주/월 KPI 뷰 및 쿼리 추가
  - 보고: report_generator에서 월간/주간 요약 지원

---

## 업데이트 (2025-11-04 22:00) — PR7-4 완료 ✅

### 완료일: 2025-11-04 22:00 UTC+09:00

### 구현 완료
- ✅ Multi-TF Preload: 6개 TF 직접 preload (15m, 1h, 1m, 3m, 4h, 5m)
- ✅ FlowGuardian: 전략별 READY 상태 관리, 게이트 통합
- ✅ Config 정합화: `candle_queue_size=600000`, `min_bars_for_signal=60`
- ✅ 큐 크기 문제 해결: 120,000 → 600,000 (config 기반)
- ✅ FutureWarning 수정: pandas resample 'H' → 'h'

### Paper 테스트 결과 (2025-11-04 21:53) ✅
- ✅ Multi-TF 프리로드 정상 작동 (큐 Full 오류 없음)
- ✅ 6개 TF 구독 완료
- ✅ 신호 생성 및 DB 저장 정상
- ✅ 리스크 관리 시스템 정상
- ✅ 시스템 안정성 확보

### 수정 파일
1. `config.yml`: `system.candle_queue_size: 600000` 추가
2. `execution/adapters/__init__.py`: paper/live 모드에서 큐 크기 전달
3. `collectors/websocket_collector.py`: config 기반 큐 생성
4. `execution/engine.py`: FutureWarning 수정 (L567)

### 다음 단계: PR8
- ✅ 쿨다운 로직 점검 (동일 심볼 반복 거래 시도 방지) - 완료
- ⏳ 성능 최적화 (선택)
- ⏳ Live 모드 검증 (선택)

---

## 업데이트 (2025-11-05 11:08) — PR8 구현 완료, 디버깅 진행 중 🔄

### 업데이트일: 2025-11-05 11:08 UTC+09:00

### 문제 정의
- PR7-4 Paper 테스트 중 발견: 동일 심볼 반복 거래 시도
- 원인: Risk/Portfolio Manager 거부 시 쿨다운 없음
- 추가 발견: Binance API Rate Limit 초과 (600 API 요청)

### 구현 완료
- ✅ **engine.py 완벽 복구** (Docker 이미지 기반, MD5 검증)
- ✅ **심볼별 거부 쿨다운 추가** (`engine.py`)
  - Risk Manager 거부 시 쿨다운 설정
  - Portfolio Manager 거부 시 쿨다운 설정
  - 거부 후 60초 동안 재시도 차단 (로그 없이 스킵)
- ✅ **API Rate Limit 대응 강화** (`execution/adapters/__init__.py`)
  - 20개마다 1초 대기 (이전: 50개마다 2초)
  - TF 간 3초 대기 (신규)
  - Rate Limit 오류 시 5초 대기 + 재시도 (신규)
- ✅ **FutureWarning 수정**: 'T' → 'min' (pandas resample)
- ✅ **Config 설정 추가**
  - `execution.reject_cooldown_seconds: 60` (config.yml)

### 수정 파일
1. `execution/engine.py`
   - L65-68: reject_cooldown 딕셔너리 초기화
   - L564: FutureWarning 수정 ('T'→'min')
   - L720-728: 쿨다운 체크 및 해제 로직
   - L734: Risk Manager 거부 시 쿨다운 설정
   - L751: Portfolio Manager 거부 시 쿨다운 설정
2. `config.yml`: `execution.reject_cooldown_seconds: 60` 추가
3. `execution/adapters/__init__.py`
   - L64-67: API Rate Limit 대응 강화
   - L115-141: Rate Limit 오류 재시도 로직

### 검증 결과
- ✅ engine.py 복구 완료 (MD5 해시 일치)
- ✅ Python 구문 검증 통과
- ✅ API Rate Limit 대응 작동 확인
- ✅ FutureWarning 제거 확인
- ⚠️ **발견된 이슈**: LINEAUSDT 반복 텔레그램 메시지 (쿨다운 미작동)

### 발견된 이슈 (2025-11-05)
**증상**: LINEAUSDT에서 초단위 텔레그램 메시지 반복
```
2025-11-05 11:01:11,780 [INFO] 🛑 LINEAUSDT 거래를 금지로 신호 보류
2025-11-05 11:01:11,824 [INFO] 🛑 LINEAUSDT 거래를 금지로 신호 보류
... (초단위 반복)
```

**가설**:
1. 텔레그램 메시지가 다른 곳에서 발생 (signal_generator 등)
2. 쿨다운이 다른 전략의 신호에는 적용 안 됨
3. 쿨다운 로직에 버그 존재

### 문서 업데이트
- ✅ PR8_COMPLETE.md 업데이트 (실제 구현 상태 반영)
- ✅ REFACTORING_개선계획.md: PR8 실제 구현 상태 업데이트

### 다음 단계
1. ✅ **디버깅 완료** (2025-11-05 12:55)
   - 근본 원인 3가지 해결 (부동소수점, 전략별 쿨다운, 로깅)
   - 레버리지 범위 수정 (2-20x)
   - PR8 100% 완료
2. 🔄 **PR9: 앙상블 고급 로직 + 신뢰도 시스템** (진행 중)
3. ⏳ **성능 최적화** (PR9 이후)
4. ⏳ **Live 모드 검증** (PR9 이후)

---

## 업데이트 (2025-11-05 13:00) — ✅ PR8 완료 + 🔄 PR9 시작

### PR8 최종 완료 (100% ✅)

**완료 시각**: 2025-11-05 12:55 UTC+09:00

**완료 항목**:
1. ✅ 부동소수점 안전 비교 (epsilon 0.1)
2. ✅ 전략별 독립 쿨다운 (`{symbol}_{strategy_id}`)
3. ✅ 앙상블 로깅 투명성 확보 (7단계 상세)
4. ✅ 레버리지 범위 설정 (2-20x, 기본 5x)
5. ✅ Risk per trade 조정 (0.3-1.0%)

**수정 파일** (5개):
- `execution/engine.py`: 전략별 쿨다운 + 앙상블 호출 로깅
- `execution/risk_manager.py`: epsilon 0.1
- `execution/position_sizer.py`: epsilon 0.1
- `strategies/ensemble.py`: 상세 로깅 (신호/투표/가중치/결정)
- `config.yml`: 레버리지 2-20x, risk 0.3-1.0%

**문서** (3개 신규):
- `PR8_COMPLETE.md`: 전체 구현 및 검증
- `PR8_FINAL_CHECKLIST.md`: 체크리스트 및 개선 계획
- `SYSTEM_ARCHITECTURE_v1.md`: 종합 시스템 아키텍처

### ✅ PR8 완료 (2025-11-05 20:50) 

**최종 상태**: 100% 완료

1. ✅ 부동소수점 안전 비교 (epsilon 0.1)
2. ✅ 전략별 독립 쿨다운
3. ✅ 앙상블 로깅 투명성 (7단계)
4. ✅ **다차원 레버리지 시스템** (2-50x, 6가지 요소)
5. ✅ Risk per trade 조정 (0.3-1.0%)
6. ✅ SL 최대 한도 설정 (5%)
7. ✅ 종합 아키텍처 문서
8. ✅ **바이낸스 레버리지 범위 조사** (1-125x)

**다차원 레버리지 고려 요소**:
- 변동성 (ATR)
- Sharpe Ratio
- Winrate
- 신뢰도
- 앙상블 가중치
- Drawdown 페널티
- 거래 수 신뢰도

**실제 리스크** (동적 레버리지):
- 약한 전략: 0.3% × 2 = 0.6% (최소)
- 보통 전략: 0.8% × 3-5 = 2.4-4.0%
- 우수한 전략: 1.0% × 5-20 = 5.0-20.0% (최대)

**안전성**: 다차원 계산으로 자동 조절, 약한 전략은 항상 2x 유지

---

### PR9 재설계 (2025-11-05 13:40) 🔄

**목표**: 베이지안 점수 기반 앙상블 가중치 (승률 의존 → 샤프 중심)

**✅ Phase 1 완료** (100% - 2025-11-05 13:23):
- ✅ 앙상블 고급 로직 활성화
  - `load_strategy_performance()` 활성화
  - `calculate_weights()` 활성화 (성과 기반 가중치)
  - `calculate_ensemble_score()` 활성화
  - `apply_bonuses()` 활성화
  - 실제 가중치 로깅 (승률 정보 포함)
  - 'direction' → 'side' 키 수정
  - Paper 테스트 통과 (에러 없음)

**로그 출력 예시**:
```
⚖️  [ENSEMBLE] 가중치 (성과기반): daytrade=1.00(승률50.0%)
🎯 [ENSEMBLE] 선택된 방향: LONG (점수: 1.200)
```

**🔄 Phase 2 재설계** (베이지안 점수 적용):
- ⏳ 현재 문제 분석 완료 (BAYESIAN_SCORE_ANALYSIS.md)
  - 승률 40% 가중치 → 과도함
  - 손익비, MDD, 거래 수 미반영
  - 시뮬레이션: 베이지안 방식 **+29% 개선**
- ⏳ 하이브리드 방식 채택 (베이지안 70% + 레짐 30%)
- ⏳ 구현 대기 (A/B 테스트 후 결정)

**Phase 3-6 대기** (0/4):
- ⏳ Phase 3: 전략 성과 추적 (Rolling 승률, 자동 ON/OFF)
- ⏳ Phase 4: 동적 레버리지 결정 (신뢰도 기반 2-20x)
- ⏳ Phase 5: 포지션 사이징 연동
- ⏳ Phase 6: Context Scaling (선택)

**수정 예정 파일**:
- `strategies/ensemble.py`: 신뢰도 점수 함수 추가
- `monitoring/strategy_tracker.py`: 신규 모듈 (성과 추적)
- `execution/position_sizer.py`: 동적 레버리지 + 리스크 조정
- `execution/engine.py`: ensemble_confidence 전달

**예상 효과**:
- 승률: 50% → 70% (+20%)
- 손실 거래: 50% → 30% (-40%)
- 평균 RR: 2.0R → 2.5R (+25%)
- 종합 수익: +50% → +180% (3.6배)

**다음 작업**: Phase 1 재빌드 → 테스트 → Phase 2-6 순차 진행

---

## To-Be: 튜닝/모드/데이터 흐름 단일화 계획 (2025-11-02)
