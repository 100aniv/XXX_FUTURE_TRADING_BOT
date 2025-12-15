#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER3: Simplified 7D Backtest Runner
================================================
최소 의존성으로 7D 백테스트 직접 실행
"""
import sys
import yaml
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from strategies.phase35_ensemble_v1 import Phase35EnsembleV1

logger = setup_logger("iter3_simple")

def main(run_number=1):
    logger.info(f"ITER3 Simple Run #{run_number} START")
    
    # Config 로드
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Strategy params merge
    strategy_params = config.get('strategies', {}).get('phase35_ensemble_v1', {}).get('params', {})
    
    def deep_merge(base, custom):
        merged = base.copy()
        for key, value in custom.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    merged_config = deep_merge(config, strategy_params)
    merged_config['mode'] = 'backtest'
    
    # 전략 초기화
    strategy = Phase35EnsembleV1(merged_config)
    
    # 데이터 로드
    data_path = project_root / "data" / "BTCUSDT_15m_2024-01-01_2024-12-31.csv"
    df = pd.read_csv(data_path)
    df['time'] = pd.to_datetime(df['time'])
    
    # 7D 필터
    df_7d = df[(df['time'] >= '2024-12-01') & (df['time'] < '2024-12-08')].copy()
    logger.info(f"7D data: {len(df_7d)} bars")
    
    # 신호 생성 (간단한 순회)
    signals = []
    lookback = 200
    
    for i in range(lookback, len(df_7d)):
        window = df_7d.iloc[:i+1]
        signal = strategy.compute_signal(window)
        
        if signal.get('side'):
            signals.append({
                'time': window.iloc[-1]['time'],
                'side': signal['side'],
                'entry': signal.get('entry', 0),
                'confidence': signal.get('confidence', 0),
            })
    
    # Summary 생성
    summary = {
        'run_number': run_number,
        'timestamp': datetime.now().isoformat(),
        'trades': len(signals),
        'config_hash': 'iter3',
        'git_commit': 'iter3',
        'seed': 42,
    }
    
    # 저장
    summary_dir = project_root / "reports" / "backtest" / "phase35"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"iter3_run{run_number}_summary.json"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Run #{run_number} Complete")
    logger.info(f"   Trades: {len(signals)}")
    logger.info(f"   Summary: {summary_path}")
    
    return 0

if __name__ == "__main__":
    run_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sys.exit(main(run_num))
