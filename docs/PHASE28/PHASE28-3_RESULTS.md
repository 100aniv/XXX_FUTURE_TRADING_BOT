# PHASE28-3: Random Search Round 1 실행 결과

**일시**: 2025-12-06 14:59:30
**상태**: ✅ PASS

---

## 📋 개요

PHASE28-3는 btc5m_baseline_v1 전략에 대한 첫 번째 대규모 Random Search 실행입니다.
이 단계는 PHASE28 튜닝 파이프라인의 핵심 단계로, 파라미터 공간 탐색을 통해 유망한 후보 파라미터 세트를 발굴하는 것이 목표입니다.

## ⚙️ 실행 파라미터

- **Trials per period**: 20
- **Market periods**: bull, range
- **총 예상 jobs**: 40
- **ParamSpace**: `configs/tuning/phase28_2_btc5m_baseline_paramspace.yml`
- **Base config**: `configs/backtest/phase28_2_btc5m_tuning_base.yml`

## 📊 실행 요약 통계

- **총 실행 jobs**: 46
- **필터 통과 trials**: 16
- **필터 탈락 trials**: 30

### 필터 통과 trials 분포

- **PnL**: 최소 -213.01, 최대 8.40, 중앙값 -126.55
- **Sharpe Ratio**: 최소 -105.7029, 최대 0.7509, 중앙값 -29.6750
- **Win Rate**: 최소 0.00%, 최대 33.33%, 중앙값 0.00%
- **거래 수**: 최소 5, 최대 6, 중앙값 5

## 🏆 Top-5 후보 파라미터 세트

정렬 기준: Sharpe Ratio > PnL > Win Rate

### 1. job_64dd8feb90dc... (Period: 2ea22570)

**메트릭**:
- PnL: 8.40
- Sharpe Ratio: 0.7509
- Win Rate: 33.33%
- 거래 수: 6
- Max Drawdown: 416.06%

**파라미터**:
```json
{
  "rr": 1.427080236719015,
  "atr_mult_sl": 1.0110363670799,
  "bb_std_main": 1.0464084623552723,
  "bb_std_strong": 1.32456380271135,
  "max_hold_minutes": 45,
  "momentum_lookback": 3,
  "momentum_threshold": 0.000608500411558031,
  "rsi_long_threshold": 44,
  "adx_trend_threshold": 23,
  "rsi_short_threshold": 55
}
```

### 2. job_432f5964f8d7... (Period: 68ef295e)

**메트릭**:
- PnL: -79.57
- Sharpe Ratio: -9.9303
- Win Rate: 33.33%
- 거래 수: 6
- Max Drawdown: 314.25%

**파라미터**:
```json
{
  "rr": 1.269551066103533,
  "atr_mult_sl": 1.8921795677048454,
  "bb_std_main": 1.1224651499279499,
  "bb_std_strong": 1.373467556141043,
  "max_hold_minutes": 120,
  "momentum_lookback": 3,
  "momentum_threshold": 0.001515049231134367,
  "rsi_long_threshold": 41,
  "adx_trend_threshold": 20,
  "rsi_short_threshold": 52
}
```

### 3. job_1642d3dd2d85... (Period: 68ef295e)

**메트릭**:
- PnL: -73.40
- Sharpe Ratio: -15.0893
- Win Rate: 20.00%
- 거래 수: 5
- Max Drawdown: 416.06%

**파라미터**:
```json
{
  "rr": 1.427080236719015,
  "atr_mult_sl": 1.0110363670799,
  "bb_std_main": 1.0464084623552723,
  "bb_std_strong": 1.32456380271135,
  "max_hold_minutes": 45,
  "momentum_lookback": 3,
  "momentum_threshold": 0.000608500411558031,
  "rsi_long_threshold": 44,
  "adx_trend_threshold": 23,
  "rsi_short_threshold": 55
}
```

### 4. job_8db34a9a8068... (Period: 68ef295e)

**메트릭**:
- PnL: -72.93
- Sharpe Ratio: -16.7995
- Win Rate: 20.00%
- 거래 수: 5
- Max Drawdown: 194.24%

**파라미터**:
```json
{
  "rr": 1.7774900908609226,
  "atr_mult_sl": 1.3516239368616199,
  "bb_std_main": 0.9449913158987957,
  "bb_std_strong": 1.5218111112028838,
  "max_hold_minutes": 120,
  "momentum_lookback": 5,
  "momentum_threshold": 0.0009529063935038739,
  "rsi_long_threshold": 41,
  "adx_trend_threshold": 19,
  "rsi_short_threshold": 53
}
```

### 5. job_8eca38c49efa... (Period: 2ea22570)

**메트릭**:
- PnL: -91.33
- Sharpe Ratio: -17.7320
- Win Rate: 20.00%
- 거래 수: 5
- Max Drawdown: 283.92%

**파라미터**:
```json
{
  "rr": 1.785035058153254,
  "atr_mult_sl": 1.3300715429886223,
  "bb_std_main": 1.066821040879024,
  "bb_std_strong": 1.4449067463498646,
  "max_hold_minutes": 60,
  "momentum_lookback": 10,
  "momentum_threshold": 0.0008285023247432009,
  "rsi_long_threshold": 42,
  "adx_trend_threshold": 25,
  "rsi_short_threshold": 55
}
```

## 📈 Period별 분석

### BULL 구간

⚠️ 필터를 통과한 trial이 없습니다.

### RANGE 구간

⚠️ 필터를 통과한 trial이 없습니다.

## 🚫 필터 탈락 Trials

총 30개 trials가 필터링 기준을 충족하지 못했습니다.

| Job ID | 거래 수 | PnL | Sharpe | 탈락 이유 |
|--------|---------|-----|--------|----------|
| job_39202b21a71... | 4 | -20.34 | -2.5334 | 거래 수 부족 (4 < 5) |
| job_6d728b9996b... | 4 | -55.39 | -8.6670 | 거래 수 부족 (4 < 5) |
| job_55a649267ab... | 4 | -67.71 | -11.8169 | 거래 수 부족 (4 < 5) |
| job_eac2405469d... | 4 | -71.21 | -20.5194 | 거래 수 부족 (4 < 5) |
| job_504ca841a3d... | 3 | -73.99 | -32.7647 | 거래 수 부족 (3 < 5) |
| job_e15d80bba26... | 3 | -73.99 | -32.7647 | 거래 수 부족 (3 < 5) |
| job_36cbf71dd12... | 3 | -157.12 | -38.7876 | 거래 수 부족 (3 < 5) |
| job_7cad8e9e340... | 4 | -224.22 | -45.8642 | 거래 수 부족 (4 < 5) |
| job_a5cf48a2254... | 4 | -134.12 | -52.4535 | 거래 수 부족 (4 < 5) |
| job_764c5676331... | 3 | -135.53 | -54.3757 | 거래 수 부족 (3 < 5) |

_(나머지 20개 생략)_

## ✅ Acceptance 판정

**상태**: ✅ PASS

**기준별 결과**:
- ✅ A1_실행_커버리지: 총 46개 jobs 실행 (예상: 40)
- ✅ A2_Period별_결과: 2/2 periods에서 필터 통과 trial 존재
- ✅ A3_거래_수_품질: 평균 거래 수: 5.1 (기준: ≥5)
- ✅ A4_유망_후보_발견: 1개 trials에서 양의 Sharpe Ratio

## 💡 인사이트 & 다음 단계 제안

1. **긍정적 결과**: 1개 trials에서 양의 Sharpe Ratio 확인
   - 이들 파라미터 세트를 기반으로 PHASE28-4에서 Bayesian Search 수행 가능


### 제안 사항

- **PHASE28-4**: 상위 5개 파라미터 세트를 시드로 Bayesian Search 수행
- **PHASE28-5**: 검증된 파라미터로 Multi-symbol 확장 테스트
- **Data Quality**: 더 다양한 market regime 구간에서 재검증

## ⚠️ Known Issues & 제약사항

1. **단일 Worker 실행**: 현재는 순차 처리로 시간이 오래 걸림
   - 향후 Multi-worker parallelization으로 개선 예정
2. **제한된 파라미터 공간**: 10개 파라미터만 탐색
   - 추가 파라미터(예: trailing stop, position sizing) 확장 필요
3. **Market Period 선택**: 수동 선택 방식
   - 자동 regime detection 및 adaptive period 선택 검토

---

**생성 일시**: 2025-12-06 14:59:30
**생성 스크립트**: `scripts/tuning/phase28_3_monitor_and_finalize.py`
