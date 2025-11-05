# 데이터 수집 모듈 분석 (Data Collection Analysis)

**작성일**: 2025-10-30  
**분석 범위**: `collectors/` 폴더 전체

---

## 📋 현재 구조

### 1. REST API 수집 (`rest_collector.py`)

**기능**:
- `fetch_history()`: 히스토리 캔들 로드
- `fetch_all_symbols()`: 전체 종목 조회
- `fetch_ticker_24h()`: 24시간 통계
- `fetch_top_volume_symbols()`: 거래량 상위 N개

**코드 구조**:
```python
def fetch_history(symbol: str, timeframe: str, limit: int = 500):
    client = BinanceClient()  # ❌ 매번 새로 생성
    klines = client.futures_klines(...)
    # DataFrame 생성 → dict 변환
    return candles
```

### 2. WebSocket 수집 (`websocket_collector.py`)

**기능**:
- 실시간 캔들 데이터 수집
- 중복 제거 (dedup)
- 누락 캔들 자동 복구 (backfill)

**코드 구조**:
```python
class WebSocketCollector:
    def __init__(self):
        self.seen_candles = set()  # ❌ 무한정 증가
        self.candle_queue = Queue(maxsize=5000)
    
    def _on_message(self, ws, message):
        # 중복 제거
        if candle_key in self.seen_candles:
            return
        self.seen_candles.add(candle_key)  # ❌ 메모리 누수
        
        # 큐에 추가
        try:
            self.candle_queue.put_nowait(candle)
        except:
            pass  # ❌ 큐 Full 시 데이터 손실
```

---

## ❌ 발견된 문제점

### 문제 #1: REST API Client 재사용 안됨

**위치**: `rest_collector.py` L39, L109, L145, L166, L204

**증상**:
```python
def fetch_history(...):
    client = BinanceClient()  # 매번 새로 생성
```

**영향**:
- 연결 오버헤드 (매번 인증, 연결 설정)
- Rate Limit에 불리 (연결당 limit이 아닌 IP당)
- 성능 저하

**PHASE5 문서 연관**:
- "데이터 간극 3.7%" - Rate Limit 초과로 인한 요청 실패 가능

---

### 문제 #2: WebSocket seen_candles 메모리 누수

**위치**: `websocket_collector.py` L77, L175, L330

**증상**:
```python
self.seen_candles = set()  # 무한정 증가
self.seen_candles.add(candle_key)
```

**영향**:
- 24시간 운영 시 메모리 누적
- 100개 심볼 × 3분봉 → 하루 48,000개 캔들 → 약 10MB
- 일주일이면 70MB, 한달이면 300MB

**PHASE5 문서 연관**:
- "메모리 사용: 24시간 운영 시 1.8GB 누적"

**근본 원인**:
- TTL(Time To Live) 없음
- 오래된 캔들 키를 제거하지 않음

---

### 문제 #3: 큐 Full 시 데이터 손실

**위치**: `websocket_collector.py` L184-188, L328-333

**증상**:
```python
try:
    self.candle_queue.put_nowait(candle)
except:
    pass  # ❌ 에러 로그 없음, 데이터 버림
```

**영향**:
- 프리로드 시 100개 심볼 × 100개 캔들 = 10,000개
- 큐 크기 5,000개 → 5,000개 데이터 손실
- **실제 발생**: 51번째 심볼부터 queue.Full 에러

**PHASE5 문서 연관**:
- "데이터 간극: 5분 데이터 3.7% 누락"

**해결 완료**:
- 프리로드 시 큐 대신 직접 콜백 호출로 변경 ✅

---

### 문제 #4: 백필 실패 시 무시

**위치**: `websocket_collector.py` L332-333

**증상**:
```python
try:
    self.candle_queue.put_nowait(backfilled_candle)
    self.seen_candles.add(candle_key)
except:
    pass  # ❌ 에러 로그 없음
```

**영향**:
- 누락 캔들을 REST API로 가져왔는데 버림
- 복구 실패를 추적할 수 없음

---

### 문제 #5: 타임프레임 매핑 불완전

**위치**: `websocket_collector.py` L288-289

**증상**:
```python
tf_map = {"1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "1h": 3600000}
tf_ms = tf_map.get(timeframe, 300000)  # 기본값: 5m
```

**영향**:
- 4h, 1d 같은 타임프레임은 기본값(5m)으로 처리
- 백필 로직이 잘못된 Gap 계산

---

### 문제 #6: 시간 동기화 없음

**위치**: 전체 모듈

**증상**:
- 로컬 시간과 Binance 서버 시간 불일치 가능성
- 타임스탬프 보정 없음

**PHASE5 문서 연관**:
- "시간 동기화 오류: 최대 47초 차이"

---

### 문제 #7: DataFrame → dict 변환 비효율

**위치**: `rest_collector.py` L43-60

**증상**:
```python
df = pd.DataFrame(klines, ...)  # 메모리 할당
for _, r in df.iterrows():  # ❌ 느린 반복
    candles.append({...})  # 중복 메모리
```

**영향**:
- 불필요한 DataFrame 생성
- iterrows()는 매우 느림 (권장: itertuples() 또는 to_dict())
- 메모리 2배 사용 (DataFrame + dict)

---

## ✅ 개선 방안

### 개선 #1: Client 싱글톤

**목표**: BinanceClient 재사용

```python
# rest_collector.py
_client_instance = None

def get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = BinanceClient()
    return _client_instance

def fetch_history(symbol: str, timeframe: str, limit: int = 500):
    client = get_client()  # ✅ 재사용
    ...
```

**효과**:
- 연결 오버헤드 제거
- Rate Limit 효율성 개선

---

### 개선 #2: seen_candles TTL 적용

**목표**: 메모리 누수 방지

```python
# websocket_collector.py
from collections import deque
from datetime import datetime, timedelta

class WebSocketCollector:
    def __init__(self):
        self.seen_candles = {}  # {candle_key: timestamp}
        self.ttl = timedelta(hours=1)  # 1시간 TTL
    
    def _cleanup_old_candles(self):
        """오래된 캔들 키 제거"""
        now = datetime.now()
        expired_keys = [
            k for k, ts in self.seen_candles.items()
            if now - ts > self.ttl
        ]
        for k in expired_keys:
            del self.seen_candles[k]
    
    def _on_message(self, ws, message):
        self._cleanup_old_candles()  # 주기적 정리
        ...
```

**효과**:
- 메모리 사용량 일정 유지
- 1시간 이상 된 캔들 자동 제거

---

### 개선 #3: 큐 Full 시 경고 + 재시도

**목표**: 데이터 손실 방지

```python
# websocket_collector.py
def _on_message(self, ws, message):
    try:
        self.candle_queue.put_nowait(candle)
    except queue.Full:
        logger.warning(f"⚠️ 큐 Full! 1초 대기 후 재시도: {symbol}")
        time.sleep(0.1)
        try:
            self.candle_queue.put(candle, timeout=1.0)
        except:
            logger.error(f"❌ 큐 Full로 데이터 손실: {symbol} {closed_at}")
```

**효과**:
- 데이터 손실 최소화
- 손실 발생 시 로그로 추적

---

### 개선 #4: 타임프레임 동적 계산

**목표**: 모든 타임프레임 지원

```python
def _parse_timeframe_ms(timeframe: str) -> int:
    """타임프레임을 밀리초로 변환"""
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    
    multipliers = {
        'm': 60 * 1000,
        'h': 60 * 60 * 1000,
        'd': 24 * 60 * 60 * 1000,
        'w': 7 * 24 * 60 * 60 * 1000
    }
    
    return value * multipliers.get(unit, 60 * 1000)
```

**효과**:
- 모든 타임프레임 지원
- 유지보수 용이

---

### 개선 #5: DataFrame 변환 최적화

**목표**: 메모리 + 성능 개선

```python
def fetch_history(symbol: str, timeframe: str, limit: int = 500):
    client = get_client()
    klines = client.futures_klines(...)
    
    # ✅ DataFrame 없이 직접 변환
    candles = []
    for k in klines:
        candles.append({
            "time": int(k[0]),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5])
        })
    
    return candles
```

**효과**:
- 메모리 50% 절감
- 속도 2-3배 향상 (DataFrame 생성 비용 제거)

---

## 🧪 테스트 계획

### 테스트 #1: REST API 성능 테스트

**목표**: Client 재사용 효과 측정

```python
# 테스트 시나리오
1. 100회 fetch_history() 호출 (재사용 X)
2. 100회 fetch_history() 호출 (재사용 O)
3. 시간 비교
```

**예상 결과**:
- 재사용 시 20-30% 성능 향상

---

### 테스트 #2: WebSocket 메모리 누수 테스트

**목표**: seen_candles 메모리 증가 측정

```python
# 테스트 시나리오
1. 24시간 시뮬레이션 (100개 심볼, 3분봉)
2. 메모리 사용량 추적
3. TTL 적용 전후 비교
```

**예상 결과**:
- TTL 적용 전: 선형 증가 (300MB/월)
- TTL 적용 후: 일정 유지 (10MB)

---

### 테스트 #3: 큐 Full 시나리오 테스트

**목표**: 데이터 손실 방지 검증

```python
# 테스트 시나리오
1. 큐 크기 100으로 제한
2. 200개 캔들 전송
3. 손실 개수 확인
```

**예상 결과**:
- 재시도 없음: 100개 손실
- 재시도 적용: 0-5개 손실

---

## 📊 우선순위

| 순위 | 개선 항목 | 난이도 | 효과 | 작업 시간 |
|------|----------|--------|------|----------|
| 1 | seen_candles TTL | 낮음 | 높음 | 1h |
| 2 | 큐 Full 재시도 | 낮음 | 중간 | 30m |
| 3 | Client 싱글톤 | 낮음 | 중간 | 20m |
| 4 | DataFrame 최적화 | 낮음 | 중간 | 30m |
| 5 | 타임프레임 동적 계산 | 낮음 | 낮음 | 20m |

**총 예상 시간**: 약 2.5시간

---

## 🎯 다음 단계

1. **우선순위 1**: seen_candles TTL 구현 + 테스트
2. **우선순위 2**: 큐 Full 재시도 구현 + 테스트
3. **우선순위 3**: Client 싱글톤 구현 + 성능 테스트
4. **전체 통합 테스트**: 데이터 수집 플로우 검증

---

## 📝 참고

- PHASE5/REFACTORING_data_collector_v1.md
- PHASE5/INTEGRATION_TEST_FINDINGS.md
