# PHASE16 Execution Plan — 12-Hour Paper Trading Test

## 📋 Overview

**Phase**: PHASE16 - 12-Hour Paper Trading Validation  
**Start Date**: 2024-11-16 20:18 UTC+09:00  
**Duration**: 12 hours  
**Status**: 🟡 **IN PROGRESS**  
**Goal**: PHASE15 Best 파라미터 Paper Trading 검증

---

## 🎯 Objectives

### Primary Goal
**PHASE15 Best 파라미터의 실시간 Paper Trading 성능 검증**

### Success Criteria
| Metric | Target | Status |
|--------|--------|--------|
| **Runtime** | 12 hours | 🟡 Running |
| **Trades** | 5~20 | ⏳ Pending |
| **Winrate** | 25%+ | ⏳ Pending |
| **Max DD** | < 25% | ⏳ Pending |
| **Errors** | 0 | ⏳ Pending |
| **Cooldown Suppression** | 100% | ⏳ Pending |

---

## 🔒 PHASE15 Best Parameters (Locked)

```yaml
# PHASE15 Best Trial #8 (Immutable in PHASE16)
rsi_oversold: 27
rsi_overbought: 71
ema_fast: 8
ema_slow: 32
max_cross_age_candles: 10
momentum_lookback: 6
volume_mult: 1.213
rr: 1.254
atr_mult_sl: 1.272
max_hold_minutes: 23
allow_short: false
```

**주의**: 이 파라미터는 PHASE16에서 절대 변경 불가

---

## 📊 Paper Trading Architecture

### Engine Configuration
```
Mode: paper (dry-run, no real API calls)
Namespace: paper:phase16
Slippage: Fixed 0.01%
Exposure: Managed by portfolio_manager
Cooldown: Enforced by execution/engine.py
```

### Redis Tracking
```
paper:phase16:state        → Engine state (running/stopped/error)
paper:phase16:positions    → Active positions
paper:phase16:metrics      → Performance metrics
paper:phase16:errors       → Error log
paper:phase16:cooldowns    → Cooldown tracking
```

### Logging
```
logs/paper_phase16/<timestamp>/
├── application.log         → Main log
├── trades.log              → Trade events
└── signals.log             → Signal events
```

### Scorecards
```
scorecards/paper_phase16/<timestamp>/
├── scorecard.csv           → Final metrics
└── trades_detail.csv       → Trade details
```

---

## 🚀 Execution Flow

### 1. Initialization (T+0)
```
✓ Load PHASE15 Best parameters from active.yml
✓ Initialize Paper Engine (dry-run mode)
✓ Setup Redis namespaces
✓ Create log directories
✓ Start monitoring dashboard
```

### 2. Paper Trading (T+0 to T+12h)
```
✓ Real-time market data ingestion
✓ Signal generation (EMA/RSI/Volume)
✓ Order placement (dry-run)
✓ Position tracking
✓ RR/SL/TP management
✓ Cooldown enforcement
✓ Event logging
```

### 3. Monitoring (Continuous)
```
✓ Redis state updates (every 10s)
✓ Console dashboard refresh
✓ Error detection & logging
✓ Periodic snapshots (every 1h)
```

### 4. Finalization (T+12h)
```
✓ Stop engine gracefully
✓ Generate final scorecard
✓ Save trade details
✓ Generate PHASE16_PAPER_REPORT.md
✓ Commit results to Git
```

---

## 📈 Expected Outcomes

### Paper Trading Metrics (Estimated)
```
Based on PHASE15 OOS performance:
- Trades: 5~20 (12h window)
- Winrate: 25~30%
- Max DD: 15~25%
- Profit Factor: 0.15~0.20
```

### Success Indicators
✅ Engine runs stably for 12 hours  
✅ No critical errors  
✅ Cooldown suppression working  
✅ Position tracking accurate  
✅ Metrics recorded correctly  

---

## 🛠️ Required Scripts

### 1. `scripts/run_paper_phase16.py`
- Launches Paper Engine with PHASE15 parameters
- Runs for 12 hours
- Streams metrics to Redis
- Handles graceful shutdown

### 2. `scripts/check_paper_phase16.py`
- Queries Redis for current state
- Displays positions, metrics, errors
- One-time snapshot

### 3. `scripts/monitor_phase16.py`
- Real-time console dashboard
- Updates every 10 seconds
- Shows state, positions, metrics, errors
- Runs continuously during paper trading

---

## 📁 Generated Files

```
docs/PHASE16/
├── PHASE16_EXECUTION_PLAN.md      ✅ (this file)
└── PHASE16_PAPER_REPORT.md        ⏳ (auto-generated)

scripts/
├── run_paper_phase16.py            ⏳ (to create)
├── check_paper_phase16.py          ⏳ (to create)
└── monitor_phase16.py              ⏳ (to create)

logs/paper_phase16/
└── <timestamp>/
    ├── application.log
    ├── trades.log
    └── signals.log

scorecards/paper_phase16/
└── <timestamp>/
    ├── scorecard.csv
    └── trades_detail.csv
```

---

## ⚠️ Constraints & Safeguards

### Hard Constraints (NEVER MODIFY)
- ❌ Scalping strategy core logic
- ❌ Fresh Cross / Lookback structure
- ❌ EMA computation
- ❌ Risk Manager / Portfolio Manager
- ❌ execution/engine.py
- ❌ tuning_core.py
- ❌ configs/scalping/active.yml

### Safeguards
✅ Paper mode only (no real API calls)  
✅ Fixed slippage (0.01%)  
✅ Exposure limits enforced  
✅ Cooldown suppression active  
✅ Error handling & logging  

---

## 📊 Monitoring Dashboard

### Console Output (Real-time)
```
═══════════════════════════════════════════════════════════════
🟢 PHASE16 Paper Trading — 12h Test
═══════════════════════════════════════════════════════════════

⏱️  Runtime: 2h 15m / 12h (18.75%)
📊 State: RUNNING

📈 Metrics:
   Trades: 3 | Winrate: 66.7% | Max DD: -8.5% | PF: 0.45

💼 Positions:
   BTCUSDT LONG: Entry=94500, TP=95679, SL=93500 (RR=1.254)

🔄 Cooldowns:
   scalping: 45s remaining

⚠️  Errors: 0

═══════════════════════════════════════════════════════════════
```

---

## 🎯 Next Steps

### During PHASE16 (12h)
1. Monitor console dashboard
2. Check Redis state periodically
3. Watch for errors
4. Verify cooldown suppression

### After PHASE16 (T+12h)
1. Generate final scorecard
2. Create PHASE16_PAPER_REPORT.md
3. Analyze results
4. Decide: Continue to PHASE17 or iterate

### PHASE17 (Production Deployment)
- Deploy to live trading (if results positive)
- Real API integration
- Continuous monitoring

---

## 📝 Execution Timeline

| Time | Event | Status |
|------|-------|--------|
| T+0 | Start Paper Engine | 🟡 Starting |
| T+1h | First snapshot | ⏳ Pending |
| T+6h | Mid-point check | ⏳ Pending |
| T+12h | Stop & Generate Report | ⏳ Pending |

---

## 🔗 Related Documents

- [PHASE15_EXECUTION_PLAN.md](../PHASE15/PHASE15_EXECUTION_PLAN.md) — Previous phase results
- [PHASE14_EXECUTION_PLAN.md](../PHASE14/PHASE14_EXECUTION_PLAN.md) — Tuning baseline

---

*Last Updated: 2024-11-16 20:18 UTC+09:00*
*Status: 🟡 IN PROGRESS*
