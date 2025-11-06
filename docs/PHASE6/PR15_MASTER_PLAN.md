# PHASE6 — PR15 마스터 플랜: UI/UX 통합 · 메시징/로깅 표준화 · 대시보드/관측성

## 배경/의도(Overview)
운영 단계에서 사용성과 관측성을 상용 수준으로 끌어올리기 위해, 텔레그램 메시징/로깅 포맷을 표준화하고, 엔진/브로커/리스크/포트폴리오 이벤트를 일관된 UX로 노출합니다. 또한 최소 대시보드와 메트릭을 정돈하여 24시간 운영 중 이상 징후를 즉시 감지할 수 있게 합니다. FlowGuardian READY 게이트는 항상 유지합니다.

## 목표(Goals)
- 텔레그램/로그 메시지의 단일 포맷(한 줄, 이모지/아이콘 표준, 필드 순서 고정)
- 하이브리드 TP/SL(Option C) 흐름을 반영한 이벤트 체계(진입/SL등록/SL갱신/TP/청산)
- 관측성 최소 세트(성능/지연/연결/리스크/포트폴리오 지표) 통일 노출
- 일/주간 리포트 자동화 및 가독성 개선(요약지표/변화 탐지 중심)
- 설정 단일 소스(config.yml) 기반 UX 토글/이모지/빈도 제어

## 범위(Scope, In)
- common/messaging.py: 메시지 포맷 표준화(단일 라인, config 기반 이모지/라벨)
- common/logger.py: 구조화/컴팩트 포맷 선택 지원(콘솔/파일/JSON)
- monitoring/performance_monitor.py: 핵심 메트릭(지연/리소스/WS상태) 표준 키 정리
- monitoring/telemetry_profiler.py: 주요 구간(신호/주문/청산) 프로파일 태그 표준화
- analytics/report_generator.py: 일/주간 리포트 템플릿 정비(요약 + 변화 포인트)
- execution/engine.py: 메시징 훅 연결 지점 정돈(진입/SL등록/SL갱신/TP/청산/하트비트)
- config.yml: messaging.*, logging.*, reporting.*, dashboard.* 키 추가/정리(중복/하드코딩 제거)
- 문서: 사용 가이드/수용 기준/테스트 플랜 동기화

## 제외(Out-of-Scope)
- 전략 로직/리스크 가드 알고리즘 변경(PR11)
- 거래소 스펙/반올림/펀딩 로직(PR12)
- 튜닝/롤아웃 파이프라인(PR13)

## 영향 파일(예상)
- common/messaging.py, common/logger.py
- monitoring/performance_monitor.py, monitoring/telemetry_profiler.py
- analytics/report_generator.py
- execution/engine.py(훅만, 로직 변경 없음)
- config.yml(messaging.*, logging.*, reporting.*, dashboard.*)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(PR15 섹션 추가)

## 설정 키(제안)
- messaging.enabled: bool
- messaging.telegram.enabled: bool
- messaging.format.single_line: bool  # 기본 true, 개행 금지
- messaging.emoji.use_config: bool    # config 이모지 맵 사용
- messaging.emoji.map: dict           # 전략/이벤트별 이모지 매핑
- logging.format: ["compact", "json", "console"]
- logging.level: ["INFO", "DEBUG", "WARNING", "ERROR"]
- reporting.daily.enabled: bool
- reporting.weekly.enabled: bool
- reporting.timezone: "Asia/Seoul"
- reporting.schedule.daily_hhmm: "23:59"
- dashboard.enabled: bool             # 최소 지표 파일/콘솔 노출
- observability.metrics.export: ["file", "console"]  # 외부 시스템 연동은 보류

## FlowGuardian 게이트
- READY 플래그 없이는 PAPER/LIVE 실행 불가(게이트 준수)

## 수용 기준(Acceptance)
- 텔레그램/로그 모든 메시지 단일 라인(개행 없음), 표준 이모지/라벨 적용
- 하트비트 10분 주기 전달, 연결/리스크/노출/성능 경보 정상
- 24시간 관찰 중 포맷 일관성 위반 0회, 누락/중복 알림 0회
- logs/trial_0000.json 생성 보장, PR 섹션 메트릭 기록
- pre-commit(ruff/black/mypy/vulture), coverage > 85% 통과
- tests/flow/test_flow_guardian.py 통과(게이트 확인)

## 체크리스트(Checklist)
- [ ] 메시지 포맷 표준(단일 라인/필드 순서/이모지 맵)
- [ ] 엔진 훅 연결(진입/SL등록/SL갱신/TP/청산/하트비트)
- [ ] 관측성 지표 최소 세트 노출(성능/연결/리스크/포트폴리오)
- [ ] 일/주간 리포트 템플릿 개선 및 스케줄 적용
- [ ] config.yml 키 추가/정리 및 하드코딩 제거
- [ ] 통합 테스트/수용 기준 검증(24h 관찰 포함)

## 테스트 플랜(Test Plan)
- 유닛: 포맷터(이모지/단일 라인/필드 순서), config 토글 반영
- 통합: 엔진 루프 6시간/24시간 관찰(하트비트/연결/리스크/성능 알림)
- 회귀: PR9 로그/멱등/쿨다운 포맷 유지, PR10 하이브리드 SL 이벤트 누락 없음
- 계약: logs/trial_0000.json, DB score_total == JSON score_total 확인

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 23:40 | 텔레그램 다중 라인 전송 | 포맷터 개행 포함 | 단일 라인 포맷터 적용, 테스트 추가 | test: messaging_single_line

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 실행/알림/지표 요약 포함
- logs/uiux_*.log: 메시지 포맷 점검 로그(선택)
- DB(있다면): 알림/이벤트 테이블과의 정합성 확인(선택)

## 배포/롤백(Release/Rollback)
- 점진적 적용: 로컬 → 페이퍼 → 부분 라이브 → 전체
- 이상 시 messaging.enabled/logging.format 토글로 즉시 롤백

## 리스크/완화(Risks & Mitigations)
- 과도한 알림/로그 스팸 → 샘플링/쿨다운/중복 억제 규칙 유지(PR9 연계)
- 포맷 변경으로 외부 파서 영향 → 버전 태그/마이그레이션 가이드 제공
- 운영 리소스 증가 → 모니터링 임계/샘플링 비율 설정

## 릴리즈 노트(Release Notes)
- UI/UX 통합(메시징/로깅/대시보드 최소치)으로 운영 가시성 개선. 전략/리스크/브로커 로직 변경 없음.
