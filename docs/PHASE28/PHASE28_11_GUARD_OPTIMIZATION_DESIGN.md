# PHASE28-11: Guard Optimization Design (V1)

**Date**: 2025-12-08  
**Phase**: PHASE28-11  
**Objective**: Guard/Filter 최적화를 통한 전환율 0.40% → 3~5% 개선  
**Status**: 🟦 DESIGN (In Progress)

---

## 📋 Executive Summary

### 목표
- **현재 전환율**: 0.40% (6,194 signals → 25 orders)
- **목표 전환율**: 3~5% (약 186~310 orders per 3-month)
- **전환율 개선 배수**: 7.5x ~ 12.5x 향상 필요

### 접근 방법
1. **Telemetry 기반 진단**: PHASE28-10에서 구축한 Guard Breakdown 데이터 활용
2. **4개 프로파일 실험**: BASELINE → 단계적 완화 → 혼합 완화
3. **리스크 밸런스**: 전환율 개선 vs 리스크 증가 트레이드오프 관리

---

## 🔍 Current State Analysis

### 1. PHASE28-10 Telemetry 결과 (3개월 백테스트)

**Period**: 2024-10-01 ~ 2024-12-31 (Q4 3개월, 92일)  
**Strategy**: btc5m_baseline_v2  
**Symbol**: BTCUSDT (5m)

| Metric | Value | Description |
|--------|-------|-------------|
| **Signal True** | 6,194 | 전략이 생성한 유효 신호 수 |
| **Guard Blocks Total** | 6,169 (99.6%) | Guard/Filter에 의해 차단된 신호 수 |
| **Orders Submitted** | 25 (0.40%) | 실제 거래로 전환된 신호 수 |
| **Conversion Rate** | **0.40%** | Signal → Order 전환율 |

**Verification**:
```
6,194 (signals) - 6,169 (blocks) = 25 (orders) ✅ PERFECT MATCH
```

---

### 2. Guard/Filter Breakdown (Top 3 Blocking Factors)

| Rank | Reason | Count | % of Signals | Cumulative % | 분석 |
|------|--------|-------|--------------|--------------|------|
| 🥇 **#1** | `FILTER_COOLDOWN_ACTIVE` | 3,263 | **52.68%** | 52.68% | **압도적 차단 요인** |
| 🥈 **#2** | `GUARD_PORTFOLIO_CAN_OPEN` | 2,284 | **36.87%** | 89.55% | **2차 차단 요인** |
| 🥉 **#3** | `FILTER_VOLUME_SPIKE` | 622 | **10.04%** | 99.60% | **3차 차단 요인** |

**Total Accounted**: 6,169 / 6,169 (100%)

---

### 3. Guard/Filter 원인 분석

#### 3.1 FILTER_COOLDOWN_ACTIVE (52.68% 차단)

**Location**: `signals/signal_generator.py::_should_alert()`

**메커니즘**:
```python
def _should_alert(self, symbol: str, side: str, ts: int) -> bool:
    key = f"{symbol}_{side}"
    prev = self.last_alert_ts.get(key)
    
    # Cooldown 계산: timeframe × cooldown_candles
    tf = self.config["timeframe"]  # e.g., "5m"
    ms = int(tf[:-1]) * 60 * 1000  # 5분 = 300,000ms
    
    cooldown = ms * self.config.get("cooldown_candles", 0)
    
    if prev and ts - prev < cooldown:
        return False  # ❌ 쿨다운 차단
    
    self.last_alert_ts[key] = ts
    return True
```

**문제점**:
1. **심볼별/방향별 쿨다운**: `{symbol}_{side}` 단위로 last_alert_ts 관리
   - BTCUSDT_LONG과 BTCUSDT_SHORT는 별도 추적
   - 같은 방향 재진입 시 쿨다운 적용
2. **Config 파라미터 불명확**: `cooldown_candles` 기본값이 0이라고 주석에 나와 있으나, 실제로는 **52.68% 차단 발생**
   - 추정: 전략별 config 또는 상위 레벨에서 `cooldown_candles > 0` 설정되어 있을 가능성
3. **누적 효과**: 5m 타임프레임에서 `cooldown_candles=12`면 1시간 쿨다운
   - 신호 빈도가 높은 전략일수록 쿨다운 충돌 확률 증가

**개선 방향**:
- `cooldown_candles` 값을 0 또는 1~2 수준으로 대폭 축소
- 또는 쿨다운 로직을 완전히 비활성화하고 FlowGuardian에게 일임

---

#### 3.2 GUARD_PORTFOLIO_CAN_OPEN (36.87% 차단)

**Location**: `execution/portfolio_manager.py::can_open_position()`

**메커니즘**:
```python
def can_open_position(
    self, symbol: str, strategy: str, position_value: float, side: str
) -> tuple[bool, str]:
    # 1. 심볼 쿨다운 체크
    if self.cooldown_seconds > 0 and symbol in self.symbol_cooldown:
        cooldown_end = self.symbol_cooldown[symbol] + self.cooldown_seconds
        if now < cooldown_end:
            return False, f"심볼 {symbol} 쿨다운 중"
    
    # 2. 최대 포지션 수 체크
    if self.max_positions > 0 and len(self.get_all_positions()) >= self.max_positions:
        return False, f"포지션 최대 한도 도달: {self.max_positions}개"
    
    # 3. 심볼별 exposure 체크
    new_symbol_exposure = (symbol_exposure + position_value) / equity
    if new_symbol_exposure > self.max_exposure_per_symbol:
        return False, f"{symbol} exposure 초과"
    
    # 4. 전체 포트폴리오 exposure 체크
    new_total_exposure = (total_exposure + position_value) / equity
    if new_total_exposure > self.max_total_exposure:
        return False, f"총 exposure 초과"
    
    # 5. 전략별 포지션 수 체크
    if self.strategy_positions[strategy] >= self.max_strategy_positions:
        return False, f"{strategy} 최대 포지션 도달"
    
    # 6. 전략별 budget 체크 (use_dynamic_budget=True일 때만)
    if self.use_dynamic_budget:
        available_budget = self.get_available_budget(strategy)
        if position_value > available_budget:
            return False, f"{strategy} 예산 초과"
    
    return True, ""
```

**현재 설정 (PHASE28-10 config 기준)**:
- `portfolio.symbol_cooldown_seconds`: **0** (비활성화) ✅
- `risk.max_positions`: **3**
- `risk.max_exposure_per_symbol`: **0.3** (30%)
- `portfolio.max_total_exposure`: **0.8** (80%)
- `portfolio.max_strategy_positions`: **2**
- `portfolio.use_dynamic_budget`: **false** (비활성화) ✅

**문제점**:
1. **복합 가드 작동**: 위 6개 조건 중 하나라도 걸리면 차단
   - 36.87% 차단이 어떤 조건에서 주로 발생하는지 세분화 필요 (PHASE28-10에서는 단일 reason으로 집계)
2. **보수적 Exposure 설정**:
   - `max_exposure_per_symbol=0.3` → 단일 심볼에 30%까지만 투입
   - `max_total_exposure=0.8` → 전체 포트폴리오 80%까지만 투입
   - 단일 심볼(BTCUSDT)만 거래하는 현재 환경에서는 과도한 제약
3. **Max Positions 제한**:
   - `max_positions=3` → 동시에 3개 포지션까지만
   - V2 전략이 신호를 자주 생성하면 slot이 full 상태로 유지될 가능성

**개선 방향**:
- `max_exposure_per_symbol`: 0.3 → 0.5~0.7 (단일 심볼 환경에서는 완화 가능)
- `max_total_exposure`: 0.8 → 0.9~1.0 (전체 자본 활용도 향상)
- `max_positions`: 3 → 5~7 (동시 포지션 수 증가)
- `max_strategy_positions`: 2 → 3~5 (전략별 포지션 증가)

---

#### 3.3 FILTER_VOLUME_SPIKE (10.04% 차단)

**Location**: `signals/signal_generator.py::validate_signal()`

**메커니즘**:
```python
if self.config.get("enable_vol_spike_filter", False):
    last = df.iloc[-1]
    if last["vol_ma"] > 0 and last["volume"] > last["vol_ma"] * self.config["vol_spike_mult"]:
        logger.info(f"⚠️ {symbol} 거래량 급증으로 신호 보류")
        if self.activity_tracker:
            self.activity_tracker.record_guard_block(symbol, "FILTER_VOLUME_SPIKE")
        return False
```

**현재 설정 (PHASE28-10 config 기준)**:
- `enable_vol_spike_filter`: **false** (config에서 명시되지 않음 → 기본값 false로 추정)
- `vol_spike_mult`: **설정되지 않음** (명시되지 않으면 필터 비활성화)

**문제점**:
1. **필터가 비활성화 상태인데도 10.04% 차단**:
   - 이상함! config에서 비활성화했는데 왜 차단?
   - 가능성 1: 전략별 config에서 활성화되어 있음
   - 가능성 2: 기본값 설정 오류
2. **거래량 급증 시 진입 차단**:
   - 변동성 높은 시장에서는 합리적인 보호 장치
   - 하지만 Breakout/Trend Following 전략에서는 오히려 진입 기회를 막을 수 있음

**개선 방향**:
- `vol_spike_mult` 값을 상향 조정 (예: 2.0 → 3.0~5.0)
- 또는 완전히 비활성화 (단, Slippage 증가 리스크 고려 필요)

---

### 4. 2시간 vs 3개월 전환율 차이 분석

| Test | Period | Signal True | Orders | Conversion Rate | 분석 |
|------|--------|-------------|--------|-----------------|------|
| **Short (2H)** | 2024-12-08 10:00~12:00 | 239 | 30 | **12.68%** ✅ | 쿨다운 미누적, 포지션 슬롯 여유 |
| **Full (3M)** | 2024-10-01~12-31 | 6,194 | 25 | **0.40%** ❌ | 쿨다운 누적, 포지션 슬롯 포화 |

**차이 원인 (시간 누적형 Guard/Filter 관점)**:

#### 4.1 쿨다운 누적 효과 (Cooldown Accumulation)
- **2시간**: 신호 239개, 쿨다운 충돌 최소 (초반 진입 → 청산 → 재진입 여유)
- **3개월**: 신호 6,194개, 쿨다운 충돌 극대화
  - 5m 타임프레임: 3개월 = 92일 × 288 candles/day = 26,496 candles
  - `cooldown_candles=12` 가정 시 1시간 쿨다운 → 동일 방향 재진입 시 충돌
  - **누적 차단률**: (3,263 / 6,194) = 52.68%

#### 4.2 포지션 슬롯 포화 (Position Slot Saturation)
- **2시간**: 최대 3개 포지션 제한에 여유
  - 초반 진입 → 빠르게 청산 → 슬롯 재활용 가능
- **3개월**: 포지션 슬롯 지속적으로 포화
  - `max_positions=3`, 평균 holding time이 길면 slot full 상태 유지
  - 새 신호 발생 시 `GUARD_PORTFOLIO_CAN_OPEN` 차단

#### 4.3 리스크 누적 (Risk Accumulation)
- **2시간**: PnL 변동 최소, Exposure 여유
- **3개월**: 연속 손실/이익에 따라 Equity 변동 → Exposure 계산 변화
  - 손실 누적 시 `equity` 감소 → `max_total_exposure` 절대값 감소 → 진입 차단

**결론**:
- 2시간 테스트는 **"Cold Start" 환경**으로, Guard/Filter가 미누적 상태
- 3개월 테스트는 **"Long-Run Equilibrium" 환경**으로, Guard/Filter가 최대 누적 상태
- **실전에 가까운 것은 3개월 테스트!**

---

## 🎯 Guard Optimization 설계

### 목표
1. **전환율 개선**: 0.40% → 3~5% (7.5x ~ 12.5x 향상)
2. **리스크 관리**: 전환율 개선과 리스크 증가 밸런스
3. **실전 타당성**: 지나치게 공격적이지 않은, 상용 가능한 후보 발굴

### 실험 프로파일 설계

총 **4개 프로파일**을 설계하여 순차 백테스트 실행:

---

## 📦 Profile A: BASELINE (현재 상태 기준선)

**목적**: 비교 기준선 (PHASE28-10과 동일 설정)

**Guard/Filter 설정**:

| Category | Parameter | Value | 비고 |
|----------|-----------|-------|------|
| **Cooldown** | `cooldown_candles` | **0** | 쿨다운 비활성화 (기본값) |
| | `portfolio.symbol_cooldown_seconds` | **0** | 심볼 쿨다운 비활성화 |
| | `execution.reject_cooldown_seconds` | **0** | 거부 쿨다운 비활성화 |
| **Portfolio** | `risk.max_positions` | **3** | 최대 동시 포지션 3개 |
| | `portfolio.max_strategy_positions` | **2** | 전략별 최대 2개 |
| | `risk.max_exposure_per_symbol` | **0.3** | 심볼별 30% |
| | `portfolio.max_total_exposure` | **0.8** | 전체 80% |
| | `portfolio.use_dynamic_budget` | **false** | Budget Cap 비활성화 |
| **Volume** | `enable_vol_spike_filter` | **false** | 거래량 필터 비활성화 |
| | `vol_spike_mult` | **2.0** | (비활성화 상태) |

**기대 결과**:
- Conversion Rate: **0.40%** (기준선)
- Trade Count: **25** (기준선)

**리스크**:
- 없음 (현재 상태 재현)

---

## 📦 Profile B: COOLDOWN_RELAXED (쿨다운 완화)

**목적**: FILTER_COOLDOWN_ACTIVE (52.68% 차단) 대폭 완화

**Guard/Filter 설정 (BASELINE 대비 변경 사항)**:

| Category | Parameter | BASELINE | PROFILE B | 변경 이유 |
|----------|-----------|----------|-----------|-----------|
| **Cooldown** | `cooldown_candles` | 0 | **0** | ⚠️ 이미 0이지만 명확히 유지 |

**⚠️ 중요 발견**: BASELINE config에서 이미 `cooldown_candles=0`인데도 52.68% 차단 발생!

**추가 조사 필요**:
1. 전략별 config에 `cooldown_candles` 설정이 있는지 확인
2. `_should_alert()` 메서드가 다른 쿨다운 소스를 참조하는지 확인

**임시 해결책**:
- Signal Generator 초기화 시 `cooldown_candles`를 **명시적으로 0으로 강제**
- 또는 `_should_alert()` 메서드를 **완전히 bypass**하도록 config 추가

**코드 수정 방안**:
```python
# signals/signal_generator.py::_should_alert()
def _should_alert(self, symbol: str, side: str, ts: int) -> bool:
    # ⭐ PHASE28-11: Cooldown 완전 비활성화 옵션
    if self.config.get("disable_signal_cooldown", False):
        return True  # 쿨다운 체크 스킵
    
    # 기존 로직...
```

**Config 추가**:
```yaml
# configs/backtest/phase28_11_btc5m_baseline_v2_profile_b.yml
disable_signal_cooldown: true  # ⭐ NEW: 신호 쿨다운 완전 비활성화
```

**기대 결과**:
- **FILTER_COOLDOWN_ACTIVE 차단**: 3,263 → 0 (완전 제거)
- **Conversion Rate**: 0.40% → **52.68%** (이론상 최대치)
  - 실제로는 GUARD_PORTFOLIO_CAN_OPEN (36.87%)가 여전히 차단하므로, **약 16~20%** 예상
- **Trade Count**: 25 → **약 1,000~1,200개** (극단적 증가)

**리스크**:
- 🔴 **Over-Trading**: 신호가 매우 빈번하게 전환되어 수수료 증가
- 🔴 **Slippage 증가**: 짧은 시간 내 다수 주문 발생 시 슬리피지 악화
- 🔴 **리스크 집중**: 동일 방향 연속 진입 시 리스크 집중도 증가

---

## 📦 Profile C: PORTFOLIO_RELAXED (포트폴리오 가드 완화)

**목적**: GUARD_PORTFOLIO_CAN_OPEN (36.87% 차단) 대폭 완화

**Guard/Filter 설정 (BASELINE 대비 변경 사항)**:

| Category | Parameter | BASELINE | PROFILE C | 변경 이유 |
|----------|-----------|----------|-----------|-----------|
| **Cooldown** | `cooldown_candles` | 0 | **0** | 유지 (쿨다운 비활성화) |
| **Portfolio** | `risk.max_positions` | 3 | **7** | 동시 포지션 수 2배 이상 증가 |
| | `portfolio.max_strategy_positions` | 2 | **5** | 전략별 포지션 2배 이상 증가 |
| | `risk.max_exposure_per_symbol` | 0.3 | **0.7** | 단일 심볼 70% (단일 심볼 환경) |
| | `portfolio.max_total_exposure` | 0.8 | **1.0** | 전체 자본 100% 활용 |

**기대 결과**:
- **GUARD_PORTFOLIO_CAN_OPEN 차단**: 2,284 → **약 500~800** (65~75% 감소)
- **Conversion Rate**: 0.40% → **약 25~30%** (기준선 + Portfolio 차단 완화)
- **Trade Count**: 25 → **약 1,500~1,800개**

**리스크**:
- 🟡 **Exposure 증가**: 최대 100% 자본 투입 → 연속 손실 시 자본 급감
- 🟡 **포지션 관리 복잡도**: 동시 7개 포지션 → 청산 관리 복잡
- 🟡 **Margin Call 리스크**: 레버리지 3x 환경에서 exposure 1.0 = 실질 3x leverage

---

## 📦 Profile D: MIXED_RELAXED (혼합 완화, 상용 후보)

**목적**: Profile B + C 혼합, 지나치게 극단적이지 않은 **상용 가능 후보**

**Guard/Filter 설정 (BASELINE 대비 변경 사항)**:

| Category | Parameter | BASELINE | PROFILE D | 변경 이유 |
|----------|-----------|----------|-----------|-----------|
| **Cooldown** | `disable_signal_cooldown` | false | **true** | 신호 쿨다운 완전 비활성화 |
| **Portfolio** | `risk.max_positions` | 3 | **5** | 동시 포지션 중간 수준 증가 |
| | `portfolio.max_strategy_positions` | 2 | **4** | 전략별 포지션 중간 수준 증가 |
| | `risk.max_exposure_per_symbol` | 0.3 | **0.5** | 단일 심볼 50% (중간 완화) |
| | `portfolio.max_total_exposure` | 0.8 | **0.9** | 전체 자본 90% (중간 완화) |
| **Volume** | `enable_vol_spike_filter` | false | **true** | 거래량 필터 활성화 |
| | `vol_spike_mult` | 2.0 | **4.0** | 필터 threshold 완화 (극단적 spike만 차단) |

**기대 결과**:
- **FILTER_COOLDOWN_ACTIVE 차단**: 3,263 → **0** (완전 제거)
- **GUARD_PORTFOLIO_CAN_OPEN 차단**: 2,284 → **약 800~1,000** (55~60% 감소)
- **FILTER_VOLUME_SPIKE 차단**: 622 → **약 200~300** (50~70% 감소)
- **Conversion Rate**: 0.40% → **약 10~15%** (목표 3~5% 초과 달성)
- **Trade Count**: 25 → **약 600~900개**

**리스크**:
- 🟢 **밸런스 양호**: 극단적이지 않은 완화로 리스크 관리 가능
- 🟡 **Trade Count 증가**: 600~900개 거래 → 수수료 및 슬리피지 증가
- 🟡 **백테스트 vs 실전 괴리**: 실전에서는 슬리피지/지연 등으로 전환율 하락 가능

**상용 타당성**:
- ✅ **실전 후보 #1**: 리스크와 전환율 밸런스가 가장 좋음
- ✅ **다음 단계 최적화 기준선**: PHASE28-12에서 파라미터 튜닝 시작점

---

## 📊 프로파일 비교 요약

| Profile | Cooldown | Max Positions | Exposure (Symbol/Total) | Vol Filter | 예상 전환율 | 예상 Trade Count | 리스크 레벨 |
|---------|----------|---------------|-------------------------|------------|-------------|------------------|-------------|
| **A: BASELINE** | 0 (기본) | 3 | 30% / 80% | OFF | **0.40%** | 25 | 🟢 LOW |
| **B: COOLDOWN_RELAXED** | OFF (강제) | 3 | 30% / 80% | OFF | **16~20%** | 1,000~1,200 | 🔴 HIGH |
| **C: PORTFOLIO_RELAXED** | 0 (기본) | 7 | 70% / 100% | OFF | **25~30%** | 1,500~1,800 | 🟡 MEDIUM-HIGH |
| **D: MIXED_RELAXED** | OFF (강제) | 5 | 50% / 90% | 4.0x | **10~15%** | 600~900 | 🟢 MEDIUM |

---

## 🔧 구현 계획

### 1. 코드 수정 (최소 변경)

#### 1.1 Signal Generator: Cooldown Bypass 옵션 추가

**파일**: `signals/signal_generator.py`

**수정 위치**: `_should_alert()` 메서드

```python
def _should_alert(self, symbol: str, side: str, ts: int) -> bool:
    """쿨다운 체크"""
    if not side:
        return False
    
    # ⭐ PHASE28-11: Cooldown 완전 비활성화 옵션
    if self.config.get("disable_signal_cooldown", False):
        return True  # 쿨다운 체크 완전 스킵
    
    # 기존 로직 유지...
    key = f"{symbol}_{side}"
    prev = self.last_alert_ts.get(key)
    
    tf = self.config["timeframe"]
    if tf.endswith("m"):
        ms = int(tf[:-1]) * 60 * 1000
    elif tf.endswith("h"):
        ms = int(tf[:-1]) * 60 * 60 * 1000
    elif tf.endswith("d"):
        ms = int(tf[:-1]) * 24 * 60 * 60 * 1000
    else:
        ms = 5 * 60 * 1000
    
    cooldown = ms * self.config.get("cooldown_candles", 0)
    
    if prev and ts - prev < cooldown:
        return False
    
    self.last_alert_ts[key] = ts
    return True
```

**테스트**:
- Unit Test 추가: `tests/test_signals/test_signal_generator.py`
- `disable_signal_cooldown=True` 설정 시 항상 True 반환 확인

---

### 2. Config 파일 생성

#### 2.1 Profile A: BASELINE

**파일**: `configs/backtest/phase28_11_btc5m_baseline_v2_profile_a.yml`

- PHASE28-10 config 복사 (변경 없음)
- `run_id`: `phase28_11_profile_a_baseline`
- `trade_activity_tracker.output_file`: `reports/backtest/phase28_11/profile_a_summary.json`

#### 2.2 Profile B: COOLDOWN_RELAXED

**파일**: `configs/backtest/phase28_11_btc5m_baseline_v2_profile_b.yml`

- Profile A 복사
- **추가**:
  - `disable_signal_cooldown: true`
- `run_id`: `phase28_11_profile_b_cooldown_relaxed`
- `trade_activity_tracker.output_file`: `reports/backtest/phase28_11/profile_b_summary.json`

#### 2.3 Profile C: PORTFOLIO_RELAXED

**파일**: `configs/backtest/phase28_11_btc5m_baseline_v2_profile_c.yml`

- Profile A 복사
- **변경**:
  - `risk.max_positions`: 3 → **7**
  - `portfolio.max_strategy_positions`: 2 → **5**
  - `risk.max_exposure_per_symbol`: 0.3 → **0.7**
  - `portfolio.max_total_exposure`: 0.8 → **1.0**
- `run_id`: `phase28_11_profile_c_portfolio_relaxed`
- `trade_activity_tracker.output_file`: `reports/backtest/phase28_11/profile_c_summary.json`

#### 2.4 Profile D: MIXED_RELAXED

**파일**: `configs/backtest/phase28_11_btc5m_baseline_v2_profile_d.yml`

- Profile A 복사
- **추가/변경**:
  - `disable_signal_cooldown: true`
  - `risk.max_positions`: 3 → **5**
  - `portfolio.max_strategy_positions`: 2 → **4**
  - `risk.max_exposure_per_symbol`: 0.3 → **0.5**
  - `portfolio.max_total_exposure`: 0.8 → **0.9**
  - `enable_vol_spike_filter: true`
  - `vol_spike_mult: 4.0`
- `run_id`: `phase28_11_profile_d_mixed_relaxed`
- `trade_activity_tracker.output_file`: `reports/backtest/phase28_11/profile_d_summary.json`

---

### 3. 백테스트 실행 순서

```bash
# 가상환경 활성화
conda activate trading_bot_env

# 1. Profile A (BASELINE) - 기준선
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_a.yml

# 2. Profile B (COOLDOWN_RELAXED) - 쿨다운 완화
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_b.yml

# 3. Profile C (PORTFOLIO_RELAXED) - 포트폴리오 완화
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_c.yml

# 4. Profile D (MIXED_RELAXED) - 혼합 완화 (상용 후보)
python scripts/run_v2.py --mode backtest --config configs/backtest/phase28_11_btc5m_baseline_v2_profile_d.yml
```

---

### 4. 분석 스크립트 (`scripts/analysis/phase28_11_profile_comparison.py`)

**기능**:
1. 4개 프로파일의 telemetry summary JSON 읽기
2. 프로파일별 핵심 지표 비교:
   - Conversion Rate
   - Trade Count
   - Guard/Filter Breakdown (Top 3)
   - PnL / Sharpe / Win Rate (있는 경우)
3. JSON + Markdown 리포트 생성

**출력**:
- `reports/backtest/phase28_11/profile_comparison.json`
- `reports/backtest/phase28_11/profile_comparison.md`

---

## ✅ Acceptance Criteria

PHASE28-11 완료 조건:

1. ✅ **AC1**: 설계 문서 작성 (`PHASE28_11_GUARD_OPTIMIZATION_DESIGN.md`)
2. ✅ **AC2**: 코드 수정 완료 (`signals/signal_generator.py::_should_alert()`)
3. ✅ **AC3**: 4개 Config 파일 생성 (Profile A/B/C/D)
4. ⏳ **AC4**: 4개 백테스트 실행 완료 (telemetry 포함)
5. ⏳ **AC5**: 분석 스크립트 구현 및 실행
6. ⏳ **AC6**: 프로파일 비교 리포트 생성 (JSON + MD)
7. ⏳ **AC7**: 상용 후보 1~2개 추천 및 근거 문서화
8. ⏳ **AC8**: PHASE_ROADMAP.md 업데이트
9. ⏳ **AC9**: Git Commit (PHASE28-11 COMPLETE)

---

## 📝 Notes

- 이 문서는 **설계서**이자 PHASE28-11의 **기준 문서**입니다.
- 백테스트 실행 전에 반드시 Redis/DB 초기화를 수행하여 이전 세션의 영향을 제거하세요.
- Profile B/C는 극단적 완화이므로, 실전 적용은 **Profile D (MIXED)** 기준으로 고려하세요.

---

## 🚀 Next Steps (After PHASE28-11)

- **PHASE28-12**: Profile D 기준으로 파라미터 Fine-Tuning
- **PHASE28-13**: Multi-Period Validation (Bull/Bear/Range 별도 검증)
- **PHASE29**: Paper Trading 실전 검증 (30일)
