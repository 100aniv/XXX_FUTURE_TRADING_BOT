# PHASE17 TASK 0: 컨텍스트 & 비전 문서 요약

**작성일**: 2025-01-XX  
**목적**: V4/V5/V5b Portfolio Budget 문제 해결을 위한 컨텍스트 정리

---

## 📌 1. PHASE17 핵심 역할 및 철학

### 1-1. PHASE17의 역할
- **Position Sizing 동적화**: Multi-position Scaling (동시 포지션 수에 따른 크기 자동 조정)
- **Exposure Guard 유연화**: 3단계 의사결정 (ALLOW / ALLOW_REDUCED / BLOCK)
- **Guard 철학 전환**: "방화벽 (Firewall)" → "가드레일 (Guardrail)"

### 1-2. TO-BE 방향 (PROJECT_VISION_TOBE.md 기준)
```
✅ DO-NOT-TOUCH Core Engine Layer
   → Backtest/Paper/Live 모두 동일 엔진 사용
   → 엔진의 기본 시그니처/입출력/이벤트 흐름은 모드 공통

✅ Config-based 설계
   → 모든 파라미터는 YAML로 제어
   → 전략/리스크/포트폴리오 설정은 config 기반

✅ Risk & Guard 우선
   → 모든 주문은 FlowGuardian 최종 승인 필요
   → Guard는 "가드레일"로 작동 (완전 차단이 아닌 조정)

✅ DRY, SRP, 최소 변경
   → 모듈 간 책임 일관성 유지
   → 하나의 기능은 하나의 모듈에서만 구현
```

### 1-3. 4대 레이어 구조
```
1. Core Engine Layer (DO-NOT-TOUCH)
   - 단일 메인 루프: 시세 → 전략 → 시그널 → Risk → Portfolio → 주문

2. Strategy & Ensemble Layer
   - 각 전략은 "시그널 생성기" 역할만
   - 포지션 크기, 리스크, 노출은 Risk/Portfolio Layer가 관리

3. Risk & Portfolio Layer
   - PositionSizer: "얼마나 살 것인가" (size 계산)
   - RiskManager: per-trade/per-symbol/per-day 리스크 관리
   - PortfolioManager: PnL, Equity, Max DD, Exposure의 단일 소스
   - FlowGuardian: Drawdown, Exposure, Slippage, Flash, Cooldown Guard

4. Infra & UX Layer
   - 데이터 수집 / Redis / Postgres
   - CLI, Runbook, 모니터링, 로그, 리포트
```

---

## 📊 2. PHASE17 V4/V5/V5b 실행 결과 요약

### 2-1. V4 실행 결과
| 항목 | 결과 | 판정 |
|------|------|------|
| **실행 시간** | 6분 30초 / 12시간 (5.4%) | ❌ FAIL |
| **Entry 성공** | 37개 | ✅ PASS |
| **ALLOW_REDUCED** | 29개 (78.4%) | ✅ **PASS** |
| **조기 종료 원인** | Volume Guard 과도 작동 | ❌ |

**핵심 문제**: Volume Guard (`vol_spike_mult: 2.5`)가 정상 거래량 변동을 "급증"으로 오인하여 00:55 이후 Entry 완전 중단

### 2-2. V5 실행 결과 (Volume Guard 비활성화)
| 항목 | 결과 | 판정 |
|------|------|------|
| **실행 시간** | ~10분 / 12시간 (1.4%) | ❌ FAIL |
| **Entry 성공** | 38개 | ✅ PASS |
| **Volume Guard 차단** | 0회 | ✅ 해결 |
| **조기 종료 원인** | **Portfolio Budget 초과** | 🔴 **NEW** |

**핵심 문제**: Portfolio Budget ($12,488) 초과로 01:33:20 이후 Entry 완전 차단
```
[ENTRY BLOCK] reason=portfolio_check_failed 
detail="전략 예산 초과: scalping $14,738.06 > $12,488.84"
```

### 2-3. V5b 실행 결과 (max_strategy_positions 증가)
| 항목 | 결과 | 판정 |
|------|------|------|
| **max_strategy_positions** | 5 → 10 (2배) | Config 변경 |
| **실행 시간** | ~2분 / 12시간 | ❌ FAIL |
| **Portfolio Budget** | ~$12,455 (동일!) | 🔴 **미해결** |

**결론**: `max_strategy_positions`는 Budget 계산에 영향 없음!

---

## 🚨 3. Portfolio Budget 문제 근본 원인

### 3-1. Budget 계산 로직 (PortfolioManager)
```python
# portfolio_manager.py::calculate_strategy_budget()
def calculate_strategy_budget(self, strategy_id: str) -> float:
    equity = self.equity  # $50,000
    
    # 전략별 예산 할당
    if strategy_id in self.strategy_budget:
        budget_pct = self.strategy_budget[strategy_id]
    else:
        budget_pct = self.default_budget_pct  # 0.2 (20%)
    
    # 전략별 예산 = 자산 * 할당 비율
    budget = equity * budget_pct  # $50,000 * 0.25 = $12,500
    return budget
```

**Config 기준** (`base.yml`):
```yaml
portfolio:
  budget:
    default_allocation: 0.2    # 20%
    strategy_allocation:
      scalping: 0.25           # 25% ← 'scalping' 전략
```

**실제 Budget**: $50,000 * 0.25 = **$12,500** ✅

### 3-2. Position Size 계산 로직 (PositionSizer)
```python
# position_sizer.py::calculate()
def calculate(self, signal: Dict) -> Tuple[float, Dict]:
    # 1. 리스크 기반 계산
    base_qty, risk_usdt = position_size(
        entry=entry,
        sl=sl,
        equity=self.equity,      # $50,000
        risk_frac=eff_rpt        # 0.003 (0.3%)
    )
    
    # 2. 품질 가중치 적용
    adjusted_qty = base_qty * quality_weight
    
    # 3. 포지션 가치 한도 적용
    position_value = adjusted_qty * entry
    if position_value > self.max_position_value:  # $15,000 (V5 config)
        adjusted_qty = self.max_position_value / entry
    
    return final_qty, metadata
```

**문제점**: Position Sizer는 **Strategy Budget을 전혀 고려하지 않음**!
- `max_position_notional: 15000` (V5 config)
- `per_trade: 0.003` (0.3% risk)
- 결과: 개별 포지션 크기 $10,000-$15,000

### 3-3. Budget 검증 로직 (PortfolioManager)
```python
# portfolio_manager.py::can_open_position()
def can_open_position(self, symbol, strategy, position_value, side):
    # ...
    # 6. 전략별 예산 한도 검사
    strategy_budget = self.calculate_strategy_budget(strategy)  # $12,500
    strategy_exposure = 0.0
    
    # 동일 전략의 기존 포지션 가치 합계
    for pos_list in self.positions.values():
        for pos in pos_list:
            if pos['strategy'] == strategy and pos['status'] == 'OPEN':
                strategy_exposure += pos.get('position_value', 0.0)  # 기존: $10,000+
    
    # 새 포지션 추가 후 전략 노출 예산
    new_strategy_exposure = strategy_exposure + position_value  # $10,000 + $14,700 = $24,700
    if new_strategy_exposure > strategy_budget:  # $24,700 > $12,500 ❌
        return False, f"전략 예산 초과: {strategy} ${new_strategy_exposure:,.2f} > ${strategy_budget:,.2f}"
```

**흐름**:
1. Position Sizer: $14,700 포지션 계산 (Budget 무시)
2. Portfolio Manager: "기존 $10,000 + 신규 $14,700 = $24,700 > $12,500" → BLOCK

---

## 🎯 4. 문제의 핵심 (Single Source of Truth 부재)

### 4-1. 문제 정의
```
❌ Position Sizer와 Portfolio Manager 사이에 Budget 정보 전달 없음
❌ Position Sizer는 "개별 포지션 최대값"만 고려 (max_position_notional)
❌ Portfolio Manager는 "전략 전체 예산"만 검증 (strategy_budget)
❌ 두 로직이 독립적으로 작동하여 충돌 발생
```

### 4-2. 책임 분리 불일치
| 모듈 | 현재 책임 | 문제점 |
|------|----------|--------|
| **PositionSizer** | - 개별 포지션 크기 계산<br>- max_position_notional 한도 적용 | ❌ Strategy Budget 미고려 |
| **PortfolioManager** | - Strategy Budget 계산<br>- Budget 초과 검증 | ❌ 사후 검증만 (사전 조정 없음) |
| **RiskManager** | - Per-trade 리스크 한도<br>- Exposure Guard | ✅ 정상 작동 |

### 4-3. TO-BE 설계 원칙 위반
```
PROJECT_VISION_TOBE.md 원칙:
✅ "PortfolioManager: PnL, Equity, Max DD, Exposure의 단일 소스"
   → Budget도 PortfolioManager가 유일한 진실 소스여야 함

❌ 현재: Position Sizer가 Budget 없이 독립적으로 크기 결정
   → 진실 소스(Portfolio Budget)를 무시하는 구조

✅ DRY, SRP 원칙
   → Budget 계산은 PortfolioManager만
   → Position Sizer는 Budget을 받아서 사용만 해야 함
```

---

## 💡 5. 해결 방향

### 5-1. 설계 원칙
```
1. PortfolioManager = Budget의 단일 진실 소스 (SSOT)
   → calculate_strategy_budget()만 Budget 계산

2. PositionSizer = Budget 소비자
   → Budget을 입력받아 포지션 크기 제한

3. Budget은 "사전 제약"으로 작동
   → 사후 검증(can_open_position)이 아닌 사전 조정(calculate)
```

### 5-2. 구현 방향
```python
# Option A (권장): PositionSizer에 available_budget 전달
qty, meta = sizer.calculate(
    signal=signal,
    available_budget=available_budget  # 추가!
)

# Option B: PositionSizer가 PortfolioManager 참조
class PositionSizer:
    def __init__(self, config, portfolio_manager):
        self.portfolio = portfolio_manager
    
    def calculate(self, signal, strategy):
        budget = self.portfolio.get_available_budget(strategy)
        # ...
```

### 5-3. 기대 효과
```
✅ Position Sizer가 Budget 내에서만 크기 결정
✅ Portfolio Manager의 can_open_position()은 검증만 수행 (조정 불필요)
✅ Budget 초과로 인한 BLOCK 발생률 90% 감소
✅ 12시간 실행 안정성 확보
```

---

## 📝 6. 다음 단계 (TASK 1)

### TASK 1. Portfolio Budget & Position Sizing 코드 정밀 분석
- `execution/portfolio_manager.py`: Budget 계산 로직 전체 분석
- `execution/risk_manager.py`: Exposure Guard 검증 로직 분석
- `execution/position_sizer.py`: 포지션 크기 계산 로직 전체 분석
- `execution/engine.py`: Position Sizer 호출 방식 확인
- **결과물**: `PHASE17_PORTFOLIO_BUDGET_ANALYSIS.md`

### TASK 2. 설계 재정의
- Budget / Sizer / Exposure의 단일 진실 소스 정립
- Position Sizer에 Budget 전달 방식 설계
- **결과물**: `PHASE17_PORTFOLIO_BUDGET_REDESIGN.md`

### TASK 3-6. 구현 → 테스트 → V6 실행 → 리포트
- 코드 리팩토링 (Position Sizer + Portfolio Manager 통합)
- V6 Config 생성 및 단위 테스트
- REAL PAPER 12H V6 실행 (FULL AUTO)
- 최종 리포트

---

**작성 완료**: 2025-01-XX  
**다음 작업**: TASK 1 - Portfolio Budget 코드 정밀 분석
