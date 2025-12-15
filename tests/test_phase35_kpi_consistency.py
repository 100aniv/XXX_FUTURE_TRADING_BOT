#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER6: KPI Consistency Test
======================================

목적: KPI 계산 SSOT 함수가 모순 없이 작동하는지 검증
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from common.metrics_kpi import compute_kpis, validate_kpi_consistency


def test_kpi_zero_trades():
    """거래 없을 때 KPI가 올바르게 계산되는지 검증"""
    kpi = compute_kpis(trades=[], initial_capital=10000)
    
    assert kpi["total_trades"] == 0
    assert kpi["winrate"] == 0.0
    assert kpi["total_pnl"] == 0.0
    assert kpi["net_pnl"] == 0.0
    assert kpi["roi"] == 0.0
    assert kpi["final_equity"] == 10000.0


def test_kpi_basic_trades():
    """기본 거래 케이스: 승/패 혼합"""
    trades = [
        {"pnl": 100.0},   # win
        {"pnl": -50.0},   # loss
        {"pnl": 200.0},   # win
        {"pnl": -30.0},   # loss
    ]
    
    kpi = compute_kpis(trades, initial_capital=10000, fees_total=10.0, slippage_total=5.0)
    
    assert kpi["total_trades"] == 4
    assert kpi["winning_trades"] == 2
    assert kpi["losing_trades"] == 2
    assert kpi["winrate"] == 50.0
    assert kpi["total_pnl"] == 220.0  # 100 - 50 + 200 - 30
    assert kpi["net_pnl"] == 205.0    # 220 - 10 - 5
    assert kpi["roi"] == 2.05         # 205 / 10000 * 100
    assert kpi["final_equity"] == 10205.0


def test_kpi_all_wins():
    """모든 거래가 승리"""
    trades = [
        {"pnl": 100.0},
        {"pnl": 50.0},
    ]
    
    kpi = compute_kpis(trades, initial_capital=10000)
    
    assert kpi["winrate"] == 100.0
    assert kpi["total_pnl"] == 150.0
    assert kpi["profit_factor"] == 0.0  # gross_loss = 0이면 Inf → 0으로 처리


def test_kpi_all_losses():
    """모든 거래가 손실"""
    trades = [
        {"pnl": -100.0},
        {"pnl": -50.0},
    ]
    
    kpi = compute_kpis(trades, initial_capital=10000)
    
    assert kpi["winrate"] == 0.0
    assert kpi["total_pnl"] == -150.0
    assert kpi["roi"] == -1.5  # -150 / 10000 * 100


def test_kpi_consistency_same_input():
    """동일 입력으로 두 번 계산 시 결과 일치 확인"""
    trades = [
        {"pnl": 100.0},
        {"pnl": -50.0},
    ]
    
    kpi1 = compute_kpis(trades, initial_capital=10000, fees_total=5.0)
    kpi2 = compute_kpis(trades, initial_capital=10000, fees_total=5.0)
    
    assert validate_kpi_consistency(kpi1, kpi2, tolerance=0.001)


def test_kpi_drawdown():
    """Drawdown 계산 검증 (허용 오차 있음)"""
    trades = [
        {"pnl": 100.0},   # peak at 100
        {"pnl": -200.0},  # drawdown -100 from peak
        {"pnl": 50.0},    # recovery to -50
    ]
    
    kpi = compute_kpis(trades, initial_capital=10000)
    
    # Max drawdown는 누적 방식에 따라 -1.0% ~ -2.0% 범위
    assert -2.5 <= kpi["max_drawdown"] <= -0.5


def test_kpi_no_pnl_contradiction():
    """PnL=0일 때 ROI도 0인지 확인 (모순 방지)"""
    trades = []
    
    kpi = compute_kpis(trades, initial_capital=10000)
    
    assert kpi["total_pnl"] == 0.0
    assert kpi["net_pnl"] == 0.0
    assert kpi["roi"] == 0.0  # ← 모순 없음 확인


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
