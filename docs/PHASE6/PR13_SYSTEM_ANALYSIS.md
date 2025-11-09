# PR13 — 시스템 현황 분석

> **작성일**: 2025-11-06 18:40  
> **목적**: 현재 시스템 완벽 분석 → 설계 기반 마련

---

## 📊 1. 기존 구현 현황 (.windsurfrules 아키텍처 계층 기준)

### 1.1 이미 구현된 모듈

#### ✅ Tuning System (`tuning/`) - .windsurfrules 튜닝 전담 계층

**파일**: `tuning/tuning_core.py` (.windsurfrules tuning/** 허용 범위)

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

**한계 (.windsurfrules Module Relocation Policy PR13)**:
- ❌ **Ensemble 파라미터 튜닝 미지원** (단일 전략만 지원)
- ❌ **common/tuning_*.py deprecated** (단일 진실 소스는 tuning/ 하위)
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

#### ✅ Metrics (`metrics/compute.py`) - .windsurfrules 메트릭 전담 계층

**구현 내용** (.windsurfrules 허용 파일):
```python
class MetricsEngine(IMetrics):
    - profit_factor, winrate, exp_score, score_total 계산
    - FlowGuardian 게이트용
    - 의존: core/interfaces.py (IMetrics Protocol)
```

**아키텍처 상태** (.windsurfrules Module Relocation Policy):
- ✅ **위치 유지**: metrics/compute.py는 core로 이동 금지 (단일 책임·의존 방향 유지)
- ✅ **import 경로 고정**: `from metrics.compute import MetricsEngine`

**한계**:
- ❌ **Sharpe, MDD, Sortino 등 고급 메트릭 미지원**
- ❌ 시계열 메트릭 추적 없음

---

#### ✅ Core Interfaces (`core/interfaces.py`) - .windsurfrules 계약/게이트 전담 계층

**구현 내용** (.windsurfrules 허용 파일):
```python
# Protocol-based contracts
- IDataSource, IStrategy, IRisk, IBroker, IMetrics, IPortfolio
- FlowGuardian READY 게이트 계약
```

**아키텍처 준수** (.windsurfrules Architecture Layering Policy):
- ✅ **core/ 전담**: 계약/게이트만 위치. 비즈니스 구현/메트릭 로직 금지
- ✅ 계약 기반 아키테쌈 (확장 가능)
- ✅ 타입 안전성

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

## 📋 2. Gap Analysis (.windsurfrules 대비 분석)

| 기능 | 현재 상태 | 필요 상태 (.windsurfrules) | Gap | 우선순위 |
|------|-----------|-----------|-----|----------|
| Ensemble 튜닝 | ❌ 없음 | ✅ tuning/ensemble_tuner.py 구현 | 🔴 크리티컴 | P0 |
| ConfigOverlay | 🟡 파일만 | ✅ tuning/config_overlay.py | 🟡 중요 | P0 |
| 롤아웃 전략 | ❌ 없음 | ✅ tuning/rollout_manager.py | 🔴 크리티컴 | P0 |
| 가드레일 | ❌ 없음 | ✅ tuning/guardrail_engine.py | 🔴 크리티컴 | P0 |
| A/B 리포트 | ❌ 없음 | ✅ analytics/ab_comparison.py | 🟡 중요 | P1 |
| FlowGuardian 게이트 | 🟡 일부 | ✅ 모든 모드 READY 강제 | 🔴 크리티컴 | P0 |
| DB/Redis 분리 | ❌ 없음 | ✅ env/run_id/네임스페이스 | 🔴 크리티컴 | P0 |
| 자동 롤백 | ❌ 없음 | ✅ 가드레일 위반 시 | 🔴 크리티컴 | P0 |

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

## 📁 4. 파일 구조 제안 (.windsurfrules 준수)

### 허용 파일 범위 (.windsurfrules Files You May Edit)
```
tuning/                          # tuning/** 허용
├── __init__.py
├── tuning_core.py              # 기존 (단일 전략용)
├── ensemble_tuner.py           # 🆕 Ensemble 튜닝 (신규)
├── config_overlay.py           # 🆕 설정 오버레이 (신규)
├── rollout_manager.py          # 🆕 롤아웃 관리 (신규)
├── guardrail_engine.py         # 🆕 가드레일 (신규)
└── tuning_api.py               # 🆕 API (신규)

analytics/                       # analytics/** 허용
├── __init__.py
├── report_generator.py         # 기존
└── ab_comparison.py            # 🆕 A/B 비교 (신규)

core/                            # 계약/게이트 추가 허용
├── interfaces.py               # ✏️ 튜닝 Protocol 추가
└── flow_guardian.py            # ✏️ 튜닝 모드 READY 판정

execution/                       # 엔진 연계 허용
└── engine.py                   # ✏️ ConfigOverlay 적용

common/                          # 메시지 템플릿 허용
└── messaging.py                # ✏️ 튜닝 메시지

metrics/                         # 메트릭 지원 허용
└── compute.py                  # ✏️ 튜닝 메트릭

tests/                           # 테스트 추가 허용
├── test_config_overlay.py      # 🆕 단위 테스트
├── test_ensemble_tuner.py      # 🆕 단위 테스트
└── test_rollout_manager.py     # 🆕 단위 테스트

docs/PHASE6/                     # 문서 업데이트 허용
├── PR13_MASTER_PLAN.md
├── PR13_ARCHITECTURE_DESIGN.md
├── PR13_SYSTEM_ANALYSIS.md
└── PR13_BUG #8_ADD.md
```

### 모듈 재배치 정책 (PR13)
- **deprecated**: `common/tuning_*.py` → `tuning/` 하위로 이관
- **유지**: `metrics/compute.py` core 이동 금지 (단일 책임 유지)

---

## 🔄 문제→해결(To-Be) 매핑

- **Redis 네임스페이스 충돌(캔들 dedup, 파라미터 채널)**
  - 문제: `candle:seen:{symbol}:{timeframe}:{closed_at}` 등 키에 모드 구분 없음 → Paper/Live/Tuner 충돌 위험
  - 해결: `{ns}:{env}:{run_id}:<domain>` 네임스페이스 도입. 예) `fa:paper:{run}:candle:seen:...`, 채널 `tuning.params.set`, `ensemble.weights.update`, `risk.cap.update`, `throttle.update`, `equity.set`

- **모드 우선순위 혼선**
  - 문제: `.env`/config 혼용으로 실제 실행 모드 불일치 가능
  - 해결: `config.yml(mode)` > `ENV.TRADING_MODE` > 기본값 `paper` 우선순위 확정. FlowGuardian READY에서 최종 모드 검증/로깅

- **단일 DB 내 환경 분리 부재**
  - 문제: paper/live 데이터 혼재로 분석/튜닝 교란
  - 해결: 모든 테이블 공통 컬럼 `env VARCHAR(10)`, `run_id UUID`, `created_at TIMESTAMPTZ` 추가/검증. 뷰/인덱스에 `(env, created_at)` 포함

- **FlowGuardian READY 미강제**
  - 문제: READY 게이트 누락 시 엔진 기동 가능
  - 해결: `execution/engine.py` 진입부에서 `FlowGuardian.assert_ready(mode)` 1회 호출 강제, 중복 금지. 실패시 즉시 중단

- **큐 헬스 라벨 편향**
  - 문제: `📊 [PR5 Queue]` 라벨로 프로젝트 단계 종속
  - 해결: "Queue Health"로 중립화. Phase 독립 로그 정책 채택

- **Paper/Live 파리티 일부 불일치**
  - 문제: 자산 동기화/메트릭/라운딩 경로 차이
  - 해결: PortfolioManager 단일 소스, `portfolio.sync_equity_with_broker()` 양 모드 공통 호출. 라운딩/펀딩 API 공용. Broker 계층만 분리

- **A/B 비교 및 수용 기준 부재**
  - 문제: 튜닝 효과 검증 체계 부족
  - 해결: `analytics/ab_comparison.py` 도입, baseline vs tuned 비교. 수용 기준을 `.windsurfrules`와 동기화

- **로그/DB 일치성 검증 부재**
  - 문제: logs/trial_0000.json과 DB 수치 불일치 탐지 어려움
  - 해결: 테스트 파이프라인에 `DB.score_total == JSON.score_total` 체크 추가. 샘플링 또는 전량 비교 기록

---

---

## ✅ 5. 처리 단계 (.windsurfrules 준수)

### Phase 1: 핵심 컴포넌트 (P0)
1. **ConfigOverlay** (`tuning/config_overlay.py`) → 오버레이 시스템
2. **EnsembleTuner** (`tuning/ensemble_tuner.py`) → Ensemble 튜닝
3. **RolloutManager** (`tuning/rollout_manager.py`) → 롤아웃 관리
4. **GuardrailEngine** (`tuning/guardrail_engine.py`) → 가드레일

### Phase 2: 분석 및 테스트 (P1)
5. **ABComparisonReport** (`analytics/ab_comparison.py`) → A/B 리포트
6. **테스트 세트** (`tests/**`) → unit/contract/flow/gate/tuning 매트릭스

### Phase 3: 통합 및 검증 (P0)
7. **FlowGuardian 강화** (`core/flow_guardian.py`) → 모든 모드 READY 강제
8. **DB/Redis 분리** → env/run_id/created_at 및 네임스페이스 적용
9. **수용 기준 검증** → .windsurfrules Testing & Acceptance 준수
