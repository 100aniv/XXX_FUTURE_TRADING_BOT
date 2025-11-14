#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scorecard Metrics (PHASE8)
===========================
백테스트 성과 지표 계산

필수 지표 6개:
1. trades_closed - 총 거래 수
2. winrate - 승률
3. profit_factor - 총이익/총손실
4. max_drawdown - 최대 손실
5. loss_over_8pct - >8% 손실 횟수
6. tp_hit - TP 도달률
"""
import pandas as pd
from typing import Dict, Any, List


def calculate_metrics(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    거래 목록에서 지표 계산
    
    Args:
        trades: 거래 목록 (각 거래는 dict)
            필수 키: 'pnl_pct', 'status', 'exit_reason'
    
    Returns:
        Dict[str, float]: 6가지 지표
        {
            'trades_closed': int,
            'winrate': float,
            'profit_factor': float,
            'max_drawdown': float,
            'loss_over_8pct': int,
            'tp_hit': float
        }
    
    Examples:
        >>> trades = [
        ...     {'pnl_pct': 2.5, 'status': 'closed', 'exit_reason': 'tp'},
        ...     {'pnl_pct': -1.2, 'status': 'closed', 'exit_reason': 'sl'},
        ... ]
        >>> metrics = calculate_metrics(trades)
        >>> print(metrics['winrate'])
        50.0
    """
    if not trades:
        return {
            'trades_closed': 0,
            'winrate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'loss_over_8pct': 0,
            'tp_hit': 0.0
        }
    
    # DataFrame 변환
    df = pd.DataFrame(trades)
    
    # 1. trades_closed - 총 거래 수
    trades_closed = len(df)
    
    # 2. winrate - 승률
    wins = len(df[df['pnl_pct'] > 0])
    winrate = (wins / trades_closed * 100) if trades_closed > 0 else 0.0
    
    # 3. profit_factor - 총이익/총손실
    total_profit = df[df['pnl_pct'] > 0]['pnl_pct'].sum()
    total_loss = abs(df[df['pnl_pct'] < 0]['pnl_pct'].sum())
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
    
    # 4. max_drawdown - 최대 손실 (누적 PnL 기준)
    df['cumulative_pnl'] = df['pnl_pct'].cumsum()
    df['cumulative_max'] = df['cumulative_pnl'].cummax()
    df['drawdown'] = df['cumulative_pnl'] - df['cumulative_max']
    max_drawdown = df['drawdown'].min()
    
    # 5. loss_over_8pct - >8% 손실 횟수
    loss_over_8pct = len(df[df['pnl_pct'] < -8.0])
    
    # 6. tp_hit - TP 도달률
    tp_hits = len(df[df['exit_reason'] == 'tp']) if 'exit_reason' in df.columns else 0
    tp_hit = (tp_hits / trades_closed * 100) if trades_closed > 0 else 0.0
    
    return {
        'trades_closed': trades_closed,
        'winrate': round(winrate, 2),
        'profit_factor': round(profit_factor, 2),
        'max_drawdown': round(max_drawdown, 2),
        'loss_over_8pct': loss_over_8pct,
        'tp_hit': round(tp_hit, 2)
    }


def calculate_sharpe_ratio(trades: List[Dict[str, Any]], risk_free_rate: float = 0.0) -> float:
    """
    샤프 비율 계산 (추가 지표)
    
    Args:
        trades: 거래 목록
        risk_free_rate: 무위험 수익률 (기본값: 0)
    
    Returns:
        float: 샤프 비율
    """
    if not trades:
        return 0.0
    
    df = pd.DataFrame(trades)
    returns = df['pnl_pct'].values
    
    mean_return = returns.mean()
    std_return = returns.std()
    
    if std_return == 0:
        return 0.0
    
    sharpe = (mean_return - risk_free_rate) / std_return
    return round(sharpe, 2)
