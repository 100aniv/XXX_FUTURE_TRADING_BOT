# Config 중심 구조 리팩토링 TO-BE 설계 (PHASE9-2)

## 📋 Executive Summary

**목표**: PAPER / LIVE / BACKTEST 모두 동일한 엔진 로직 사용, 오직 config로 behavior 전부 바꾸도록 구조화

**원칙**:
1. **Zero Hard-coding**: 모든 파라미터는 config에서 읽기
2. **Mode Agnostic**: 모드별 분기 최소화 (어댑터 패턴)
3. **Single Source**: config 계층을 단일 소스로 사용

---

## 🏗️ Config 계층 구조 (TO-BE)

```
┌─────────────────────────────────────────────────────────────┐
│                   1. base.yml (Base)                         │
│  - 전역 기본값 (모든 모드/전략 공통)                          │
│  - indicators, risk, portfolio, execution 등                │
└─────────────────────────────────────────────────────────────┘
                             ▼ (Override)
┌─────────────────────────────────────────────────────────────┐
│            2. strategies/<name>.yml (Strategy)               │
│  - 전략별 고유 파라미터 (scalping, breakout, daytrade)        │
│  - BB 임계값, RSI 범위, Volume 배수 등                        │
└─────────────────────────────────────────────────────────────┘
                             ▼ (Override)
┌─────────────────────────────────────────────────────────────┐
│            3. modes/<mode>.yml (Mode)                        │
│  - 모드별 동작 (backtest_clean, backtest_raw, paper, live)   │
│  - Risk 완화/강화, Portfolio 제한, Execution 정책            │
└─────────────────────────────────────────────────────────────┘
                             ▼ (Override)
┌─────────────────────────────────────────────────────────────┐
│              4. active/current.yml (Active)                  │
│  - 실험용 오버라이드 (튜닝/디버깅)                            │
└─────────────────────────────────────────────────────────────┘
                             ▼ (Override)
┌─────────────────────────────────────────────────────────────┐
│                   5. CLI/ENV (Runtime)                       │
│  - 런타임 오버라이드 (--mode, --symbol, --timeframe 등)      │
└─────────────────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│               📦 Effective Config (Merged)                   │
│  - 최종 병합된 설정 (artifacts/{run_id}/effective_config.yml)│
│  - 재현성 보장 (동일 config → 동일 결과)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Config 파일 구조 (TO-BE)

### `configs/base.yml` (기본값)

```yaml
# ========================================
# GLOBAL DEFAULTS (모든 모드 공통)
# ========================================

capital:
  initial: 50000

risk:
  per_trade: 0.003  # 0.3%
  max_positions: 20
  max_exposure_pct: 0.95
  max_exposure_per_symbol: 0.3  # 30%
  max_daily_loss_pct: 2.0
  max_consecutive_losses: 4
  cooldown_after_consecutive: 30
  max_drawdown_pct: 10.0
  extreme_loss_cutoff_pct: -30.0
  liq_buffer_multiple_of_SL: 4
  leverage_cap: 5
  margin_ratio: 0.01
  
  # ⭐ NEW: Epsilon & Thresholds
  exposure_epsilon_pct: 0.001  # 0.1% (상대적 허용 오차)

portfolio:
  max_strategy_positions: 5
  max_total_exposure: 0.95
  symbol_cooldown_seconds: 60
  load_existing: true  # Paper/Live: true, Backtest: false
  
  # ⭐ NEW: Duplicate Entry Policy
  allow_duplicate_entry: false  # 기본값 (안전)
  duplicate_entry_policy: "reject"  # reject | average_down | pyramid
  max_duplicate_entries: 1

position_sizing:
  quality_weight_min: 0.5
  quality_weight_max: 1.5
  max_position_value: 10000
  min_position_value: 10
  
  # ⭐ NEW: Quality Weight Parameters
  quality_weight_slope: 1.2  # confidence 기울기
  
  context_scaling:
    enabled: true
    atr_low_pct: 0.004
    atr_high_pct: 0.02
    low_vol_mult: 1.2
    high_vol_mult: 0.7
    neutral_mult: 1.0

execution:
  fill_policy: next_open
  fees_bps: 10
  slippage:
    type: fixed
    bps: 5
  reject_cooldown_seconds: 60
  
  # ⭐ NEW: Min Qty by Symbol
  min_qty_by_symbol:
    BTCUSDT: 0.001
    ETHUSDT: 0.01
    default: 0.001
  
  # ⭐ NEW: Engine Parameters
  websocket_stabilize_sec: 2
  redis_ttl_buffer_pct: 1.05

exits:
  take_profits:
    - r_multiple: 1.0
      size_pct: 30
    - r_multiple: 2.0
      size_pct: 40
  trailing:
    type: atr
    k: 3.0
    move_to_break_even_at_r: 0.8
  time_exit_min: 360
  
  # ⭐ NEW: Volatility Regime Multipliers
  volatility_regime_multipliers:
    high_vol: 1.2
    neutral: 1.0
    low_vol: 0.9

flash_guard:
  enabled: true
  flash_pct: 0.03
  pause_candles: 3
  log_throttle_sec: 300
  
  # ⭐ NEW: Buffer Parameters
  buffer_size: 2

# ⭐ NEW: Signal Validation Parameters
signal_validation:
  enable_vol_spike_filter: true
  vol_spike_mult: 2.0
  enable_mtf_confirm: true
  require_htf_aligned: true

filters:
  regime_filter: true
  require_trend_align: true
  session_whitelist: ["asia", "europe", "us"]
```

---

### `configs/strategies/scalping.yml` (전략별)

```yaml
# ========================================
# SCALPING STRATEGY CONFIG
# ========================================

name: scalping
description: "BB 터치 + EMA 정렬 + MACD 크로스"

timeframe: 3m
lookback: 400

# Leverage (ATR 기반 동적)
leverage:
  min: 2
  max: 50
  default: 10

# Risk/Reward
atr_mult_sl: 1.5  # SL = ATR * 1.5
rr: 2.0           # TP = SL * 2.0

# ⭐ Strategy-specific: BB Parameters
bb_touch_upper_pct: 0.995
bb_touch_lower_pct: 1.005
bb_bounce_lower_now_mult: 1.003
bb_bounce_lower_prev_mult: 1.008
bb_bounce_upper_now_mult: 0.997
bb_bounce_upper_prev_mult: 0.992

# ⭐ Strategy-specific: RSI Parameters
rsi_min: 30
rsi_max: 70

# ⭐ Strategy-specific: Volume Parameters
volume_mult: 1.5
volume_filter_required: true

# ⭐ NEW: Volatility Regime Adjustments (전략별 오버라이드 가능)
volatility_adjustments:
  high_vol:
    atr_mult_sl: 1.8  # 1.5 * 1.2
    rr: 1.8           # 2.0 * 0.9 (TP 가깝게)
  low_vol:
    atr_mult_sl: 1.35  # 1.5 * 0.9
    rr: 2.2            # 2.0 * 1.1 (TP 멀게)

# Filters
filters:
  allow_short: true
  mtf_confirm: true
  regime: false  # 스캘핑은 레짐 무시
  volume_spike: true
  volume_spike_guard: false
```

---

### `configs/modes/backtest_raw.yml` (모드별)

```yaml
# ========================================
# BACKTEST_RAW MODE (PHASE9)
# ========================================
# 가드/필터 최소화 모드 - 순수 전략 성향 확인용

execution:
  fill_policy: next_open
  fees_bps: 10
  slippage:
    type: fixed
    bps: 5
  cooldown_minutes: 0  # ⭐ 전역 쿨다운 제거

risk:
  flash_guard: false
  stop_outlier: true
  max_consecutive_losses: 99999
  max_daily_loss_pct: 50.0
  extreme_loss_cutoff_pct: -60.0
  
  # ⭐ PHASE9-1 FIX
  max_exposure_per_symbol: 0.99  # 99% (거의 무제한)

portfolio:
  max_strategy_positions: 50
  max_total_exposure: 0.99
  max_positions: 50
  load_existing: false  # ⭐ 완전 격리
  symbol_cooldown_seconds: 0
  allow_duplicate_entry: true  # ⭐ 연구용 (중복 허용)

# ⭐ 전역 필터 OFF
signal_validation:
  enable_vol_spike_filter: false
  enable_mtf_confirm: false

filters:
  regime_filter: false
  require_trend_align: false
  mtf_confirm: false
  volume_spike: false
  session_whitelist: []
```

---

### `configs/modes/backtest_clean.yml` (모드별)

```yaml
# ========================================
# BACKTEST_CLEAN MODE (PHASE8)
# ========================================
# 안전 가드 활성화 모드 (PAPER/LIVE 근접)

execution:
  fill_policy: next_open
  fees_bps: 10
  slippage:
    type: fixed
    bps: 5

risk:
  flash_guard: true
  max_consecutive_losses: 4
  max_daily_loss_pct: 2.0
  extreme_loss_cutoff_pct: -20.0
  max_exposure_per_symbol: 0.3  # 30%

portfolio:
  max_strategy_positions: 5
  max_total_exposure: 0.95
  max_positions: 20
  load_existing: false  # ⭐ Backtest는 격리
  allow_duplicate_entry: false  # 안전

signal_validation:
  enable_vol_spike_filter: true
  enable_mtf_confirm: true

filters:
  regime_filter: true
  require_trend_align: true
  session_whitelist: ["asia", "europe", "us"]
```

---

### `configs/modes/paper.yml` (모드별)

```yaml
# ========================================
# PAPER MODE
# ========================================
# LIVE 동일 로직, 단 실제 주문 없음

execution:
  fill_policy: next_open  # Paper는 시뮬레이션
  fees_bps: 10
  slippage:
    type: adaptive  # 실시간 슬리피지 추정

risk:
  flash_guard: true
  max_consecutive_losses: 4
  cooldown_after_consecutive: 30
  max_daily_loss_pct: 2.0

portfolio:
  load_existing: true  # ⭐ Paper는 기존 포지션 로드
  allow_duplicate_entry: false

signal_validation:
  enable_vol_spike_filter: true
  enable_mtf_confirm: true

filters:
  regime_filter: true
  session_whitelist: ["asia", "europe", "us"]
```

---

### `configs/modes/live.yml` (모드별)

```yaml
# ========================================
# LIVE MODE (⚠️ PRODUCTION)
# ========================================
# 최대 보수적 설정

execution:
  fill_policy: market  # 즉시 체결
  fees_bps: 10
  slippage:
    type: adaptive

risk:
  flash_guard: true
  max_consecutive_losses: 3  # ⚠️ 더 보수적
  cooldown_after_consecutive: 60  # ⚠️ 1시간
  max_daily_loss_pct: 1.0  # ⚠️ 1% (보수적)
  extreme_loss_cutoff_pct: -10.0  # ⚠️ -10%

portfolio:
  max_strategy_positions: 3  # ⚠️ 더 보수적
  max_total_exposure: 0.8  # ⚠️ 80%
  load_existing: true
  allow_duplicate_entry: false

signal_validation:
  enable_vol_spike_filter: true
  enable_mtf_confirm: true

filters:
  regime_filter: true
  require_trend_align: true
  session_whitelist: ["asia", "europe", "us"]
```

---

## 🔧 코드 수정 포인트 (PHASE9-3~5)

### 1. Engine: 중복 진입 방지 (PHASE9-3)

#### AS-IS (하드코딩)
```python
# execution/engine.py:1231-1233
same_direction_positions = [...]
if same_direction_positions:
    logger.warning("⚠️ [중복 진입 방지] ...")
    continue  # ⚠️ 무조건 차단
```

#### TO-BE (Config 제어)
```python
# execution/engine.py
allow_dup = config.get('portfolio', {}).get('allow_duplicate_entry', False)
dup_policy = config.get('portfolio', {}).get('duplicate_entry_policy', 'reject')

same_direction_positions = [...]

if same_direction_positions and not allow_dup:
    if dup_policy == 'reject':
        logger.warning("⚠️ [중복 진입 방지] 신호 스킵")
        continue
    elif dup_policy == 'average_down':
        # 평균 단가 하향 로직
        logger.info("📊 [평균화] 기존 포지션에 추가")
        # ... (추가 구현)
    elif dup_policy == 'pyramid':
        # 피라미딩 로직
        logger.info("📈 [피라미딩] 기존 포지션 확장")
        # ... (추가 구현)
```

---

### 2. TP Manager: 변동성 레짐 배수 (PHASE9-3)

#### AS-IS (하드코딩)
```python
# execution/tp_manager.py:76-80
vol_mult = 1.0
if volatility_regime == 'high_vol':
    vol_mult = 1.2  # ⚠️ 하드코딩
elif volatility_regime == 'low_vol':
    vol_mult = 0.9  # ⚠️ 하드코딩
```

#### TO-BE (Config 제어)
```python
# execution/tp_manager.py
vol_mults = self.config.get('exits', {}).get('volatility_regime_multipliers', {
    'high_vol': 1.2,
    'neutral': 1.0,
    'low_vol': 0.9
})

vol_mult = vol_mults.get(volatility_regime, 1.0)
adjusted_one_r = one_r * vol_mult
```

---

### 3. Position Sizer: Quality Weight (PHASE9-4)

#### AS-IS (하드코딩)
```python
# execution/position_sizer.py:180
base_weight = self.quality_weight_min + (confidence - 0.5) * 1.2  # ⚠️ 1.2 하드코딩
```

#### TO-BE (Config 제어)
```python
# execution/position_sizer.py
slope = self.config.get('position_sizing', {}).get('quality_weight_slope', 1.2)
base_weight = self.quality_weight_min + (confidence - 0.5) * slope
```

---

### 4. Risk Manager: Flash Buffer & Epsilon (PHASE9-4)

#### AS-IS (하드코딩)
```python
# execution/risk_manager.py:237, 341
if len(buf) >= 2:  # ⚠️ 하드코딩
    ...

epsilon = 0.1  # ⚠️ 하드코딩 (절대값)
```

#### TO-BE (Config 제어)
```python
# execution/risk_manager.py
flash_buffer_size = self.config.get('flash_guard', {}).get('buffer_size', 2)
if len(buf) >= flash_buffer_size:
    ...

epsilon_pct = self.config.get('risk', {}).get('exposure_epsilon_pct', 0.001)
epsilon = max_per_symbol * epsilon_pct  # 상대적 허용 오차
```

---

## 📊 리팩토링 단계별 계획

### PHASE9-3 (CRITICAL + HIGH)

**목표**: 중복 진입 & 변동성 레짐 배수 Config 이동

**작업 항목**:
1. `base.yml`에 `portfolio.allow_duplicate_entry`, `exits.volatility_regime_multipliers` 추가
2. `engine.py:1231` 중복 진입 방지 로직 수정
3. `tp_manager.py:76` 변동성 레짐 배수 config 읽기
4. `strategies/scalping.py:165` 변동성 조정 config 읽기
5. 10월 backtest 재실행 검증

**예상 결과**:
- backtest_raw: `allow_duplicate_entry: true` → 거래 빈도 증가
- backtest_clean: `allow_duplicate_entry: false` → 거래 빈도 유지

---

### PHASE9-4 (MED)

**목표**: Quality Weight, Flash Buffer Config 이동

**작업 항목**:
1. `position_sizer.py:180` 품질 가중치 기울기 config 읽기
2. `risk_manager.py:237` Flash 버퍼 크기 config 읽기
3. `risk_manager.py:341` Epsilon % 방식으로 변경
4. Backtest 재실행 검증

---

### PHASE9-5 (LOW)

**목표**: 나머지 하드코딩 제거

**작업 항목**:
1. `execution/broker/*`: 최소 수량 심볼별 설정
2. `engine.py:69`: WebSocket 대기 시간 config
3. `engine.py:155`: Redis TTL 버퍼 config
4. 최종 회귀 테스트

---

### PHASE9-6 (안정화)

**목표**: 회귀 테스트 & 안정화

**작업 항목**:
1. 10월/11월/12월 전체 재백테스트
2. Paper 모드 7일 실행 (안정성 검증)
3. Config Validation 강화 (스키마 검증)
4. 문서화 완료 (SCALPING_STRATEGY_MAP, ENGINE_HARDCODE_REPORT 업데이트)

---

## 🎯 최종 목표

### 달성 기준

✅ **Zero Hard-coding**: 모든 파라미터 config 제어 가능  
✅ **Mode Agnostic**: Backtest = Paper = Live (어댑터만 교체)  
✅ **Single Source**: Config가 유일한 진리의 원천  
✅ **Reproducibility**: 동일 config → 동일 결과 보장

### 기대 효과

1. **백테스트 신뢰성**: 하드코딩 제거 → Paper/Live와 동일 로직
2. **튜닝 효율성**: Config만 변경 → 코드 수정 불필요
3. **실험 안전성**: `backtest_raw` vs `backtest_clean` 비교 가능
4. **배포 안정성**: Config 검증 → 실수 최소화

---

*Generated: PHASE9-2*  
*Status: ✅ TO-BE 설계 완료*
