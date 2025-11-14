# Execution 모듈 하드코딩 전수 조사 (PHASE9-2)

## 📋 Summary

**조사 범위**: `execution/` 디렉토리 전체 (engine, risk, portfolio, sizer, broker, tracker)  
**목표**: Config 이동 가능/불가능 항목 분류 및 영향 분석

---

## 🔍 파일별 하드코딩 요소

### 1. `execution/engine.py`

#### 하드코딩 항목

| Line | 코드 | 값 | Config 이동 | 우선순위 | 영향 |
|------|------|----|-------------|----------|------|
| 69 | `time.sleep(2)` | 2초 | ✅ 가능 | LOW | WebSocket 안정화 대기 |
| 117 | `reject_cooldown_seconds` | 60초 | ✅ 완료 | - | 거부 쿨다운 (config에서 읽기) |
| 155 | `int(base_seconds * 1.05)` | 1.05 | ✅ 가능 | LOW | Redis TTL 버퍼 (5%) |
| 1231-1233 | 중복 진입 방지 | 암묵적 | ✅ 가능 | **CRITICAL** | 동일 심볼+방향 진입 차단 |

#### 영향 분석

**CRITICAL: 중복 진입 방지 (Line 1231-1233)**
```python
same_direction_positions = [
    (pos_id, pos) for pos_id, pos in list(active_positions.items())
    if pos["symbol"] == candle_symbol and pos["side"] == new_side
]
if same_direction_positions:
    logger.warning(f"⚠️ [중복 진입 방지] ...")
    continue  # ⚠️ 하드코딩으로 무조건 차단
```

**문제점**:
- Config로 제어 불가 (ON/OFF 불가)
- Backtest vs Live 동작 차이 발생 가능
- 평균화 전략(DCA) 구현 불가

**TO-BE**:
```yaml
# config.yml
portfolio:
  allow_duplicate_entry: false  # 기본값 false (안전)
  duplicate_entry_policy: "reject"  # reject | average_down | pyramid
```

---

### 2. `execution/risk_manager.py`

#### 하드코딩 항목

| Line | 코드 | 값 | Config 이동 | 우선순위 | 영향 |
|------|------|----|-------------|----------|------|
| 95 | `max_drawdown_pct` | 10.0% | ✅ 완료 | - | 최대 낙폭 (config에서 읽기) |
| 100 | `max_slippage_pct` | 0.5% | ✅ 완료 | - | 슬리피지 가드 |
| 106 | `extreme_loss_cutoff_pct` | -30.0% | ✅ 완료 | - | 극단 손실 가드 |
| 130 | `flash_pct` | 0.03 | ✅ 완료 | - | Flash Guard 임계값 (3%) |
| 145 | `_flash_log_throttle_ms` | 300000 | ✅ 완료 | - | Flash 로그 쓰로틀 (5분) |
| 237 | `len(buf) >= 2` | 2 | ✅ 가능 | LOW | Flash 버퍼 최소 크기 |
| 341 | `epsilon = 0.1` | 0.1 USDT | ✅ 가능 | LOW | Exposure 허용 오차 |

#### 영향 분석

**Flash Guard 버퍼 크기 (Line 237)**
```python
if len(buf) >= 2:  # ⚠️ 최소 2개 데이터 필요
    p0 = buf[0][1]
    change = abs(price - p0) / p0
```

**문제점**:
- 짧은 버퍼 → 급등락 오탐 가능
- 긴 버퍼 → 급등락 늦게 감지

**TO-BE**:
```yaml
# config.yml
flash_guard:
  buffer_size: 3  # 기본값 2 → 3 (더 안정적)
```

**Exposure Epsilon (Line 341)**
```python
epsilon = 0.1  # ⚠️ 부동소수점 허용 오차
if total_exposure > max_per_symbol + epsilon:
    return False, "심볼별 한도 초과"
```

**문제점**:
- 0.1 USDT는 작은 계좌에서는 큼 ($100 equity → 0.1%)
- 큰 계좌에서는 작음 ($100K equity → 0.0001%)

**TO-BE**:
```yaml
# config.yml
risk:
  exposure_epsilon_pct: 0.001  # 0.1% (상대적 허용 오차)
```

---

### 3. `execution/position_sizer.py`

#### 하드코딩 항목

| Line | 코드 | 값 | Config 이동 | 우선순위 | 영향 |
|------|------|----|-------------|----------|------|
| 140 | `final_qty < 0.001` | 0.001 | ✅ 가능 | LOW | 거래소 최소 수량 |
| 147 | `epsilon = 1.0` | 1.0 USDT | ✅ 가능 | LOW | 포지션 가치 허용 오차 |
| 180 | `(confidence - 0.5) * 1.2` | 1.2 | ✅ 가능 | MED | 품질 가중치 기울기 |
| 190-225 | Quality Weight 로직 | 복합 | ⚠️ 복잡 | MED | Sharpe/Winrate/DD 배수 |

#### 영향 분석

**거래소 최소 수량 (Line 140)**
```python
if final_qty < 0.001:  # ⚠️ 바이낸스 최소 수량
    return 0.0, {"reason": "below_min_qty"}
```

**문제점**:
- 거래소별로 다름 (Bybit: 0.0001, OKX: 0.001)
- 심볼별로 다름 (BTCUSDT: 0.001, PEPEUSDT: 1000)

**TO-BE**:
```yaml
# config.yml
execution:
  min_qty_by_symbol:
    BTCUSDT: 0.001
    ETHUSDT: 0.01
    default: 0.001
```

**Quality Weight 기울기 (Line 180)**
```python
base_weight = self.quality_weight_min + (confidence - 0.5) * 1.2  # ⚠️ 1.2 하드코딩
```

**문제점**:
- 기울기 1.2가 최적값인지 불명확
- 백테스트로 튜닝 필요

**TO-BE**:
```yaml
# config.yml
position_sizing:
  quality_weight_slope: 1.2  # 기본값, 튜닝 가능
```

---

### 4. `execution/portfolio_manager.py`

#### 하드코딩 항목

✅ **없음** - 모든 파라미터가 config에서 읽기 가능

| 파라미터 | Config 경로 | 비고 |
|---------|-------------|------|
| `max_strategy_positions` | `portfolio.max_strategy_positions` | ✅ |
| `max_total_exposure` | `portfolio.max_total_exposure` | ✅ |
| `symbol_cooldown_seconds` | `portfolio.symbol_cooldown_seconds` | ✅ |
| `load_existing` | `portfolio.load_existing` | ✅ |

---

### 5. `execution/tp_manager.py`

#### 하드코딩 항목

| Line | 코드 | 값 | Config 이동 | 우선순위 | 영향 |
|------|------|----|-------------|----------|------|
| 37-39 | TP 기본값 | `[{r:1.0, 30%}, {r:2.0, 40%}]` | ✅ 완료 | - | Fallback 값 |
| 44 | `trail_k` | 3.0 | ✅ 완료 | - | 트레일링 ATR 배수 |
| 45 | `be_at_r` | 0.8 | ✅ 완료 | - | Break-Even 이동 시점 |
| 76-80 | `vol_mult` | 1.2 / 0.9 | ✅ 가능 | **HIGH** | 변동성 레짐 조정 |
| 274 | `remaining_pct` | 100.0 | ✅ 완료 | - | 초기 잔여 % |

#### 영향 분석

**변동성 레짐 배수 (Line 76-80)**
```python
vol_mult = 1.0
if volatility_regime == 'high_vol':
    vol_mult = 1.2  # ⚠️ 하드코딩 (20% 증가)
elif volatility_regime == 'low_vol':
    vol_mult = 0.9  # ⚠️ 하드코딩 (10% 감소)

adjusted_one_r = one_r * vol_mult
```

**문제점**:
- 고변동성 시 SL 20% 넓게 → TP도 멀어짐
- 저변동성 시 SL 10% 좁게 → TP도 가까워짐
- 배수가 최적값인지 검증 필요

**영향**:
- **Backtest**: 고변동성 구간(10월-12월 2024)에서 SL 너무 넓음 → 손실 커짐
- **Paper/Live**: 동일 로직 적용 → 일관성 유지

**TO-BE**:
```yaml
# config.yml
exits:
  volatility_regime_multipliers:
    high_vol: 1.2  # 기본값, 튜닝 가능
    neutral: 1.0
    low_vol: 0.9
```

---

### 6. `execution/broker/sim_broker.py`

#### 하드코딩 항목

✅ **최소화됨** - 대부분 config에서 읽기

| 파라미터 | Config 경로 | 비고 |
|---------|-------------|------|
| `fill_policy` | `execution.fill_policy` | ✅ |
| `fees_bps` | `execution.fees_bps` | ✅ |
| `slippage.type` | `execution.slippage.type` | ✅ |
| `slippage.bps` | `execution.slippage.bps` | ✅ |

---

## 📊 하드코딩 요약

### Config 이동 가능 (9개)

| 항목 | 현재 값 | 우선순위 | 영향도 | 비고 |
|------|---------|----------|--------|------|
| 중복 진입 방지 | 무조건 차단 | **CRITICAL** | ★★★★★ | DCA/Pyramid 불가 |
| 변동성 레짐 배수 | 1.2 / 0.9 | **HIGH** | ★★★★☆ | SL/TP 크기 결정 |
| 품질 가중치 기울기 | 1.2 | MED | ★★★☆☆ | 포지션 크기 영향 |
| Flash 버퍼 크기 | 2 | LOW | ★★☆☆☆ | 급등락 오탐률 |
| Exposure Epsilon | 0.1 USDT | LOW | ★★☆☆☆ | 부동소수점 허용 오차 |
| 최소 수량 | 0.001 | LOW | ★★☆☆☆ | 거래소 제약 |
| WebSocket 대기 | 2초 | LOW | ★☆☆☆☆ | 연결 안정성 |
| Redis TTL 버퍼 | 1.05 | LOW | ★☆☆☆☆ | 멱등성 |

### Config 이동 불가 (0개)

✅ **모든 하드코딩이 Config 이동 가능**

---

## 🚨 백테스트/Paper/Live 영향 분석

### CRITICAL: 중복 진입 방지

| 모드 | 현재 동작 | 문제점 |
|------|----------|--------|
| Backtest | `load_existing=False` → 중복 방지 정상 작동 | ✅ 정상 |
| Paper | `load_existing=True` → 기존 포지션 로드 → 중복 차단 | ⚠️ 신규 진입 불가 발생 가능 |
| Live | `load_existing=True` → 기존 포지션 로드 → 중복 차단 | ⚠️ 신규 진입 불가 발생 가능 |

**시나리오**:
1. Live 모드에서 BTCUSDT LONG 포지션 보유 중
2. 엔진 재시작 (`load_existing=True`)
3. 새로운 BTCUSDT LONG 신호 발생
4. 중복 진입 방지 로직에서 차단 (Line 1231-1233)
5. **결과: 신호 무시됨** ❌

**해결 방안**:
```yaml
# config.yml
portfolio:
  allow_duplicate_entry: false  # 기본값 (안전)
  # 또는
  allow_duplicate_entry: true   # DCA 전략용
  max_duplicate_entries: 3      # 최대 중복 진입 횟수
```

### HIGH: 변동성 레짐 배수

| 모드 | 현재 동작 | 문제점 |
|------|----------|--------|
| Backtest | `vol_mult=1.2` (고변동성) → SL 넓음 | ⚠️ 손실 커짐 |
| Paper | 동일 | ⚠️ 동일 |
| Live | 동일 | ⚠️ 동일 |

**PHASE9-0 결과 분석** (2024-10-01 ~ 2024-12-31):
- 고변동성 구간 → SL 20% 넓게 → **손실 확대**
- `backtest_clean` (10월): 6건, Winrate 33%, PF 0.52
- `backtest_raw` (10월): 8건, Winrate 25%, PF 0.35

**추정**:
- 변동성 배수 1.2 → 1.1로 축소 시 Winrate 개선 가능
- 변동성 배수 0.9 → 1.0으로 확대 시 신호 빈도 증가

**해결 방안**:
```yaml
# config.yml
exits:
  volatility_regime_multipliers:
    high_vol: 1.1  # 1.2 → 1.1 (손실 축소)
    neutral: 1.0
    low_vol: 0.95  # 0.9 → 0.95 (진입 기회 증가)
```

---

## 🎯 Config 리팩토링 우선순위

### Phase 1 (PHASE9-3) - CRITICAL + HIGH

1. **중복 진입 방지 정책**: `allow_duplicate_entry`, `duplicate_entry_policy`
2. **변동성 레짐 배수**: `vol_regime_mult_high/low`

### Phase 2 (PHASE9-4) - MED

1. **품질 가중치 기울기**: `quality_weight_slope`
2. **Flash 버퍼 크기**: `flash_buffer_size`

### Phase 3 (PHASE9-5) - LOW

1. **Exposure Epsilon**: `exposure_epsilon_pct`
2. **최소 수량**: `min_qty_by_symbol`
3. **WebSocket 대기**: `websocket_stabilize_sec`
4. **Redis TTL 버퍼**: `redis_ttl_buffer_pct`

---

*Generated: PHASE9-2*  
*Status: ✅ Execution 모듈 하드코딩 전수 조사 완료*
