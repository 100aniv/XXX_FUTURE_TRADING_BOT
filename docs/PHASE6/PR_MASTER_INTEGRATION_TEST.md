# PHASE6 — PR 마스터 통합 테스트

## 전역 사전조건(Global Preconditions)
- FlowGuardian READY 게이트 활성(READY 없이는 PAPER/LIVE 불가)
- 설정 단일 소스: config.yml
- logs/trial_0000.json 기록 활성화, DB score_total == JSON score_total
- pre-commit: ruff, black, mypy, vulture 통과
- **coverage ≥90% (PR14에서 달성)**

---

## PR8 — 정합화 & 소형 패치
- PositionSizer `self.config` 패치 검증: liquidation/epsilon 경로 호출 시 정상 동작
- flow_guardian 섹션 단일화 확인: enabled: true 및 정책 키 존재
- Paper 10분 스모크: 쿨다운/epsilon/DB 쓰기 정상
- 산출물: logs/trial_0000.json 존재, DB 동등성 OK

---

## PR9 — 신호 무결성 & Redis 통합
### 로그 패턴
- "⏭️ 중복 캔들 무시"
- "🔒 {strategy} {symbol} 쿨다운 중"
- "🧩 신호 멱등 hit: signal:{symbol}:{hash}"

### 절차
1) 동일 캔들 2회 주입 → 2번째는 skip(dedup 로그 확인)
2) Risk/Portfolio 거부 1회 유도 → `cooldown:{symbol}_{strategy}` TTL 생성 확인
3) 프로세스 재시작 → 동일 거래 시도 → 쿨다운 유지 확인
4) 동일 파라미터 신호 2회 발행 → 멱등 hit로 중복 차단

### 수용 기준
- 재시작/재생 후 중복 처리 0건
 - 쿨다운 TTL 재시작 전후 잔여 TTL 편차 ≤ 2초
 - 멱등 키 TTL = monitoring.redis.ttl_seconds 내 중복 신호 100% 차단
- READY 유지, logs/trial_0000.json 존재, DB=JSON
- pre-commit/coverage 기준 충족

---

## PR10 — 앙상블 고급화 + Experience Score + 베이시안 튜닝(설계)
### 절차
1) 현행 앙상블 설정으로 N시간 페이퍼 baseline 수집
2) 튜닝 설계 산출(목표/파라미터/오버레이 구조/가드레일 정의)
3) A/B 비교 계획 수립(적용은 PR13에서 실시)

### 수용 기준
- 개선 설계 문서화 완료(가중/보너스/경계/로그)
- Experience Score 로깅 경로 합의
 - DB/JSON 동등성 및 로그 영향 없음
 - 24시간 페이퍼 평가에서 baseline 대비 `score_total` ≥ 12% 향상
 - Sharpe-like(analytics.kpis) ≥ 10% 향상
 - 최대낙폭(MDD) 증가는 ≤ 1%p
 - 최소 거래수 ≥ 60, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%

---

## PR11 — 리스크 가드 + 프로퍼티 테스트
### 절차
1) DD 임계 초과 시나리오 → 주문 차단, 사유 로그
2) 슬리피지 임계 초과 → 주문 차단
3) CI(pre-commit)에서 프로퍼티 테스트 스위트 실행

### 수용 기준
- 가드가 신뢰성 있게 차단, 사유 로깅
 - 프로퍼티 테스트 통과(회귀 방지)
 - risk 모듈 커버리지 ≥ 95%

---

## PR12 — 고급 가격 레벨 + 거래소 스펙 + 운영
### 절차
1) 레짐/최근 고저 대비 고급 레벨 산출 검증
2) 거래소 스펙 기반 동적 반올림 검증
3) 펀딩 반영 계산 일관성 검증
4) 예산 배분/상관 가드 시나리오 검증
5) 운영 대시보드에서 메트릭/알림 확인

### 수용 기준
 - 반올림: price % tick_size == 0 및 qty % step_size == 0 (허용오차 ≤ 1e-9)
 - 펀딩 반영: 계산값과 DB/로그 차이 ≤ 수수료의 0.5% 또는 5e-7(둘 중 큰 값)
 - 포트폴리오 제약: 초과 시 100% 차단, 차단 사유 로깅
 - 운영 모니터링(6h): api_latency_ms_p95 ≤ 300ms, ws_last_message_ago_sec ≤ 30s, queue_drop_rate_pct ≤ 0.5%, cpu critical 경고 0회

---

## PR13 — 베이시안 운영 튜닝 & 단계적 롤아웃
### 절차
1) 페이퍼 기반 튜닝 실험 N시간(K회) 수행 → 최적 파라미터/오버레이 산출
2) 섀도우 모드 적용(실거래 미반영) → 가드레일 모니터링
3) 카나리 10% → 30% → 50% → 100% 순차 램프업(가드레일 위반 시 즉시 중단/롤백)
4) A/B 비교 리포트 생성 및 승인 후 전체 적용

### 수용 기준
 - 24시간 페이퍼 실험에서 baseline 대비 `score_total` ≥ 15% 향상
 - Sharpe-like(analytics.kpis) ≥ 12% 향상, MDD 증가는 ≤ 0.5%p
 - 최소 거래수 ≥ 80, 승률 하락 ≤ 0.5%p, 거래 수 변화 |Δ| ≤ 15%
 - 섀도우 모드: 8시간 이상 가드레일 위반 0건(DD 증가 한계, min_trades, 변동성 증가)
 - 카나리 단계: 각 단계 6시간 이상 가드레일 위반 0건 시에만 승격
 - READY/로그/DB 동등성 유지, pre-commit 통과

---

## PR14 — 코드 리팩토링 + 최종 상용 검증 + Coverage 90%

### Phase 1: 코드 리팩토링 (Coverage 90% 달성)
#### 문제점
- engine.py 거대 함수 (1358줄)
- 강한 의존성 결합 (indicators, monitoring, database 직접 import)
- 테스트 불가능한 구조

#### 리팩토링 절차
1) **engine.py 모듈 분리**:
   - `CandleProcessor`: 캔들 처리 로직 분리
   - `SignalProcessor`: 신호 생성 및 검증 분리
   - `PositionManager`: 포지션 관리 분리
   - `ExecutionLoop`: 메인 루프 제어

2) **의존성 주입 패턴 적용**:
   - 각 모듈이 인터페이스를 통해 통신
   - Mock 객체로 단위 테스트 가능하게 구조 개선

3) **단위 테스트 작성**:
   - CandleProcessor 테스트 (dedup, 버퍼 관리)
   - SignalProcessor 테스트 (신호 생성, 검증, 멱등성)
   - PositionManager 테스트 (포지션 추적, TP/SL)
   - ExecutionLoop 테스트 (메인 루프 플로우)

#### Coverage 목표
- engine 모듈: 90%+
- execution 패키지: 85%+
- core 패키지: 95%+
- **전체 프로젝트: 90%+**

### Phase 2: 아키텍처 감사
1) 모듈/함수 중복성, 하드코딩, 단일 책임 원칙 감사
2) 문서-코드-설정 동기화 점검(.windsurfrules 준수)
3) 통합/회귀/부하/장시간 안정성 테스트(재시작/네트워크 변동/백프레셔)
4) FlowGuardian 게이트/로그/DB/커버리지 최종 확인

### 수용 기준
#### Phase 1: 리팩토링
- ✅ engine.py 모듈 분리 완료 (4개 모듈)
- ✅ 의존성 주입 패턴 적용
- ✅ **Coverage 90% 달성** (engine: 90%+, execution: 85%+, core: 95%+)
- ✅ 모든 기존 테스트 통과 (회귀 없음)

#### Phase 2: 최종 검증
- 중복/하드코딩/규칙 위반 0건
- logs/trial_0000.json 생성 보장, DB=JSON
- 24h 안정성: 프로세스 크래시 0, 메모리 증가율 ≤ 3%, CPU p95 ≤ 80%
- 부하: 큐 사용률 p95 ≤ 70%, queue_drop_rate_pct ≤ 0.25%, api_latency_ms_p95 ≤ 300ms
- 재시작 내구성: 의도적 재시작 3회 동안 데이터 유실 0, 복구 ≤ 45초
- **Coverage ≥ 90% (필수)**, pre-commit 전 항목 통과

---

## 리포팅(Reporting)
- 각 PR 수용 시점의 로그/DB 스냅샷 보관
- 타임스탬프/커밋/설정 해시와 함께 pass/fail 기록

