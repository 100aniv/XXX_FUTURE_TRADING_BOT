# PHASE36-0 Smoke Run Failure Analysis

## Executive Summary
**Verdict**: ❌ **FAIL** - Critical issues preventing validation completion

### Critical Issues
1. **Duration Mode Not Terminating**: Process exceeded 60m target and continued indefinitely
2. **Zero Trades Generated**: 0 trades in 69+ minutes of runtime
3. **Strategy Signature Mismatch**: ScalpingStrategy `compute_signal()` error
4. **No Artifacts Generated**: No trace.json or report JSON for final run

---

## Run Details

### Timeline
- **Start**: 2025-12-21 19:58:18
- **Target Duration**: 1.00 hour (engine log confirmation)
- **Actual Runtime**: 69+ minutes
- **Termination**: Manual (taskkill PID 35376, 38532)
- **Status**: Process did not self-terminate at duration target

### Configuration
- **Stage**: smoke
- **Profile**: L4
- **Symbol**: BTCUSDT
- **Timeframe**: 15m
- **Expected Duration (DURATION_MAP)**: 0.33h (20 minutes)
- **Actual Duration (Engine Log)**: 1.00 hour
- **Initial Equity**: $50,000

### System State
- **FlowGuardian**: READY ✅
- **Multi-TF Preload**: 6 timeframes, 6000 candles ✅
- **WS Feed**: Active, receiving 15m candles ✅
- **Flash-Guard**: Triggered once (19:58:27, 17.98% volatility)
- **Process Stability**: No crashes or ERROR/CRITICAL logs ✅

---

## Root Cause Analysis

### 1. Duration Mode Failure
**Symptom**: Process ran 69+ minutes without terminating despite 60m target
- Engine logged: "⏱️  [MARKET-TIME] Duration 모드 시작: 1.00시간"
- No automatic termination signal observed at ~20:58:18
- Process continued streaming and logging normally

**Possible Causes**:
- Duration check logic not executing
- Timer thread not triggering termination
- Wall-clock calculation error
- Duration config override from profile or environment

**Evidence**:
```
2025-12-21 19:58:18,349 [INFO] ⏱️  [MARKET-TIME] Duration 모드 시작: 1.00시간
2025-12-21 21:08:00,529 [INFO] 📊 BTCUSDT 15m 실시간 수신 중... (가격: 88684.00, 닫힘: False)
# Process still running 69+ minutes later
```

### 2. Zero Trade Generation
**Symptom**: 0 trades across entire 69-minute run

**Primary Root Cause**: Strategy Signature Mismatch
```
2025-12-21 19:58:01,046 [WARNING] ⚠️  전략 실행 실패 (우회): ScalpingStrategy.compute_signal() got an unexpected keyword argument 'config'
```

**Impact**:
- ScalpingStrategy unable to generate signals
- Ensemble likely bypassed scalping strategy
- Other strategies may not have triggered under current market conditions
- Flash-Guard activated once but no trades followed

**Market Conditions**:
- Price range: 88550-88730 USDT
- Relatively low volatility (except flash event)
- No significant trend or breakout patterns

### 3. Missing Artifacts
**Expected**:
- `artifacts/phase36/phase36_0/runs/phase36_0_L4_smoke_20251221_195754_*_trace.json`
- `reports/paper/paper_20251221_195754_*.json`

**Actual**:
- ❌ No trace.json found for 19:57-19:58 run_id
- ❌ No report JSON found
- Most recent trace: `phase36_0_L4_smoke_20251221_183838_trace.json` (earlier run)

**Implication**:
- Runner script did not complete save_artifacts() phase
- Manual termination may have interrupted file writes
- AC validation impossible without artifacts

---

## AC Status (Best Estimate)

| AC | Criteria | Status | Evidence |
|----|----------|--------|----------|
| AC1 | trades > 0 | ❌ FAIL | 0 trades observed |
| AC2 | DB persist 100% | ❌ FAIL | N/A (0/0) |
| AC3 | persist_trace valid | ❌ FAIL | 0 calls expected |
| AC4 | report JSON | ❌ FAIL | No file generated |
| AC5 | run complete | ❌ FAIL | Manual termination required |

**Overall**: **0/5 PASS** - Complete validation failure

---

## Impact Assessment

### Blocking Issues
1. **Duration mode reliability**: Cannot trust automatic termination
2. **Strategy integration**: Signature mismatch prevents ensemble operation
3. **Artifact generation**: No SSOT report for validation

### Non-Blocking (But Concerning)
1. **Duration config discrepancy**: DURATION_MAP (0.33h) vs actual (1.00h)
2. **Zero trade scenario**: Validation framework not tested under no-trade conditions
3. **Manual intervention required**: Automated testing pipeline broken

---

## Required Fixes (Priority Order)

### P0 - Critical (Blocks All Validation)
1. **Fix Duration Termination Logic**
   - Investigate `execution.engine` duration check mechanism
   - Verify wall-clock vs candle-count modes
   - Add explicit timeout safety mechanism
   - Test: 5m smoke run with forced termination

2. **Fix ScalpingStrategy Signature**
   - File: `strategies/scalping.py`
   - Method: `compute_signal()`
   - Issue: Unexpected `config` keyword argument
   - Fix: Update signature or caller to match interface
   - Test: Unit test + 5m smoke

3. **Verify Artifact Generation**
   - Ensure trace.json writes before exit
   - Ensure report JSON writes before exit
   - Add exit handler for graceful shutdown
   - Test: Check files exist after run

### P1 - High (Improves Reliability)
1. **Resolve Duration Config Confusion**
   - Clarify DURATION_MAP vs profile overrides
   - Document precedence: CLI > profile > DURATION_MAP > default
   - Update runner script documentation

2. **Add Zero-Trade AC Handling**
   - Define PASS criteria for 0-trade scenario
   - Distinguish: "no signals" vs "signals blocked by guards"
   - Update AC logic to handle edge cases

### P2 - Medium (Quality of Life)
1. **Add Process Health Checks**
   - Monitor expected termination time
   - Alert if process exceeds target by 10%
   - Auto-kill after 150% of target duration

2. **Improve Logging**
   - Log duration target at start
   - Log periodic "X% complete" messages
   - Log final "Duration target reached, terminating..."

---

## Recommendations

### Immediate Actions
1. **DO NOT PROCEED** with baseline or longrun stages
2. Fix P0 issues in isolated test environment
3. Re-run 5-minute smoke test to verify fixes
4. Only after 3 consecutive 5m smoke PASS, attempt 20m validation

### Testing Strategy
```
Phase 1: Fix & Unit Test (2-4 hours)
- Fix strategy signature
- Fix duration termination
- Run unit tests

Phase 2: 5m Smoke Validation (30 min)
- 3x consecutive runs
- Verify: termination, trades > 0, artifacts exist
- PASS criteria: All 3 runs complete successfully

Phase 3: 20m Smoke Validation (1 hour)
- 1x full smoke run
- Verify: AC1-AC5 all PASS
- Document evidence

Phase 4: Proceed to PHASE36-0-1 (if Phase 3 PASS)
```

### Documentation Updates Needed
1. `@c:\work\XXX_FUTURE_TRADING_BOT\docs\PHASE36\PHASE36_0_AC2-4_VALIDATION_REPORT.md` - Mark as BLOCKED
2. `@c:\work\XXX_FUTURE_TRADING_BOT\PHASE_ROADMAP.md` - Add PHASE36-0 FAIL entry
3. Create: `PHASE36_0_RECOVERY_PLAN.md` - Detailed fix implementation

---

## Conclusion

**Status**: **BLOCKED** - Cannot proceed with validation until P0 issues resolved

**Next Phase**: **PHASE36-0 Recovery** (not PHASE36-0-1)

**ETA**: 4-6 hours for fixes + validation

**Risk**: High - Core engine behavior (duration mode) may be broken across entire system
