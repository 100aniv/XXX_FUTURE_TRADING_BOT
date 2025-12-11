#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-6: trial_id/run_id Mapping 테스트
==========================================

목적:
- run_id와 trial_id가 정확히 동기화되는지 검증
- 서로 다른 run에서 trade가 섞이지 않는지 확인
"""
import pytest
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection
from common.performance_metrics import compute_performance_metrics_from_db


class TestTrialIdMapping:
    """trial_id/run_id 매핑 정확도 테스트"""
    
    def setup_method(self):
        """각 테스트 전 DB 정리"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 테스트용 trade 삭제
                cur.execute("""
                    DELETE FROM trading.trades 
                    WHERE trial_id LIKE 'test_%'
                """)
                conn.commit()
    
    def _insert_test_trades(self, trial_id: str, trades: List[Dict]):
        """테스트용 trade 삽입"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for trade in trades:
                    cur.execute("""
                        INSERT INTO trading.trades (
                            trade_id, symbol, side, entry_price, exit_price,
                            quantity, leverage, pnl, status, strategy_id,
                            ts_open, ts_close, created_at, trial_id, mode
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            NOW(), NOW(), NOW(), %s, %s
                        )
                    """, (
                        trade['trade_id'],
                        trade['symbol'],
                        trade['side'],
                        trade['entry_price'],
                        trade['exit_price'],
                        trade['quantity'],
                        trade.get('leverage', 1),
                        trade['pnl'],
                        'CLOSED',
                        trade.get('strategy_id', 'test_strategy'),
                        trial_id,
                        'backtest'
                    ))
                conn.commit()
    
    def test_separate_trials_no_mixing(self):
        """서로 다른 trial_id의 trade가 섞이지 않는지 검증"""
        # Run A: 3건 (모두 이익)
        trades_a = [
            {
                'trade_id': 'test_a_001',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 51000,
                'quantity': 0.1,
                'pnl': 100.0
            },
            {
                'trade_id': 'test_a_002',
                'symbol': 'BTCUSDT',
                'side': 'SHORT',
                'entry_price': 51000,
                'exit_price': 50000,
                'quantity': 0.1,
                'pnl': 100.0
            },
            {
                'trade_id': 'test_a_003',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 52000,
                'quantity': 0.1,
                'pnl': 200.0
            }
        ]
        
        # Run B: 2건 (모두 손실)
        trades_b = [
            {
                'trade_id': 'test_b_001',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 49000,
                'quantity': 0.1,
                'pnl': -100.0
            },
            {
                'trade_id': 'test_b_002',
                'symbol': 'BTCUSDT',
                'side': 'SHORT',
                'entry_price': 49000,
                'exit_price': 50000,
                'quantity': 0.1,
                'pnl': -100.0
            }
        ]
        
        self._insert_test_trades('test_run_a', trades_a)
        self._insert_test_trades('test_run_b', trades_b)
        
        # Run A 성능 지표
        perf_a = compute_performance_metrics_from_db(
            trial_id='test_run_a',
            initial_equity=10000.0
        )
        
        # Run B 성능 지표
        perf_b = compute_performance_metrics_from_db(
            trial_id='test_run_b',
            initial_equity=10000.0
        )
        
        # 검증: Run A (3건, 모두 이익)
        assert perf_a['num_trades'] == 3, f"Run A should have 3 trades, got {perf_a['num_trades']}"
        assert perf_a['win_rate'] == 1.0, f"Run A should have 100% win rate, got {perf_a['win_rate']}"
        assert perf_a['pnl_total'] == 400.0, f"Run A should have 400 PnL, got {perf_a['pnl_total']}"
        assert perf_a['num_wins'] == 3
        assert perf_a['num_losses'] == 0
        
        # 검증: Run B (2건, 모두 손실)
        assert perf_b['num_trades'] == 2, f"Run B should have 2 trades, got {perf_b['num_trades']}"
        assert perf_b['win_rate'] == 0.0, f"Run B should have 0% win rate, got {perf_b['win_rate']}"
        assert perf_b['pnl_total'] == -200.0, f"Run B should have -200 PnL, got {perf_b['pnl_total']}"
        assert perf_b['num_wins'] == 0
        assert perf_b['num_losses'] == 2
    
    def test_null_trial_id_isolation(self):
        """trial_id=NULL인 trade는 조회되지 않아야 함"""
        import uuid
        test_trade_id = f'test_null_{uuid.uuid4().hex[:8]}'
        
        # NULL trial_id trade
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trading.trades (
                        trade_id, symbol, side, entry_price, exit_price,
                        quantity, leverage, pnl, status, strategy_id,
                        ts_open, ts_close, created_at, trial_id, mode
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        NOW(), NOW(), NOW(), NULL, %s
                    )
                """, (
                    test_trade_id,
                    'BTCUSDT',
                    'LONG',
                    50000,
                    51000,
                    0.1,
                    1,
                    100.0,
                    'CLOSED',
                    'test_strategy',
                    'backtest'
                ))
                conn.commit()
        
        # 특정 trial_id로 조회 시 NULL trade는 제외
        perf = compute_performance_metrics_from_db(
            trial_id='test_run_specific',
            initial_equity=10000.0
        )
        
        # 0건이어야 함
        assert perf['num_trades'] == 0, "NULL trial_id trades should not be included"
    
    def test_performance_calculation_accuracy(self):
        """성능 지표 계산 정확도 검증 (trial_id 기반)"""
        # 혼합 trade (이익 2, 손실 1)
        trades = [
            {
                'trade_id': 'test_acc_001',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 51000,
                'quantity': 0.1,
                'pnl': 100.0
            },
            {
                'trade_id': 'test_acc_002',
                'symbol': 'BTCUSDT',
                'side': 'SHORT',
                'entry_price': 50000,
                'exit_price': 49000,
                'quantity': 0.1,
                'pnl': 100.0
            },
            {
                'trade_id': 'test_acc_003',
                'symbol': 'BTCUSDT',
                'side': 'LONG',
                'entry_price': 50000,
                'exit_price': 49500,
                'quantity': 0.1,
                'pnl': -50.0
            }
        ]
        
        self._insert_test_trades('test_accuracy', trades)
        
        perf = compute_performance_metrics_from_db(
            trial_id='test_accuracy',
            initial_equity=10000.0
        )
        
        # 검증
        assert perf['num_trades'] == 3
        assert perf['num_wins'] == 2
        assert perf['num_losses'] == 1
        assert perf['pnl_total'] == 150.0
        assert perf['win_rate'] == pytest.approx(2/3, rel=1e-9)
        assert perf['avg_win'] == 100.0
        assert perf['avg_loss'] == -50.0
        assert perf['roi'] == pytest.approx(150.0 / 10000.0, rel=1e-9)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
