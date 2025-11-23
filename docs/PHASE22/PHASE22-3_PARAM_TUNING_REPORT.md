# PHASE22-3: Parameter Tuning Report
**Status**: FAIL (Trade Generation)  
**Date**: 2025-11-23  
**Objective**: Ensemble v2 + Individual Strategy Parameter Tuning

---

## 1. Executive Summary

PHASE22-3의 목표는 PHASE22-2에서 발생한 "0 trades" 문제를 해결하기 위해 Ensemble threshold 및 개별 전략 파라미터를 완화하고, 짧은 테스트(15-60분)를 통해 거래가 실제로 발생하는지 검증하는 것이었습니다.

**최종 결과**: **FAIL**
- **Trades Generated**: 0
- **Test Duration**: 15분 (0.25H)
- **Root Cause**: Config 파라미터가 전략에 전달되지 않음 (Legacy 전략-Engine 간 인터페이스 문제)

---

## 2. Work Completed

### 2.1 Infrastructure Fixes (SUCCESS)

#### A. Ensemble Aggregator Config Integration
**Issue**: Ensemble tier thresholds가 하드코딩되어 config 반영 안 됨  
**Fix**: `scripts/run_phase22_2_ensemble.py` 수정

```python
# Before (하드코딩)
ensemble_module = EnsembleAggregator(
    registry=registry,
    score_engine=score_engine
)

# After (Config 기반)
tier1_threshold = ensemble_cfg.get('tier1_threshold', 0.8)
tier2_threshold = ensemble_cfg.get('tier2_threshold', 0.5)
tier2_min_votes = ensemble_cfg.get('tier2_min_votes', 2)

ensemble_module = EnsembleAggregator(
    registry=registry,
    score_engine=score_engine,
    min_tier1_score=tier1_threshold,
    min_tier2_score=tier2_threshold,
    min_tier2_votes=tier2_min_votes
)
```

**Validation**: 로그 확인 → Tier1: 0.6, Tier2: 0.3 (올바르게 적용) ✅

---

#### B. Engine-Aggregator Interface Restoration
**Issue**: `engine.py`는 `combine_signals()` 호출, `aggregator.py`는 `decide()` 메서드만 제공  
**Symptom**: Ensemble 모듈이 로드되지만 실제로 호출되지 않음  
**Fix**: `common/ensemble/aggregator.py`에 `combine_signals()` wrapper 추가

```python
def combine_signals(
    self,
    signals: List[Dict[str, Any]],
    conn,
    config: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Engine 호환용 Wrapper (PHASE22-3 호환성 복구)"""
    # signals에서 전략 이름 추출
    strategy_names = [s.get('strategy_id') for s in signals if s.get('direction')]
    
    # df 가져오기 (signals[0]['df'])
    df = signals[0].get('df') if signals else None
    if df is None:
        logger.warning("⚠️  [ENSEMBLE] combine_signals: df 없음, 첫 신호 사용 (fallback)")
        return signals[0]
    
    # decide() 호출
    ensemble_decision = self.decide(strategy_names, df, regime)
    
    # EnsembleDecision → dict 변환
    return decision
```

**Validation**: 코드 레벨 검증 완료, 하지만 실제 호출되지 않음 (신호 0개) ❌

---

#### C. Engine Signal DataFrame Injection
**Issue**: `engine.py`가 signals에 `df`를 포함하지 않아 Aggregator에 df 전달 불가  
**Fix**: `execution/engine.py` L1198 수정

```python
signal = strategy_module.signal_logic(df_tf, cfg)

if signal and signal.get("side"):
    signal["strategy_id"] = strategy_id
    signal["df"] = df_tf  # ⭐ PHASE22-3: Ensemble에 df 전달
    # ... rest of signal setup
```

**Validation**: 코드 레벨 검증 완료 ✅

---

### 2.2 Config Tuning (ATTEMPTED)

#### Phase22_3_Ensemble_Tuning_60m.yml

**Ensemble Thresholds**:
- `tier1_threshold`: 0.8 → 0.6 (25% 완화)
- `tier2_threshold`: 0.5 → 0.3 (40% 완화)
- `tier2_min_votes`: 2 (유지)

**Strategy Entry Conditions (Attempted)**:
- Scalping:
  - `rsi_oversold`: 30 → 40
  - `rsi_overbought`: 70 → 60
  - `momentum_enabled`: true → false
  - `volume_required`: true → false

**Result**: Config 파라미터가 전략에 전달되지 않음 (로그에서 기본값 30/70 확인) ❌

---

## 3. Test Execution

### Test Runs Summary

| Run | Duration | Config | Trades | Status | Note |
|-----|----------|--------|--------|--------|------|
| 1 | 1H (중단) | phase22_3_ensemble_tuning_60m.yml | 0 | ABORTED | 전략 이름 불일치 발견 |
| 2 | 1H (중단) | phase22_3_ensemble_tuning_60m.yml | 0 | ABORTED | Config 파라미터 미반영 발견 |
| 3 | 15min | phase22_3_ensemble_tuning_60m.yml | 0 | COMPLETED | 최종 테스트 |

**Final Test Details**:
- Start: 2025-11-23 11:04:38
- End: 2025-11-23 11:19:38 (자동 종료)
- Duration: 15분 (0.25H)
- Trades: **0**
- Strategies Loaded: 7 (scalping, swing_bb, daytrade, swing, trend, reversion, breakout)
- Ensemble Registered: 3 (scalping, trend, breakout)

---

## 4. Root Cause Analysis

### 4.1 Config-Strategy Interface Issue

**Problem**: Legacy 전략(scalping, trend, breakout 등)이 config params를 받지 못함

**Evidence**:
```
# Config 설정
strategies:
  scalping:
    params:
      rsi_oversold: 40  # 완화
      rsi_overbought: 60  # 완화

# 로그 출력 (실제 사용된 값)
[SCALPING V2 INIT] 파라미터 로드 완료
  - RSI 과매도: < 30  # 기본값!
  - RSI 과매수: > 70  # 기본값!
```

**Cause**: 
- `load_strategies()`는 전략 모듈만 로드하고, config params를 전달하지 않음
- 전략이 `signal_logic(df, config)`를 호출받지만, config는 **global config**이지 **strategy-specific params**가 아님

**Impact**: 
- 파라미터 튜닝이 실제로 적용되지 않음
- 전략 조건이 기본값(매우 엄격)으로 실행됨
- 결과적으로 신호 생성 0개

---

### 4.2 Strategy Loading Mechanism

**Current Flow**:
```
1. load_strategies(config)
   → all_strategies = {'scalping': module, 'trend': module, ...}
   → strategies_cfg = config.get('strategies', {})
   → for name, module in all_strategies.items():
       enabled = strategies_cfg.get(name, {}).get('enabled', True)  # enabled 체크만!
       if enabled:
           strategies[name] = module  # 모듈 그대로 전달

2. engine.py
   → for strategy_id, strategy_module in strategies.items():
       cfg = config  # ❌ 전체 config 전달 (strategy params 없음)
       signal = strategy_module.signal_logic(df, cfg)
```

**Required Flow**:
```
1. load_strategies(config)
   → for name in enabled_strategies:
       strategy_cfg = config['strategies'][name]['params']  # ⭐ params 추출
       strategies[name] = {
           'module': module,
           'config': strategy_cfg  # ⭐ config 포함
       }

2. engine.py
   → for strategy_id, strategy_obj in strategies.items():
       cfg = strategy_obj['config']  # ⭐ strategy-specific config
       signal = strategy_obj['module'].signal_logic(df, cfg)
```

---

### 4.3 Market Conditions

**Secondary Factor**: 저변동성 시장  
- Test Period: 2025-11-23 11:04-11:19 (KST, UTC+9)
- BTC/USDT 5m: 낮은 변동성 관찰
- 하지만 **Primary Cause는 Config 미반영**

---

## 5. Lessons Learned

### 5.1 DO-NOT-TOUCH 원칙의 함정

**Issue**: Legacy 전략들(scalping, trend, etc.)을 "건드리지 말아야 할 코어"로 분류했지만, 실제로는 **config integration이 불완전**한 상태였음

**Learning**: 
- "DO-NOT-TOUCH"는 "버그가 없고 완전히 작동하는 코드"에만 적용
- Config-driven 시스템에서 config가 반영되지 않는 것은 **Critical Bug**
- DO-NOT-TOUCH보다 **Functional Correctness**가 우선

---

### 5.2 Interface Contract Verification

**Issue**: 
- Ensemble Aggregator의 `decide()` 메서드와 Engine의 `combine_signals()` 호출 불일치
- Engine의 `signal['df']` 누락

**Learning**:
- 모듈 간 인터페이스는 **명시적인 contract**와 **통합 테스트**가 필요
- 코드 레벨 수정만으로는 불충분, **실제 실행 검증** 필수

---

### 5.3 Config Propagation Testing

**Issue**: Config 변경 후 실제 반영 여부를 로그로 확인하지 않고 테스트 진행

**Learning**:
- Config 튜닝 시 **첫 5분 내에 로그 확인** 필수
- 파라미터 초기화 로그가 없으면 즉시 중단하고 디버깅
- "실행 완료 후 분석"보다 "실행 초기 빠른 검증"

---

## 6. Recommendations

### 6.1 Immediate (PHASE22-4 또는 PHASE23)

#### A. Config Integration Refactoring
**Priority**: P0 (Blocking)  
**Scope**: `strategies/__init__.py`, `execution/engine.py`

1. **load_strategies() 수정**:
   ```python
   def load_strategies(config: dict) -> Dict[str, Dict]:
       strategies = {}
       for name, module in all_strategies.items():
           strategy_cfg = config.get('strategies', {}).get(name, {})
           if strategy_cfg.get('enabled', True):
               strategies[name] = {
                   'module': module,
                   'params': strategy_cfg.get('params', {}),  # ⭐ params 추가
                   'enabled': True
               }
       return strategies
   ```

2. **Engine signal_logic 호출 수정**:
   ```python
   cfg = {
       **config,  # global config
       **strategies[strategy_id]['params']  # strategy-specific params (우선순위 높음)
   }
   signal = strategy_module.signal_logic(df, cfg)
   ```

---

#### B. Ensemble Integration Testing
**Priority**: P1  
**Scope**: `tests/integration/test_ensemble_integration.py` (신규 생성)

- Config → Aggregator threshold 전달 검증
- Engine → Aggregator `combine_signals()` 호출 검증
- Signal['df'] 존재 여부 검증

---

### 6.2 Short-term (PHASE23)

#### C. BaseStrategy Config Injection Pattern
**Priority**: P1  
**Rationale**: PHASE22-1에서 생성한 v2 전략(volatility_breakout_v2, mean_reversion_v2 등)은 `BaseStrategy` 패턴을 사용하지만, Legacy 전략은 사용하지 않음

**Proposal**:
- Legacy 전략(scalping, trend, breakout 등)을 `BaseStrategy` 패턴으로 마이그레이션
- Config params를 `__init__(config)` 시점에 주입
- 또는 별도 wrapper 레이어 추가

---

### 6.3 Long-term (PHASE24+)

#### D. Strategy Registry v2
**Priority**: P2  
**Scope**: `common/registry/strategy_registry.py`

- Strategy metadata + config schema 통합
- Config validation at load time
- Runtime config override 지원

---

## 7. Acceptance Criteria Status

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Ensemble 1H test trades | ≥30 | 0 | ❌ FAIL |
| Participating strategies | ≥2 | 0 | ❌ FAIL |
| Strategy dominance | <80% | N/A | N/A |
| Infrastructure stability | No errors | ✅ OK | ✅ PASS |
| Duration enforcement | 15min exact | ✅ OK | ✅ PASS |

**Overall**: **FAIL (Trading Criteria)**

---

## 8. Next Steps

### Option A: Quick Fix (Recommended)
1. Implement config integration fix (Section 6.1.A)
2. Re-run 30min test with same thresholds
3. Validate trades ≥5

**Estimated Time**: 30-45 minutes

---

### Option B: Full Refactor
1. Migrate all legacy strategies to BaseStrategy
2. Implement Registry v2
3. Run comprehensive 1H ensemble test

**Estimated Time**: 4-6 hours

---

### Option C: Defer Tuning
1. Mark PHASE22-3 as SKIP
2. Proceed to PHASE23 (Infra hardening)
3. Return to tuning after strategy refactor

**Recommended**: Option A (최소 수정으로 빠른 검증)

---

## 9. Artifacts

- **Config**: `configs/paper/phase22_3_ensemble_tuning_60m.yml`
- **Scorecard**: `scorecards/paper_phase22_2/20251123_110433_5lxj/`
- **Log Sample**: `phase22_3_last_log.txt` (마지막 200줄)
- **Code Changes**: 
  - `scripts/run_phase22_2_ensemble.py`: Config threshold 전달
  - `common/ensemble/aggregator.py`: `combine_signals()` wrapper
  - `execution/engine.py`: `signal['df']` injection

---

## 10. Conclusion

PHASE22-3는 **Infrastructure 측면에서는 성공**했지만, **Trading 측면에서는 실패**했습니다.

**Successes**:
- Ensemble threshold config integration 복구 ✅
- Engine-Aggregator interface 호환성 복구 ✅
- Signal df injection 구현 ✅

**Failures**:
- Strategy-specific config params 미전달 ❌
- 0 trades generated ❌

**Root Cause**: Legacy 전략과 Engine 간 config propagation 누락

**Recommendation**: Config integration 수정 후 PHASE22-4로 재시도, 또는 PHASE23으로 진행 후 돌아오기

---

**Report Generated**: 2025-11-23 11:30 KST  
**Phase Status**: FAIL  
**Next Phase**: PHASE22-4 (Config Fix + Retest) or PHASE23 (Infra Hardening)
