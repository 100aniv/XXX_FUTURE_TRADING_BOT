#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
리팩토링 검증 테스트
===================
Signal Bot → Trading Bot 포지션 추적 분리 검증
"""
import pytest
import sys
import os


def test_position_tracker():
    """Trading Bot - PositionTracker 클래스 확인"""
    sys.path.insert(0, os.path.dirname(__file__))
    from trading_bot import PositionTracker
    
    # PositionTracker 초기화
    tracker = PositionTracker(mode='paper')
    assert tracker is not None, "PositionTracker 초기화 실패"
    
    # 메서드 확인
    methods = ['track_new_position', 'check_tp_sl', 'get_goal_progress', 
               'get_active_positions', 'get_daily_pnl']
    for method in methods:
        assert hasattr(tracker, method), f"{method}() 없음"
    
    # 속성 확인
    attrs = ['active_positions', 'daily_pnl', 'mode']
    for attr in attrs:
        assert hasattr(tracker, attr), f"{attr} 속성 없음"
    
    # 간단한 기능 테스트
    tracker.track_new_position(
        symbol="BTCUSDT",
        side="LONG",
        entry=50000.0,
        sl=49000.0,
        tp=52000.0,
        qty=0.01,
        timestamp=1700000000000
    )
    positions = tracker.get_active_positions()
    assert len(positions) == 1, "포지션 추적 기능 오류"
    
    pnl = tracker.get_daily_pnl()
    assert pnl == 0.0, "PnL 초기값 이상"
    
    progress = tracker.get_goal_progress()
    assert "목표 진행률" in progress, "목표 진행률 기능 오류"



@pytest.mark.parametrize("bot_module,desc", [
    ('telegram_signal_bot', 'SCALPING/DAYTRADE/SWING'),
    ('signal_bot_trend', 'TREND'),
    ('signal_bot_reversion', 'REVERSION'),
    ('signal_bot_breakout', 'BREAKOUT')
])
def test_signal_bots(bot_module, desc):
    """Signal Bot - 제거된 함수 확인"""
    removed_functions = ['track_new_signal', 'touch_check', 'goal_progress_text']
    required_functions = ['signal_logic', 'on_message', 'main']
    
    try:
        module = __import__(bot_module)
        
        # 제거된 함수들이 없는지 확인
        for func in removed_functions:
            assert not hasattr(module, func), f"{bot_module}에 제거되어야 할 함수 {func} 발견"
        
        # 필수 함수들이 있는지 확인
        for func in required_functions:
            assert hasattr(module, func), f"{bot_module}에 필수 함수 {func} 없음"
            
    except ImportError:
        pytest.skip(f"{bot_module} import 실패 - 의존성 문제")
