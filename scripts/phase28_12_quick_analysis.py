#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PHASE28-12: Quick Analysis - Profile E/F/G"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "reports/backtest/phase28_12"

def analyze_profile(profile_name: str):
    """프로파일 결과 분석"""
    summary_path = REPORT_DIR / f"profile_{profile_name}_summary.json"
    
    if not summary_path.exists():
        print(f"⚠️ Profile {profile_name.upper()}: Summary 파일 없음")
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    totals = data['totals']
    signals = totals['strategy_signals_true']
    orders = totals['orders_submitted']
    conversion = (orders / signals * 100) if signals > 0 else 0
    
    guard_blocks = data['symbols']['BTCUSDT'].get('guard_blocks', {})
    
    return {
        'signals': signals,
        'orders': orders,
        'conversion': conversion,
        'guard_blocks': guard_blocks
    }

def main():
    print("=" * 70)
    print("PHASE28-12: Profile E/F/G Quick Analysis")
    print("=" * 70)
    print()
    
    for profile in ['e', 'f', 'g']:
        result = analyze_profile(profile)
        if result:
            print(f"📊 Profile {profile.upper()}:")
            print(f"   Signals: {result['signals']}")
            print(f"   Orders: {result['orders']}")
            print(f"   Conversion Rate: {result['conversion']:.2f}%")
            print(f"   Guard Blocks: {result['guard_blocks']}")
            print()

if __name__ == '__main__':
    main()
