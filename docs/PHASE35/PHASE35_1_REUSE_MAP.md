# PHASE35-1: 재사용 지도 (Reuse Map)

**생성일**: 2025-12-13
**목적**: PHASE35-1 Moderate Hybrid 앙상블 구현 시 기존 모듈 최대 재사용 확인

---

## 1. 재사용 가능 인프라 (100% 재사용, DO-NOT-TOUCH)

### 1.1 Core Engine Layer

| 모듈 | 경로 | 역할 | 재사용 방식 |
|------|------|------|------------|
| **Engine** | `execution/engine.py` | 백테스트/Paper/Live 통합 엔진 | ✅ 그대로 사용 (143KB, 멀티모드 지원) |
| **PortfolioManager** | `execution/portfolio_manager.py` | Budget/PnL/Equity SSOT | ✅ 그대로 사용 (PHASE17 V6.1 검증) |
| **RiskManager** | `execution/risk_manager.py` | Exposure/Guard 시스템 | ✅ 그대로 사용 (Guard Telemetry 내장) |
| **PositionSizer** | `execution/position_sizer.py` | Position Size 계산 | ✅ 그대로 사용 |
| **PositionTracker** | `execution/position_tracker.py` | 포지션 추적 | ✅ 그대로 사용 |

**재사용 근거**:
- PHASE17 V6.1에서 12H REAL PAPER 검증 완료 (ERROR/CRITICAL 0건)
- Portfolio SSOT, Budget Cap 정상 작동 확인
- .windsurfrules에 DO-NOT-TOUCH 명시됨

---

### 1.2 Telemetry & Monitoring

| 모듈 | 경로 | 기능 | 활용 계획 |
|------|------|------|----------|
| **TelemetryProfiler** | `monitoring/telemetry_profiler.py` | 이벤트 기반 프로파일링 | ✅ 재사용 (with profiler.profile("event")) |
| **ActivityTracker** | `execution/engine.py` 내장 | Guard Block 기록 | ✅ 재사용 (`record_guard_block()`) |
| **Guard Telemetry** | `execution/risk_manager.py` | Guard 통계 수집 | ✅ PHASE34 분석에 이미 활용 |

**추가 필요 사항**:
- ✨ **DecisionTrace** (신규): 진입/차단 사유를 구조화하여 기록
  - 현재: 엔진에 `record_guard_block()` 훅 존재 → 확장 필요
  - 목표: 레짐별/전략별/차단 사유별 분해 통계

---

### 1.3 Data & Indicators

| 모듈 | 경로 | 기능 | 재사용 |
|------|------|------|--------|
| **Indicators** | `indicators/*.py` | RSI, EMA, ATR 등 | ✅ 그대로 사용 |
| **Data Sources** | `execution/data_sources/` | OHLCV 데이터 공급 | ✅ 그대로 사용 (MTF 지원) |
| **Collectors** | `collectors/*.py` | 백테스트 데이터 수집 | ✅ 그대로 사용 |

---

## 2. 참고 전략 (구조 참고, 갈아엎기 금지)

### 2.1 기존 전략 모듈

| 전략 | 경로 | 특징 | 활용 방식 |
|------|------|------|----------|
| **btc15m_core_v2** | `strategies/btc15m_core_v2.py` | MTF Regime Detection, 2-Tier Filter | 📖 구조 참고 (detect_regime_mtf 로직) |
| **scalping** | `strategies/scalping.py` | 1m 기반 스캘핑 | 📖 신호 생성 패턴 참고 |
| **ensemble** | `strategies/ensemble.py` | 과거 앙상블 시도 | ⚠️ READ-ONLY (PHASE19에서 망가짐, 복구 예정) |

**재사용 방침**:
- `btc15m_core_v2.py`의 `detect_regime_mtf()` 함수 → 레짐 필터 구현 시 참고
- 기존 전략들의 신호 생성 인터페이스 (`generate_signal()`) 구조 재사용
- **갈아엎기 금지**: 기존 전략 파일 수정 대신, 신규 모듈 생성

---

## 3. 실행 스크립트 (재사용 + 확장)

### 3.1 기존 Runner

| 스크립트 | 경로 | 용도 | 재사용 |
|---------|------|------|--------|
| **run_backtest.py** | `scripts/run_backtest.py` | 백테스트 실행 | ✅ PHASE35 백테스트에 그대로 사용 |
| **run_paper.py** | `scripts/run_paper.py` | Paper Trading | ✅ PHASE35-5에서 사용 |
| **run_v2.py** | `scripts/run_v2.py` | V2 엔진 실행 | ✅ 참고 (MTF 지원 확인) |

**확장 계획**:
- 기존 스크립트는 수정 없이 사용
- Config 파일로 전략 선택 (`configs/phase35/ensemble_v1.yaml`)

---

## 4. 신규 구현 필요 항목 (최소 추가)

### 4.1 전략 레이어

| 항목 | 경로 (예상) | 역할 | 우선순위 |
|------|-------------|------|----------|
| **Ensemble Strategy** | `strategies/phase35_ensemble_v1.py` | 3개 Sub-Model + 2/3 Vote | 🔴 P0 (PHASE35-1 핵심) |
| **Sub-Model 1** | 내장 함수 | Trend-Following 로직 | 🔴 P0 |
| **Sub-Model 2** | 내장 함수 | Mean-Reversion 로직 | 🔴 P0 |
| **Sub-Model 3** | 내장 함수 | Breakout 로직 | 🔴 P0 |

**구현 원칙**:
- ✅ BaseStrategy 상속 (기존 인터페이스 호환)
- ✅ Config-driven (하드코딩 금지)
- ✅ 각 Sub-Model은 함수로 구현 (독립 모듈 아님)
- ✅ 출력: `{direction: LONG/SHORT/FLAT, confidence: 0~1, reasons: []}`

---

### 4.2 Regime Filter (간이 버전 우선)

| 항목 | 구현 위치 | 방식 | 우선순위 |
|------|----------|------|----------|
| **ATR 필터** | `strategies/phase35_ensemble_v1.py` 내 함수 | ATR 임계값 기반 3상태 (TREND/RANGE/CHOP) | 🟡 P1 (초기) |
| **HMM 필터** | (미래) `strategies/utils/hmm_regime.py` | 은닉 마코프 모델 | ⚪ P2 (PHASE35-3 이후) |

**초기 접근**:
- ATR + MTF(1H/4H) 기반 단순 레짐 판정 (PHASE35-1~2)
- HMM은 PHASE35-3 이후 추가 검토

---

### 4.3 DecisionTrace (품질 원인 추적)

| 항목 | 구현 위치 | 기능 | 우선순위 |
|------|----------|------|----------|
| **DecisionTrace Logger** | `common/decision_trace.py` (신규) | 진입/차단 사유 구조화 기록 | 🔴 P0 |
| **Trace Aggregator** | `scripts/phase35/analyze_decision_trace.py` (신규) | 레짐별/전략별 분해 통계 | 🔴 P0 |

**출력 예시**:
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "symbol": "BTCUSDT",
  "regime": "TREND_UP",
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

---

### 4.4 Exit Logic (손실 패턴 고정 방지)

| 항목 | 구현 위치 | 방식 | 우선순위 |
|------|----------|------|----------|
| **Time-based Exit** | `strategies/phase35_ensemble_v1.py` | holding_max_bars 설정 | 🟡 P1 |
| **Adverse Move Exit** | 동일 | ATR 스케일 기반 조기 종료 | 🟡 P1 |
| **Regime Switch Exit** | 동일 | 레짐 전환 시 포지션 축소 | ⚪ P2 |

---

## 5. Config 구조 (신규)

### 5.1 Ensemble Config

**경로**: `configs/phase35/ensemble_v1.yaml`

```yaml
strategy:
  name: "phase35_ensemble_v1"
  type: "ensemble"
  
  sub_models:
    - name: "trend_following"
      weight: 0.4
      indicators: ["ema_20", "ema_50", "adx"]
    
    - name: "mean_reversion"
      weight: 0.3
      indicators: ["rsi", "bbands"]
    
    - name: "breakout"
      weight: 0.3
      indicators: ["atr", "volume"]
  
  ensemble:
    method: "majority_vote"  # 2-out-of-3
    confidence_threshold: 0.5
  
  regime_filter:
    enabled: true
    type: "atr_simple"  # ATR 기반 간이 필터
    atr_period: 14
    thresholds:
      trend_min: 0.015  # ATR% 1.5% 이상
      range_max: 0.008  # ATR% 0.8% 이하
  
  exit:
    time_based:
      holding_max_bars: 48  # 15m × 48 = 12H
    adverse_move:
      atr_multiplier: 1.5
    regime_switch:
      enabled: false  # PHASE35-2 이후
```

---

## 6. 테스트 인프라 (재사용 + 확장)

### 6.1 기존 테스트

| 테스트 | 경로 | 재사용 |
|--------|------|--------|
| **Core Regression** | `tests/test_*.py` | ✅ 기존 회귀 테스트 유지 |
| **Integration** | `tests/integration/*.py` | ✅ 엔진 통합 테스트 재사용 |

### 6.2 신규 테스트 (필수)

| 테스트 | 경로 (예상) | 목적 | 우선순위 |
|--------|-------------|------|----------|
| **Ensemble Unit Test** | `tests/test_phase35_ensemble.py` | Sub-Model 로직, Vote 검증 | 🔴 P0 |
| **DecisionTrace Test** | `tests/test_decision_trace.py` | Trace 기록/집계 검증 | 🔴 P0 |
| **Smoke Test Runner** | `scripts/phase35/run_7d_smoke_test.py` | 7일 백테스트 자동 실행 | 🟡 P1 |

---

## 7. 재사용 원칙 요약

### ✅ 100% 재사용 (DO-NOT-TOUCH)
- `execution/engine.py`
- `execution/portfolio_manager.py`
- `execution/risk_manager.py`
- `execution/position_sizer.py`
- `execution/position_tracker.py`
- `monitoring/telemetry_profiler.py`
- `indicators/*.py`

### 📖 구조 참고 (수정 금지)
- `strategies/btc15m_core_v2.py` (detect_regime_mtf)
- `strategies/scalping.py` (신호 생성 패턴)
- `strategies/ensemble.py` (READ-ONLY, 복구 예정)

### ✨ 신규 구현 (최소 필요)
- `strategies/phase35_ensemble_v1.py` (앙상블 전략)
- `common/decision_trace.py` (DecisionTrace)
- `scripts/phase35/analyze_decision_trace.py` (분석기)
- `configs/phase35/ensemble_v1.yaml` (Config)
- `tests/test_phase35_ensemble.py` (Unit Test)

---

## 8. 중복 구현 금지 체크리스트

| 항목 | 확인 | 비고 |
|------|------|------|
| ☑️ 새 엔진 만들지 않음 | ✅ | `execution/engine.py` 재사용 |
| ☑️ Portfolio 로직 수정 안 함 | ✅ | PHASE17 V6.1 그대로 |
| ☑️ Indicator 재구현 안 함 | ✅ | `indicators/*.py` 사용 |
| ☑️ 기존 전략 파일 수정 안 함 | ✅ | 신규 모듈만 생성 |
| ☑️ Runner 스크립트 복사 안 함 | ✅ | `run_backtest.py` 그대로 |

---

## 9. 다음 단계 (STEP 2 구현)

**구현 순서**:
1. `strategies/phase35_ensemble_v1.py` 생성 (3 Sub-Models + Vote)
2. `common/decision_trace.py` 생성 (Trace 기록)
3. `configs/phase35/ensemble_v1.yaml` 생성 (Config)
4. `tests/test_phase35_ensemble.py` 생성 (Unit Test)
5. Fast Gate 테스트 → PASS 확인
6. Core Regression → 100% PASS 확인
7. 7D Smoke Test → AC-BT0~BT3 검증

---

**작성자**: Cascade AI  
**검토 필요**: STEP 2 구현 전 이 지도 기반으로 작업 범위 확정
