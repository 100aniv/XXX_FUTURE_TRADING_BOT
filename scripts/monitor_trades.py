#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick trade monitor"""
import sys
from datetime import datetime
from trade_counter_v2 import count_paper_trades, get_paper_trade_stats

strategy_id = sys.argv[1] if len(sys.argv) > 1 else None

count = count_paper_trades(strategy_id=strategy_id)
stats = get_paper_trade_stats(strategy_id=strategy_id)

now = datetime.now().strftime("%H:%M:%S")
print(f"[{now}] Trades: {count} (LONG: {stats['long']}, SHORT: {stats['short']}, PnL: ${stats['pnl_total']:.2f})")
