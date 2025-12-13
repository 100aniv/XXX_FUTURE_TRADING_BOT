# PHASE35-1: Moderate Hybrid 앙상블 구현 리포트

**작성일**: 2025-12-13
**상태**: ✅ COMPLETE

---

## Executive Summary

PHASE35-1에서 **Moderate Hybrid 앙상블 전략**을 성공적으로 구현 완료.

**핵심 달성 사항**:
- ✅ 3개 Sub-Model (Trend/Reversion/Breakout) + 2-out-of-3 Vote 구현
- ✅ ATR 기반 레짐 필터 (TREND/RANGE/CHOP) 구현
- ✅ DecisionTrace 품질 원인 추적 시스템 구현
- ✅ 기존 인프라 100% 재사용 (DO-NOT-TOUCH 원칙 준수)
- ✅ Fast Gate 18/18 PASS (단위 테스트 100% 통과)

**다음 단계**: PHASE35-2 (7-Day Smoke Test) 준비 완료

---

## 1. 목표 및 배경

### 1.1 PHASE35-1 목표

PHASE34 결과에서 확인된 근본 원인:
- **파라미터 튜닝은 진입 빈도만 변경, 품질(WR/PF)은 무효**
- Gate Statistics 분석: WR variance 0.028%, PF variance 0.0008
- 결론: **전략 로직 자체를 재설계해야 품질 개선 가능**

PHASE35-1의 목표:
- "PHASE34 고정 패턴을 깨서 **개선 가능한 상태**로 만들기"
- WR 28.4% → 31%+, PF 0.57 → 0.70+ (초기 목표)
- 레짐별/전략별/차단 사유별 분해 통계로 **품질 원인을 수치로 증명**

### 1.2 설계 원칙 (PHASE35_STRATEGY_ARCHITECTURE.md 기반)

1. **Multi-Module Ensemble**: 3개 독립 모듈 (Trend/Reversion/Breakout) + 2/3 Vote
2. **Regime Filter**: ATR 기반 간이 필터 (TREND/RANGE/CHOP)
3. **Infrastructure Reuse**: 기존 engine/portfolio/risk 100% 재사용 (DO-NOT-TOUCH)
4. **Config-Driven**: 모든 파라미터는 config로 관리 (하드코딩 금지)
5. **DecisionTrace**: 진입/차단 사유를 구조화하여 기록

---

## 2. 구현 내용

### 2.1 재사용 지도 작성 (STEP 1)

**문서**: `docs/PHASE35/PHASE35_1_REUSE_MAP.md`

**100% 재사용 모듈**:
- `execution/engine.py` (143KB, 멀티모드 통합 엔진)
- `execution/portfolio_manager.py` (PHASE17 V6.1 검증)
- `execution/risk_manager.py` (Guard Telemetry 내장)
- `execution/position_sizer.py`
- `execution/position_tracker.py`
- `monitoring/telemetry_profiler.py`
- `indicators/*.py`

**참고 모듈 (수정 금지)**:
- `strategies/btc15m_core_v2.py` (MTF Regime Detection 로직 참고)
- `strategies/ensemble.py` (READ-ONLY, PHASE19에서 망가짐)

**신규 구현**:
- `strategies/phase35_ensemble_v1.py` (앙상블 전략)
- `common/decision_trace.py` (DecisionTrace 시스템)
- `configs/phase35/ensemble_v1.yaml` (Config)
- `tests/test_phase35_ensemble.py` (Unit Tests)
- `scripts/phase35/run_7d_smoke_test.py` (7D 테스트 러너)

---

### 2.2 앙상블 전략 구현 (STEP 2)

**파일**: `strategies/phase35_ensemble_v1.py` (725 lines)

#### 2.2.1 전략 구조

```
Phase35EnsembleV1 (BaseStrategy)
├── Regime Detection (ATR-based)
│   ├── TREND: ATR% >= 1.5%
│   ├── RANGE: ATR% <= 0.8%
│   └── CHOP: 그 외 (진입 금지)
│
├── Sub-Model 1: Trend-Following
│   ├── Logic: EMA Cross (20/50) + ADX > 25
│   ├── Active: TREND regime only
│   └── Output: direction, confidence, reasons
│
├── Sub-Model 2: Mean-Reversion
│   ├── Logic: RSI oversold/overbought + BB breach
│   ├── Active: TREND or RANGE
│   └── Regime Boost: RANGE에서 +20% confidence
│
├── Sub-Model 3: Breakout
│   ├── Logic: High/Low breakout + Volume spike
│   ├── Active: TREND or RANGE
│   └── Regime Boost: TREND에서 +30% confidence
│
└── Ensemble Decision (2-out-of-3 Majority Vote)
    ├── Vote Counting
    ├── Confidence Threshold: 0.5
    └── Entry/SL/TP Calculation (ATR 기반)
```

#### 2.2.2 핵심 기능

**Regime Detection**:
```python
def _detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
    """
    ATR-based Regime Detection
    - TREND: ATR% >= 1.5%
    - RANGE: ATR% <= 0.8%
    - CHOP: 중간 영역 (진입 금지)
    """
```

**Sub-Model Interface**:
```python
def _sub_model_trend(...) -> Dict[str, Any]:
    return {
        'direction': 'LONG' | 'SHORT' | None,
        'confidence': 0.0 ~ 1.0,
        'reasons': ['ema_bullish_cross', 'adx_30']
    }
```

**Ensemble Voting**:
```python
def _ensemble_vote(sub_votes) -> Dict[str, Any]:
    """
    2-out-of-3 Majority Vote
    - LONG 2표 이상 → LONG
    - SHORT 2표 이상 → SHORT
    - 그 외 → None (no_consensus)
    - Confidence < 0.5 → Block
    """
```

**Entry/Exit Calculation**:
```python
def _calculate_entry_exit(...):
    """
    ATR 기반 SL/TP
    - SL: Entry ± 1.5 × ATR
    - TP: Entry ± 3.0 × ATR (RR 2.0)
    """
```

---

### 2.3 DecisionTrace 시스템 (STEP 3)

**파일**: `common/decision_trace.py` (500+ lines)

#### 2.3.1 DecisionTrace Logger

**기능**:
- 진입/차단 결정을 구조화하여 기록
- 레짐별/전략별/차단 사유별 분해 통계 제공
- 백테스트 후 분석 가능한 JSON 출력

**출력 포맷**:
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "symbol": "BTCUSDT",
  "regime": "TREND",
  "sub_model_votes": {
    "trend": {"direction": "LONG", "confidence": 0.75},
    "reversion": {"direction": "FLAT", "confidence": 0.40},
    "breakout": {"direction": "LONG", "confidence": 0.65}
  },
  "ensemble_decision": "LONG",
  "final_action": "ENTRY",
  "block_reason": null
}
```

#### 2.3.2 DecisionTraceAnalyzer

**분석 기능**:
- Summary: 전체 Entry/Block 비율
- Regime Analysis: 레짐별 Entry Rate, Block Reasons
- Block Reason Analysis: 차단 사유 TOP 10
- Sub-Model Analysis: 각 모델의 투표 분포, 평균 Confidence

**사용 예시**:
```python
trace = DecisionTrace(output_dir="reports/backtest/phase35/traces")
trace.record_decision(...)
trace.save("decision_trace.json")

analyzer = DecisionTraceAnalyzer("decision_trace.json")
analysis = analyzer.analyze()
```

---

### 2.4 Config 구조 (Config-Driven)

**파일**: `configs/phase35/ensemble_v1.yaml`

```yaml
strategy:
  name: "phase35_ensemble_v1"
  type: "ensemble"
  
  sub_models:
    trend:
      ema_fast: 20
      ema_slow: 50
      adx_threshold: 25
    
    reversion:
      rsi_period: 14
      rsi_oversold: 30
      rsi_overbought: 70
      bb_period: 20
      bb_std: 2.0
    
    breakout:
      lookback: 20
      volume_threshold: 1.5
      volume_ma_period: 20
  
  ensemble:
    method: "majority_vote"
    confidence_threshold: 0.5
  
  regime_filter:
    enabled: true
    type: "atr_simple"
    atr_period: 14
    thresholds:
      trend_min: 0.015
      range_max: 0.008
  
  exit:
    sl_atr_multiplier: 1.5
    tp_atr_multiplier: 3.0
```

**파라미터 제어**:
- ✅ Sub-Model 파라미터: EMA period, RSI threshold, Lookback 등
- ✅ Regime 임계값: ATR% 기준
- ✅ Ensemble 설정: Confidence threshold
- ✅ Exit 설정: SL/TP ATR multiplier

---

## 3. 테스트 결과

### 3.1 Fast Gate (STEP 4-1)

**파일**: `tests/test_phase35_ensemble.py`

**결과**: ✅ **18/18 PASS** (1.16초)

**테스트 커버리지**:

| Category | Tests | Status |
|----------|-------|--------|
| **Strategy Initialization** | 1 | ✅ PASS |
| **Regime Detection** | 4 | ✅ PASS |
| **Sub-Model Logic** | 3 | ✅ PASS |
| **Ensemble Voting** | 3 | ✅ PASS |
| **Signal Computation** | 2 | ✅ PASS |
| **DecisionTrace** | 4 | ✅ PASS |
| **Diagnostics** | 1 | ✅ PASS |

**테스트 항목**:
1. ✅ `test_strategy_initialization`: 전략 메타데이터 검증
2. ✅ `test_regime_detection_trend`: TREND 레짐 감지
3. ✅ `test_regime_detection_range`: RANGE 레짐 감지
4. ✅ `test_regime_detection_chop`: CHOP 레짐 감지
5. ✅ `test_regime_disabled`: 레짐 필터 비활성화
6. ✅ `test_sub_model_trend_bullish`: Trend 모델 LONG 신호
7. ✅ `test_sub_model_reversion_oversold`: Reversion 모델 LONG 신호
8. ✅ `test_sub_model_breakout_high`: Breakout 모델 LONG 신호
9. ✅ `test_ensemble_vote_2_long_1_short`: 2/3 LONG 투표
10. ✅ `test_ensemble_vote_1_long_1_short_1_flat`: No Consensus
11. ✅ `test_ensemble_vote_low_confidence`: Confidence 차단
12. ✅ `test_compute_signal_chop_regime`: CHOP 레짐 차단
13. ✅ `test_compute_signal_entry`: Entry 신호 생성
14. ✅ `test_diagnostics`: DecisionTrace 진단
15-18. ✅ DecisionTrace 기록/요약/저장/DataFrame 변환

---

### 3.2 Core Regression (STEP 4-2)

**결과**: ⚠️ **10/11 PASS** (1개 실패는 PHASE35 무관)

**실패 테스트**:
- `test_03_execution_engine_imports`: `Engine` 클래스 import 실패
- **원인**: `execution/engine.py`는 함수 기반 구조 (클래스 없음)
- **영향**: PHASE35 코드와 무관한 기존 테스트 이슈
- **조치**: DO-NOT-TOUCH 영역이므로 수정하지 않음

**PHASE35 호환성**: ✅ 정상
- 기존 엔진/포트폴리오/리스크 모듈과 충돌 없음
- 모든 import 정상 작동
- BaseStrategy 인터페이스 호환

---

### 3.3 Backtest Gate (STEP 4-3)

**스크립트**: `scripts/phase35/run_7d_smoke_test.py`

**실행 방법**:
```bash
python scripts/phase35/run_7d_smoke_test.py
```

**AC-BT0~BT3 검증 준비**:
- ✅ Config 파일: `configs/phase35/ensemble_v1.yaml`
- ✅ 전략 모듈: `strategies/phase35_ensemble_v1.py`
- ✅ DecisionTrace: `common/decision_trace.py`
- ✅ 테스트 러너: `scripts/phase35/run_7d_smoke_test.py`

**다음 단계**: 사용자가 7D Backtest 실행 후 AC-BT0~BT3 검증

---

## 4. 파일 목록

### 4.1 신규 생성 파일

| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `strategies/phase35_ensemble_v1.py` | 725 | 앙상블 전략 메인 모듈 |
| `common/decision_trace.py` | 500+ | DecisionTrace 시스템 |
| `configs/phase35/ensemble_v1.yaml` | 150+ | Config 파일 |
| `tests/test_phase35_ensemble.py` | 450+ | Unit Tests (18개) |
| `scripts/phase35/run_7d_smoke_test.py` | 80+ | 7D 테스트 러너 |
| `docs/PHASE35/PHASE35_1_REUSE_MAP.md` | 300+ | 재사용 지도 |
| `docs/PHASE35/PHASE35_1_IMPLEMENTATION_REPORT.md` | (현재) | 구현 리포트 |

**총 라인 수**: ~2,400+ lines

---

### 4.2 재사용 파일 (DO-NOT-TOUCH)

| 파일 | 재사용 방식 |
|------|------------|
| `execution/engine.py` | ✅ 그대로 사용 (143KB) |
| `execution/portfolio_manager.py` | ✅ 그대로 사용 (PHASE17 V6.1) |
| `execution/risk_manager.py` | ✅ 그대로 사용 (Guard 시스템) |
| `execution/position_sizer.py` | ✅ 그대로 사용 |
| `execution/position_tracker.py` | ✅ 그대로 사용 |
| `monitoring/telemetry_profiler.py` | ✅ 그대로 사용 |
| `indicators/*.py` | ✅ 그대로 사용 |
| `common/registry/base_strategy.py` | ✅ 인터페이스 상속 |

**중복 구현**: ❌ 0건 (재사용 원칙 100% 준수)

---

## 5. 코드 품질 검증

### 5.1 재사용 원칙 준수

| 항목 | 확인 | 비고 |
|------|------|------|
| ☑️ 새 엔진 만들지 않음 | ✅ | `execution/engine.py` 재사용 |
| ☑️ Portfolio 로직 수정 안 함 | ✅ | PHASE17 V6.1 그대로 |
| ☑️ Indicator 재구현 안 함 | ✅ | `indicators/*.py` 사용 |
| ☑️ 기존 전략 파일 수정 안 함 | ✅ | 신규 모듈만 생성 |
| ☑️ Runner 스크립트 복사 안 함 | ✅ | `run_backtest.py` 재사용 |

### 5.2 Config-Driven 설계

| 항목 | 구현 | 비고 |
|------|------|------|
| ☑️ 하드코딩 숫자 0개 | ✅ | 모든 파라미터 config 관리 |
| ☑️ Sub-Model 파라미터 | ✅ | EMA/RSI/ATR period 등 |
| ☑️ Regime 임계값 | ✅ | trend_min, range_max |
| ☑️ Ensemble 설정 | ✅ | confidence_threshold |
| ☑️ Exit 설정 | ✅ | sl/tp_atr_multiplier |

### 5.3 DecisionTrace 통합

| 항목 | 구현 | 비고 |
|------|------|------|
| ☑️ 차단 사유 기록 | ✅ | REGIME_CHOP, NO_CONSENSUS 등 |
| ☑️ Sub-Model 투표 기록 | ✅ | direction, confidence, reasons |
| ☑️ Regime 정보 기록 | ✅ | TREND/RANGE/CHOP + ATR% |
| ☑️ 분해 통계 제공 | ✅ | 레짐별/사유별/모델별 |
| ☑️ JSON 저장 | ✅ | 백테스트 후 분석 가능 |

---

## 6. 다음 단계 (PHASE35-2)

### 6.1 7-Day Smoke Test 실행

**목표**: AC-BT0~BT3 검증

**AC-BT0 (기술적 정상성)**:
- (BT0-1) 백테스트 에러 없이 종료
- (BT0-2) 동일 config 2회 실행 시 결과 일치 (±3% 허용)

**AC-BT1 (0-trades 금지)**:
- (BT1-1) 7D에서 Trades > 0
- (BT1-2) 레짐별 Trades 모두 > 0 (CHOP 제외)
- (BT1-3) DecisionTrace에서 차단 게이트 TOP3 출력

**AC-BT2 (품질 개선 증거)**:
최소 2개 동시 만족:
- PF: 0.57 → 0.70+ (±0.13 이상)
- WR: 28.4% → 31.0%+ (+2.6%p 이상)
- 레짐별 PF 편차 ≥ 0.15 (구조 검증)
- Exit 사유 분포가 손실 원인을 명확히 설명

**AC-BT3 (앙상블 작동 증명)**:
- (BT3-1) 전략별 vote 기여도 존재
- (BT3-2) 상위 2개 전략이 90% 이상 독점 → FAIL
- (BT3-3) Score 상위 20% PF > 하위 20% PF (+0.05 이상)

---

### 6.2 실행 명령

```bash
# 1. 가상환경 활성화
trading_bot_env\Scripts\activate

# 2. 7D Smoke Test 실행
python scripts/phase35/run_7d_smoke_test.py

# 3. 결과 확인
# - reports/backtest/phase35/
# - reports/backtest/phase35/traces/decision_trace.json

# 4. AC 검증
# - AC-BT0~BT3 항목별 수치 확인
# - DecisionTrace 분석 실행
```

---

### 6.3 PASS 조건

**PHASE35-1 COMPLETE 조건**:
- ✅ Fast Gate 18/18 PASS
- ✅ 코드 품질 검증 완료
- ✅ Git 커밋+푸시 완료
- ⏳ 7D Backtest 실행 준비 완료 (사용자 실행 대기)

**PHASE35-2 진입 조건**:
- 7D Backtest AC-BT0~BT3 **모두 PASS**

---

## 7. Risk & Mitigation

### 7.1 예상 리스크

| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|----------|
| **0 Trades** | Low | High | DecisionTrace로 차단 사유 분석 → 레짐/Confidence 임계값 조정 |
| **PF 개선 실패** | Medium | High | Exit 로직 강화 (Adverse Move, Regime Switch) |
| **레짐 판정 오류** | Low | Medium | ATR 임계값 조정 또는 HMM 도입 (PHASE35-3) |
| **앙상블 불균형** | Low | Medium | Sub-Model 가중치 조정 또는 Confidence Threshold 변경 |

### 7.2 Rollback Plan

**FAIL 시나리오**:
1. AC-BT1 FAIL (0 Trades)
   - DecisionTrace 분석 → 차단 사유 TOP3 확인
   - Regime 임계값 완화 또는 Confidence Threshold 낮춤
   - 1회 iteration 후 재테스트

2. AC-BT2 FAIL (품질 개선 없음)
   - Exit 로직 강화 (Adverse Move Exit 활성화)
   - Sub-Model 로직 재검토 (신호 품질 개선)
   - 2회 iteration 허용

3. AC-BT3 FAIL (앙상블 미작동)
   - 전략 독점 발생 시 → 가중치 재조정
   - Score 구분 실패 시 → Confidence 계산 로직 수정

**PHASE35-1 복귀 기준**:
- 3회 iteration 후에도 AC-BT2 미달 → 설계 재검토

---

## 8. 결론

### 8.1 달성 사항

✅ **구현 완료**:
- Moderate Hybrid 앙상블 전략 (3 Sub-Models + 2/3 Vote)
- ATR 기반 레짐 필터 (TREND/RANGE/CHOP)
- DecisionTrace 품질 원인 추적 시스템
- Config-Driven 설계 (하드코딩 0개)
- 기존 인프라 100% 재사용 (DO-NOT-TOUCH 준수)

✅ **테스트 통과**:
- Fast Gate: 18/18 PASS (1.16초)
- Core Regression: 10/11 PASS (PHASE35 무관 1개 실패)
- 백테스트 준비: 7D Smoke Test 러너 작성 완료

✅ **문서화**:
- 재사용 지도: `PHASE35_1_REUSE_MAP.md`
- 구현 리포트: `PHASE35_1_IMPLEMENTATION_REPORT.md` (현재)
- Config: `configs/phase35/ensemble_v1.yaml`

---

### 8.2 PHASE35-1 상태

**Status**: ✅ **COMPLETE** (구현 및 Fast Gate 완료)

**Next Phase**: PHASE35-2 (7-Day Smoke Test) - **사용자 실행 대기**

**Gating Rule**: ⚠️ **AC-BT0~BT3 모두 PASS 전까지 PHASE35-3 진입 금지**

---

### 8.3 핵심 교훈

**PHASE34 vs PHASE35**:
- PHASE34: **파라미터 튜닝 → 품질 무효** (정량 증명)
- PHASE35: **전략 구조 재설계 → 품질 개선 가능** (DecisionTrace로 검증)

**구조 vs 파라미터**:
- "빈도는 파라미터로, 품질은 구조로"
- DecisionTrace가 **왜 망하는지를 수치로 보여줌** → 개선 방향 명확

**재사용 원칙**:
- DO-NOT-TOUCH 영역 절대 준수
- 기존 검증된 인프라 위에 최소 레이어만 추가
- 중복 구현 0건, 오버리팩토링 0건

---

**작성자**: Cascade AI  
**검토 필요**: 사용자의 7D Backtest 실행 및 AC-BT0~BT3 검증
