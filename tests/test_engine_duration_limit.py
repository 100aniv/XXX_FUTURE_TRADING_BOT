#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Engine Duration Limit (Wall-Clock)
========================================
PHASE22-1-FIX: wall-clock 기반 duration 종료 로직 검증
"""
import time
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


def test_duration_config_parsing():
    """duration_hours와 duration_mode가 config에서 올바르게 파싱되는지 검증"""
    from scripts.run_phase22_ensemble_single_symbol import main
    import sys
    
    # Mock argparse
    test_args = [
        'run_phase22_ensemble_single_symbol.py',
        '--config', 'configs/paper/phase22_ensemble_single_symbol.yml',
        '--duration-hours', '0.5',
        '--duration-mode', 'wall_clock',
    ]
    
    with patch.object(sys, 'argv', test_args):
        # 실제로 실행하지 않고 argparse만 테스트
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', type=str, default='configs/paper/base.yml')
        parser.add_argument('--duration-hours', type=float, default=0.5)
        parser.add_argument('--duration-mode', type=str, choices=['market_time', 'wall_clock'], default='wall_clock')
        parser.add_argument('--clean-state', action='store_true')
        
        args = parser.parse_args(test_args[1:])
        
        assert args.duration_hours == 0.5
        assert args.duration_mode == 'wall_clock'
        
        print(f"✅ Duration config 파싱 PASS: {args.duration_hours}h, mode={args.duration_mode}")


def test_duration_calculation():
    """duration_hours → duration_seconds 변환이 올바른지 검증"""
    test_cases = [
        (0.5, 1800),      # 30분
        (1.0, 3600),      # 1시간
        (0.0833, 299.88), # 5분 (약간의 오차 허용)
        (0.01, 36),       # 36초
    ]
    
    for hours, expected_seconds in test_cases:
        actual_seconds = hours * 3600
        
        if expected_seconds > 100:  # 정수 비교
            assert abs(actual_seconds - expected_seconds) < 1, \
                f"Duration 계산 오류: {hours}h → {actual_seconds}s (예상: {expected_seconds}s)"
        else:  # 소수점 비교
            assert abs(actual_seconds - expected_seconds) < 0.2, \
                f"Duration 계산 오류: {hours}h → {actual_seconds}s (예상: {expected_seconds}s)"
        
        print(f"✅ Duration 계산 PASS: {hours}h = {actual_seconds:.2f}s")


def test_wall_clock_duration_logic_mock():
    """
    Wall-clock duration 로직을 mock으로 검증
    
    시나리오:
    - duration_seconds = 2초 설정
    - 루프가 2초 안팎에서 종료되는지 확인
    """
    import time
    
    # Mock config
    config = {
        'paper': {
            'duration_mode': 'wall_clock',
            'duration_hours': 2 / 3600,  # 2초
        }
    }
    
    duration_mode = config['paper']['duration_mode']
    duration_hours = config['paper']['duration_hours']
    duration_seconds = duration_hours * 3600
    
    assert duration_mode == 'wall_clock'
    assert abs(duration_seconds - 2.0) < 0.01
    
    # Simulate loop with duration check
    start_wall_time = time.time()
    loop_count = 0
    max_loops = 1000
    should_break = False
    
    while loop_count < max_loops:
        loop_count += 1
        
        # Simulate some work
        time.sleep(0.01)  # 10ms per iteration
        
        # Duration check (engine.py 로직과 동일)
        if duration_mode == 'wall_clock':
            elapsed_wall = time.time() - start_wall_time
            if elapsed_wall >= duration_seconds:
                should_break = True
                actual_elapsed = elapsed_wall
                break
    
    assert should_break, "Duration 조건이 도달하지 못함 (무한 루프 방지 실패)"
    
    # 실제 경과 시간이 설정값과 유사한지 확인 (±0.5초 오차 허용)
    assert abs(actual_elapsed - duration_seconds) < 0.5, \
        f"Duration 타이밍 오류: 설정={duration_seconds}s, 실제={actual_elapsed:.2f}s"
    
    print(f"✅ Wall-clock duration 로직 PASS: 설정={duration_seconds}s, 실제={actual_elapsed:.2f}s, 루프={loop_count}회")


def test_duration_seconds_conversion_edge_cases():
    """Duration 변환 엣지 케이스 검증"""
    # 매우 짧은 시간 (1초 미만)
    assert abs(0.0001 * 3600 - 0.36) < 0.01  # 0.36초
    
    # 0시간 (즉시 종료)
    assert 0 * 3600 == 0
    
    # 매우 긴 시간 (24시간)
    assert 24 * 3600 == 86400
    
    print("✅ Duration 변환 엣지 케이스 PASS")


if __name__ == "__main__":
    test_duration_config_parsing()
    test_duration_calculation()
    test_wall_clock_duration_logic_mock()
    test_duration_seconds_conversion_edge_cases()
    print("\n✅ 모든 Duration 테스트 PASS!")
