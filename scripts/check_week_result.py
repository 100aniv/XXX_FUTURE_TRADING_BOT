import json

with open('reports/backtest/phase29_2b/btc5m_baseline_v3_week_scenario_a_summary.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'Trades: {data.get("summary_trades", 0)}')
print(f'Signal True: {data.get("signal_true", 0)}')
print(f'Signal False: {data.get("signal_false", 0)}')
print(f'Win Rate: {data.get("summary_win_rate", 0):.2f}%')
print(f'Max DD: {data.get("summary_max_drawdown_pct", 0):.2f}%')
print(f'Final Equity: ${data.get("summary_final_equity", 0):,.2f}')
