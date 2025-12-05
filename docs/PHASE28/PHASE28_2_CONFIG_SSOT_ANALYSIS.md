# PHASE28-2: Config SSOT 분석 및 필수 키 목록

## 1. 엔진/PositionSizer/PortfolioManager 필수 Config 키

### Engine (execution/engine.py)
```python
# 라인 453-456
config["timeframe"]           # 필수
config["lookback"]            # 필수
config["equity"]              # 필수
config["risk"]["per_trade"]   # 필수 (라인 456)
config.get("execution", {}).get("reject_cooldown_seconds", 60)  # Optional, default 60
```

### PositionSizer (execution/position_sizer.py)
```python
# __init__ (라인 41-50)
config['capital']['initial']                      # 필수
config['risk']['per_trade']                       # 필수
config['position_sizing']['quality_weight_min']   # 필수
config['position_sizing']['quality_weight_max']   # 필수
config['position_sizing']['max_position_value']   # 필수
config['position_sizing']['min_position_value']   # 필수

# calculate (라인 505)
config['risk']['max_positions']                   # 필수
```

### PortfolioManager (execution/portfolio_manager.py)
- 분석 필요: `max_symbol_exposure_pct`, `max_exposure_pct`, `max_total_exposure` 등

### RiskManager
- 분석 필요: `max_exposure_per_symbol`, `max_total_exposure` 등

---

## 2. Config 파일 비교

### A. phase28_1_btc5m_baseline_presets.yml (PHASE28-1, 수정됨)
- **상태**: 일부 키 추가됨 (per_trade, quality_weight_*, min/max_position_value)
- **문제**: 여전히 불완전, 실행 중 KeyError 발생

### B. phase27_5_baseline_replay_30d.yml (PHASE27-5 Golden Config)
- **상태**: 30일 replay에서 검증됨
- **문제**: `risk.per_trade` 없음 → 엔진에서 KeyError 발생 가능

### C. phase28_2_btc5m_tuning_base.yml (현재 튜닝 base)
- **상태**: PHASE27-5 복사본 + 일부 패치
- **문제**: 여전히 불완전

---

## 3. 필수 키 통합 목록 (Canonical SSOT)

튜닝 base config가 반드시 포함해야 하는 키들:

```yaml
# === CORE ===
mode: backtest
env: backtest
symbol: BTCUSDT
timeframe: 5m
lookback: 1000

# === CAPITAL ===
capital:
  initial: 50000

equity: 50000

# === BACKTEST ===
backtest:
  symbol: BTCUSDT
  data_dir: data
  data_file: BTCUSDT_5m_2024-01-01_2024-12-31.csv
  start_date: "2024-11-30"
  end_date: "2024-12-30"

# === STRATEGY ===
strategy:
  selector: btc5m_baseline_v1
  use_ensemble: false

# === STRATEGIES (PHASE27/28 구조) ===
strategies:
  btc5m_baseline_v1:
    # ... 전략 파라미터 (튜닝으로 override됨)

# === EXECUTION ===
execution:
  order_type: MARKET
  timeout_sec: 30
  reject_cooldown_seconds: 60

# === POSITION SIZING ===
position_sizing:
  default_risk_per_trade: 0.02
  mode: kelly_fraction
  kelly_fraction: 0.25
  leverage: 3.0
  min_position_size: 0.001
  max_position_size: 10.0
  quality_weight_min: 0.5        # ⚠️ 필수
  quality_weight_max: 1.5        # ⚠️ 필수
  min_position_value: 100.0      # ⚠️ 필수
  max_position_value: 15000.0    # ⚠️ 필수
  multi_position_scaling: true
  exposure_reduction_factor: 0.95
  allow_partial_entry: true

# === RISK ===
risk:
  per_trade: 0.02                 # ⚠️ 필수 (engine.py 요구)
  max_positions: 3                # ⚠️ 필수 (position_sizer.py 요구)
  max_open_positions: 3
  max_risk_per_trade: 0.03
  max_portfolio_risk: 0.1
  max_daily_loss: 0.05
  max_consecutive_losses: 5
  drawdown_threshold: 0.15
  risk_free_rate: 0.0
  max_exposure_per_symbol: 0.3    # ⚠️ PortfolioManager/RiskManager 요구
  max_total_exposure: 0.6         # ⚠️ PortfolioManager/RiskManager 요구

# === PORTFOLIO ===
portfolio:
  initial_balance: 50000.0
  currency: USDT
  max_open_positions: 3
  max_symbol_exposure_pct: 30     # ⚠️ 필수
  max_exposure_pct: 60            # ⚠️ 필수
  max_total_exposure: 0.6         # ⚠️ 필수
  max_strategy_positions: 2
  use_dynamic_exposure: true
  use_dynamic_budget: true
  symbol_cooldown_seconds: 60

# === EXITS ===
exits:
  use_trailing_stop: false
  trailing_stop_pct: 0.02
  use_time_exit: true
  max_hold_minutes: 180
  emergency_exit:
    enabled: true
    loss_threshold: 0.10

# === FLOW GUARDIAN ===
flow_guardian:
  enabled: true
  cooldown:
    enabled: true
    seconds: 15
  entry_filter:
    enabled: true
  position_block:
    enabled: true

# === MONITORING (optional) ===
monitoring:
  prometheus:
    enabled: false
  redis:
    enabled: false
```

---

## 4. Worker Default 제거 전략

현재 `tuning/cluster/worker.py`에 추가된 default 삽입 로직 (라인 221-241):
```python
# PHASE28-2-FIX: 필수 config 키 default 값 보장
if 'risk' not in config:
    config['risk'] = {}
config['risk'].setdefault('per_trade', 0.02)
config['risk'].setdefault('max_positions', 3)
# ... 등등
```

**제거 전략**:
1. base config를 완전하게 만들어서 이 로직이 필요 없게 한다
2. 대신 `_validate_tuning_config(config)` 함수를 추가해 명확한 에러 메시지 제공
3. Validation에서 실패하면 즉시 ConfigError 발생

---

## 5. 다음 단계

1. `phase28_2_btc5m_tuning_base.yml`을 위 SSOT 목록으로 재작성
2. Worker에 config validation 추가, default 땜빵 제거
3. 단일 trial 스모크 테스트로 Trades > 0 검증
4. Random Search 3 trials 재실행
