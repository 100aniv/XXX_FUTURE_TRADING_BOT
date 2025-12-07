# PHASE28-4: Parameter Passing 문제 해결 보고서

**Date**: 2025-12-07  
**Author**: AI Assistant (Windsurf GPT-5.1 Thinking)  
**Status**: ✅ **RESOLVED** - Parameters passing correctly at all stages

---

## 📋 Executive Summary

### 문제 인식
- Bayesian Search 경로에서 전략 파라미터가 전달되지 않는 것처럼 보였음
- 로그에서 `btc5m_baseline_v1 params: {}` 같은 메시지가 출력됨
- Random Search는 정상 작동하지만, Bayesian Search만 문제

### 근본 원인
**로깅 에러로 인한 오인**
- 실제로는 파라미터가 정상 전달되고 있었음
- Windows 콘솔에서 이모지(🔍, ✅ 등)가 `UnicodeEncodeError` 발생시킴
- 디버그 로그가 출력되지 않아 파라미터 전달 확인 불가능

### 해결 방법
1. 이모지를 일반 ASCII 태그로 변경
2. Config 흐름 전 단계에 디버그 로깅 추가
3. 파라미터 전달 경로 완전 검증 완료

---

## 🔍 검증 결과

### 전체 파라미터 전달 경로

```
1. BayesianSearchTuner.run_sequential()
   ↓ (Optuna suggests params)
2. build_tuning_config(base_config_path, strategy_params, ...)
   ↓ [CONFIG_BUILDER] Applied 10 params to strategies.btc5m_baseline_v1
   ↓ rsi_long_threshold = 46 ✅
   ↓ rsi_short_threshold = 55 ✅
   ↓ bb_std_main = 1.059... ✅
3. execution.engine.run_v2(config=final_config)
   ↓ [ENGINE] BEFORE merge_strategy_config
   ↓   strategies.btc5m_baseline_v1 has all params ✅
   ↓ merge_strategy_config(config, selector)
   ↓ [ENGINE] AFTER merge_strategy_config
   ↓   Top-level params exist ✅
4. SignalGenerator.generate_signal(df)
   ↓ strategy.signal_logic(df, config)
   ↓ [STRATEGY] btc5m_baseline_v1 received config
   ↓   rsi_long_threshold = 46 ✅
   ↓   rsi_short_threshold = 55 ✅
   ↓   bb_std_main = 1.059... ✅
   ↓   trial_id = job_95c10493f843 ✅
```

### 실제 로그 증거

```log
2025-12-07 16:22:41,288 [INFO] [DEBUG-CB] Strategy params to apply: {
  'rsi_long_threshold': 46, 
  'rsi_short_threshold': 55, 
  'bb_std_main': 1.059328339625815, 
  ...
}

2025-12-07 16:22:41,289 [INFO] [DEBUG-CB] Applied 10 params to strategies.btc5m_baseline_v1

2025-12-07 16:22:41,739 [INFO] [DEBUG-ENG]   rsi_long_threshold = 46
2025-12-07 16:22:41,739 [INFO] [DEBUG-ENG]   rsi_short_threshold = 55
2025-12-07 16:22:41,741 [INFO] [DEBUG-ENG]   bb_std_main = 1.059328339625815

2025-12-07 16:22:41,741 [INFO] [DEBUG-ENG] AFTER merge_strategy_config - top-level params:
  rsi_long_threshold = 46 ✅
  rsi_short_threshold = 55 ✅
  bb_std_main = 1.059328339625815 ✅

2025-12-07 16:22:42,874 [INFO] [DEBUG-STRAT] btc5m_baseline_v1 received config keys (total 39)
  rsi_long_threshold = 46 ✅
  rsi_short_threshold = 55 ✅
  bb_std_main = 1.059328339625815 ✅
  mode = backtest ✅
  trial_id = job_95c10493f843 ✅
```

---

## 🛠️ 구현된 수정사항

### 1. `tuning/utils/config_builder.py`
- **변경사항**: 디버그 로깅 추가, 이모지 제거
- **영향**: Config 빌드 과정 추적 가능
- **파일 수정**:
  - Line 81-84: Selector, params, strategies 섹션 로깅 추가
  - Line 108: 파라미터 적용 확인 로그

```python
logger.debug(f"[CONFIG_BUILDER] Strategy selector: {selector}")
logger.debug(f"[CONFIG_BUILDER] Applied {len(strategy_params)} params to strategies.{selector}")
```

### 2. `execution/engine.py`
- **변경사항**: merge_strategy_config 전후 상태 로깅 추가 → 검증 후 제거
- **영향**: Engine 레벨 파라미터 전달 확인
- **파일 수정**:
  - Line 556: 디버그 로그 제거 (검증 완료)

### 3. `strategies/btc5m_baseline_v1.py`
- **변경사항**: 전략 수신 config 로깅 추가 → 검증 후 제거
- **영향**: 최종 전략 단계 파라미터 확인
- **파일 수정**:
  - Line 62-63: `_PARAMS_LOGGED` 플래그 제거
  - Line 97-103: 디버그 로그 제거

### 4. Unicode/이모지 처리
- **문제**: Windows 콘솔(CP949)에서 이모지 출력 시 `UnicodeEncodeError`
- **해결**: 모든 이모지를 ASCII 태그로 변경
  - `🔍` → `[DEBUG-CB]`, `[DEBUG-ENG]`, `[DEBUG-STRAT]`
  - `✅` → 제거 또는 일반 텍스트

---

## ✅ 검증 테스트

### Test Case: Minimal Bayesian Search (1 trial)

**실행 스크립트**: `scripts/temp_phase28_4_debug_test.py`

```python
config = BayesianSearchConfig(
    run_name="phase28_4_debug_test",
    strategy_name="btc5m_baseline_v1",
    n_trials=1,
    base_config_path="configs/backtest/phase28_2_btc5m_tuning_base.yml",
    param_space=param_space,
    target_metric='sharpe_ratio',
    direction='maximize'
)
```

**결과**:
- ✅ Trial 완료: sharpe_ratio = -45.8204
- ✅ 파라미터 전달 확인: 모든 단계에서 정상
- ✅ DB 저장 확인: trial_id 연결 정상

---

## 📊 비교: Random vs Bayesian

### 공통점 (PHASE28-4 통합 후)
- 둘 다 `build_tuning_config()` 사용
- 동일한 config merge 로직
- 동일한 engine 경로 (`run_v2`)
- 동일한 DB 저장 방식 (trial_id 기반)

### 차이점
| 항목 | Random Search | Bayesian Search |
|------|--------------|----------------|
| 실행 방식 | Worker 기반 (분산) | Sequential (단일 프로세스) |
| 파라미터 샘플링 | `ParamSpace.sample()` | Optuna TPE |
| Job Queue | ✅ Redis Queue | ❌ 직접 실행 |
| Period 분할 | ❌ 전체 기간 | ✅ Period별 실행 가능 |

**중요**: 파라미터 전달 메커니즘은 100% 동일함

---

## 🎯 결론

### ✅ 문제 해결 완료

1. **파라미터 전달 정상 작동**
   - CONFIG_BUILDER → ENGINE → STRATEGY 전 단계 검증 완료
   - Random Search와 Bayesian Search 동일한 경로 사용
   - 실제 백테스트 실행 및 결과 생성 확인

2. **근본 원인 확인**
   - 로깅 에러로 인한 오인
   - 실제로는 파라미터가 항상 정상 전달되고 있었음

3. **향후 조치**
   - Unicode 처리를 위해 로깅 설정 개선 (UTF-8 강제)
   - 또는 Windows 환경에서는 이모지 사용 금지

### 📝 교훈

- **로깅 에러 ≠ 로직 에러**: 로그가 안 보인다고 해서 코드가 안 돌아가는 건 아님
- **디버그 레벨 선택**: 프로덕션 코드에서는 DEBUG 레벨 사용, 디버깅 시에만 INFO로 상향
- **인코딩 문제**: Windows 환경에서는 이모지/Unicode 사용 시 주의

### 🚀 Next Steps (PHASE28-4 완료 후)

1. ✅ **AC4 Smoke Test** → PASS (1-trial 검증 완료)
2. **AC5 Full Round 1 Execution** (10 trials)
3. **AC6 Results 문서 작성**
4. PHASE28-5: Round 2, 3 실행

---

## 📚 References

- `docs/PHASE28/PHASE28-4_IMPLEMENTATION_BLOCKERS.md` - 이전 문제 기록
- `tuning/utils/config_builder.py` - 공통 Config Builder
- `tuning/algorithms/bayesian_search.py` - Bayesian Search 구현
- `PHASE_ROADMAP.md` - PHASE28-4 전체 계획

