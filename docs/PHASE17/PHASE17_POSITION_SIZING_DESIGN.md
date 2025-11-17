# PHASE17: Position Sizing + Exposure Guard 리팩토링 설계

**작성일**: 2025-11-17  
**목표**: PHASE16 REAL PAPER 12h 실패 원인(Exposure Guard 반복 차단)을 구조적으로 해결  
**범위**: Position Sizing 로직 강화 + Per-symbol Exposure Guard 통합 + YAML 스키마 확장

---

## 📌 1. 현재 상태 분석 (PHASE16 REAL PAPER 12h 결과)

### 1-1. 3회 시도 결과 요약

| 실행 | 시간 | 원인 | 설정 | 문제점 |
|------|------|------|------|--------|
| **1차** | 2분 59초 | Drawdown Guard (17.55% > 10%) | real_paper_1h.yml | Guard 임계값 너무 엄격 |
| **2차** | 11분 24초 | Exposure Guard (Entry 차단) | real_paper_12h.yml (max_pos: 5) | 포지션 크기 제어 불가 |
| **3차** | 13분 19초 (진행 중) | Exposure Guard (Entry 차단) | real_paper_12h_v3.yml (max_pos: 2) | 기존 포지션이 이미 제한값 초과 |

### 1-2. 핵심 문제 (PHASE16 결론)

**Per-symbol Exposure Guard 반복 차단**:
- 2차 실행: BTCUSDT 노출 20,048 USDT > 제한값 14,705 USDT (+36.3%)
- 3차 실행: BTCUSDT 노출 20,048 USDT > 제한값 14,928 USDT (+34.3%)
- **원인**: `max_positions` 제한만으로는 포지션 크기 제어 불가능
- **결과**: Entry 신호가 차단되어 12h 테스트 의미 상실

### 1-3. 근본 원인 분석

```
YAML 설정 튜닝의 한계:
┌─────────────────────────────────────────────────────┐
│ 1. max_positions: 2/5 (포지션 수량 제한)            │
│    → 각 포지션의 크기는 제어하지 않음                │
│                                                     │
│ 2. symbol_cooldown_seconds: 60/120 (쿨다운)        │
│    → 새로운 Entry 신호를 지연시킬 뿐,               │
│       기존 포지션의 노출도는 줄이지 않음             │
│                                                     │
│ 3. max_drawdown_pct: 25.0/30.0 (DD Guard)         │
│    → 포지션 크기와 무관하게 손실 기준으로만 작동    │
│                                                     │
│ 결론: 포지션 크기 자체를 동적으로 조정할 수 없음    │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 2. PHASE17 목표 및 설계 원칙

### 2-1. 목표

1. **동적 Position Sizing**
   - Per-trade 리스크 기반 (balance 대비 %, USDT 고정)
   - 동시 포지션 수에 따른 자동 크기 조정
   - 변동성/ATR 기반 리스크 스케일링

2. **Per-symbol Exposure Guard 통합**
   - "완전 차단" → "사이즈 축소 후 진입" 로직으로 전환
   - 허용 노출도 범위 내에서 최대한 거래 가능하도록 설계
   - Guard가 "레일(가드레일)"처럼 작동

3. **12h REAL PAPER 안정성**
   - Entry ≥ 1, Closed ≥ 1 (거래 정지 방지)
   - Guard로 인한 시스템 중단 없음
   - 실행 시간 ≥ 10시간 48분

### 2-2. 설계 원칙

- **하위 호환성**: 기존 PHASE16 설정과 호환 유지
- **점진적 강화**: YAML 설정 → 코드 로직 순서로 개선
- **투명성**: Guard 차단 이유를 명확히 로그/테스트에 기록
- **안전성**: 포지션 크기 제어 메커니즘 다층화

---

## 🧱 3. 설계 상세 (공식 + 로직)

### 3-1. 동적 Position Sizing 공식

#### Step 1: 기본 포지션 크기 (Risk-per-trade 기반)

```
Base Position Size (USDT):
  risk_usdt = equity × risk_per_trade_pct
  
  예시:
  - equity = 50,000 USDT
  - risk_per_trade_pct = 0.3% (0.003)
  - risk_usdt = 50,000 × 0.003 = 150 USDT
```

#### Step 2: 동시 포지션 수에 따른 크기 조정

```
Adjusted Position Size (Multi-position Scaling):
  
  num_open_positions = 현재 열린 포지션 수
  max_positions = 설정값 (예: 2)
  
  scaling_factor = 1.0 / (1 + num_open_positions / max_positions)
  
  예시:
  - max_positions = 2
  - 0개 열림: scaling = 1.0 / (1 + 0/2) = 1.0 (100%)
  - 1개 열림: scaling = 1.0 / (1 + 1/2) = 0.667 (67%)
  - 2개 열림: scaling = 1.0 / (1 + 2/2) = 0.5 (50%)
  
  adjusted_risk_usdt = risk_usdt × scaling_factor
```

#### Step 3: Per-symbol Exposure 계산 및 제약

```
Per-symbol Exposure (현재 + 신규):
  
  current_exposure = Σ(open_position_size × price) for symbol
  new_exposure = adjusted_risk_usdt / SL_distance × entry_price
  total_exposure = current_exposure + new_exposure
  
  max_symbol_exposure = equity × max_symbol_exposure_pct
  
  예시:
  - equity = 50,000
  - max_symbol_exposure_pct = 0.3 (30%)
  - max_symbol_exposure = 15,000 USDT
  - current_exposure = 10,000 (BTCUSDT)
  - new_exposure_requested = 8,000
  - total_exposure = 18,000 > 15,000 ❌ EXCEED
```

#### Step 4: Exposure Guard 통합 (사이즈 축소)

```
IF total_exposure > max_symbol_exposure:
  
  # 옵션 1: 사이즈 축소 (권장)
  available_exposure = max_symbol_exposure - current_exposure
  if available_exposure > 0:
    new_exposure_adjusted = available_exposure × 0.95  # 5% 안전 마진
    adjusted_qty = new_exposure_adjusted / entry_price
    
    IF adjusted_qty >= min_position_notional:
      PROCEED with reduced size
    ELSE:
      BLOCK (너무 작아서 거래 불가)
  ELSE:
    # 옵션 2: 완전 차단 (현재 노출도가 이미 한계)
    BLOCK with reason "Per-symbol exposure limit exceeded"
```

#### Step 5: 최종 포지션 크기 제약

```
Final Position Size:
  
  final_qty = adjusted_qty
  
  # 안전 장치
  IF final_qty * entry_price < min_position_notional:
    REJECT
  
  IF final_qty * entry_price > max_position_notional:
    final_qty = max_position_notional / entry_price
  
  RETURN final_qty
```

### 3-2. Per-symbol Exposure Guard 로직 (새로운 구조)

#### 현재 (PHASE16) 구조

```python
# 현재: 이진 차단 (Block or Pass)
if per_symbol_exposure > limit:
    BLOCK_ENTRY()  # 새로운 Entry 신호 차단
else:
    ALLOW_ENTRY()
```

#### 새로운 (PHASE17) 구조

```python
# 새로운: 3단계 의사결정
def check_exposure_and_adjust_size(symbol, new_exposure_requested):
    current_exposure = get_current_exposure(symbol)
    max_exposure = config.risk.max_symbol_exposure_usdt
    
    total_exposure = current_exposure + new_exposure_requested
    
    if total_exposure <= max_exposure:
        # ✅ 정상 진입
        return ALLOW, new_exposure_requested
    
    elif current_exposure < max_exposure:
        # ⚠️ 부분 진입 (사이즈 축소)
        available = max_exposure - current_exposure
        adjusted_exposure = available × 0.95  # 5% 안전 마진
        
        if adjusted_exposure >= min_position_notional:
            return ALLOW_REDUCED, adjusted_exposure
        else:
            return BLOCK, "Adjusted size too small"
    
    else:
        # ❌ 완전 차단
        return BLOCK, "Per-symbol exposure already at limit"
```

### 3-3. YAML 스키마 확장

#### 기존 (PHASE16)

```yaml
risk:
  max_positions: 2
  max_drawdown_pct: 25.0
  per_trade: 0.003
  max_exposure_pct: 0.95
  max_exposure_per_symbol: 0.3

portfolio:
  symbol_cooldown_seconds: 120
```

#### 새로운 (PHASE17)

```yaml
risk:
  # 기존 필드 (하위 호환)
  max_positions: 2
  max_drawdown_pct: 25.0
  per_trade: 0.003
  max_exposure_pct: 0.95
  max_exposure_per_symbol: 0.3
  
  # ⭐ 신규 필드 (Position Sizing)
  position_sizing:
    # 포지션 크기 범위 (USDT)
    min_position_notional: 100      # 최소 포지션 가치
    max_position_notional: 10000    # 최대 포지션 가치
    
    # 동시 포지션 수에 따른 크기 조정
    multi_position_scaling: true    # 활성화 여부
    scaling_formula: "1.0 / (1 + num_open / max_positions)"
    
    # Per-symbol Exposure 제어
    max_symbol_exposure_usdt: null  # null이면 equity × max_exposure_per_symbol로 계산
    exposure_reduction_factor: 0.95 # 사이즈 축소 시 안전 마진 (95%)
    allow_partial_entry: true       # 사이즈 축소 후 진입 허용
    
    # 변동성 기반 리스크 스케일링
    volatility_scaling: true
    atr_low_pct: 0.004              # 저변동성 기준
    atr_high_pct: 0.02              # 고변동성 기준
    low_vol_mult: 1.2               # 저변동성 시 리스크 증가
    high_vol_mult: 0.7              # 고변동성 시 리스크 감소

portfolio:
  symbol_cooldown_seconds: 120
  # ⭐ 신규: Exposure Guard 쿨다운
  exposure_guard_cooldown_seconds: 30  # Guard 차단 후 재시도 대기
```

---

## 📊 4. 구현 범위 (모듈/파일)

### 4-1. 수정/생성할 파일

| 파일 | 상태 | 목적 |
|------|------|------|
| `execution/position_sizer.py` | ENHANCE | Position Sizing 로직 강화 (multi-position scaling, exposure adjustment) |
| `execution/risk_manager.py` | ENHANCE | Per-symbol Exposure Guard 통합 (3단계 의사결정) |
| `execution/portfolio_manager.py` | REVIEW | 포지션 추적 및 노출도 계산 로직 검증 |
| `configs/base.yml` | UPDATE | 신규 YAML 필드 추가 (하위 호환성 유지) |
| `configs/scalping/real_paper_12h_v4.yml` | NEW | PHASE17 설계 적용 설정 |
| `tests/test_phase17_position_sizing.py` | NEW | 단위 테스트 (시나리오별) |
| `docs/PHASE17/PHASE17_POSITION_SIZING_REPORT.md` | NEW | 구현 리포트 |

### 4-2. 핵심 변경 사항

#### A) `execution/position_sizer.py`

**추가 메서드**:
```python
def calculate_with_exposure_check(
    self, 
    signal: Dict,
    current_symbol_exposure: float,
    max_symbol_exposure: float
) -> Tuple[float, Dict, str]:
    """
    포지션 크기 계산 + Exposure Guard 통합
    
    Returns:
        (qty, metadata, action)
        - action: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
    """
```

**강화 메서드**:
```python
def apply_multi_position_scaling(
    self,
    base_qty: float,
    num_open_positions: int,
    max_positions: int
) -> float:
    """
    동시 포지션 수에 따른 크기 조정
    """
```

#### B) `execution/risk_manager.py`

**새로운 로직**:
```python
def check_symbol_exposure_with_adjustment(
    self,
    symbol: str,
    new_exposure_requested: float
) -> Tuple[str, float, str]:
    """
    Per-symbol Exposure 체크 + 사이즈 조정
    
    Returns:
        (action, adjusted_exposure, reason)
        - action: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
    """
```

#### C) `configs/base.yml`

**신규 섹션**:
```yaml
position_sizing:
  min_position_notional: 100
  max_position_notional: 10000
  multi_position_scaling: true
  # ... (위 스키마 참조)
```

---

## 🧪 5. 테스트 시나리오

### 5-1. 단위 테스트 (test_phase17_position_sizing.py)

#### Scenario 1: 기본 포지션 크기 계산

```python
def test_basic_position_sizing():
    """
    equity=50,000, risk_per_trade=0.3%, entry=95,000, sl=94,000
    → risk_usdt = 150, qty ≈ 0.0016 BTC
    """
```

#### Scenario 2: 다중 포지션 스케일링

```python
def test_multi_position_scaling():
    """
    max_positions=2
    - 0개 열림: scaling=1.0 (100%)
    - 1개 열림: scaling=0.667 (67%)
    - 2개 열림: scaling=0.5 (50%)
    """
```

#### Scenario 3: Per-symbol Exposure 체크 (사이즈 축소)

```python
def test_exposure_check_with_reduction():
    """
    current_exposure=10,000, max_symbol_exposure=15,000
    new_exposure_requested=8,000
    → total=18,000 > 15,000
    → adjusted_exposure = (15,000 - 10,000) × 0.95 = 4,750
    → ALLOW_REDUCED
    """
```

#### Scenario 4: Per-symbol Exposure 체크 (완전 차단)

```python
def test_exposure_check_block():
    """
    current_exposure=15,000, max_symbol_exposure=15,000
    new_exposure_requested=5,000
    → total=20,000 > 15,000
    → available=0
    → BLOCK
    """
```

#### Scenario 5: 변동성 기반 리스크 스케일링

```python
def test_volatility_scaling():
    """
    atr_pct=0.004 (저변동성) → mult=1.2 (리스크 증가)
    atr_pct=0.02 (고변동성) → mult=0.7 (리스크 감소)
    """
```

### 5-2. 통합 테스트 (시뮬레이션)

#### Test Case: 12h REAL PAPER 시뮬레이션

```
초기 상태:
- equity = 50,000 USDT
- max_positions = 2
- max_symbol_exposure_pct = 30% (15,000 USDT)
- risk_per_trade = 0.3%

Entry 시나리오:
1. Entry 1 (BTCUSDT): qty=0.15 BTC @ 95,000 → exposure=14,250 ✅
2. Entry 2 (BTCUSDT): qty=0.10 BTC @ 95,500 → total=23,000 > 15,000
   → Adjusted: qty=0.07 BTC @ 95,500 → exposure=6,685 ✅ (ALLOW_REDUCED)
3. Entry 3 (BTCUSDT): current=20,935 > 15,000 → BLOCK
4. Exit 1: exposure 감소 → Entry 3 재시도 가능

결과:
- Entry 신호 차단 없음 (사이즈 축소로 해결)
- 12h 동안 지속적인 거래 가능
```

---

## 📋 6. 구현 순서 (Windsurf 작업 흐름)

1. ✅ **PHASE16 자료 복원** (현재 완료)
2. ✅ **PHASE17 설계 문서 작성** (현재 완료)
3. **Position Sizing 강화** (다음)
   - `position_sizer.py`: multi-position scaling 추가
   - `position_sizer.py`: exposure adjustment 메서드 추가
4. **Risk Manager 통합**
   - `risk_manager.py`: 3단계 의사결정 로직 추가
5. **YAML 스키마 확장**
   - `configs/base.yml`: 신규 필드 추가
   - `configs/scalping/real_paper_12h_v4.yml`: 신규 설정 파일
6. **테스트 코드 작성**
   - `tests/test_phase17_position_sizing.py`: 단위 테스트
7. **PHASE17 리포트 작성**
   - `docs/PHASE17/PHASE17_POSITION_SIZING_REPORT.md`
8. **Git Commit**

---

## 🔗 7. PHASE16과의 연계

### 7-1. 문제 → 해결 흐름

```
PHASE16 문제:
┌─────────────────────────────────────────┐
│ 1차: Drawdown Guard (17.55% > 10%)     │
│ 2차: Exposure Guard (20,048 > 14,705)  │
│ 3차: Exposure Guard (Entry 차단)       │
└─────────────────────────────────────────┘
                    ↓
PHASE17 해결:
┌─────────────────────────────────────────┐
│ 1. 동적 Position Sizing                 │
│    → 포지션 크기 자동 조정              │
│                                         │
│ 2. Per-symbol Exposure 통합             │
│    → 사이즈 축소 후 진입 (차단 아님)    │
│                                         │
│ 3. Multi-position Scaling               │
│    → 동시 포지션 수에 따른 조정         │
│                                         │
│ 결과: 12h 동안 Entry 신호 차단 없음    │
└─────────────────────────────────────────┘
```

### 7-2. PHASE16 리포트 업데이트 예정

```markdown
## PHASE17 개선 사항

PHASE16에서 발견된 Exposure Guard 반복 차단 문제를 다음과 같이 해결:

1. **Position Sizing 강화**
   - Multi-position scaling: 동시 포지션 수에 따른 자동 크기 조정
   - Volatility scaling: ATR 기반 동적 리스크 조정

2. **Per-symbol Exposure Guard 통합**
   - 3단계 의사결정: ALLOW → ALLOW_REDUCED → BLOCK
   - 사이즈 축소 후 진입으로 거래 정지 방지

3. **YAML 스키마 확장**
   - position_sizing 섹션 추가
   - 하위 호환성 유지

4. **테스트 검증**
   - 단위 테스트: 5개 시나리오
   - 통합 테스트: 12h 시뮬레이션
```

---

## 📝 8. 제한사항 및 향후 개선

### 8-1. 현재 설계의 제한사항

1. **포지션 크기 조정의 한계**
   - 사이즈 축소 후에도 min_position_notional 미만이면 거래 불가
   - 극도로 높은 노출도 상황에서는 여전히 차단 가능

2. **실시간 노출도 계산**
   - 기존 포지션의 실시간 PnL 반영 미흡
   - 손실로 인한 노출도 변화 즉시 반영 필요

3. **심볼 상관관계**
   - 현재는 심볼별 독립적 계산
   - 향후 상관관계 기반 포트폴리오 노출도 고려 필요

### 8-2. PHASE18+ 개선 방향

1. **동적 Exposure Limit**
   - 시간대별 / 시장 상황별 노출도 한계 조정
   - 예: 고변동성 시 노출도 한계 축소

2. **포지션 병합 (Position Merging)**
   - 동일 심볼 다중 포지션 병합
   - 노출도 효율화

3. **AI 기반 Position Sizing**
   - 머신러닝으로 최적 포지션 크기 학습
   - 시장 상황별 동적 조정

---

**문서 작성 완료**: 2025-11-17 22:35 (KST)
