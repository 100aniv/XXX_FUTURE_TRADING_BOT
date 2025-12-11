#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3.2: Duration Backtest Unlimited 테스트
===============================================
Backtest 모드에서 Duration이 unlimited로 동작하는지 검증
"""
import pytest
from execution.engine import _init_duration_state


class TestDurationBacktest:
    """Duration 초기화 테스트 (Backtest/Paper/Live 모드별)"""
    
    def test_backtest_mode_unlimited(self):
        """
        Backtest 모드: Duration unlimited 자동 설정
        """
        config = {
            'mode': 'backtest',
            # paper 섹션 없음 (Backtest Config 구조)
        }
        
        result = _init_duration_state(config, 'backtest')
        
        assert result['duration_mode'] == 'unlimited', \
            "Backtest 모드에서는 duration_mode가 unlimited여야 함"
        assert result['duration_hours'] == 0, \
            "Backtest 모드에서는 duration_hours가 0이어야 함"
        assert result['duration_seconds'] == 0, \
            "Backtest 모드에서는 duration_seconds가 0이어야 함"
        assert 'start_wall_time' in result, \
            "start_wall_time이 반환되어야 함"
    
    def test_paper_mode_market_time_default(self):
        """
        Paper 모드: 기본값 (market_time, 1시간)
        """
        config = {
            'mode': 'paper',
            # paper 섹션 없음 → 기본값 사용
        }
        
        result = _init_duration_state(config, 'paper')
        
        assert result['duration_mode'] == 'market_time', \
            "Paper 모드 기본값은 market_time이어야 함"
        assert result['duration_hours'] == 1, \
            "Paper 모드 기본값은 1시간이어야 함"
        assert result['duration_seconds'] == 3600, \
            "Paper 모드 기본값은 3600초여야 함"
    
    def test_paper_mode_wall_clock(self):
        """
        Paper 모드: wall_clock 명시 + 2.5시간
        """
        config = {
            'mode': 'paper',
            'paper': {
                'duration_mode': 'wall_clock',
                'duration_hours': 2.5
            }
        }
        
        result = _init_duration_state(config, 'paper')
        
        assert result['duration_mode'] == 'wall_clock', \
            "Paper Config에서 wall_clock 설정이 반영되어야 함"
        assert result['duration_hours'] == 2.5, \
            "Paper Config에서 duration_hours 설정이 반영되어야 함"
        assert result['duration_seconds'] == 2.5 * 3600, \
            "duration_seconds가 올바르게 계산되어야 함"
    
    def test_paper_mode_duration_zero(self):
        """
        Paper 모드: duration_hours = 0 → unlimited 전환
        """
        config = {
            'mode': 'paper',
            'paper': {
                'duration_hours': 0
            }
        }
        
        result = _init_duration_state(config, 'paper')
        
        assert result['duration_mode'] == 'unlimited', \
            "duration_hours가 0이면 unlimited로 전환되어야 함"
        assert result['duration_hours'] == 0, \
            "duration_hours가 0으로 설정되어야 함"
        assert result['duration_seconds'] == 0, \
            "duration_seconds가 0으로 설정되어야 함"
    
    def test_paper_mode_duration_negative(self):
        """
        Paper 모드: duration_hours < 0 → unlimited 전환 + warning
        """
        config = {
            'mode': 'paper',
            'paper': {
                'duration_hours': -1
            }
        }
        
        result = _init_duration_state(config, 'paper')
        
        assert result['duration_mode'] == 'unlimited', \
            "duration_hours가 음수면 unlimited로 전환되어야 함"
        assert result['duration_hours'] == 0, \
            "duration_hours가 0으로 설정되어야 함"
    
    def test_live_mode_default(self):
        """
        Live 모드: Paper와 동일한 로직 (market_time 기본)
        """
        config = {
            'mode': 'live',
            # paper 섹션 없음
        }
        
        result = _init_duration_state(config, 'live')
        
        assert result['duration_mode'] == 'market_time', \
            "Live 모드 기본값은 market_time이어야 함"
        assert result['duration_hours'] == 1, \
            "Live 모드 기본값은 1시간이어야 함"


class TestDurationIntegration:
    """Duration 초기화 통합 테스트 (Config 구조 검증)"""
    
    def test_backtest_config_structure(self):
        """
        실제 Backtest Config 구조 시뮬레이션
        """
        config = {
            'mode': 'backtest',
            'env': 'backtest',
            'symbol': 'BTCUSDT',
            'timeframe': '5m',
            'backtest': {
                'start_date': '2024-11-24 00:00:00',
                'end_date': '2024-11-25 00:00:00',
                'duration_minutes': 1440  # 이 값은 무시되어야 함
            }
            # paper 섹션 없음
        }
        
        result = _init_duration_state(config, config['mode'])
        
        assert result['duration_mode'] == 'unlimited', \
            "Backtest Config에서는 duration_mode가 unlimited여야 함"
        # backtest.duration_minutes는 무시되고, start/end 날짜로 범위가 정해짐
    
    def test_paper_config_structure(self):
        """
        실제 Paper Config 구조 시뮬레이션
        """
        config = {
            'mode': 'paper',
            'env': 'paper',
            'symbol': 'BTCUSDT',
            'timeframe': '5m',
            'paper': {
                'duration_mode': 'wall_clock',
                'duration_hours': 12
            }
        }
        
        result = _init_duration_state(config, config['mode'])
        
        assert result['duration_mode'] == 'wall_clock'
        assert result['duration_hours'] == 12
        assert result['duration_seconds'] == 12 * 3600


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
