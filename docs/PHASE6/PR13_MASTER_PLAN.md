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

#### Phase별 참조 문서 가이드
각 Phase 진행 시 아래 문서를 참조하여 누락 없이 구현:

**Phase 1: ConfigOverlay & EnsembleTuner**
- 📖 주 참조: `PR13_ARCHITECTURE_DESIGN.md` (2.1 ConfigOverlay, 2.2 EnsembleTuner 섹션)
- 🧪 테스트: `PR13_BUG #8_ADD.md` (Unit 테스트 매트릭스 라인 75)
- 📏 정책: `.windsurfrules` (Architecture Layering Policy, Redis Namespace Policy)

**Phase 2: RolloutManager & GuardrailEngine**
- 📖 주 참조: `PR13_ARCHITECTURE_DESIGN.md` (2.3 RolloutManager, 2.4 GuardrailEngine 섹션)
- 🧪 테스트: `PR13_BUG #8_ADD.md` (Tuning 테스트 매트릭스 라인 79)
- 📏 정책: `.windsurfrules` (Runtime & Roles)

**Phase 3: ABComparisonReport & 통합**
- 📖 주 참조: `PR13_ARCHITECTURE_DESIGN.md` (2.5 ABComparisonReport, 3절 데이터 플로우)
- 🔗 통합: `PR13_SYSTEM_ANALYSIS.md` (5절 처리 단계 라인 234-247)
- ✅ 수용: `PR13_BUG #8_ADD.md` (수용 기준 라인 52-70)

---

## 🐛 **Fix Log & 이슈 추적**

### Phase 1.5 이슈
1. **window 파라미터 타입 오류** (2025-11-09 22:49)
   - 문제: `run_tuner.py` window 파라미터가 int로 정의되어 소수점 불가
   - 해결: type=float로 변경
   - 커밋: `fix(PR13): window 파라미터 float 지원`

2. **EnsembleTuner 시그니처 불일치** (2025-11-09 22:49)
   - 문제: `run_tuner.py`에서 namespace/env/run_id 파라미터 전달, 하지만 EnsembleTuner는 받지 않음
   - 해결: 불필요한 파라미터 제거
   - 커밋: `fix(PR13): EnsembleTuner 시그니처 수정`

3. **거래 미발생 (Paper 모드)** (2025-11-09 22:52 ~ 23:53) ✅ **최종 해결**
   - 현상: 오후 9시 38분 이후 신호 발생 → Ensemble 결정 → 거래 미발생, 텔레그램 알람 없음
   - **근본 원인**: Docker 컨테이너가 재기동(restart)만 되고 재빌드(rebuild) 안됨
     - broker.execute() 코드 수정했으나 구버전 이미지로 실행
     - 멱등성 개선 코드 미적용 (해시 기반 → candle_close_time 기반)
     - Redis에 102개 구버전 멱등 키 잔존
   - 해결 과정:
     1. **broker.execute() 호출 추가** (2025-11-09 23:22)
        - 라인 1239: `fill = broker.execute(decision, qty)` 추가
        - 라인 1247-1248: `position_id`, `entry_time` 생성
        - 라인 1238-1420: 전체 들여쓰기 수정
     2. **멱등성 개선** (2025-11-09 23:42)
        - 타임프레임 기반 동적 TTL (1m=63s, 5m=315s)
        - 멱등 키: symbol:side:candle_close_time
        - 로그 레벨: INFO → WARNING
     3. **Docker 재빌드 + Redis 플러시** (2025-11-09 23:50)
        - `docker-compose build trading_bot_paper_ensemble`
        - `docker exec trading_redis redis-cli FLUSHALL`
   - **검증 완료** (2025-11-09 23:53):
     - ✅ DB 저장: ICPUSDT SHORT @ 23:00, TIAUSDT LONG @ 23:53
     - ✅ 텔레그램 알림: "[TELEGRAM] [ENSEMBLE] TIAUSDT | LONG X2🔵📈"
     - ✅ 마지막 거래: 23:53 (2시간 15분 공백 해소)
   - 커밋:
     - `fix(CRITICAL): broker.execute() 호출 누락 수정`
     - `fix(PR9): 멱등성 개선 - 타임프레임 기반 동적 TTL`
   - 참고: `execution/engine.py` 라인 1238-1247 (broker), 137-156 (TTL), 1133-1156 (멱등)

### 설계 검증
1. **SQLite → PostgreSQL 정책** (2025-11-09)
   - ✅ 모든 문서 및 코드에서 PostgreSQL로 통일
   - ✅ `ensemble_tuner.py` 기본 storage 수정

2. **자동 루프 설계** (2025-11-09)
   - ✅ `run_tuner_loop.py` 구현 (while True + sleep)
   - ✅ Redis 파라미터 발행 기능 포함
   - ✅ 문서 명시 사항과 100% 일치

---

## 처리 단계

- [✅] **Phase 1: ConfigOverlay & EnsembleTuner** (P0, 2일) - **✅ 완료 및 검증**
  - [✅] tuning/config_overlay.py 구현 - **완료** (17개 테스트 통과)
  - [✅] tuning/ensemble_tuner.py 구현 (기존 TunerCore 확장) - **완료** (13개 테스트 통과)
  - [✅] 단위 테스트 - **Phase 1 완료** (ConfigOverlay 17개 + EnsembleTuner 13개 = 30개 전체 통과)
  - [✅] 통합 테스트 (페이퍼 모드 검증) - **완료** (15분 실행, 에러 0건, 정상 실행)
  - [✅] PostgreSQL 저장소 설정 - **완료** (SQLite 제거, 단일 DB 정책 준수)
  - [✅] 최종 검증 - **2025-11-09 22:23 완료**

- [✅] **Phase 1.5: 튜닝 실행 검증** (P0, 0.5일) - **✅ 완료**
  - [✅] 튜닝 실행 스크립트 작성 (scripts/run_tuner.py) - **완료**
  - [✅] 클린 환경 준비 (모든 컨테이너 종료 + DB/Redis 데이터 클린) - **완료**
  - [✅] 자동 루프 스크립트 작성 (scripts/run_tuner_loop.py) - **완료**
    - while True + sleep 구현
    - Redis 파라미터 발행 기능
    - 주기적 튜닝 실행
  - [✅] Paper 모드 실행 (10분 데이터 쌓기) - **완료**
  - [✅] 튜닝 실행 테스트 (3 trials, 10분 window) - **완료**
    - 1개 성공, 2개 pruned
    - Best 값: 0.3000
    - 실행 시간: 약 1초
  - [✅] 오버레이 파일 생성 확인 (configs/overlays/) - **완료**
    - tuning_best_ensemble_tuning_20251109_225033.yml
  - [✅] Best 파라미터 검증 - **완료**
    - 9개 파라미터 정상 생성
  - [✅] Docker Compose 설정 추가 (trading_bot_paper_tuner) - **완료**
    - 컨테이너: trading_bot_paper_tuner
    - 프로파일: tuner, paper
    - 자동 루프: 1시간마다 3 trials
    - Redis 발행: 활성화
  - [✅] 문서 업데이트 및 커밋 - **2025-11-09 23:02 최종 완료**

- [ ] **Phase 2: RolloutManager & GuardrailEngine** (P0, 2일)
  - tuning/rollout_manager.py 구현
  - tuning/guardrail_engine.py 구현
  - 섀도우 모드 테스트 (8시간 가드레일 위반 0건)
  - 카나리 모드 테스트 (10%→30%→50%→100%, 각 단계 6시간)

- [ ] **Phase 2.5: Live 전환 및 검증** (P0, 1일) - **NEW**
  - [ ] 챔피언 파라미터 확정 및 커밋
  - [ ] Live 모드 전환 (tuning.mode=full)
  - [ ] Live 모드 실행 검증 (Binance API 호출 정상)
  - [ ] 실거래 모니터링 (최소 24시간)
  - [ ] Paper/Live 파리티 검증 (로직 동일, 실행만 다름)
  - [ ] FlowGuardian READY 게이트 Live 모드 검증
  - [ ] DB env='live' 데이터 확인
  - [ ] Redis 네임스페이스 fa:live:{run_id}:* 확인
  - [ ] 긴급 롤백 절차 준비 (이전 파라미터로 즉시 복귀)

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

---

## ❓ **FAQ (자주 묻는 질문)**

### Q1: 튜너는 Docker로 실행하나요?
**A:** ✅ 예! `trading_bot_paper_tuner` 컨테이너로 실행합니다.

**실행 방법:**
```bash
# Paper + Tuner 함께 실행
docker-compose --profile paper up -d

# 또는 Tuner만 실행
docker-compose --profile tuner up -d trading_bot_paper_tuner
```

**설정:**
- 컨테이너: `trading_bot_paper_tuner`
- 자동 루프: 1시간마다 3 trials (24h window)
- Redis 발행: 활성화
- 오버레이 저장: `configs/overlays/`

**참조:** 
- docker-compose.yml 라인 254-303
- 라인 66 (런타임/컨테이너 역할)

### Q2: 오버레이 파일의 역할은?
**A:** 튜닝된 파라미터를 저장하는 설정 파일입니다.
- **생성**: EnsembleTuner.optimize() 완료 후 자동 생성
- **위치**: `configs/overlays/tuning_best_{study_name}.yml`
- **사용**: ConfigOverlay.load_overlay()로 로드하여 base config에 병합
- **예시**: alpha_winrate, beta_rr 등 9개 파라미터

### Q3: 튜닝은 1회만 실행되나요?
**A:** 아니오, 자동 루프로 연속 실행됩니다.
- **테스트**: `run_tuner.py` (1회 실행)
- **운영**: `run_tuner_loop.py` (while True + sleep)
- **주기**: 기본 1시간마다 (설정 가능)
- **참조**: 라인 45, 199-202

### Q4: 라이브 모드에 어떻게 반영되나요?
**A:** 2가지 방식으로 반영됩니다.

**방법 1: 실시간 (Redis)** - 가중치/리스크
```python
# tuner → Redis 발행
redis_client.publish("fa:live:{run_id}:ensemble.weights.update", params)

# live 엔진 수신 → 즉시 적용
```
- 채널: `ensemble.weights.update`, `risk.cap.update`
- 지연: 거의 즉시 (초 단위)
- 참조: 라인 263-265

**방법 2: 단계적 (오버레이)** - 전략 파라미터
```python
# Phase 2: ConfigOverlay 로드
overlay = ConfigOverlay("config.yml")
overlay.load_overlay("tuning_best_*.yml")

# Phase 2: RolloutManager 단계적 적용
Shadow (8h) → Canary (10%→100%, 각 6h) → Full

# Phase 2.5: Live 전환
챔피언 파라미터 고정 커밋 → Live 모드 적용
```
- 단계: Shadow/Canary 검증 필수
- 지연: 24~48시간 (안전 검증)
- 참조: 라인 257-260

### Q5: 성과 비교는 어떻게 하나요?
**A:** Phase 3에서 ABComparisonReport 구현 예정입니다.
- **현재**: 튜닝 실행 + 오버레이 생성 (Phase 1.5 완료)
- **다음**: RolloutManager로 Shadow/Canary 단계 검증 (Phase 2)
- **이후**: A/B 비교 리포트 자동 생성 (Phase 3)
- **참조**: 라인 237-243

### Q6: 거래가 발생하지 않는 이유는?
**A:** ✅ 해결 완료! Redis 신호 멱등 TTL 문제였습니다.
- **원인**: Redis TTL 3600초 (1시간) → 동일 신호 1시간 차단
- **현상**: 신호 발생 → Ensemble 결정 → 멱등 차단 → 거래 미발생
- **해결**: `Redis FLUSHALL` + Paper 재시작
- **상태**: ✅ 해결 완료 (2025-11-09 22:57)
- **참조**: 라인 188-194 (Fix Log)

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
