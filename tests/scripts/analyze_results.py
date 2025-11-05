#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""백테스트 로그 분석"""
import re
from collections import defaultdict

log_file = "logs/application/2025-10-23.log"

# 거래 데이터 수집
trades = {
    'tp1': [], 'tp2': [], 'trailing_sl': [], 'sl': [], 'tp': []
}
exit_counts = defaultdict(int)
exit_pnls = defaultdict(list)
symbol_stats = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
strategy_stats = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})

print("=" * 80)
print("📊 백테스트 로그 분석")
print("=" * 80)

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        # TP1/TP2 청산
        if "TP1:" in line or "TP2:" in line:
            match = re.search(r'(TP[12]).*PnL: \$([0-9.-]+)', line)
            if match:
                reason, pnl = match.groups()
                exit_counts[reason] += 1
                exit_pnls[reason].append(float(pnl))
        
        # 전체 청산
        elif "🔚" in line:
            # 예: 🔚 [1] SL: LONG BNBUSDT @ 771.93 (Entry: 775.59) | PnL: $-11.80
            match = re.search(r'🔚.*\] ([\w_]+): (LONG|SHORT) (\w+) @ ([0-9.]+) \(Entry: ([0-9.]+)\) \| PnL: \$([0-9.-]+)', line)
            if match:
                reason, side, symbol, exit_p, entry_p, pnl = match.groups()
                pnl = float(pnl)
                
                exit_counts[reason] += 1
                exit_pnls[reason].append(pnl)
                
                symbol_stats[symbol]['count'] += 1
                symbol_stats[symbol]['pnl'] += pnl
                if pnl > 0:
                    symbol_stats[symbol]['wins'] += 1
        
        # 전략별 진입
        elif "✅" in line and ("LONG @" in line or "SHORT @" in line):
            # 포트폴리오 로그에서 전략 추출
            prev_line_match = None

total_trades = sum(exit_counts.values())
total_pnl = sum(sum(pnls) for pnls in exit_pnls.values())

print(f"\n총 청산: {total_trades}건")
print(f"총 PnL: ${total_pnl:,.2f}")

print("\n" + "=" * 80)
print("📈 청산 사유별 분석")
print("=" * 80)
for reason in sorted(exit_counts.keys()):
    count = exit_counts[reason]
    pnls = exit_pnls[reason]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    win_rate = wins / count * 100 if count > 0 else 0
    
    print(f"{reason:15s}: {count:4d}건 | 승률 {win_rate:5.1f}% | Avg ${avg_pnl:8.2f} | Total ${total:10,.2f}")

print("\n" + "=" * 80)
print("💰 심볼별 분석")
print("=" * 80)
for symbol in sorted(symbol_stats.keys(), key=lambda x: symbol_stats[x]['pnl'], reverse=True):
    stats = symbol_stats[symbol]
    win_rate = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
    avg_pnl = stats['pnl'] / stats['count'] if stats['count'] > 0 else 0
    print(f"{symbol:10s}: {stats['count']:4d}건 | 승률 {win_rate:5.1f}% | Avg ${avg_pnl:8.2f} | Total ${stats['pnl']:10,.2f}")

print("\n" + "=" * 80)
print("🎯 TP 분할 효과")
print("=" * 80)
tp1_count = exit_counts.get('TP1', 0)
tp2_count = exit_counts.get('TP2', 0)
trail_count = exit_counts.get('TRAILING_SL', 0)
tp_count = exit_counts.get('TP', 0)

print(f"TP1 청산 (30%): {tp1_count}건")
print(f"TP2 청산 (40%): {tp2_count}건")
print(f"트레일링 청산: {trail_count}건")
print(f"단일 TP 청산: {tp_count}건")

if tp1_count + tp2_count > 0:
    print(f"\n✅ TP 분할 시스템 작동 중!")
    print(f"   분할 진행률: {tp1_count}건 → {tp2_count}건 ({tp2_count/tp1_count*100:.1f}%)" if tp1_count > 0 else "")
else:
    print("\n⚠️  TP 분할 미작동 (TP1/TP2 기록 없음)")

print("\n" + "=" * 80)
