# PHASE6 — PR10 마스터 플랜: 앙상블 고급화 + Experience Score + 베이시안 튜닝(설계)

## 배경/의도(Overview)
앙상블 품질을 고도화하고, 데이터 충분성과 최근 OOS 성능을 반영한 Experience Score를 도입합니다. 베이시안 튜닝은 페이퍼 모드에서 설계/준비만 수행하며, 실제 운영 반영은 PR13(운영 튜닝/롤아웃)에서 안전 게이팅과 함께 진행합니다.

## 목표(Goals)
- 앙상블 의사결정의 품질/안정성 향상
- Experience Score 산출 및 로깅
- 페이퍼 모드 기반 튜닝 설계(운영 반영은 PR13에서 단계적 적용)

## 범위(Scope, In)
- 가중치 개선(Sharpe, 승률, MDD, 샘플 크기 등)
- 보너스 로직(컨센서스/리스크 보정) 정리 및 클램핑
- Experience Score 계산/로깅
- 튜닝 파라미터/오버레이 구조 설계(실 적용은 PR13)

## 제외(Out-of-Scope)
- 엔진/Redis(→ PR9)
- 리스크 가드 강화(→ PR11)
- 고급 가격 레벨/거래소 스펙(→ PR12)

## 영향 파일(예상)
- strategies/ensemble.py(가중/점수/로깅)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(테스트)
- config.yml(ensemble.* 키; 튜닝 키는 PR13에서 활성화)

## 설정 키(제안; PR13에서 활성화)
- ensemble.min_confidence: float
- ensemble.consensus_bonus: float
- ensemble.max_weight_per_strategy: float
- ensemble.experience.min_trades: int
- tuning.enabled: bool(기본 false)
- tuning.sampler: "tpe"|"bayes"
- tuning.trials: int

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 24시간 페이퍼 평가에서 baseline 대비 `score_total` ≥ 12% 향상
- Sharpe-like(analytics.kpis) ≥ 10% 향상
- 최대낙폭(MDD) 증가는 ≤ 1%p
- 최소 거래수 ≥ 60, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%
- DB/JSON 동등성 및 logs/trial_0000.json 유지
- pre-commit 통과, coverage>85%

## 체크리스트(Checklist)
- [ ] 가중치 계산 업데이트 및 클램핑(설정 기반)
- [ ] Experience Score 계산/기록
- [ ] 튜닝 파라미터/오버레이 구조 설계 완료(PR13 연계)
- [ ] A/B 비교 리포트(페이퍼) 산출 경로 정의

## 테스트 플랜(Test Plan)
- 유닛: 가중치 수식/경계, Experience Score 입력/엣지
- 통합: 페이퍼 모드 N시간 비교(baseline vs 개선)
- A/B: 의사결정 분포/점수/간단 PnL proxy 비교

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 01:20 | 앙상블 가중치 NaN | 샘플 부족 | min_trades 가드 추가 | unit: experience_min_trades

## 라이브 모드 고려사항(Live Considerations)
- 라이브 전략 파일에 백테스트 전용 휴리스틱 삽입 금지(오버레이/설정으로 분리)
- 안전모드/섀도우런 우선, 실제 반영은 PR13의 게이트/롤아웃 정책 적용

## 리스크 & 롤백(Risks & Rollback)
- 튜닝 과적합 위험: OOS 윈도/패널티/최소 거래수 제약으로 완화
- 롤백: ensemble.* 기본값 회귀, 튜닝 비활성화

## 비고(Notes)
- PR13에서 베이시안 운영 튜닝을 정식 적용(스케줄러/오버레이/게이트 연동)
