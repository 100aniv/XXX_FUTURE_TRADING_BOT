# PHASE6 — PR16 마스터 플랜: 전략 신호 로직 개선(필터/임계/중복 제거)

## 배경/의도(Overview)
8h/24h 평가에서 관측된 낮은 승률(예: 6.65%) 문제를 해결하기 위해 전략 신호 생성 로직을 체계적으로 개선합니다. 신호 품질을 높이되, 설정 단일 소스(config.yml), 하드코딩 제거, 모듈 단일 책임 및 중복 제거 원칙을 준수합니다. FlowGuardian READY 게이트는 항상 유지합니다.

## 목표(Goals)
- 엔트리 신호 품질 개선(필터/임계/쿨다운/멱등성 강화)
- 신뢰도 임계값/컨센서스 보너스/전략별 예산의 설정화 및 오버레이 지원
- 중복/하드코딩 제거 및 모듈 경계 정리(단일 책임)
- Bug #8: 승률 저하 개선(엔트리 품질 중심) — PR12/PR13 구조·튜닝과 상호 보완

## 범위(Scope, In)
- strategies/ensemble.py: 신뢰도 임계/컨센서스 보너스/최대 가중 클램프 주입(설정 기반)
- strategies/*: 엔트리 필터(최소 샘플/변동성/레짐) 및 신호 멱등성/쿨다운 점검
- common/*: 중복 로직 모듈화(필요 시), 하드코딩 제거
- analytics/*: 신호 품질 지표(Precision/Recall proxy, TP hit rate 전조 지표) 산출
- tests/strategy/*: 단위/속성/통합 테스트 추가

## 제외(Out-of-Scope)
- 거래소 스펙/라운딩/펀딩 로직(→ PR12)
- 리스크 가드/프로퍼티 테스트 신규 추가(→ PR11)
- 튜닝/롤아웃 파이프라인(→ PR13)

## 영향 파일(예상)
- strategies/ensemble.py, strategies/* (필터/쿨다운/멱등성)
- common/calculations.py, common/utils.py(중복 제거 시)
- analytics/metrics.py 또는 analytics/report_generator.py(신호 품질 지표)
- tests/strategy/test_*.py
- config.yml(strategy.*, ensemble.*, portfolio.* 일부)

## 설정 키(제안)
- strategy.filters.min_samples: int
- strategy.filters.min_volatility_pct: float
- ensemble.min_confidence: float (PR13 오버레이와 연계)
- ensemble.consensus_bonus: float
- portfolio.budget_per_strategy: dict (PR13 오버레이와 연계)
- signals.cooldown.sec: int

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 승률: baseline 대비 +5.0%p 이상(최소 +3.0%p 달성 시 조건부 통과)
- `score_total`: baseline 대비 ≥ +10% 향상, Sharpe-like ≥ +10% 향상, MDD 증가는 ≤ 0.5%p
- 거래 수 변화 |Δ| ≤ 20%, 평균 보유시간 악화 없음(±5% 내)
- logs/trial_0000.json 생성, DB.score_total == JSON.score_total 일치
- pre-commit 통과(ruff/black/mypy/vulture), coverage > 85%

## 체크리스트(Checklist)
- [ ] 신뢰도 임계/컨센서스 보너스/가중 클램프 설정 주입
- [ ] 엔트리 필터(최소 샘플/변동성/레짐) 및 쿨다운/멱등성 가드 강화
- [ ] 중복 제거 및 공통 유틸 이전(필요 시)
- [ ] 신호 품질 지표 로깅 및 리포트 노출
- [ ] 단위/속성/통합 테스트 통과
- [ ] PR12/PR13과 상호 영향 점검(구조/튜닝 대비 이득/부작용 분석)

## 테스트 플랜(Test Plan)
- 유닛: 필터 임계 경계/쿨다운/멱등성/가중 클램프
- 속성: 동일 입력 멱등성, 임계 ±epsilon 전후 동작 일관성
- 통합: 실시간 스트림 K시간, false positive/negative 점검, 거래 수 영향 관찰
- A/B: baseline vs 개선안 — 승률/TP hit rate/홀드시간/score_total/Sharpe-like

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 신호 품질/결정/거래 메타 기록
- DB: decisions/trades — 승률 및 품질 관련 컬럼 정합

## 배포/롤백(Release/Rollback)
- 섀도우런 → 카나리(10%→30%→50%→100%) 단계 적용(운영 반영은 PR13 롤아웃 정책 준수)
- 문제 시 설정 키로 즉시 회귀(오버레이 제거 또는 기본값 복원)

## 리스크/완화(Risks & Mitigations)
- 임계 과도 상향 → 거래 급감/드리프트 위험 — 단계적 상향, A/B 감시, 가드레일 경계 적용
- 필터 과적합 위험 — OOS 윈도/보수적 페널티/최소 거래수 제약

## 문서 동기화(필수)
- PR12/PR13 문서와 교차 링크 — 구조적 완화/튜닝 오버레이와 정합성 확인
- .windsurfrules 준수 상태 및 예외(전략 로직 변경) 명시 및 승인 경로 기록

## 릴리즈 노트(Release Notes)
- 전략 신호 로직 개선으로 승률/안정성 향상. 설정 기반/무하드코딩/단일 책임 원칙 준수. FlowGuardian READY 유지.
