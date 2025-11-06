# PR10 — A/B 비교 리포트 구조

## 개요
Baseline vs Tuned 앙상블 파라미터의 성능 비교를 위한 리포트 구조 및 경로 정의

## 1. 리포트 저장 경로

### 1.1 디렉토리 구조
```
logs/ab_comparison/
├── ensemble_baseline_vs_tuned_001/
│   ├── config/
│   │   ├── baseline_config.yml      # Baseline 설정
│   │   └── tuned_config.yml         # Tuned 설정
│   ├── metrics/
│   │   ├── baseline_metrics.json    # Baseline 메트릭
│   │   ├── tuned_metrics.json       # Tuned 메트릭
│   │   └── comparison.json          # 비교 결과
│   ├── charts/
│   │   ├── score_comparison.png     # 점수 비교 차트
│   │   ├── equity_curve.png         # 자산 곡선 비교
│   │   └── decision_distribution.png # 의사결정 분포
│   └── report.md                    # 최종 리포트 (마크다운)
```

### 1.2 파일 명명 규칙
```
logs/ab_comparison/
  {experiment_name}_{timestamp}/
    - experiment_name: baseline_vs_tuned, shadow_vs_canary 등
    - timestamp: YYYYMMDD_HHMMSS
```

---

## 2. 메트릭 JSON 구조

### 2.1 Baseline/Tuned 메트릭
```json
{
  "config_id": "baseline_20251106",
  "timestamp": "2025-11-06T13:00:00",
  "period": {
    "start": "2025-11-05T13:00:00",
    "end": "2025-11-06T13:00:00",
    "duration_hours": 24
  },
  "ensemble_params": {
    "alpha_winrate": 0.4,
    "beta_rr": 0.2,
    "gamma_sharpe": 0.2,
    "delta_confidence": 0.15,
    "epsilon_regime": 0.05,
    "min_trades": 20,
    "max_weight_per_strategy": 0.4
  },
  "performance": {
    "score_total": 65.2,
    "sharpe": 1.05,
    "mdd": -0.12,
    "winrate": 0.52,
    "profit_factor": 1.65,
    "total_trades": 95,
    "wins": 49,
    "losses": 46,
    "avg_win": 120.5,
    "avg_loss": -85.3,
    "total_profit": 5904.5,
    "total_loss": -3923.8,
    "net_profit": 1980.7
  },
  "decision_distribution": {
    "LONG": 42,
    "SHORT": 53,
    "FLAT": 0
  },
  "strategy_participation": {
    "scalping": 28,
    "daytrade": 35,
    "swing": 12,
    "trend": 8,
    "reversion": 7,
    "breakout": 5
  },
  "experience_scores": {
    "scalping": 0.75,
    "daytrade": 0.82,
    "swing": 0.68,
    "trend": 0.55,
    "reversion": 0.60,
    "breakout": 0.45
  }
}
```

### 2.2 Comparison JSON
```json
{
  "comparison_id": "baseline_vs_tuned_001",
  "timestamp": "2025-11-06T13:00:00",
  "period": {
    "start": "2025-11-05T13:00:00",
    "end": "2025-11-06T13:00:00",
    "duration_hours": 24
  },
  "baseline": {
    "config_id": "baseline_20251106",
    "score_total": 65.2,
    "sharpe": 1.05,
    "mdd": -0.12,
    "winrate": 0.52,
    "total_trades": 95
  },
  "tuned": {
    "config_id": "tuned_trial_0042",
    "score_total": 78.5,
    "sharpe": 1.25,
    "mdd": -0.08,
    "winrate": 0.58,
    "total_trades": 120
  },
  "delta": {
    "score_total": {
      "absolute": 13.3,
      "percent": 20.4,
      "direction": "improvement"
    },
    "sharpe": {
      "absolute": 0.20,
      "percent": 19.0,
      "direction": "improvement"
    },
    "mdd": {
      "absolute": 0.04,
      "percent": -33.3,
      "direction": "improvement"
    },
    "winrate": {
      "absolute": 0.06,
      "percent": 11.5,
      "direction": "improvement"
    },
    "total_trades": {
      "absolute": 25,
      "percent": 26.3,
      "direction": "increase"
    }
  },
  "acceptance_criteria": {
    "score_total_improvement": {
      "target": 12.0,
      "actual": 20.4,
      "passed": true
    },
    "sharpe_improvement": {
      "target": 10.0,
      "actual": 19.0,
      "passed": true
    },
    "mdd_increase_limit": {
      "target": 1.0,
      "actual": -4.0,
      "passed": true
    },
    "min_trades": {
      "target": 60,
      "actual": 120,
      "passed": true
    },
    "winrate_drop_limit": {
      "target": -0.5,
      "actual": 6.0,
      "passed": true
    }
  },
  "verdict": "PASS",
  "recommendation": "Proceed to Shadow Mode"
}
```

---

## 3. 리포트 마크다운 구조

### 3.1 report.md 템플릿
```markdown
# A/B Comparison Report: Baseline vs Tuned

## Summary
- **Comparison ID**: baseline_vs_tuned_001
- **Period**: 2025-11-05 13:00 ~ 2025-11-06 13:00 (24 hours)
- **Verdict**: ✅ PASS
- **Recommendation**: Proceed to Shadow Mode

---

## Performance Comparison

### Primary Metrics
| Metric | Baseline | Tuned | Delta | Status |
|--------|----------|-------|-------|--------|
| **Score Total** | 65.2 | 78.5 | +20.4% | ✅ PASS |
| **Sharpe Ratio** | 1.05 | 1.25 | +19.0% | ✅ PASS |
| **MDD** | -12.0% | -8.0% | +4.0%p | ✅ PASS |
| **Winrate** | 52.0% | 58.0% | +6.0%p | ✅ PASS |
| **Total Trades** | 95 | 120 | +26.3% | ✅ PASS |

### Secondary Metrics
| Metric | Baseline | Tuned | Delta |
|--------|----------|-------|-------|
| Profit Factor | 1.65 | 1.85 | +12.1% |
| Avg Win | $120.5 | $135.2 | +12.2% |
| Avg Loss | $-85.3 | $-78.1 | +8.4% |
| Net Profit | $1,980.7 | $3,245.8 | +63.9% |

---

## Acceptance Criteria

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| Score Total Improvement | ≥12% | 20.4% | ✅ PASS |
| Sharpe Improvement | ≥10% | 19.0% | ✅ PASS |
| MDD Increase Limit | ≤1%p | -4.0%p | ✅ PASS |
| Min Trades | ≥60 | 120 | ✅ PASS |
| Winrate Drop Limit | ≤-0.5%p | +6.0%p | ✅ PASS |

**Overall**: ✅ All criteria passed

---

## Configuration Changes

### Ensemble Parameters
| Parameter | Baseline | Tuned | Change |
|-----------|----------|-------|--------|
| alpha_winrate | 0.40 | 0.45 | +12.5% |
| beta_rr | 0.20 | 0.18 | -10.0% |
| gamma_sharpe | 0.20 | 0.22 | +10.0% |
| delta_confidence | 0.15 | 0.12 | -20.0% |
| epsilon_regime | 0.05 | 0.03 | -40.0% |
| min_trades | 20 | 25 | +25.0% |
| max_weight_per_strategy | 0.40 | 0.38 | -5.0% |

---

## Decision Distribution

### Baseline
- LONG: 42 (44.2%)
- SHORT: 53 (55.8%)
- FLAT: 0 (0.0%)

### Tuned
- LONG: 48 (40.0%)
- SHORT: 72 (60.0%)
- FLAT: 0 (0.0%)

---

## Strategy Participation

### Baseline
| Strategy | Count | Percentage |
|----------|-------|------------|
| daytrade | 35 | 36.8% |
| scalping | 28 | 29.5% |
| swing | 12 | 12.6% |
| trend | 8 | 8.4% |
| reversion | 7 | 7.4% |
| breakout | 5 | 5.3% |

### Tuned
| Strategy | Count | Percentage |
|----------|-------|------------|
| daytrade | 42 | 35.0% |
| scalping | 35 | 29.2% |
| swing | 18 | 15.0% |
| trend | 10 | 8.3% |
| reversion | 9 | 7.5% |
| breakout | 6 | 5.0% |

---

## Experience Scores

| Strategy | Baseline | Tuned | Change |
|----------|----------|-------|--------|
| daytrade | 0.82 | 0.85 | +3.7% |
| scalping | 0.75 | 0.78 | +4.0% |
| swing | 0.68 | 0.72 | +5.9% |
| trend | 0.55 | 0.58 | +5.5% |
| reversion | 0.60 | 0.63 | +5.0% |
| breakout | 0.45 | 0.48 | +6.7% |

---

## Charts

### Score Comparison
![Score Comparison](charts/score_comparison.png)

### Equity Curve
![Equity Curve](charts/equity_curve.png)

### Decision Distribution
![Decision Distribution](charts/decision_distribution.png)

---

## Recommendation

✅ **Proceed to Shadow Mode**

**Rationale**:
- All acceptance criteria passed
- Score Total improved by 20.4% (target: ≥12%)
- Sharpe Ratio improved by 19.0% (target: ≥10%)
- MDD improved by 4.0%p (better than baseline)
- Winrate improved by 6.0%p (no drop)
- Total trades increased by 26.3% (within acceptable range)

**Next Steps**:
1. Deploy tuned parameters in Shadow Mode (8 hours)
2. Monitor guardrails (MDD delta, min trades, volatility)
3. If Shadow Mode passes, proceed to Canary 10%

---

## Appendix

### Baseline Config
```yaml
ensemble:
  alpha_winrate: 0.4
  beta_rr: 0.2
  gamma_sharpe: 0.2
  delta_confidence: 0.15
  epsilon_regime: 0.05
  experience:
    min_trades: 20
  max_weight_per_strategy: 0.4
```

### Tuned Config
```yaml
ensemble:
  alpha_winrate: 0.45
  beta_rr: 0.18
  gamma_sharpe: 0.22
  delta_confidence: 0.12
  epsilon_regime: 0.03
  experience:
    min_trades: 25
  max_weight_per_strategy: 0.38
```

---

**Generated**: 2025-11-06 13:00:00
**Comparison ID**: baseline_vs_tuned_001
```

---

## 4. 리포트 생성 스크립트

### 4.1 스크립트 경로
```
scripts/analysis/generate_ab_report.py
```

### 4.2 사용법
```bash
python scripts/analysis/generate_ab_report.py \
  --baseline logs/trial_baseline.json \
  --tuned logs/trial_tuned.json \
  --output logs/ab_comparison/baseline_vs_tuned_001/
```

### 4.3 주요 기능
- JSON 메트릭 로드
- Delta 계산
- 수용 기준 체크
- 마크다운 리포트 생성
- 차트 생성 (matplotlib)

---

## 5. 차트 생성

### 5.1 Score Comparison (막대 차트)
```python
import matplotlib.pyplot as plt

def generate_score_comparison(baseline, tuned, output_path):
    metrics = ['Score Total', 'Sharpe', 'Winrate']
    baseline_values = [baseline['score_total'], baseline['sharpe'], baseline['winrate']]
    tuned_values = [tuned['score_total'], tuned['sharpe'], tuned['winrate']]
    
    x = range(len(metrics))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - width/2 for i in x], baseline_values, width, label='Baseline')
    ax.bar([i + width/2 for i in x], tuned_values, width, label='Tuned')
    
    ax.set_xlabel('Metrics')
    ax.set_ylabel('Value')
    ax.set_title('Performance Comparison: Baseline vs Tuned')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
```

### 5.2 Equity Curve (선 차트)
```python
def generate_equity_curve(baseline_trades, tuned_trades, output_path):
    # 누적 PnL 계산
    baseline_cumulative = calculate_cumulative_pnl(baseline_trades)
    tuned_cumulative = calculate_cumulative_pnl(tuned_trades)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(baseline_cumulative, label='Baseline', linewidth=2)
    ax.plot(tuned_cumulative, label='Tuned', linewidth=2)
    
    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Cumulative PnL (USDT)')
    ax.set_title('Equity Curve Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
```

### 5.3 Decision Distribution (파이 차트)
```python
def generate_decision_distribution(baseline, tuned, output_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Baseline
    labels = ['LONG', 'SHORT', 'FLAT']
    sizes_baseline = [
        baseline['decision_distribution']['LONG'],
        baseline['decision_distribution']['SHORT'],
        baseline['decision_distribution']['FLAT']
    ]
    ax1.pie(sizes_baseline, labels=labels, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Baseline Decision Distribution')
    
    # Tuned
    sizes_tuned = [
        tuned['decision_distribution']['LONG'],
        tuned['decision_distribution']['SHORT'],
        tuned['decision_distribution']['FLAT']
    ]
    ax2.pie(sizes_tuned, labels=labels, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Tuned Decision Distribution')
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
```

---

## 6. 자동화 워크플로우

### 6.1 24시간 평가 후 자동 리포트 생성
```python
def auto_generate_report_after_24h():
    """
    24시간 페이퍼 평가 후 자동으로 A/B 리포트 생성
    """
    # 1. Baseline 메트릭 로드
    baseline_metrics = load_metrics("logs/trial_baseline.json")
    
    # 2. Tuned 메트릭 로드
    tuned_metrics = load_metrics("logs/trial_tuned.json")
    
    # 3. 비교 분석
    comparison = compare_metrics(baseline_metrics, tuned_metrics)
    
    # 4. 수용 기준 체크
    acceptance = check_acceptance_criteria(comparison)
    
    # 5. 리포트 생성
    report_dir = f"logs/ab_comparison/baseline_vs_tuned_{timestamp}/"
    os.makedirs(report_dir, exist_ok=True)
    
    # 6. JSON 저장
    save_json(f"{report_dir}/metrics/baseline_metrics.json", baseline_metrics)
    save_json(f"{report_dir}/metrics/tuned_metrics.json", tuned_metrics)
    save_json(f"{report_dir}/metrics/comparison.json", comparison)
    
    # 7. 차트 생성
    generate_score_comparison(baseline_metrics, tuned_metrics, f"{report_dir}/charts/score_comparison.png")
    generate_equity_curve(baseline_trades, tuned_trades, f"{report_dir}/charts/equity_curve.png")
    generate_decision_distribution(baseline_metrics, tuned_metrics, f"{report_dir}/charts/decision_distribution.png")
    
    # 8. 마크다운 리포트 생성
    generate_markdown_report(comparison, acceptance, f"{report_dir}/report.md")
    
    # 9. 텔레그램 알림
    send_telegram_notification(f"✅ A/B 리포트 생성 완료: {report_dir}")
    
    return report_dir
```

---

## 7. 다음 단계

### PR10 (현재)
- [x] Experience Score 구현
- [x] 가중치 클램핑 구현
- [x] 튜닝 파라미터 설계
- [x] A/B 비교 리포트 경로 정의 ✅
- [ ] 24시간 페이퍼 평가 (진행 중)

### PR13 (향후)
- [ ] A/B 리포트 생성 스크립트 구현
- [ ] 차트 생성 로직 구현
- [ ] 자동화 워크플로우 구현

---

## 참고 문서
- `docs/PHASE6/PR10_MASTER_PLAN.md`: PR10 마스터 플랜
- `docs/PHASE6/PR10_TUNING_DESIGN.md`: 튜닝 설계 문서
- `docs/PHASE6/PR13_MASTER_PLAN.md`: PR13 마스터 플랜
