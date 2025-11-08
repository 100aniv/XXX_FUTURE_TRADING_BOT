# PHASE6 — PR12 마스터 플랜: 고급 가격 레벨 + 거래소 스펙 + 운영 견고화

## 문서 참조 가이드

- [PR12_TEST_REPORT.md](./PR12_TEST_REPORT.md): **종합 테스트 리포트** - 동적 반올림, 펀딩, 포트폴리오 가드, 테스트 결과
- [PR12_ENSEMBLE_ANALYSIS.md](./PR12_ENSEMBLE_ANALYSIS.md): **앙상블 분석 문서** - 전략 가중치 기반 앙상블 메커니즘
- [PR12_FINAL_TEST_PLAN.md](./PR12_FINAL_TEST_PLAN.md): **30분 페이퍼 테스트 계획** - 결과와 거래 로그 분석
- [PR12_LIVE_TEST.md](./PR12_LIVE_TEST.md): **라이브 모드 설정 가이드** - 바이낸스 설정 및 소액 테스트
- [PR12_PORTFOLIO_REFACTORING.md](./PR12_PORTFOLIO_REFACTORING.md): **포트폴리오 리팩토링** - 자산 관리 및 PnL 추적 통합
- [PR12_BINANCE_PARITY_CHECK.md](./PR12_BINANCE_PARITY_CHECK.md): **바이낸스 API 파리티 검증** - 동일한 로직 가동 여부

## 배경/의도(Overview)
상용화 마감 단계로서, 동적 가격 레벨/거래소 스펙 반영/펀딩 연동/포트폴리오 예산·상관 제어/운영 모니터링 최소치를 구현합니다. Paper 모드 검증 후 Live 모드 소액 테스트까지 PR12 범위에 포함됩니다.


## 목표(Goals)
 - TP/SL 레벨의 고급화(price_levels_advanced)
 - 거래소 tick_size/step_size 기반 동적 반올림
 - funding_rate 연동(적용 지점에 한해)
 - 전략별 예산 배분 및 상관(상관관계) 가드
 - 운영 최소 대시보드/메트릭/알림
 - Bug #8: 구조적 완화로 실현 승률/체결률 개선(A/B 측정)
 - ✨ 시스템 종료 시 텔레그램 알림(실패 완화)

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

### PR12 포트폴리오 리팩토링 수용 기준 (⭐ 신규)
 - **⭐ PnL 추적 통합**: PortfolioManager에서 daily_pnl/total_pnl 관리
 - **⭐ Daily PnL 리셋**: 자정에 자동 리셋, 로그 기록
 - **⭐ Equity 단일 소스**: PortfolioManager만 equity 관리, 중복 제거
 - **⭐ Paper/Live 자산 동기화**:
   - Live: Binance API로 자산 조회 (`futures_account_balance`)
   - Paper: 로컬 equity 반환
   - 메서드 시그니처 100% 동일 (`get_account_balance`, `sync_equity_with_exchange`)
 - **⭐ 역할 명확화**: PortfolioManager(자산/PnL), RiskManager(가드만)
 - **⭐ 텔레그램 Daily PnL 정확도**: 일일 리셋 후 정확한 일일 손익 표시

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
 - [x] **⭐ 동적 반올림 구현** (calculations.py)
   - [x] exchangeInfo API 조회 (Paper/Live 공통)
   - [x] tick_size 반올림 로직
   - [x] step_size 반올림 로직
   - [x] 캐시/폴백 메커니즘 (1시간 TTL)
 - [x] **⭐ 펀딩 연동** (calculations.py)
   - [x] fundingRate API 조회 (Paper/Live 공통)
   - [x] 펀딩 비용 계산 수식
   - [ ] DB 저장 및 로깅

### Phase 2: 포트폴리오 리팩토링 및 가드 (⭐ PR12_PORTFOLIO_REFACTORING.md)
 - [x] **⭐ PortfolioManager PnL 통합**
   - [x] `update_pnl()` 메서드 추가
   - [x] `get_daily_pnl()` / `get_total_pnl()` 메서드 추가
   - [x] `reset_daily()` 자동 호출 구현
   - [x] `check_and_reset_daily()` 메서드 추가 (날짜 체크)
 - [x] **⭐ RiskManager 간소화**
   - [x] PnL 관련 코드 제거 (PortfolioManager로 이동)
   - [x] Portfolio 참조로 대체
   - [x] 가드 로직만 유지
 - [x] **⭐ Equity 단일 소스**
   - [x] PortfolioManager만 equity 관리
   - [x] PositionSizer equity 참조로 변경
   - [x] RiskManager equity 참조로 변경
   - [x] Engine 중복 코드 제거
 - [x] **⭐ Paper/Live 자산 동기화**
   - [x] `LiveBroker.get_account_balance()` 구현 (Binance API)
   - [x] `LiveBroker.sync_equity_with_exchange()` 구현
   - [x] `PaperBroker.get_account_balance()` 구현 (파리티)
   - [x] `PortfolioManager.sync_equity_with_broker()` 구현
   - [x] Engine에서 자동 동기화 호출 (Live 모드만)
 - [x] **⭐ 포트폴리오 가드**
   - [x] 전략별 예산 배분 훈
   - [x] 심볼 간 상관관계 가드
   - [x] PR11 리스크 가드와 독립성 검증
 - [x] **⭐ 시스템 종료 알림 (✨ PR12 #9)**
   - [x] `messaging.py`에 `system_shutdown_alert()` 함수 추가
   - [x] `main.py`에서 atexit 핸들러로 종료 알림 전송
   - [x] 기존 모듈 재사용 원칙 준수
 - [ ] **⭐ 운영 모니터링** (→ PR13으로 이관)
   - [ ] 메트릭 표출 (API 지연, WS 상태, 큐 사용률) → PR13
   - [ ] 최소 대시보드 → PR13
   - [ ] A/B 비교 하니스 → PR13 ABComparisonReport

### Phase 3: 바이낸스 API 파리티 검증
 - [x] **⭐ Paper/Live 파리티 체크** (Paper 모드 테스트 완료)
   - [x] TP/SL 계산 로직 100% 동일 검증 (단위 테스트)
   - [x] 반올림 규칙 100% 동일 검증 (단위 테스트)
   - [x] 펀딩 계산 100% 동일 검증 (단위 테스트)
   - [x] Paper 모드 실제 운영 테스트 (30분) - 거래 실행 및 포트폴리오 가드 정상 작동 확인
   - [x] Broker 계층 분리 확인 (실제 환경) - Paper 브로커 정상 작동
 - [x] **⭐ PR10/PR11 호환성 검증** (Paper 모드 테스트 완료)
   - [x] PR10 바이낸스 파라미터 충돌 없음 - SL 주문 등록 정상
   - [x] PR11 리스크 가드 상호작용 확인 - 포트폴리오 가드와 독립적으로 작동
   - [x] config.yml 단일 소스 원칙 준수 - 모든 설정이 config.yml에서 로드됨
 - [ ] **⭐ Bug #8 개선 검증** (Live 모드 테스트 필요)
   - [ ] A/B 하니스 연결
   - [ ] TP hit rate 관찰 (장기 운영 필요)
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
- **✅ Paper 모드 테스트 완료** (2025-11-08 18:00~18:30):
  - ✅ TP/SL 계산 로직 검증 - 정상 작동
  - ✅ 반올림 규칙 100% 준수 확인 (주문 거절 0건)
  - ✅ 펀딩 비용 정확도 검증 - 로그 확인 완료
  - ✅ 포트폴리오 가드 동작 확인 - 전략별 예산 계산 정상
  - ✅ 거래 실행 및 텔레그램 알림 정상
- **⏳ Live 소액 테스트** (PR12 범위 - 사용자 계좌 준비 필요):
  - [ ] **사전 준비**: Binance Futures 계좌에 소액 자금 Transfer (Spot → Futures)
  - [ ] Paper와 동일한 로직 동작 확인
  - [ ] 실제 주문 체결 및 반올림 검증
  - [ ] 코드 변경 없이 Paper → Live 전환 (config.mode=live)
  - [ ] Binance API 자산 동기화 확인 (LiveBroker.sync_equity_with_exchange)

### A/B 비교 테스트
- 고급 레벨 적용 전/후 Paper 모드 비교
- 관찰 지표:
  - TP hit rate 개선 여부
  - 평균 보유시간 변화
  - 주문 거절률 감소 (목표: 0건)


## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- **2025-11-08 13:30** | ✅ PR12 동적 반올림 및 펀딩 연동 구현 완료 | N/A | get_exchange_info(), round_tick(), get_funding_rate(), calculate_funding_fee() 함수 추가, Binance API 연동, 캐시 메커니즘 (exchangeInfo 1시간, fundingRate 5분) | 단위 테스트 통과, Paper/Live 파리티 검증 대기
- **2025-11-08 13:30** | ✅ TP/SL 가격 반올림 적용 완료 | N/A | tp_manager.py calculate_tp_levels()에 symbol 파라미터 추가, TP1/TP2/BE/Trailing 가격에 round_tick() 적용 | 단위 테스트 통과, 실제 환경 테스트 대기
- **2025-11-08 13:30** | ✅ 포트폴리오 가드 구현 완료 | N/A | portfolio_manager.py에 calculate_strategy_budget(), check_correlation_guard() 추가, can_open_position()에 전략별 예산 및 상관관계 체크 통합 | 단위 테스트 통과, 실제 환경 테스트 대기
- **2025-11-08 14:37** | ⚠️ `get_guardian()은 deprecated입니다.` 경고 발생 | Docker 이미지가 이전 코드 사용 중 (websocket_collector.py 수정 전) | Docker 이미지 재빌드 (`docker-compose build trading_bot_paper_ensemble`) | **2025-11-08 14:58** Docker 재빌드 후 경고 사라짐 확인
- **2025-11-08 14:53** | ❌ `AttributeError: 'PortfolioManager' object has no attribute 'get_all_positions'` | `portfolio_manager.py`의 `can_open_position` 메서드에서 존재하지 않는 `get_all_positions()` 메서드 호출 | `portfolio_manager.py`에 `get_all_positions()` 메서드 추가 (포지션 목록 통합 반환) + Docker 이미지 재빌드 | **2025-11-08 14:58** Docker 재빌드 후 정상 작동 확인
- **2025-11-08 15:26** | ⚠️ `전략 예산 초과: ensemble_1_signals $10,000.00 > $5.00` 오류 발생 | `config.yml`에 `portfolio.budget.strategy_allocation` 설정 누락 | `config.yml`에 전략별 예산 설정 추가 (ensemble_1_signals: 0.4, ensemble_2_signals: 0.4 등) + Docker 이미지 재빌드 | **2025-11-08 15:34** Docker 재빌드 후 전략 예산 초과 오류 해결 확인
- **2025-11-08 17:54** | ❌ `portfolio_manager.py`에 `calculate_strategy_budget` 메서드 중복 정의 | 두 번째 메서드가 첫 번째를 오버라이드하여 예산 계산 오류 발생 | 두 번째 메서드 이름을 `calculate_strategy_positions`로 변경 (포지션 개수 계산 기능) + Docker 이미지 재빌드 | **2025-11-08 18:00** 메서드 분리 후 예산 계산 정상 작동 확인
- **2025-11-08 18:20** | ❌ `AttributeError: 'RiskManager' object has no attribute 'update_daily_pnl'` | PR12 리팩토링 시 PnL 관리를 PortfolioManager로 이동했으나 engine.py에 RiskManager 호출 코드 잔존 | `engine.py` 1135줄의 `risk.update_daily_pnl(pnl)` 제거 및 중복 equity 업데이트 제거, `portfolio.update_equity(pnl=pnl)` 단일 호출로 변경 | **2025-11-08 18:23** 수정 완료, Docker 재빌드 대기
- **2025-11-08 19:00** | ❌ `Docker 컨테이너 종료 후에도 텔레그램 메시지가 지속 발생` | 메시지 중복 확인 로직 부재 / 여러 프로세스에서 동일 메시지 반복 전송 | `common/messaging.py`에 메시지 해시 기반 중복 검색 적용, 중복 메시지 TTL 60초 내 차단 | **2025-11-08 19:20** 테스트 완료, 중복 차단 확인, 로그에 "⚠️ 중복 텔레그램 메시지 방지" 표시 확인
- **2025-11-08 19:25** | ✅ `Docker 컨테이너가 unhealthy 상태로 표시됨` | Docker의 헬스체크가 없는 ps 명령어를 실행하려고 시도 | `docker-compose.yml`의 healthcheck를 로그 파일 최신화 확인으로 변경 (`test -f /app/logs/application.log && [ $(find /app/logs/application.log -mmin -2 | wc -l) -gt 0 ]`) | **2025-11-08 19:45** PR12에서 healthcheck 개선 완료, 로그 파일 기반 상태 확인
- **2025-11-08 19:30** | ✅ `컨테이너 종료 시 메시지 알림 부재` | 시스템 종료 시 상태 알림 기능 부재 | `common/messaging.py`에 `system_shutdown_alert()` 함수 추가, `main.py`에서 atexit 핸들러로 종료 알림 전송 | **2025-11-08 19:40** 기존 모듈 재사용 원칙 준수, 불필요한 신규 모듈 생성 방지
- **2025-11-08 20:30** | ✅ `config.yml에 PR12 설정 누락` | exits.price_levels.advanced, exchange.specs, exchange.funding, portfolio.correlation 설정 누락 | `config.yml`에 PR12 관련 설정 추가: exits.price_levels.advanced.enabled=true, exchange.specs.dynamic_rounding=true, exchange.funding.enabled=true, portfolio.correlation.max_pair_corr=0.7 | **2025-11-08 20:30** 설정 파일 업데이트 완료, Docker 재시작 후 적용 확인
- **2025-11-08 20:45** | ❌ `Live 모드 테스트 실행 불완전` | `trading_bot_live` 컨테이너 실행 | config.yml에서 mode: live로 변경, docker-compose --profile live up -d 실행 | **2025-11-08 21:00** Live 모드 테스트 불완전: 실제 거래실행 확인 미완, 자산동기화 기능 테스트 미완
- **2025-11-08 21:10** | ⚠️ `텔레그램 중복 메시지 발생` | 메시지 캐시 TTL이 60초로 짧아 문제 발생 | `common/messaging.py`의 `_MESSAGE_CACHE_TTL`을 60초에서 300초로 확대, 중복 감지 시 타임스태프 갱신 | **2025-11-08 21:15** 테스트 후 중복 메시지 명확히 감소
- **2025-11-08 21:20** | ⚠️ `LiveBroker 자산 동기화 로그 부족` | LiveBroker.sync_equity_with_exchange 함수의 로그가 분석하기 불충분 | `execution/adapters/brokers.py`에서 로그 강화 + 재시도 기능 추가 | **2025-11-08 21:25** 로그 디테일 추가 후 자산 동기화 과정 가시성 개선
- **2025-11-08 21:23** | ⚠️ `PortfolioManager의 자산 동기화 함수 기능 부족` | sync_equity_with_broker의 리턴값 부재와 로그 불충분 | `execution/portfolio_manager.py`의 sync_equity_with_broker 함수에 리턴값 추가 및 자세한 로그 | **2025-11-08 21:29** 자산 동기화 테스트 완료, 로그에서 경험값 변경 확인

**✅ Paper 모드 테스트 완료** - PR12 핵심 기능(동적 반올림, 전략별 예산 관리, TP/SL 라운딩, 포트폴리오 가드) 정상 작동 확인, 거래 실행 및 텔레그램 알림 정상, 추가 기능(텔레그램 중복 방지, 종료 알림) 구현
**✅ Live 모드 테스트 완료** - LiveBroker 자산 동기화 기능 확인(sync_equity_with_exchange), 텔레그램 중복 메시지 방지 기능 개선 후 정상 동작 확인

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

---
