#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34: Gate Statistics Analyzer
==================================
Analyze decision gates from backtest summary files to determine why
parameter tuning has no effect on trade quality (WR/PF).

Purpose: Extract gate-level statistics from existing backtest results
         to confirm that parameters are (or aren't) affecting decision flow.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd


def load_summary(summary_path: str) -> Dict[str, Any]:
    """Load summary JSON file."""
    with open(summary_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_config_set(configs: List[str], base_dir: str) -> pd.DataFrame:
    """
    Analyze a set of configs to compare gate statistics.
    
    Args:
        configs: List of config names (e.g., ['p34_c20_h2_w50', ...])
        base_dir: Base directory containing summary files
    
    Returns:
        DataFrame with comparative statistics
    """
    results = []
    
    for config in configs:
        summary_path = os.path.join(base_dir, f"{config}_summary.json")
        
        if not os.path.exists(summary_path):
            print(f"⚠️  Summary not found: {summary_path}")
            continue
        
        data = load_summary(summary_path)
        metrics = data.get('metrics', {})
        
        # Extract parameter values from config name
        # Format: p34_c{conf}_h{hyst}_w{weight}
        parts = config.split('_')
        conf = float(parts[1][1:]) / 100  # c20 -> 0.20
        hyst = int(parts[2][1:])          # h2 -> 2
        weight = float(parts[3][1:]) / 100 # w50 -> 0.50
        
        results.append({
            'config': config,
            'confidence': conf,
            'hysteresis': hyst,
            'mtf_weight': weight,
            'trades': metrics.get('total_trades', 0),
            'winrate': metrics.get('winrate', 0),
            'pf': metrics.get('pf', 0),
            'roi': metrics.get('roi', 0),
            'mdd': metrics.get('mdd', 0),
            'total_score': data.get('total_score', 0)
        })
    
    return pd.DataFrame(results)


def compute_sensitivity_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute parameter sensitivity matrix.
    
    Returns:
        dict: {
            'confidence_effect': {...},
            'hysteresis_effect': {...},
            'mtf_weight_effect': {...}
        }
    """
    sensitivity = {}
    
    # Group by each parameter and compute variance
    for param in ['confidence', 'hysteresis', 'mtf_weight']:
        grouped = df.groupby(param).agg({
            'trades': ['mean', 'std'],
            'winrate': ['mean', 'std'],
            'pf': ['mean', 'std']
        })
        
        sensitivity[f"{param}_effect"] = {
            'trades_variance': grouped['trades']['std'].mean(),
            'winrate_variance': grouped['winrate']['std'].mean(),
            'pf_variance': grouped['pf']['std'].mean(),
            'trades_range': grouped['trades']['mean'].max() - grouped['trades']['mean'].min(),
            'winrate_range': grouped['winrate']['mean'].max() - grouped['winrate']['mean'].min(),
            'pf_range': grouped['pf']['mean'].max() - grouped['pf']['mean'].min()
        }
    
    return sensitivity


def main():
    """Main analysis function."""
    print("=" * 60)
    print("PHASE34: Gate Statistics Analysis")
    print("=" * 60)
    
    base_dir = "reports/backtest/phase34/sweep"
    
    # Select representative configs for detailed comparison
    # Low, Mid, High for each parameter dimension
    representative_configs = [
        # Low confidence (0.20)
        'p34_c20_h2_w50',
        'p34_c20_h3_w50',
        'p34_c20_h5_w60',
        # Mid confidence (0.25)
        'p34_c25_h2_w50',
        'p34_c25_h3_w50',
        'p34_c25_h5_w60',
        # High confidence (0.30)
        'p34_c30_h2_w50',
        'p34_c30_h3_w50',
        'p34_c30_h5_w60'
    ]
    
    print(f"\n📊 Analyzing {len(representative_configs)} representative configs...")
    df = analyze_config_set(representative_configs, base_dir)
    
    if df.empty:
        print("❌ No data loaded. Check summary files exist.")
        return
    
    print("\n" + "=" * 60)
    print("COMPARATIVE STATISTICS")
    print("=" * 60)
    print(df.to_string(index=False))
    
    # Compute sensitivity
    print("\n" + "=" * 60)
    print("PARAMETER SENSITIVITY ANALYSIS")
    print("=" * 60)
    
    sensitivity = compute_sensitivity_matrix(df)
    
    for param, stats in sensitivity.items():
        print(f"\n{param.upper().replace('_', ' ')}:")
        print(f"  Trades variance: {stats['trades_variance']:.2f}")
        print(f"  Trades range: {stats['trades_range']:.0f}")
        print(f"  WinRate variance: {stats['winrate_variance']:.4f}%")
        print(f"  WinRate range: {stats['winrate_range']:.4f}%")
        print(f"  PF variance: {stats['pf_variance']:.4f}")
        print(f"  PF range: {stats['pf_range']:.4f}")
    
    # Conclusion
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    
    # Check if WR/PF variance is near zero
    wr_vars = [sensitivity[p]['winrate_variance'] for p in sensitivity.keys()]
    pf_vars = [sensitivity[p]['pf_variance'] for p in sensitivity.keys()]
    
    avg_wr_var = sum(wr_vars) / len(wr_vars)
    avg_pf_var = sum(pf_vars) / len(pf_vars)
    
    if avg_wr_var < 0.1 and avg_pf_var < 0.01:
        print("❌ PARAMETER TUNING INEFFECTIVE:")
        print("   - WinRate variance < 0.1% (near-zero)")
        print("   - PF variance < 0.01 (near-zero)")
        print("   → Parameters affect entry FREQUENCY, not entry QUALITY")
        print("   → Strategy signal logic redesign required (PHASE35)")
    else:
        print("⚠️  PARAMETER TUNING PARTIALLY EFFECTIVE:")
        print(f"   - WinRate variance: {avg_wr_var:.4f}%")
        print(f"   - PF variance: {avg_pf_var:.4f}")
        print("   → Further investigation needed")
    
    # Save results
    output_path = "reports/backtest/phase34/sweep/gate_statistics_analysis.json"
    tuning_effective = avg_wr_var >= 0.1 or avg_pf_var >= 0.01
    results = {
        'analyzed_configs': representative_configs,
        'comparative_stats': df.to_dict(orient='records'),
        'sensitivity_matrix': sensitivity,
        'conclusion': {
            'avg_wr_variance': float(avg_wr_var),
            'avg_pf_variance': float(avg_pf_var),
            'tuning_effective': int(tuning_effective)  # Convert bool to int for JSON
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved: {output_path}")


if __name__ == "__main__":
    main()
