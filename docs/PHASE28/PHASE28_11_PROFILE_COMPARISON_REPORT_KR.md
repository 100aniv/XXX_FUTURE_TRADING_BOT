# PHASE28-11: Guard Optimization V1 프로파일 비교 최종 리포트

**Date**: 2025-12-08  
**Phase**: PHASE28-11  
**Status**: 🔴 FAIL (목표 미달성)  
**Objective**: Guard/Filter 최적화를 통한 전환율 0.40% → 3~5% 개선

---

## 📋 Executive Summary

### 목표 vs 실제 결과

| 지표 | 목표 | 실제 (최상) | 달성 여부 |
|------|------|------------|-----------|
| **전환율 (Conversion Rate)** | **3~5%** | **0.24%** | ❌ **FAIL** |
| **거래 수 (Orders)** | 186~310 (3개월) | 15 | ❌ FAIL |
| **Guard 차단율** | <95% | 99.76% | ❌ FAIL |

### 핵심 발견

1. **4개 프로파일 모두 목표 전환율(3~5%)에 크게 못 미침**
   - Profile A (BASELINE): 0.24% (15 orders)
   - Profile B (COOLDOWN_RELAXED): 0.24% (15 orders)
   - Profile C (PORTFOLIO_RELAXED): 0.24% (15 orders)
   - Profile D (MIXED_RELAXED): 0.13% (8 orders)

2. **압도적인 차단 요인: `GUARD_PORTFOLIO_CAN_OPEN` (99.76%)**
   - 모든 프로파일에서 Portfolio Guard가 99% 이상의 신호를 차단
   - 전략 예산 제한 (20% = $9,941)이 실질적으로 거래 진입을 거의 불가능하게 만듦

3. **Cooldown 완화 효과 없음**
   - Profile B (쿨다운 완전 제거) vs Profile A (BASELINE): 동일한 전환율 0.24%
   - 이유: Cooldown 이전에 Portfolio Guard가 먼저 모든 신호를 차단

4. **Portfolio 완화 효과 없음**
   - Profile C (포트폴리오 대폭 완화) vs Profile A: 동일한 전환율 0.24%
   - 이유: **Config 설정이 실제 로직에 반영되지 않음** (코드 레벨 버그 의심)

5. **Volume Spike Filter 부작용**
   - Profile D: FILTER_VOLUME_SPIKE가 3.31% 차단 (205건)
   - 전환율을 0.13%로 더 낮춤 (역효과)

---

## 🔍 프로파일별 상세 분석

### Profile A: BASELINE (기준선)

**설정**:
- `disable_signal_cooldown`: false (쿨다운 기본 동작)
- `cooldown_candles`: 0
- `max_positions`: 3
- `max_symbol_exposure_pct`: 30%
- `max_total_exposure`: 80%
- `use_dynamic_budget`: false

**결과**:
- Signal True: 6,194
- Guard Blocks: 6,179 (99.76%)
- Orders Submitted: 15
- **Conversion Rate: 0.24%**

**차단 요인**:
| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

**분석**:
- `GUARD_PORTFOLIO_CAN_OPEN`이 거의 모든 신호를 차단
- 백테스트 로그 확인 결과: **"전략 예산 초과: btc5m_baseline_v2 $9,975.62 > $9,941.55"** 메시지 반복
- 전략 예산이 자본의 20% ($9,941)로 제한되어 있고, 대부분의 신호가 이 한도를 초과하여 차단됨

---

### Profile B: COOLDOWN_RELAXED (쿨다운 완화)

**설정**:
- `disable_signal_cooldown`: **true** (쿨다운 완전 제거)
- 나머지 설정: Profile A와 동일

**결과**:
- Signal True: 6,194
- Guard Blocks: 6,179 (99.76%)
- Orders Submitted: 15
- **Conversion Rate: 0.24%**

**차단 요인**:
| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

**분석**:
- **Profile A와 동일한 결과** (쿨다운 완화 효과 0%)
- 이유: Cooldown 체크 이전에 Portfolio Guard가 먼저 신호를 차단
- Guard 실행 순서: Portfolio Guard (먼저) → Signal Cooldown (나중)
- **결론**: Cooldown은 현재 전환율의 병목이 아님

---

### Profile C: PORTFOLIO_RELAXED (포트폴리오 완화)

**설정**:
- `max_positions`: **3 → 7개** (대폭 완화)
- `max_symbol_exposure_pct`: **30% → 70%** (대폭 완화)
- `max_total_exposure`: **80% → 100%** (대폭 완화)
- `max_strategy_positions`: **2 → 5개** (대폭 완화)

**결과**:
- Signal True: 6,194
- Guard Blocks: 6,179 (99.76%)
- Orders Submitted: 15
- **Conversion Rate: 0.24%**

**차단 요인**:
| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 6,179 | 99.76% |

**분석**:
- **⚠️ CRITICAL**: Profile A와 동일한 결과 (포트폴리오 완화 효과 0%)
- **의심되는 버그**: Config 설정이 실제 `portfolio_manager.py::can_open_position()` 로직에 반영되지 않음
- 백테스트 로그에서 **동일한 "전략 예산 초과" 메시지** 반복 확인
- **근본 원인**: `use_dynamic_budget=false`로 설정했음에도, 전략 예산 체크(20% 한도)가 여전히 활성 상태
- **결론**: Portfolio Guard 로직에 구조적 문제 존재 (PHASE28-12에서 수정 필요)

---

### Profile D: MIXED_RELAXED (혼합 완화, 상용 후보)

**설정**:
- `disable_signal_cooldown`: **true** (쿨다운 제거)
- `max_positions`: **3 → 5개** (중간 완화)
- `max_symbol_exposure_pct`: **30% → 50%** (중간 완화)
- `max_total_exposure`: **80% → 90%** (중간 완화)
- `max_strategy_positions`: **2 → 4개** (중간 완화)
- `enable_vol_spike_filter`: **true** (볼륨 필터 활성화)
- `vol_spike_mult`: **4.0** (완화된 임계값)

**결과**:
- Signal True: 6,194
- Guard Blocks: 6,186 (99.87%)
- Orders Submitted: 8
- **Conversion Rate: 0.13%**

**차단 요인**:
| Rank | Reason | Count | % of Signals |
|------|--------|-------|--------------|
| 🥇 | `GUARD_PORTFOLIO_CAN_OPEN` | 5,981 | 96.56% |
| 🥈 | `FILTER_VOLUME_SPIKE` | 205 | 3.31% |

**분석**:
- **Profile A/B/C보다 더 낮은 전환율** (0.24% → 0.13%)
- Volume Spike Filter가 추가로 205건(3.31%) 차단하여 역효과
- Portfolio Guard는 여전히 96.56% 차단 (Config 설정 미반영 동일)
- **결론**: Volume Spike Filter는 현재 시점에서 불필요하며 부작용만 유발

---

## 📊 프로파일 비교 요약 테이블

| Profile | Conversion Rate | Orders | Top Guard Block | Top Block % | 평가 |
|---------|-----------------|--------|-----------------|-------------|------|
| **A: BASELINE** | **0.24%** | 15 | PORTFOLIO_CAN_OPEN | 99.76% | 🔴 기준선 |
| **B: COOLDOWN_RELAXED** | **0.24%** | 15 | PORTFOLIO_CAN_OPEN | 99.76% | 🔴 효과 없음 |
| **C: PORTFOLIO_RELAXED** | **0.24%** | 15 | PORTFOLIO_CAN_OPEN | 99.76% | 🔴 Config 미반영 |
| **D: MIXED_RELAXED** | **0.13%** | 8 | PORTFOLIO_CAN_OPEN | 96.56% | 🔴 역효과 (Volume Filter) |

---

## 🔍 근본 원인 분석 (Root Cause Analysis)

### 1. 전략 예산 제한이 압도적 병목

**증거**:
- 백테스트 로그에서 반복적으로 발견된 메시지:
  ```
  ❌ [ENTRY BLOCK] reason=portfolio_check_failed 
  detail="전략 예산 초과: btc5m_baseline_v2 $9,975.62 > $9,941.55"
  ```
- 전략 예산: 자본의 20% = $50,000 × 0.2 = $9,941
- 평균 신호 포지션 가치: ~$10,000 (레버리지 3x 기준)
- **대부분의 신호가 전략 예산을 약간 초과하여 차단됨**

**코드 위치**:
- `execution/portfolio_manager.py::can_open_position()`
- 전략 예산 체크 로직:
  ```python
  if self.use_dynamic_budget:
      available_budget = self.get_available_budget(strategy)
      if position_value > available_budget:
          return False, f"{strategy} 예산 초과"
  ```

**문제점**:
- Config에서 `use_dynamic_budget: false`로 설정했음에도,
- **실제로는 전략 예산 체크가 여전히 작동 중** (로그에서 확인됨)
- 이는 코드 로직 버그이거나, 다른 경로에서 예산 체크가 실행되는 것으로 추정

---

### 2. Config 설정이 실제 로직에 반영되지 않음 (Critical Bug)

**증거**:
- Profile C에서 `max_positions`, `max_symbol_exposure_pct`, `max_total_exposure`를 대폭 완화했으나,
- **Profile A와 동일한 결과** (전환율 0.24%, 차단 6,179건)
- 백테스트 로그에서 **동일한 "전략 예산 초과" 메시지** 반복

**가능한 원인**:
1. **Portfolio Manager 초기화 오류**: Config 파라미터가 제대로 전달되지 않음
2. **전략 예산 계산 로직 우선순위**: 다른 Guard 조건보다 전략 예산 체크가 먼저 실행되어 모든 신호 차단
3. **하드코딩된 값**: Config와 무관하게 코드에 하드코딩된 20% 한도 존재 가능

**검증 필요**:
- `portfolio_manager.py::__init__()`: Config 파라미터 로딩 과정 확인
- `portfolio_manager.py::can_open_position()`: Guard 조건 체크 순서 확인
- `portfolio_manager.py::get_available_budget()`: 전략 예산 계산 로직 확인

---

### 3. Guard 실행 순서 문제

**현재 Guard 실행 순서** (추정):
1. **Portfolio Guard** (`can_open_position()`)
   - 전략 예산 체크 (20% 한도)
   - Max positions, Exposure 체크
2. **Signal Cooldown** (`_should_alert()`)
3. **기타 Filter** (Volume Spike, Regime, Trend 등)

**문제점**:
- Portfolio Guard가 가장 먼저 실행되어 99.76%의 신호를 차단
- 이후 Cooldown, Volume Filter 등은 실행 기회조차 없음
- **Cooldown 완화 (Profile B) 효과가 0%인 이유**

**개선 방향**:
- Portfolio Guard의 전략 예산 체크를 **완전히 비활성화**하거나,
- 전략 예산 한도를 자본의 **100%** (unlimited)로 설정하여 무력화

---

## 🚫 PHASE28-11 실패 원인 요약

1. **설계 오류**: Cooldown과 Portfolio 완화만으로는 전환율을 개선할 수 없음
   - 근본 병목은 **전략 예산 제한** (20% 한도)
   - 이 한도를 완화하지 않는 한, 다른 Guard 조건 완화는 의미 없음

2. **구현 버그**: Profile C의 Config 설정이 실제 로직에 반영되지 않음
   - `max_positions`, `max_symbol_exposure_pct`, `max_total_exposure` 완화 효과 0%
   - Portfolio Manager 로직 점검 필요

3. **Guard 순서 설계 결함**: Portfolio Guard가 너무 강력하고 우선순위가 높음
   - 다른 Guard/Filter는 실행 기회조차 없음

4. **Volume Filter 부작용**: Profile D에서 FILTER_VOLUME_SPIKE가 전환율을 더 낮춤
   - 현재 단계에서는 불필요한 필터

---

## 💡 상용 후보 선정 (Production Candidate)

### ⚠️ 결론: **상용 후보 없음 (No Production Candidate)**

**이유**:
- 모든 프로파일이 목표 전환율(3~5%)에 크게 못 미침
- 최상 전환율 0.24% (목표 대비 **12.5배 부족**)
- 3개월 동안 15건의 거래는 상용 트레이딩 봇으로서 의미 없음

**현재 상태 평가**:
- PHASE28-11은 **FAIL** 판정
- 전환율 개선 실패의 근본 원인을 파악했으므로, 다음 PHASE에서 집중 공략 가능

---

## 🎯 PHASE28-12 권장 사항 (Next Steps)

### 긴급 수정 사항 (High Priority)

#### 1. Portfolio Guard 전략 예산 로직 완전 비활성화

**목표**: 전략 예산 제한을 제거하여 Portfolio Guard 차단율을 99.76% → <20%로 감소

**수정 위치**: `execution/portfolio_manager.py::can_open_position()`

**수정 방안**:
```python
# 기존 로직 (문제):
if self.use_dynamic_budget:
    available_budget = self.get_available_budget(strategy)
    if position_value > available_budget:
        return False, f"{strategy} 예산 초과"

# 수정 로직 (제안):
# Option 1: 전략 예산 체크 완전 제거
# if self.use_dynamic_budget:
#     pass  # 비활성화

# Option 2: Config 플래그 추가
if self.use_dynamic_budget and self.config.get('enable_strategy_budget_cap', False):
    available_budget = self.get_available_budget(strategy)
    if position_value > available_budget:
        return False, f"{strategy} 예산 초과"
```

**기대 효과**:
- Portfolio Guard 차단율: 99.76% → 10~20%
- 전환율: 0.24% → 5~10% (예상)

---

#### 2. Config 파라미터 반영 검증 및 수정

**목표**: Profile C의 Config 설정이 실제로 반영되도록 수정

**검증 항목**:
- `portfolio_manager.py::__init__()`: Config 파라미터 로딩 로그 추가
- `can_open_position()`: 각 Guard 조건 체크 시 로그 출력하여 실제 적용 값 확인

**수정 예시**:
```python
def can_open_position(self, symbol, strategy, position_value, side):
    logger.info(f"🔍 [Portfolio Guard Check] max_positions={self.max_positions}, "
                f"max_symbol_exposure={self.max_exposure_per_symbol}, "
                f"max_total_exposure={self.max_total_exposure}")
    
    # ... 기존 로직 ...
```

---

#### 3. Volume Spike Filter 비활성화 (Optional)

**근거**: Profile D에서 FILTER_VOLUME_SPIKE가 3.31% 차단하여 역효과

**수정 방안**:
- PHASE28-12 프로파일에서는 `enable_vol_spike_filter: false`로 설정
- 전략 예산 문제 해결 후, 전환율이 충분히 높아지면(>10%) 재활성화 고려

---

### PHASE28-12 실험 계획 (제안)

#### Profile E: BUDGET_UNLIMITED (전략 예산 제거)

**설정**:
- 전략 예산 체크 완전 비활성화 (코드 수정)
- 나머지: Profile A (BASELINE)과 동일

**기대 전환율**: **5~15%**

---

#### Profile F: BUDGET_UNLIMITED + PORTFOLIO_LIGHT (혼합 최적화)

**설정**:
- 전략 예산 체크 완전 비활성화
- `max_positions`: 3 → 5
- `max_symbol_exposure_pct`: 30% → 50%
- `max_total_exposure`: 80% → 90%

**기대 전환율**: **10~20%**

---

#### Profile G: AGGRESSIVE (공격적 완화)

**설정**:
- 전략 예산 체크 완전 비활성화
- `max_positions`: 3 → 10
- `max_symbol_exposure_pct`: 30% → 100%
- `max_total_exposure`: 80% → 100%
- `max_strategy_positions`: 2 → 10

**기대 전환율**: **20~40%** (리스크 높음)

---

### PHASE28-12 실행 계획

1. **코드 수정** (30분)
   - `portfolio_manager.py`: 전략 예산 로직 비활성화 옵션 추가
   - Config 반영 검증 로직 추가

2. **Profile E/F/G 백테스트** (3개월, 각 10분, 총 30분)
   - 전략 예산 제거 효과 검증

3. **결과 분석 및 리포트** (30분)
   - 전환율이 3~5% 달성 시 상용 후보 선정
   - 달성 못하면 다른 근본 원인 추가 분석

4. **총 소요 시간**: 약 1.5시간

---

## 📈 전환율 개선 로드맵

### PHASE28-11 (현재): FAIL
- **전환율**: 0.24%
- **주요 차단 요인**: Portfolio Guard 전략 예산 제한 (99.76%)

### PHASE28-12 (다음): 전략 예산 제거
- **목표 전환율**: 3~5%
- **수정 사항**: Portfolio Guard 전략 예산 로직 비활성화
- **기대 효과**: Portfolio Guard 차단율 99.76% → 10~20%

### PHASE28-13 (이후): 멀티 기간 검증
- **목표**: Profile E/F 중 선택된 후보를 Bull/Bear/Range 기간에서 검증
- **기간**: 1개월 × 3개 (총 3개월)

### PHASE29: Paper Trading 검증
- **목표**: 선택된 프로파일을 실시간 Paper Trading에서 30일 검증
- **전환율 목표**: 3~5% 유지
- **리스크 목표**: Max DD <10%, Sharpe Ratio >1.0

---

## 🔧 기술 부채 (Technical Debt)

1. **Portfolio Manager 로직 리팩토링 필요**
   - 전략 예산 체크 로직이 Config 플래그와 무관하게 작동 중
   - Guard 조건 체크 순서가 비직관적 (전략 예산이 최우선)

2. **Config 파라미터 반영 검증 부재**
   - Profile C에서 Config 설정이 무시되는 현상
   - 백테스트 시작 시 실제 적용된 값을 로그로 출력하는 로직 추가 필요

3. **Guard Telemetry 개선 필요**
   - 현재는 최종 차단 이유만 기록
   - 각 Guard 조건별 체크 결과를 모두 기록하는 Detailed Telemetry 필요
   - 예: "전략 예산: FAIL, Max positions: PASS, Exposure: PASS" 등

---

## 📝 레슨 런드 (Lessons Learned)

1. **Guard 최적화는 단계적으로 접근해야 함**
   - 한 번에 여러 Guard를 완화하면, 어떤 Guard가 실제 병목인지 파악 어려움
   - PHASE28-11에서는 Cooldown과 Portfolio를 동시에 완화하려 했으나, 근본 병목(전략 예산)을 놓침

2. **Config 설정과 실제 로직의 괴리 주의**
   - Config에서 `use_dynamic_budget: false`로 설정했으나, 실제로는 전략 예산 체크가 작동
   - 백테스트 전에 Config 파라미터가 제대로 반영되는지 검증 로직 필수

3. **백테스트 로그가 가장 중요한 디버깅 도구**
   - PHASE28-11에서 전환율이 0.24%로 나오자, 백테스트 로그를 확인한 결과 전략 예산 초과 메시지 발견
   - Telemetry JSON만으로는 근본 원인 파악 불가

4. **Guard Optimization은 "완화"가 아니라 "병목 제거"**
   - Cooldown을 0으로 만들거나 Portfolio를 100%로 완화하는 것이 목표가 아님
   - **진짜 병목(99.76% 차단 요인)을 찾아 집중 공략**하는 것이 핵심

---

## 📚 참고 문서

- [PHASE28_11_GUARD_OPTIMIZATION_DESIGN.md](./PHASE28_11_GUARD_OPTIMIZATION_DESIGN.md): 설계 문서
- [profile_comparison.json](../../reports/backtest/phase28_11/profile_comparison.json): 원본 비교 데이터
- [profile_comparison.md](../../reports/backtest/phase28_11/profile_comparison.md): 영문 비교 리포트
- [PHASE28_10_GUARD_BREAKDOWN_REPORT.md](./PHASE28_10_GUARD_BREAKDOWN_REPORT.md): PHASE28-10 Guard Telemetry

---

## ✅ PHASE28-11 최종 판정

- **Status**: 🔴 **FAIL** (목표 전환율 3~5% 미달성)
- **전환율**: 0.24% (목표 대비 12.5배 부족)
- **근본 원인**: Portfolio Guard 전략 예산 제한 (20% 한도)
- **다음 단계**: PHASE28-12에서 전략 예산 로직 비활성화 및 재실험

---

**Report Generated**: 2025-12-08 18:55:00  
**Generated by**: PHASE28-11 Profile Comparison Analysis Script  
**Total Backtest Duration**: ~45분 (Profile A/B/C/D 각 ~12분)
