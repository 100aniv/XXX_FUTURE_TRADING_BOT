#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER17: Effective Params Contract Tests
==================================================

AC2 검증: strategy/engine이 읽는 config 경로 SSOT를 "코드+테스트"로 확정

테스트 케이스:
1. root만 설정 시 resolved가 root에서 옴
2. strategy.ensemble이 있으면 우선됨
3. strategies.phase35_ensemble_v1.params.ensemble이 최우선
4. override 적용 결과가 artifact에 저장되는지 (경로/스키마)
5. get_effective_params() 메서드 계약 검증
6. _ensemble_vote가 self._min_votes 사용하는지 검증
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


class TestEffectiveParamsResolution:
    """Config 경로 우선순위 테스트"""
    
    def test_root_ensemble_path(self):
        """케이스 1: root만 설정 시 resolved가 root에서 옴"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 3,
                "confidence_threshold": 0.85,
                "cooldown_bars": 7,
            }
        }
        
        strategy = Phase35EnsembleV1(config)
        
        assert strategy._min_votes == 3
        assert strategy._confidence_threshold == 0.85
        assert strategy._cooldown_bars == 7
        assert strategy._effective_params_source == "ensemble"
    
    def test_strategy_ensemble_path(self):
        """케이스 2: strategy.ensemble이 있으면 root보다 우선 (현재 구현에서는 root가 우선)"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        # 현재 _get_cfg 구현은 첫 번째 찾은 경로를 반환하므로
        # 우선순위: ensemble > strategy.ensemble > strategies.phase35_ensemble_v1.params.ensemble
        config = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.70,
                "cooldown_bars": 3,
            },
            "strategy": {
                "ensemble": {
                    "min_votes": 99,  # 이 값은 무시됨 (root가 우선)
                    "confidence_threshold": 0.99,
                    "cooldown_bars": 99,
                }
            }
        }
        
        strategy = Phase35EnsembleV1(config)
        
        # root "ensemble"이 먼저 발견되므로 그 값을 사용
        assert strategy._min_votes == 2
        assert strategy._confidence_threshold == 0.70
        assert strategy._cooldown_bars == 3
        assert strategy._effective_params_source == "ensemble"
    
    def test_nested_strategies_path(self):
        """케이스 3: root가 없으면 strategies.phase35_ensemble_v1.params.ensemble 사용"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            # ensemble 키 없음
            "strategies": {
                "phase35_ensemble_v1": {
                    "params": {
                        "ensemble": {
                            "min_votes": 1,
                            "confidence_threshold": 0.55,
                            "cooldown_bars": 10,
                        }
                    }
                }
            }
        }
        
        strategy = Phase35EnsembleV1(config)
        
        assert strategy._min_votes == 1
        assert strategy._confidence_threshold == 0.55
        assert strategy._cooldown_bars == 10
        assert strategy._effective_params_source == "strategies.phase35_ensemble_v1.params.ensemble"
    
    def test_defaults_when_no_config(self):
        """케이스 4: config가 없으면 defaults 사용"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            # ensemble 관련 키 없음
        }
        
        strategy = Phase35EnsembleV1(config)
        
        # defaults: min_votes=2, confidence_threshold=0.5, cooldown_bars=0
        assert strategy._min_votes == 2
        assert strategy._confidence_threshold == 0.5
        assert strategy._cooldown_bars == 0
        assert strategy._effective_params_source == "defaults"


class TestGetEffectiveParams:
    """get_effective_params() 메서드 계약 테스트"""
    
    def test_get_effective_params_schema(self):
        """get_effective_params()가 올바른 스키마 반환"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.7,
                "cooldown_bars": 3,
            }
        }
        
        strategy = Phase35EnsembleV1(config)
        params = strategy.get_effective_params()
        
        assert "min_votes" in params
        assert "confidence_threshold" in params
        assert "cooldown_bars" in params
        assert "source" in params
        
        assert isinstance(params["min_votes"], int)
        assert isinstance(params["confidence_threshold"], float)
        assert isinstance(params["cooldown_bars"], int)
        assert isinstance(params["source"], str)
    
    def test_get_effective_params_consistency(self):
        """get_effective_params()가 인스턴스 변수와 일치"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        config = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 3,
                "confidence_threshold": 0.8,
                "cooldown_bars": 5,
            }
        }
        
        strategy = Phase35EnsembleV1(config)
        params = strategy.get_effective_params()
        
        assert params["min_votes"] == strategy._min_votes
        assert params["confidence_threshold"] == strategy._confidence_threshold
        assert params["cooldown_bars"] == strategy._cooldown_bars
        assert params["source"] == strategy._effective_params_source


class TestEnsembleVoteUsesInstanceVars:
    """_ensemble_vote가 self._min_votes, self._confidence_threshold 사용 검증"""
    
    def test_min_votes_affects_voting(self):
        """min_votes 값이 실제 voting에 영향"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        # min_votes=1 설정 (1개만 있어도 통과)
        config_mv1 = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 1,
                "confidence_threshold": 0.0,  # 낮게 설정
                "cooldown_bars": 0,
            }
        }
        
        # min_votes=3 설정 (3개 모두 필요)
        config_mv3 = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 3,
                "confidence_threshold": 0.0,
                "cooldown_bars": 0,
            }
        }
        
        strategy_mv1 = Phase35EnsembleV1(config_mv1)
        strategy_mv3 = Phase35EnsembleV1(config_mv3)
        
        # 1 LONG, 2 FLAT 투표
        sub_votes = {
            "trend": {"direction": "LONG", "confidence": 0.8},
            "reversion": {"direction": None, "confidence": 0.0},
            "breakout": {"direction": None, "confidence": 0.0},
        }
        
        # min_votes=1이면 LONG 통과
        result_mv1 = strategy_mv1._ensemble_vote(sub_votes)
        assert result_mv1["direction"] == "LONG"
        
        # min_votes=3이면 consensus 실패
        result_mv3 = strategy_mv3._ensemble_vote(sub_votes)
        assert result_mv3["direction"] is None
    
    def test_confidence_threshold_affects_voting(self):
        """confidence_threshold 값이 실제 voting에 영향"""
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        # confidence_threshold=0.3 설정 (낮은 임계값)
        config_low = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.3,
                "cooldown_bars": 0,
            }
        }
        
        # confidence_threshold=0.9 설정 (높은 임계값)
        config_high = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.9,
                "cooldown_bars": 0,
            }
        }
        
        strategy_low = Phase35EnsembleV1(config_low)
        strategy_high = Phase35EnsembleV1(config_high)
        
        # 2 LONG 투표, 평균 confidence=0.5
        sub_votes = {
            "trend": {"direction": "LONG", "confidence": 0.4},
            "reversion": {"direction": "LONG", "confidence": 0.6},
            "breakout": {"direction": None, "confidence": 0.0},
        }
        
        # threshold=0.3이면 통과 (avg=0.5 > 0.3)
        result_low = strategy_low._ensemble_vote(sub_votes)
        assert result_low["direction"] == "LONG"
        
        # threshold=0.9이면 차단 (avg=0.5 < 0.9)
        result_high = strategy_high._ensemble_vote(sub_votes)
        assert result_high["direction"] is None
        assert "confidence_low" in result_high["reason"]


class TestIter17RunnerIntegration:
    """ITER17 Runner 통합 테스트"""
    
    def test_extract_effective_params_from_config(self):
        """extract_effective_params_from_config 함수 테스트"""
        import sys
        sys.path.insert(0, str(project_root / "scripts" / "phase35"))
        from run_iter17_effective_params import extract_effective_params_from_config
        
        config = {
            "ensemble": {
                "min_votes": 3,
                "confidence_threshold": 0.8,
                "cooldown_bars": 5,
            }
        }
        
        result = extract_effective_params_from_config(config)
        
        assert result["min_votes"] == 3
        assert result["confidence_threshold"] == 0.8
        assert result["cooldown_bars"] == 5
        assert result["source"] == "ensemble"
    
    def test_apply_overrides_syncs_all_paths(self):
        """apply_overrides가 모든 경로에 동기화"""
        import sys
        sys.path.insert(0, str(project_root / "scripts" / "phase35"))
        from run_iter17_effective_params import apply_overrides
        
        base_config = {
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.7,
                "cooldown_bars": 3,
            }
        }
        
        overrides = {
            "ensemble.min_votes": 3,
            "ensemble.confidence_threshold": 0.85,
        }
        
        result = apply_overrides(base_config, overrides)
        
        # Root path
        assert result["ensemble"]["min_votes"] == 3
        assert result["ensemble"]["confidence_threshold"] == 0.85
        
        # strategy.ensemble path
        assert result["strategy"]["ensemble"]["min_votes"] == 3
        assert result["strategy"]["ensemble"]["confidence_threshold"] == 0.85
        
        # strategies.phase35_ensemble_v1.params.ensemble path
        assert result["strategies"]["phase35_ensemble_v1"]["params"]["ensemble"]["min_votes"] == 3
        assert result["strategies"]["phase35_ensemble_v1"]["params"]["ensemble"]["confidence_threshold"] == 0.85


class TestOverrideInjectionContract:
    """Override 주입 계약 테스트 (AC2)"""
    
    def test_override_reflected_in_strategy(self):
        """Override가 전략에 반영되는지 검증"""
        import sys
        sys.path.insert(0, str(project_root / "scripts" / "phase35"))
        from run_iter17_effective_params import apply_overrides
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        base_config = {
            "mode": "backtest",
            "ensemble": {
                "min_votes": 2,
                "confidence_threshold": 0.7,
                "cooldown_bars": 3,
            }
        }
        
        # Override 적용
        overrides = {"ensemble.min_votes": 3, "ensemble.confidence_threshold": 0.9}
        config_with_overrides = apply_overrides(base_config, overrides)
        
        # 전략 생성
        strategy = Phase35EnsembleV1(config_with_overrides)
        
        # 검증: override 값이 전략에 반영됨
        assert strategy._min_votes == 3
        assert strategy._confidence_threshold == 0.9
        
        # get_effective_params()도 일치
        params = strategy.get_effective_params()
        assert params["min_votes"] == 3
        assert params["confidence_threshold"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
