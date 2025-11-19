# PHASE18-2: run_id 네임스페이스 전역 적용 설계

**작성일**: 2025-11-19  
**목표**: Redis/DB/로그를 run_id 기준으로 완전 격리  
**우선순위**: P0 (필수)  
**진입 조건**: PHASE18-1 완료 ✅

---

## 1. Objective

### 1.1 핵심 목표

**"실행(run) 간 상태 완전 격리를 통해, 동시 실행/멀티 봇/멀티 전략 환경에서도 안전하게 운영 가능한 인프라 구축"**

### 1.2 run_id의 역할

**run_id**: 단일 실행 인스턴스를 식별하는 고유 ID

```
포맷: YYYYMMDD_HHMMSS_xxxx
예시: 20251119_140530_a7f3
```

**용도**:
1. **실행 간 격리**: 서로 다른 run_id는 Redis/DB/로그에서 완전히 분리
2. **멀티 실행 지원**: 동시에 여러 봇 실행 시 상태 충돌 방지
3. **이력 추적**: run_id 기반으로 과거 실행 결과 조회/분석
4. **디버깅**: 문제 발생 시 해당 run_id의 모든 상태를 재구성 가능

### 1.3 env (실행 환경)와의 관계

**env**: 실행 모드 (backtest / paper / live)

**env와 run_id의 계층 구조**:
```
env (실행 모드)
  ├─ run_id_1 (실행 인스턴스 1)
  ├─ run_id_2 (실행 인스턴스 2)
  └─ run_id_3 (실행 인스턴스 3)
```

**네임스페이스 규칙**:
- 동일 env 내에서도 run_id로 격리
- 서로 다른 env는 완전히 분리된 네임스페이스

**예시**:
```
Redis 키:
- cooldown:backtest:20251119_140530_a7f3:BTCUSDT:scalping
- cooldown:paper:20251119_141030_b8e4:BTCUSDT:scalping
- cooldown:live:20251119_141530_c9f5:BTCUSDT:scalping

→ 동일 심볼/전략이지만 env + run_id가 다르므로 독립적으로 관리
```

### 1.4 향후 멀티 심볼/멀티 전략/멀티 봇 시 이득

**시나리오 1: 멀티 심볼 백테스트**
```bash
# 동시에 3개 심볼 백테스트 (서로 다른 터미널)
python run_backtest.py --symbol BTCUSDT --timeframe 1m --days 7
python run_backtest.py --symbol ETHUSDT --timeframe 1m --days 7
python run_backtest.py --symbol BNBUSDT --timeframe 1m --days 7

→ 각각 다른 run_id → Redis 키 충돌 없음
```

**시나리오 2: Paper + Live 동시 운영**
```bash
# Paper 모드 테스트 (새 전략 검증)
python run_paper.py --strategy new_scalping --duration-hours 1

# Live 모드 (기존 전략 실운영)
python run_live.py --strategy scalping --duration-hours 24

→ env가 다르므로 완전 격리 (paper와 live의 cooldown이 섞이지 않음)
```

**시나리오 3: 앙상블 멀티 전략**
```python
# 미래 PHASE19+: 앙상블 프레임워크
ensemble.run([
    Strategy("scalping", weight=0.3),
    Strategy("trend", weight=0.4),
    Strategy("reversion", weight=0.3),
])

→ 각 전략의 cooldown/guard 상태가 run_id로 격리
→ 전략 간 간섭 없음
```

---

## 2. 네임스페이스 규칙

### 2.1 Redis 키 네임스페이스

**일반 규칙**:
```
{domain}:{env}:{run_id}:{symbol}[:{extra}]
```

**domain**: 키의 용도 (cooldown, candle_seen, signal 등)  
**env**: 실행 모드 (backtest, paper, live)  
**run_id**: 실행 인스턴스 ID  
**symbol**: 심볼 (BTCUSDT 등)  
**extra**: 추가 식별자 (strategy, timeframe 등)

### 2.2 구체적 Redis 키 예시

| domain | 현재 키 (PHASE17) | 변경 후 (PHASE18-2) |
|--------|------------------|-------------------|
| **cooldown** | `cooldown:{symbol}_{strategy}` | `cooldown:{env}:{run_id}:{symbol}:{strategy}` |
| **candle_seen** | `candle:seen:{symbol}:{timeframe}:{timestamp}` | `candle:seen:{env}:{run_id}:{symbol}:{timeframe}:{timestamp}` |
| **signal** | `signal:{symbol}` | `signal:{env}:{run_id}:{symbol}` |

**예시**:
```python
# Before (PHASE17)
cooldown:BTCUSDT_scalping
candle:seen:BTCUSDT:1m:1700000000

# After (PHASE18-2)
cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping
candle:seen:paper:20251119_140530_a7f3:BTCUSDT:1m:1700000000
```

### 2.3 호환성 규칙

**기존 구조와의 호환성**:
- 기존 키는 점진적으로 deprecate (PHASE18-2에서 강제 변경)
- Fallback 전략 없음 (clean-state로 시작하므로 기존 키 무시)

**이유**:
- PHASE18-1에서 --clean-state 플래그로 실행 전 Redis 초기화 보장
- 기존 키가 남아있어도 새 네임스페이스로 격리되므로 충돌 없음

---

## 3. run_id 생성/전달 설계

### 3.1 run_id 생성 위치

**엔트리 포인트에서 생성**:
- `scripts/run_paper.py`
- `scripts/run_backtest.py`
- (미래) `scripts/run_live.py`

**생성 함수**: `common.config_loader.generate_run_id()`

```python
def generate_run_id() -> str:
    """
    run_id 생성: YYYYMMDD_HHMMSS_xxxx
    
    Returns:
        str: run_id (예: 20251119_140530_a7f3)
    """
    import secrets
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = secrets.token_hex(2)  # 4자리 hex
    
    return f"{timestamp}_{random_suffix}"
```

### 3.2 run_id 전달 메커니즘

**Config 객체에 주입**:
```python
# scripts/run_paper.py
from common.config_loader import load_config_with_mode, generate_run_id

cfg = load_config_with_mode(mode="paper")

# run_id 생성 및 주입
run_id = generate_run_id()
cfg['run_id'] = run_id
cfg['env'] = 'paper'  # 실행 모드 명시

logger.info(f"🆔 Run ID: {run_id}, Env: {cfg['env']}")
```

**Engine 레이어로 전달**:
```python
# execution/engine.py
def run_trading_engine(config, ...):
    run_id = config.get('run_id', 'unknown')
    env = config.get('env', 'paper')
    
    # Redis 클라이언트에 전달
    redis_client = RedisClient.get_instance(run_id=run_id, env=env)
    
    # 나머지 로직...
```

**전달 흐름**:
```
scripts/run_paper.py
  ↓ (config 주입)
execution/engine.py
  ↓ (생성자 파라미터)
database/RedisClient
  ↓ (키 생성 시 사용)
Redis Keys
```

### 3.3 공통 네임스페이스 유틸

**새 파일 생성**: `common/namespace.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-2: Redis/DB 네임스페이스 유틸
======================================
run_id 기반 키 생성 표준화
"""

def build_redis_key(domain: str, env: str, run_id: str, symbol: str, extra: str = None) -> str:
    """
    Redis 키 생성 (네임스페이스 표준)
    
    Args:
        domain: 키 도메인 (cooldown, candle_seen, signal 등)
        env: 실행 모드 (backtest, paper, live)
        run_id: 실행 인스턴스 ID
        symbol: 심볼 (BTCUSDT 등)
        extra: 추가 식별자 (strategy, timeframe 등)
    
    Returns:
        str: Redis 키 (예: cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping)
    
    Examples:
        >>> build_redis_key('cooldown', 'paper', '20251119_140530_a7f3', 'BTCUSDT', 'scalping')
        'cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping'
    """
    parts = [domain, env, run_id, symbol]
    if extra:
        parts.append(extra)
    
    return ':'.join(parts)


def build_candle_seen_key(env: str, run_id: str, symbol: str, timeframe: str, timestamp: int) -> str:
    """
    Candle dedup 키 생성
    
    Args:
        env: 실행 모드
        run_id: 실행 인스턴스 ID
        symbol: 심볼
        timeframe: 타임프레임 (1m, 3m, 5m 등)
        timestamp: 캔들 타임스탬프
    
    Returns:
        str: Redis 키 (예: candle:seen:paper:20251119_140530_a7f3:BTCUSDT:1m:1700000000)
    """
    return f"candle:seen:{env}:{run_id}:{symbol}:{timeframe}:{timestamp}"


def parse_redis_key(key: str) -> dict:
    """
    Redis 키 파싱 (역변환)
    
    Args:
        key: Redis 키
    
    Returns:
        dict: 파싱 결과 (domain, env, run_id, symbol, extra)
    
    Examples:
        >>> parse_redis_key('cooldown:paper:20251119_140530_a7f3:BTCUSDT:scalping')
        {'domain': 'cooldown', 'env': 'paper', 'run_id': '20251119_140530_a7f3', 
         'symbol': 'BTCUSDT', 'extra': 'scalping'}
    """
    parts = key.split(':')
    
    result = {
        'domain': parts[0] if len(parts) > 0 else None,
        'env': parts[1] if len(parts) > 1 else None,
        'run_id': parts[2] if len(parts) > 2 else None,
        'symbol': parts[3] if len(parts) > 3 else None,
        'extra': ':'.join(parts[4:]) if len(parts) > 4 else None,
    }
    
    return result
```

---

## 4. 적용 범위

### 4.1 1차 적용 범위 (PHASE18-2 필수)

**✅ 반드시 이번 PHASE에서 완료**:

1. **common/namespace.py** (신규)
   - `build_redis_key()` 함수
   - `build_candle_seen_key()` 함수
   - `parse_redis_key()` 함수

2. **database/redis.py** (수정)
   - RedisClient에 run_id, env 파라미터 추가
   - `is_seen()`, `mark_seen()` 메서드 수정
   - candle:seen 키에 네임스페이스 적용

3. **execution/engine.py** (수정)
   - cooldown 키 생성 부분 수정 (3곳)
   - `build_redis_key()` 사용으로 변경

4. **scripts/run_paper.py** (수정)
   - env='paper' 명시적 주입
   - run_id 생성 로직 통일 (generate_run_id 사용)

5. **scripts/run_backtest.py** (수정)
   - env='backtest' 명시적 주입
   - run_id 생성 로직 이미 generate_run_id 사용 중 (확인만)

### 4.2 2차/향후 적용 (문서화만, 코드 변경 X)

**⏭️ PHASE19+ 에서 진행**:

1. **멀티 봇 환경**:
   - 서로 다른 전략을 동시 실행 시 run_id 자동 생성
   - Docker Compose 기반 멀티 컨테이너 구성

2. **앙상블 프레임워크**:
   - 앙상블 내부 전략별로 sub-run_id 할당
   - 계층적 네임스페이스 (ensemble_run_id / strategy_run_id)

3. **Aggregation/리포트**:
   - run_id 기반 필터링 (특정 실행의 결과만 조회)
   - 크로스 run_id 비교 (A/B 테스트)

4. **로그 파일 분리**:
   - logs/{env}/{run_id}/application.log
   - 실행별로 로그 완전 분리

---

## 5. 테스트 전략

### 5.1 단위 테스트

**파일**: `tests/test_phase18_2_run_id_namespace.py`

**시나리오**:
1. `build_redis_key()` 함수 테스트
   - 정상 입력 → 예상 키 생성
   - extra 파라미터 유무 확인

2. `build_candle_seen_key()` 함수 테스트
   - timestamp 포함 키 생성

3. `parse_redis_key()` 함수 테스트
   - 키 → dict 역변환
   - 불완전한 키 처리

### 5.2 통합 테스트

**시나리오 1: 단일 실행 네임스페이스 확인**
```bash
# 짧은 paper 실행 (5분)
python run_paper.py --clean-state --duration-hours 0.083
```

**검증**:
- Redis 키 스캔: 모든 키가 `{domain}:{env}:{run_id}:` 형식
- run_id 일관성: 로그에 출력된 run_id와 Redis 키의 run_id 일치

**시나리오 2: 멀티 실행 격리 확인**
```bash
# 터미널 1: backtest (3분)
python run_backtest.py --clean-state --days 3

# 터미널 2: paper (3분, 동시 실행)
python run_paper.py --clean-state --duration-hours 0.05
```

**검증**:
- Redis 키 분리: backtest run_id와 paper run_id가 다름
- 키 충돌 없음: 동일 심볼이어도 run_id가 다르므로 격리

### 5.3 회귀 테스트

**기존 테스트 재실행**:
- `tests/test_phase17_simple.py` (Multi-position Scaling, Exposure Guard)
- `tests/test_d4x_*.py` (주요 기능 회귀)
- `tests/test_engine_*.py` (엔진 레벨 테스트)

**목적**: run_id 네임스페이스 적용이 기존 기능을 깨지 않았는지 확인

### 5.4 REAL PAPER Smoke Test

**실행**:
```bash
python scripts/run_paper.py \
  --clean-state \
  --duration-hours 0.25 \
  --config configs/scalping/real_paper_12h_v6_1_phase17.yml
```

**검증 항목**:
1. Redis 키 네임스페이스
   - 모든 키가 `{domain}:paper:{run_id}:` 형식
   - run_id 일관성 확인

2. 로그/리포트
   - 로그에 run_id 출력
   - effective_config.yml에 run_id 저장

3. 에러 없음
   - ERROR/CRITICAL 로그 0건
   - Guard 충돌 없음

---

## 6. 예상 이슈 및 대응

### 6.1 DO-NOT-TOUCH 코어 레이어

**문제**: engine.py, portfolio_manager.py 등 코어 레이어 변경 최소화

**대응**:
- engine.py의 cooldown 키 생성 부분만 수정 (3곳)
- 나머지 로직은 건드리지 않음
- 함수 시그니처 변경 최소화

### 6.2 기존 테스트 호환성

**문제**: 기존 테스트가 run_id 없이 작성됨

**대응**:
- 테스트용 MockRedisClient에 run_id 파라미터 추가
- 기본값으로 'test_run_id' 사용
- 기존 테스트 코드 최소 수정

### 6.3 Redis 연결 실패 시

**문제**: Redis 없이도 작동해야 함 (로컬 메모리 fallback)

**대응**:
- RedisClient의 fallback 로직 유지
- 네임스페이스는 Redis 사용 시에만 적용
- 메모리 모드에서는 기존 키 구조 허용

### 6.4 env 값 불일치

**문제**: config의 mode와 env가 다를 수 있음

**대응**:
- env는 run_paper.py/run_backtest.py에서 명시적 설정
- mode는 기존 의미 유지 (실행 방식)
- env는 네임스페이스용 (backtest/paper/live)

---

## 7. Exit Criteria (완료 조건)

### 7.1 필수 조건

✅ **설계 문서 작성 완료**
- 이 문서 (PHASE18-2_RUN_ID_NAMESPACE_DESIGN.md)

✅ **코드 구현 완료**
- common/namespace.py 생성
- database/redis.py 수정
- execution/engine.py 수정
- scripts/run_paper.py, run_backtest.py 수정

✅ **단위 테스트 PASS**
- tests/test_phase18_2_run_id_namespace.py
- 모든 시나리오 PASS

✅ **짧은 REAL PAPER 검증**
- 10~15분 실행
- Redis 키 네임스페이스 확인
- ERROR/CRITICAL 0건

✅ **완료 리포트 작성**
- PHASE18-2_COMPLETE_REPORT.md

### 7.2 판정 기준

**PASS 조건**:
- 모든 Redis 키가 `{domain}:{env}:{run_id}:` 형식
- 단위 테스트 100% PASS
- REAL PAPER smoke test ERROR 0건
- 기존 테스트 회귀 없음

**FAIL 조건**:
- Redis 키에 여전히 run_id 없는 키 존재
- 테스트 실패
- REAL PAPER 실행 중 ERROR 발생
- 기존 기능 회귀

---

## 8. 향후 확장 (PHASE19+)

### 8.1 계층적 네임스페이스

```python
# 앙상블 환경
ensemble_run_id = "20251119_150000_e1a2"
strategy_run_ids = {
    "scalping": "20251119_150000_e1a2_s1",
    "trend": "20251119_150000_e1a2_s2",
    "reversion": "20251119_150000_e1a2_s3",
}

# Redis 키
cooldown:paper:20251119_150000_e1a2_s1:BTCUSDT:scalping
cooldown:paper:20251119_150000_e1a2_s2:BTCUSDT:trend
```

### 8.2 로그 파일 분리

```
logs/
  ├─ paper/
  │   ├─ 20251119_140530_a7f3/
  │   │   ├─ application.log
  │   │   └─ trading.log
  │   └─ 20251119_141030_b8e4/
  │       └─ ...
  ├─ backtest/
  └─ live/
```

### 8.3 DB 네임스페이스

```sql
-- run_id 인덱스 추가
CREATE INDEX idx_positions_run_id ON positions(run_id);
CREATE INDEX idx_trades_run_id ON trades(run_id);

-- run_id 기반 조회 최적화
SELECT * FROM trades WHERE run_id = '20251119_140530_a7f3';
```

---

**문서 작성**: 2025-11-19  
**작성자**: Cascade AI (Claude 4.5 Thinking)  
**상태**: 설계 완료, 구현 준비  
**다음 단계**: STEP 3 - 구현 (코드 변경)
