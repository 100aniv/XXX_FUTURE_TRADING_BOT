# PHASE6 — PR13 마스터 플랜: 베이시안 운영 튜닝 & 단계적 롤아웃

## 배경/의도(Overview)
페이퍼 모드에서 검증된 베이시안 튜닝을 운영 환경에 안전하게 적용합니다. 섀도우런→카나리→점진적 확대의 롤아웃 전략과 가드레일(리스크 한계/변동성/최소 거래수)을 갖춘 운영 최적화 파이프라인을 구축합니다. FlowGuardian READY 게이트는 항상 유지됩니다.

## 목표(Goals)
- 페이퍼 기반 최적 파라미터 산출(가중치/임계/보너스/출구 일부)
- 섀도우 모드에서 안전성 검증 후 카나리 릴리즈
- 가드레일 기반 자동 중단/롤백 체계

## 범위(Scope, In)
- 튜닝 파이프라인: 실험 구성(K회/시간창), 결과 집계, 오버레이 산출
- 운영 롤아웃: 섀도우런→카나리(10%→30%→50%→100%) 단계 적용
- 가드레일: DD 증가 한계, 최소 거래수, 분산/변동성 상승 한계, 에러율
- A/B 비교: baseline vs tuned 결과 리포트

## 제외(Out-of-Scope)
- 신호 무결성/Redis(→ PR9)
- 리스크 가드/프로퍼티 테스트 신규 추가(→ PR11)
- 고급 가격 레벨/거래소 스펙(→ PR12)

## 영향 파일(확정)

### 신규 파일 (구현 필요)
```
tuning/
├── config_overlay.py           # 🆕 설정 오버레이 시스템
├── ensemble_tuner.py           # 🆕 Ensemble 튜닝 (TunerCore 확장)
├── rollout_manager.py          # 🆕 롤아웃 관리
├── guardrail_engine.py         # 🆕 가드레일
└── tuning_api.py               # 🆕 API

analytics/
└── ab_comparison.py            # 🆕 A/B 비교 리포트
```

### 수정 파일 (기존 활용)
```
tuning/
├── tuning_core.py              # ✏️ 단일 전략용 (유지, EnsembleTuner가 확장)
└── tuning_scheduler.py         # ✏️ 스케줄러 (Ensemble 추가)

analytics/
└── report_generator.py         # ✏️ 기존 리포트 (ABComparison이 확장)

config.yml                      # ✏️ tuning.* 섹션 추가
```

### 참조 파일 (변경 없음)
```
metrics/compute.py              # ✅ 메트릭 계산 (그대로 사용)
core/interfaces.py              # ✅ Protocol (그대로 사용)
strategies/ensemble.py          # ✅ Ensemble 로직 (Config만 주입)
```

## 설정 키(제안)
- tuning.enabled: bool(기본 false)
- tuning.mode: "paper"|"shadow"|"canary"|"full"
- tuning.trials: int, tuning.window_hours: int
- rollout.canary.stages: [10,30,50,100]
- guardrails.max_dd_delta_pct: float
- guardrails.min_trades: int
- guardrails.max_vol_increase_pct: float

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 24시간 페이퍼 실험에서 baseline 대비 `score_total` ≥ 15% 향상
- Sharpe-like(analytics.kpis) ≥ 12% 향상, MDD 증가는 ≤ 0.5%p
- 최소 거래수 ≥ 80, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%
- 섀도우 모드: 8시간 이상 가드레일 위반 0건(DD 증가 한계, min_trades, 변동성 증가)
- 카나리 단계(10%→30%→50%→100%): 각 단계 6시간 이상 가드레일 위반 0건 시에만 승격
- logs/trial_0000.json/DB 동등성 유지, pre-commit 통과

## 체크리스트(Checklist)

### 설계 완료 ✅
- [x] 시스템 분석 완료 (PR13_SYSTEM_ANALYSIS.md)
  - 기존 구현 현황 (tuning/, analytics/, metrics/, core/)
  - Gap Analysis (P0/P1/P2 우선순위)
  - 파일 구조 제안
- [x] 아키텍처 설계 완료 (PR13_ARCHITECTURE_DESIGN.md)
  - 5개 핵심 컴포넌트 (ConfigOverlay, EnsembleTuner, RolloutManager, GuardrailEngine, ABComparisonReport)
  - 데이터 플로우
  - 설정 스키마

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

- [ ] **Phase 3: ABComparisonReport** (P1, 1일)
  - analytics/ab_comparison.py 구현 (기존 report_generator.py 확장)
  - 차트 생성 (matplotlib)
  - Markdown 템플릿
  - 자동 리포트 생성 워크플로우

- [ ] **Phase 4: 통합 및 최적화** (P2, 1일)
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

## 배포/롤백(Release/Rollback)
- 배포: tuning.mode 단계 변경으로 제어
- 롤백: 이전 파라미터 오버레이/기본값으로 즉시 회귀

## 리스크/완화(Risks & Mitigations)
- 과적합 위험 → OOS 윈도/분산 페널티/최소 거래수 적용
- 카나리 실패 → 자동 중단/롤백, 원인 로그
- 구성 드리프트 → config.yml 단일 소스, 커밋 해시 고정

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
