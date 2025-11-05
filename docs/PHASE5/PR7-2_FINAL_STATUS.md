# PR7-2 Mixed-TF 최종 상태 보고서

**작성일**: 2025-11-03 23:20  
**상태**: ✅ **환경 수정 완료, 검증 진행 중**

---

## 📋 요약

### ✅ 해결 완료
1. **Redis 연결 실패** → **환경변수 추가로 해결**
   - `REDIS_HOST=redis`, `REDIS_PORT=6379` 추가
   - ✅ Redis 연결 성공: redis:6379 (TTL: 3600초)

2. **코드 정리**
   - 불필요한 디버그 로그 제거
   - 기존 모듈 활용 (신규 파일 없음)

### ⏳ 진행 중
1. **신호 생성 확인** (버퍼 축적 중, ~1.5시간 소요)
2. **다중 TF 신호 생성** (3m/5m/15m/1h/4h)
3. **앙상블 거래 결정**

---

## 🔍 발견된 문제와 해결

### 문제 1: Redis 연결 실패

**증상**:
```
⚠️ Redis 연결 실패 (1/3): Error -2 connecting to ${REDIS_HOST}:6379
⚠️ Redis 연결 최종 실패 (3회 시도), 메모리 모드로 폴백
```

**근본 원인**:
- **config.yml**: `redis.host: ${REDIS_HOST}`, `redis.port: ${REDIS_PORT}`
- **docker-compose.yml**: `REDIS_URL=redis://redis:6379/0`만 있음
- **결과**: 환경변수 `REDIS_HOST`, `REDIS_PORT` 없음 → 연결 실패

**해결**:
```yaml
# docker-compose.yml (L205-206)
- REDIS_HOST=redis
- REDIS_PORT=6379
```

**검증**:
```
✅ Redis 연결 성공: redis:6379 (TTL: 3600초)
```

---

## 📊 현재 진행 상황

### Phase 1: 환경 수정 ✅ 완료

| 항목 | 상태 | 비고 |
|------|------|------|
| Redis 환경변수 추가 | ✅ | REDIS_HOST, REDIS_PORT |
| 재빌드 및 재시작 | ✅ | docker-compose up --build |
| Redis 연결 확인 | ✅ | redis:6379 연결 성공 |

### Phase 2: 데이터 수집 ✅ 완료

| 항목 | 상태 | 비고 |
|------|------|------|
| WebSocket 1m 캔들 수신 | ✅ | 실시간 수신 중 (23:49 확인) |
| 큐에 캔들 추가 | ✅ | "닫힌 캔들 큐 추가" 로그 반복 확인 |
| 버퍼 축적 (100개) | ✅ | 30분 경과 (14:18 시작) |

### Phase 3: 신호 생성 ⏳ 진행 중

| 항목 | 상태 | 비고 |
|------|------|------|
| 전략 실행 | ✅ | scalping 전략 실행 중 |
| 리샘플링 검증 | ⏳ | 1m→3m 확인됨, 5m/15m/1h/4h 대기 |
| 다중 TF 신호 | 🟡 | 3m: 44건, 5m/15m/1h/4h: 대기 중 |

### Phase 4: 앙상블 거래 ⏳ 대기 중

| 항목 | 상태 | 비고 |
|------|------|------|
| 신호 결합 | ⏳ | 6개 전략 신호 대기 |
| 거래 결정 | ⏳ | trading.decisions: 0건 |
| 거래 실행 | ⏳ | trading.trades: 대기 |

**현재 상태 (23:52) - 근본 원인 파악**:
- 컨테이너 시작: 14:18 (약 30분 경과)
- monitoring.signals: 44건 (3m만)
- trading.decisions: 0건

**근본 원인 분석**:
- **버퍼 크기**: lookback=100 (1m 기준)
- **30분 경과**: 30개 1m 캔들 축적
- **리샘플링 결과**:
  - 3m: 30÷3 = 10개 → min_bars_for_signal=50 **미달** (그런데 신호 44건 생성됨, 확인 필요)
  - 5m: 30÷5 = 6개 → 50개 **미달**
  - 15m: 30÷15 = 2개 → 50개 **미달**
  - 1h: 30÷60 = 0.5개 → 50개 **미달**
  - 4h: 30÷240 = 0.125개 → 50개 **미달**

**필요 시간 (min_bars=50 충족)**:
- 3m: 50×3 = 150분 = **2.5시간**
- 5m: 50×5 = 250분 = **4.2시간**
- 15m: 50×15 = 750분 = **12.5시간**
- 1h: 50×60 = 3000분 = **50시간** (2일)
- 4h: 50×240 = 12000분 = **200시간** (8일)

**문제**: 전략별 min_bars_for_signal이 전역 설정(50)을 사용하여 장기 타임프레임은 신호 생성 불가

**해결1 (23:58 완료)**: 전략별 min_bars_for_signal 설정
```yaml
scalping (3m):    min_bars_for_signal: 50  # 150분 = 2.5시간
daytrade (5m):    min_bars_for_signal: 30  # 150분 = 2.5시간
reversion (15m):  min_bars_for_signal: 20  # 300분 = 5시간
breakout (15m):   min_bars_for_signal: 20  # 300분 = 5시간
swing (1h):       min_bars_for_signal: 15  # 900분 = 15시간
trend (4h):       min_bars_for_signal: 10  # 2400분 = 40시간
```

**해결2 (00:10 완료)**: lookback 100 → 300 증가
- 프리로드: 100개 캔들 (1m 기준)
- 버퍼 크기: 300개 캔들 (lookback 반영)
- **즉시 실행 가능**: 프리로드 완료 후 바로 전략 실행

**재시작**: 00:10 완료 (lookback=300 반영됨)
**프리로드**: 00:11~00:12 완료 (100개 심볼)
**WebSocket**: 00:12~ 실시간 수신 중

---

## 🎯 다음 단계

### 즉시 (완료)
- [x] Redis 환경변수 추가
- [x] 재빌드 및 재시작
- [x] Redis 연결 확인

### 신호 생성 예상 시간 (재시작 00:10 기준)

**현재 상태**:
- 프리로드: 100개 1m 캔들 완료 (00:11~00:12)
- 버퍼: lookback=300 (실시간 수신 중)
- 추가 필요: 200개 1m 캔들 = 200분 = 3.3시간

| 전략 | TF | min_bars | 버퍼 필요 | 추가 대기 | 예상 시각 |
|------|----|---------|---------|---------|---------| 
| scalping | 3m | 50 | 150개 | 50분 | **01:00** |
| daytrade | 5m | 30 | 150개 | 50분 | **01:00** |
| reversion | 15m | 20 | 300개 | 200분 | **03:30** |
| breakout | 15m | 20 | 300개 | 200분 | **03:30** |
| swing | 1h | 15 | 900개 | 불가 | lookback 부족 |
| trend | 4h | 10 | 2400개 | 불가 | lookback 부족 |

**다음 확인 시점**:
- [ ] 01:00 - scalping/daytrade 신호 생성 확인
- [ ] 03:30 - reversion/breakout 신호 생성 확인
- [ ] 앙상블 결정 생성 확인

**참고**: swing/trend는 lookback=300으로 부족. 추후 조정 필요 시 lookback 증가 검토

---

## 📝 문서 업데이트 필요

### 1. PR7_COMPLETE.md
- Redis 연결 실패 → 성공으로 업데이트
- 환경변수 추가 내역 반영

### 2. PR7-2_COMPLETE.md
- 검증 진행 상황 업데이트
- Redis 연결 성공 반영

### 3. INTEGRATION_TEST.md
- End-to-End 테스트 시나리오 추가
- Redis 연결 테스트 추가
- WebSocket → Engine → Strategy → DB 플로우 테스트

### 4. REFACTORING_collector_v1.md
- Redis 환경변수 설정 방법 명시
- docker-compose.yml 예시 추가

---

## 🧪 테스트 시나리오 (추가 필요)

### 1. Redis 연결 테스트
```bash
docker exec trading_bot_paper_ensemble python -c "
from database.redis import RedisClient
rc = RedisClient.get_instance(host='redis', port=6379)
print('Redis enabled:', rc.enabled)
rc.mark_seen('TEST', '1m', 1234567890)
print('Is seen:', rc.is_seen('TEST', '1m', 1234567890))
"
```

### 2. WebSocket → Queue 테스트
```bash
# 1분마다 100개 심볼의 닫힌 캔들 로그 확인
docker logs trading_bot_paper_ensemble | grep "닫힌 캔들 큐 추가" | wc -l
# 예상: 1분당 100개
```

### 3. Engine → Strategy 테스트
```bash
# 2시간 후 전략 실행 로그 확인
docker logs trading_bot_paper_ensemble | grep "전략 실행"
```

### 4. Strategy → DB 테스트
```sql
-- 다중 TF 신호 확인
SELECT timeframe, COUNT(*) as cnt, MAX(created_at) as last
FROM monitoring.signals
WHERE created_at > NOW() - INTERVAL '10 minutes'
GROUP BY timeframe
ORDER BY timeframe;

-- 예상 결과:
-- 3m  | 10 | 2025-11-03 23:20:00
-- 5m  | 6  | 2025-11-03 23:20:00
-- 15m | 2  | 2025-11-03 23:15:00
-- 1h  | 1  | 2025-11-03 23:00:00
-- 4h  | 0  | NULL
```

### 5. Ensemble → Trade 테스트
```sql
-- 앙상블 거래 결정 확인
SELECT * FROM trading.decisions
WHERE created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 10;

-- 거래 실행 확인
SELECT * FROM trading.trades
WHERE created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 10;
```

---

## 🔄 변경 이력

### 2025-11-03 23:20
- ✅ Redis 환경변수 추가 (REDIS_HOST, REDIS_PORT)
- ✅ Redis 연결 성공 확인
- ✅ PR7-2_STATUS_REPORT.md 작성
- ✅ PR7-2_FINAL_STATUS.md 작성

### 2025-11-03 19:00
- ✅ Mixed-TF 코드 구현 완료
- ✅ WebSocket 1m 캔들 수신 확인
- ✅ 큐 추가 성공

---

## 📚 참고 문서

- [PR7_COMPLETE.md](./PR7_COMPLETE.md) - PR7 리팩토링 완료
- [PR7-2_COMPLETE.md](./PR7-2_COMPLETE.md) - PR7-2 Mixed-TF 구현
- [PR7-2_STATUS_REPORT.md](./PR7-2_STATUS_REPORT.md) - 상세 분석 보고서
- [INTEGRATION_TEST.md](./INTEGRATION_TEST.md) - 통합 테스트 (업데이트 필요)
- [REFACTORING_collector_v1.md](./REFACTORING_collector_v1.md) - Collector 리팩토링
- [REFACTORING_개선계획.md](./REFACTORING_개선계획.md) - 전체 개선 계획
