# PHASE6 — PR12 마스터 플랜: 고급 가격 레벨 + 거래소 스펙 + 운영 견고화

## 배경/의도(Overview)
상용화 마감 단계로서, 동적 가격 레벨/거래소 스펙 반영/펀딩 연동/포트폴리오 예산·상관 제어/운영 모니터링 최소치를 구현합니다. 필요 시 출구 파라미터에 대한 튜닝 확장 가능성은 명시하되 실제 운영 튜닝은 PR13에서 수행합니다.

## 목표(Goals)
 - TP/SL 레벨의 고급화(price_levels_advanced)
 - 거래소 tick_size/step_size 기반 동적 반올림
 - funding_rate 연동(적용 지점에 한해)
 - 전략별 예산 배분 및 상관(상관관계) 가드
 - 운영 최소 대시보드/메트릭/알림
 - Bug #8: 구조적 완화로 실현 승률/체결률 개선(A/B 측정)

## 범위(Scope, In)
 - TPManager: 레짐 인지 S/R, 최근 고저가 반영
 - 동적 반올림: 거래소 tick/step 규격 준수
 - Funding: 수수료/캐리 계산에 반영되는 경우 연동
 - 포트폴리오: 전략별 예산 배분 훅, 상관 가드
 - 운영: 메트릭 표출, 최소 대시보드, A/B 비교 하니스
 - Bug #8 KPI 관찰: TP hit rate/평균 보유시간/주문 거절률(반올림 위반) 지표화

## 제외(Out-of-Scope)
- 앙상블/튜닝 내부 설계(→ PR10)
- 리스크 가드 재설계(→ PR11)

## 영향 파일(예상)
- **⭐ execution/tp_manager.py**: TP/SL 고급 레벨 계산 (PR10 연계)
- **⭐ common/calculations.py**: 반올림/펀딩 계산
- **⭐ execution/adapters/exchange_specs.py**: 거래소 스펙 조회 (신규)
- **⭐ execution/adapters/brokers.py**: Paper/Live Broker 파리티 보장
- 포트폴리오 관리 모듈(예산/상관 훅)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md
- **⭐ docs/PHASE6/PR12_BINANCE_PARITY_CHECK.md**: 바이낸스 API 파리티 검증 (신규)
- config.yml(exits.*, exchange.*, portfolio.*)

## 설정 키(제안)
- exits.price_levels.advanced.enabled: bool
- exchange.specs.dynamic_rounding: bool
- exchange.funding.enabled: bool
- portfolio.budget_per_strategy: dict
- portfolio.correlation.max_pair_corr: float

## FlowGuardian 게이트
- READY 없이는 PAPER/LIVE 불가(게이트 준수)

## 수용 기준(Acceptance)

### PR12 기능 수용 기준
 - 가격 반올림: price % tick_size == 0 및 qty % step_size == 0 (허용오차 ≤ 1e-9)
 - 펀딩 반영: 계산값과 DB/로그 차이 ≤ 수수료의 0.5% 또는 5e-7(둘 중 큰 값)
 - 예산/상관 가드: 초과 시 100% 차단, 차단 사유 로깅
 - 운영 모니터링: 6시간 관찰 동안
   - api_latency_ms_p95 ≤ 300(ms)
   - ws_last_message_ago_sec ≤ 30(s)
   - queue_drop_rate_pct ≤ 0.5%
   - cpu_pct_critical 경고 0회
 - A/B 관찰: TP hit rate 비열화 없음(↑ 기대), 주문 거절률↓ 또는 동등, 평균 보유시간 악화 없음
 - pre-commit 통과, coverage>85%

### 바이낸스 API 파리티 수용 기준 (PR10/PR11 연계)
 - **⭐ Paper/Live 로직 100% 동일**: TP/SL 계산, 반올림, 펀딩, 포트폴리오 가드
 - **⭐ Broker 계층 분리**: 주문 실행만 Paper(가상) vs Live(실제)로 분리
 - **⭐ exchangeInfo API**: Paper/Live 모두 실제 바이낸스 API 조회 (읽기 전용)
 - **⭐ fundingRate API**: Paper/Live 모두 실제 바이낸스 API 조회 (읽기 전용)
 - **⭐ PR10 호환**: workingType/priceProtect 파라미터와 충돌 없음
 - **⭐ PR11 호환**: 리스크 가드와 독립적/보완적 동작
 - **⭐ config.yml 단일 소스**: 모든 설정값 config에서 로드, 하드코딩 제거

## 체크리스트(Checklist)

### Phase 1: 고급 가격 레벨 및 거래소 스펙
 - [ ] **⭐ TP/SL 고급 레벨 구현** (tp_manager.py)
   - [ ] 레짐 인지 S/R 반영
   - [ ] 최근 고저가 동적 반영
   - [ ] PR10 workingType/priceProtect 호환성 검증
 - [ ] **⭐ 동적 반올림 구현** (calculations.py, exchange_specs.py)
   - [ ] exchangeInfo API 조회 (Paper/Live 공통)
   - [ ] tick_size 반올림 로직
   - [ ] step_size 반올림 로직
   - [ ] 캐시/폴백 메커니즘
 - [ ] **⭐ 펀딩 연동** (calculations.py)
   - [ ] fundingRate API 조회 (Paper/Live 공통)
   - [ ] 펀딩 비용 계산 수식
   - [ ] DB 저장 및 로깅

### Phase 2: 포트폴리오 가드 및 운영 모니터링
 - [ ] **⭐ 포트폴리오 가드**
   - [ ] 전략별 예산 배분 훅
   - [ ] 심볼 간 상관관계 가드
   - [ ] PR11 리스크 가드와 독립성 검증
 - [ ] **⭐ 운영 모니터링**
   - [ ] 메트릭 표출 (API 지연, WS 상태, 큐 사용률)
   - [ ] 최소 대시보드
   - [ ] A/B 비교 하니스

### Phase 3: 바이낸스 API 파리티 검증
 - [ ] **⭐ Paper/Live 파리티 체크**
   - [ ] TP/SL 계산 로직 100% 동일 검증
   - [ ] 반올림 규칙 100% 동일 검증
   - [ ] 펀딩 계산 100% 동일 검증
   - [ ] Broker 계층 분리 확인
 - [ ] **⭐ PR10/PR11 호환성 검증**
   - [ ] PR10 바이낸스 파라미터 충돌 없음
   - [ ] PR11 리스크 가드 상호작용 확인
   - [ ] config.yml 단일 소스 원칙 준수
 - [ ] **⭐ Bug #8 개선 검증**
   - [ ] A/B 하니스 연결
   - [ ] TP hit rate 관찰
   - [ ] 주문 거절률 관찰
   - [ ] KPI 대시보드 노출

## 테스트 플랜(Test Plan)

### 유닛 테스트
- 반올림 정확도: `price % tick_size == 0`, `qty % step_size == 0`
- TP/SL 레벨 산출: 레짐/고저가 반영 로직
- 펀딩 수식: `funding_cost = position_value × funding_rate × interval`
- 포트폴리오 가드: 예산/상관 임계값 체크

### 통합 테스트
- 실시간 거래소 스펙 조회: exchangeInfo API (Paper/Live 공통)
- 포트폴리오 제약 검사: 전략별 예산/상관 가드 동작
- PR10 호환성: workingType/priceProtect와 충돌 없음
- PR11 호환성: 리스크 가드 상호작용 정상

### Paper/Live 파리티 테스트
- **Paper 2-3시간 테스트**:
  - TP/SL 계산 로직 검증
  - 반올림 규칙 100% 준수 확인 (주문 거절 0건)
  - 펀딩 비용 정확도 검증
  - 포트폴리오 가드 동작 확인
- **Live 소액 테스트**:
  - Paper와 동일한 로직 동작 확인
  - 실제 주문 체결 및 반올림 검증
  - 코드 변경 없이 Paper → Live 전환

### A/B 비교 테스트
- 고급 레벨 적용 전/후 Paper 모드 비교
- 관찰 지표:
  - TP hit rate 개선 여부
  - 평균 보유시간 변화
  - 주문 거절률 감소 (목표: 0건)

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 02:30 | 주문 거절(틱 불일치) | 반올림 순서 오류 | tick→step 순서로 재정렬 | unit: rounding_tick_step_order

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 출구/펀딩/라운딩 관련 메타
- DB: 결정/거래 기록과 스펙 준수 여부 점검

## 배포/롤백(Release/Rollback)
- 스펙 캐시/폴백 경로 제공(네트워크 변동성 대비)
- 문제 시 새 키 비활성화 후 기본 출구 로직으로 복귀

## 리스크/완화(Risks & Mitigations)
- 거래소 API 변동성 → 캐시/폴백/리트라이 전략
- 계산 복잡도 증가 → 프로파일링 및 임계경고

## 비고(Notes)
- 출구 파라미터 튜닝 확장은 가능하나 운영 반영은 PR13에서 안전 게이트와 함께 수행

## Bug #8 처리 계획 (승률 6.65% 개선)
### 개요
- 본 PR12는 전략 로직을 변경하지 않고도 승률 저하를 완화할 수 있는 출구/거래소/포트폴리오 측면 개선을 제공합니다.
- 전략 신호 품질/임계값 튜닝(엔트리 필터)은 PR13(튜닝/롤아웃)에서 수행합니다.

### 범위 정렬(Scope Alignment)
- TP/SL 고급 레벨(price_levels_advanced): 레짐 인지/최근 고저가 반영으로 TP 도달 확률(체결 가능성) 개선
- 거래소 스펙 반영: tick_size/step_size 반올림 정확도 → 주문 거절/미체결 감소로 실현 승률에 기여
- 포트폴리오 가드: 전략별 예산·상관 가드로 과잉 익스포저/동일 방향 몰림을 억제
- 운영 메트릭: TP hit rate, 평균 홀드 시간, partial exit 분포를 대시보드로 관찰

### 비범위(Out-of-Scope)
- 전략 신호 생성 로직 자체 변경(전략 필터/휴리스틱 수정) → 별도 PR
- 신뢰도 임계값(ensemble.min_confidence) 조정 → PR13에서 오버레이/튜닝으로 처리

### 테스트/수용 보완(추가 관찰 지표)
- A/B 비교(고급 레벨 적용 전/후)에서 다음 지표 관찰 및 리포트:
  - TP hit rate 증가(± 통계 유의성 주석)
  - 평균 보유시간 감소 또는 동일 수준 유지
  - 주문 거절률/반올림 위반 0건(수용 기준과 일치)

### 문서/연계
- PR13과 연계: PR13에서 `ensemble.min_confidence`/`portfolio.budget_per_strategy` 등 파라미터 튜닝
- PR10/PR11과 충돌 없음(전략 로직/리스크 가드 불변)
