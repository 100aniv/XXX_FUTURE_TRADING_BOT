# PHASE17 비전 정합성 분석 리포트

**작성일**: 2025-11-17 23:50 KST  
**목적**: PHASE17 구현이 PROJECT_VISION_TOBE.md와 정합하는지 검증

---

## 📌 1. PROJECT_VISION_TOBE 핵심 원칙 요약

### 1-1. 4대 레이어 구조

```
1. Core Engine Layer (DO-NOT-TOUCH)
   - 단일 메인 루프: 시세 수집 → 전략 호출 → 시그널 → RiskManager → PortfolioManager → 주문
   - Backtest/Paper/Live 공통 사용
   - 엔진의 기본 시그니처/입출력/이벤트 흐름은 모두 모드 공통

2. Strategy & Ensemble Layer
   - 각 전략은 "시그널 생성기" 역할만
   - 포지션 크기, 리스크, 노출은 Risk/Portfolio Layer에서 관리

3. Risk & Portfolio Layer
   - PositionSizer: "얼마나 살 것인가" (size 계산)
   - RiskManager: per-trade/per-symbol/per-day 리스크 관리
   - PortfolioManager: PnL, Equity, Max DD, Exposure의 단일 소스
   - FlowGuardian: Drawdown, Exposure, Slippage, Flash, Cooldown Guard

4. Infra & UX Layer
   - 데이터 수집 / Redis / Postgres
   - CLI, Runbook, 모니터링, 로그, 리포트
```

### 1-2. 핵심 철학

```
✅ 엔진 코어 = DO-NOT-TOUCH 레이어
   → Backtest/Paper/Live가 모두 동일 엔진 사용

✅ 모든 행동은 config-based / YAML 기반
   → 전략/리스크/포트폴리오 파라미터는 전부 설정파일로 관리

✅ Risk & Guard 우선
   → 모든 주문 전 FlowGuardian에서 최종 승인

✅ DRY, SRP, 최소 변경
   → 모듈 간 책임 일관성 유지
```

---

## ❌ 2. PHASE17 구현의 비전 불일치 분석

### 2-1. **심각**: 엔진 통합 누락

**문제**:
- PHASE17에서 추가한 핵심 메서드들이 `execution/engine.py`에서 **전혀 사용되지 않음**
- 현재 엔진은 여전히 구 방식 사용:
  ```python
  # engine.py Line 1155 (현재 사용 중)
  qty, meta = sizer.calculate(signal)
  
  # engine.py Line 1246 (현재 사용 중)
  allowed, reason = risk.check_order(decision, qty, position_value)
  
  # ❌ PHASE17 신규 메서드 (미사용)
  # position_sizer.calculate_with_exposure_check()
  # risk_manager.check_symbol_exposure_with_adjustment()
  ```

**비전 위반**:
- ✅ "DO-NOT-TOUCH 엔진" 원칙은 지켰으나,
- ❌ 신규 로직이 엔진에 통합되지 않아 **실제로 작동하지 않음**

**파급효과**:
- PHASE17 설계 문서의 Multi-position Scaling, Exposure Guard 3단계 의사결정이 **런타임에서 비활성화 상태**
- 12h REAL PAPER 재테스트를 해도 PHASE16과 동일한 결과 발생 예상

---

### 2-2. **중간**: 책임 분리 미흡

**문제**:
- `PositionSizer`와 `RiskManager` 모두 Exposure 체크 로직 포함:
  ```python
  # position_sizer.py::calculate_with_exposure_check()
  # → Exposure Guard 3단계 의사결정 포함
  
  # risk_manager.py::check_symbol_exposure_with_adjustment()
  # → Exposure Guard 3단계 의사결정 포함 (중복)
  ```

**비전 위반**:
- PROJECT_VISION_TOBE.md §4.2: "RiskManager: per-symbol 노출 제한"
- 현재는 PositionSizer와 RiskManager가 모두 Exposure 체크 수행 → **DRY 위반**

**권장 구조**:
```
✅ PositionSizer:
   - 기본 포지션 크기 계산
   - Multi-position Scaling 적용
   - Volatility Scaling 적용
   - BUT, Exposure Guard는 호출하지 않음 (책임 초과)

✅ RiskManager:
   - Per-symbol Exposure Guard (ALLOW/ALLOW_REDUCED/BLOCK)
   - Per-trade 리스크 한도
   - 일일 손실 한도
   - Flash Guard, Cooldown

✅ PortfolioManager:
   - 현재 노출도 계산 및 제공
   - PnL, Equity, DD 추적
```

---

### 2-3. **경미**: 변경 범위 과다

**문제**:
- PHASE17 커밋: 56개 파일, +13,120줄
- 실제 런타임 코드 변경은 3개 파일에 국한:
  - `execution/position_sizer.py` (+197줄)
  - `execution/risk_manager.py` (+128줄)
  - `configs/base.yml` (+14줄)
- 나머지는 문서, 설정, 테스트, 스냅샷 등

**비전 위반**:
- ✅ "최소 변경" 원칙은 대체로 준수 (문서 제외 시)
- ⚠️ 하지만 56개 파일 변경은 리뷰/추적 부담 증가

**권장**:
- 문서/리포트는 별도 커밋으로 분리
- 런타임 코드 변경만 모아서 작은 PR 단위로 관리

---

## ✅ 3. PHASE17 구현의 비전 정합 요소

### 3-1. Config 기반 설계

**정합**:
- `configs/base.yml`에 PHASE17 필드 추가
- 하위 호환성 유지 (기존 필드는 그대로)
- 기본값 제공으로 기존 설정 파일에서도 작동

**예시**:
```yaml
position_sizing:
  multi_position_scaling: true
  allow_partial_entry: true
  exposure_reduction_factor: 0.95
```

**비전 준수**: ✅ "모든 행동은 config-based"

---

### 3-2. FlowGuardian 통합 가능성

**정합**:
- `RiskManager.check_symbol_exposure_with_adjustment()`가 3단계 의사결정 제공
- `ExposureDecision` 데이터 클래스로 명확한 의사결정 이유 전달
- 향후 FlowGuardian에 쉽게 통합 가능

**비전 준수**: ✅ "Risk & Guard 우선"

---

### 3-3. 단위 테스트 작성

**정합**:
- `tests/test_phase17_position_sizing.py` (16개 테스트)
- Multi-position Scaling, Exposure Guard, Edge Cases 커버
- PHASE16 실패 케이스 재현 및 검증

**비전 준수**: ✅ "문서 → 코드 → 테스트 순환 루프"

---

## 🔧 4. 수정 필요 사항 (우선순위별)

### P0 (즉시): 엔진 통합

```python
# execution/engine.py Line 1154-1246 수정 필요

# [현재] 구 방식
qty, meta = sizer.calculate(signal)
allowed, reason = risk.check_order(decision, qty, position_value)

# [수정 후] PHASE17 방식
# 1. PositionSizer에서 기본 크기 + Multi-position Scaling 계산
# 2. RiskManager에서 Exposure Guard 3단계 의사결정
# 3. 의사결정에 따라 크기 조정 또는 차단
```

**작업량**: engine.py 약 50줄 수정

---

### P1 (중요): 책임 분리 명확화

**옵션 A (권장)**: PositionSizer에서 Exposure Check 제거
```python
# position_sizer.py
# ❌ calculate_with_exposure_check() 삭제
# ✅ apply_multi_position_scaling() 유지
```

**옵션 B (대안)**: RiskManager에서만 Exposure Check 수행
```python
# risk_manager.py
# ✅ check_symbol_exposure_with_adjustment() 유지
# engine.py에서 이 메서드만 사용
```

**작업량**: 약 100줄 제거 또는 수정

---

### P2 (선택): 변경 범위 정리

- 문서/리포트 커밋 분리
- 런타임 코드 변경만 재커밋
- 변경 이력 정리

**작업량**: Git 히스토리 정리 (선택)

---

## 📊 5. 최종 정합성 평가

| 평가 항목 | 상태 | 점수 |
|----------|------|------|
| **DO-NOT-TOUCH 엔진** | ⚠️ 엔진 미수정 (통합 필요) | 50/100 |
| **Config 기반 설계** | ✅ 완벽 준수 | 100/100 |
| **Risk & Guard 우선** | ✅ FlowGuardian 통합 가능 | 90/100 |
| **DRY/SRP** | ⚠️ 책임 중복 존재 | 60/100 |
| **최소 변경** | ⚠️ 변경 범위 과다 (문서 포함) | 70/100 |
| **테스트 주도** | ✅ 단위 테스트 작성 완료 | 90/100 |
| **총점** | **중간** | **73/100** |

---

## 🎯 6. 수정 후 예상 정합성

위 P0/P1 작업 완료 시:

| 평가 항목 | 예상 점수 |
|----------|---------|
| **DO-NOT-TOUCH 엔진** | 95/100 (통합 완료, 최소 변경) |
| **DRY/SRP** | 95/100 (책임 명확화) |
| **총점** | **92/100** |

---

## 📝 7. 결론

### 7-1. 핵심 문제

**PHASE17 구현은 설계와 코드는 우수하나, 실제 엔진과의 통합이 누락되어 런타임에서 작동하지 않는 상태입니다.**

### 7-2. 해결 방안

1. ✅ **엔진 통합 (P0)**: `engine.py`에서 PHASE17 로직 호출
2. ✅ **책임 분리 (P1)**: PositionSizer ↔ RiskManager 간 Exposure 체크 중복 제거
3. ⚠️ **테스트 실행 (P0)**: Import 오류 해결 및 통과 확인

### 7-3. 작업 시간 예상

- P0 (엔진 통합): 1시간
- P1 (책임 분리): 30분
- P0 (테스트 수정): 30분
- **총 2시간**

---

**다음 작업**: [TASK 2] engine.py 통합 구현
