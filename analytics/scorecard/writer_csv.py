#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scorecard CSV Writer (PHASE8)
==============================
Scorecard를 CSV 형식으로 저장
"""
import csv
from pathlib import Path
from typing import Dict, Any


def save_scorecard_csv(scorecard: Dict[str, Any], output_dir: Path) -> Path:
    """
    Scorecard를 CSV로 저장
    
    Args:
        scorecard: scorecard 데이터
        output_dir: 출력 디렉토리
    
    Returns:
        Path: 저장된 CSV 파일 경로
    
    Examples:
        >>> scorecard = {
        ...     'strategy': 'scalping',
        ...     'winrate': 45.5,
        ...     'profit_factor': 1.25,
        ... }
        >>> output_dir = Path('artifacts/backtest_clean/20251114_135030_a7f3/')
        >>> path = save_scorecard_csv(scorecard, output_dir)
    """
    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV 파일 경로
    csv_path = output_dir / "scorecard.csv"
    
    # CSV 작성
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # 헤더
        writer.writerow(['Metric', 'Value'])
        
        # 데이터
        writer.writerow(['Strategy', scorecard['strategy']])
        writer.writerow(['Symbol', scorecard['symbol']])
        writer.writerow(['Timeframe', scorecard['timeframe']])
        writer.writerow(['Trades Closed', scorecard['trades_closed']])
        writer.writerow(['Winrate (%)', scorecard['winrate']])
        writer.writerow(['Profit Factor', scorecard['profit_factor']])
        writer.writerow(['Max Drawdown (%)', scorecard['max_drawdown']])
        writer.writerow(['Loss > 8%', scorecard['loss_over_8pct']])
        writer.writerow(['TP Hit (%)', scorecard['tp_hit']])
        if 'sharpe_ratio' in scorecard:
            writer.writerow(['Sharpe Ratio', scorecard['sharpe_ratio']])
    
    return csv_path
