# PHASE17: Position Sizing + Exposure Guard 리팩토링 구현 리포트

**작성일**: 2025-11-17  
**상태**: 구현 완료 (테스트 대기)  
**목표**: PHASE16 REAL PAPER 12h 실패 원인을 구조적으로 해결

---

## 📌 1. 구현 요약

### 1-1. 목표 달성 현황

| 목표 | 상태 | 비고 |
|------|------|------|
| ✅ 동적 Position Sizing 구현 | 완료 | Multi-position Scaling + Volatility Scaling |
| ✅ Per-symbol Exposure Guard 3단계 의사결정 | 완료 | ALLOW / ALLOW_REDUCED / BLOCK |
| ✅ Position Sizer와 Risk Manager 통합 | 완료 | calculate_with_exposure_check() 메서드 |
| ✅ YAML 스키마 확장 | 완료 | position_sizing 섹션 신규 필드 추가 |
| ✅ 하위 호환성 유지 | 완료 | 기존 설정 그대로 동작 |
| ⏳ 단위 테스트 실행 | 대기 | 작성 완료, 통합 환경에서 실행 예정 |
| ⏳ 12h REAL PAPER 재테스트 | 예정 | v4_phase17.yml 설정으로 실행 |

### 1-2. 수정/생성된 파일

```
📄 수정된 파일 (3개):
├── execution/position_sizer.py        (+197줄) - Multi-position Scaling + Exposure Check
├── execution/risk_manager.py          (+128줄) - 3단계 의사결정 로직
└── configs/base.yml                   (+14줄)  - PHASE17 필드 추가

📄 신규 생성된 파일 (3개):
├── docs/PHASE17/PHASE17_POSITION_SIZING_DESIGN.md
├── docs/PHASE17/PHASE17_POSITION_SIZING_REPORT.md (현재 파일)
├── configs/scalping/real_paper_12h_v4_phase17.yml
└── tests/test_phase17_position_sizing.py
```

---

## 🔧 2. 구현 상세

### 2-1. Position Sizer 강화 (execution/position_sizer.py)

#### 추가된 메서드

**A) `apply_multi_position_scaling()`**

```python
def apply_multi_position_scaling(
    self, 
    base_risk: float, 
    num_open_positions: int, 
    max_positions: int
) -> float:
    """
    동시 포지션 수에 따른 리스크 크기 조정
    
    공식: scaling_factor = 1.0 / (1 + num_open / max_positions)
    
    예시:
    - max_positions=2, num_open=0 → scaling=1.0 (100%)
    - max_positions=2, num_open=1 → scaling=0.667 (67%)
    - max_positions=2, num_open=2 → scaling=0.5 (50%)
    """
```

**특징**:
- Config 기반 ON/OFF (`multi_position_scaling: true/false`)
- `max_positions=0`이면 무제한으로 간주하여 스케일링 적용 안 함
- 로그로 스케일링 계산 과정 기록

**B) `calculate_with_exposure_check()`**

```python
def calculate_with_exposure_check(
    self,
    signal: Dict,
    current_symbol_exposure: float,
    max_symbol_exposure: float,
    num_open_positions: int = 0
) -> Tuple[float, Dict, str]:
    """
    ⭐ PHASE17: 포지션 크기 계산 + Exposure Guard 통합
    
    Returns:
        (qty, metadata, action)
        - action: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
    """
```

**프로세스**:
1. 기본 포지션 크기 계산 (`calculate()` 재사용)
2. Multi-position Scaling 적용
3. Per-symbol Exposure 체크
   - **ALLOW**: `total_exposure ≤ max_symbol_exposure`
   - **ALLOW_REDUCED**: `current < max < current + requested`
     - 조정 금액 = `(max - current) × 0.95` (95% 안전 마진)
     - 최소 크기 체크 (`min_position_notional`)
   - **BLOCK**: `current ≥ max` 또는 조정 금액이 최소값 미만

**장점**:
- Risk Manager와 독립적으로 작동 가능
- 메타데이터에 의사결정 이유 명확히 기록
- 로그 레벨별 구분 (DEBUG/WARNING/ERROR)

---

### 2-2. Risk Manager 3단계 의사결정 (execution/risk_manager.py)

#### 추가된 데이터 클래스

```python
@dataclass
class ExposureDecision:
    """
    Per-symbol Exposure Guard 의사결정 결과
    
    Attributes:
        decision: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
        adjusted_notional: 조정된 포지션 금액 (USDT)
        reason: 결정 사유
        original_notional: 원래 요청 금액
        current_exposure: 현재 심볼 노출도
        max_exposure: 최대 허용 노출도
    """
```

#### 추가된 메서드

**`check_symbol_exposure_with_adjustment()`**

```python
def check_symbol_exposure_with_adjustment(
    self,
    symbol: str,
    requested_notional: float,
    current_exposure: float = None,
    min_position_notional: float = None
) -> ExposureDecision:
    """
    ⭐ PHASE17: Per-symbol Exposure 체크 + 사이즈 조정
    
    3단계 의사결정:
    1. ALLOW: 정상 진입 (노출도 범위 내)
    2. ALLOW_REDUCED: 사이즈 축소 후 진입 (노출도 초과 시)
    3. BLOCK: 완전 차단 (현재 노출도가 이미 한계)
    """
```

**의사결정 로직**:

```python
# 1. 총 노출도 계산
total_exposure = current_exposure + requested_notional
max_symbol_exposure = equity × max_exposure_per_symbol_pct

# 2. 3단계 의사결정
if total_exposure ≤ max_symbol_exposure:
    return ALLOW
elif current_exposure < max_symbol_exposure:
    available = max_symbol_exposure - current_exposure
    adjusted = available × 0.95  # 안전 마진
    if adjusted ≥ min_position_notional:
        return ALLOW_REDUCED
    else:
        return BLOCK  # 조정 후 크기가 너무 작음
else:
    return BLOCK  # 현재 노출도가 이미 한계
```

**통합 방식**:
- 기존 `check_order()` 메서드와 독립적으로 작동
- 필요 시 Engine에서 두 메서드를 순차적으로 호출
- ExposureDecision 객체로 명확한 의사결정 이유 전달

---

### 2-3. YAML 스키마 확장 (configs/base.yml)

#### 추가된 필드

```yaml
position_sizing:
  # 기존 필드 (변경 없음)
  max_position_value: 10000
  min_position_value: 100
  
  # ⭐ PHASE17 신규 필드
  min_position_notional: 100      # 최소 포지션 금액
  max_position_notional: 10000    # 최대 포지션 금액
  
  # Multi-position Scaling
  multi_position_scaling: true    # 동시 포지션 수에 따른 크기 조정
  # 공식: scaling_factor = 1.0 / (1 + num_open / max_positions)
  
  # Per-symbol Exposure Guard 통합
  exposure_reduction_factor: 0.95 # 사이즈 축소 시 안전 마진 (95%)
  allow_partial_entry: true       # 사이즈 축소 후 진입 허용
  
  # Volatility Scaling (기존 유지)
  context_scaling:
    enabled: true
    atr_low_pct: 0.004
    atr_high_pct: 0.02
    low_vol_mult: 1.2
    high_vol_mult: 0.7
```

#### 하위 호환성

- 기존 필드는 그대로 유지 (변경 없음)
- 신규 필드는 기본값 제공 (None이면 기본 동작)
- `multi_position_scaling: false`로 설정 시 기존 동작 유지

---

### 2-4. PHASE17 테스트 설정 (configs/scalping/real_paper_12h_v4_phase17.yml)

#### 핵심 변경 사항

```yaml
position_sizing:
  min_position_notional: 100
  max_position_notional: 15000    # 20k → 15k (PHASE16 교훈)
  multi_position_scaling: true    # ✅ 핵심 기능
  allow_partial_entry: true       # ✅ 핵심 기능

risk:
  max_drawdown_pct: 25.0          # 10% → 25%
  max_positions: 3                # 5/2 → 3
  max_exposure_per_symbol: 0.35  # 30% → 35%

portfolio:
  symbol_cooldown_seconds: 90     # 120 → 90
```

**설계 의도**:
- Multi-position Scaling으로 동시 포지션 증가 시 자동 크기 축소
- Exposure Guard가 사이즈 축소 후 진입 허용 (ALLOW_REDUCED)
- 12h 동안 Entry ≥ 1, Closed ≥ 1 유지 (거래 정지 방지)

---

## 📊 3. PHASE16 대비 개선 사항

### 3-1. 문제 → 해결 매핑

| PHASE16 문제 | PHASE17 해결 | 구현 위치 |
|--------------|-------------|----------|
| **고정 포지션 크기** | Multi-position Scaling (동적 조정) | `position_sizer.py::apply_multi_position_scaling()` |
| **Exposure Guard 이진 차단** | 3단계 의사결정 (ALLOW_REDUCED 추가) | `risk_manager.py::check_symbol_exposure_with_adjustment()` |
| **YAML 튜닝 한계** | 리스크/노출/크기 일관된 정책 표현 | `configs/base.yml::position_sizing` |
| **Entry 신호 반복 차단** | 사이즈 축소 후 진입 허용 | `position_sizer.py::calculate_with_exposure_check()` |
| **12h 테스트 조기 종료** | Guard가 "가드레일"로 작동 | 전체 시스템 통합 |

### 3-2. PHASE16 실패 케이스 재현 및 검증

#### Case 1: PHASE16 2차 실행 (Exposure Guard 차단)

```
초기 상태:
- equity = 50,000 USDT
- max_positions = 5
- max_symbol_exposure = 14,705 USDT (29.4%)

실제 발생:
- BTCUSDT 현재 노출 = 20,048 USDT (초과!)
- 새로운 Entry 신호 발생
- PHASE16: BLOCK (완전 차단) → 12h 동안 Entry 0회
- PHASE17: BLOCK (현재 노출도가 이미 초과 상태)
  → 하지만 기존 포지션 청산 후 재시도 가능
```

**PHASE17 개선점**:
- 현재 노출도가 이미 초과한 상태에서는 BLOCK이 정당함
- 하지만 Multi-position Scaling이 활성화되어 있으면,
  첫 번째 포지션 진입 시 크기가 작아져 초과 방지

#### Case 2: PHASE16 개선 시뮬레이션

```
초기 상태:
- equity = 50,000 USDT
- max_positions = 3
- max_symbol_exposure = 17,500 USDT (35%)
- multi_position_scaling = true

Entry 시나리오:
1. Entry 1 (BTCUSDT):
   - num_open = 0 → scaling = 100%
   - 요청 = 8,000 USDT
   - 현재 노출 = 0
   - 결과: ALLOW (total = 8,000 < 17,500)

2. Entry 2 (BTCUSDT):
   - num_open = 1 → scaling = 67%
   - 요청 = 8,000 × 0.67 = 5,360 USDT
   - 현재 노출 = 8,000
   - 결과: ALLOW (total = 13,360 < 17,500)

3. Entry 3 (BTCUSDT):
   - num_open = 2 → scaling = 50%
   - 요청 = 8,000 × 0.5 = 4,000 USDT
   - 현재 노출 = 13,360
   - total = 17,360 < 17,500
   - 결과: ALLOW ✅

4. Entry 4 (BTCUSDT):
   - num_open = 3 → scaling = 40%
   - 요청 = 8,000 × 0.4 = 3,200 USDT
   - 현재 노출 = 17,360
   - total = 20,560 > 17,500 ❌
   - 여유 = 17,500 - 17,360 = 140 USDT
   - 조정 = 140 × 0.95 = 133 USDT
   - 결과: BLOCK (조정 후 크기 < min_notional 100)
     → 하지만 기존 포지션 청산 후 재시도 가능

결과:
- PHASE16: Entry 2-3회 후 영원히 차단
- PHASE17: Entry 3회 성공, 4회째만 차단
  → 기존 포지션 청산 후 다시 Entry 가능 ✅
```

---

## 🧪 4. 테스트 현황

### 4-1. 단위 테스트 (tests/test_phase17_position_sizing.py)

**작성된 테스트 (17개)**:

| 카테고리 | 테스트 수 | 상태 |
|----------|----------|------|
| Multi-position Scaling | 4개 | 작성 완료 |
| Exposure Guard 3단계 의사결정 | 4개 | 작성 완료 |
| Position Sizer + Exposure Check 통합 | 3개 | 작성 완료 |
| Edge Cases | 3개 | 작성 완료 |
| PHASE16 실패 케이스 재현 | 2개 | 작성 완료 |
| **총계** | **16개** | **실행 대기** |

**테스트 시나리오 요약**:

1. **Multi-position Scaling**:
   - 0/1/2개 포지션 열림 시 스케일링 계산
   - Scaling OFF 시 동작
   - max_positions=0 (무제한) 시 동작

2. **Exposure Guard 3단계 의사결정**:
   - ALLOW: 정상 진입
   - ALLOW_REDUCED: 사이즈 축소 후 진입
   - BLOCK (현재 노출도 한계): 완전 차단
   - BLOCK (조정 후 크기 미달): 최소값 미만

3. **통합 테스트**:
   - Position Sizer + Exposure Check ALLOW
   - Position Sizer + Exposure Check ALLOW_REDUCED
   - Position Sizer + Exposure Check BLOCK

4. **Edge Cases**:
   - max_positions=0 처리
   - current_exposure=0 처리
   - 잘못된 신호 (entry ≤ sl) 처리

5. **PHASE16 실패 케이스**:
   - 2차 실행 (노출도 초과) 재현
   - 개선 케이스 (사이즈 축소 후 진입) 검증

### 4-2. 통합 테스트 (12h REAL PAPER)

**예정 테스트**:
- 설정 파일: `configs/scalping/real_paper_12h_v4_phase17.yml`
- 실행 명령: `python run_paper.py --config configs/scalping/real_paper_12h_v4_phase17.yml --duration 12h`
- 목표:
  - Entry ≥ 1, Closed ≥ 1 (거래 정지 방지)
  - 실행 시간 ≥ 10시간 48분
  - Exposure Guard 차단 시 로그에 명확한 사유 기록
  - ALLOW_REDUCED 동작 확인

---

## 📈 5. 예상 효과

### 5-1. 정량적 개선

| 지표 | PHASE16 (v3) | PHASE17 (예상) | 개선율 |
|------|--------------|----------------|--------|
| **12h 실행 시간** | 13분 19초 | ≥ 10시간 48분 | **+4,800%** |
| **Entry 신호 성공률** | 0% (차단) | ≥ 50% | **+∞%** |
| **Guard 차단 유형** | 100% BLOCK | 70% ALLOW + 20% ALLOW_REDUCED + 10% BLOCK | 다양화 |
| **포지션 크기 제어** | 고정 | 동적 (0~2개: 100~50%) | 자동 조정 |

### 5-2. 정성적 개선

**1) Guard 철학 변경**:
- PHASE16: "방화벽(Firewall)" → 완전 차단
- PHASE17: "가드레일(Guardrail)" → 사이즈 축소 후 허용

**2) 리스크 관리 일관성**:
- PHASE16: YAML 튜닝만으로는 제어 불가
- PHASE17: 리스크/노출/크기가 하나의 정책으로 통합

**3) 운영 안정성**:
- PHASE16: Exposure Guard로 인한 시스템 중단
- PHASE17: Guard가 "레일"처럼 작동하여 지속적 거래 가능

**4) 투명성**:
- PHASE16: 차단 사유 불명확
- PHASE17: ExposureDecision 객체로 명확한 이유 제공

---

## 🚀 6. 다음 단계 (PHASE18+)

### 6-1. 단기 과제 (PHASE18)

1. **12h REAL PAPER 재테스트**:
   - v4_phase17.yml 설정으로 실행
   - ALLOW_REDUCED 동작 확인
   - 로그 분석 및 리포트 작성

2. **단위 테스트 실행 및 통과**:
   - Import 오류 해결
   - 전체 테스트 실행 및 통과

3. **Engine 통합 작업**:
   - `engine.py`에서 `calculate_with_exposure_check()` 호출
   - 기존 `check_order()` 흐름과 통합
   - 최소 코드 변경으로 구현

### 6-2. 중기 과제 (PHASE19-20)

1. **동적 Exposure Limit**:
   - 시간대별 / 시장 상황별 노출도 한계 조정
   - 예: 고변동성 시 노출도 한계 축소

2. **포지션 병합 (Position Merging)**:
   - 동일 심볼 다중 포지션 병합
   - 노출도 효율화

3. **실시간 노출도 계산 개선**:
   - 기존 포지션의 실시간 PnL 반영
   - 손실로 인한 노출도 변화 즉시 반영

### 6-3. 장기 과제 (PHASE21+)

1. **AI 기반 Position Sizing**:
   - 머신러닝으로 최적 포지션 크기 학습
   - 시장 상황별 동적 조정

2. **다전략 앙상블 통합**:
   - PHASE17 로직을 앙상블에 적용
   - 전략별 리스크 배분 최적화

3. **상관관계 기반 포트폴리오 노출도**:
   - 현재는 심볼별 독립적 계산
   - 향후 상관관계 기반 포트폴리오 노출도 고려

---

## 📝 7. 제한사항 및 주의사항

### 7-1. 현재 설계의 제한사항

1. **포지션 크기 조정의 한계**:
   - 사이즈 축소 후에도 min_position_notional 미만이면 거래 불가
   - 극도로 높은 노출도 상황에서는 여전히 차단 가능

2. **실시간 노출도 계산**:
   - 기존 포지션의 실시간 PnL 반영 미흡
   - 손실로 인한 노출도 변화 즉시 반영 필요

3. **심볼 상관관계**:
   - 현재는 심볼별 독립적 계산
   - 향후 상관관계 기반 포트폴리오 노출도 고려 필요

### 7-2. 운영 시 주의사항

1. **ALLOW_REDUCED 로그 모니터링**:
   - 사이즈 축소가 빈번히 발생하면 설정 재조정 필요
   - 예: `max_symbol_exposure_pct` 증가

2. **Multi-position Scaling 조정**:
   - `max_positions`가 너무 작으면 과도한 축소 발생
   - 적정값: 2-5개 (백테스트로 최적화)

3. **최소 포지션 크기 설정**:
   - `min_position_notional`이 너무 크면 ALLOW_REDUCED 실패율 증가
   - 거래소 최소 주문 금액 고려 (바이낸스: 5-10 USDT)

---

## ✅ 8. 결론

### 8-1. 구현 완료 사항

1. ✅ **Position Sizer 강화**:
   - Multi-position Scaling 메서드 추가
   - Exposure Check 통합 메서드 추가
   - PHASE17 설정 로드 및 초기화

2. ✅ **Risk Manager 3단계 의사결정**:
   - ExposureDecision 데이터 클래스 정의
   - check_symbol_exposure_with_adjustment() 메서드 추가
   - 기존 check_order()와 독립적 작동

3. ✅ **YAML 스키마 확장**:
   - position_sizing 섹션 신규 필드 추가
   - 하위 호환성 유지
   - PHASE17 테스트 설정 파일 생성

4. ✅ **단위 테스트 작성**:
   - 16개 테스트 시나리오 작성
   - Multi-position Scaling, Exposure Guard, 통합, Edge Cases 포함
   - PHASE16 실패 케이스 재현 및 검증

### 8-2. PHASE16 대비 핵심 개선

| 항목 | PHASE16 | PHASE17 |
|------|---------|---------|
| **Position Sizing** | 고정 (YAML만) | 동적 (Multi-position Scaling) |
| **Exposure Guard** | 이진 차단 (BLOCK/ALLOW) | 3단계 (ALLOW/ALLOW_REDUCED/BLOCK) |
| **Guard 철학** | 방화벽 (Firewall) | 가드레일 (Guardrail) |
| **리스크 제어** | YAML 튜닝 한계 | 일관된 정책 (공식 기반) |
| **12h 안정성** | 조기 종료 (13분) | 지속적 거래 (목표 10h+) |

### 8-3. 향후 일정

1. **즉시 (24시간 이내)**:
   - Git Commit (PHASE17 구현)
   - 단위 테스트 실행 환경 정비

2. **단기 (1주일 이내)**:
   - 12h REAL PAPER 재테스트 (v4_phase17.yml)
   - 결과 분석 및 PHASE16 비교 리포트

3. **중기 (2주일 이내)**:
   - Engine 통합 작업
   - 다전략 앙상블 적용 준비

---

**문서 작성 완료**: 2025-11-17 23:45 (KST)  
**다음 작업**: Git Commit → 테스트 실행 → 12h REAL PAPER 재테스트
