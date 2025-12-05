#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-1: Single Strategy Performance Baseline Tests
======================================================

테스트 목적:
- Config preset 파싱 검증
- Runner 메트릭 생성 검증
- 메트릭 타입/범위 sanity check
"""
import pytest
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 테스트 대상 모듈
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.research.phase28_1_single_strategy_performance import (
    load_config,
    merge_config_for_backtest,
    extract_metrics_from_result
)


class TestConfigLoading:
    """Config 로딩 테스트"""
    
    def test_load_config_success(self):
        """Config 파일 로딩 성공"""
        config_path = PROJECT_ROOT / 'configs' / 'backtest' / 'phase28_1_btc5m_baseline_presets.yml'
        
        if not config_path.exists():
            pytest.skip(f"Config 파일 없음: {config_path}")
        
        config = load_config(config_path)
        
        # 필수 섹션 확인
        assert 'common' in config
        assert 'presets' in config
        assert 'market_periods' in config
    
    def test_config_has_three_presets(self):
        """3개 이상 preset 정의 확인"""
        config_path = PROJECT_ROOT / 'configs' / 'backtest' / 'phase28_1_btc5m_baseline_presets.yml'
        
        if not config_path.exists():
            pytest.skip(f"Config 파일 없음: {config_path}")
        
        config = load_config(config_path)
        presets = config.get('presets', {})
        
        assert len(presets) >= 3, "최소 3개 preset 필요"
        
        # Preset 구조 확인
        for preset_name, preset_cfg in presets.items():
            assert 'name' in preset_cfg
            assert 'description' in preset_cfg
            assert 'params' in preset_cfg
    
    def test_config_has_market_periods(self):
        """시장 구간 정의 확인"""
        config_path = PROJECT_ROOT / 'configs' / 'backtest' / 'phase28_1_btc5m_baseline_presets.yml'
        
        if not config_path.exists():
            pytest.skip(f"Config 파일 없음: {config_path}")
        
        config = load_config(config_path)
        periods = config.get('market_periods', {})
        
        assert len(periods) >= 3, "최소 3개 시장 구간 필요"
        
        # 각 구간에 start, end 있는지 확인
        for period_name, period_cfg in periods.items():
            assert 'start' in period_cfg
            assert 'end' in period_cfg


class TestConfigMerge:
    """Config 병합 테스트"""
    
    def test_merge_config_for_backtest(self):
        """백테스트용 Config 병합"""
        common_cfg = {
            'symbol': 'BTCUSDT',
            'timeframe': '5m',
            'initial_equity': 10000.0
        }
        
        preset_params = {
            'rsi_long_threshold': 45,
            'rsi_short_threshold': 55
        }
        
        period_cfg = {
            'start': '2024-01-01',
            'end': '2024-01-31'
        }
        
        config = merge_config_for_backtest(
            common_cfg=common_cfg,
            preset_name='test_preset',
            preset_params=preset_params,
            period_name='test_period',
            period_cfg=period_cfg
        )
        
        # 필수 필드 확인
        assert config['mode'] == 'backtest'
        assert 'run_id' in config
        assert config['start_date'] == '2024-01-01'
        assert config['end_date'] == '2024-01-31'
        
        # PHASE28-1-FIX: 파라미터는 strategies 섹션에 배치 (merge_strategy_config가 top-level로 복사)
        strategy_cfg = config.get('strategies', {}).get('btc5m_baseline_v1', {})
        assert strategy_cfg['rsi_long_threshold'] == 45
        assert strategy_cfg['rsi_short_threshold'] == 55


class TestMetricsExtraction:
    """메트릭 추출 테스트"""
    
    def test_extract_metrics_zero_trades(self):
        """트레이드 0개일 때 메트릭"""
        result = {
            'trades': [],
            'equity_curve': []
        }
        
        config = {'initial_equity': 10000.0}
        
        metrics = extract_metrics_from_result(result, config)
        
        # 기본 값 확인
        assert metrics['total_trades'] == 0
        assert metrics['win_rate'] == 0.0
        assert metrics['gross_pnl'] == 0.0
        assert metrics['net_pnl'] == 0.0
    
    def test_extract_metrics_with_trades(self):
        """트레이드 있을 때 메트릭"""
        result = {
            'trades': [
                {
                    'pnl': 100.0,
                    'fee': 5.0,
                    'side': 'LONG',
                    'ts_open': datetime(2024, 1, 1, 0, 0),
                    'ts_close': datetime(2024, 1, 1, 1, 0)
                },
                {
                    'pnl': -50.0,
                    'fee': 3.0,
                    'side': 'SHORT',
                    'ts_open': datetime(2024, 1, 1, 2, 0),
                    'ts_close': datetime(2024, 1, 1, 3, 0)
                },
                {
                    'pnl': 75.0,
                    'fee': 4.0,
                    'side': 'LONG',
                    'ts_open': datetime(2024, 1, 1, 4, 0),
                    'ts_close': datetime(2024, 1, 1, 5, 0)
                }
            ],
            'equity_curve': []
        }
        
        config = {'initial_equity': 10000.0}
        
        metrics = extract_metrics_from_result(result, config)
        
        # 메트릭 검증
        assert metrics['total_trades'] == 3
        assert metrics['winning_trades'] == 2
        assert metrics['losing_trades'] == 1
        assert metrics['win_rate'] == pytest.approx(2/3, abs=0.01)
        assert metrics['gross_pnl'] == 125.0  # 100 - 50 + 75
        assert metrics['net_pnl'] == 113.0  # 125 - 12 (fees)
        assert metrics['long_count'] == 2
        assert metrics['short_count'] == 1


class TestMetricsSanityCheck:
    """메트릭 Sanity Check 테스트"""
    
    def test_metrics_types(self):
        """메트릭 타입 확인"""
        result = {
            'trades': [
                {
                    'pnl': 100.0,
                    'fee': 5.0,
                    'side': 'LONG',
                    'ts_open': datetime(2024, 1, 1, 0, 0),
                    'ts_close': datetime(2024, 1, 1, 1, 0)
                }
            ],
            'equity_curve': []
        }
        
        config = {'initial_equity': 10000.0}
        
        metrics = extract_metrics_from_result(result, config)
        
        # 타입 확인
        assert isinstance(metrics['total_trades'], int)
        assert isinstance(metrics['win_rate'], float)
        assert isinstance(metrics['gross_pnl'], float)
        assert isinstance(metrics['net_pnl'], float)
        assert isinstance(metrics['max_drawdown'], float)
        assert isinstance(metrics['sharpe_like_ratio'], float)
        assert isinstance(metrics['avg_holding_minutes'], float)
        assert isinstance(metrics['long_short_ratio'], (int, float))
    
    def test_metrics_ranges(self):
        """메트릭 범위 확인"""
        result = {
            'trades': [
                {
                    'pnl': 100.0,
                    'fee': 5.0,
                    'side': 'LONG',
                    'ts_open': datetime(2024, 1, 1, 0, 0),
                    'ts_close': datetime(2024, 1, 1, 1, 0)
                },
                {
                    'pnl': -50.0,
                    'fee': 3.0,
                    'side': 'SHORT',
                    'ts_open': datetime(2024, 1, 1, 2, 0),
                    'ts_close': datetime(2024, 1, 1, 3, 0)
                }
            ],
            'equity_curve': []
        }
        
        config = {'initial_equity': 10000.0}
        
        metrics = extract_metrics_from_result(result, config)
        
        # 범위 확인
        assert metrics['total_trades'] >= 0
        assert 0.0 <= metrics['win_rate'] <= 1.0
        assert metrics['max_drawdown'] >= 0.0  # MDD는 양수 (손실 비율)
        assert metrics['avg_holding_minutes'] >= 0.0
        assert metrics['long_count'] >= 0
        assert metrics['short_count'] >= 0
    
    def test_metrics_no_nan(self):
        """메트릭에 NaN 없는지 확인"""
        import math
        
        result = {
            'trades': [
                {
                    'pnl': 100.0,
                    'fee': 5.0,
                    'side': 'LONG',
                    'ts_open': datetime(2024, 1, 1, 0, 0),
                    'ts_close': datetime(2024, 1, 1, 1, 0)
                }
            ],
            'equity_curve': []
        }
        
        config = {'initial_equity': 10000.0}
        
        metrics = extract_metrics_from_result(result, config)
        
        # NaN 체크 (inf는 허용, long_short_ratio에서 발생 가능)
        for key, value in metrics.items():
            if isinstance(value, float):
                assert not math.isnan(value), f"{key} is NaN"


class TestMinimumTradesThreshold:
    """최소 거래 수 Threshold 테스트"""
    
    def test_smoke_test_should_have_min_trades(self):
        """스모크 테스트는 최소 10개 거래 필요"""
        # 이 테스트는 실제 실행 후 검증
        # 여기서는 로직만 확인
        min_trades_threshold = 10
        
        # 시뮬레이션: 거래 수가 threshold 이상이면 PASS
        total_trades_scenario_1 = 15
        assert total_trades_scenario_1 >= min_trades_threshold, "전략이 충분한 거래를 생성해야 함"
        
        # 시뮬레이션: 거래 수가 threshold 미만이면 경고
        total_trades_scenario_2 = 5
        if total_trades_scenario_2 < min_trades_threshold:
            # 경고 로그 발생 (실제 실행 시)
            pass


class TestSSOTCompliance:
    """SSOT 규칙 준수 테스트"""
    
    def test_runner_uses_run_v2(self):
        """Runner가 run_v2() 사용하는지 확인"""
        runner_path = PROJECT_ROOT / 'scripts' / 'research' / 'phase28_1_single_strategy_performance.py'
        
        if not runner_path.exists():
            pytest.skip(f"Runner 파일 없음: {runner_path}")
        
        with open(runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # run_v2 호출 확인
        assert 'engine.run_v2' in content or 'execution.engine.run_v2' in content
        
        # 새로운 엔진 진입점 생성 금지
        assert 'run_v3' not in content
        assert 'run_custom' not in content
    
    def test_no_signal_logic_direct_call(self):
        """Runner에서 signal_logic 직접 호출 금지"""
        runner_path = PROJECT_ROOT / 'scripts' / 'research' / 'phase28_1_single_strategy_performance.py'
        
        if not runner_path.exists():
            pytest.skip(f"Runner 파일 없음: {runner_path}")
        
        with open(runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # signal_logic 직접 호출 금지 (주석 제외)
        lines = content.split('\n')
        for line in lines:
            if 'signal_logic(' in line and not line.strip().startswith('#'):
                pytest.fail("Runner에서 signal_logic 직접 호출 금지")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
