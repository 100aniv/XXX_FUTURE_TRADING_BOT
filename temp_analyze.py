import json

with open('reports/backtest/phase29_2b/btc5m_baseline_v3_week_scenario_a_summary.json') as f:
    data = json.load(f)

print(f"Run ID: {data['run_id']}")
print(f"신호 TRUE: {data['totals']['strategy_signals_true']}")
print(f"주문 제출: {data['totals']['orders_submitted']}")
print(f"Guard 차단: {data['totals']['guard_blocks_total']}")
print(f"Long: {data['totals']['long_signals']}, Short: {data['totals']['short_signals']}")
print(f"Timestamp: {data['timestamp']}")
print(f"End Timestamp: {data['end_timestamp']}")
