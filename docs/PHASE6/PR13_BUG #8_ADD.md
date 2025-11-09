# PR13 — BUG #8: 엔트리 품질(승률) 저하 개선 계획

> 이 문서는 PR13 마스터 플랜의 버그 특화 문서입니다. 마스터 문서: PR13_MASTER_PLAN.md

## 요약(Summary)
- 증상: 페이퍼/라이브에서 엔트리 품질 저하(승률 하락, TP hit rate 저하)가 관찰됨.
- 원인: 앙상블 파라미터가 고정/노이즈 민감. 전략별 예산/가중치 클램핑 미흡. 임계값/보너스 조정 미적용.
- 해결: 설정 오버레이(ConfigOverlay) + 베이시안 튜닝(EnsembleTuner)로 파라미터 최적화. 가드레일 기반 섀도우→카나리 롤아웃. Live는 챔피언 파라미터만.

## 증상(Symptoms)
- 승률 하락(최근 24h 기준 baseline 대비 -X%p)
- TP hit rate 하락, 평균 보유시간 증가
- 주문 거절률은 낮으나 체결 후 성과 저하

## 근본 원인(Root Cause)
- 앙상블 가중/임계 파라미터가 고정되어 시장 레짐 변화에 둔감
- 전략별 예산 배분과 가중치 상한 클램프 미흡으로 과도한 치우침 발생
- 임계값/보너스 미세 조정 부재로 엔트리 필터의 민감도 불균형

## 해결 전략(Resolution) - .windsurfrules 준수

### 핵심 컴포넌트 (.windsurfrules 허용 파일 범위 내)
- **ConfigOverlay** (`tuning/config_overlay.py`): 베이스 config.yml에 대한 런타임 오버레이 적용/관리
- **EnsembleTuner** (`tuning/ensemble_tuner.py`): Optuna 기반 베이시안 파라미터 최적화
- **GuardrailEngine** (`tuning/guardrail_engine.py`): DD 증가 ≤ 0.5%p, 최소 거래수 ≥ 20, 변동성 증가 ≤ 20%
- **RolloutManager** (`tuning/rollout_manager.py`): shadow(8h) → canary(10→30→50→100%) → full

### 튜닝 파라미터 후보
- `ensemble.min_confidence`: 신뢰도 임계값 최적화
- `portfolio.budget_per_strategy`: 전략별 예산 배분 및 가중치 상/하한 클램프
- `ensemble.consensus_bonus`: 다전략 일치 시 가산점 조절
- `exits.trailing.multiplier` (선택): 트레일링 민감도 조정 (출구 로직 변경 없음)

### 운영 정책 (.windsurfrules Runtime & Roles)
- **Live 환경**: 챔피언 파라미터만 사용. 실시간 조정은 안전 항목만 Redis로 허용
- **Paper 환경**: 섀도우/카나리 단계에서 실시간 파라미터 수신 및 적용
- **Tuner 환경**: 베이시안 자동 루프, 결과를 오버레이 파일 및 Redis로 발행

## DB/Redis 분리 정책 (.windsurfrules Data Separation/Redis Namespace Policy)

### Postgres 데이터 분리
- **필수 컴럼**: 모든 신규/핵심 테이블에 `env VARCHAR(10)`, `run_id UUID`, `created_at TIMESTAMPTZ` 필수
- **INSERT 경로**: 모든 INSERT는 env, run_id를 누락 없이 채움. 인덱스/뷰에 (env, created_at) 포함 권장
- **지표 동기화**: 로그/리포트/DB 간 score_total 등 핵심 지표는 단일 정의에 따라 동기화

### Redis 네임스페이스
- **키 형식**: 모든 키/채널은 `{ns}:{env}:{run_id}:<domain>` 접두사를 사용해 충돌 방지
- **권장 채널**: `tuning.params.set`, `ensemble.weights.update`, `risk.cap.update`, `throttle.update`, `equity.set`
- **상태 키**: 캔들 dedup 등 상태키도 동일 네임스페이스 적용
- **예시**: `fa:paper:{run_id}:candle:seen:{symbol}:{tf}:{closed_at}`

## 수용 기준(Acceptance) - .windsurfrules Testing & Acceptance 준수

### 기본 게이트 수용 기준
1. **FlowGuardian 게이트**: `tests/flow/test_flow_guardian.py` 통과
2. **로그 생성**: `logs/trial_0000.json` 생성 보장
3. **DB 동등성**: `DB.score_total == JSON.score_total` 일치 검증
4. **FlowGuardian READY**: READY 미호출 시 PAPER/LIVE 실행 금지
5. **코드 품질**: pre-commit(ruff/black/mypy/vulture) 통과, coverage > 85%

### 튜닝/롤아웃 수용 기준 (PR13 특화)
- **Shadow 단계**: 8시간 이상 가드레일 위반 0건
- **Canary 단계**: 10%→30%→50%→100%, 각 단계 6시간 위반 0건
- **성과 기준**: 페이퍼 24h baseline 대비 score_total ≥ +15%, Sharpe-like ≥ +12%, MDD 증가 ≤ 0.5%p
- **거래 안정성**: 최소 거래수 ≥ 80, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%

### DB/Redis 분리 정책 준수
- **Postgres**: env/run_id/created_at 필드 존재 및 채움률 검증
- **Redis**: 모든 키/채널에 env/run_id 포함 로그 증적
- **네임스페이스**: 비네임스페이스 키 사용 시 CI 실패

## 테스트 플랜(Test Plan) - .windsurfrules 테스트 매트릭스 준수

### unit/contract/flow/gate/tuning 매트릭스
- **Unit**: ConfigOverlay deep-merge/스키마 검증, 가중치 클램프, 임계/보너스 적용 ✅ Phase 1 완료
- **Contract**: Interface/Protocol 계약 검증 (core/interfaces.py 준수)
- **Flow**: 24h×N 트라이얼, A/B 비교(ABComparisonReport) 자동 생성
- **Gate**: FlowGuardian READY 게이트 검증
- **Tuning**: 
  - ✅ Phase 1: 단위 테스트 (ConfigOverlay 17개 + EnsembleTuner 13개)
  - ⏳ Phase 1.5: 실제 튜닝 실행 검증 (3 trials, 오버레이 파일 생성)
  - ⏳ Phase 2: 섀도우/카나리 단계별 가드레일 체크 및 자동 승격/롤백

### 특화 테스트
- **섀도우 모드**: 실시간 메트릭 수집, 거래 미반영 검증 (8시간)
- **카나리 모드**: 10→30→50→100% 단계별 6시간 모니터링
- **가드레일**: DD/거래수/변동성 한계 위반 시 자동 롤백 검증
- **Live 전환** (Phase 2.5 - NEW):
  - 챔피언 파라미터 확정 및 커밋
  - Live 모드 실행 검증 (Binance API 호출)
  - 실거래 모니터링 (최소 24시간)
  - Paper/Live 파리티 검증 (로직 동일, 실행만 다름)
  - DB env='live', Redis fa:live:{run_id}:* 확인
  - 긴급 롤백 절차 준비

## 롤백 절차(Rollback) - 운영 안전성 보장

### 자동 롤백 시나리오
- **가드레일 위반**: GuardrailEngine에서 DD/거래수/변동성 한계 초과 감지 시
- **카나리 단계 실패**: 각 단계에서 6h 모니터링 중 위반 발생 시
- **시스템 오류**: ConfigOverlay 적용 실패 또는 Redis 채널 오류 시

### 롤백 단계
1. **즉시 중단**: `tuning.mode=none` 설정 또는 이전 안정 버전 `tuning_best.yml`로 복귀
2. **사유 로깅**: 실패 원인, 시간, 영향 범위 상세 로깅
3. **알림 전송**: 운영팀에 즉시 알림 (Telegram/Slack)
4. **상태 검증**: 롤백 후 시스템 정상 동작 확인

## 산출물(Artifacts) - .windsurfrules 준수

### 파일 산출물
- **오버레이 설정**: `configs/overlays/tuning_best_<study>.yml`
- **실험 로그**: `logs/trial_0000.json` (.windsurfrules 필수 생성)
- **A/B 비교**: `logs/ab_comparison/ensemble_<timestamp>/`
- **테스트 결과**: `tests/results/` 하위 단위/통합/롤아웃 테스트 결과

### DB 산출물 (.windsurfrules DB 분리 정책)
- **거래 데이터**: `trading.trades` 테이블 with `(env, run_id, created_at)`
- **의사결정**: `trading.decisions` 테이블 with `(env, run_id, created_at)`
- **리스크 이벤트**: `trading.risk_events` 테이블 with `(env, run_id, created_at)`
- **메트릭 동기화**: `DB.score_total == JSON.score_total` 동등성 보장

## 문서 관계(Documentation)
- 마스터: PR13_MASTER_PLAN.md
- 설계: PR13_ARCHITECTURE_DESIGN.md
- 시스템 분석: PR13_SYSTEM_ANALYSIS.md

---

## (아카이브) 이전 내용

## 배경/의도(Overview)
페이퍼 모드에서 검증된 베이시안 튜닝을 운영 환경에 안전하게 적용합니다. 섀도우런→카나리→점진적 확대의 롤아웃 전략과 가드레일(리스크 한계/변동성/최소 거래수)을 갖춘 운영 최적화 파이프라인을 구축합니다. FlowGuardian READY 게이트는 항상 유지됩니다.
- `ensemble.min_confidence`: 신뢰도 임계값 상향(예: 0.55→0.65) 후보군 그리드/베이시안 탐색
- `portfolio.budget_per_strategy`: 성과부진 전략 비중 하향, 상한/하한 클램프
- `ensemble.consensus_bonus`: 다전략 일치 시 가산점 조절(과도한 롱/숏 치우침 방지)
- `exits.trailing.multiplier`(선택): 트레일링 민감도 완화/강화 실험(출구 로직 자체는 변경 없음)

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
