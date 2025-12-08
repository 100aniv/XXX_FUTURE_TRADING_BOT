# PHASE29-0: btc5m_baseline_v2 전략 리디자인 설계

## 📋 Executive Summary

**작성 일자**: 2025-12-08  
**Phase**: PHASE29-0 (전략 드로우다운 진단 & 리디자인 설계)  
**대상 전략**: `btc5m_baseline_v2` (PHASE28-6/7 설계)

**핵심 발견**:
- ✅ Guard/Infra는 PHASE28-13 기준 상용급 수준 (Daily Loss Guard OFF/SOFT/HARD 모드 완성)
- ❌ **전략 기대값<0**: 10% Drawdown에서 백테스트 조기 종료 (35% 완료)
- ❌ **Trend Regime 편향**: 95% Trend 구간, Range 구간 진입 부족
- ❌ **전환율 vs 생존 기간 트레이드오프**: 28% 전환율 극대화, 하지만 빠른 손실 누적

**결론**:
- 현재 병목은 **전략 성능**이며, Guard/Infra 최적화로는 한계
- V3 리디자인 필요: Win Rate 개선, R:R 조정, Regime별 전략 모드 분리

---

## 📊 Quick Nav

- [현재 전략 로직 요약](#현재-전략-로직-요약-btc5m_baseline_v2)
- [정량 분석 결과](#정량-분석-결과-phase29-0-진단)
- [근본 원인 가설](#근본-원인-가설)
- [리디자인 목표 정의](#리디자인-목표-정의-v3)
- [리디자인 방향성](#리디자인-방향성-v3-설계-개요)
- [PHASE29 이후 실행 계획](#phase29-이후-실행-계획)

---

## 🎯 현재 전략 로직 요약 (btc5m_baseline_v2)

### 설계 원칙 (PHASE28-6/7)

**V1 → V2 주요 변경**:
- **Regime Detection**: ADX + DI+/DI- + ATR → 6-state 분류 (Bull/Bear/Range × High/Low Volatility)
- **Dynamic Threshold**: 고정 RSI 45/55 → Rolling percentile (20%/80%), BB 고정 1.0/1.5 → Volatility 조정 (0.5-2.5)
- **ParamSpace 확장**: RSI 30-70, BB 0.5-2.5, RR 0.8-3.0
- **Regime별 신호 로직**: 6개 상태별 다른 진입 조건

### 진입 로직 (Regime별)

| Regime | 전략 방향 | LONG 조건 | SHORT 조건 | Long/Short Bias |
|--------|-----------|-----------|------------|-----------------|
| **bull_high_vol** | 추세 추종 + 돌파 | Price < BB Main Lower & RSI < threshold | Price > BB Strong Upper & RSI > threshold*1.2 | 70/30 |
| **bull_low_vol** | 조정 매수 + Mean Reversion | RSI < threshold OR Price < BB Main Lower | RSI > threshold & Price > BB Strong Upper | 60/40 |
| **bear_high_vol** | 추세 추종 + 돌파 | Price < BB Strong Lower & RSI < threshold*0.8 | Price > BB Main Upper & RSI > threshold | 30/70 |
| **bear_low_vol** | 반등 매도 + Mean Reversion | RSI < threshold & Price < BB Strong Lower | RSI > threshold OR Price > BB Main Upper | 40/60 |
| **range_high_vol** | 경계 거래 + 빠른 익절 | Price < BB Main Lower & RSI < threshold | Price > BB Main Upper & RSI > threshold | 50/50 |
| **range_low_vol** | Mean Reversion | RSI < threshold OR Price < BB Main Lower | RSI > threshold OR Price > BB Main Upper | 50/50 |

### TP/SL 구조

- **SL Distance**: `atr * atr_mult_sl` (기본 1.5)
- **TP Distance**: `sl_distance * rr` (기본 1.5, ParamSpace 0.8-3.0)
- **Max Hold Time**: `max_hold_minutes` (기본 60분)
- **Leverage**: ATR 기반 동적 계산 (min/max 범위 내)

### 주요 파라미터 (ParamSpace)

```yaml
# strategies/btc5m_baseline_v2.py 기준
- atr_mult_sl: 1.5 (SL 거리 계산)
- rr: 1.5 (Risk/Reward Ratio)
- max_hold_minutes: 60 (최대 홀드 시간)
- rsi_long_percentile_base: 25 (LONG RSI percentile)
- rsi_short_percentile_base: 75 (SHORT RSI percentile)
- bb_mult_main_base: 0.8 (BB Main 배수)
- bb_mult_strong_base: 1.5 (BB Strong 배수)
- momentum_threshold_base: 0.001 (모멘텀 threshold)
- adx_trend_threshold: 25 (Trend vs Range 분류)
- atr_high_threshold: 70 (High vs Low Volatility 분류)
```

---

## 📈 정량 분석 결과 (PHASE29-0 진단)

### Profile 비교 테이블 (PHASE28-10~13)

| Metric | Profile E (SOFT) | Profile H (OFF) | 개선율 |
|--------|------------------|-----------------|--------|
| **Daily Loss Guard** | SOFT (5%) | OFF | - |
| **Total Calls** | 26,002 | 10,305 | **-60%** (조기 종료) |
| **Signal True** | 6,194 | 2,162 | **-65%** (조기 종료) |
| **Orders Submitted** | 138 | 612 | **+344%** |
| **전환율** | 2.23% | 28.31% | **+12.7배** |
| **Guard 차단** | 11,678 (93.7% DAILY_LOSS) | 1,350 (58.8% COOLDOWN) | **-88.4%** |
| **백테스트 완료율** | 100% | **35%** | **-65%** (Drawdown Guard 10%) |
| **Regime Trend %** | 93.3% | 94.8% | - |
| **Long/Short Ratio** | 47.7% / 52.3% | 47.6% / 52.4% | Balanced |

### Profile H/I/J 비교 (모두 OFF mode)

| Metric | H (Baseline) | I (Light) | J (Aggressive) |
|--------|--------------|-----------|----------------|
| **Total Calls** | 10,305 | 8,154 | 7,746 |
| **Signal True** | 2,162 | 1,703 | 1,613 |
| **Orders** | 612 | 485 | 465 |
| **전환율** | 28.31% | 28.48% | 28.83% |
| **완료율** | 35% | 31% | 30% |

**해석**:
- Portfolio 설정 (max_positions, exposure)은 **Drawdown 영향 없음**
- 모든 Profile이 **10% 손실 근처에서 조기 종료**
- 전환율은 극대화되었으나, **생존 기간이 단축**됨

### Regime 분포 (모든 Profile 공통)

- **Trend Regime**: 94~95% (압도적 지배)
- **Range Regime**: 5~6% (진입 부족)
- **Long/Short Ratio**: 47~48% / 52~53% (방향 편향 없음)

**해석**:
- Regime Detection은 정상 작동 (Trend 구간 인식)
- 하지만 **Trend 구간에서도 손실 발생** → Trend Following 로직 실패
- Range 구간 진입 부족 → Mean Reversion 기회 놓침

---

## 🧪 근본 원인 가설

### 1. ❌ **전략 기대값<0: Win Rate 또는 R:R 문제**

**증거**:
- Profile H: 612 orders, 10% 손실까지 3,600 candles (약 12.5일)
- Per-trade 평균 손실: -$5~10 추정 (10% / 612 trades ≈ -0.016% per trade)

**가설**:
- **Win Rate < 45%**: 진입 조건이 너무 느슨 (RSI OR BB → 많은 False Signal)
- **R:R < 1.2**: SL이 너무 가까워 잦은 손절, TP는 멀어 드물게 도달
- **홀드 타임 너무 짧음**: 60분 제한 → 추세가 전개되기 전에 Time Exit

**근거**:
- Trend 구간에서 추세 추종 실패 → 진입 타이밍 후행 또는 TP/SL 부적절
- Range 구간 진입 부족 → Mean Reversion 조건 너무 보수적

### 2. 📊 **Regime Detection은 정상, 하지만 진입 로직 미흡**

**증거**:
- Trend Regime 94.8% 정확히 인식
- 하지만 Trend 구간에서도 손실 → **"올바른 Regime, 잘못된 Entry"**

**가설**:
- **Bull Trend에서 LONG 진입 타이밍 후행**: RSI < 25th percentile는 이미 과매도 구간 → 추세 반전 우려
- **Bear Trend에서 SHORT 진입 타이밍 후행**: RSI > 75th percentile는 이미 과매수 구간 → 추세 반전 우려
- **BB + RSI OR 로직**: 너무 많은 False Signal (하나만 충족해도 진입)

**대안**:
- Trend 구간: Pullback 진입 (EMA + ADX Confirmation)
- Range 구간: Mean Reversion 유지 (하지만 Range 진입 조건 강화)

### 3. 🔄 **전환율 vs 생존 기간 트레이드오프**

**증거**:
- 전환율 28% → 612 orders / 10,305 candles → 평균 **16.8 candles/order (84분)**
- 잦은 거래 → 슬리피지/수수료 누적 + 빠른 손실 누적

**가설**:
- **신호가 너무 자주 발생**: Cooldown 완화로 전환율 증가했지만, 거래 품질 하락
- **소수의 큰 손실이 Drawdown 지배**: 일부 거래가 -2~3% 손실 → 전체 DD 견인

**대안**:
- 신호 품질 향상 (Entry 조건 강화)
- Multi-TP 구조: 1차 TP 빠르게 → 2차 TP는 추세 추종

### 4. 🚫 **TP/SL 구조: SL은 가깝고 TP는 멀다**

**증거**:
- `atr_mult_sl: 1.5`, `rr: 1.5` → SL 1.5 ATR, TP 2.25 ATR
- 5m 평균 ATR ≈ 0.3~0.5% → SL ≈ 0.45~0.75%, TP ≈ 0.68~1.13%

**가설**:
- **SL이 너무 가까움**: 5m 노이즈로 잦은 손절 (Win Rate 하락)
- **TP가 너무 멀음**: RR 1.5는 멀지 않지만, 추세가 전개되기 전에 Time Exit
- **Time Exit 60분**: 평균 홀드 타임 < 60분일 가능성 → TP 미도달

**대안**:
- SL 거리 상향 (1.5 → 2.0 ATR)
- RR 하향 또는 Multi-TP (1차 TP 1.0 ATR, 2차 TP 2.0 ATR)
- BE 이동: 1차 TP 도달 시 SL → Entry로 이동

### 5. 🎲 **Cooldown Filter 58.8% 차단 → 전략 로직과 불일치**

**증거**:
- Profile H: `FILTER_COOLDOWN_ACTIVE` 1,271건 (58.8%)
- 신호 생성 간격 < Cooldown 시간

**가설**:
- 전략이 **연속 신호를 생성**하지만, Cooldown이 차단 (예: 5분마다 신호)
- Cooldown은 리스크 관리용이지만, **전략 자체가 연속 신호를 설계함**

**대안**:
- Cooldown 설정 완화 (현재 설정 확인 필요)
- 또는 전략 로직에서 **"이전 신호 이후 N바 이상 경과" 조건 추가**

---

## 🎯 리디자인 목표 정의 (V3)

### 정량 목표

| Metric | 현재 (V2) | 목표 (V3) | 우선순위 |
|--------|-----------|-----------|----------|
| **Win Rate** | ~40% (추정) | **≥ 50%** | 🥇 **최우선** |
| **Average R:R** | ~1.5 | **≥ 1.3** (1차 TP + 2차 TP 평균) | 🥈 |
| **Max Drawdown (3M)** | -10% (조기 종료) | **≤ 15%** (전체 완료) | 🥉 |
| **전환율 (OFF mode)** | 28.3% | **10~20%** (품질 우선) | - |
| **평균 홀드 타임** | ~60분 (추정) | **30~120분** (Regime별 조정) | - |
| **Trades per Month (3M 기준)** | ~612 (35% 완료) → 1,750/월 | **100~300/월** (품질 우선) | - |

### 질적 목표

1. **Regime별 "하는 일 / 안 하는 일" 명확화**
   - Trend 구간: Pullback 진입 + 추세 추종
   - Range 구간: Mean Reversion + 빠른 TP
   - 현재는 6개 Regime에 모두 진입 → V3는 선택적 진입

2. **소수의 고품질 트레이드 vs 잦은 매매**
   - 현재: 28% 전환율 (잦은 거래)
   - V3: 10~20% 전환율 (Entry 조건 강화)

3. **Multi-TP 구조로 Win Rate + R:R 동시 개선**
   - 1차 TP: 빠르게 도달 (Win Rate 향상)
   - 2차 TP: 추세 추종 (Big Winner 확보)

---

## 🔧 리디자인 방향성 (V3 설계 개요)

### 1. Regime별 전략 모드 분리

#### Trend Mode (Bull/Bear High/Low Volatility)

**진입 조건 (LONG 예시)**:
- ❌ 현재: `RSI < threshold OR Price < BB Lower` (OR 로직)
- ✅ V3: `RSI < threshold AND Price < BB Lower AND EMA Pullback` (AND 로직 + EMA)
- **추가 조건**:
  - ADX ≥ 25 (Trend 강도 확인)
  - DI+ > DI- (LONG) or DI- > DI+ (SHORT)
  - EMA 5/20 Pullback: Price가 EMA 5와 EMA 20 사이 (추세 유지 확인)

**TP/SL 구조**:
- **SL**: 2.0 ATR (현재 1.5 → 노이즈 필터링)
- **1차 TP**: 1.2 ATR (60% 포지션, Win Rate 향상)
- **2차 TP**: 3.0 ATR (40% 포지션, Big Winner)
- **BE 이동**: 1차 TP 도달 시 SL → Entry

**Max Hold Time**: 120분 (현재 60분 → 추세 전개 여유)

#### Range Mode (Range High/Low Volatility)

**진입 조건**:
- ❌ 현재: `RSI < threshold OR Price < BB Lower`
- ✅ V3: `RSI < 30 (고정) AND Price < BB Lower (1.5 std) AND ADX < 20` (Range 확인)
- **추가 조건**:
  - DI+ ≈ DI- (차이 < 3)
  - ATR percentile < 50 (낮은 변동성)

**TP/SL 구조**:
- **SL**: 1.5 ATR (타이트)
- **TP**: 1.0 ATR (빠른 익절, Mean Reversion)
- **Max Hold Time**: 30분 (빠른 진출)

### 2. 시그널 필터링 강화

#### 최소 조건 추가

| Filter | 현재 | V3 |
|--------|------|-----|
| **최소 ATR** | 없음 | ≥ 0.2% (극단적 낮은 변동성 배제) |
| **최소 Volume** | 없음 | ≥ 최근 20바 평균의 80% |
| **시간대 필터** | 없음 | Asia/EU Session 우선 (US는 변동성 높음) |
| **연속 신호 방지** | Cooldown 외부 | 전략 내부에 "이전 신호 ≥ 10바 경과" 조건 |

#### Backtest-Only Optimization

- **V3 개발 단계**: 위 필터를 **Config 기반 토글**로 구현
- **Tuning 단계**: 각 필터의 On/Off 조합을 실험하여 최적값 탐색

### 3. TP/SL 구조 재설계 (Multi-TP)

#### 제안: 2-Level TP 구조

```python
# V3 pseudocode
if side == "LONG":
    sl = entry - (atr * 2.0)  # 2.0 ATR (현재 1.5)
    tp1 = entry + (atr * 1.2)  # 1차 TP: 1.2 ATR (60% 포지션)
    tp2 = entry + (atr * 3.0)  # 2차 TP: 3.0 ATR (40% 포지션)
    
    # 1차 TP 도달 시 → SL을 Entry로 이동 (BE)
    # 2차 TP는 Trailing Stop 또는 Time Exit
```

**기대 효과**:
- **1차 TP**: Win Rate 향상 (빠르게 도달, 60% 포지션 확보)
- **2차 TP**: R:R 향상 (Big Winner, 40% 포지션 추세 추종)
- **평균 R:R**: (0.6 * 1.2) + (0.4 * 3.0) / 2.0 = 0.96 (1차 TP만) + 0.6 (2차 TP 30% 도달 시) ≈ **1.3~1.5**

### 4. Risk/Guard 연동

#### Per-Trade 리스크 축소

- ❌ 현재: Drawdown 10%에서 조기 종료 → 거래당 평균 리스크 ≈ 0.016%
- ✅ V3: **per-trade 리스크 0.3~0.5%** (SL 거리 기준)
  - 예: SL 2.0 ATR ≈ 0.6~1.0% → 포지션 사이즈 조정 (leverage 하향)

#### Drawdown Guard 한도 재검토

- **PHASE29-0**: Drawdown Guard 10% 유지 (V2 기준)
- **PHASE29-3+**: 전략 개선 후 15~20%로 상향 고려

---

## 📅 PHASE29 이후 실행 계획

### PHASE29-1: btc5m_baseline_v3 코드 스켈레톤 + 기본 로직 구현

**목표**: V3 설계를 코드로 구현 (Regime별 모드, Multi-TP, 필터링)

**작업 내역**:
1. `strategies/btc5m_baseline_v3.py` 신규 파일 생성
2. Regime별 진입 로직 구현 (Trend vs Range 모드)
3. Multi-TP 구조 구현 (1차/2차 TP, BE 이동)
4. 시그널 필터링 추가 (최소 ATR/Volume, 시간대, 연속 신호 방지)
5. Config 파라미터 정의 (V3 전용 ParamSpace)

**산출물**:
- `strategies/btc5m_baseline_v3.py`
- `configs/strategies/btc5m_baseline_v3.yml` (ParamSpace)
- Unit Test: `tests/test_btc5m_baseline_v3.py`

**기간**: 2~3 sessions

---

### PHASE29-2: 1주/1개월 스모크 백테스트 + 빠른 피드백

**목표**: V3 로직이 정상 작동하는지 검증 (Full 3M 백테스트 전 스모크 테스트)

**작업 내역**:
1. 1주일 백테스트 실행 (2024-12-01 ~ 2024-12-07)
   - Drawdown Guard OFF (연구용)
   - 최소 거래 수: 20~50 trades
2. 1개월 백테스트 실행 (2024-12-01 ~ 2024-12-31)
   - Drawdown Guard ON (10%)
   - 목표: 전체 완료 + Win Rate ≥ 45%
3. 로그 분석: Regime별 Win Rate, R:R, 홀드 타임

**산출물**:
- `reports/backtest/phase29_2/v3_smoke_1week_summary.json`
- `reports/backtest/phase29_2/v3_smoke_1month_summary.json`
- `docs/PHASE29/PHASE29_2_V3_SMOKE_TEST_REPORT.md`

**판정 기준**:
- ✅ PASS: 1개월 백테스트 전체 완료 + Win Rate ≥ 45%
- ❌ FAIL: Drawdown 10% 조기 종료 또는 Win Rate < 40%

**기간**: 1 session

---

### PHASE29-3: Random/Bayesian/Local Grid 튜닝 인프라 활용한 파라미터 탐색

**목표**: V3 ParamSpace에서 최적 파라미터 조합 탐색

**작업 내역**:
1. Tuning Config 생성 (V3 ParamSpace)
   - SL/TP 배수, RSI/BB threshold, Regime 조건, 필터 On/Off
2. Random Search 50회 실행 (1개월 백테스트)
3. Top 10 조합 선정 → Bayesian Optimization 30회
4. 최종 후보 3개 선정 → 3개월 Full Backtest

**산출물**:
- `configs/tuning/phase29_3_v3_tuning.yml`
- `reports/tuning/phase29_3_v3_top10.json`
- `docs/PHASE29/PHASE29_3_V3_TUNING_REPORT.md`

**판정 기준**:
- Top 3 조합이 모두 3개월 Drawdown < 15% + Win Rate ≥ 50%

**기간**: 3~5 sessions (튜닝 반복 포함)

---

### PHASE29-4: 3M Multi-Regime 백테스트 + Guard 통합 검증

**목표**: V3 최종 후보를 3개월 Full Backtest로 검증 (Bull/Bear/Range 모든 구간)

**작업 내역**:
1. 3개월 백테스트 (2024-10-01 ~ 2024-12-31)
   - Drawdown Guard ON (10% → 15% 상향 실험)
   - Daily Loss Guard SOFT (5%)
2. Regime별 성능 분석:
   - Trend 구간: Win Rate, R:R, 홀드 타임
   - Range 구간: Win Rate, R:R, 홀드 타임
3. Guard 통합 검증:
   - Daily Loss Guard, Drawdown Guard, Portfolio Guard 정상 작동 확인

**산출물**:
- `reports/backtest/phase29_4/v3_3m_full_summary.json`
- `reports/backtest/phase29_4/v3_regime_breakdown.json`
- `docs/PHASE29/PHASE29_4_V3_FULL_BACKTEST_REPORT.md`

**판정 기준**:
- ✅ PASS: 3개월 전체 완료 + Win Rate ≥ 50% + Max DD ≤ 15%
- ✅ TARGET: Sharpe ≥ 0.5, Profit Factor ≥ 1.2

**기간**: 2~3 sessions

---

### PHASE30+: Multi-Symbol 확장 및 Paper Trading

**PHASE30**: V3 전략을 Multi-Symbol로 확장 (Top 10~50 심볼)  
**PHASE31**: Ensemble 프레임워크 복구 (V2/V3 혼합)  
**PHASE32**: 30일 Paper Trading 검증  
**PHASE33**: Live 연동 & Final Hardening

---

## 📝 Appendix: V2 vs V3 비교 요약

| 항목 | V2 (btc5m_baseline_v2) | V3 (Proposed) |
|------|------------------------|---------------|
| **Regime Detection** | 6-state (Bull/Bear/Range × High/Low Vol) | ✅ 동일 유지 |
| **진입 로직** | OR 로직 (RSI OR BB) | ✅ AND 로직 (RSI AND BB AND EMA) |
| **Trend 진입** | RSI < threshold OR Price < BB Lower | ✅ Pullback 진입 (EMA 추가) |
| **Range 진입** | 동일 (Mean Reversion) | ✅ ADX < 20 조건 추가 |
| **SL 거리** | 1.5 ATR | ✅ 2.0 ATR (노이즈 필터링) |
| **TP 구조** | 단일 TP (1.5 RR) | ✅ Multi-TP (1.2 ATR + 3.0 ATR) |
| **BE 이동** | 없음 | ✅ 1차 TP 도달 시 SL → Entry |
| **Max Hold Time** | 60분 | ✅ Regime별 (30~120분) |
| **필터링** | Cooldown 외부 | ✅ 전략 내부 (최소 ATR/Volume, 시간대, 연속 신호) |
| **Win Rate 목표** | N/A | ✅ ≥ 50% |
| **R:R 목표** | 1.5 | ✅ 1.3~1.5 (평균) |
| **전환율** | 28.3% (OFF mode) | ✅ 10~20% (품질 우선) |

---

## 🚀 요약 및 다음 단계

### 핵심 메시지

1. **Guard/Infra는 완성**: PHASE28-13 기준 상용급
2. **병목은 전략 성능**: 전략 기대값<0 → V3 리디자인 필요
3. **V3 설계 방향**:
   - Win Rate 개선 (≥ 50%)
   - Multi-TP 구조
   - Regime별 모드 분리 (Trend Pullback vs Range Mean Reversion)
   - 신호 품질 우선 (전환율 10~20%)

### 즉시 시작 가능한 작업

- [x] ✅ PHASE29-0: 진단 & 설계 문서 작성 (이 문서)
- [ ] PHASE29-1: V3 코드 스켈레톤 구현
- [ ] PHASE29-2: 1주/1개월 스모크 백테스트
- [ ] PHASE29-3: 파라미터 튜닝 (Random/Bayesian)
- [ ] PHASE29-4: 3M Full Backtest + 검증

**PHASE29-0 완료. 다음 Phase로 진행하세요!** 🚀
