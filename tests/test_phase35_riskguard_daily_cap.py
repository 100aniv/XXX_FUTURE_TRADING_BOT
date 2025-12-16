#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test PHASE35-2 ITER11: RiskGuard max_trades_per_day enforcement
AC2 verification via unit test (UPDATED FOR ITER11)
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import pytest
from execution.risk_manager import RiskManager


def test_riskguard_daily_cap_enforcement():
    """AC2: max_trades_per_day가 실제로 차단하는지 검증"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'per_trade': 0.01,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.1,
            'max_trades_per_day': 10,
        }
    }
    
    rm = RiskManager(config)
    today_ts = int(datetime.now().timestamp() * 1000)
    
    # 1~10번 거래는 통과
    for i in range(1, 11):
        signal = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': today_ts, 'reduce_only': False}
        result = rm.check_order(signal, qty=0.002, position_value=100)
        assert result[0], f"{i}번째 거래가 차단됨: {result[1]}"
        rm.record_trade(f'trade_{i}', timestamp=today_ts, is_entry=True)
    
    # 11번째는 차단
    signal_11 = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': today_ts, 'reduce_only': False}
    result = rm.check_order(signal_11, qty=0.002, position_value=100)
    assert not result[0], "11번째 거래가 승인됨"
    assert '거래 상한' in result[1] or 'daily' in result[1].lower(), f"차단 이유 확인: {result[1]}"


def test_riskguard_daily_cap_reset_next_day():
    """AC2-B: 날짜가 바뀌면 카운터 리셋"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'per_trade': 0.01,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.1,
            'max_trades_per_day': 5,
        }
    }
    
    rm = RiskManager(config)
    
    # 오늘 5개 거래
    today = datetime.now()
    today_ts = int(today.timestamp() * 1000)
    for i in range(1, 6):
        signal = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': today_ts, 'reduce_only': False}
        result = rm.check_order(signal, qty=0.002, position_value=100)
        assert result[0], f"오늘 {i}번째가 차단됨"
        rm.record_trade(f'today_{i}', timestamp=today_ts, is_entry=True)
    
    # 오늘 6번째는 차단
    signal_6 = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': today_ts, 'reduce_only': False}
    result = rm.check_order(signal_6, qty=0.002, position_value=100)
    assert not result[0], "오늘 6번째가 승인됨"
    
    # 내일 첫 거래는 승인
    tomorrow = today + timedelta(days=1)
    tomorrow_ts = int(tomorrow.timestamp() * 1000)
    signal_tomorrow = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': tomorrow_ts, 'reduce_only': False}
    result = rm.check_order(signal_tomorrow, qty=0.002, position_value=100)
    assert result[0], f"내일 첫 거래가 차단됨: {result[1]}".lower()


def test_riskguard_7d_total_cap():
    """AC2-C: 7일 누적 체크 (일별 10개씩 허용)"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'per_trade': 0.01,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.1,
            'max_trades_per_day': 10,
        }
    }
    
    rm = RiskManager(config)
    
    # 7일간 각각 10개씩 (총 70개)
    for day_offset in range(7):
        day_date = datetime.now() + timedelta(days=day_offset)
        day_ts = int(day_date.timestamp() * 1000)
        for i in range(1, 11):
            signal = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': day_ts, 'reduce_only': False}
            result = rm.check_order(signal, qty=0.002, position_value=100)
            assert result[0], f"Day{day_offset} {i}번째 차단됨"
            rm.record_trade(f'day{day_offset}_trade{i}', timestamp=day_ts, is_entry=True)
    
    # 8일째 첫 거래 (일별 리셋되므로 승인)
    day_8 = datetime.now() + timedelta(days=7)
    day_8_ts = int(day_8.timestamp() * 1000)
    signal_8 = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': day_8_ts, 'reduce_only': False}
    result = rm.check_order(signal_8, qty=0.002, position_value=100)
    assert result[0], f"8일째 첫 거래가 차단됨 (일별 리셋되어야 함): {result[1]}"


def test_riskguard_metadata_tracking():
    """AC2-D: 거래 메타데이터 추적 (trade_id 기반)"""
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'per_trade': 0.01,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.1,
            'max_trades_per_day': 3,
        }
    }
    
    rm = RiskManager(config)
    
    today = datetime.now()
    today_ts = int(today.timestamp() * 1000)
    
    # trade_id 기반 중복 방지
    signal = {'symbol': 'BTCUSDT', 'side': 'long', 'entry_price': 50000, 'timestamp': today_ts, 'reduce_only': False}
    rm.check_order(signal, qty=0.002, position_value=100)
    rm.record_trade('trade_A', timestamp=today_ts, is_entry=True)
    rm.record_trade('trade_A', timestamp=today_ts, is_entry=True)  # 중복
    rm.record_trade('trade_B', timestamp=today_ts, is_entry=True)
    
    # 아직 2개만 카운트되었으므로 3번째는 승인
    result = rm.check_order(signal, qty=0.002, position_value=100)
    assert result[0], "3번째가 차단됨"
    rm.record_trade('trade_C', timestamp=today_ts, is_entry=True)
    
    # 4번째는 차단 (cap=3)
    result = rm.check_order(signal, qty=0.002, position_value=100)
    assert not result[0], "4번째가 승인됨 (차단되어야 함)"
    assert len(result) == 2, "check_order는 (bool, str) tuple 반환"
    assert isinstance(result[1], str), "차단 이유는 문자열"
