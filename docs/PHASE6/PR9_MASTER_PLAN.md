# PHASE6 — PR9 마스터 플랜: 신호 무결성 & Redis 통합

## 배경/의도(Overview)
재시작/병렬 처리 상황에서도 신호 무결성을 보장하기 위해 다음을 구현합니다:
- 캔들 중복 처리 방지(dedup)
- Redis 기반 쿨다운 TTL 지속성
- 신호 멱등성(동일 파라미터 신호의 중복 발행 차단)
또한 FlowGuardian READY 게이트는 항상 유지됩니다.

## 목표(Goals)
- 캔들 중복 처리 0건
- 프로세스 재시작 이후에도 쿨다운 TTL 유지
- 전략+심볼+파라미터 기준 멱등 키로 중복 신호 차단

## 범위(Scope, In)
- 엔진 레벨 캔들 dedup(키: 심볼+타임프레임+캔들 타임스탬프)
- Redis TTL 기반 쿨다운(`cooldown:{symbol}_{strategy}`)
- 신호 멱등 키(`signal:{symbol}:{hash}`)
- 재시작 내구성 및 계측(로그 패턴)
- 선택: Context Scaling 훅 배선(알고리즘 변경 없음)

## 제외(Out-of-Scope)
- 앙상블 알고리즘 개선(→ PR10)
- 리스크 가드 강화(→ PR11)
- 고급 가격 레벨/거래소 스펙(→ PR12)

## 영향 파일(Affected Files, 예상)
- execution/engine.py(dedup, TTL, 멱등 검사)
- docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(테스트 플랜)
- config.yml(기존 키 사용, 없으면 최소 추가)

## 설정 및 계약(Config Policy)
- 단일 소스: config.yml
- execution.reject_cooldown_seconds: int(기본 60)
- redis.*(host, port, db, prefix)
- logging.patterns(선택)

## FlowGuardian 게이트
- READY 플래그 없이는 PAPER/LIVE 실행 불가

## 단계(Phases)
- Phase 1: 엔진 루프에 캔들 dedup(중복 캔들 skip)
- Phase 2: Redis에 쿨다운 TTL 저장/갱신
- Phase 3: 신호 멱등성(정규화 파라미터 해시)
- Phase 4: 재시작 내구성 시나리오 테스트
- Phase 5: 계측/로그 패턴, 최소 메트릭 노출
- Phase 6: Context Scaling 훅 배선(행동 변화 없음)

## 로깅 패턴(Logging)
- "⏭️ 중복 캔들 무시"
- "🔒 {strategy} {symbol} 쿨다운 중"
- "🧩 신호 멱등 hit: signal:{symbol}:{hash}"

## 수용 기준(Acceptance)
- 재시작/급재생 3회 반복 테스트에서 중복 처리 0건
- 쿨다운 TTL 재시작 전후 잔여 TTL 편차 ≤ 2초
- 멱등 키 TTL = monitoring.redis.ttl_seconds(현재 3600초) 사용, TTL 만료 전 중복 신호 100% 차단
- dedup/쿨다운/멱등 로그 패턴 각 1회 이상 확인
- FlowGuardian READY 유지, logs/trial_0000.json 존재
- DB score_total == JSON score_total
- pre-commit 통과, coverage>85%

## 체크리스트(Checklist)
- [ ] Dedup 캐시(키: symbol, timeframe, ts)
- [ ] 쿨다운 TTL 키 설정/존중
- [ ] 신호 해시 계산 및 TTL 저장
- [ ] 재시작 시나리오 테스트 통과
- [ ] dedup/쿨다운/멱등 hit 로그 확인

## 테스트 플랜(Test Plan)
상세 절차는 docs/PHASE6/PR_MASTER_INTEGRATION_TEST.md(PR9 섹션) 참조. 로그 패턴과 선택 SQL 포함.

## 오류 수정 항목(Fix Log)
- 발생 일시 | 증상 | 원인 | 수정 내역 | 재발 방지(테스트/가드)
- 예: 2025-11-06 00:40 | 중복 캔들 처리됨 | dedup 키에 타임프레임 누락 | dedup 키 (symbol, timeframe, ts)로 교정 | integration: duplicate_candle_twice

## 로그/DB 산출물(Artifacts)
- logs/trial_0000.json: 실행 메타/점수
- DB(trading.*): decisions 등 중복 없이 기록
- Redis: cooldown, signal 키 TTL 상태

## 배포/롤백(Release/Rollback)
- 위험: 해시 정의가 과도하면 정상 신호가 차단될 수 있음
- 완화: 정규화 파라미터 사용, 적절한 TTL/만료, 모든 hit 로깅
- 롤백: config.yml의 기능 플래그(dedup/idempotency)로 비활성화

## 릴리즈 노트(Release Notes)
- 인프라 견고화 중심, 전략 로직의 기능 변경 없음

