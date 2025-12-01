# PHASE23-1: Single-Engine Entry Point Refactor & Config Propagation Fix

**Status**: ✅ COMPLETE  
**Date**: 2025-12-01  
**Duration**: ~2.5 hours

---

## 📋 Objective

**Primary Goal**: PHASE22-4의 runtime config propagation 이슈를 아키텍처 레벨에서 해결

**Specific Goals**:
1. 엔진 중심 아키텍처 구현 (Single-Engine-Centric)
2. 얇은 스크립트 wrapper 생성 (`run_v2.py`)
3. Strategy params가 100% 전파되도록 보장
4. Config SSOT 원칙 준수

---

## 🔍 Problem Statement (PHASE22-4 Issue)

### AS-IS (문제 있는 구조)

```
run_paper.py (Script):
  - Line 255: effective_strategy 계산 (script-level orchestration)
  - Line 376: load_strategies(config=cfg) 호출
  - Config를 여러 번 수정 (max_runtime_hours, mode, env 등)
  - engine.run(strategies=strategies, ...)에 전달

engine.run():
  - strategies는 이미 로딩된 dict를 받음
  - config params 병합 로직은 Line 1218-1229에 존재
  - 그러나 script에서 config가 여러 번 변경되어 params가 손실됨
```

**증상**:
- Unit test: ✅ PASS (load_strategies → params 정상)
- Direct Python test: ✅ PASS
- **Runtime (run_paper.py 경유)**: ❌ FAIL
  - params: {} (빈 dict)
  - RSI threshold: 30/70 (기본값) ← **45/55 (config 값) 사용해야 함**

**근본 원인** (PHASE23-0 분석):
- **Script-level orchestration** 문제
- Config 로딩/전달 경로가 script에서 중복/분산
- Script가 전략 선택/로딩을 수행하여 엔진의 제어권 침해

---

## 🎯 TO-BE Architecture

### TO-BE (목표 구조)

```
run_v2.py (Thin Script, <100 lines):
  - Config 로딩만 (YAML load + deep merge)
  - Run ID 생성
  - engine.run_v2(mode, config, clean_state) 호출

engine.run_v2():
  - Config validation
  - load_strategies(config) 직접 호출 ← **핵심 변경**
  - use_ensemble 판단
  - Mode-based adapter 생성 (paper/backtest/live)
  - Duration 설정
  - 기존 run() 호출 (단일 엔진 원칙)

engine.run():
  - Line 1218-1229: strategy params 병합 (기존 로직 재사용)
  - cfg = {**config, **strategy_params}
  - strategy.signal_logic(df, cfg) 호출
```

**핵심 원칙**:
1. **Single-Engine Entry Point**: 모든 모드(paper/backtest/live)는 `engine.run_v2()`로 진입
2. **Config SSOT**: Script는 config를 수정하지 않음 (mode/duration만 설정)
3. **Strategy Loading in Engine**: `load_strategies()`는 엔진이 호출
4. **Mode-based Adapter**: Script가 아닌 엔진이 adapter를 생성

---

## 📂 Implementation

### 1. 새로운 스크립트: `scripts/run_v2.py` (97 lines)

**책임**:
- YAML config 로딩 (base.yml + custom config deep merge)
- Run ID 생성
- Mode/Duration 설정
- `engine.run_v2()` 호출

**핵심 코드**:
```python
# Config 로딩
config = deep_merge(base_cfg, custom_cfg)
config['run_id'] = generate_run_id()
config['mode'] = args.mode
config['env'] = args.mode

# Engine 호출 (단일 진입점)
from execution.engine import run_v2

run_v2(
    mode=args.mode,
    config=config,
    clean_state=args.clean_state
)
```

**사용법**:
```bash
python scripts/run_v2.py --mode paper --config configs/paper/phase22_4_scalping_param_smoke_30m.yml --duration-hours 0.5
```

### 2. 엔진 진입점: `execution/engine.py::run_v2()` (102 lines)

**책임**:
- Config validation (필수 키 확인)
- **load_strategies() 직접 호출** ← 핵심
- Ensemble 모듈 로딩 (use_ensemble 판단)
- Mode-based adapter 생성
- Duration 설정
- 기존 `run()` 호출

**핵심 코드**:
```python
def run_v2(mode: str, config: dict, clean_state: bool = False):
    # 1. Config Validation
    required_keys = ['timeframe', 'lookback', 'equity', 'risk', 'strategy']
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"❌ Config 필수 키 누락: {missing}")
    
    # 2. Strategy 로딩 (Engine이 직접 호출 - PHASE23-1 핵심)
    from strategies import load_strategies
    strategies = load_strategies(config=config)
    
    # PHASE23-1 DEBUG: Params 전파 확인
    for strategy_name, strategy_info in strategies.items():
        params = strategy_info.get('params', {})
        logger.info(f"🔍 [PHASE23-1 DEBUG] {strategy_name} params: {params}")
    
    # 3. Ensemble 모듈 로딩
    ensemble_module = None
    use_ensemble = config.get('strategy', {}).get('use_ensemble', False)
    if use_ensemble:
        from strategies import ensemble
        ensemble_module = ensemble
    
    # 4. Mode-based Adapter 생성
    if mode == 'paper':
        adapters = _create_paper_adapters(config, clean_state)
    elif mode == 'backtest':
        adapters = _create_backtest_adapters(config)
    elif mode == 'live':
        adapters = _create_live_adapters(config, clean_state)
    
    # 5. Duration 설정
    duration_hours = config.get('duration_hours')
    if duration_hours:
        config.setdefault('execution', {})['max_runtime_hours'] = duration_hours
    
    # 6. 기존 run() 호출 (단일 엔진 원칙)
    run(
        feed=adapters['feed'],
        broker=adapters['broker'],
        clock=adapters['clock'],
        strategies=strategies,
        ensemble_module=ensemble_module,
        config=config
    )
```

### 3. Adapter 생성 함수

**Before** (Script-level):
```python
# run_paper.py에서 직접 생성
from execution.adapters import create_adapters
feed, broker, clock = create_adapters(mode='paper', symbols=[symbol], config=cfg)
```

**After** (Engine-level):
```python
# engine.py의 helper function
def _create_paper_adapters(config: dict, clean_state: bool) -> dict:
    from execution.adapters import create_adapters
    
    symbol = config.get('symbol', 'BTCUSDT')
    feed, broker, clock = create_adapters(
        mode='paper',
        symbols=[symbol],
        config=config,
        logger=logger
    )
    
    if clean_state and hasattr(broker, 'open_positions'):
        broker.open_positions.clear()
    
    return {'feed': feed, 'broker': broker, 'clock': clock}
```

---

## ✅ Acceptance Criteria Validation

### 1. ✅ Unit Tests (6/6 PASS)

```bash
pytest -q --tb=short tests/test_phase22_4_config_integration.py
# Result: ==================== 6 passed in 2.03s ====================
```

### 2. ✅ 30분 PAPER Smoke Test

**Command**:
```bash
python scripts/run_v2.py --mode paper --config configs/paper/phase22_4_scalping_param_smoke_30m.yml --duration-hours 0.5
```

**Critical Logs** (성공 증거):
```
2025-12-01 21:08:47 [INFO] 🔍 [PHASE23-1 DEBUG] scalping params: {'rsi_oversold': 45, 'rsi_overbought': 55, ...}
2025-12-01 21:11:24 [INFO] 🔍 [PHASE22-4 DEBUG] scalping params: {'rsi_oversold': 45, 'rsi_overbought': 55, ...}
2025-12-01 21:11:24 [INFO] 🔍 [PHASE22-4 DEBUG] scalping cfg rsi_oversold=45, rsi_overbought=55
```

**결과**:
- ✅ Params correctly loaded: `rsi_oversold=45, rsi_overbought=55` (NOT 30/70 defaults)
- ✅ Params merged into cfg at engine level (Line 1228)
- ✅ Strategy received correct parameters
- ✅ Actual trade executed (SHORT @ 86334.81, TP1 @ 86100.10, PnL +$19.23)

### 3. ✅ Acceptance Criteria Summary

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `run_v2.py` exists and is thin (<100 lines) | ✅ PASS | 97 lines total |
| `engine.run_v2()` calls `load_strategies()` internally | ✅ PASS | Line 77 in engine.py |
| Config params are 100% propagated | ✅ PASS | RSI 45/55 in logs (not 30/70) |
| Unit tests pass | ✅ PASS | 6/6 tests passed |
| 30min paper test shows correct params | ✅ PASS | Logs confirm params |
| Actual trades executed | ✅ PASS | 1 entry + 1 TP1 exit |

---

## 📊 Impact & Benefits

### Before (AS-IS)
- **Script-level orchestration**: 난잡한 config 수정
- **Config propagation broken**: params 손실
- **3개의 진입점**: run_paper.py, run_backtest.py, (future) run_live.py
- **테스트/실행 불일치**: Unit test OK, Runtime FAIL

### After (TO-BE)
- **Engine-centric architecture**: 깨끗한 책임 분리
- **Config propagation fixed**: params 100% 전파
- **1개의 진입점**: `engine.run_v2(mode, config, ...)`
- **테스트/실행 일치**: Unit test = Runtime

### Benefits
1. **Maintainability**: Script는 얇고 단순, 로직은 엔진에 집중
2. **Testability**: 엔진 레벨에서 모든 경로 테스트 가능
3. **Scalability**: 새 모드(live) 추가 시 adapter만 구현하면 됨
4. **Debuggability**: Config 전파 경로가 명확하고 단일

---

## 🔄 Migration Path

### Existing Scripts (Deprecated)

- `scripts/run_paper.py`: ⚠️ DEPRECATED (향후 run_v2 wrapper로 축소 예정)
- `scripts/run_backtest.py`: ⚠️ DEPRECATED (향후 제거)

**Transition Plan**:
1. PHASE23-1: `run_v2.py` 추가 (기존 스크립트 유지)
2. PHASE23-2~4: `run_v2.py`로 모든 테스트 전환
3. PHASE24: 기존 스크립트에서 `run_v2` wrapper만 남기고 나머지 제거

---

## 🚀 Next Steps (PHASE23-2)

**PHASE23-2: Strategy Interface Unification**
- Duration: 3-5 hours
- Goal: `scalping_v3` → `BaseStrategy` 마이그레이션
- Tasks:
  - Rename `signal_logic` → `compute_signal`
  - Add `metadata` property
  - Update all strategy calls in engine
  - 1H paper test (5 strategies)

**Acceptance Criteria**:
- [ ] All 5 strategies use `compute_signal(df, config)`
- [ ] All 5 strategies implement `metadata` property
- [ ] 1H paper test executes without errors

---

## 📝 Files Changed

### New Files
- `scripts/run_v2.py` (97 lines)
- `docs/PHASE23/PHASE23-1_ENGINE_ENTRYPOINT_REFACTOR.md` (this file)

### Modified Files
- `execution/engine.py`:
  - Added `run_v2()` function (L41-L142)
  - Added `_create_paper_adapters()` (L145-L164)
  - Added `_create_backtest_adapters()` (L167-L181)
  - Added `_create_live_adapters()` (L184-L187)
- `tests/test_phase22_4_config_integration.py`:
  - Updated docstring for PHASE23-1

### No Changes (Expected)
- `strategies/__init__.py`: No changes (PHASE22-4 params logic reused)
- `execution/engine.py::run()`: No changes (Line 1218-1229 params merge logic reused)

---

## 🎓 Lessons Learned

1. **Architecture First**: Code-level fixes (PHASE22-4) passed unit tests but failed at runtime. The real issue was architectural (script-level orchestration).

2. **Single Source of Truth**: Config should be modified in exactly ONE place. Multiple script-level modifications = guaranteed bugs.

3. **Test Coverage Gap**: Need integration tests that cover the full path (script → engine → strategy), not just unit tests of individual components.

4. **Separation of Concerns**: Scripts should be dumb wrappers. All business logic (strategy loading, ensemble, etc.) belongs in the engine.

---

## 📌 References

- **PHASE22-4**: `docs/PHASE22/PHASE22-4_CONFIG_INTEGRATION_INCOMPLETE.md`
- **PHASE23-0**: `docs/PHASE23/PHASE23-0_ARCHITECTURE_TOBE_V2.md`
- **Ensemble TO-BE**: `docs/PHASE23/ENSEMBLE_STRATEGY_TOBE_V2.md`
- **Roadmap**: `PHASE_ROADMAP.md` (PHASE23 section)

---

**Status**: ✅ **COMPLETE** (2025-12-01)  
**Next**: PHASE23-2 (Strategy Interface Unification)
