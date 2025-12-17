# PHASE35-4 ITER21 REPORT: Sub-models Config SSOT + Signal Activation

**작성일**: 2025-12-18  
**담당**: Cascade AI  
**결과**: ⚠️ **PARTIAL PASS** (DoD1,DoD4 PASS / DoD2,DoD3 FAIL)

---

## 📋 Executive Summary

### ITER21 DoD (Definition of Done)

| DoD | 설명 | 상태 | 비고 |
|-----|------|------|------|
| DoD1 | Config override가 sub_models까지 실제 적용됨 | ✅ PASS | effective_params.json에서 확인 |
| DoD2 | 서브모델 신호가 0이 아닌 상태로 발생 | ❌ FAIL | lookback 설정 문제 |
| DoD3 | Baseline vs Relaxed 최소 1개 지표 차이 | ❌ FAIL | 두 후보 모두 trades=0 |
| DoD4 | Postgres trial_id 격리 증거 | ✅ PASS | DB isolation 정상 |

---

## 🔬 핵심 구현 사항

### 1. sub_models Config 멀티패스 리졸브 (SSOT)

**phase35_ensemble_v1.py 수정**:

```python
def _resolve_sub_models_cfg(self) -> Dict[str, Any]:
    """
    ITER21 SSOT: sub_models config 멀티패스 리졸브
    
    우선순위:
    1. config["sub_models"]
    2. config["strategy"]["sub_models"]
    3. config["strategies"][<selector>]["params"]["sub_models"]
    4. config["strategy_params"]["sub_models"]
    5. {} (기본값)
    """
    path_variants = [
        "sub_models",
        "strategy.sub_models",
        "strategies.phase35_ensemble_v1.params.sub_models",
        "strategy_params.sub_models",
    ]
    return self._get_cfg(path_variants, {})
```

**핵심 변경**:
- `_resolve_sub_models_cfg()` 함수 추가
- `_resolve_sub_models_source()` 함수 추가 (소스 추적)
- `__init__`에서 `self._sub_models_cfg` 캐싱
- `_get_sub_model_votes()`가 `self._sub_models_cfg` 사용
- `get_effective_params()`에 sub_models 정보 포함

### 2. Runner 다중 경로 주입

**run_iter21_submodel_ssot.py**:

```python
def inject_sub_models_multi_path(config, sub_models_override):
    """
    전략이 어느 경로로 config를 읽든 sub_models가 반드시 들어가게 함
    """
    # 1. Top-level sub_models
    config["sub_models"][key].update(val)
    
    # 2. strategy.sub_models
    config["strategy"]["sub_models"][key].update(val)
    
    # 3. strategy_params.sub_models
    config["strategy_params"]["sub_models"][key].update(val)
```

### 3. 계단식 완화 레벨

| Level | adx_threshold | rsi_oversold | rsi_overbought | volume_threshold | regime_filter |
|-------|---------------|--------------|----------------|------------------|---------------|
| L0_baseline | 25 | 30 | 70 | 1.5 | enabled |
| L1_mild | 15 | 35 | 65 | 1.2 | enabled |
| L2_moderate | 12 | 40 | 60 | 1.0 | enabled |
| L3_aggressive | 8 | 45 | 55 | 0.8 | **disabled** |

---

## 📊 실행 결과

### Effective Params 검증 (DoD1 PASS)

**L0_baseline**:
```json
{
  "sub_models": {
    "trend": {"adx_threshold": 25},
    "reversion": {"rsi_oversold": 30, "rsi_overbought": 70}
  }
}
```

**L3_aggressive**:
```json
{
  "sub_models": {
    "trend": {"adx_threshold": 8},
    "reversion": {"rsi_oversold": 45, "rsi_overbought": 55}
  },
  "regime_filter": {"enabled": false}
}
```

✅ **Config override가 sub_models까지 정확히 적용됨**

### DB/Redis Evidence (DoD4 PASS)

```
Postgres (trial_id별 trades count):
- iter21_L0_baseline_xxx: 0 trades
- iter21_L3_aggressive_xxx: 0 trades

Isolation Verification:
- AC1 (DB Isolation): ✅ PASS
- AC2 (No Cross Contamination): ✅ PASS
```

---

## ❌ DoD2,DoD3 실패 원인

### 문제
`lookback=30`이 30일이 아닌 30개 캔들(=7.5시간)로 해석됨

### 원인
- base config에서 `lookback: 100`은 캔들 개수를 의미
- 30일 = 30 * 24 * 4 = 2880 캔들 (15분 타임프레임)
- runner에서 `config["lookback"] = 30`으로 설정 → 30개 캔들만 처리

### 증거
- 백테스트 실행 시간: 6초 (정상이면 수분 소요)
- 로그: "백테스트 리포트 생성 실패: 데이터 없음"

---

## ✅ 테스트 결과

### ITER21 Contract Tests: 10/10 PASS

```
TestSubModelsConfigSSOT: 4/4 PASS
TestMultiPathInjection: 2/2 PASS
TestEffectiveParamsContract: 2/2 PASS
TestTrialIdIsolation: 2/2 PASS
```

---

## 🔧 코드 변경 사항

### 신규 파일

| 파일 | 설명 |
|------|------|
| `scripts/phase35/run_iter21_submodel_ssot.py` | ITER21 Runner |
| `tests/test_phase35_iter21_submodel_ssot_contract.py` | Contract Tests |
| `docs/PHASE35/PHASE35_4_ITER21_REPORT.md` | 본 문서 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `strategies/phase35_ensemble_v1.py` | sub_models 멀티패스 리졸브 추가 |

---

## 📁 Artifacts

### 코드
1. `strategies/phase35_ensemble_v1.py` (수정)
2. `scripts/phase35/run_iter21_submodel_ssot.py` (신규)
3. `tests/test_phase35_iter21_submodel_ssot_contract.py` (신규)

### 결과
1. `artifacts/phase35/iter21/iter21_results.json`
2. `artifacts/phase35/iter21/L*/effective_params.json`
3. `artifacts/phase35/iter21/L*/db_counts.json`

---

## 📝 결론

### 판정: ⚠️ **PARTIAL PASS**

**성공 (DoD1, DoD4)**:
- **sub_models config 멀티패스 리졸브 SSOT 구현 완료**
- effective_params.json에서 override 적용 확인
- DB trial_id 격리 정상 작동
- 테스트 10/10 PASS

**실패 (DoD2, DoD3)**:
- 백테스트 lookback 설정 오류로 trades 미생성
- lookback이 캔들 개수로 해석되어 데이터 부족

---

## 🔮 다음 ITER22 액션 (단 1개)

**lookback 설정 수정**:
```python
# 30일 = 2880 캔들 (15분 타임프레임)
config["lookback"] = 2880  # 또는 날짜 기반으로 계산
```

또는 runner에서 날짜→캔들 변환 로직 추가:
```python
lookback_candles = lookback_days * 24 * 4  # 15분 기준
config["lookback"] = lookback_candles
```

---

**ITER21 REPORT 종료**
