# PHASE17: Portfolio Budget & Position Sizing 재설계

**작성일**: 2025-01-XX  
**목적**: Budget/Sizer/Exposure의 단일 진실 소스(SSOT) 정립 및 구현 설계

---

## 📌 Executive Summary

### 설계 철학
```
1. PortfolioManager = Budget의 단일 진실 소스 (SSOT)
2. PositionSizer = Budget 소비자 (Budget 내에서만 크기 결정)
3. Budget은 "사전 제약"으로 작동 (사후 검증 X, 사전 조정 O)
```

### 구현 방식
```python
# 1. PortfolioManager: 남은 예산 계산
available_budget = portfolio.get_available_budget(strategy)

# 2. Engine: Position Sizer에 budget 전달
qty, meta = sizer.calculate(signal, available_budget=available_budget)

# 3. PositionSizer: Budget 내에서 크기 제한
position_value = min(calculated_value, available_budget)
```

---

## 🎯 1. 설계 목표

### 1-1. 문제 정의
```
현재: Position Sizer가 Budget 무시 → Portfolio Manager가 사후 차단
목표: Position Sizer가 Budget 준수 → Portfolio Manager는 검증만
```

### 1-2. 성공 기준
```
✅ Position Sizer가 available_budget 파라미터 받음
✅ Budget 내에서만 포지션 크기 결정
✅ Portfolio Budget 초과 BLOCK 발생률 90% 감소
✅ 12H 실행 시 Entry 지속 (조기 종료 X)
```

---

## 🏗️ 2. 아키텍처 설계

### 2-1. 책임 분리 (Redesign)

| 모듈 | 기존 책임 | 신규 책임 | 변경 |
|------|----------|----------|------|
| **PortfolioManager** | - Budget 계산<br>- 사후 검증 | - Budget 계산 (SSOT)<br>- **남은 예산 제공**<br>- 최종 검증 | + get_available_budget() |
| **PositionSizer** | - 크기 계산<br>- max_notional 한도 | - **Budget 내 크기 계산**<br>- max_notional 한도 | + available_budget param |
| **Engine** | - 흐름 제어 | - **Budget 정보 전달**<br>- 흐름 제어 | + budget 조회 및 전달 |

### 2-2. 데이터 흐름 (TO-BE)
```
[PortfolioManager]
    ├─ calculate_strategy_budget() → $12,500 (총 예산)
    ├─ _get_used_budget() → $10,000 (사용 중)
    └─ get_available_budget() → $2,500 (남은 예산) ⭐ 신규

            ↓ (Engine이 조회)

[Engine]
    ├─ available_budget = portfolio.get_available_budget(strategy)
    └─ qty, meta = sizer.calculate(signal, available_budget)

            ↓ (Position Sizer가 소비)

[PositionSizer]
    ├─ calculated_value = qty * entry → $9,000
    ├─ capped_value = min($9,000, $2,500) → $2,500 ⭐ Budget 준수
    └─ final_qty = $2,500 / entry

            ↓ (Portfolio Manager가 최종 검증)

[PortfolioManager]
    └─ can_open_position() → ✅ PASS ($10,000 + $2,500 = $12,500 ≤ $12,500)
```

---

## 🔧 3. 구현 상세

### 3-1. PortfolioManager 수정

#### 신규 메서드: get_available_budget()
```python
def get_available_budget(self, strategy: str) -> float:
    """
    전략별 남은 예산 계산
    
    Args:
        strategy: 전략 ID (예: 'scalping')
        
    Returns:
        float: 사용 가능한 예산 (USDT)
    """
    total_budget = self.calculate_strategy_budget(strategy)  # $12,500
    used_budget = self._get_used_budget(strategy)  # $10,000
    available = max(0.0, total_budget - used_budget)  # $2,500
    
    logger.debug(
        f"💰 [Budget] {strategy}: total=${total_budget:,.0f} "
        f"used=${used_budget:,.0f} available=${available:,.0f}"
    )
    return available
```

#### 신규 내부 메서드: _get_used_budget()
```python
def _get_used_budget(self, strategy: str) -> float:
    """
    전략별 현재 사용 중인 예산 계산
    
    Args:
        strategy: 전략 ID
        
    Returns:
        float: 사용 중인 예산 (USDT)
    """
    used = 0.0
    for pos_list in self.positions.values():
        for pos in pos_list:
            if pos.get('strategy') == strategy and pos.get('status') == 'OPEN':
                used += pos.get('position_value', 0.0)
    return used
```

### 3-2. PositionSizer 수정

#### calculate() 메서드 시그니처 변경
```python
# 기존
def calculate(self, signal: Dict) -> Tuple[float, Dict]:
    ...

# 신규
def calculate(
    self, 
    signal: Dict, 
    available_budget: float = None  # ⭐ 추가!
) -> Tuple[float, Dict]:
    """
    포지션 크기 계산
    
    Args:
        signal: {'entry_price', 'sl_price', 'confidence', ...}
        available_budget: 사용 가능한 예산 (USDT). None이면 무제한.
    """
    entry = signal['entry_price']
    sl = signal['sl_price']
    
    # 1) 기존 계산 로직 (Risk-based)
    eff_rpt = self._get_effective_rpt(signal)
    base_qty, risk_usdt = position_size(entry, sl, self.equity, eff_rpt)
    
    # 2) 품질 가중치 적용
    quality_weight = self._calculate_quality_weight(signal)
    adjusted_qty = base_qty * quality_weight
    
    # 3) 포지션 가치 계산
    position_value = adjusted_qty * entry
    
    # 4) max_position_value 한도 적용
    if position_value > self.max_position_value:
        position_value = self.max_position_value
        adjusted_qty = position_value / entry
    
    # 5) ⭐ available_budget 한도 적용 (신규!)
    if available_budget is not None and position_value > available_budget:
        logger.info(
            f"📉 [Budget Cap] Position capped by available budget: "
            f"${position_value:.2f} → ${available_budget:.2f}"
        )
        position_value = available_budget
        adjusted_qty = position_value / entry
    
    # 6) min_position_value 체크
    if position_value < self.min_position_value:
        return 0.0, {"reason": "below_min_value"}
    
    # 7) 최종 수량 계산
    final_qty = float(round(adjusted_qty, 3))
    
    metadata = {
        "risk_usdt": float(risk_usdt),
        "quality_weight": float(quality_weight),
        "base_qty": float(base_qty),
        "final_qty": final_qty,
        "position_value": float(position_value),
        "available_budget": float(available_budget) if available_budget else None,
        "budget_capped": available_budget and position_value >= available_budget  # ⭐ 신규
    }
    
    return final_qty, metadata
```

### 3-3. Engine 수정

#### Position Sizer 호출 부분 (Line ~1156)
```python
# 기존
qty, meta = sizer.calculate({
    "entry_price": decision.get("entry"),
    "sl_price": decision.get("sl"),
    "confidence": decision.get("confidence", 0.8),
})

# 신규
# ⭐ 1. 남은 예산 조회
available_budget = portfolio.get_available_budget(strategy_id)

# ⭐ 2. Position Sizer에 budget 전달
qty, meta = sizer.calculate(
    {
        "entry_price": decision.get("entry"),
        "sl_price": decision.get("sl"),
        "confidence": decision.get("confidence", 0.8),
    },
    available_budget=available_budget  # ⭐ 추가!
)

# ⭐ 3. Budget Cap 로그
if meta.get('budget_capped'):
    logger.info(
        f"💰 [Budget Cap Applied] {candle_symbol} {decision.get('side')} "
        f"strategy={strategy_id} position_value=${meta['position_value']:.2f} "
        f"available_budget=${available_budget:.2f}"
    )
```

---

## 📊 4. 동작 시나리오 (V6 예상)

### 4-1. 시나리오: 첫 Entry (Budget 충분)
```
1. Portfolio Manager
   - total_budget: $12,500
   - used_budget: $0
   - available_budget: $12,500

2. Position Sizer (Entry 1)
   - Risk-based calculation: $9,000
   - max_position_value check: $9,000 < $15,000 → PASS
   - available_budget check: $9,000 < $12,500 → PASS
   → Final: $9,000

3. Exposure Guard
   - current_exposure: $0, requested: $9,000
   - max_symbol_exposure: $17,500
   → ALLOW

4. Portfolio Manager
   - new_strategy_exposure: $0 + $9,000 = $9,000
   - strategy_budget: $12,500
   → $9,000 < $12,500 ✅ PASS
```

### 4-2. 시나리오: 추가 Entry (Budget 부족)
```
1. Portfolio Manager
   - total_budget: $12,500
   - used_budget: $9,000
   - available_budget: $3,500

2. Position Sizer (Entry 2)
   - Risk-based calculation: $8,500
   - max_position_value check: $8,500 < $15,000 → PASS
   - available_budget check: $8,500 > $3,500 → CAP!
   → Final: $3,500 ⭐ Budget에 맞춰 조정

3. Exposure Guard
   - current_exposure: $9,000, requested: $3,500
   - total: $12,500 < $17,500
   → ALLOW

4. Portfolio Manager
   - new_strategy_exposure: $9,000 + $3,500 = $12,500
   - strategy_budget: $12,500
   → $12,500 ≤ $12,500 ✅ PASS (Budget 꽉 참)
```

### 4-3. 시나리오: 추가 Entry (Budget 소진)
```
1. Portfolio Manager
   - total_budget: $12,500
   - used_budget: $12,500
   - available_budget: $0

2. Position Sizer (Entry 3)
   - Risk-based calculation: $7,000
   - available_budget check: $7,000 > $0 → CAP to $0
   → Final: $0

3. ❌ qty=0 → Entry BLOCK (정상!)
   - Reason: "Budget fully allocated"
   - 로그: "📉 [Budget Cap] Available budget: $0"
```

---

## 🔄 5. 기존 코드와의 차이

### 5-1. 변경 영역 요약

| 파일 | 메서드/라인 | 변경 타입 | 변경 내용 |
|------|------------|----------|----------|
| `portfolio_manager.py` | 신규 메서드 | ADD | `get_available_budget()` |
| `portfolio_manager.py` | 신규 메서드 | ADD | `_get_used_budget()` |
| `position_sizer.py` | `calculate()` | MODIFY | + `available_budget` param<br>+ Budget Cap logic |
| `engine.py` | Line ~1150-1160 | MODIFY | + Budget 조회 및 전달 |

### 5-2. 호환성 유지
```python
# Position Sizer: available_budget는 Optional
def calculate(self, signal: Dict, available_budget: float = None):
    # available_budget=None → 기존 동작 유지 (무제한)
    # available_budget=값 → 신규 Budget Cap 적용
```

**기존 코드 호환**:
- Backtest 모드: `available_budget=None` → Budget 무제한 (기존 동작)
- Paper/Live 모드: `available_budget=값` → Budget Cap 적용 (신규)

---

## 📈 6. 기대 효과

### 6-1. 정량적 효과
| 지표 | V5/V5b (현재) | V6 (예상) | 개선 |
|------|--------------|-----------|------|
| **Portfolio Budget BLOCK** | 80%+ | <10% | 90% 감소 |
| **Entry 지속 시간** | ~10분 | 12시간+ | 목표 달성 |
| **총 Entry 수** | 38개 | 150-300개 | 4-8배 증가 |
| **Budget 활용률** | 50% (조기 중단) | 95%+ | 안정적 소진 |

### 6-2. 정성적 효과
```
✅ Position Sizer가 "현실적인" 크기 제안
   - Budget 범위 내에서만 계산
   - Exposure Guard / Portfolio Manager 통과율 상승

✅ Portfolio Manager는 "최종 검증"만 수행
   - 사후 차단이 아닌 사전 조정
   - 로직 단순화 (검증만)

✅ SSOT 원칙 준수
   - PortfolioManager = Budget의 유일한 진실 소스
   - Position Sizer = Budget 소비자
   - 책임 분리 명확

✅ 12H 실행 안정성 확보
   - Entry가 지속적으로 발생
   - Budget 소진 시 "budget fully allocated" 로그만
   - 시스템 비정상 종료 없음
```

---

## 🧪 7. 테스트 시나리오

### 7-1. 단위 테스트 (test_phase17_position_sizing.py)

#### Test 1: Budget 충분 (정상 계산)
```python
def test_budget_sufficient():
    sizer = PositionSizer(config)
    signal = {"entry_price": 100000, "sl_price": 98000}
    available_budget = 50000  # 충분
    
    qty, meta = sizer.calculate(signal, available_budget)
    
    # Risk-based 계산 결과 유지
    assert meta['position_value'] < available_budget
    assert meta['budget_capped'] is False
```

#### Test 2: Budget 부족 (Cap 적용)
```python
def test_budget_cap():
    sizer = PositionSizer(config)
    signal = {"entry_price": 100000, "sl_price": 98000}
    available_budget = 3000  # 부족
    
    qty, meta = sizer.calculate(signal, available_budget)
    
    # Budget에 맞춰 조정
    assert meta['position_value'] == available_budget
    assert meta['budget_capped'] is True
```

#### Test 3: Budget 소진 (qty=0)
```python
def test_budget_exhausted():
    sizer = PositionSizer(config)
    signal = {"entry_price": 100000, "sl_price": 98000}
    available_budget = 0  # 소진
    
    qty, meta = sizer.calculate(signal, available_budget)
    
    # qty=0 반환
    assert qty == 0.0
    assert meta['reason'] == 'below_min_value'
```

### 7-2. 통합 테스트 (test_phase17_simple.py)

#### Test 4: Portfolio 전체 흐름
```python
def test_portfolio_budget_integration():
    portfolio = PortfolioManager(config)
    sizer = PositionSizer(config)
    
    # 시나리오 1: 첫 Entry ($9k)
    available = portfolio.get_available_budget('scalping')  # $12.5k
    qty1, meta1 = sizer.calculate(signal, available)
    assert meta1['position_value'] == 9000
    
    # 포지션 등록
    portfolio.add_position('BTC', 'scalping', 9000, 'LONG')
    
    # 시나리오 2: 두 번째 Entry ($8.5k → $3.5k)
    available = portfolio.get_available_budget('scalping')  # $3.5k
    qty2, meta2 = sizer.calculate(signal, available)
    assert meta2['position_value'] == 3500
    assert meta2['budget_capped'] is True
    
    # 포지션 등록
    portfolio.add_position('ETH', 'scalping', 3500, 'SHORT')
    
    # 시나리오 3: 세 번째 Entry ($0)
    available = portfolio.get_available_budget('scalping')  # $0
    qty3, meta3 = sizer.calculate(signal, available)
    assert qty3 == 0.0
```

---

## 🚀 8. 배포 계획

### 8-1. 구현 순서
```
1. PortfolioManager 수정 (30분)
   - get_available_budget() 추가
   - _get_used_budget() 추가
   - 기존 can_open_position() 유지 (검증 로직)

2. PositionSizer 수정 (20분)
   - calculate() 시그니처 변경
   - available_budget Cap 로직 추가
   - metadata에 budget_capped 추가

3. Engine 수정 (15분)
   - Budget 조회 추가
   - Position Sizer 호출 시 budget 전달
   - Budget Cap 로그 추가

4. 단위 테스트 작성/수정 (30분)
   - test_phase17_position_sizing.py
   - test_phase17_simple.py

5. V6 Config 생성 (10분)
   - real_paper_12h_v6_phase17.yml
   - Budget 관련 파라미터 확정

6. 통합 테스트 실행 (5분)
   - pytest tests/test_phase17*.py

7. V6 REAL PAPER 12H 실행 (12시간+)
   - Full Auto Execution Mode
   - 실시간 모니터링
```

### 8-2. 롤백 계획
```
만약 V6 실행 중 치명적 오류 발생 시:
1. 프로세스 즉시 종료
2. Git revert (이번 변경 롤백)
3. V5 config로 재실행
4. 문제 분석 후 재설계
```

---

**다음 작업**: TASK 3 - 코드 리팩토링 & 구현
