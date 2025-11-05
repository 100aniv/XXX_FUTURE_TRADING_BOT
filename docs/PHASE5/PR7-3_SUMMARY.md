         # PR7-3: Docs-Only — Observability & Paper E2E

상태: ✅ 승인 (문서만 갱신, 코드 변경 없음)
작성일: 2025-11-03 23:35

---

## 목적
- 운영 관측성 패턴을 표준화하고, 페이퍼 모드 End-to-End(E2E) 테스트 절차/수용 기준을 문서화
- Option A 유지: 1m base feed → 엔진 리샘플(3m/5m/15m/1h/4h)
- Redis dedup 유지(재시작/분산 안전성) 및 환경변수 매핑 명확화

## 범위 (Docs Only)
- INTEGRATION_TEST.md: Phase 7.3 Paper E2E 시나리오/수용 기준 추가
- REFACTORING_database_v1.md: Redis 환경변수 매핑, TimescaleDB 도입 판단(보류) 명시
- REFACTORING_collector_v1.md: 관측 로그 패턴(닫힘 감지/큐 적재/백필/Redis 연결) 추가, 운영 체크리스트 보강
- PR7_COMPLETE.md: PR7-3 범위와 문서 업데이트 레퍼런스 추가

## 비범위 (Non-Goals)
- 코드 변경 없음 (엔진/전략/브로커/스토리지)
- TimescaleDB 도입 및 마이그레이션 (추후 별도 PR에서 검토)
- 이벤트 버스(Pub/Sub) 도입

## 수용 기준

### 문서 업데이트 (Docs-only)
- [x] INTEGRATION_TEST.md: Phase 7.3 Paper E2E 섹션 추가
- [x] REFACTORING_database_v1.md: PR7-3 Redis 매핑/TimescaleDB 판단 추가
- [x] REFACTORING_collector_v1.md: PR7-3 운영 관측 패턴 추가
- [x] PR7_COMPLETE.md: PR7-3 범위 섹션 추가
- [x] PR7-3_SUMMARY.md: 요약 문서 생성

### 운영 검증 (PR7-2 완료 후)
- [ ] Redis 연결 성공 로그 확인
- [ ] 닫힌 캔들 큐 적재 로그 반복 확인
- [ ] monitoring.signals 다중 TF 레코드 존재 (3m/5m/15m/1h/4h 중 ≥1)
- [ ] trading.decisions 생성 ≥1건

## 근거/결정
- TimescaleDB: 현재 규모(Postgres + 인덱스)로 충분, 보존/압축/다운샘플링·대량 리포팅 니즈 증가 시 별도 PR로 검토
- 신호·결정 분리 저장: 이미 충족(signals/decisions). 체결 품질 분석 고도화 필요 시 orders/fills 추가는 후속 검토

## 다음 단계(운영 절차)
- 1.5시간 데이터 축적 후: signals(3m/5m/15m/1h/4h) 생성 확인 → decisions ≥1 확인 → 문서 최종 업데이트

---

## 링크
- PR7_COMPLETE.md — PR7-3 섹션
- INTEGRATION_TEST.md — Phase 7.3 Paper E2E
- REFACTORING_database_v1.md — Redis 매핑/Timescale 판단
- REFACTORING_collector_v1.md — 관측 로그 패턴
