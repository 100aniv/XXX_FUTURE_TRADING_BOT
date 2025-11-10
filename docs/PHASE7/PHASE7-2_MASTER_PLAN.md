# PHASE7-2 마스터 플랜: 포지션 관리 개선 (승률 45% 달성)

## 배경/의도 (Overview)

PHASE 7-1 긴급 패치 완료 후, 시스템의 근본적 성과 개선 필요.
- 현재 승률: 39.6% → 목표: 45% 이상
- TP2 도달: 0건 → 목표: 5% 이상
- 손익비: 0.45 → 목표: 0.8 이상
- **빈번한 거래**: 시간당 310건 → 목표: 시간당 5건 이하

**상용 프로그램 벤치마킹** (PHASE7_ALGORITHM_BEST.md 참조):
- 3Commas: 승률 60-70%, 거래 쿨다운 24시간
- Pionex: 승률 55-65%, 그리드 간격 1%+
- TradingView: 승률 50-60%, 손익비 2:1, 엄격한 필터링

포지션 관리 로직을 개선하여 **상용 수준 진입**을 위한 기반 마련.

## 목표 (Goals)

- **승률 45% 이상** 달성 (Paper 3일 평균)
- **TP1/TP2 비율 최적화**: 손익비 0.8 이상
- **중복 진입 방지 완성**: DB-메모리 동기화
- **슬리피지 정확도**: Paper 실제 시장 반영
- **TP2 도달**: 전체 거래의 5% 이상

## 범위 (Scope, In)

### 1. SL/TP 재조정 (1일)

**현재 문제**:
- TP1: 1.5R (너무 가까움, 미세 수익)
- TP2: 3.0R (너무 멀어 도달 0건)
- SL: 8% (너무 넓음)

**개선**:
- TP1: 1.5R → 2.0R (보수적 조정)
- TP2: 3.0R → 삭제 or 4.5R
- SL: 동적 조정 (ATR 기반, 최대 6%)
- Trailing Stop: TP1 도달 후 즉시 활성화

**영향 파일**:
- `common/calculations.py::price_levels()`
- `config.yml::exits.*`
- `execution/position_tracker.py` (Trailing 조기 활성화)

### 2. 중복 진입 방지 완성 (반나절)

**현재 문제**:
- 중복 진입 여전히 발생 (로그 없음)
- DB와 메모리 `active_positions` 불일치
- ensemble_1 vs ensemble_2 별도 관리

**개선**:
- DB OPEN 포지션 동기화 로직 강화
- active_positions 상태 검증 로그 추가
- 진입 전 DB 쿼리로 재확인
- Redis 분산 락 (optional)

**영향 파일**:
- `execution/engine.py` (진입 전 체크)
- `common/redis_client.py` (분산 락, optional)

### 3. 슬리피지 시뮬레이션 (반나절)

**현재 문제**:
- PaperBroker 고정 슬리피지 0.05%
- 실제 시장 변동성 미반영
- LIMIT vs MARKET 주문 구분 없음

**개선**:
- 변동성 기반 슬리피지 (ATR 참조)
- 시장가 주문: ATR * 0.5% ~ 1.0%
- 지정가 주문: 0% (체결 가정)
- 유동성 부족 시뮬레이션 (optional)

**영향 파일**:
- `execution/adapters/brokers.py::PaperBroker`
- `config.yml::fees.slippage_model`

### 4. 전략별 독립 설정 (1일) ⭐ 앙상블 시스템 특화

⚠️ **구현 상태**: 설계 완료, 코드 구현 대기 중 (PHASE7-2)

**현재 문제** (PHASE7_ALGORITHM_BEST.md 분석):
- **6개 전략을 동일하게 처리** (단일 전략 로직 적용)
- scalping(1분)과 swing(1시간)이 동일한 제한
- 전략별 특성 무시 → 시간당 310건 거래 발생

**개선** (QuantConnect/Freqtrade 벤치마킹):

#### 전략별 독립 설정 (config.yml)

```yaml
strategies:
  scalping:
    cooldown_minutes: 5        # 5분 쿨다운
    max_positions: 5           # 최대 5개
    max_trades_per_hour: 20    # 시간당 20개
    confidence_threshold: 0.65 # 낮은 임계값 (빈번한 거래)
    atr_range:
      min_pct: 0.003
      max_pct: 0.030
  
  daytrade:
    cooldown_minutes: 15       # 15분 쿨다운
    max_positions: 3
    max_trades_per_hour: 12
    confidence_threshold: 0.70
    atr_range:
      min_pct: 0.005
      max_pct: 0.025
  
  swing:
    cooldown_minutes: 60       # 1시간 쿨다운
    max_positions: 2
    max_trades_per_hour: 5
    confidence_threshold: 0.75 # 높은 임계값 (신중한 진입)
    atr_range:
      min_pct: 0.008
      max_pct: 0.030
  
  breakout:
    cooldown_minutes: 30
    max_positions: 3
    max_trades_per_hour: 8
    confidence_threshold: 0.78
  
  trend:
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 3
    confidence_threshold: 0.70
  
  reversion:
    cooldown_minutes: 20
    max_positions: 3
    max_trades_per_hour: 10
    confidence_threshold: 0.68
```

#### 포트폴리오 레벨 제한 (ensemble)

```yaml
ensemble:
  max_total_positions: 10       # 20 → 10 (상용 기준)
  max_exposure_pct: 50          # 총 노출 50%
  max_positions_per_symbol: 1   # 심볼당 1개 (중복 방지)
  max_trades_per_hour: 15       # 전체 시간당 15개 (310 → 15)
```

**영향 파일**:
- `execution/engine.py` (진입 전 전략별 체크)
- `strategies/ensemble.py` (가중치 계산 시 전략별 성과 반영)
- `common/redis_client.py` (전략별 쿨다운 관리)
- `config.yml::strategies.*`

**예상 효과**:
- 시간당 거래: 310건 → **15건** (95% 감소)
- 수수료 누적: 24.8% → **1.2%** (95% 감소)
- 승률: 신호 품질 향상으로 **45%+** 달성 예상

### 5. 신호 필터링 강화 (기존 유지, 하위 호환)

**현재 문제**:
- Confidence 낮은 신호도 진입 (0.5+)
- 최소 투표수 체크 약함

**개선** (전략별 설정으로 대체):
- 전략별 confidence_threshold 적용 (위 참조)
- 포트폴리오 레벨에서만 최소 투표수 체크
- 전략 자체 필터링 강화 (각 전략 파일에서)

## 제외 (Out-of-Scope)

- 전략 신호 로직 (Strategy 모듈)
- Graceful Shutdown (PHASE 7-3)
- Dashboard (PHASE 7-3)
- 백테스트 파이프라인 (PHASE 7-4)

## 영향 파일

**필수**:
- `common/calculations.py`
- `execution/engine.py`
- `execution/position_tracker.py`
- `execution/adapters/brokers.py`
- `config.yml`

**선택**:
- `common/redis_client.py` (분산 락)

**테스트**:
- `tests/execution/test_position_tracker.py`
- `tests/execution/test_engine.py`
- `tests/adapters/test_brokers.py`

**문서**:
- `docs/PHASE7/PHASE7-2_IMPLEMENTATION_LOG.md`

## 설정 키

```yaml
exits:
  # TP/SL 비율
  tp1_r: 2.0              # 1.5R → 2.0R
  tp2_r: 4.5              # 3.0R → 4.5R (or null)
  tp1_pct: 50             # TP1 청산 50%
  tp2_pct: 0              # TP2 삭제 (or 30)
  
  # SL 동적 조정
  sl_max_pct: 6.0         # 최대 6% (기존 8%)
  sl_min_pct: 2.0         # 최소 2%
  sl_atr_multiplier: 1.5  # ATR * 1.5
  
  # Trailing Stop
  trailing_activate_at: "TP1"  # TP1 도달 후 즉시
  trailing_distance_pct: 2.0   # 2% 거리 유지

fees:
  # 슬리피지 모델
  slippage_model: "dynamic"    # "fixed" or "dynamic"
  slippage_fixed: 0.0005       # 고정 0.05%
  slippage_atr_multiplier: 0.5 # ATR * 0.5% (동적)
  slippage_max: 0.02           # 최대 2%

risk:
  # 중복 진입 방지
  duplicate_check_strict: true
  duplicate_check_db: true     # DB 재확인
  use_distributed_lock: false  # Redis 분산 락 (optional)

signals:
  # 신호 필터링 (승률 향상)
  min_confidence: 0.70         # 0.5 → 0.70
  min_votes: 2                 # 1 → 2
  atr_range:
    min_pct: 0.003             # 0.3%
    max_pct: 0.030             # 3.0%
  volume_threshold: 1.5        # 평균 대비 1.5배

rate_limits:
  # 거래 빈도 제한 (수수료 절감)
  symbol_cooldown_hours: 4     # 종목별 쿨다운 4시간
  max_trades_per_hour: 5       # 시간당 최대 5개
  confirmation_candles: 1      # 확인 캔들 1개
```

## 구현 상세

### 1. TP1/TP2 재조정

**AS-IS**:
```python
# common/calculations.py::price_levels()
tp1_r = 1.5  # 하드코딩
tp2_r = 3.0
sl_max_pct = 0.08  # 8%
```

**TO-BE**:
```python
def price_levels(entry, side, atr, config):
    # config에서 읽기
    tp1_r = config.get('exits', {}).get('tp1_r', 2.0)
    tp2_r = config.get('exits', {}).get('tp2_r', 4.5)
    sl_max_pct = config.get('exits', {}).get('sl_max_pct', 0.06) / 100
    
    # 동적 SL (ATR 기반)
    sl_multiplier = config.get('exits', {}).get('sl_atr_multiplier', 1.5)
    sl_distance = atr * sl_multiplier
    sl_distance_pct = sl_distance / entry
    
    # SL 범위 제한
    sl_min_pct = config.get('exits', {}).get('sl_min_pct', 2.0) / 100
    sl_distance_pct = max(sl_min_pct, min(sl_max_pct, sl_distance_pct))
    
    if side == 'LONG':
        sl_price = entry * (1 - sl_distance_pct)
        tp1_price = entry * (1 + tp1_r * sl_distance_pct)
        tp2_price = entry * (1 + tp2_r * sl_distance_pct) if tp2_r else None
    else:  # SHORT
        sl_price = entry * (1 + sl_distance_pct)
        tp1_price = entry * (1 - tp1_r * sl_distance_pct)
        tp2_price = entry * (1 - tp2_r * sl_distance_pct) if tp2_r else None
    
    return {
        'entry': entry,
        'sl': sl_price,
        'tp1': tp1_price,
        'tp2': tp2_price,
        'sl_distance_pct': sl_distance_pct * 100,
        'tp1_r': tp1_r,
        'tp2_r': tp2_r
    }
```

**Trailing Stop 조기 활성화**:
```python
# execution/position_tracker.py::check_tpsl_with_partial()
def check_tpsl_with_partial(self, position, current_price, atr=None, candle=None):
    # ... SL/TP 체크 ...
    
    # TP1 도달 시 Trailing Stop 활성화
    if reason == 'TP1':
        trailing_activate = config.get('exits', {}).get('trailing_activate_at', 'TP1')
        if trailing_activate == 'TP1':
            position['trailing_active'] = True
            position['trailing_highest'] = current_price  # LONG
            position['trailing_lowest'] = current_price   # SHORT
            logger.info(f"✅ TP1 도달 → Trailing Stop 활성화: {position['symbol']}")
        
        return True, partial_qty, 'TP1'
```

### 2. 중복 진입 방지

**AS-IS**:
```python
# execution/engine.py (기존 로직)
# 메모리 active_positions만 체크
if (candle_symbol, new_side) in [(p['symbol'], p['side']) for p in active_positions]:
    logger.warning(f"⚠️ 중복 진입 방지: {candle_symbol} {new_side}")
    continue
```

**TO-BE**:
```python
# execution/engine.py (강화)
def check_duplicate_entry(symbol, side, active_positions, config):
    """중복 진입 체크 (메모리 + DB)"""
    # 1. 메모리 체크
    for pos in active_positions:
        if pos['symbol'] == symbol and pos['side'] == side:
            logger.warning(f"⚠️ [MEMORY] 중복 진입 방지: {symbol} {side}")
            return True
    
    # 2. DB 재확인 (설정 시)
    if config.get('risk', {}).get('duplicate_check_db', True):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM trading.trades
                    WHERE symbol = %s AND side = %s 
                      AND status = 'OPEN' AND mode = %s
                """, (symbol, side, mode))
                count = cur.fetchone()[0]
                if count > 0:
                    logger.warning(f"⚠️ [DB] 중복 진입 방지: {symbol} {side} (OPEN: {count}건)")
                    return True
    
    return False

# 진입 전 체크
if check_duplicate_entry(candle_symbol, new_side, active_positions, config):
    continue
```

**Redis 분산 락 (선택)**:
```python
# common/redis_client.py
def acquire_lock(key, timeout=5):
    """분산 락 획득"""
    lock_key = f"lock:{key}"
    return redis_client.set(lock_key, "1", nx=True, ex=timeout)

def release_lock(key):
    """분산 락 해제"""
    lock_key = f"lock:{key}"
    redis_client.delete(lock_key)

# execution/engine.py
lock_key = f"{mode}:entry:{candle_symbol}:{new_side}"
if acquire_lock(lock_key, timeout=5):
    try:
        # 진입 로직
        pass
    finally:
        release_lock(lock_key)
```

### 3. 슬리피지 시뮬레이션

**AS-IS**:
```python
# execution/adapters/brokers.py::PaperBroker
def place_order(self, symbol, side, qty, price=None):
    slippage_pct = 0.0005  # 고정 0.05%
    if side == 'BUY':
        filled_price = price * (1 + slippage_pct)
    else:
        filled_price = price * (1 - slippage_pct)
```

**TO-BE**:
```python
def place_order(self, symbol, side, qty, price=None, atr=None, order_type='MARKET'):
    """
    주문 실행 (동적 슬리피지)
    
    Args:
        order_type: 'MARKET' or 'LIMIT'
        atr: ATR 값 (변동성)
    """
    slippage_model = self.config.get('fees', {}).get('slippage_model', 'fixed')
    
    if slippage_model == 'dynamic' and atr and order_type == 'MARKET':
        # ATR 기반 슬리피지
        atr_multiplier = self.config.get('fees', {}).get('slippage_atr_multiplier', 0.5)
        slippage_pct = (atr / price) * atr_multiplier / 100  # ATR * 0.5%
        
        # 최대치 제한
        slippage_max = self.config.get('fees', {}).get('slippage_max', 0.02)
        slippage_pct = min(slippage_pct, slippage_max)
    elif order_type == 'LIMIT':
        # 지정가 주문: 슬리피지 0%
        slippage_pct = 0.0
    else:
        # 고정 슬리피지
        slippage_pct = self.config.get('fees', {}).get('slippage_fixed', 0.0005)
    
    # 체결가 계산
    if side == 'BUY':
        filled_price = price * (1 + slippage_pct)
    else:
        filled_price = price * (1 - slippage_pct)
    
    logger.debug(
        f"📊 슬리피지: {symbol} {side} | "
        f"Model: {slippage_model}, Slip: {slippage_pct*100:.3f}%, "
        f"Price: ${price:.6f} → ${filled_price:.6f}"
    )
    
    return {'filled_price': filled_price, ...}
```

## 금지 사항

❌ 전략 신호 로직 수정  
❌ 하드코딩 (config.yml 사용)  
❌ TP/SL 과도한 조정 (점진적 테스트)  
❌ 성능 저하 (DB 쿼리 최소화)

## 수용 기준

### 필수

- [ ] Paper 3일 평균 승률: **45% 이상**
- [ ] 손익비: **0.8 이상** (TP 평균 / SL 평균)
- [ ] TP2 도달: **5% 이상** (전체 거래 대비)
- [ ] 중복 진입: **0건** (3일 동안)
- [ ] 8% 초과 손실: **0건** (PHASE 7-1 유지)

### 선택

- [ ] Trailing Stop 활성화: TP1 도달 케이스의 80%
- [ ] 슬리피지 정확도: 실제 시장 ±10% 이내
- [ ] DB 쿼리 성능: < 50ms

## 테스트 플랜

### 단위 테스트

```python
# tests/common/test_calculations.py
def test_price_levels_dynamic_sl():
    """동적 SL (ATR 기반) 테스트"""
    entry = 100.0
    atr = 2.0  # 2% 변동성
    config = {'exits': {'sl_atr_multiplier': 1.5, 'sl_max_pct': 6.0}}
    
    levels = price_levels(entry, 'LONG', atr, config)
    
    # SL = ATR * 1.5 = 3%
    assert 2.0 <= levels['sl_distance_pct'] <= 6.0
    assert levels['tp1_r'] == 2.0

def test_price_levels_tp2_optional():
    """TP2 선택적 사용"""
    config = {'exits': {'tp2_r': None}}
    levels = price_levels(100.0, 'LONG', 2.0, config)
    assert levels['tp2'] is None

# tests/execution/test_engine.py
def test_duplicate_entry_prevention_db():
    """중복 진입 방지 (DB 체크)"""
    # DB에 OPEN 포지션 삽입
    insert_open_position('TESTUSDT', 'LONG')
    
    # 진입 시도
    is_duplicate = check_duplicate_entry('TESTUSDT', 'LONG', [], config)
    assert is_duplicate == True

# tests/adapters/test_brokers.py
def test_slippage_dynamic():
    """동적 슬리피지 (ATR 기반)"""
    broker = PaperBroker(config={'fees': {'slippage_model': 'dynamic', 'slippage_atr_multiplier': 0.5}})
    
    result = broker.place_order('TEST', 'BUY', 1.0, price=100.0, atr=2.0, order_type='MARKET')
    
    # ATR 2%, 0.5배 = 1% 슬리피지
    assert 100.5 <= result['filled_price'] <= 101.5

def test_slippage_limit_order():
    """지정가 주문 슬리피지 0%"""
    broker = PaperBroker(config={'fees': {'slippage_model': 'dynamic'}})
    
    result = broker.place_order('TEST', 'BUY', 1.0, price=100.0, order_type='LIMIT')
    assert result['filled_price'] == 100.0
```

### 통합 테스트

```sql
-- Paper 3일 후 검증
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN pnl_pct > 0 THEN 1 END) as wins,
  ROUND(AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END), 2) as avg_win,
  ROUND(AVG(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) END), 2) as avg_loss,
  COUNT(CASE WHEN exit_reason='TP2' THEN 1 END) as tp2_count,
  COUNT(CASE WHEN pnl_pct < -8 THEN 1 END) as over_8pct
FROM trading.trades 
WHERE mode='paper' 
  AND ts_open >= NOW() - INTERVAL '3 days';

-- 승률 계산
SELECT ROUND((COUNT(CASE WHEN pnl_pct > 0 THEN 1 END)::float / COUNT(*)) * 100, 1) as win_rate
FROM trading.trades 
WHERE mode='paper' AND ts_open >= NOW() - INTERVAL '3 days';

-- 중복 진입 체크
SELECT symbol, side, COUNT(*) as count
FROM trading.trades
WHERE status='OPEN' AND mode='paper'
GROUP BY symbol, side
HAVING COUNT(*) > 1;
```

**수용 기준**:
- `win_rate`: 45% 이상
- `avg_win / avg_loss`: 0.8 이상
- `tp2_count`: 전체의 5% 이상
- `over_8pct`: 0건
- 중복 진입: 0건

## 체크리스트

### 구현

- [ ] **TP/SL 재조정**
  - [ ] `price_levels()` TP1 2.0R, TP2 4.5R
  - [ ] 동적 SL (ATR * 1.5, 2~6%)
  - [ ] config.yml 키 추가
  - [ ] Trailing Stop TP1 활성화

- [ ] **중복 진입 방지**
  - [ ] `check_duplicate_entry()` 함수
  - [ ] DB 재확인 로직
  - [ ] Redis 분산 락 (optional)
  - [ ] 상태 로그 추가

- [ ] **슬리피지 시뮬레이션**
  - [ ] `PaperBroker` 동적 슬리피지
  - [ ] ATR 기반 계산
  - [ ] LIMIT 주문 0% 슬리피지
  - [ ] config 설정

### 테스트

- [ ] 단위 테스트 (price_levels, duplicate, slippage)
- [ ] Paper 3일 실행
- [ ] 승률 45% 달성
- [ ] TP2 5% 도달
- [ ] 중복 진입 0건
- [ ] pre-commit 통과

### 문서

- [ ] IMPLEMENTATION_LOG.md
- [ ] CRITICAL_SYSTEM_ANALYSIS 업데이트

## 배포/롤백

- PHASE 7-1 완료 확인 → 7-2 적용
- Paper 3일 검증 → Live 소액 테스트
- 승률 저하 시 config 롤백 (TP/SL 원복)

## 리스크/완화

- TP1 2.0R로 승률 하락? → 1.8R로 조정
- TP2 여전히 미도달? → 삭제하고 Trailing 강화
- 슬리피지 과대? → ATR multiplier 0.3으로 감소
- DB 쿼리 부하? → Redis 캐싱

## 릴리즈 노트

PHASE7-2: TP/SL 최적화 + 중복 방지 완성 + 슬리피지 개선으로 승률 45% 달성. 상용 수준 진입 기반 마련.
