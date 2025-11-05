# PHASE6 — PR14 마스터 플랜: 최종 상용 검증 & 무중복 아키텍처 감사

## 배경/의도(Overview)
전체 PR(8~13) 결과물을 상용 기준으로 최종 검증합니다. 모듈/함수 중복, 하드코딩, 문서-코드-설정 동기화, 안정성/회귀/부하/장시간 테스트를 수행하고 FlowGuardian 게이트/로그/DB/커버리지를 최종 확인합니다.

## 목표(Goals)
- 무중복(duplicate-free) 아키텍처 보장 및 하드코딩 제거
- 문서/코드/설정 정합성 100%
- 안정성·회귀·부하·장시간(재시작/네트워크 변동/백프레셔) 테스트 통과
- 커버리지 상향(≥90% 권장), pre-commit 100% 통과

## 범위(Scope, In)
- 코드 정적 분석(중복/미사용/스타일) 및 제거
- 설정(config.yml) 단일 소스 준수 검증 및 drift 제거
- 문서 동기화(아래 문서 포함) 및 링크 점검
- 통합/회귀/부하/장시간 테스트 실행
- FlowGuardian READY 게이트 최종 검수

## 제외(Out-of-Scope)
- 신규 기능 개발(테스트/정리 중심)

## 영향 파일(예상)
- tests/**/* (회귀/부하/장시간/통합)
- docs/**/* (REFACTORING_* 문서 동기화)
- .pre-commit-config.yaml, CI 스크립트(필요 시)

## 설정 키(제안)
- testing.longrun.enabled: bool
- testing.load.max_qps: int
- testing.stability.hours: int

## 문서 동기화(필수)
- docs/PHASE5/REFACTORING_문서아키텍처.md
- docs/PHASE5/REFACTORING_flow_guardian_gate.md(존재 시)
- docs/PHASE6/PR*_MASTER_PLAN.md 전 섹션 교차 링크 점검

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)
- 중복/하드코딩/규칙 위반 0건(vulture/ruff/custom rule)
- logs/trial_0000.json 생성 보장, DB score_total == JSON score_total
- 회귀/부하/장시간 테스트 전부 통과
- 24h 안정성: 프로세스 크래시 0건, 메모리 증가율 ≤ 3%, CPU p95 ≤ 80%
- 부하: 큐 사용률 p95 ≤ 70%, queue_drop_rate_pct ≤ 0.25%, api_latency_ms_p95 ≤ 300ms
- 재시작 내구성: 의도적 재시작 3회 동안 데이터 유실 0, 복구 시간 ≤ 45초
- 커버리지 ≥ 90%(권장), pre-commit 전 항목 통과

## 체크리스트(Checklist)
- [ ] 코드 중복/미사용 제거, 하드코딩 제거
- [ ] 문서-코드-설정 링크/동기화 점검
- [ ] 회귀/부하/장시간 테스트 작성 및 통과
- [ ] FlowGuardian READY/로그/DB/커버리지 최종 확인

## 테스트 플랜(Test Plan)
- 회귀: 핵심 기능 경로 및 PR9~PR13 핵심 시나리오 재검증
- 부하: 큐 백프레셔, API 속도, Redis/DB 부하 관찰
- 장시간: ≥24h 연속 구동, 재시작/네트워크 변동 주입
- 결과: 모든 실패 건 이슈화→수정→재검증 사이클 완료

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 03:40 | 장시간 구동 중 메모리 상승 | 캐시 미해제 | 주기적 캐시 정리 추가 | longrun_memory_guard

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json(필수), 부하/장시간 로그 별도 보관
- DB 스냅샷(결정/거래/리스크 이벤트) 및 비교 리포트

## 배포/롤백(Release/Rollback)
- 배포: 테스트 전용 프로파일→스테이징→프로덕션 순
- 롤백: 마지막 안정 태그로 즉시 회귀, 변경점 diff 남김

## 리스크/완화(Risks & Mitigations)
- 잔여 중복/하드코딩 발견 → 즉시 제거 및 테스트 확장
- 장시간 테스트 중 리소스 고갈 → 모니터링/알림 임계치 조정, 샘플링 로그

## 릴리즈 노트(Release Notes)
- 상용 검증 완료. 무중복/고커버리지/안정성 기준 만족 확인.
