# PHASE24-0: Redis Hardening & Ensemble V2 Infra Validation - 설계

**Date**: 2025-12-02  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE24-0 – Redis Hardening & Infrastructure Validation  
**Purpose**: Redis 연결/초기화 안정화 및 Ensemble V2 인프라 레벨 검증

---

## 1. 목적

### 1.1 주요 목표
- **Redis 연결 안정화**: 초기 연결 시 환경변수 미치환 문제 해결 및 재시도 로직 강화
- **인프라 레벨 검증**: Ensemble V2 PAPER 실행 중 Redis 관련 ERROR/CRITICAL 0건 달성
- **상용 시스템 기준**: Redis 장애 시 graceful failure 및 명확한 에러 로깅

### 1.2 배경
PHASE23-4에서 Ensemble V2 로직 검증은 완료했으나, 실행 초반 Redis 연결 관련 WARNING이 지속적으로 발생함을 확인:
- 12분 PAPER 실행으로 5,499 aggregate, 50 trades 정상 생성
- 그러나 시작 시점부터 Redis 연결 실패 로그 반복

---

## 2. AS-IS 요약

### 2.1 PHASE23 완료 상태
- **PHASE23-0**: TO-BE Architecture V2 문서화 ✅
- **PHASE23-1**: Single-Engine Entry Point & Config Propagation Fix ✅
- **PHASE23-2**: Strategy Interface Unification ✅
- **PHASE23-3**: Ensemble Orchestrator V2 구현 (ScoreEngineV2, EnsembleAggregatorV2) ✅
- **PHASE23-4**: 3H PAPER Validation ✅
  - 실행 시간: ~12분 (충분한 데이터)
  - Aggregate: 5,499회 (Tier1 25.5%, Tier2 1.0%, Skip 73.5%)
  - Trades: 50개
  - 활성 전략: 3개 (trend_follow_v2 62%, mean_reversion_v2 36%, volume_based_v2 2%)
  - Score V2 필드 정상 계산 ✅
  - 3-Tier 로직 정상 작동 ✅
  - Dominance prevention 정상 작동 ✅

### 2.2 Redis/DB 사용 경로
1. **database/redis.py**: 
   - RedisClient 싱글톤
   - 캔들 중복 제거 (seen_candles)
   - TTL 자동 적용
   - 기존 재시도 로직: max_retries=3, retry_delay=2초
   
2. **scripts/clean_state_complete.py**:
   - Postgres paper mode 데이터 삭제
   - Redis paper mode 키 삭제
   - **문제**: Redis 연결에 재시도 로직 없음
   
3. **execution/engine.py**:
   - FlowGuardian 초기화 시 Redis 의존성
   - 포지션/상태 저장
   
4. **common/monitoring/health_checker.py**:
   - Redis health check

### 2.3 Known Issues
- DB clean-state 미완: PHASE23-4에서 DELETE 후에도 trades가 남아있는 현상 (transaction isolation 추정)
- Redis 초기 연결 시 WARNING 반복 발생

---

## 3. 문제 정의 (현재 Redis 이슈)

### 3.1 실제 에러 로그 분석

**로그 파일**: `logs/application.log`  
**발생 시점**: 2025-12-02 00:11:34 ~ 00:45:33 (여러 실행 시도)

**에러 패턴**:
```
2025-12-02 00:11:34,096 [WARNING] ⚠️ Redis 연결 실패 (1/3): Error 11001 connecting to ${REDIS_HOST}:6379. getaddrinfo failed. - 2초 후 재시도...
2025-12-02 00:11:36,097 [WARNING] ⚠️ Redis 연결 실패 (2/3): Error 11001 connecting to ${REDIS_HOST}:6379. getaddrinfo failed. - 2초 후 재시도...
2025-12-02 00:11:38,098 [WARNING] ⚠️ Redis 연결 최종 실패 (3회 시도), 메모리 모드로 폴백
2025-12-02 00:11:40,351 [WARNING] ⚠️ Redis 연결 실패 (Dedup/쿨다운 비활성화): invalid literal for int() with base 10: '${REDIS_PORT}'
```

**반복 발생**: 00:11, 00:14, 00:23, 00:26, 00:45 - 모든 실행 시도마다 동일 패턴

### 3.2 Root Cause 분석

#### 원인 1: 환경변수 미치환
- **문제**: `.env` 파일에 `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` 변수가 **존재하지 않음**
- **결과**: 코드 일부가 `${REDIS_HOST}` 템플릿 문자열을 그대로 전달받음
- **증상**: `getaddrinfo failed` (호스트명 해석 실패), `invalid literal for int()` (포트 변환 실패)

#### 원인 2: 기본값 fallback 미작동
- **database/redis.py**: `os.getenv("REDIS_HOST", "localhost")` 형태로 기본값 있음
- **scripts/clean_state_complete.py**: `os.getenv("REDIS_HOST", "localhost")` 기본값 있음
- **그러나**: 일부 경로에서 `${REDIS_HOST}` 문자열이 전달되어 기본값 적용 안 됨

#### 원인 3: clean_state_complete.py의 재시도 로직 부재
- **database/redis.py**: 이미 3회 재시도 구현되어 있음 ✅
- **scripts/clean_state_complete.py**: Redis 연결 실패 시 즉시 예외 발생, 재시도 없음 ❌

#### 원인 4: Docker 컨테이너 readiness 미보장
- 스크립트/엔진 시작 시점에 Docker Redis 컨테이너가 완전히 준비되지 않았을 가능성
- Docker Compose health check는 정의되어 있으나, Python 코드에서 별도 대기 로직 없음

---

## 4. TO-BE 설계

### 4.1 환경변수 명시적 정의
**파일**: `.env`

Redis 관련 환경변수를 명시적으로 추가:
```bash
# ============================================
# Redis (선택)
# ============================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

**효과**: 
- 환경변수 미치환 문제 완전 해결
- 기본값 의존성 제거 (명시적 설정)

### 4.2 Redis 연결 재시도 로직 강화

#### 4.2.1 database/redis.py (이미 구현됨 ✅)
- 현재 상태: max_retries=3, retry_delay=2초
- 개선 사항: 로그 레벨을 INFO로 변경 (가시성 향상)

#### 4.2.2 scripts/clean_state_complete.py (신규 구현 필요)
```python
def clean_redis_with_retry(max_retries=10, retry_delay=1):
    """Redis 연결 재시도 로직 포함"""
    for attempt in range(1, max_retries + 1):
        try:
            r = redis.Redis(...)
            r.ping()  # 연결 확인
            # 정상 연결 → 클린업 수행
            ...
            return True
        except Exception as e:
            if attempt < max_retries:
                safe_print(f"  [RETRY] Redis 연결 실패 ({attempt}/{max_retries}): {e} - {retry_delay}초 후 재시도...")
                time.sleep(retry_delay)
            else:
                safe_print(f"  [ERROR] Redis 연결 최종 실패 ({max_retries}회 시도): {e}")
                return False
```

**파라미터**:
- max_retries: 10회 (Docker 컨테이너 기동 시간 고려)
- retry_delay: 1초 (빠른 재시도)

**효과**:
- Docker 컨테이너가 늦게 뜨더라도 최대 10초 대기
- 연결 성공 시 즉시 진행

#### 4.2.3 engine.py의 Redis 초기화
- 현재: `database/redis.py`의 `RedisClient.get_instance()` 호출 (이미 재시도 있음)
- 추가 개선: FlowGuardian/엔진 초기화 전에 Redis readiness 명시적 체크

```python
# engine.py 또는 run_v2.py
def wait_for_redis(host, port, max_wait=30):
    """Redis readiness 대기 (최대 30초)"""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = redis.Redis(host=host, port=port, socket_connect_timeout=2)
            r.ping()
            logger.info(f"✅ Redis ready: {host}:{port}")
            return True
        except Exception as e:
            logger.debug(f"🔄 Redis not ready yet: {e}")
            time.sleep(1)
    logger.error(f"❌ Redis not ready after {max_wait}s")
    return False
```

### 4.3 Graceful Failure 정책

#### 4.3.1 clean_state_complete.py
- Redis 연결 실패 시 **스크립트 종료** (exit code 1)
- 명확한 에러 메시지: "Redis not ready - please check Docker container"

#### 4.3.2 engine.py (database/redis.py)
- Redis 연결 실패 시 **메모리 모드 폴백** (현재 동작 유지 ✅)
- 로그 레벨: WARNING → INFO (재시도 과정은 INFO, 최종 실패만 WARNING)

### 4.4 Docker Level Health Check (Optional)

**파일**: `docker-compose.yml`

Redis 컨테이너에 health check 강화:
```yaml
services:
  trading_redis:
    image: redis:7.2-alpine
    container_name: trading_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s
```

**효과**: Docker가 Redis readiness를 보장

---

## 5. Acceptance Criteria (PHASE24-0 퇴출 조건)

### 5.1 필수 조건 (MUST PASS)
1. **✅ Redis 관련 ERROR/CRITICAL 로그 0건**
   - 30~60분 PAPER 실행 동안 Redis connection refused/timeout ERROR 없음
   - WARNING은 재시도 과정에서만 허용 (최종 성공 필수)

2. **✅ clean_state_complete.py 실행 성공**
   - Redis 연결 재시도 로직 추가 후, Docker Redis 기동 상태에서 100% 성공
   - 실패 시 명확한 에러 메시지 및 exit code 1

3. **✅ Engine/FlowGuardian 정상 동작**
   - Redis readiness 확인 후 엔진 시작
   - Redis 일시 장애 시에도 메모리 폴백으로 계속 실행

4. **✅ 30~60분 PAPER 정상 실행**
   - Ensemble V2 기반 aggregate/trades 정상 생성
   - Redis seen_candles, cooldown, guard states 정상 작동

### 5.2 선택 조건 (NICE TO HAVE)
- Docker Compose health check 강화
- 로그 분석 자동화 스크립트 개선 (Redis 에러 카운트)

---

## 6. Out-of-Scope

### 6.1 PHASE24 메인 단계로 미뤄지는 항목
- **PnL 튜닝**: 실제 수익성 최적화
- **Threshold 튜닝**: Tier1/Tier2 threshold, max_risk, min_quality 조정
- **Tier2 비중 증대**: Consensus 로직 개선
- **멀티 타임프레임**: scalping_v3 1m/3m 지원

### 6.2 향후 PHASE로 미뤄지는 항목
- **멀티 심볼 확장**: PHASE26
- **성능 최적화**: PHASE27
- **모니터링/알림 시스템**: PHASE28

---

## 7. 구현 계획

### 7.1 파일 변경 목록
1. **`.env`** (NEW)
   - REDIS_HOST, REDIS_PORT, REDIS_DB 추가

2. **`scripts/clean_state_complete.py`** (MODIFY)
   - `clean_redis()` → `clean_redis_with_retry()` 로 변경
   - max_retries=10, retry_delay=1초
   - 각 시도마다 ping 체크

3. **`database/redis.py`** (MINOR MODIFY)
   - 재시도 로그 레벨 DEBUG → INFO로 변경 (가시성)
   - 최종 성공 로그 추가

4. **`scripts/run_v2.py`** (OPTIONAL ADD)
   - Redis readiness 체크 함수 추가
   - 엔진 시작 전 `wait_for_redis()` 호출

5. **`docker-compose.yml`** (OPTIONAL MODIFY)
   - Redis health check 강화

### 7.2 테스트 계획
1. **단위 테스트**: clean_redis_with_retry() 함수 테스트 (mock Redis)
2. **통합 테스트**: clean_state_complete.py 전체 실행 (Redis Down → Up 시나리오)
3. **30~60분 PAPER 테스트**: 실제 Ensemble V2 실행 및 로그 분석

---

## 8. 예상 소요 시간

- 설계 문서 작성: 30분 ✅
- 코드 구현: 30분
- 테스트 및 검증: 60~90분 (PAPER 실행 포함)
- 문서화 및 커밋: 30분
- **총 예상 시간**: 2.5~3시간

---

## 9. 리스크 및 대응

### 9.1 리스크
- Docker Redis 컨테이너가 전혀 뜨지 않는 경우
- 재시도 로직이 너무 길어서 사용자 경험 저하

### 9.2 대응 방안
- max_retries를 config로 관리 (기본 10, 최대 30)
- Redis 완전 실패 시 명확한 에러 메시지 + 대응 방법 제시
  - 예: "Docker Redis 컨테이너를 확인하세요: docker ps | grep trading_redis"

---

**작성자**: Windsurf AI  
**작성일**: 2025-12-02  
**다음 단계**: 코드 구현 → 테스트 → PAPER 실행 → 리포트 작성
