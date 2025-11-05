# PR7-2 Mixed-TF 상태 보고서

**작성일**: 2025-11-03  
**작성자**: AI Assistant  
**목적**: PR7-2 진행 상황 및 문제점 종합 분석

---

## 📋 목차

1. [현재 상황 요약](#현재-상황-요약)
2. [발견된 문제](#발견된-문제)
3. [코드 vs 문서 불일치](#코드-vs-문서-불일치)
4. [해결 방안](#해결-방안)
5. [테스트 계획](#테스트-계획)

---

## 현재 상황 요약

### ✅ 완료된 작업

1. **PR7 (리팩토링)**
   - 6개 전략 모듈화 완료
   - 앙상블 로직 구현
   - 테스트 8/12 통과 (핵심 7/7)
   - 백테스트 검증 완료

2. **PR7-2 (Mixed-TF 구현)**
   - Feed 레이어: `config.yml` base_timeframe=1m 추가
   - Engine 레이어: 전략별 리샘플링 로직 구현
   - WebSocket: 1m 캔들 수신 확인
   - 큐 추가: 닫힌 캔들 큐 추가 성공

### ⚠️ 진행 중 이슈

1. **Redis 연결 실패** (근본 원인)
   - 환경변수 불일치: `REDIS_URL` vs `REDIS_HOST`/`REDIS_PORT`
   - 3회 재시도 후 메모리 폴백 모드로 작동 중
   - 재시작 시 중복 제거 데이터 손실 가능

2. **신호 생성 미확인**
   - 버퍼 축적 중 (lookback=100, ~1.5시간 소요)
   - 전략 실행 여부 미확인
   - DB에 신호 없음 (3m 44건은 이전 데이터)

---

## 발견된 문제

### 🔴 문제 1: Redis 환경변수 불일치

**현상**:
```
⚠️ Redis 연결 실패 (1/3): Error -2 connecting to ${REDIS_HOST}:6379
⚠️ Redis 연결 실패 (2/3): Error -2 connecting to ${REDIS_HOST}:6379
⚠️ Redis 연결 최종 실패 (3회 시도), 메모리 모드로 폴백
```

**원인**:

**config.yml** (L264-267):
```yaml
redis:
  host: ${REDIS_HOST}  # ❌ 환경변수 없음
  port: ${REDIS_PORT}  # ❌ 환경변수 없음
  ttl_seconds: 3600
```

**docker-compose.yml** (L204):
```yaml
environment:
  - REDIS_URL=redis://redis:6379/0  # ✅ 이것만 있음
```

**영향**:
- Redis 연결 실패 → 메모리 폴백
- 재시작 시 중복 제거 데이터 손실
- 분산 환경 지원 불가

**해결책**:
```yaml
# docker-compose.yml에 추가
- REDIS_HOST=redis
- REDIS_PORT=6379
```

---

### 🟡 문제 2: 신호 생성 확인 불가

**현상**:
- ✅ WebSocket 1m 캔들 수신
- ✅ 큐에 캔들 추가
- ✅ 엔진 시작
- ❌ 전략 실행 로그 없음
- ❌ 신호 생성 없음

**추정 원인**:
1. 버퍼 크기 부족 (lookback=100, 현재 축적 중)
2. 리샘플링 로직 오류 가능성
3. min_bars_for_signal 조건 미충족

**확인 필요**:
- 버퍼 크기 로그
- 리샘플링 결과 로그
- 전략 실행 여부

---

### 🟡 문제 3: 문서 vs 코드 불일치

#### PR7_COMPLETE.md
- **상태**: "✅ COMPLETE"
- **실제**: Redis 연결 실패, 신호 생성 미확인

#### PR7-2_COMPLETE.md
- **상태**: "⚠️ CODE COMPLETE, VERIFICATION PENDING"
- **실제**: 검증 진행 중, 문제 발견

#### INTEGRATION_TEST.md
- **내용**: 단순 스크립트 테스트만
- **부족**: 페이퍼 모드 end-to-end 테스트 없음

---

## 코드 vs 문서 불일치

### 1. Redis 설정

**문서 (REFACTORING_collector_v1.md)**:
```
Redis 기반 중복 제거 (재시작 시에도 유지)
```

**실제 코드**:
- Redis 연결 실패 (환경변수 없음)
- 메모리 폴백 모드로 작동
- 재시작 시 데이터 손실

### 2. Mixed-TF 검증

**문서 (PR7-2_COMPLETE.md)**:
```
검증 대기: 신호 생성 확인 (버퍼 축적 중)
```

**실제 상황**:
- 1.5시간 경과 후에도 신호 없음
- 전략 실행 여부 불명확
- 리샘플링 로직 검증 필요

### 3. 테스트 범위

**문서 (INTEGRATION_TEST.md)**:
- 백테스트 스크립트 테스트
- 단위 테스트

**부족한 부분**:
- 페이퍼 모드 end-to-end 테스트
- Redis 연결 테스트
- WebSocket → Engine → Strategy → DB 전체 플로우 테스트

---

## 해결 방안

### 1단계: Redis 연결 수정 (즉시)

**docker-compose.yml 수정**:
```yaml
trading_bot_paper_ensemble:
  environment:
    - REDIS_URL=redis://redis:6379/0
    - REDIS_HOST=redis  # ✅ 추가
    - REDIS_PORT=6379   # ✅ 추가
```

**검증**:
```bash
docker-compose --profile paper up --build -d
docker logs trading_bot_paper_ensemble | grep Redis
# 예상: "✅ Redis 연결 성공: redis:6379"
```

---

### 2단계: 신호 생성 디버깅 (1시간)

**디버그 로그 추가** (임시):
```python
# engine.py
logger.info(f"🔍 버퍼 크기: {len(df)}, 리샘플: {len(df_tf)}, 필요: {min_required}")
logger.info(f"🔍 전략 실행: signal={signal is not None}")
```

**확인 사항**:
1. 버퍼가 100개 이상 쌓였는지
2. 리샘플링이 정상 작동하는지
3. 전략이 실행되는지

---

### 3단계: End-to-End 테스트 (2시간)

**테스트 시나리오**:

1. **Redis 연결 테스트**
   ```bash
   docker exec trading_bot_paper_ensemble python -c "
   from database.redis import RedisClient
   rc = RedisClient.get_instance(host='redis', port=6379)
   print('Redis enabled:', rc.enabled)
   "
   ```

2. **WebSocket → Queue 테스트**
   ```bash
   # 로그 확인
   docker logs trading_bot_paper_ensemble | grep "닫힌 캔들 큐 추가"
   # 예상: 1분마다 100개 심볼 로그
   ```

3. **Engine → Strategy 테스트**
   ```bash
   # 버퍼 축적 후 (2시간)
   docker logs trading_bot_paper_ensemble | grep "전략 실행"
   # 예상: 전략 실행 로그
   ```

4. **Strategy → DB 테스트**
   ```sql
   SELECT timeframe, COUNT(*) 
   FROM monitoring.signals 
   WHERE created_at > NOW() - INTERVAL '10 minutes'
   GROUP BY timeframe;
   -- 예상: 3m, 5m, 15m, 1h, 4h 신호
   ```

5. **Ensemble → Trade 테스트**
   ```sql
   SELECT * FROM trading.decisions 
   WHERE created_at > NOW() - INTERVAL '10 minutes'
   ORDER BY created_at DESC LIMIT 10;
   -- 예상: 앙상블 거래 결정
   ```

---

## 테스트 계획

### Phase 1: 환경 수정 (30분)

1. ✅ Redis 환경변수 추가
2. ✅ 재빌드 및 재시작
3. ✅ Redis 연결 확인

### Phase 2: 데이터 수집 (2시간)

1. ⏳ WebSocket 1m 캔들 수신 확인
2. ⏳ 버퍼 축적 (lookback=100)
3. ⏳ 큐 헬스 모니터링

### Phase 3: 신호 생성 (1시간)

1. ⏳ 전략 실행 확인
2. ⏳ 리샘플링 검증
3. ⏳ 다중 TF 신호 생성 확인

### Phase 4: 앙상블 거래 (1시간)

1. ⏳ 신호 결합 로직 확인
2. ⏳ 거래 결정 생성
3. ⏳ DB 저장 확인

### Phase 5: 문서 업데이트 (1시간)

1. ⏳ PR7-2_COMPLETE.md 업데이트
2. ⏳ INTEGRATION_TEST.md 확장
3. ⏳ REFACTORING_collector_v1.md 수정

---

## 다음 단계

### 즉시 실행
1. Redis 환경변수 추가
2. 재빌드 및 재시작
3. Redis 연결 확인

### 2시간 후
1. 버퍼 축적 확인
2. 신호 생성 확인
3. DB 저장 확인

### 완료 후
1. 문서 업데이트
2. 테스트 케이스 추가
3. PR7-2 완료 승인

---

## 참고 문서

- [PR7_COMPLETE.md](./PR7_COMPLETE.md)
- [PR7-2_COMPLETE.md](./PR7-2_COMPLETE.md)
- [INTEGRATION_TEST.md](./INTEGRATION_TEST.md)
- [REFACTORING_collector_v1.md](./REFACTORING_collector_v1.md)
- [REFACTORING_개선계획.md](./REFACTORING_개선계획.md)
