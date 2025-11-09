# PHASE6 — PR13 마스터 플랜: 베이시안 운영 튜닝 & 단계적 롤아웃

## 배경/의도(Overview)
페이퍼 모드에서 검증된 베이시안 튜닝을 운영 환경에 안전하게 적용합니다. 섀도우런→카나리→점진적 확대의 롤아웃 전략과 가드레일(리스크 한계/변동성/최소 거래수)을 갖춘 운영 최적화 파이프라인을 구축합니다. FlowGuardian READY 게이트는 항상 유지됩니다.

## 목표(Goals)
- 페이퍼 기반 최적 파라미터 산출(가중치/임계/보너스/출구 일부)
- 섀도우 모드에서 안전성 검증 후 카나리 릴리즈
- 가드레일 기반 자동 중단/롤백 체계
- Bug #8: 파라미터 오버레이로 엔트리 품질(승률) 개선

## 범위(Scope, In)
- 튜닝 파이프라인: 실험 구성(K회/시간창), 결과 집계, 오버레이 산출
- 운영 롤아웃: 섀도우런→카나리(10%→30%→50%→100%) 단계 적용
- 가드레일: DD 증가 한계, 최소 거래수, 분산/변동성 상승 한계, 에러율
- A/B 비교: baseline vs tuned 결과 리포트(승률/TP hit rate/평균 보유시간 포함)
- **⭐ 운영 모니터링** (PR12에서 이관):
  - 메트릭 표출 (API 지연, WS 상태, 큐 사용률)
  - 최소 대시보드
  - A/B 비교 하니스 (ABComparisonReport로 구현)

## 제외(Out-of-Scope)
- 신호 무결성/Redis(→ PR9)
- 리스크 가드/프로퍼티 테스트 신규 추가(→ PR11)
- 고급 가격 레벨/거래소 스펙(→ PR12)

## 영향 파일(확정)

### .windsurfrules 허용 파일 범위 내 작업
**신규 파일**:
```
tuning/
├── config_overlay.py           # 🆕 설정 오버레이 시스템 (tuning/** 허용)
├── ensemble_tuner.py           # 🆕 Ensemble 튜닝 (tuning/** 허용)
├── rollout_manager.py          # 🆕 롤아웃 관리 (tuning/** 허용)
├── guardrail_engine.py         # 🆕 가드레일 (tuning/** 허용)
└── tuning_api.py               # 🆕 API (tuning/** 허용)

analytics/
└── ab_comparison.py            # 🆕 A/B 비교 리포트 (analytics/** 허용)

tests/
├── test_config_overlay.py      # 🆕 단위 테스트 (tests/** 허용)
├── test_ensemble_tuner.py      # 🆕 단위 테스트 (tests/** 허용)
└── test_rollout_manager.py     # 🆕 단위 테스트 (tests/** 허용)
```

**수정 파일** (.windsurfrules 허용 범위):
```
core/interfaces.py              # ✏️ 튜닝 관련 Protocol 추가 (허용)
core/flow_guardian.py           # ✏️ 튜닝 모드 READY 판정 추가 (허용)
execution/engine.py             # ✏️ ConfigOverlay 적용 (허용)
common/messaging.py             # ✏️ 튜닝 메시지 템플릿 (허용)
metrics/compute.py              # ✏️ 튜닝 메트릭 지원 (허용)
docs/PHASE6/**                  # ✏️ PR13 관련 문서 업데이트 (허용)
```

**참조만 하는 파일** (변경 없음):
```
strategies/ensemble.py          # ✅ Config 주입만 받음
common/config_loader.py         # ✅ 오버레이 로드 지원
common/redis_client.py          # ✅ 네임스페이스 키 사용
```

## 런타임/컨테이너 역할
- **trading_bot_paper_tuner**: 페이퍼 환경에서 베이시안 튜닝 루프 실행(자동). 결과를 오버레이 파일 및 Redis로 발행.
- **trading_bot_paper**: 페이퍼 실행 엔진. 섀도우/카나리 단계에서 튜닝 파라미터 적용 검증.
- **trading_bot_live**: 운영 엔진. 항상 안정화된 챔피언 파라미터만 사용. 실시간 조정 항목은 Redis를 통해 제한적으로 적용.
- **postgres**: 단일 DB. `env`, `run_id`로 데이터 분리.
- **redis**: 실시간 파라미터/상태 채널. 네임스페이스로 Paper/Live/Tuner 충돌 방지.

## 설정 키(제안)
- tuning.enabled: bool(기본 false)
- tuning.mode: "paper"|"shadow"|"canary"|"full"
- tuning.trials: int, tuning.window_hours: int
- rollout.canary.stages: [10,30,50,100]
- guardrails.max_dd_delta_pct: float
- guardrails.min_trades: int
- guardrails.max_vol_increase_pct: float

### DB/Redis 설계(단일 소스 + 분리)
- Postgres 공통 스키마(요지):
  - 공통 컬럼: `env VARCHAR(10) NOT NULL CHECK (env IN ('paper','live','tuner'))`, `run_id UUID NOT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
  - 예: `trading.trades(trade_id, symbol, side, qty, pnl, score_total, ... , env, run_id, created_at)`
  - 수용 기준 연계: `DB.score_total == JSON.score_total` 동등성 검증(샘플링 또는 전량)
- Redis 네임스페이스(충돌 방지):
  - 키 프리픽스: `{ns}:{env}:{run_id}:<domain>`
  - 예: `fa:tuner:{run}:tuning.params.set`, `fa:paper:{run}:ensemble.weights.update`
  - 채널 권장:
    - `tuning.params.set`(오버레이 배포)
    - `ensemble.weights.update`(가중치 실시간 조정; Live는 안전 항목만)
    - `risk.cap.update`(일일 손실/전략 예산 상한 조정)
    - `throttle.update`(거래 빈도 제한/쿨다운)
    - `equity.set`(Paper 자산 동기화용)

### 모드/파라미터 적용 정책
- 모드 해석 우선순위: `config.yml(mode)` > `ENV.TRADING_MODE` > 기본값 `paper`
- Live는 챔피언 파라미터만 사용. 실시간 변경 허용 항목은 운영 안전 파라미터에 한함(가중치 미세조정, 리스크 캡, 스로틀 등).
- Paper/Shadow/Canary에서만 실험 파라미터 적용. Canary 단계폭: 10%→30%→50%→100%.

## 아키텍처 계층/모듈 소유
- **core/**: 계약/게이트 전담. `interfaces.py`, `flow_guardian.py`만 위치. 비즈니스 구현 금지.
- **tuning/**: 튜닝 전담. `config_overlay.py`, `ensemble_tuner.py`, `rollout_manager.py`, `guardrail_engine.py`, `tuning_api.py` 등.
- **metrics/**: 메트릭 전담. `metrics/compute.py::MetricsEngine` 유지. Analytics(AB 비교)는 `analytics/`로 분리.
- **common/**: 공통 유틸. `config_loader`, `calculations`, `messaging`, `logger`, `redis_client`, `database`, `symbol_manager`, `utils` 등만.

### 모듈 재배치 정책 (.windsurfrules Module Relocation Policy PR13)
- **튜닝 모듈 통합**: `common/tuning_*.py`는 deprecated. 단일 진실 소스는 `tuning/` 하위 구현.
  - **이전**: `common/tuning_core.py`, `common/tuning_scheduler.py`
  - **이후**: `tuning/ensemble_tuner.py`, `tuning/rollout_manager.py` 등으로 대체
  - **정리**: deprecated 파일은 차기 코드 정리 PR에서 제거
- **메트릭 모듈 유지**: `metrics/compute.py`는 core로 이동 금지
  - **이유**: 단일 책임·의존 방향 유지 (계약은 core, 구현은 metrics)
  - **고정**: import 경로 `from metrics.compute import MetricsEngine` 유지

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)

### .windsurfrules 기본 게이트 준수
1. **FlowGuardian 게이트**: `tests/flow/test_flow_guardian.py` 통과
2. **로그 생성**: `logs/trial_0000.json` 생성 보장
3. **DB 동등성**: `DB.score_total == JSON.score_total` 일치 검증
4. **코드 품질**: pre-commit(ruff/black/mypy/vulture) 통과, coverage > 85%

### 튜닝/롤아웃 특화 기준 (.windsurfrules 준수)
- **Shadow 단계**: 8시간 이상 가드레일 위반 0건
- **Canary 단계**: 10%→30%→50%→100%, 각 단계 6시간 위반 0건
- **성과 기준**: 페이퍼 24h baseline 대비
  - `score_total` ≥ +15%
  - Sharpe-like ≥ +12%
  - MDD 증가 ≤ 0.5%p
- **거래 안정성**: 최소 거래수 ≥ 80, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%

### DB/Redis 분리 정책 준수
- **Postgres**: 모든 신규/핵심 테이블에 `env VARCHAR(10)`, `run_id UUID`, `created_at TIMESTAMPTZ` 필수
- **Redis**: 모든 키/채널에 `{ns}:{env}:{run_id}:<domain>` 네임스페이스 적용
- **검증**: DB env/run_id/created_at 채움률, Redis 네임스페이스 적용 로그 증적 포함

## 체크리스트(Checklist)

### 설계 완료 ✅
- [x] 시스템 분석 완료 (PR13_SYSTEM_ANALYSIS.md)
  - Gap Analysis (P0/P1/P2 우선순위)
  - 파일 구조 제안
- [x] 아키텍처 설계 완료 (PR13_ARCHITECTURE_DESIGN.md)
  - 5개 핵심 컴포넌트 (ConfigOverlay, EnsembleTuner, RolloutManager, GuardrailEngine, ABComparisonReport)
  - 데이터 플로우
  - 설정 스키마
  - 단일 DB/Redis 네임스페이스 설계(충돌 없음)

### 구현 예정
- [ ] **Phase 1: ConfigOverlay & EnsembleTuner** (P0, 2일)
  - tuning/config_overlay.py 구현
  - tuning/ensemble_tuner.py 구현 (기존 TunerCore 확장)
  - 단위 테스트
  - 통합 테스트 (24시간 페이퍼 실험)

- [ ] **Phase 2: RolloutManager & GuardrailEngine** (P0, 2일)
  - tuning/rollout_manager.py 구현
  - tuning/guardrail_engine.py 구현
  - 섀도우 모드 테스트
  - 카나리 모드 테스트 (10%→30%→50%→100%)

- [ ] **Phase 3: ABComparisonReport & 운영 모니터링** (P1, 1일)
  - analytics/ab_comparison.py 구현 (기존 report_generator.py 확장)
  - 차트 생성 (matplotlib)
  - Markdown 템플릿
  - 자동 리포트 생성 워크플로우
  - **⭐ PR12에서 이관된 운영 모니터링**:
    - 메트릭 표출 (API 지연, WS 상태, 큐 사용률)
    - 최소 대시보드 (Grafana 또는 간단한 웹 대시보드)
    - A/B 비교 하니스 (ABComparisonReport와 통합)

- [ ] **Phase 4: 통합 및 최적화** (P2, 1일)
 - [ ] Bug #8: 파라미터 후보 정의(min_confidence/consensus_bonus/budget_per_strategy) 및 오버레이 생성
  - API 통합 (tuning/api.py, tuning/rollout_api.py)
  - CLI 개선 (tuning/tuning_cli.py)
  - 성능 최적화

## 테스트 플랜(Test Plan)
- 페이퍼: N시간 K회 실험, 결과 분포/안정성 분석
- 섀도우: 실시간 로그/DB 영향 평가(거래 미반영)
- 카나리: 각 단계에서 가드레일 모니터링, 실패 시 롤백 검증
- 최종: full 적용 후 일정 기간 안정성 관찰

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 03:00 | 카나리 승격 후 DD 급증 | 가중 클램핑 누락 | max_weight_per_strategy 클램프 추가 | canary_guardrail_weight_clamp

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 실험/롤아웃 메타, 점수, 가드레일 이벤트
- DB: 결정/거래/리스크 이벤트의 전후 비교
 - DB 분리 필드: `env`, `run_id`의 채움률 및 유효성(모든 인서트 경로 적용) 로그로 검증

## 배포/롤백(Release/Rollback)
- 배포: tuning.mode 단계 변경으로 제어
- 롤백: 이전 파라미터 오버레이/기본값으로 즉시 회귀

## 리스크/완화(Risks & Mitigations)
- 과적합 위험 → OOS 윈도/분산 페널티/최소 거래수 적용
- 카나리 실패 → 자동 중단/롤백, 원인 로그
- 구성 드리프트 → config.yml 단일 소스, 커밋 해시 고정

## 운영 절차(Ops Runbook)

### 튜닝 시작 프로세스
1. **Paper 튜닝 시작**: `tuning.enabled=true`, `tuning.mode=shadow`
2. **Shadow 검증**: 8시간 가드레일 위반 0건 확인
3. **Canary 승격**: 단계별(10%→30%→50%→100%) 6시간 검증
4. **Live 전환**: `tuning.mode=full`, 챔피언 파라미터 고정 커밋

### 실시간 조정 (Redis 채널)
- **허용 항목**: `ensemble.weights.update`, `risk.cap.update`, `throttle.update`, `equity.set`
- **네임스페이스**: `{ns}:{env}:{run_id}:<domain>` 형식 준수
- **제한**: Live 환경은 안전 항목만 실시간 조정

### 검증 체크리스트 (.windsurfrules 준수)
1. **FlowGuardian**: `assert_ready(mode)` 호출 확인
2. **DB 분리**: env/run_id/created_at 필드 존재 및 채움 확인
3. **Redis 네임스페이스**: 로그에서 `:{env}:{run_id}:` 패턴 확인
4. **로그 생성**: `logs/trial_0000.json` 및 `DB.score_total == JSON.score_total` 동등성

## 릴리즈 노트(Release Notes)
- 운영 최적화 파이프라인 및 단계적 롤아웃 도입. 전략 로직 자체 변경은 최소화.

## Bug #8 튜닝 계획 (승률 6.65% 개선 - 파라미터 오버레이)
### 개요
- 본 PR13에서는 전략 로직을 변경하지 않고, 설정 오버레이(튜닝)를 통해 승률 저하를 완화합니다.
- PR12의 구조적 완화(가격 레벨 고급화/반올림/포트폴리오 가드)를 보완합니다.

### 튜닝 파라미터(후보)
- `ensemble.min_confidence`: 신뢰도 임계값 상향(예: 0.55→0.65) 후보군 그리드/베이시안 탐색
- `portfolio.budget_per_strategy`: 성과부진 전략 비중 하향, 상한/하한 클램프
- `ensemble.consensus_bonus`: 다전략 일치 시 가산점 조절(과도한 롱/숏 치우침 방지)
- `exits.trailing.multiplier`(선택): 트레일링 민감도 완화/강화 실험(출구 로직 자체는 변경 없음)

### 실험 설계
- 페이퍼 24h × N 트라이얼, OOS 샘플 기준
- A/B 비교: baseline vs tuned, `score_total`/Sharpe-like/승률/거래수/홀드시간/TP hit rate
- 가드레일: DD 증가 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%, 승률 하락 ≤ 0.5%p

### 롤아웃
- 섀도우 → 카나리(10%→30%→50%→100%)
- 단계별 6h 모니터링, 위반 시 자동 롤백(ConfigOverlay 회귀)

### 교차 참조
- PR12: 구조적 개선(레벨/스펙/포트폴리오)으로 실현 승률 및 체결율 개선
- PR10/PR11: Binance 호환성/리스크 가드와 충돌 없음
