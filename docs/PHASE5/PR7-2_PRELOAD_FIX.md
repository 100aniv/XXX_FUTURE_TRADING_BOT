# PR7-2: 프리로드 큐 드롭 문제 완벽 해결

## 📋 요약

100심볼 × 100캔들 프리로드가 큐 사이즈 제한으로 절반만 전달되던 문제를 근본적으로 해결.

## 🔍 근본 원인 분석

### 문제 증상
- 프리로드: 100심볼 × 100캔들 = 10,000개 시도
- 큐 제한: `maxsize=5000`
- 결과: 5,000개만 저장, 나머지 5,000개 드롭
- 로그: `⚠️ 프리로드 큐 Full! LINKUSDT 캔들 추가 실패`

### 디버깅 과정
1. **Docker 이미지 캐시 문제 발견**
   - `docker-compose build`로 빌드했으나 코드 반영 안됨
   - 해결: `docker builder prune -af` + `--no-cache` 빌드
   
2. **큐 사이즈 로깅 추가**
   ```python
   # adapters/__init__.py
   queue_size = ws.candle_queue.qsize()
   logger.info(f"✅ [{idx}/{len(symbols)}] {sym} 프리로드 완료: {len(candles)}개 캔들 | 큐 사이즈: {queue_size}")
   
   final_queue_size = ws.candle_queue.qsize()
   logger.info(f"🔍 [DEBUG] 프리로드 후 최종 큐 사이즈: {final_queue_size}")
   ```

3. **stream() 시작 전 큐 상태 확인**
   ```python
   # engine.py
   queue_size_before = feed.candle_queue.qsize()
   logger.info(f"🔍 [DEBUG] stream() 시작 전 큐 사이즈: {queue_size_before}")
   ```

4. **첫 5개 캔들 포맷 검증**
   ```python
   if candle_count <= 5:
       logger.info(f"🔍 [DEBUG] 캔들 #{candle_count} 포맷: symbol={candle.get('symbol')}, time={candle.get('time')}, close={candle.get('close')}")
   ```

## 🔧 해결 방법

### 1. 큐 사이즈 확장

**파일:** `collectors/websocket_collector.py`

```python
# 변경 전
self.candle_queue = queue.Queue(maxsize=5000)

# 변경 후
# 프리로드: 100심볼 × 100캔들 = 10,000 + 실시간 버퍼 5,000 = 15,000
self.candle_queue = queue.Queue(maxsize=15000)
```

**근거:**
- 프리로드: 10,000개
- 실시간 버퍼: 5,000개 (WebSocket 수신 중 처리 지연 대비)
- 총 필요: 15,000개

### 2. 디버깅 로깅 (검증 후 제거)

**추가한 로깅:**
- 프리로드 진행 상황 (심볼별 큐 사이즈)
- 프리로드 완료 후 최종 큐 사이즈
- stream() 시작 전 큐 사이즈
- 첫 5개 캔들 포맷
- 100개 처리 후 큐 사이즈

**제거 이유:**
- 검증 완료 후 불필요한 로그 제거
- 운영 환경 로그 깔끔하게 유지

## ✅ 검증 결과

### 테스트 환경
- Docker 완전 재빌드: `docker builder prune -af` + `--no-cache`
- 재시작 시간: 2025-11-04 01:06

### 로그 증거

```
2025-11-04 01:06:32,741 [INFO] ✅ [100/100] DASHUSDT 프리로드 완료: 100개 캔들 | 큐 사이즈: 10000
2025-11-04 01:06:32,741 [INFO] ✅ 전체 심볼 프리로드 완료: 100/100개 성공
2025-11-04 01:06:32,742 [INFO] 🔍 [DEBUG] 프리로드 후 최종 큐 사이즈: 10000
2025-11-04 01:06:32,742 [INFO] ✅ 전체 심볼 프리로드 완료
2025-11-04 01:06:32,742 [INFO] 🔍 [DEBUG] stream() 시작 전 큐 사이즈: 10000
2025-11-04 01:06:32,743 [INFO] 🔍 [DEBUG] feed.stream() 루프 시작...
2025-11-04 01:06:32,743 [INFO] 🔍 [DEBUG] 캔들 #1 포맷: symbol=AMBUSDT, time=1762180020000, close=0.001188
2025-11-04 01:06:32,744 [INFO] 💓 [ENSEMBLE] 상태: 캔들 1개 | 활성 포지션: 0개 | 총 거래: 0건 | Equity: $50,000
...
2025-11-04 01:06:37,504 [INFO] 🔍 [DEBUG] 100개 캔들 처리 후 큐 사이즈: 9900
```

### 검증 항목

| 항목 | 기대값 | 실제값 | 상태 |
|------|--------|--------|------|
| 프리로드 심볼 수 | 100 | 100 | ✅ |
| 심볼당 캔들 수 | 100 | 100 | ✅ |
| 최종 큐 사이즈 | 10,000 | 10,000 | ✅ |
| stream() 시작 전 | 10,000 | 10,000 | ✅ |
| 100개 처리 후 | 9,900 | 9,900 | ✅ |
| 캔들 포맷 | 정상 | symbol/time/close 정상 | ✅ |
| 큐 드롭 | 0 | 0 | ✅ |

## 📊 성능 영향

### 메모리
- 이전: 5,000 캔들 큐
- 이후: 15,000 캔들 큐
- 증가: 약 10,000개 × 200 bytes = ~2MB (무시 가능)

### 처리 속도
- 영향 없음: 큐는 메모리 기반으로 빠름
- 프리로드 → stream() 전환: 즉시

## 🚨 발견된 추가 문제

### daytrade/reversion/breakout 전략 에러

```
[ERROR] ❌ [daytrade] 전략 오류: single positional indexer is out-of-bounds
[ERROR] ❌ [reversion] 전략 오류: single positional indexer is out-of-bounds
[ERROR] ❌ [breakout] 전략 오류: single positional indexer is out-of-bounds
```

**상태:**
- scalping 전략은 정상 작동
- 다른 전략들의 데이터 인덱싱 문제
- 별도 이슈로 추적 필요

## 🔄 다음 단계

1. **디버깅 로깅 제거** ✅ (완료)
2. **Docker 재빌드 및 재시작** (필요)
3. **전략 에러 수정** (별도 PR)
4. **신호 생성 모니터링** (최소 1시간)

## 📝 변경 파일

```
collectors/websocket_collector.py       # 큐 사이즈 15000
execution/adapters/__init__.py           # 프리로드 로직
execution/engine.py                      # 디버깅 로깅 제거
docs/PHASE5/PR7-2_PRELOAD_FIX.md        # 이 문서
```

## ✅ 완료 기준

- [x] 근본 원인 파악
- [x] 큐 사이즈 확장
- [x] 디버깅 로깅 추가
- [x] Docker 완전 재빌드
- [x] 10,000개 프리로드 검증
- [x] stream() 정상 작동 확인
- [x] 디버깅 로깅 제거
- [ ] 최종 재배포 및 모니터링

---
**작성일:** 2025-11-04 01:10
**상태:** ✅ 디버깅 완료, 재배포 대기
