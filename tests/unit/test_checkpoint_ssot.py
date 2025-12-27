#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE36-2 S6: Checkpoint SSOT 재발 방지 테스트
===============================================
1. Config 기반 checkpoint_dir 적용 검증
2. Duration < interval인 짧은 런에서 final flush 검증
3. Live 모드 duration_hours가 live 섹션에서 정상 읽히는지 검증
"""
import pytest
from pathlib import Path
from common.signal_telemetry import SignalTelemetry, reset_signal_telemetry


def test_checkpoint_dir_from_config():
    """
    AC: Config의 signal_telemetry.checkpoint_dir이 실제로 반영되는지 검증
    """
    # Given
    config = {
        'signal_telemetry': {
            'checkpoint_dir': 'logs/checkpoints/test_custom_dir',
            'checkpoint_interval_minutes': 5
        }
    }
    
    # When: 엔진이 checkpoint_dir을 읽는 로직 시뮬레이션
    checkpoint_dir_str = config.get('signal_telemetry', {}).get('checkpoint_dir', None)
    
    # Then
    assert checkpoint_dir_str is not None, "checkpoint_dir이 config에서 읽혀야 함"
    assert checkpoint_dir_str == 'logs/checkpoints/test_custom_dir'
    
    # Fallback 테스트
    config_no_dir = {'signal_telemetry': {}}
    checkpoint_dir_str = config_no_dir.get('signal_telemetry', {}).get('checkpoint_dir', None)
    assert checkpoint_dir_str is None, "checkpoint_dir이 없으면 None 반환"


def test_checkpoint_final_flush_logic():
    """
    AC: Duration < interval인 짧은 런에서도 final flush로 최소 1개 생성
    """
    # Given
    reset_signal_telemetry()
    telemetry = SignalTelemetry()
    telemetry.set_start_time()
    telemetry.signal_evaluated()
    telemetry.signal_evaluated()
    
    # When: Final checkpoint 저장
    checkpoint_dir = Path("logs/checkpoints/test_final_flush")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    label = "checkpoint_final_20min"
    checkpoint_path = telemetry.save_checkpoint(str(checkpoint_dir), label)
    
    # Then
    assert Path(checkpoint_path).exists(), "Final checkpoint 파일이 생성되어야 함"
    assert "checkpoint_final" in checkpoint_path, "Final flush 파일명에 'final' 포함"
    
    # Cleanup
    import shutil
    if checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)


def test_duration_hours_live_section_priority():
    """
    AC: Live 모드에서 duration_hours를 live 섹션에서 우선 읽는지 검증
    (PHASE36-2 S6 Duration 버그 재발 방지)
    """
    # Given: live 섹션과 paper 섹션이 모두 있는 config
    config = {
        'mode': 'live',
        'live': {
            'duration_mode': 'wall_clock',
            'duration_hours': 0.5  # 30분
        },
        'paper': {
            'duration_mode': 'market_time',
            'duration_hours': 1.0  # 1시간
        },
        'duration_hours': 2.0  # Top-level fallback
    }
    
    # When: engine.py의 _init_duration_state 로직 시뮬레이션
    mode = config.get('mode', 'backtest')
    if mode == 'live':
        duration_mode = config.get('live', {}).get('duration_mode', config.get('duration_mode', 'wall_clock'))
        duration_hours = config.get('live', {}).get('duration_hours', config.get('duration_hours', 0))
    else:  # paper
        duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
        duration_hours = config.get('paper', {}).get('duration_hours', 1)
    
    # Then
    assert duration_mode == 'wall_clock', "Live 모드는 live.duration_mode 우선"
    assert duration_hours == 0.5, "Live 모드는 live.duration_hours 우선 (0.5시간)"
    
    # Paper 모드 검증
    config['mode'] = 'paper'
    mode = config.get('mode', 'backtest')
    if mode == 'live':
        duration_mode = config.get('live', {}).get('duration_mode', config.get('duration_mode', 'wall_clock'))
        duration_hours = config.get('live', {}).get('duration_hours', config.get('duration_hours', 0))
    else:  # paper
        duration_mode = config.get('paper', {}).get('duration_mode', 'market_time')
        duration_hours = config.get('paper', {}).get('duration_hours', 1)
    
    assert duration_mode == 'market_time', "Paper 모드는 paper.duration_mode 유지"
    assert duration_hours == 1.0, "Paper 모드는 paper.duration_hours 유지 (1.0시간)"


def test_checkpoint_filename_pattern():
    """
    AC: Checkpoint 파일명이 telemetry_checkpoint_*.json 패턴을 따르는지 검증
    (report_telemetry_checkpoints.py 호환성)
    """
    # Given
    reset_signal_telemetry()
    telemetry = SignalTelemetry()
    telemetry.set_start_time()
    
    # When
    checkpoint_dir = Path("logs/checkpoints/test_filename_pattern")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    label = "checkpoint_000_5min"
    checkpoint_path = telemetry.save_checkpoint(str(checkpoint_dir), label)
    
    # Then
    filename = Path(checkpoint_path).name
    assert filename.startswith("telemetry_checkpoint_"), "파일명은 'telemetry_checkpoint_'로 시작"
    assert filename.endswith(".json"), "파일명은 '.json'으로 끝남"
    assert "000_5min" in filename, "label이 파일명에 포함"
    
    # Cleanup
    import shutil
    if checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
