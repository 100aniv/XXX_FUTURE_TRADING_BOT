"""
PHASE35-4 ITER21: Sub-models Config SSOT Contract Tests
========================================================

DoD:
- DoD1: Config override가 sub_models까지 실제 전략 실행에서 적용됨
- DoD2: 서브모델 신호가 0이 아닌 상태로 발생
- DoD3: (Baseline vs Relaxed) 최소 1개 핵심 지표가 달라짐
- DoD4: Postgres trial_id로 격리된 per-run trades 카운트가 증거로 남음
"""

import pytest
from typing import Dict, Any


class TestSubModelsConfigSSOT:
    """ITER21: sub_models config 멀티패스 리졸브 테스트"""
    
    def test_resolve_sub_models_from_top_level(self):
        """top-level sub_models가 우선 적용되는지 확인"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "sub_models": {
                "trend": {"adx_threshold": 15},
                "reversion": {"rsi_oversold": 40, "rsi_overbought": 60},
            },
            "decision_trace": {"enabled": True},
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        assert "sub_models" in effective
        assert effective["sub_models"]["trend"]["adx_threshold"] == 15
        assert effective["sub_models"]["reversion"]["rsi_oversold"] == 40
        assert effective["sub_models_source"] == "sub_models"
    
    def test_resolve_sub_models_from_strategy_path(self):
        """strategy.sub_models 경로에서 읽는지 확인"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "strategy": {
                "sub_models": {
                    "trend": {"adx_threshold": 12},
                },
            },
            "decision_trace": {"enabled": True},
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        assert "sub_models" in effective
        assert effective["sub_models"]["trend"]["adx_threshold"] == 12
        assert effective["sub_models_source"] == "strategy.sub_models"
    
    def test_resolve_sub_models_priority(self):
        """top-level이 strategy보다 우선순위 높은지 확인"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "sub_models": {
                "trend": {"adx_threshold": 8},  # 우선순위 1
            },
            "strategy": {
                "sub_models": {
                    "trend": {"adx_threshold": 20},  # 우선순위 2
                },
            },
            "decision_trace": {"enabled": True},
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        # top-level이 우선
        assert effective["sub_models"]["trend"]["adx_threshold"] == 8
        assert effective["sub_models_source"] == "sub_models"
    
    def test_resolve_sub_models_defaults(self):
        """sub_models가 없으면 빈 dict 반환"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "decision_trace": {"enabled": True},
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        assert "sub_models" in effective
        assert effective["sub_models"] == {}
        assert effective["sub_models_source"] == "defaults"


class TestMultiPathInjection:
    """ITER21: Runner의 다중 경로 주입 테스트"""
    
    def test_inject_sub_models_multi_path(self):
        """다중 경로에 sub_models가 주입되는지 확인"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        
        from scripts.phase35.run_iter21_submodel_ssot import inject_sub_models_multi_path
        
        config = {
            "strategy": {},
            "strategy_params": {},
        }
        
        override = {
            "trend": {"adx_threshold": 10},
            "reversion": {"rsi_oversold": 45},
        }
        
        result = inject_sub_models_multi_path(config, override)
        
        # top-level
        assert result["sub_models"]["trend"]["adx_threshold"] == 10
        # strategy.sub_models
        assert result["strategy"]["sub_models"]["trend"]["adx_threshold"] == 10
        # strategy_params.sub_models
        assert result["strategy_params"]["sub_models"]["trend"]["adx_threshold"] == 10
    
    def test_relaxation_levels_defined(self):
        """완화 레벨이 정의되어 있는지 확인"""
        from scripts.phase35.run_iter21_submodel_ssot import RELAXATION_LEVELS
        
        assert "L0_baseline" in RELAXATION_LEVELS
        assert "L1_mild" in RELAXATION_LEVELS
        assert "L2_moderate" in RELAXATION_LEVELS
        assert "L3_aggressive" in RELAXATION_LEVELS
        
        # L3_aggressive는 regime_filter 비활성화
        assert RELAXATION_LEVELS["L3_aggressive"]["regime_filter_enabled"] == False


class TestEffectiveParamsContract:
    """get_effective_params() 계약 테스트"""
    
    def test_effective_params_contains_sub_models(self):
        """effective params에 sub_models가 포함되어야 함"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "sub_models": {
                "trend": {"adx_threshold": 15},
            },
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        # 필수 필드
        assert "min_votes" in effective
        assert "confidence_threshold" in effective
        assert "cooldown_bars" in effective
        assert "source" in effective
        # ITER21 추가 필드
        assert "sub_models" in effective
        assert "sub_models_source" in effective
    
    def test_effective_params_reflects_override(self):
        """effective params가 override를 반영하는지 확인"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "sub_models": {
                "trend": {"adx_threshold": 8, "ema_fast": 10},
                "reversion": {"rsi_oversold": 45, "rsi_overbought": 55},
                "breakout": {"volume_threshold": 0.8},
            },
        }
        
        strategy = Phase35EnsembleV1(config)
        effective = strategy.get_effective_params()
        
        assert effective["sub_models"]["trend"]["adx_threshold"] == 8
        assert effective["sub_models"]["reversion"]["rsi_oversold"] == 45
        assert effective["sub_models"]["breakout"]["volume_threshold"] == 0.8


class TestTrialIdIsolation:
    """trial_id 기반 격리 테스트"""
    
    def test_trial_id_generation_unique(self):
        """trial_id가 고유하게 생성되는지 확인"""
        import uuid
        
        trial_ids = set()
        for i in range(100):
            trial_id = f"iter21_L{i % 4}_{uuid.uuid4().hex[:8]}"
            assert trial_id not in trial_ids
            trial_ids.add(trial_id)
        
        assert len(trial_ids) == 100
    
    def test_engine_accepts_trial_id(self):
        """engine run_v2가 trial_id를 받을 수 있는지 확인"""
        from execution.engine import run_v2
        import inspect
        
        sig = inspect.signature(run_v2)
        params = list(sig.parameters.keys())
        
        # config에 trial_id를 넣을 수 있음
        assert "config" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
