# PR13 — 시스템 현황 분석

> **작성일**: 2025-11-06 18:40  
> **목적**: 현재 시스템 완벽 분석 → 설계 기반 마련

---

## 📊 1. 기존 구현 현황

### 1.1 이미 구현된 모듈

#### ✅ Tuning System (`tuning/`)

**파일**: `tuning/tuning_core.py`

**구현 내용**:
```python
class TunerCore:
    - Optuna TPE Sampler + MedianPruner
    - 7일 롤링 메트릭 (Postgres 기반)
    - 스코어: Sharpe * trade_term * (1 - dd_penalty)
    - 단일 전략 파라미터 튜닝
      * scalping, daytrade, trend, swing, reversion, breakout
    - 파라미터 발행: configs/<전략>/active.yml
```

**한계**:
- ❌ **Ensemble 파라미터 튜닝 미지원**
- ❌ config.yml 오버라이드 메커니즘 없음
- ❌ 롤아웃 전략 없음
- ❌ 가드레일 미구현

---

#### ✅ Analytics (`analytics/`)

**파일**: `analytics/report_generator.py`

**구현 내용**:
```python
class ReportGenerator:
    - JSON/HTML/Telegram 리포트 생성
    - 일일/주간 리포트
```

**한계**:
- ❌ **A/B 비교 기능 없음**
- ❌ Baseline vs Tuned 비교 리포트 미지원

---

#### ✅ Metrics (`metrics/compute.py`)

**구현 내용**:
```python
class MetricsEngine(IMetrics):
    - profit_factor, winrate, exp_score, score_total 계산
    - FlowGuardian 게이트용
```

**한계**:
- ❌ **Sharpe, MDD, Sortino 등 고급 메트릭 미지원**
- ❌ 시계열 메트릭 추적 없음

---

#### ✅ Core Interfaces (`core/interfaces.py`)

**구현 내용**:
```python
# Protocol-based contracts
- IDataSource, IStrategy, IRisk, IBroker, IMetrics
```

**강점**:
- ✅ 계약 기반 아키텍처 (확장 가능)
- ✅ 타입 안정성

---

#### ✅ Ensemble System (`strategies/ensemble.py`)

**구현 내용**:
```python
- calculate_experience_score()
- calculate_weights() with clamping
```

**한계**:
- ❌ **파라미터가 하드코딩**
- ❌ 튜닝 불가 (config.yml에서 로드하지만 정적)

---

## 📋 2. Gap Analysis

| 기능 | 현재 상태 | 필요 상태 | Gap | 우선순위 |
|------|-----------|-----------|-----|----------|
| Ensemble 튜닝 | ❌ 없음 | ✅ alpha, beta, gamma 등 튜닝 | 🔴 크리티컬 | P0 |
| 오버레이 시스템 | 🟡 파일만 | ✅ 런타임 오버라이드 | 🟡 중요 | P1 |
| 롤아웃 전략 | ❌ 없음 | ✅ 섀도우→카나리→full | 🔴 크리티컬 | P0 |
| 가드레일 | ❌ 없음 | ✅ DD/거래수/변동성 | 🔴 크리티컬 | P0 |
| A/B 리포트 | ❌ 없음 | ✅ Baseline vs Tuned | 🟡 중요 | P1 |
| 실험 추적 | 🟡 Optuna | ✅ MLflow-like | 🟢 선택 | P2 |
| 자동 롤백 | ❌ 없음 | ✅ 가드레일 위반 시 | 🔴 크리티컬 | P0 |

---

## 🎯 3. 핵심 요구사항

### 3.1 Ensemble 파라미터 튜닝 (P0)
```yaml
# 튜닝 대상
ensemble:
  alpha_winrate: 0.4      # 범위: 0.2~0.6
  beta_rr: 0.2            # 범위: 0.1~0.4
  gamma_sharpe: 0.2       # 범위: 0.1~0.4
  delta_confidence: 0.15  # 범위: 0.05~0.25
  epsilon_regime: 0.05    # 범위: 0.0~0.15
```

**제약 조건**:
- alpha + beta + gamma + delta + epsilon ≈ 1.0 (±0.1)

### 3.2 롤아웃 전략 (P0)
```
none → shadow (8h) → canary (10%→30%→50%→100%) → full
```

### 3.3 가드레일 (P0)
- DD 증가 ≤ 0.5%p
- 최소 거래수 ≥ 20
- 변동성 증가 ≤ 20%

---

## 📁 4. 파일 구조 제안

```
tuning/
├── __init__.py
├── tuning_core.py              # 기존 (단일 전략용)
├── ensemble_tuner.py           # 🆕 Ensemble 튜닝
├── config_overlay.py           # 🆕 설정 오버레이
├── rollout_manager.py          # 🆕 롤아웃 관리
├── guardrail_engine.py         # 🆕 가드레일
└── tuning_api.py               # 🆕 API

analytics/
├── __init__.py
├── report_generator.py         # 기존
└── ab_comparison.py            # 🆕 A/B 비교

configs/
├── base/
│   └── config.yml              # 베이스 설정
├── overlays/
│   ├── tuning_baseline.yml
│   ├── tuning_trial_001.yml
│   └── tuning_best.yml
└── active/
    └── current.yml             # 현재 활성화
```

---

## ✅ 다음 단계

1. **ConfigOverlay 구현** → 오버레이 시스템
2. **EnsembleTuner 구현** → Ensemble 튜닝
3. **RolloutManager 구현** → 롤아웃 관리
4. **GuardrailEngine 구현** → 가드레일
5. **ABComparisonReport 구현** → A/B 리포트
