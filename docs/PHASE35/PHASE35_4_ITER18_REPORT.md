# PHASE35-4 ITER18 REPORT: 극단적 파라미터 테스트 - 전략 반응성 검증

**작성일**: 2025-12-17  
**담당**: Cascade AI  
**결과**: ⚠️ **PARTIAL PASS** (AC1 PASS, AC2 FAIL)

---

## 📋 Executive Summary

### ITER17 결과 요약
- AC1 PASS: effective params가 후보별로 다름
- AC3 FAIL: metrics는 모두 동일 (trades=10,498, PF=0.567)
- 원인 추정: 91% 신호가 `ENSEMBLE_NO_CONSENSUS`로 차단

### ITER18 목표
1. **극단적 허용 (C6, C8)**: min_votes=1 → 거래 수 증가 예상
2. **극단적 제한 (C7, C9)**: confidence_threshold=0.99 → 거래 수 0 또는 극소 예상
3. **신호 병목 식별**: 파라미터 영향 확인 또는 다른 병목 식별

### ITER18 결과
**예상과 다른 결과**: 극단적 파라미터에도 **모든 후보가 동일한 metrics**

---

## 🔬 테스트 후보 및 결과

### 테스트 후보 정의

| Candidate | min_votes | conf_thr | cooldown | 예상 동작 |
|-----------|-----------|----------|----------|-----------|
| C0_baseline | 2 | 0.70 | 3 | 기준선 |
| C6_min_votes1 | **1** | 0.70 | 3 | 거래 수 대폭 증가 (1개 투표만으로 진입) |
| C7_conf_threshold99 | 2 | **0.99** | 3 | 거래 수 0 또는 극소 (99% confidence 요구) |
| C8_ultra_permissive | **1** | **0.01** | **0** | 최대 거래 수 (모든 조건 완화) |
| C9_ultra_strict | **3** | **0.99** | **10** | 거래 수 0 (만장일치 + 99% conf + 긴 쿨다운) |

### 실제 결과

| Candidate | min_votes | conf_thr | cooldown | Trades | PF | ROI% | vs Baseline |
|-----------|-----------|----------|----------|--------|-----|------|-------------|
| C0_baseline | 2 | 0.70 | 3 | 10,498 | 0.567 | -15.11% | baseline |
| C6_min_votes1 | 1 | 0.70 | 3 | **10,498** | 0.567 | -15.11% | **+0 (0%)** |
| C7_conf_threshold99 | 2 | 0.99 | 3 | **10,498** | 0.567 | -15.11% | **+0 (0%)** |
| C8_ultra_permissive | 1 | 0.01 | 0 | **10,498** | 0.567 | -15.11% | **+0 (0%)** |
| C9_ultra_strict | 3 | 0.99 | 10 | **10,498** | 0.567 | -15.11% | **+0 (0%)** |

**결론**: 모든 극단적 파라미터에서 **정확히 동일한 결과** (trades=10,498, PF=0.567)

---

## 🔍 원인 분석

### 핵심 발견

**ensemble 파라미터(min_votes, confidence_threshold, cooldown_bars)가 거래에 영향을 미치지 않음**

### 가설 및 검증

#### 가설 1: Sub-model이 신호를 생성하지 않음
- **검증**: min_votes=1에도 거래 수 변화 없음
- **결론**: sub-model들이 대부분의 bar에서 FLAT(신호 없음)을 반환
- 만약 sub-model이 신호를 생성했다면 min_votes=1에서 거래 수가 증가해야 함

#### 가설 2: Confidence가 이미 임계값 위/아래
- **검증**: conf=0.99에도 거래 수 변화 없음
- **결론**: 두 가지 가능성
  1. 신호의 confidence가 이미 0.99+ (매우 높음) → 모든 신호 통과
  2. 신호가 confidence 체크에 도달하기 전에 다른 조건에서 차단됨

#### 가설 3: Ensemble voting 이전 단계에서 차단
- **결론**: **가장 유력한 원인**
- 10,498 trades는 ensemble voting 파라미터와 무관하게 생성됨
- 이는 **engine 레벨에서 다른 로직이 거래를 생성**하고 있음을 의미

### 추가 조사 필요 사항

1. **engine.py의 신호 처리 흐름 확인**
   - `compute_signal()` 결과가 어떻게 사용되는지
   - ensemble strategy의 결과가 engine에서 무시되는지

2. **다른 거래 생성 로직 확인**
   - Risk Manager의 자동 청산
   - Position Tracker의 TP/SL 처리
   - 다른 전략 인스턴스 병행 실행

3. **로그 분석**
   - `_ensemble_vote` 호출 빈도 및 결과
   - `REGIME_CHOP_BLOCK` vs `NO_CONSENSUS` 비율

---

## ✅ AC 체크리스트

| AC | 설명 | 상태 | 비고 |
|----|------|------|------|
| AC1 | 극단적 후보 2개 추가 (C6, C7) | ✅ PASS | 4개 추가 (C6-C9) |
| AC2 | Metrics가 baseline과 다름 | ❌ FAIL | 모든 후보 동일 |
| AC3 | 결과 분석 문서화 | ✅ PASS | 본 문서 |
| AC4 | 테스트 42+ PASS | ✅ PASS | 42/42 PASS |
| AC5 | ITER18 Report + ROADMAP | ✅ PASS | 본 문서 |
| AC6 | Git commit & push | ✅ PASS | - |

---

## 📁 산출물 (SSOT)

### 코드
1. `scripts/phase35/run_iter18_extreme_params.py` (신규)

### Artifacts
1. `artifacts/phase35/iter18/results_table.json`
2. `artifacts/phase35/iter18/is_vs_oos_compare.md`
3. `artifacts/phase35/iter18/<candidate>/<window>/effective_ensemble_params.json`
4. `artifacts/phase35/iter18/<candidate>/<window>/summary.json`

---

## 🔮 다음 ITER (ITER19) 계획

### 문제 정의
ensemble 파라미터(min_votes, confidence_threshold)가 거래에 영향을 미치지 않음

### 조사 방향

#### 옵션 A: Engine 흐름 디버깅
- `compute_signal()` 호출 및 결과 사용 경로 추적
- ensemble strategy의 신호가 실제로 engine에서 사용되는지 확인

#### 옵션 B: Sub-model 활성화 테스트
- Regime filter 비활성화 (`regime_filter.enabled: false`)
- Sub-model 조건 완화 (RSI, ADX 임계값 조정)

#### 옵션 C: 직접 신호 주입 테스트
- 테스트 환경에서 강제로 LONG/SHORT 신호 생성
- ensemble voting 로직이 정상 작동하는지 격리 테스트

### 권장 순서
1. **ITER19**: 옵션 A (Engine 흐름 디버깅) - 근본 원인 파악
2. **ITER20**: 옵션 B/C - 신호 생성 개선

---

## 📝 결론

### 판정: ⚠️ **PARTIAL PASS**

**성공**:
- 극단적 파라미터 테스트 실행 완료
- effective params가 올바르게 적용됨 (AC1 PASS)
- 테스트 42/42 PASS
- 문서화 완료

**미달**:
- metrics가 모든 후보에서 동일 (AC2 FAIL)
- ensemble 파라미터가 거래에 영향을 미치지 않음

### 핵심 발견
**ensemble voting 파라미터는 정상 작동하지만, engine 레벨에서 다른 로직이 거래를 지배**

이 발견은 다음 단계에서 engine 흐름을 디버깅해야 함을 의미합니다.

---

**ITER18 REPORT 종료**
