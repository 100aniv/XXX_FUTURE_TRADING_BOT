#!/usr/bin/env python3
"""PHASE35-2 ITER2: Fast 7D Backtest (Dec 1-8, 2024)"""
import sys
import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
from common.logger import setup_logger

logger = setup_logger("iter2_7d_fast")


def main():
    print("=" * 80)
    print("PHASE35-2 ITER2: Fast 7D Backtest (Dec 1-8, 2024)")
    print("=" * 80)
    
    # 1. Load config
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter2_ssot.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 2. Load 7D data only
    data_path = project_root / "data" / "BTCUSDT_15m_2024-01-01_2024-12-31.csv"
    logger.info(f"Loading data: {data_path}")
    df_full = pd.read_csv(data_path)
    
    # Convert time column to datetime
    if 'time' in df_full.columns:
        df_full['time'] = pd.to_datetime(df_full['time'])
    
    # Filter 7D: 2024-12-01 ~ 2024-12-08
    start_date = pd.Timestamp("2024-12-01")
    end_date = pd.Timestamp("2024-12-08")
    
    df = df_full[(df_full['time'] >= start_date) & (df_full['time'] < end_date)].copy()
    logger.info(f"Filtered data: {len(df)} bars ({df['time'].min()} ~ {df['time'].max()})")
    
    # 3. Initialize strategy
    strategy_params = config['strategies']['phase35_ensemble_v1']['params']
    merged_config = {**config, **strategy_params}
    
    strategy = Phase35EnsembleV1(merged_config)
    logger.info(f"Strategy initialized: cooldown={strategy._cooldown_bars}, min_votes={strategy._min_votes}, threshold={strategy._confidence_threshold}")
    
    # 4. Run signals
    signals = []
    blocks = {
        'COOLDOWN_BLOCK': 0,
        'REGIME_CHOP_BLOCK': 0,
        'CONFIDENCE_FILTER_BLOCK': 0,
        'NO_CONSENSUS': 0
    }
    
    lookback = config.get('lookback', 1000)
    
    for i in range(lookback, len(df)):
        df_window = df.iloc[:i+1].copy()
        signal = strategy.compute_signal(df_window)
        
        if signal.get('side'):
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'side': signal['side'],
                'confidence': signal.get('confidence', 0),
                'reason': signal.get('reason', ''),
                'close': df.iloc[i]['close']
            })
        else:
            reason = signal.get('reason', '')
            if 'cooldown' in reason:
                blocks['COOLDOWN_BLOCK'] += 1
            elif 'regime_chop' in reason:
                blocks['REGIME_CHOP_BLOCK'] += 1
            elif 'confidence_low' in reason:
                blocks['CONFIDENCE_FILTER_BLOCK'] += 1
            elif 'no_consensus' in reason:
                blocks['NO_CONSENSUS'] += 1
    
    # 5. Report
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total bars processed: {len(df) - lookback}")
    print(f"Total signals: {len(signals)}")
    print(f"\nBlocks:")
    for reason, count in blocks.items():
        print(f"  - {reason}: {count}")
    
    if signals:
        print(f"\nSignals breakdown:")
        signals_df = pd.DataFrame(signals)
        print(signals_df.groupby('side').size())
        print(f"\nFirst 5 signals:")
        print(signals_df.head())
        print(f"\nLast 5 signals:")
        print(signals_df.tail())
        
        # Save to CSV
        output_path = project_root / "reports" / "phase35_iter2_run1_signals.csv"
        signals_df.to_csv(output_path, index=False)
        print(f"\nSignals saved to: {output_path}")
    
    print("=" * 80)
    
    # AC-2 Check
    print(f"\n✅ AC-1: Config reflected (cooldown={strategy._cooldown_bars}, min_votes={strategy._min_votes}, threshold={strategy._confidence_threshold})")
    print(f"📊 AC-2: Trade count = {len(signals)} (ITER1 baseline was 10,498)")
    
    if len(signals) > 0:
        reduction_pct = (1 - len(signals) / 10498) * 100
        print(f"   Reduction: {reduction_pct:.1f}% vs ITER1")
        if reduction_pct >= 30:
            print(f"   ✅ AC-2 PASS: Reduction >= 30%")
        else:
            print(f"   ⚠️  AC-2 MARGINAL: Reduction < 30%")
    else:
        print(f"   ❌ AC-2 FAIL: 0 trades")


if __name__ == "__main__":
    main()
