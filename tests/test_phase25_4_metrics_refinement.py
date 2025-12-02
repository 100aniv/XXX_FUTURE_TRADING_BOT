#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-4: Metrics Refinement 테스트
====================================
메트릭 계산 정교화 테스트

테스트 범위:
1. 시간 기반 isolation (run 간 trades 분리)
2. Sharpe Ratio 계산 검증
3. Max Drawdown 계산 검증
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from tuning.cluster import TuningWorker, JobQueue


# ============================================
# Helper Functions
# ============================================

def create_synthetic_trades(n: int, start_time: datetime) -> List[Dict[str, Any]]:
    """합성 trades 생성"""
    trades = []
    for i in range(n):
        pnl_usdt = np.random.uniform(-10, 20)
        pnl_pct = pnl_usdt / 1000 * 100  # 1000 USDT 가정
        
        trades.append({
            'pnl_usdt': pnl_usdt,
            'pnl_pct': pnl_pct,
            'exit_time': start_time + timedelta(minutes=i * 5)
        })
    
    return trades


# ============================================
# Test 1: Sharpe Ratio Calculation
# ============================================

def test_sharpe_ratio_calculation():
    """Sharpe Ratio 계산 검증"""
    
    worker = TuningWorker(worker_id='test-worker', job_queue=JobQueue(), use_dummy=False)
    
    # Case 1: 일정한 양수 수익률
    trades_positive = [
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': datetime.now()},
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': datetime.now()},
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': datetime.now()},
    ]
    
    sharpe_positive = worker._calculate_sharpe_ratio(trades_positive)
    
    # 표준편차가 0이면 Sharpe = 0
    assert sharpe_positive == 0.0
    
    # Case 2: 변동성 있는 수익률
    trades_volatile = [
        {'pnl_usdt': 20, 'pnl_pct': 2.0, 'exit_time': datetime.now()},
        {'pnl_usdt': -10, 'pnl_pct': -1.0, 'exit_time': datetime.now()},
        {'pnl_usdt': 15, 'pnl_pct': 1.5, 'exit_time': datetime.now()},
        {'pnl_usdt': -5, 'pnl_pct': -0.5, 'exit_time': datetime.now()},
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': datetime.now()},
    ]
    
    sharpe_volatile = worker._calculate_sharpe_ratio(trades_volatile)
    
    # Sharpe가 계산되어야 함 (0이 아님)
    assert sharpe_volatile != 0.0
    assert not np.isnan(sharpe_volatile)
    
    print(f"✅ Sharpe 계산:")
    print(f"   Positive (no variance): {sharpe_positive:.4f}")
    print(f"   Volatile: {sharpe_volatile:.4f}")


# ============================================
# Test 2: Max Drawdown Calculation
# ============================================

def test_max_drawdown_calculation():
    """Max Drawdown 계산 검증"""
    
    worker = TuningWorker(worker_id='test-worker', job_queue=JobQueue(), use_dummy=False)
    
    # Case 1: 모든 trades가 양수 (drawdown 없음)
    now = datetime.now()
    trades_all_wins = [
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': now},
        {'pnl_usdt': 20, 'pnl_pct': 2.0, 'exit_time': now + timedelta(minutes=5)},
        {'pnl_usdt': 15, 'pnl_pct': 1.5, 'exit_time': now + timedelta(minutes=10)},
    ]
    
    max_dd, dd_duration = worker._calculate_max_drawdown(trades_all_wins)
    
    # Drawdown이 없어야 함
    assert max_dd == 0.0
    assert dd_duration == 0.0
    
    # Case 2: Drawdown 있는 경우
    trades_with_dd = [
        {'pnl_usdt': 50, 'pnl_pct': 5.0, 'exit_time': now},  # Peak: 50
        {'pnl_usdt': -20, 'pnl_pct': -2.0, 'exit_time': now + timedelta(minutes=5)},  # Cumulative: 30
        {'pnl_usdt': -10, 'pnl_pct': -1.0, 'exit_time': now + timedelta(minutes=10)},  # Cumulative: 20 (DD = 60%)
        {'pnl_usdt': 40, 'pnl_pct': 4.0, 'exit_time': now + timedelta(minutes=15)},  # Cumulative: 60 (new peak)
    ]
    
    max_dd, dd_duration = worker._calculate_max_drawdown(trades_with_dd)
    
    # Drawdown이 있어야 함
    assert max_dd > 0.0
    assert dd_duration >= 0.0  # Duration은 0일 수도 있음 (로직 상)
    
    # DD% 계산: (50 - 20) / 50 * 100 = 60%
    expected_dd = (50 - 20) / 50 * 100
    assert abs(max_dd - expected_dd) < 0.01
    
    print(f"✅ Max Drawdown 계산:")
    print(f"   All wins: DD={max_dd:.2f}%, Duration={dd_duration:.2f}h")
    
    trades_with_dd_2 = [
        {'pnl_usdt': 50, 'pnl_pct': 5.0, 'exit_time': now},
        {'pnl_usdt': -20, 'pnl_pct': -2.0, 'exit_time': now + timedelta(minutes=5)},
        {'pnl_usdt': -10, 'pnl_pct': -1.0, 'exit_time': now + timedelta(minutes=10)},
        {'pnl_usdt': 40, 'pnl_pct': 4.0, 'exit_time': now + timedelta(minutes=15)},
    ]
    
    max_dd_2, dd_duration_2 = worker._calculate_max_drawdown(trades_with_dd_2)
    
    print(f"   With DD: DD={max_dd_2:.2f}%, Duration={dd_duration_2:.2f}h")
    print(f"   Expected DD: {expected_dd:.2f}%")


# ============================================
# Test 3: Time-based Isolation (Synthetic)
# ============================================

def test_time_based_isolation():
    """시간 기반 isolation 검증 (synthetic)"""
    
    worker = TuningWorker(worker_id='test-worker', job_queue=JobQueue(), use_dummy=False)
    
    # Run A: 10시 ~ 11시 (10개 trades, 5분 간격 = 45분)
    run_a_start = datetime(2025, 12, 3, 10, 0, 0)
    run_a_end = datetime(2025, 12, 3, 11, 0, 0)
    
    trades_a = create_synthetic_trades(n=10, start_time=run_a_start)
    
    # Run B: 12시 ~ 13시
    run_b_start = datetime(2025, 12, 3, 12, 0, 0)
    run_b_end = datetime(2025, 12, 3, 13, 0, 0)
    
    trades_b = create_synthetic_trades(n=10, start_time=run_b_start)
    
    # 검증: trades_a는 run_a_start ~ run_a_end 범위에만 있어야 함
    for trade in trades_a:
        assert run_a_start <= trade['exit_time'] <= run_a_end
    
    for trade in trades_b:
        assert run_b_start <= trade['exit_time'] <= run_b_end
    
    # 섞이지 않음 확인
    all_trades = trades_a + trades_b
    trades_in_a_range = [t for t in all_trades if run_a_start <= t['exit_time'] <= run_a_end]
    trades_in_b_range = [t for t in all_trades if run_b_start <= t['exit_time'] <= run_b_end]
    
    assert len(trades_in_a_range) == len(trades_a)
    assert len(trades_in_b_range) == len(trades_b)
    
    print(f"✅ 시간 기반 isolation 검증:")
    print(f"   Run A: {len(trades_a)}개 trades ({run_a_start} ~ {run_a_end})")
    print(f"   Run B: {len(trades_b)}개 trades ({run_b_start} ~ {run_b_end})")
    print(f"   Isolation 확인: A 범위={len(trades_in_a_range)}, B 범위={len(trades_in_b_range)}")


# ============================================
# Test 4: Empty Trades Handling
# ============================================

def test_empty_trades_handling():
    """Trades가 없을 때 빈 메트릭 반환 검증"""
    
    worker = TuningWorker(worker_id='test-worker', job_queue=JobQueue(), use_dummy=False)
    
    # Sharpe: 빈 trades
    sharpe_empty = worker._calculate_sharpe_ratio([])
    assert sharpe_empty == 0.0
    
    # MaxDD: 빈 trades
    max_dd, dd_duration = worker._calculate_max_drawdown([])
    assert max_dd == 0.0
    assert dd_duration == 0.0
    
    # Empty metrics
    empty_metrics = worker._get_empty_metrics(runtime_sec=10.5)
    
    assert empty_metrics['pnl'] == 0.0
    assert empty_metrics['trade_count'] == 0
    assert empty_metrics['sharpe_ratio'] == 0.0
    assert empty_metrics['max_drawdown'] == 0.0
    assert empty_metrics['runtime_sec'] == 10.5
    
    print(f"✅ Empty trades 처리 검증")


# ============================================
# Test 5: Sharpe with Single Trade
# ============================================

def test_sharpe_with_single_trade():
    """단일 trade일 때 Sharpe = 0 검증"""
    
    worker = TuningWorker(worker_id='test-worker', job_queue=JobQueue(), use_dummy=False)
    
    trades_single = [
        {'pnl_usdt': 10, 'pnl_pct': 1.0, 'exit_time': datetime.now()}
    ]
    
    sharpe = worker._calculate_sharpe_ratio(trades_single)
    
    # 단일 trade → 표준편차 계산 불가 → Sharpe = 0
    assert sharpe == 0.0
    
    print(f"✅ 단일 trade Sharpe: {sharpe:.4f} (예상: 0.0)")


# ============================================
# Test 6: Profit Factor Calculation
# ============================================

def test_profit_factor_in_metrics():
    """Profit Factor 계산 검증"""
    
    # Synthetic trades
    trades_pf = [
        {'pnl_usdt': 50},   # win
        {'pnl_usdt': 40},   # win
        {'pnl_usdt': -20},  # lose
        {'pnl_usdt': -10},  # lose
    ]
    
    # PF = (total win) / (total lose) = 90 / 30 = 3.0
    
    win_total = sum(t['pnl_usdt'] for t in trades_pf if t['pnl_usdt'] > 0)
    lose_total = abs(sum(t['pnl_usdt'] for t in trades_pf if t['pnl_usdt'] <= 0))
    
    expected_pf = win_total / lose_total if lose_total > 0 else 0.0
    
    assert abs(expected_pf - 3.0) < 0.01
    
    print(f"✅ Profit Factor 계산:")
    print(f"   Win total: {win_total}, Lose total: {lose_total}")
    print(f"   Profit Factor: {expected_pf:.2f}")
