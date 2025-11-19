# PHASE18 INFRA Hardening Plan

**시작일**: 2025-11-19  
**진입 조건**: PHASE17 V6.1 완료 (Production Ready)  
**목표**: INFRA 전역 진단 및 하드닝  
**원칙**: 코어 엔진 DO-NOT-TOUCH, INFRA 레이어만 개선

---

## 1. Objective

### 1.1 핵심 목표

**"엔진이 안정적으로 돌아가는 것"에서 한 단계 더 나아가,  
"운영 환경에서 예측 가능하고 관리 가능한 방식으로 돌아가는 것"을 보장한다.**

### 1.2 PHASE17 경험에서 얻은 교훈

| Pain Point | 문제 | 해결 방향 |
|-----------|------|----------|
| **세션 외부 종료** | 12H 테스트 10H 종료 (로컬 PC 세션 끊김) | 프로세스 감시, graceful shutdown |
| **상태 초기화 불명확** | Redis/DB 이전 실행 잔여 상태 간섭 가능성 | 표준 초기화 스크립트, run_id 네임스페이스 |
| **모니터링 임시 구현** | 테스트마다 새 모니터링 스크립트 작성 | 범용 모니터링 프레임워크 |
| **Config/CLI 불일치** | duration_mode 혼란 (1H 종료) | 실행 전 검증 레이어 |
| **로그 정책 불명확** | Telegram 404 오류 103건 혼재 | 로그 카테고리 분리, 알람 정책 |

---

## 2. Scope

### 2.1 In-Scope

✅ 실행/프로세스 관리 표준화  
✅ 환경 초기화 규칙 정립  
✅ 모니터링/로그/알람 정책  
✅ Docker/운영 구조 문서화  
✅ Guard 동작 확인 및 문서화

### 2.2 Out-of-Scope

❌ 전략 로직 변경 (scalping, ensemble 등)  
❌ Portfolio/Risk 알고리즘 변경 (V6.1 유지)  
❌ 새로운 전략 추가 (PHASE19 이후)  
❌ 튜닝/최적화 (Budget allocation 등)  
❌ Live 모드 구현 (PHASE24+)

---

## 3. Work Items (D-Tasks)

### PHASE18-D50: 실행 전 환경 초기화 표준 스크립트

**파일**: `scripts/ops/init_clean_state.py` (신규)

**내용**:
- Redis 초기화 (Guard/쿨다운/dedup 키)
- DB 초기화 옵션 (run_id 기반 포지션/트레이드)
- 로그 백업 (application.log → .bak)
- `--clean-state` 플래그로 자동 실행

**Acceptance**:
- [ ] 초기화 스크립트 실행 성공
- [ ] run_paper.py/run_backtest.py에 통합
- [ ] 초기화 전/후 상태 로그 출력

**우선순위**: P0 (필수)

---

### PHASE18-D51: run_id 네임스페이스 전역 적용

**파일**: `execution/risk_manager.py`, `database/postgres.py`

**내용**:
- Redis 키 네임스페이스: `flow_guard:{run_id}:{symbol}`
- DB run_id 필드 인덱스 추가
- 로그 파일 분리 (optional)

**Acceptance**:
- [ ] 동시 2개 run_id 실행 시 충돌 없음
- [ ] 네임스페이스 설계 문서 작성

**우선순위**: P0 (필수)

---

### PHASE18-D52: 종료 시그널 핸들링

**파일**: `execution/engine.py` (수정)

**내용**:
- SIGTERM/SIGINT 핸들러 등록
- Graceful shutdown (상태 스냅샷 저장)
- 종료 사유 로그 출력

**Acceptance**:
- [ ] SIGTERM 시 "Graceful shutdown" 로그
- [ ] shutdown_snapshot.json 저장
- [ ] 재시작 시 스냅샷 복구 가능 (optional)

**우선순위**: P1 (중요)

---

### PHASE18-D53: 범용 모니터링 프레임워크

**파일**: `monitoring/monitor_framework.py` (신규)

**내용**:
- 로그 실시간 파싱 엔진
- 메트릭 수집 (Equity/PnL/Guard 통계)
- 체크포인트 JSON 자동 생성

**Acceptance**:
- [ ] 실시간 모니터링 스크립트 실행
- [ ] checkpoints_{run_id}.json 생성
- [ ] 기존 monitor_12h_acceptance.py 대체

**우선순위**: P1 (중요)

---

### PHASE18-D54: Config/CLI 일관성 검증

**파일**: `common/config_validator.py` (신규)

**내용**:
- Pre-flight check (Config vs CLI 불일치 감지)
- effective_config.yml 미리 출력
- Critical 파라미터 검증 (duration_mode 등)

**Acceptance**:
- [ ] 불일치 시 경고 출력
- [ ] effective_config 실행 전 생성
- [ ] 검증 실패 시 중단 옵션

**우선순위**: P1 (중요)

---

### PHASE18-D55: 로그 카테고리 표준화

**파일**: `common/logger.py` (수정)

**내용**:
- 로그 분리: application.log / trading.log / external.log
- 로그 레벨 정책 (ERROR=시스템만, CRITICAL=엔진 중단)
- 로그 포맷 표준화

**Acceptance**:
- [ ] Telegram 오류 → external.log 분리
- [ ] application.log에 시스템 에러만
- [ ] LOGGING_POLICY.md 문서 작성

**우선순위**: P1 (중요)

---

### PHASE18-D56: Telegram 알람 정책

**파일**: `monitoring/telegram_notifier.py` (refactor)

**내용**:
- 알람 트리거 정의 (CRITICAL만 알림)
- Telegram 오류 재시도 로직
- 알람 정책 문서

**Acceptance**:
- [ ] CRITICAL만 Telegram 알림
- [ ] Guard BLOCK 시 알림 안 감
- [ ] ALARM_POLICY.md 문서 작성

**우선순위**: P2 (권장)

---

### PHASE18-D57: Docker 운영 가이드

**파일**: `docs/PHASE18/DOCKER_OPERATIONS_GUIDE.md` (신규)

**내용**:
- Docker Compose 관리 가이드
- 실행 체크리스트
- 트러블슈팅

**Acceptance**:
- [ ] 신규 사용자가 가이드만으로 실행 가능
- [ ] 문서 작성 완료

**우선순위**: P1 (중요)

---

### PHASE18-D58: K8s 대응 설계 초안 (Optional)

**파일**: `docs/PHASE18/K8S_MIGRATION_DESIGN.md` (신규)

**내용**:
- K8s 요구사항 정의
- 마이그레이션 단계
- 설계 초안

**우선순위**: P3 (미래 대비)

---

### PHASE18-D59: Guard 동작 문서화

**파일**: `docs/PHASE18/GUARD_BEHAVIOR_SPEC.md` (신규)

**내용**:
- 각 Guard 트리거/해제 조건
- 메트릭 수집 구조
- 테스트 시나리오

**우선순위**: P2 (권장)

---

## 4. Exit Criteria

### 4.1 필수 조건 (Must Have)

- [ ] D50: 환경 초기화 스크립트 완료
- [ ] D51: run_id 네임스페이스 적용 완료
- [ ] D52: 종료 시그널 핸들링 완료
- [ ] D53: 모니터링 프레임워크 완료
- [ ] D54: Config/CLI 검증 완료
- [ ] D55: 로그 카테고리 분리 완료
- [ ] D57: Docker 운영 가이드 완료

### 4.2 검증 조건

- [ ] **6H REAL PAPER 실행 성공** (clean-state로 시작)
- [ ] **외부 종료 시 graceful shutdown 확인**
- [ ] **모니터링 프레임워크로 체크포인트 수집**
- [ ] **로그 분석 시 시스템/외부 에러 명확히 구분**

### 4.3 문서화

- [ ] PHASE18_EXECUTION_SUMMARY.md (6H 테스트 결과)
- [ ] PHASE18_INFRA_FINAL_REPORT.md (최종 리포트)
- [ ] NAMESPACE_DESIGN.md
- [ ] LOGGING_POLICY.md
- [ ] DOCKER_OPERATIONS_GUIDE.md

---

## 5. Risks & Mitigations

| 리스크 | 완화 전략 | 우선순위 |
|--------|----------|----------|
| 초기화로 인한 데이터 손실 | 백업 자동 생성, run_id 기반 제한 | P0 |
| 모니터링 성능 오버헤드 | 비동기 파싱, 주기 조절 | P1 |
| 검증 로직 복잡도 증가 | YAML 선언적 정의, critical만 체크 | P1 |
| 네임스페이스 호환성 문제 | 하위 호환성 유지, 점진적 마이그레이션 | P0 |

---

## 6. Timeline (예상)

| 단계 | 작업 | 예상 소요 | 완료 조건 |
|------|------|----------|----------|
| **Week 1** | D50-D52 | 3-5일 | 환경 초기화 + 종료 핸들링 |
| **Week 2** | D53-D55 | 3-5일 | 모니터링 + 로그 표준화 |
| **Week 3** | D56-D57 + 검증 | 3-5일 | 알람 정책 + 6H 테스트 |
| **Week 4** | 문서화 + 리포트 | 2-3일 | PHASE18 완료 |

**총 예상**: 2-4주

---

## 7. PHASE19 진입 조건

PHASE18 완료 후, 다음 조건 만족 시 PHASE19 진입:

✅ PHASE18 Exit Criteria 모두 만족  
✅ 6H REAL PAPER 안정 실행 확인  
✅ INFRA 문서 5개 이상 작성 완료  
✅ 코어 엔진 DO-NOT-TOUCH 원칙 유지 확인

**PHASE19 Focus**: 앙상블 프레임워크 복구 및 정리

---

**문서 작성**: 2025-11-19  
**작성자**: Cascade AI  
**승인**: PHASE18 계획 초안
