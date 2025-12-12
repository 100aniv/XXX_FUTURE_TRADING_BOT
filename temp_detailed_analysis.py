import json
import os

# Scenario A 결과 로드
scenario_a_file = 'reports/backtest/phase29_2b/btc5m_baseline_v3_week_scenario_a_summary.json'

if os.path.exists(scenario_a_file):
    with open(scenario_a_file) as f:
        data = json.load(f)
    
    print("=" * 60)
    print("PHASE29-2B Scenario A 백테스트 결과 분석")
    print("=" * 60)
    print(f"Run ID: {data['run_id']}")
    print(f"기간: {data['timestamp']} ~ {data['end_timestamp']}")
    print()
    
    print("[신호 생성]")
    totals = data['totals']
    print(f"  - 전략 호출: {totals['strategy_signals_total']}회")
    print(f"  - 신호 TRUE: {totals['strategy_signals_true']}건")
    print(f"  - Long: {totals['long_signals']}건, Short: {totals['short_signals']}건")
    print(f"  - Regime (Trend/Range): {totals['regime_trend']}/{totals['regime_range']}")
    print()
    
    print("[Guard 차단]")
    btc_data = data['symbols']['BTCUSDT']
    print(f"  - 총 차단: {totals['guard_blocks_total']}건")
    for guard_type, count in btc_data['guard_blocks'].items():
        print(f"    • {guard_type}: {count}건")
    print()
    
    print("[주문 & 거래]")
    print(f"  - 주문 제출: {totals['orders_submitted']}건")
    print()
    
    # 신호율 계산
    signal_rate = (totals['strategy_signals_true'] / totals['strategy_signals_total']) * 100
    guard_block_rate = (totals['guard_blocks_total'] / totals['strategy_signals_true']) * 100 if totals['strategy_signals_true'] > 0 else 0
    order_conversion_rate = (totals['orders_submitted'] / totals['strategy_signals_true']) * 100 if totals['strategy_signals_true'] > 0 else 0
    
    print("[전환율 분석]")
    print(f"  - 신호 생성율: {signal_rate:.2f}% ({totals['strategy_signals_true']}/{totals['strategy_signals_total']})")
    print(f"  - Guard 차단율: {guard_block_rate:.2f}% ({totals['guard_blocks_total']}/{totals['strategy_signals_true']})")
    print(f"  - 주문 전환율: {order_conversion_rate:.2f}% ({totals['orders_submitted']}/{totals['strategy_signals_true']})")
    print()
    
    print("[평가]")
    target_min = 20
    target_max = 60
    actual_orders = totals['orders_submitted']
    
    if actual_orders < target_min:
        print(f"  ⚠️ FAIL: 주문 {actual_orders}건 < 목표 {target_min}~{target_max}건")
        print(f"  → Scenario A+로 추가 완화 필요")
    elif actual_orders <= target_max:
        print(f"  ✅ PASS: 주문 {actual_orders}건이 목표 범위 내")
    else:
        print(f"  ⚠️ WARNING: 주문 {actual_orders}건 > 목표 {target_max}건 (Overtrading 위험)")
    
else:
    print(f"ERROR: {scenario_a_file} 파일을 찾을 수 없습니다.")
