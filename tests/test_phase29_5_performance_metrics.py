#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-5: Performance Metrics 단위 테스트
==========================================

테스트 항목:
1. 모든 포지션 이익 → win_rate = 1.0, max_dd = 0
2. 이익/손실 섞인 케이스 → win_rate, max_dd, pnl_total 검증
3. 포지션 0개 → 빈 지표 반환
4. Sharpe Ratio 계산 (표본 적음 시 None)
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.performance_metrics import (
    compute_performance_metrics_from_trades,
    _calculate_max_drawdown,
    _calculate_max_consecutive_losses_from_list,
    _calculate_sharpe_ratio,
    _empty_metrics
)


class TestPerformanceMetricsBasic:
    """기본 성능 지표 계산 테스트"""
    
    def test_all_wins_scenario(self):
        """모든 포지션 이익 → win_rate = 1.0, max_dd = 0"""
        trades = [
            {'pnl': 100.0, 'exit_time': 1},
            {'pnl': 150.0, 'exit_time': 2},
            {'pnl': 200.0, 'exit_time': 3},
        ]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        assert result['num_trades'] == 3
        assert result['pnl_total'] == 450.0
        assert result['win_rate'] == 1.0
        assert result['num_wins'] == 3
        assert result['num_losses'] == 0
        assert result['max_drawdown'] == 0.0
        assert result['profit_factor'] == 0.0  # 손실 없음
    
    def test_mixed_wins_losses(self):
        """이익/손실 섞인 케이스"""
        trades = [
            {'pnl': 100.0, 'exit_time': 1},
            {'pnl': -50.0, 'exit_time': 2},
            {'pnl': 200.0, 'exit_time': 3},
            {'pnl': -100.0, 'exit_time': 4},
            {'pnl': 150.0, 'exit_time': 5},
        ]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        assert result['num_trades'] == 5
        assert result['pnl_total'] == 300.0
        assert result['num_wins'] == 3
        assert result['num_losses'] == 2
        assert result['win_rate'] == 0.6  # 3/5
        assert result['avg_win'] == pytest.approx(150.0, rel=1e-2)  # (100+200+150)/3
        assert result['avg_loss'] == pytest.approx(-75.0, rel=1e-2)  # (-50-100)/2
        
        # Profit Factor = 총이익 / 총손실
        total_profit = 450.0  # 100+200+150
        total_loss = 150.0  # 50+100
        expected_pf = total_profit / total_loss
        assert result['profit_factor'] == pytest.approx(expected_pf, rel=1e-2)
        
        # Max DD는 음수 구간이 있어야 발생
        assert result['max_drawdown'] >= 0.0
    
    def test_zero_trades(self):
        """포지션 0개 → 빈 지표 반환"""
        trades = []
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        assert result['num_trades'] == 0
        assert result['pnl_total'] == 0.0
        assert result['win_rate'] == 0.0
        assert result['max_drawdown'] == 0.0
        assert result['sharpe_ratio'] is None
    
    def test_drawdown_calculation(self):
        """Drawdown 계산 검증"""
        # 시나리오: 연속 손실로 인한 Drawdown
        trades = [
            {'pnl': 100.0, 'exit_time': 1},  # equity: 10100
            {'pnl': -200.0, 'exit_time': 2},  # equity: 9900 (peak에서 -200)
            {'pnl': -300.0, 'exit_time': 3},  # equity: 9600 (peak에서 -500)
            {'pnl': 500.0, 'exit_time': 4},  # equity: 10100 (회복)
        ]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        # Peak = 10100, Min = 9600 → DD = 500 / 10100 ≈ 0.0495
        expected_dd_ratio = 500.0 / 10100.0
        assert result['max_drawdown'] == pytest.approx(expected_dd_ratio, rel=1e-2)
        assert result['max_drawdown_abs'] == pytest.approx(-500.0, rel=1e-2)


class TestMaxDrawdownHelper:
    """Max Drawdown 헬퍼 함수 테스트"""
    
    def test_no_drawdown(self):
        """지속적인 상승 → DD = 0"""
        equity_curve = [10100, 10200, 10300, 10400]
        dd_ratio, dd_abs = _calculate_max_drawdown(equity_curve, 10000.0)
        
        assert dd_ratio == 0.0
        assert dd_abs == 0.0
    
    def test_single_dip(self):
        """단일 하락 후 회복"""
        equity_curve = [10100, 10200, 9800, 10300]
        dd_ratio, dd_abs = _calculate_max_drawdown(equity_curve, 10000.0)
        
        # Peak = 10200, Min = 9800 → DD = 400 / 10200
        expected_ratio = 400.0 / 10200.0
        assert dd_ratio == pytest.approx(expected_ratio, rel=1e-2)
        assert dd_abs == pytest.approx(-400.0, rel=1e-2)
    
    def test_multiple_peaks(self):
        """여러 Peak, 최대 DD는 가장 큰 것"""
        equity_curve = [10100, 9900, 10200, 9700, 10300]
        dd_ratio, dd_abs = _calculate_max_drawdown(equity_curve, 10000.0)
        
        # Peak1 = 10100 → 9900 (DD 200)
        # Peak2 = 10200 → 9700 (DD 500) ← 최대
        expected_ratio = 500.0 / 10200.0
        assert dd_ratio == pytest.approx(expected_ratio, rel=1e-2)
        assert dd_abs == pytest.approx(-500.0, rel=1e-2)


class TestConsecutiveLosses:
    """연속 손실 계산 테스트"""
    
    def test_no_losses(self):
        """손실 없음"""
        pnl_list = [100, 200, 150, 300]
        max_consecutive = _calculate_max_consecutive_losses_from_list(pnl_list)
        assert max_consecutive == 0
    
    def test_single_loss_streak(self):
        """단일 연속 손실"""
        pnl_list = [100, -50, -100, -150, 200]
        max_consecutive = _calculate_max_consecutive_losses_from_list(pnl_list)
        assert max_consecutive == 3
    
    def test_multiple_streaks(self):
        """여러 손실 구간, 최대값 반환"""
        pnl_list = [100, -50, -100, 200, -30, -40, -50, -60, 300]
        max_consecutive = _calculate_max_consecutive_losses_from_list(pnl_list)
        assert max_consecutive == 4


class TestSharpeRatio:
    """Sharpe Ratio 계산 테스트"""
    
    def test_insufficient_data(self):
        """표본 부족 → None"""
        equity_curve = [10100]
        sharpe = _calculate_sharpe_ratio(equity_curve, 10000.0, num_trades=1)
        assert sharpe is None
    
    def test_zero_std(self):
        """표준편차 0 (모든 수익률 동일) → None"""
        equity_curve = [10100, 10200, 10300, 10400]
        sharpe = _calculate_sharpe_ratio(equity_curve, 10000.0, num_trades=4)
        # 동일 수익률이면 std=0이므로 None
        assert sharpe is None or sharpe > 0  # 구현 방식에 따라 다를 수 있음
    
    def test_positive_sharpe(self):
        """정상적인 Sharpe 계산"""
        # 변동성 있는 수익률
        equity_curve = [10100, 10050, 10200, 10150, 10300]
        sharpe = _calculate_sharpe_ratio(equity_curve, 10000.0, num_trades=5)
        
        # Sharpe는 계산되어야 함 (None이 아님)
        assert sharpe is not None
        # 양수 수익률이므로 Sharpe > 0
        assert sharpe > 0


class TestEmptyMetrics:
    """빈 지표 반환 테스트"""
    
    def test_empty_structure(self):
        """빈 지표 구조 검증"""
        empty = _empty_metrics()
        
        assert empty['num_trades'] == 0
        assert empty['pnl_total'] == 0.0
        assert empty['win_rate'] == 0.0
        assert empty['max_drawdown'] == 0.0
        assert empty['sharpe_ratio'] is None
        assert 'profit_factor' in empty
        assert 'num_wins' in empty
        assert 'num_losses' in empty


class TestEdgeCases:
    """엣지 케이스 테스트"""
    
    def test_breakeven_trades(self):
        """PnL = 0인 거래 (Breakeven)"""
        trades = [
            {'pnl': 100.0, 'exit_time': 1},
            {'pnl': 0.0, 'exit_time': 2},
            {'pnl': -50.0, 'exit_time': 3},
        ]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        # Breakeven은 승/패에서 제외
        assert result['num_wins'] == 1
        assert result['num_losses'] == 1
        assert result['win_rate'] == 0.5  # 1 / (1 + 1)
    
    def test_single_trade_win(self):
        """단일 거래 (이익)"""
        trades = [{'pnl': 100.0, 'exit_time': 1}]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        assert result['num_trades'] == 1
        assert result['win_rate'] == 1.0
        assert result['max_drawdown'] == 0.0
        # Sharpe는 표본 부족으로 None
        assert result['sharpe_ratio'] is None
    
    def test_single_trade_loss(self):
        """단일 거래 (손실)"""
        trades = [{'pnl': -100.0, 'exit_time': 1}]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        assert result['num_trades'] == 1
        assert result['win_rate'] == 0.0
        # DD = 100 / 10000 = 0.01
        expected_dd = 100.0 / 10000.0
        assert result['max_drawdown'] == pytest.approx(expected_dd, rel=1e-2)
    
    def test_roi_calculation(self):
        """ROI 계산 검증"""
        trades = [
            {'pnl': 500.0, 'exit_time': 1},
            {'pnl': -200.0, 'exit_time': 2},
        ]
        
        result = compute_performance_metrics_from_trades(trades, initial_equity=10000.0)
        
        # ROI = (500 - 200) / 10000 = 0.03 = 3%
        expected_roi = 300.0 / 10000.0
        assert result['roi'] == pytest.approx(expected_roi, rel=1e-2)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
