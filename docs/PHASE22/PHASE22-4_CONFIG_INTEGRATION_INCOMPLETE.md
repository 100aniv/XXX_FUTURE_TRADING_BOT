# PHASE22-4: Config Integration Fix - INCOMPLETE
**Status**: PARTIAL SUCCESS (Code Fixed, Runtime Issue Unresolved)  
**Date**: 2025-11-23  
**Duration**: ~2 hours

---

## Executive Summary

PHASE22-4의 목표는 전략별 config params가 제대로 전달되도록 수정하는 것이었습니다.

**Code Level**: ✅ SUCCESS  
- `strategies/__init__.py` 수정 완료
- `execution/engine.py` 수정 완료
- Unit tests 6/6 PASS
- 직접 Python 테스트 성공

**Runtime Level**: ❌ FAIL  
- `run_paper.py` 실행 시 params가 빈 dict로 전달됨
- 30분 paper test 실행했으나 RSI threshold 여전히 기본값(30/70) 사용
- 근본 원인 미파악

---

## Code Changes (COMPLETED)

### 1. strategies/__init__.py

**Before**:
```python
def load_strategies(config: dict) -> Dict[str, Any]:
    strategies = {}
    for name, module in all_strategies.items():
        if enabled:
            strategies[name] = module  # 모듈만 반환
    return strategies
```

**After (PHASE22-4)**:
```python
def load_strategies(config: dict) -> Dict[str, Dict[str, Any]]:
    strategies = {}
    for name, module in all_strategies.items():
        strategy_config = strategies_cfg.get(name, {})
        params = strategy_config.get('params', {})
        if enabled:
            strategies[name] = {
                "module": module,
                "params": params,  # ⭐ params 포함
                "enabled": True
            }
    return strategies
```

### 2. execution/engine.py

**Before**:
```python
for strategy_id, strategy_module in selected_strategies.items():
    cfg = config  # 전체 config만 전달
    signal = strategy_module.signal_logic(df_tf, cfg)
```

**After (PHASE22-4)**:
```python
for strategy_id, strategy_info in selected_strategies.items():
    strategy_module = strategy_info["module"]
    strategy_params = strategy_info.get("params", {})
    
    cfg = {
        **config,
        **strategy_params,  # ⭐ params 병합 (우선순위 높음)
    }
    signal = strategy_module.signal_logic(df_tf, cfg)
```

---

## Unit Tests (ALL PASS)

File: `tests/test_phase22_4_config_integration.py`

```
==================== test session starts =====================
tests/test_phase22_4_config_integration.py::test_load_strategies_returns_dict_with_params PASSED
tests/test_phase22_4_config_integration.py::test_load_strategies_with_empty_params PASSED
tests/test_phase22_4_config_integration.py::test_load_strategies_without_params_key PASSED
tests/test_phase22_4_config_integration.py::test_load_strategies_single_strategy_mode PASSED
tests/test_phase22_4_config_integration.py::test_load_strategies_multiple_enabled PASSED
tests/test_phase22_4_config_integration.py::test_load_strategies_fallback_to_daytrade PASSED
===================== 6 passed in 0.92s ======================
```

---

## Direct Python Test (SUCCESS)

```bash
$ python test_config_load.py
=== Config Structure ===
strategy: {'use_ensemble': False, 'selector': 'scalping'}
strategies.scalping: {'enabled': True, 'params': {'rsi_oversold': 45, ...}}

=== load_strategies Result ===
Loaded strategies: ['scalping']
scalping params: {'rsi_oversold': 45, 'rsi_overbought': 55, ...}
```

✅ **Config 로딩 및 params 추출 정상 작동 확인**

---

## Runtime Issue (UNRESOLVED)

### Symptom

`run_paper.py` 실행 시 engine.py의 디버그 로그:
```
🔍 [PHASE22-4 DEBUG] scalping params: {}
🔍 [PHASE22-4 DEBUG] scalping cfg rsi_oversold=MISSING, rsi_overbought=MISSING
```

### Observed Behavior

- 30분 paper test 실행
- Log에서 RSI threshold가 30/70 (기본값) 사용 확인:
  ```
  [SCALPING V2 INIT]
    - RSI 과매도: < 30  (config는 45)
    - RSI 과매수: > 70  (config는 55)
  ```
- 하지만 trades는 발생함 (RSI 27~75 범위에서 신호 생성)

### Possible Causes

1. **Config 재로딩**: run_paper.py가 config를 다시 로드하거나 수정하는 과정에서 params 손실
2. **Python Caching**: __pycache__의 이전 버전 사용 (시도했으나 해결 안 됨)
3. **다른 코드 경로**: run_paper.py가 load_strategies를 다른 방식으로 호출
4. **Logging 타이밍**: load_strategies의 DEBUG 로그가 application log에 기록되지 않음

### Debugging Attempts

- ✅ Config 파일 확인: 올바름
- ✅ Unit tests: PASS
- ✅ 직접 Python 테스트: 성공
- ✅ `__pycache__` 삭제: 효과 없음
- ❌ run_paper.py의 load_strategies 호출 시점 로그: 확인 실패

---

## Config File

`configs/paper/phase22_4_scalping_param_smoke_30m.yml`:

```yaml
strategy:
  use_ensemble: false
  selector: scalping

strategies:
  scalping:
    enabled: true
    params:
      rsi_oversold: 45  # ← 이 값이 전달되어야 함
      rsi_overbought: 55
      momentum_enabled: false
      volume_required: false
      # ... other params
```

---

## Next Steps (Recommendations)

### Option A: Deep Runtime Debugging (Est. 2-4 hours)

1. Add extensive logging to `run_paper.py`:
   - Log config immediately after loading
   - Log strategies immediately after load_strategies()
   - Trace every step where config is modified

2. Use Python debugger (pdb) to step through run_paper.py

3. Check if there are multiple code paths loading strategies

### Option B: Workaround Approach (Est. 30-60 min)

1. Create a new simplified runner script:
   ```python
   # scripts/run_phase22_4_simple.py
   from execution import engine
   from strategies import load_strategies
   import yaml
   
   with open('configs/paper/phase22_4_scalping_param_smoke_30m.yml') as f:
       config = yaml.safe_load(f)
   
   strategies = load_strategies(config)
   # Verify params here
   print(f"DEBUG: scalping params = {strategies['scalping']['params']}")
   
   # Run engine
   engine.run(feed, broker, clock, strategies, None, config)
   ```

2. Test with this simplified runner

3. If successful, identify differences with run_paper.py

### Option C: Alternative Fix (Est. 1 hour)

Modify `scalping.py` to read params from a nested config structure:

```python
# strategies/scalping.py
def signal_logic(df, config):
    # Try to get params from strategies.scalping.params first
    strategy_cfg = config.get('strategies', {}).get('scalping', {})
    params = strategy_cfg.get('params', {})
    
    rsi_oversold = params.get('rsi_oversold', config.get('rsi_oversold', 30))
    rsi_overbought = params.get('rsi_overbought', config.get('rsi_overbought', 70))
    # ...
```

This is a defensive approach but doesn't fix the root cause.

### Option D: Defer to PHASE23 (Recommended if time-constrained)

1. Mark PHASE22-4 as PARTIAL
2. Document known issues
3. Proceed to PHASE23 (Infrastructure hardening)
4. Revisit config propagation after broader refactor

---

## Acceptance Criteria Status

| Criterion | Target | Status | Note |
|-----------|--------|--------|------|
| Unit tests PASS | 6/6 | ✅ PASS | All tests passing |
| Code modifications | Complete | ✅ PASS | load_strategies + engine.py |
| Direct Python test | params loaded | ✅ PASS | Manual test successful |
| 30min paper test | ≥5 trades | ❓ UNCLEAR | Trades occurred but with wrong params |
| RSI config applied | 45/55 | ❌ FAIL | Still using 30/70 |
| Logs show config params | Yes | ❌ FAIL | Shows params={} |

**Overall**: ❌ **FAIL (Runtime Integration)**

---

## Lessons Learned

### 1. Testing Pyramid Gap

- Unit tests: ✅ PASS
- Direct script test: ✅ PASS  
- Integration test (via run_paper.py): ❌ FAIL

**Lesson**: Need integration tests that mimic the actual runtime environment, not just unit tests.

### 2. Hidden Dependencies

The `run_paper.py` script may have hidden dependencies or initialization steps that affect how config is processed. Direct testing bypassed these.

**Lesson**: Always test through the actual entry point, not just the modified functions in isolation.

### 3. Logging Visibility

load_strategies' DEBUG logs were not visible in the application log during run_paper.py execution.

**Lesson**: Ensure all critical initialization steps log to a consistent, easily accessible location.

### 4. Python Caching Complexity

Deleting `__pycache__` did not resolve the issue, suggesting the problem is not caching-related but deeper in the runtime flow.

---

## Artifacts

- **Code Changes**:
  - `strategies/__init__.py` (modified)
  - `execution/engine.py` (modified)
- **Tests**:
  - `tests/test_phase22_4_config_integration.py` (new, 6 tests)
  - `test_config_load.py` (temp debug script)
- **Config**:
  - `configs/paper/phase22_4_scalping_param_smoke_30m.yml` (new)
- **Logs**:
  - `logs/application/2025-11-23.log` (runtime debug attempts)

---

## Conclusion

PHASE22-4는 **코드 레벨에서는 성공**했지만, **런타임 통합에서 실패**했습니다.

**Code Fix**: ✅ Complete  
**Runtime Fix**: ❌ Incomplete  
**Root Cause**: Unknown (likely in run_paper.py's config handling)

**Recommendation**: Option D - Defer to PHASE23, revisit after broader refactor.

---

**Report Generated**: 2025-11-23 14:30 KST  
**Phase Status**: PARTIAL (Code PASS, Runtime FAIL)  
**Next Action**: User decision on how to proceed
