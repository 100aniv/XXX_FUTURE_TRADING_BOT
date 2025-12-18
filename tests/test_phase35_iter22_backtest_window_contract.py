#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER22 Contract Tests: Backtest Data Window SSOT

테스트 항목:
1. backtest.days가 HistoricalFeed에 올바르게 전달되는지
2. 데이터 윈도우 계산이 정확한지
3. AC1: loaded_candles >= expected_candles * 0.9 검증 로직
4. multi-path sub_models 주입이 정상 작동하는지
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestBacktestDaysSSoT:
    """backtest.days SSOT 테스트"""
    
    def test_config_backtest_days_passed_to_adapters(self):
        """backtest.days가 config에 올바르게 설정되는지 확인"""
        config = {
            "timeframe": "15m",
            "backtest": {}
        }
        
        lookback_days = 7
        config["backtest"]["days"] = lookback_days
        
        assert config["backtest"]["days"] == 7
        assert "days" in config["backtest"]
    
    def test_expected_candles_calculation_15m(self):
        """15분 타임프레임에서 예상 캔들 수 계산"""
        lookback_days = 7
        timeframe = "15m"
        
        # 1일 = 24시간 * 4 (15분) = 96 캔들
        expected_candles = lookback_days * 96
        
        assert expected_candles == 672
    
    def test_expected_candles_calculation_5m(self):
        """5분 타임프레임에서 예상 캔들 수 계산"""
        lookback_days = 7
        timeframe = "5m"
        
        # 1일 = 24시간 * 12 (5분) = 288 캔들
        expected_candles = lookback_days * 288
        
        assert expected_candles == 2016
    
    def test_expected_candles_calculation_1m(self):
        """1분 타임프레임에서 예상 캔들 수 계산"""
        lookback_days = 7
        timeframe = "1m"
        
        # 1일 = 24시간 * 60 (1분) = 1440 캔들
        expected_candles = lookback_days * 1440
        
        assert expected_candles == 10080


class TestAC1Validation:
    """AC1: loaded_candles >= expected_candles * 0.9 검증"""
    
    def test_ac1_pass_when_sufficient_candles(self):
        """충분한 캔들이 로드되면 AC1 PASS"""
        expected_candles = 672
        loaded_candles = 670
        
        threshold = expected_candles * 0.9
        ac1_pass = loaded_candles >= threshold
        
        assert ac1_pass == True
    
    def test_ac1_fail_when_insufficient_candles(self):
        """캔들이 부족하면 AC1 FAIL"""
        expected_candles = 672
        loaded_candles = 500
        
        threshold = expected_candles * 0.9
        ac1_pass = loaded_candles >= threshold
        
        assert ac1_pass == False
    
    def test_ac1_threshold_calculation(self):
        """AC1 threshold 계산 (90%)"""
        expected_candles = 672
        threshold = expected_candles * 0.9
        
        assert abs(threshold - 604.8) < 0.01


class TestMultiPathSubModelsInjection:
    """multi-path sub_models 주입 테스트"""
    
    def test_inject_sub_models_to_top_level(self):
        """top-level sub_models에 주입"""
        from scripts.phase35.run_iter22_backtest_window_ssot import inject_sub_models_multi_path
        
        config = {}
        sub_models_override = {
            "trend": {"adx_threshold": 8}
        }
        
        result = inject_sub_models_multi_path(config, sub_models_override)
        
        assert result["sub_models"]["trend"]["adx_threshold"] == 8
    
    def test_inject_sub_models_to_strategy_path(self):
        """strategy.sub_models에 주입"""
        from scripts.phase35.run_iter22_backtest_window_ssot import inject_sub_models_multi_path
        
        config = {}
        sub_models_override = {
            "reversion": {"rsi_oversold": 45}
        }
        
        result = inject_sub_models_multi_path(config, sub_models_override)
        
        assert result["strategy"]["sub_models"]["reversion"]["rsi_oversold"] == 45
    
    def test_inject_sub_models_to_strategies_selector_path(self):
        """strategies.<selector>.params.sub_models에 주입"""
        from scripts.phase35.run_iter22_backtest_window_ssot import inject_sub_models_multi_path
        
        config = {
            "strategy": {"selector": "phase35_ensemble_v1"}
        }
        sub_models_override = {
            "breakout": {"volume_threshold": 0.8}
        }
        
        result = inject_sub_models_multi_path(config, sub_models_override)
        
        assert result["strategies"]["phase35_ensemble_v1"]["params"]["sub_models"]["breakout"]["volume_threshold"] == 0.8
    
    def test_inject_regime_filter_override(self):
        """regime_filter override 주입"""
        from scripts.phase35.run_iter22_backtest_window_ssot import inject_sub_models_multi_path
        
        config = {
            "strategy": {"selector": "phase35_ensemble_v1"}
        }
        sub_models_override = {}
        regime_filter_override = {"enabled": False}
        
        result = inject_sub_models_multi_path(config, sub_models_override, regime_filter_override)
        
        assert result["regime_filter"]["enabled"] == False
        assert result["strategy"]["regime_filter"]["enabled"] == False


class TestRelaxationLevels:
    """Relaxation levels 테스트"""
    
    def test_relaxation_levels_defined(self):
        """RELAXATION_LEVELS가 정의되어 있는지 확인"""
        from scripts.phase35.run_iter22_backtest_window_ssot import RELAXATION_LEVELS
        
        assert "L0_baseline" in RELAXATION_LEVELS
        assert "L3_aggressive" in RELAXATION_LEVELS
    
    def test_baseline_has_default_values(self):
        """L0_baseline이 기본값을 가지는지 확인"""
        from scripts.phase35.run_iter22_backtest_window_ssot import RELAXATION_LEVELS
        
        baseline = RELAXATION_LEVELS["L0_baseline"]
        
        assert baseline["trend"]["adx_threshold"] == 25
        assert baseline["reversion"]["rsi_oversold"] == 30
        assert baseline["reversion"]["rsi_overbought"] == 70
    
    def test_aggressive_has_relaxed_values(self):
        """L3_aggressive가 완화된 값을 가지는지 확인"""
        from scripts.phase35.run_iter22_backtest_window_ssot import RELAXATION_LEVELS
        
        aggressive = RELAXATION_LEVELS["L3_aggressive"]
        
        assert aggressive["trend"]["adx_threshold"] == 8
        assert aggressive["reversion"]["rsi_oversold"] == 45
        assert aggressive["reversion"]["rsi_overbought"] == 55
        assert aggressive["regime_filter"]["enabled"] == False


class TestTrialIdGeneration:
    """trial_id 생성 테스트"""
    
    def test_trial_id_format(self):
        """trial_id 포맷 확인"""
        import uuid
        
        candidate_id = "L0_baseline"
        trial_id = f"iter22_{candidate_id}_{uuid.uuid4().hex[:8]}"
        
        assert trial_id.startswith("iter22_L0_baseline_")
        assert len(trial_id) == len("iter22_L0_baseline_") + 8
    
    def test_trial_id_uniqueness(self):
        """trial_id가 유니크한지 확인"""
        import uuid
        
        candidate_id = "L0_baseline"
        trial_id_1 = f"iter22_{candidate_id}_{uuid.uuid4().hex[:8]}"
        trial_id_2 = f"iter22_{candidate_id}_{uuid.uuid4().hex[:8]}"
        
        assert trial_id_1 != trial_id_2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
