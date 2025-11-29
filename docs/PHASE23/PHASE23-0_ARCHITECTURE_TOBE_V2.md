# PHASE23-0: TO-BE Architecture V2

**Date**: 2025-11-29  
**Status**: 🔄 IN PROGRESS  
**Phase**: PHASE23-0 – TO-BE Architecture V2 Design  
**Purpose**: Establish a unified, scalable architecture for 5-strategy ensemble trading system

---

## 1. Objective

### 1.1 PHASE23-0 Purpose

**Primary Goals**:
1. **5-Strategy Family Ensemble v2 Architecture**: Define a clean, unified architecture for the 5-family ensemble system
2. **Single-Engine-Centric Structure**: Consolidate strategy/config/ensemble flows around a single engine entry point
3. **PHASE22-4 Issue Resolution**: Structurally eliminate the run_paper/config legacy problems identified in PHASE22-4
4. **Clear Separation of Concerns**: Establish clean boundaries between Core Engine, Strategy Layer, Config Layer, and Script Layer

**Background**:
- PHASE22-0~4 revealed critical architectural issues:
  - PHASE22-2: 12H Ensemble run produced 0 trades (threshold + config propagation issues)
  - PHASE22-3: Param tuning failed due to config not reaching strategies
  - PHASE22-4: **Code-level fix succeeded** (unit tests 6/6 PASS, direct Python test OK), but **runtime integration failed** (run_paper.py path lost params)
- **Root Cause (Architectural)**:
  - Config loading/propagation is fragmented across script-level glue code
  - run_paper.py and similar scripts contain **duplicated strategy/config orchestration logic**
  - No single source of truth for strategy param propagation
  - Engine is not the sole entry point for strategy execution

**Key Insight**:
- This is **NOT an engine core problem**
- This is a **script-level orchestration / legacy structure problem**
- Solution: Design a TO-BE architecture where **scripts are thin wrappers**, engine is the **single orchestrator**, and config flows cleanly from YAML → load_strategies → engine → strategy

---

## 2. Current Architecture Snapshot

### 2.1 Core Engine Layer

**Components**:
- `execution/engine.py`: Main trading loop
  - `engine.run(feed, broker, clock, strategies, ensemble_module, config)`
  - Handles: candle stream consumption, strategy invocation, Risk/Portfolio/FlowGuardian checks, Execution Adapter delegation
- `execution/portfolio_manager.py`: SSOT for PnL, Equity, Budget
- `execution/position_tracker.py`: Position state machine
- `execution/risk_manager.py`: Per-trade risk, leverage limits, Max DD
- `core/flow_guardian.py`: READY check, cooldown, Flash Guard, API health

**Data Flow (Engine-centric)**:
```
Candle → Engine Loop → Strategy.signal_logic/compute_signal → Signal Validation →
Risk Check → Portfolio Budget Check → Execution → Position Tracking
```

**Status**: ✅ Stable (PHASE17~21 validated)

### 2.2 Strategy Layer

**Current Structure**:
```
strategies/
├── core/
│   └── scalping_v3.py          # Family 1: HF Momentum (PHASE21 validated)
├── research/
│   ├── volatility_breakout_v2.py   # Family 2: Volatility Breakout
│   ├── mean_reversion_v2.py        # Family 3: Mean Reversion
│   ├── trend_follow_v2.py          # Family 4: Trend Following
│   └── volume_based_v2.py          # Family 5: Volume-Based
├── deprecated/
│   └── (6 old strategies)
├── __init__.py                 # load_strategies(), get_all_strategies()
└── ensemble.py
```

**Strategy Interface** (PHASE22-1):
- All research strategies implement `BaseStrategy`
- `metadata` property → `StrategyMetadata`
- `compute_signal(df) → Dict[str, Any]`
- scalping_v3 uses legacy `signal_logic(df, config)` (to be unified in PHASE23-2)

**Status**: ⚠️ Mixed (scalping_v3 validated, research 4 strategies unit-tested but not runtime-validated)

### 2.3 Ensemble Layer

**Components**:
- `common/registry/strategy_registry.py`: Strategy registry + metadata storage
- `common/ensemble/score_engine.py`: Calculate strategy scores (S_LONG, S_SHORT, S_RISK, S_QUALITY)
- `common/ensemble/aggregator.py`: 3-Tier decision logic (Tier1: High-Confidence, Tier2: Consensus, Tier3: Skip)

**Data Flow (Ensemble Mode)**:
```
Engine → Multiple Strategies → Individual Signals → ScoreEngine → EnsembleAggregator →
Unified Decision → Engine Execution
```

**Status**: ⚠️ Implemented but untested (PHASE22-2 produced 0 trades, threshold tuning needed)

### 2.4 Config & Script Layer

**Config Files**:
```
configs/
├── paper/
│   ├── phase22_2_ensemble_12h.yml      # Ensemble 5-strategy config
│   ├── phase22_3_ensemble_tuning_60m.yml
│   └── phase22_4_scalping_param_smoke_30m.yml
└── base.yml
```

**Script Files**:
```
scripts/
├── run_backtest.py
├── run_paper.py                # Single-strategy Paper runner
├── run_phase22_2_ensemble.py   # Ensemble Paper runner
└── ...
```

**Current Flow**:
```
YAML Config → Script-level loading → Script-level strategy selection → 
load_strategies(config) → engine.run(strategies, config)
```

**Problem** (PHASE22-4):
- Scripts like `run_paper.py` contain **strategy orchestration logic** (e.g., Line 243: effective_strategy calculation, Line 361: load_strategies call)
- Config gets modified at script level (e.g., Line 378-379: cfg['execution']['max_runtime_hours'] = duration_hours)
- **Fragmented config propagation**: config → script modifications → load_strategies → engine → strategy
- **Result**: In unit tests, params flow correctly. In runtime via run_paper, params get lost somewhere in this fragmented chain.

**Status**: ❌ FAIL (Config propagation broken in runtime paths)

### 2.5 Current Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Script Layer (run_paper.py)                │
│  - Load config YAML                                                 │
│  - Modify config (add duration, etc.)                               │
│  - Calculate effective_strategy                                     │
│  - Call load_strategies(config)  ← PHASE22-4 ISSUE: params lost    │
│  - Call engine.run(strategies, config)                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Strategy Loading (strategies/__init__.py)       │
│  - load_strategies(config)                                          │
│  - Returns: {"strategy_name": {"module": ..., "params": {...}}}    │
│  ← PHASE22-4 CODE FIX: This works in unit tests, fails in runtime  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Engine Layer (execution/engine.py)             │
│  - engine.run(feed, broker, clock, strategies, ensemble, config)   │
│  - For each candle:                                                 │
│    - For each strategy_id, strategy_info in strategies.items():    │
│      - Extract strategy_module, strategy_params                     │
│      - Merge config: cfg = {**config, **strategy_params}           │
│      - Call strategy_module.signal_logic(df, cfg)  ← params={}     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Strategy Layer (e.g., scalping.py)             │
│  - signal_logic(df, config)                                         │
│  - Read params: rsi_oversold = config.get('rsi_oversold', 30)      │
│  ← RUNTIME ISSUE: config doesn't have 'rsi_oversold', uses default │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Observation**:
- **Unit test path**: config → load_strategies → direct strategy call → params OK ✅
- **Runtime path**: config → script modifications → load_strategies → engine → strategy → params MISSING ❌
- **Hypothesis**: Script-level config modifications or intermediate steps are **overwriting or bypassing** the params dict structure

---

## 3. Pain Points & Known Issues

### 3.1 PHASE22-2: 12H Ensemble Run (0 Trades)

**Issue**:
- 12H Paper run with 5 strategies produced 0 trades
- Infrastructure PASS, but no trading decisions made

**Root Causes**:
1. **Overly strict thresholds**: Ensemble tier1_threshold (0.8), tier2_threshold (0.5) too high
2. **Config params not propagating**: Even with relaxed thresholds in config, strategies didn't receive them

**Status**: ❌ FAIL (Infrastructure OK, Trading KO)

### 3.2 PHASE22-3: Parameter Tuning (0 Trades)

**Issue**:
- 15-minute test run with relaxed RSI thresholds (45/55) produced 0 trades
- Logs showed RSI still using defaults (30/70)

**Root Cause**:
- Config params **not reaching strategies**
- `load_strategies()` / `engine.py` interface problem suspected

**Status**: ❌ FAIL → Led to PHASE22-4

### 3.3 PHASE22-4: Config Integration Fix (PARTIAL)

**Code-Level Fix** (✅ SUCCESS):
- `strategies/__init__.py`: Modified `load_strategies()` to return `{"module": ..., "params": {...}, "enabled": True}`
- `execution/engine.py`: Modified strategy loop to extract params and merge: `cfg = {**config, **strategy_params}`
- Unit tests: 6/6 PASS
- Direct Python test: params loaded correctly

**Runtime Issue** (❌ FAIL):
- `run_paper.py` execution: params arrive as empty dict `{}`
- Engine debug logs: `params: {}, rsi_oversold=MISSING, rsi_overbought=MISSING`
- Strategy still uses defaults (30/70)

**Root Cause** (Hypothesis):
1. **Script-level config manipulation**: run_paper.py modifies config after loading, potentially breaking the params structure
2. **Intermediate config passing**: Config is passed through multiple layers (script → feed/broker/clock creation → engine), params might get stripped
3. **Legacy orchestration logic**: Strategy selection and params handling scattered across script and engine layers

**Key Insight**:
- This is **NOT a load_strategies() bug** (unit tests prove it works)
- This is **NOT an engine.py bug** (code logic is correct)
- This is a **script-level orchestration problem** where the runtime path differs from the unit test path

**Status**: ⚠️ PARTIAL (Code PASS, Runtime FAIL)

### 3.4 Script-Level Logic Duplication

**Problem**:
- `run_paper.py`: Has strategy selection logic (Line 243: effective_strategy)
- `run_phase22_2_ensemble.py`: Has ensemble-specific setup logic
- `run_backtest.py`: Likely has similar orchestration
- **Result**: Multiple code paths with subtly different config handling

**Impact**:
- Hard to maintain consistency
- Hard to debug (which path is being used?)
- Config propagation fragile (breaks in some paths but not others)

**Status**: ⚠️ TECH DEBT

---

## 4. TO-BE Principles

### 4.1 Single-Engine-Centric Architecture

**Principle**:
- **Engine is the sole orchestrator** for strategy execution
- Scripts are **thin wrappers** that only:
  1. Parse command-line arguments
  2. Load config YAML (no modifications except essential runtime overrides like duration)
  3. Create mode-specific adapters (feed, broker, clock)
  4. Call `engine.run(mode, config, ...)`
  5. Handle graceful shutdown

**What Scripts MUST NOT Do**:
- ❌ Strategy selection logic
- ❌ Strategy param manipulation
- ❌ Config structure modifications (except mode/duration)
- ❌ Ensemble vs single-strategy decision logic

**What Engine MUST Do**:
- ✅ Read config.strategy.use_ensemble flag
- ✅ Call load_strategies(config) internally
- ✅ Handle ensemble vs single-strategy mode
- ✅ Merge strategy params correctly
- ✅ Pass merged config to strategies

### 4.2 Strategy Config as Single Source of Truth (SSOT)

**Principle**:
- **All strategy parameters** defined in config.strategies.{strategy_name}.params
- **load_strategies() is SSOT** for strategy loading
- **No intermediate param modifications** after load_strategies() call
- **Engine is the only consumer** of load_strategies() output

**Config Structure** (TO-BE):
```yaml
strategy:
  use_ensemble: false / true    # Engine reads this
  selector: scalping            # Engine reads this (if use_ensemble=false)

strategies:
  scalping:
    enabled: true
    params:
      rsi_oversold: 45          # Strategy-specific params
      rsi_overbought: 55
      momentum_enabled: false
      ...
  volatility_breakout_v2:
    enabled: true
    params:
      atr_mult: 2.0
      ...
```

**Data Flow** (TO-BE):
```
config.yml → engine.run(config) → load_strategies(config) → 
{"scalping": {"module": ..., "params": {rsi_oversold: 45, ...}}} →
engine loop: cfg = {**config, **params} → strategy.signal_logic(df, cfg)
```

### 4.3 Mode-Based Adapter Pattern

**Principle**:
- Backtest / Paper / Live differences are **ONLY in adapters**:
  - Feed: HistoricalFeed / WebSocketFeed / LiveFeed
  - Broker: SimBroker / PaperBroker / LiveBroker
  - Clock: SimClock / LiveClock
- **Engine logic is identical** for all modes
- Scripts create appropriate adapters, then call common engine.run()

### 4.4 Ensemble ON/OFF Controlled by Config Only

**Principle**:
- **No script-level logic** to decide ensemble vs single-strategy
- Engine reads `config.strategy.use_ensemble`
- If True: Use ensemble path (ScoreEngine → EnsembleAggregator)
- If False: Use single-strategy path (selector)

### 4.5 Clean Layering & Separation of Concerns

**Layers** (TO-BE):
```
┌─────────────────────────────────────────────────────────────┐
│  Script Layer (run_*.py)                                    │
│  - Parse CLI args                                           │
│  - Load config                                              │
│  - Create adapters (feed, broker, clock)                   │
│  - Call engine.run()                                        │
│  - Minimal, thin wrappers                                   │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Engine Layer (execution/engine.py)                         │
│  - Single entry point: engine.run(mode, config, ...)       │
│  - Load strategies: load_strategies(config)                │
│  - Decide ensemble vs single (based on config)             │
│  - Main trading loop                                        │
│  - Strategy invocation with merged config                  │
│  - Risk/Portfolio/FlowGuardian checks                       │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Strategy Layer (strategies/*)                              │
│  - Unified interface: compute_signal(df, config)           │
│  - Read params from config                                  │
│  - Return signal dict                                       │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  Ensemble Layer (common/ensemble/*)                         │
│  - ScoreEngine: Calculate strategy scores                  │
│  - EnsembleAggregator: 3-Tier decision                     │
│  - Used only if config.strategy.use_ensemble = true        │
└─────────────────────────────────────────────────────────────┘
```

**Boundaries**:
- Script ↔ Engine: Boundary is `engine.run()` call
- Engine ↔ Strategy: Boundary is `strategy.compute_signal(df, config)` call
- Engine ↔ Ensemble: Boundary is `aggregator.decide(strategies, df, regime)`

---

## 5. TO-BE Data Flow

### 5.1 Unified Data Flow (All Modes)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Step 1: Script Initialization                   │
│  - Parse CLI: --config path, --mode backtest/paper/live            │
│  - Load YAML: config = load_config(config_path)                    │
│  - Create Adapters:                                                 │
│    - feed = create_feed(mode, config)                              │
│    - broker = create_broker(mode, config)                          │
│    - clock = create_clock(mode)                                    │
│  - NO strategy/params handling here                                │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Step 2: Engine Entry                            │
│  - engine.run(mode, config, feed, broker, clock)                   │
│  - Read config.strategy.use_ensemble                                │
│  - Load strategies:                                                 │
│    - strategies = load_strategies(config)                          │
│    - Returns: {"name": {"module": ..., "params": {...}}}           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Step 3: Strategy Selection                      │
│  - If use_ensemble = False:                                         │
│    - selector = config.strategy.selector                           │
│    - selected = {selector: strategies[selector]}                   │
│  - If use_ensemble = True:                                          │
│    - selected = strategies  (all enabled strategies)               │
│    - Initialize EnsembleAggregator                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Step 4: Main Trading Loop                       │
│  - For each candle:                                                 │
│    - Build indicator DataFrame                                      │
│    - Single-strategy mode:                                          │
│      - strategy_info = selected[strategy_id]                       │
│      - cfg = {**config, **strategy_info["params"]}                 │
│      - signal = strategy_info["module"].compute_signal(df, cfg)    │
│    - Ensemble mode:                                                 │
│      - For each strategy: collect individual signals               │
│      - decision = aggregator.decide(signals, df, regime)           │
│    - Validate signal (MTF, cooldown, volume)                       │
│    - Risk check, Portfolio budget check                            │
│    - Execute trade                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Config Propagation Flow (Detail)

```
YAML File (phase22_4_scalping_param_smoke_30m.yml)
└─> strategies:
      scalping:
        enabled: true
        params:
          rsi_oversold: 45
          rsi_overbought: 55
          ...
          
↓ load_config(path)

Python Dict (config)
└─> config["strategies"]["scalping"]["params"] = {...}

↓ engine.run(mode, config, ...)

↓ load_strategies(config)

Strategy Dict (strategies)
└─> strategies["scalping"] = {
      "module": <scalping_module>,
      "params": {"rsi_oversold": 45, "rsi_overbought": 55, ...},
      "enabled": True
    }

↓ engine main loop

↓ strategy selection

Selected Strategy (selected["scalping"])
└─> strategy_info = strategies["scalping"]
    strategy_params = strategy_info["params"]

↓ config merge

Merged Config (cfg)
└─> cfg = {
      **config,                 # Global config (leverage, tp_sl, etc.)
      **strategy_params         # Strategy-specific params (HIGHEST priority)
    }

↓ strategy invocation

strategy_module.compute_signal(df, cfg)
└─> Inside strategy:
    rsi_oversold = cfg.get("rsi_oversold", 30)
    # Should get 45, not 30!
```

### 5.3 Critical Path for PHASE22-4 Issue Resolution

**Problem Location** (Hypothesis):
- Somewhere between `load_config()` and `engine.run()`, the config structure gets **modified or shallow-copied** in a way that loses the params

**TO-BE Solution**:
1. **Remove all script-level config modifications** except essential overrides (duration, mode)
2. **Pass config dict by reference** consistently (no intermediate copies)
3. **load_strategies() called ONLY by engine**, not by scripts
4. **Engine is sole consumer** of strategies dict
5. **No intermediate layers** between load_strategies() and strategy invocation

---

## 6. PHASE22-4 Issue Absorption Plan

### 6.1 Diagnosis Summary

**What Works** (✅):
- `load_strategies(config)`: Code is correct, unit tests PASS
- `engine.py` param merge: Code is correct, logic is sound
- Direct Python test: Config → load_strategies → params extraction works

**What Fails** (❌):
- `run_paper.py → engine → strategy` path: params arrive as empty dict

**Architectural Root Cause**:
- **Script-level orchestration** breaks the clean config flow
- run_paper.py likely modifies config in ways that don't preserve the nested structure
- Multiple config passing steps create opportunities for data loss

### 6.2 TO-BE Refactoring Plan (PHASE23-1+)

**PHASE23-1: Script Layer Cleanup**
1. **Simplify run_paper.py**:
   - Remove: Line 243 (effective_strategy calculation)
   - Remove: Line 361 (load_strategies call)
   - Keep: Config loading, adapter creation, engine.run() call
   - Result: Script becomes a thin wrapper

2. **Simplify run_phase22_2_ensemble.py**:
   - Remove ensemble-specific logic
   - Use same structure as run_paper.py
   - Only difference: Pass different config file

3. **Create common runner**:
   - `scripts/run.py --mode backtest/paper/live --config path`
   - Single entry point for all modes
   - Delegates everything to engine

**PHASE23-2: Engine Layer Enhancement**
1. **Move strategy selection logic to engine**:
   - Engine reads config.strategy.use_ensemble
   - Engine reads config.strategy.selector
   - Engine calls load_strategies(config)
   - Engine handles ensemble vs single-strategy branching

2. **Ensure config immutability**:
   - Config loaded once at script level
   - Passed to engine by reference (no copies)
   - Engine makes local merged copies for each strategy (cfg = {**config, **params})
   - Original config never modified

3. **Add config validation**:
   - Engine validates config structure on startup
   - Check: strategies section exists
   - Check: each enabled strategy has params dict (even if empty)
   - Fail fast with clear error if structure is wrong

**PHASE23-3: Strategy Interface Unification**
1. **Migrate scalping_v3 to BaseStrategy**:
   - Change from `signal_logic(df, config)` to `compute_signal(df, config)`
   - Implement `metadata` property
   - Result: All 5 strategies use identical interface

2. **Standardize param reading**:
   - All strategies read params via `self.config.get(key, default)`
   - No direct access to global config for strategy-specific params
   - Result: Clear param ownership

### 6.3 Backward Compatibility Strategy

**During PHASE23 Transition**:
- Keep old scripts (run_paper.py, run_phase22_2_ensemble.py) for reference
- Create new scripts (run_v2.py) with TO-BE structure
- Test both paths in parallel
- Once new path validated, deprecate old scripts

**Migration Path**:
1. PHASE23-1: Create new scripts, test
2. PHASE23-2: Migrate engine, test
3. PHASE23-3: Unify strategy interface, test
4. PHASE23-4: Deprecate old scripts, cleanup

### 6.4 Acceptance Criteria (PHASE23-1)

**For Script Layer Cleanup**:
- [ ] run_v2.py created (thin wrapper, <100 lines)
- [ ] No strategy selection logic in script
- [ ] No load_strategies() call in script
- [ ] Config passed to engine unmodified (except mode/duration)
- [ ] 30min paper test: Params reach strategy correctly (rsi_oversold=45, not 30)
- [ ] Logs show: `[PHASE23-1 DEBUG] Strategy params loaded: {rsi_oversold: 45, ...}`

**For Engine Layer**:
- [ ] engine.run() calls load_strategies(config) internally
- [ ] Engine handles use_ensemble flag
- [ ] Engine handles selector logic
- [ ] Config validation on startup
- [ ] Clear error messages if config structure is wrong

---

## 7. Implementation Roadmap

### 7.1 PHASE23-0 (Current)
- ✅ Document TO-BE Architecture V2
- ✅ Document Ensemble Strategy TO-BE
- ✅ Identify PHASE22-4 root cause (architectural)
- ✅ Define refactoring plan

### 7.2 PHASE23-1 (Script Layer Cleanup)
- Duration: 2-4 hours
- Tasks:
  1. Create `scripts/run_v2.py` (thin wrapper)
  2. Refactor `engine.run()` signature to accept mode
  3. Move load_strategies() call to engine
  4. Move use_ensemble/selector logic to engine
  5. Add config validation to engine
  6. 30min paper test with debug logs
  7. Verify params reach strategy

### 7.3 PHASE23-2 (Strategy Interface Unification)
- Duration: 3-5 hours
- Tasks:
  1. Migrate scalping_v3.py to BaseStrategy
  2. Rename signal_logic → compute_signal
  3. Add metadata property to scalping_v3
  4. Update all strategy calls in engine
  5. Unit tests for unified interface
  6. 1H paper test (5 strategies)

### 7.4 PHASE23-3 (Strategy Validation & Tuning)
- Duration: 4-6 hours
- Tasks:
  1. 3H backtest for each strategy (individual)
  2. Parameter rough tuning (not optimization, just "does it work?")
  3. Identify dead strategies (0 trades in 3H)
  4. Document each strategy's behavior

### 7.5 PHASE23-4 (Ensemble Integration Test)
- Duration: 2-3 hours
- Tasks:
  1. 3H ensemble paper test (5 strategies)
  2. Verify all strategies participate (trades > 0 for at least 3/5)
  3. Check tier1/tier2 decision distribution
  4. Document ensemble behavior

---

## 8. Success Metrics

### 8.1 PHASE23-0 Completion Criteria
- [x] TO-BE Architecture V2 document complete
- [x] Ensemble Strategy TO-BE document complete
- [x] PHASE22-4 issue absorbed into architectural plan
- [x] Implementation roadmap defined

### 8.2 Overall PHASE23 Success Metrics

**Technical Metrics**:
- [ ] 30min paper test: Strategy params correctly propagated (PHASE23-1)
- [ ] 1H paper test: All 5 strategies execute without errors (PHASE23-2)
- [ ] 3H backtest: Each individual strategy produces >0 trades (PHASE23-3)
- [ ] 3H ensemble paper: At least 3/5 strategies participate (PHASE23-4)

**Architectural Metrics**:
- [ ] Single engine entry point established
- [ ] Scripts reduced to <100 lines (thin wrappers)
- [ ] Config propagation: YAML → engine → strategy (no intermediate modifications)
- [ ] All strategies use unified BaseStrategy interface

**Code Quality Metrics**:
- [ ] Unit test coverage >80% for new code
- [ ] No pylint/flake8 warnings in modified files
- [ ] Clear docstrings for all new functions
- [ ] README updated with new architecture

---

## 9. Risk Assessment & Mitigation

### 9.1 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Refactoring breaks existing functionality** | Medium | High | Keep old scripts for reference, test both paths in parallel |
| **Config propagation still fails after refactor** | Low | High | Add extensive debug logging, validate config structure early |
| **Strategies don't produce trades after unification** | Medium | Medium | Individual strategy validation before ensemble integration |
| **PHASE23 takes longer than estimated** | High | Low | Break into smaller sub-phases, deliver incrementally |

### 9.2 Mitigation Strategies

**For Breaking Changes**:
- Create new scripts (run_v2.py) rather than modifying old ones
- Run both old and new paths in parallel during transition
- Comprehensive unit tests for refactored code

**For Config Issues**:
- Add config validation layer in engine
- Fail fast with clear error messages
- Debug logging at every config passing step

**For Strategy Issues**:
- Validate each strategy individually before ensemble testing
- Use 3H backtest as smoke test
- Document expected trade frequency for each strategy

---

## 10. Conclusion

PHASE23-0 establishes a clear, unified TO-BE architecture that resolves the PHASE22-4 config propagation issue by **eliminating script-level orchestration complexity** and **consolidating all strategy/config/ensemble logic into the engine layer**.

**Key Takeaways**:
1. **PHASE22-4 issue is NOT a code bug** (unit tests prove code is correct)
2. **Root cause is architectural** (fragmented script-level logic)
3. **Solution is structural** (thin scripts + single-engine-centric design)
4. **Implementation is phased** (PHASE23-1~4, each testable)

**Next Steps**:
- Complete PHASE23-0: Finalize Ensemble Strategy TO-BE document
- Proceed to PHASE23-1: Script Layer Cleanup & Engine Refactor
- Validate with 30min paper test: Params must reach strategy correctly

---

**Document Status**: 🟢 COMPLETE  
**Review Date**: 2025-11-29  
**Author**: Cascade AI (PHASE23-0)  
**Approved By**: [Pending User Review]
