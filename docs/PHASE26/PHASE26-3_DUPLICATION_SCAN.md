# PHASE26-3: 모듈 중복 패턴 스캔 결과

**작성 일자**: 2025-12-03  
**목적**: `common/*` 하위의 domain 로직 중복 여부 확인

---

## 스캔 결과 요약

### ✅ 정리 완료

1. **indicators**
   - **Top-level**: `indicators/` (canonical, domain logic)
   - **common**: `common/indicators/` (deprecated shim으로 변경 완료)
   - **상태**: ✅ **통합 완료** (PHASE26-3 Indicators Consolidation)

---

## 스캔 대상 (중복 없음 확인)

### 2. **perf** - 중복 없음
   - **common/perf/**: `perf_profiler.py` (PHASE26-3 전용)
   - **Top-level**: 없음
   - **판정**: 단일 위치, 중복 없음

### 3. **monitoring** - 의도적 분리
   - **Top-level monitoring/**: 
     - `performance_monitor.py` (성능 메트릭)
     - `telemetry_profiler.py` (텔레메트리)
   - **common/monitoring/**:
     - `health_checker.py` (헬스 체크)
     - `heartbeat_monitor.py` (하트비트)
     - `latency_monitor.py` (레이턴시)
     - `watchdog.py` (감시)
   - **판정**: 기능이 명확히 분리됨, 중복 아님

### 4. **ensemble** - 단일 위치
   - **common/ensemble/**: 앙상블 관련 유틸리티
   - **Top-level**: 없음
   - **판정**: 단일 위치, 중복 없음

### 5. **registry** - 단일 위치
   - **common/registry/**: 전역 레지스트리
   - **Top-level**: 없음
   - **판정**: 단일 위치, 중복 없음

---

## 결론

**중복 패턴 발견**: 1건 (indicators)  
**정리 완료**: 1건 (indicators → 통합 완료)

**현재 상태**: 
- ✅ 모든 domain 로직은 top-level 패키지에 위치
- ✅ `common/*`은 범용 유틸리티와 인프라 코드만 포함
- ✅ 중복 없음

**향후 조치**: 
- 추가 모듈 생성 시 반드시 기존 패키지 스캔
- Domain 로직은 top-level 패키지로
- `common/*`에 domain 로직 추가 금지

---

## 모듈 생성 가이드라인

### ✅ DO
- Domain 로직: top-level 패키지 생성 (`indicators/`, `strategies/`, `signals/` 등)
- 범용 유틸리티: `common/` 하위 (`common/logger.py`, `common/utils.py` 등)
- 인프라 코드: `common/` 하위 (`common/database.py`, `common/redis_client.py` 등)

### ❌ DON'T
- Domain 로직을 `common/` 하위에 생성
- 이미 존재하는 top-level 패키지와 동일한 이름의 `common/` 서브패키지 생성
- 기존 모듈 스캔 없이 새 모듈 추가

---

**문서 작성**: PHASE26-3 Indicators Consolidation  
**다음 작업**: 전략 및 앙상블 로직 개선 (PHASE_ROADMAP 참조)
