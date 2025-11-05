# PHASE6 — PR11 마스터 플랜: 리스크 가드 강화 + 프로퍼티 테스트

## 배경/의도(Overview)
모든 모드에서 리스크 불변식을 보장하기 위해 안전 장치(Drawdown Cutoff, Slippage Guard)를 강화하고, 형식적인 프로퍼티 테스트를 도입합니다.

## 목표(Goals)
- 최대 손실/슬리피지 경계 강제
- 프로퍼티 테스트로 리스크 불변식 검증 자동화

## 범위(Scope, In)
- RiskManager: DD cutoff, Slippage Guard
- Property Tests: 일일 손실, 연속 손실 쿨다운, 익스포저/심볼·전체, 레버리지 경계, epsilon 경계
- 메시징 알림 후크(선택)

## 제외(Out-of-Scope)
- 고급 가격 레벨/거래소 라운딩(→ PR12)
- 앙상블 내부 로직(→ PR10)

## 영향 파일(예상)
- execution/risk_manager.py(가드)
- tests/risk/property_tests_*.py(새 테스트)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(수용 기준)
- config.yml(risk.* 키)

## 설정 키(제안)
- risk.max_drawdown_pct: float
- risk.max_slippage_pct: float
- risk.property_tests.enabled: bool

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 일일 손실 한도(risk.max_daily_loss_pct, 프로파일 기준) 초과 시 100% 차단 및 사유 로깅
- 슬리피지 가드: 예상 슬리피지 > execution.max_slippage_bp 기준(±epsilon)일 때 100% 차단
- 프로퍼티 테스트 스위트 100% 통과(pre-commit 포함), risk 모듈 커버리지 ≥ 95%
- pre-commit 통과, coverage>85%

## 체크리스트(Checklist)
- [ ] 전역 DD cutoff 강제
- [ ] 주문 단위 슬리피지 가드 강제
- [ ] 프로퍼티 테스트 구현/통과
- [ ] 가드 hit 시 알림(선택)

## 테스트 플랜(Test Plan)
- 유닛: 임계 경계/epsilon 처리
- 통합: 강제 DD/슬리피지 시나리오 → 차단 및 TTL 쿨다운 검증
- 회귀: 정상 변동성 구간에서 false positive 없음
- 프로퍼티 테스트 항목(예시):
  - daily_loss_pct ≤ risk.max_daily_loss_pct
  - consecutive_losses ≤ N → cooldown 활성화
  - exposure_per_symbol ≤ max_per_symbol + epsilon
  - total_exposure ≤ max_total + epsilon
  - leverage ∈ [min_leverage, max_leverage]
  - position_value_diff < epsilon 경계 내 비교 안전성

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 02:10 | DD 컷오프 미작동 | 프로파일 키 오버라이드 | paper/live 프로파일 병합 로직 수정 | property: dd_cutoff_profile_merge

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 리스크 이벤트 기록
- DB(risk_events/logs 테이블 존재 시): 차단/쿨다운 사유 저장

## 배포/롤백(Release/Rollback)
- 점진적 활성화(임계 완화 → 정상치)
- 오탑재 시 config.yml 키로 비활성화

## 리스크/완화(Risks & Mitigations)
- 임계 과도 설정 시 거래 정지 가능 → 단계적 조정, 경고 기준 도입
- 시세 급변 시 false positive → epsilon/버퍼/쿨다운 정책 보정

## 릴리즈 노트(Release Notes)
- 리스크 가드 강화 및 자동 검증 도입. 전략 로직 변경 없음.
