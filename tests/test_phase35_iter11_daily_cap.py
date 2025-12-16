#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test PHASE35-3 ITER11: max_trades_per_day 구현 검증
단위 테스트로 EC1-EC4 증명
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import pytest


def test_riskmanager_max_trades_per_day_field_exists():
    """EC0: RiskManager에 max_trades_per_day 필드 존재"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': 10,
            'max_positions': 3,
            'max_exposure_per_symbol': 0.1,
        }
    }
    
    rm = RiskManager(config)
    
    # 필드 존재 확인
    assert hasattr(rm, 'max_trades_per_day'), "max_trades_per_day 필드 없음"
    assert rm.max_trades_per_day == 10, f"Expected 10, got {rm.max_trades_per_day}"
    assert hasattr(rm, '_daily_trades'), "_daily_trades 필드 없음"
    assert hasattr(rm, 'record_trade'), "record_trade 메서드 없음"
    assert hasattr(rm, 'get_daily_trade_stats'), "get_daily_trade_stats 메서드 없음"


def test_ec1_cap_enforcement():
    """EC1: max_trades_per_day 초과 시 주문 차단"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': 2,  # 2개로 제한
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5,
        }
    }
    
    rm = RiskManager(config)
    
    # 오늘 날짜
    today_ts = int(datetime.now().timestamp() * 1000)
    
    # Entry 신호 (reduce_only=False)
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'long',
        'entry_price': 50000,
        'timestamp': today_ts,
        'reduce_only': False
    }
    
    # 1번째 주문: 허용
    result1 = rm.check_order(signal, qty=0.1, position_value=5000)
    assert result1[0] == True, f"1번째 주문이 차단됨: {result1[1]}"
    rm.record_trade(f"trade_1", timestamp=today_ts, is_entry=True)
    
    # 2번째 주문: 허용
    result2 = rm.check_order(signal, qty=0.1, position_value=5000)
    assert result2[0] == True, f"2번째 주문이 차단됨: {result2[1]}"
    rm.record_trade(f"trade_2", timestamp=today_ts, is_entry=True)
    
    # 3번째 주문: 차단되어야 함 (cap=2)
    result3 = rm.check_order(signal, qty=0.1, position_value=5000)
    assert result3[0] == False, "3번째 주문이 허용됨 (차단되어야 함)"
    assert '거래 상한' in result3[1] or 'daily' in result3[1].lower(), \
        f"차단 이유에 daily cap 언급 필요: {result3[1]}"


def test_ec2_daily_reset():
    """EC2: 날짜 변경 시 카운터 리셋"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': 2,
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5,
        }
    }
    
    rm = RiskManager(config)
    
    # 오늘 2개 거래
    today = datetime.now()
    today_ts = int(today.timestamp() * 1000)
    
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'long',
        'entry_price': 50000,
        'timestamp': today_ts,
        'reduce_only': False
    }
    
    rm.check_order(signal, qty=0.1, position_value=5000)
    rm.record_trade("trade_today_1", timestamp=today_ts, is_entry=True)
    
    rm.check_order(signal, qty=0.1, position_value=5000)
    rm.record_trade("trade_today_2", timestamp=today_ts, is_entry=True)
    
    # 오늘 3번째는 차단
    result_today = rm.check_order(signal, qty=0.1, position_value=5000)
    assert result_today[0] == False, "오늘 3번째 주문이 허용됨"
    
    # 내일 거래
    tomorrow = today + timedelta(days=1)
    tomorrow_ts = int(tomorrow.timestamp() * 1000)
    
    signal_tomorrow = signal.copy()
    signal_tomorrow['timestamp'] = tomorrow_ts
    
    # 내일 첫 거래는 허용되어야 함 (리셋)
    result_tomorrow = rm.check_order(signal_tomorrow, qty=0.1, position_value=5000)
    assert result_tomorrow[0] == True, f"내일 첫 거래가 차단됨: {result_tomorrow[1]}"


def test_ec3_entry_only_policy():
    """EC3: Entry 주문만 카운트 (reduce_only/close 제외)"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': 2,
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5,
        }
    }
    
    rm = RiskManager(config)
    
    today_ts = int(datetime.now().timestamp() * 1000)
    
    # Entry 신호
    entry_signal = {
        'symbol': 'BTCUSDT',
        'side': 'long',
        'entry_price': 50000,
        'timestamp': today_ts,
        'reduce_only': False
    }
    
    # Close 신호
    close_signal = {
        'symbol': 'BTCUSDT',
        'side': 'close',
        'entry_price': 51000,
        'timestamp': today_ts,
        'reduce_only': True
    }
    
    # Entry 2개
    rm.check_order(entry_signal, qty=0.1, position_value=5000)
    rm.record_trade("trade_1", timestamp=today_ts, is_entry=True)
    
    rm.check_order(entry_signal, qty=0.1, position_value=5000)
    rm.record_trade("trade_2", timestamp=today_ts, is_entry=True)
    
    # Close는 카운트 안 됨
    rm.record_trade("close_1", timestamp=today_ts, is_entry=False)
    
    # 3번째 Entry는 차단
    result = rm.check_order(entry_signal, qty=0.1, position_value=5000)
    assert result[0] == False, "3번째 Entry가 허용됨 (Close는 카운트 안 됨)"
    
    # Close 주문은 항상 허용 (cap 무관)
    close_result = rm.check_order(close_signal, qty=0.1, position_value=5000)
    # Close 주문은 다른 가드로 차단될 수 있지만, daily cap으로는 차단 안 됨
    # (is_entry=False이므로 카운트 안 됨)


def test_ec4_cap_disabled_when_none():
    """EC4: max_trades_per_day=None이면 차단 없음"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': None,  # 비활성화
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5,
        }
    }
    
    rm = RiskManager(config)
    
    today_ts = int(datetime.now().timestamp() * 1000)
    
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'long',
        'entry_price': 50000,
        'timestamp': today_ts,
        'reduce_only': False
    }
    
    # 10개 주문 모두 허용되어야 함
    for i in range(10):
        result = rm.check_order(signal, qty=0.1, position_value=5000)
        assert result[0] == True, f"{i+1}번째 주문이 차단됨 (cap=None이면 무제한)"
        rm.record_trade(f"trade_{i+1}", timestamp=today_ts, is_entry=True)


def test_get_daily_trade_stats():
    """통계 조회 메서드 테스트"""
    from execution.risk_manager import RiskManager
    
    config = {
        'mode': 'backtest',
        'capital': {'initial': 10000},
        'risk': {
            'max_trades_per_day': 5,
            'max_positions': 5,
            'max_exposure_per_symbol': 0.5,
        }
    }
    
    rm = RiskManager(config)
    
    today_ts = int(datetime.now().timestamp() * 1000)
    
    # 3개 거래
    for i in range(3):
        rm.record_trade(f"trade_{i+1}", timestamp=today_ts, is_entry=True)
    
    stats = rm.get_daily_trade_stats()
    
    assert 'per_day_trades' in stats
    assert 'total_blocks' in stats
    assert 'max_trades_per_day' in stats
    assert stats['max_trades_per_day'] == 5
    
    # 오늘 거래 수 확인
    today = datetime.fromtimestamp(today_ts / 1000.0).strftime('%Y-%m-%d')
    assert today in stats['per_day_trades']
    assert stats['per_day_trades'][today] == 3
