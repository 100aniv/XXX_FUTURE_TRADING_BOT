# PHASE28-4: Bayesian Search Round 1 결과 리포트
**생성일**: 2025-12-07 17:59:54
**상태**: ⚠️ CRITICAL ISSUES DETECTED - 파라미터 전달 실패
---

## ⚠️ CRITICAL ISSUES

### 파라미터 전달 완전 실패
**발견 사실**:
- 실행 로그에서 반복적으로 `params: {}` 확인
- 전략 파라미터 전체가 `MISSING`으로 표시: `rsi_oversold=MISSING, rsi_overbought=MISSING`
- `metrics_json`에는 결과 메트릭만 저장되어 있으며, 튜닝 파라미터는 전혀 없음

**영향**:
- 모든 trials가 **default 파라미터**로 실행됨
- Bayesian Optimization이 **전혀 작동하지 않음**
- 결과: **13 trials 모두 Sharpe ≤ 0**, 9개 trials는 거래 0건

**근본 원인 (추정)**:
1. `BayesianSearchTuner._run_single_trial`에서 파라미터를 Optuna trial 객체에서 추출하지만, `build_tuning_config`로 전달되지 않음
2. 또는 `build_tuning_config`의 병합 로직이 Bayesian Search에서 작동하지 않음
3. PHASE28-4 파라미터 전달 해결 작업(PHASE28-4_PARAM_PASSING_RESOLUTION.md)이 **실제로는 해결되지 않음**

**PHASE28-4 결과의 유효성**:
- ❌ **본 실행 결과는 무효**
- ❌ Bayesian Optimization 검증 불가
- ❌ AC5(10+ trials) 형식적 충족이지만 **실질적으로 실패**

---

## 📋 요약 (Executive Summary)
- **총 Trial 수**: 13개
- **유효 Trial** (거래 수 ≥5): 4개
- **양의 Sharpe Trial**: 0개
- **Sharpe Ratio 범위**: [-118.5175, 0.0000]
- **PnL 범위**: [-202.84, 0.00]

## 🏆 Top-4 Trials
| Rank | Sharpe | PnL | Trades | Win Rate | MaxDD | Period |
|------|--------|-----|--------|----------|-------|--------|
| 1 | -19.4773 | -202.84 | 6 | 33.33% | 202.84% | unknown |
| 2 | -26.4545 | -158.22 | 5 | 0.00% | 158.22% | unknown |
| 3 | -45.8204 | -161.55 | 5 | 0.00% | 161.55% | unknown |
| 4 | -118.5175 | -144.34 | 5 | 0.00% | 144.34% | unknown |

## 🔍 파라미터 경향 (Parameter Trends)
Top trials의 주요 파라미터 분포:

| Parameter | Min | Max | Mean | Median |
|-----------|-----|-----|------|--------|
| pnl | -202.84 | -144.34 | -166.74 | -159.88 |
| avg_win | 0.00 | 7.71 | 1.93 | 0.00 |
| pnl_pct | -0.34 | -0.29 | -0.32 | -0.32 |
| avg_lose | -54.57 | -28.87 | -36.85 | -31.98 |
| win_rate | 0.00 | 0.33 | 0.08 | 0.00 |
| win_count | 0.00 | 2.00 | 0.50 | 0.00 |
| lose_count | 4.00 | 5.00 | 4.75 | 5.00 |
| runtime_sec | 166.33 | 262.64 | 217.27 | 220.06 |
| trade_count | 5.00 | 6.00 | 5.25 | 5.00 |
| max_drawdown | 144.34 | 202.84 | 166.74 | 159.88 |
| sharpe_ratio | -118.52 | -19.48 | -52.57 | -36.14 |
| profit_factor | 0.00 | 0.07 | 0.02 | 0.00 |
| max_drawdown_duration_hours | 0.00 | 0.00 | 0.00 | 0.00 |

## 🔄 Random Search Round 1과 비교
- **Random Search**: 0 trials, Best Sharpe: 0.0000
- **Bayesian Search**: 13 trials, Best Sharpe: 0.0000

## 🚀 필수 수정 사항 및 다음 단계

### 즉시 수정 필요
1. **파라미터 전달 문제 재조사**: 
   - `BayesianSearchTuner._run_single_trial` 코드 검토
   - Optuna trial → `build_tuning_config` 파라미터 전달 경로 추적
   - Random Search와 비교하여 차이점 파악
   
2. **임시 해결책 고려**:
   - Bayesian Search가 수정될 때까지 Random Search 확장 사용
   - 또는 Grid Search로 전환하여 파라미터 전달 검증

3. **PHASE28-4 재실행**:
   - 파라미터 전달 수정 후 Bayesian Search Round 1 재실행
   - 최소 20+ trials로 확장하여 TPE 샘플러의 효과 확인

### 장기 목표 (수정 후)
1. **Local Grid Search (PHASE28-5)**: 파라미터 전달 검증 후 진행
2. **PAPER 검증**: Valid 후보 확보 후 실시간 검증
3. **앙상블 준비**: 다양한 레짐/구간에서 안정적인 후보 조합 설계

---

## 📌 결론
**PHASE28-4 Bayesian Search Round 1은 형식적으로 AC5(10+ trials)를 충족했으나, 파라미터 전달 실패로 인해 실질적으로는 실패**했습니다. 튜닝 인프라의 근본적인 문제가 해결되지 않았으며, 이를 우선 수정해야 다음 단계로 진행할 수 있습니다.

