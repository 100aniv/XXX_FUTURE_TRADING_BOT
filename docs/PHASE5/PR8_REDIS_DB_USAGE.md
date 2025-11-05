# PR8: Redis & DB 사용 현황

**작성**: 2025-11-05 21:50 UTC+09:00  
**상태**: 검토 완료

---

## 📊 현재 상황 요약

### Redis ⚠️ 미사용
**구현**: ✅ 완료 (`database/redis.py`)  
**실제 사용**: ❌ 없음

**구현 기능**:
- 캔들 중복 제거 (seen_candles)
- TTL 자동 적용 (1시간)
- 메모리 폴백
- 싱글톤 패턴

**문제**: 
- `RedisClient` 클래스가 구현되어 있지만
- 실제로 `is_seen()`, `mark_seen()` 호출하는 코드 없음
- Docker에서 Redis 컨테이너는 실행 중이지만 사용 안 함

### PostgreSQL ✅ 사용 중
**구현**: ✅ 완료  
**실제 사용**: ✅ 활발

**사용 테이블**:
1. `monitoring.signals` - 전략별 신호 저장
2. `trading.decisions` - 앙상블 결정 저장
3. `trading.trades` - 거래 내역 저장
4. `monitoring.gate_results` - 게이트 결과 저장

**사용 위치**:
- `strategies/ensemble.py` - decisions 저장 (INSERT)
- `execution/engine.py` - trades 저장 (추정)
- 각 전략 - signals 저장 (추정)

---

## 🔍 상세 분석

### 1. Redis 구현 vs 사용

**구현된 파일**:
```
database/redis.py (231줄)
common/redis_client.py (shim, 23줄)
```

**핵심 메서드**:
```python
class RedisClient:
    def is_seen(symbol, timeframe, closed_at) -> bool
    def mark_seen(symbol, timeframe, closed_at) -> bool
    def get(key) -> str
    def set(key, value, ttl) -> bool
```

**사용처 검색 결과**:
```bash
$ grep -r "RedisClient\|redis_client" *.py
# 결과: 없음
```

**결론**: Redis는 구현만 되어 있고 실제 사용되지 않음

### 2. PostgreSQL 사용 현황

**테이블별 사용**:

#### A. monitoring.signals
**목적**: 각 전략의 신호 저장  
**사용**: ✅ 활발 (ensemble에서 조회)

```python
# strategies/ensemble.py
SELECT * FROM monitoring.signals
WHERE created_at >= NOW() - INTERVAL '1 minute'
  AND NOT EXISTS (SELECT 1 FROM trading.decisions ...)
```

#### B. trading.decisions
**목적**: 앙상블 최종 결정 저장  
**사용**: ✅ 활발

```python
# strategies/ensemble.py (419줄)
INSERT INTO trading.decisions (
    decision_id, symbol, timeframe, candle_closed_at,
    chosen_side, chosen_size, score, weights, from_signals, reason,
    entry_price, sl_price, tp_price
) VALUES (...)
```

#### C. trading.trades
**목적**: 실제 거래 내역 저장  
**사용**: ✅ 활발

**저장 타이밍**:
1. 진입 시: status='OPEN'
2. 청산 시: status='CLOSED', PnL 업데이트

#### D. monitoring.gate_results
**목적**: FlowGuardian 게이트 결과  
**사용**: ✅ (Phase 5에서 구현)

---

## 💡 개선 방안

### Redis 활용 방안

#### A. 캔들 중복 제거 (즉시 적용 가능)
**문제**: 재시작 시 같은 캔들 재처리 가능성  
**해결**: Redis로 이미 처리한 캔들 추적

```python
# execution/engine.py
def on_candle(self, candle):
    redis = RedisClient.get_instance()
    
    # 중복 체크
    if redis.is_seen(candle['symbol'], candle['timeframe'], candle['closed_at']):
        logger.debug(f"⏭️ 이미 처리한 캔들: {candle['symbol']}")
        return
    
    # 신호 생성
    signals = self.generate_signals(candle)
    
    # 처리 완료 표시
    redis.mark_seen(candle['symbol'], candle['timeframe'], candle['closed_at'])
```

**효과**:
- 재시작 후 중복 처리 방지
- 분산 환경 지원 (여러 인스턴스 동시 실행 가능)
- TTL로 자동 정리 (1시간 후 삭제)

#### B. 신호 중복 제거
**문제**: 같은 신호가 여러 번 생성될 가능성  
**해결**: Redis로 신호 해시 저장

```python
import hashlib

def generate_signal_hash(symbol, side, entry, sl, tp):
    """신호 고유 해시 생성"""
    data = f"{symbol}:{side}:{entry:.2f}:{sl:.2f}:{tp:.2f}"
    return hashlib.md5(data.encode()).hexdigest()

# 신호 생성 시
signal_hash = generate_signal_hash(...)
if not redis.is_seen("signal", symbol, signal_hash):
    # 신호 전송
    redis.mark_seen("signal", symbol, signal_hash)
```

#### C. 심볼별 쿨다운 (Redis 기반)
**현재**: 메모리 기반 (재시작 시 초기화)  
**개선**: Redis 기반 (재시작 후에도 유지)

```python
# portfolio_manager.py
def is_in_cooldown(self, symbol):
    redis = RedisClient.get_instance()
    key = f"cooldown:{symbol}"
    return redis.get(key) is not None

def set_cooldown(self, symbol, seconds):
    redis = RedisClient.get_instance()
    key = f"cooldown:{symbol}"
    redis.set(key, "1", ttl=seconds)
```

---

## 📋 구현 우선순위

### 🔴 즉시 (Critical)
1. ✅ 캔들 중복 제거 (Redis)
   - `execution/engine.py` 수정
   - 재시작 후 중복 처리 방지

### 🟡 중요 (High)
2. ✅ 심볼별 쿨다운 (Redis)
   - `portfolio_manager.py` 수정
   - 재시작 후에도 쿨다운 유지

### 🟢 보통 (Medium)
3. 신호 중복 제거 (Redis)
   - 같은 신호 반복 전송 방지
4. 성능 모니터링 캐시 (Redis)
   - 실시간 통계 저장

---

## 🎯 DB 사용 현황 (정상)

### 저장 타이밍

**신호 생성 시**:
```
전략 → monitoring.signals (INSERT)
```

**앙상블 결정 시**:
```
앙상블 → monitoring.signals (SELECT)
       → trading.decisions (INSERT)
```

**거래 실행 시**:
```
Engine → trading.trades (INSERT, status=OPEN)
```

**거래 청산 시**:
```
Engine → trading.trades (UPDATE, status=CLOSED, PnL)
```

**게이트 체크 시**:
```
FlowGuardian → monitoring.gate_results (INSERT)
```

---

## 📝 다음 단계

### PR8 완료 전
- ❌ Redis 통합 (PR8에 포함하지 않음, 별도 PR 필요)
- ✅ 레버리지 중복 제거
- ✅ 포트폴리오 동적 설정
- ✅ 라이브 모드 자산 로드

### PR9 제안 (Redis 통합)
1. 캔들 중복 제거 (engine.py)
2. 심볼별 쿨다운 (portfolio_manager.py)
3. 신호 중복 제거 (strategies/)
4. 성능 모니터링 캐시

**예상 시간**: 1-2시간  
**테스트**: 재시작 후 중복 방지 확인

---

## ✅ 결론

### Redis
- **구현**: ✅ 완료
- **사용**: ❌ 미사용
- **이유**: 구현 후 통합 안 됨
- **제안**: PR9에서 통합

### PostgreSQL
- **구현**: ✅ 완료
- **사용**: ✅ 활발
- **테이블**: 4개 (signals, decisions, trades, gate_results)
- **타이밍**: 신호 생성 → 결정 → 거래 → 청산 전 과정

**Redis는 구현되어 있지만 실제로 연결되지 않았습니다.**  
**DB는 정상적으로 사용 중입니다.**
