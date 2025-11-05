# PR9: 종합 시스템 개선 계획

**작성일**: 2025-11-05 12:55 UTC+09:00  
**목표**: Signal Integrity & Redis 통합(중복 방지, 재시작 내구성)  
**예상 작업 시간**: 2-4시간  
**.windsurfrules 준수**: 100%

---

## 📋 PR8 완료 사항 (100% ✅)

1. ✅ 부동소수점 안전 비교 (epsilon 0.1)
2. ✅ 전략별 독립 쿨다운
3. ✅ 앙상블 로깅 투명성 확보
4. ✅ **레버리지 설정 정합** (기본 2x, 범위 2-50x, cap=50)
5. ✅ Risk per trade 조정 (0.3-1.0%)
6. ✅ 종합 아키텍처 문서

---

## 🎯 PR9 작업 목록 (Redis 통합 중심, 5개 단계)

### Phase 1: 캔들 중복 제거 (Engine)
**작업 시간**: ~45분  
**파일**: `execution/engine.py`  
**내용**:
- RedisClient 훅 연결: `is_seen(symbol, timeframe, closed_at)` → duplicate skip → `mark_seen()`
- TTL: `monitoring.redis.ttl_seconds` 사용(기본 3600)
- 미가용 시 메모리 폴백 유지(기존 로직 영향 없음)

**수용 기준**:
- 재시작 직후 동일 캔들 재처리 없음
- 로그: `⏭️ 중복 캔들 무시` 패턴 1회 이상 발생

---

### Phase 2: 심볼/전략별 쿨다운 Redis TTL (Portfolio/Engine)
**작업 시간**: ~45분  
**파일**: `execution/engine.py`, `execution/portfolio_manager.py`  
**내용**:
- 현재 메모리 dict 기반 쿨다운을 Redis TTL 키(`cooldown:{symbol}_{strategy}`)로 보강
- 엔진에서 거부 시 set(TTL), 체크 시 get
- 미가용 시 메모리 폴백 유지

**수용 기준**:
- 프로세스 재시작 후에도 쿨다운 지속
- 로그: 쿨다운 중 디버그 1회 이상

---

### Phase 3: 신호 중복 제거 (Strategies/DB 멱등)
**작업 시간**: ~45분  
**파일**: `strategies/*`(발행부), `strategies/ensemble.py`(조회부)  
**내용**:
- 신호 해시: `symbol/side/entry/sl/tp` → MD5 → `signal:{symbol}:{hash}` TTL 저장
- DB 레벨 멱등: `(strategy_id, symbol, timeframe, candle_closed_at)` UNIQUE 충돌 시 무시

**수용 기준**:
- 동일 신호 재발행 시 Redis hit로 무시
- decisions 조회 시 from_signals 중복 없음

---

### Phase 4: 레버리지 x2 원인 진단 로깅(계산 경로 가시화)
**작업 시간**: ~30분  
**파일**: `common/calculations.py`  
**내용**:
- `leverage_suggestion()` 내부에 base_lev, 각 멀티플라이어, clamp 포인트 디버그 로그 추가(토글 가능)

**수용 기준**:
- 레버리지 2x 지속 시 어느 단계에서 clamp되는지 로그로 식별 가능

---

### Phase 5: 테스트/문서/수용 기준
**작업 시간**: ~15분  
**파일**: `docs/PHASE5/INTEGRATION_TEST.md`, `docs/PHASE5/PR8_REDIS_DB_USAGE.md`  
**내용**:
- INTEGRATION_TEST에 Redis 확인 절차 추가(재시작 내구성, dedup hit)
- PR8_REDIS_DB_USAGE에 최종 통합 결과와 키 네이밍 표기

**수용 기준 (공통)**:
- FlowGuardian READY 통과 유지
- logs/trial_0000.json 생성, DB score_total == JSON score_total
- pre-commit(ruff, black, mypy, vulture, coverage>85%) 통과

---

### Phase 6: Context Scaling ⚙️ (추가!)
**작업 시간**: 1시간  
**파일**: `execution/risk_manager.py`, `execution/position_sizer.py`  
**내용**:
- Regime 기반 조정 (트렌드 → 1.2x, 횡보 → 0.8x)
- Volatility 기반 조정 (급등 → 0.5x)
- Drawdown 기반 조정 (DD > 5% → 0.5x)

**예상 효과**:
- 시장 상황 부적합 시 리스크 자동 축소
- 드로우다운 시 자동 방어

---

## 📊 예상 개선 효과 (PR9)

- 재시작/다중 인스턴스 환경에서 중복 처리 제거 → 안정성 향상
- 엔진 로딩 직후 재처리/중복 신호 제거 → 리소스 절감, 로그 가독성 향상
- 레버리지 진단 로그로 계산 경로 투명성 확보

---

## 🚀 작업 순서

### 즉시 작업 (오늘)
1. ✅ 캔들 중복 제거 (Engine)
2. 🔄 심볼/전략 쿨다운 Redis TTL (Portfolio/Engine)
3. 🔄 신호 중복 제거 (Strategies/DB)

### 단기 작업 (내일)
4. 🔄 레버리지 x2 진단 로깅
5. 🔄 테스트/문서 수용 기준 반영

---

## 📝 수정 파일 목록 (PR9)

1. `execution/engine.py` — Redis dedup 훅 + 쿨다운 TTL 연동
2. `execution/portfolio_manager.py` — 쿨다운 TTL get/set(옵션)
3. `strategies/*` — 신호 발행부에 Redis 해시 멱등 처리
4. `common/calculations.py` — 레버리지 진단 로그(토글)
5. `docs/PHASE5/INTEGRATION_TEST.md`, `docs/PHASE5/PR8_REDIS_DB_USAGE.md` — 테스트/문서 동기화

---

**다음 작업**: Phase 1 (엔진 Redis dedup)부터 진행할까요?
