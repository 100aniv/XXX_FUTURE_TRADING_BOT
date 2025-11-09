#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnsembleTuner 단위 테스트
=========================
PR13 Phase 1: EnsembleTuner 구현 검증

참조:
- docs/PHASE6/PR13_ARCHITECTURE_DESIGN.md (2.2 EnsembleTuner)
- docs/PHASE6/PR13_BUG #8_ADD.md (Unit 테스트 매트릭스)

테스트 항목:
- 파라미터 샘플링 검증
- 제약 조건 검증 (가중치 합 1.0 ± 0.1)
- 스코어 계산 검증
- 오버레이 구조 검증
"""
import pytest
import tempfile
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from tuning.ensemble_tuner import EnsembleTuner, EnsembleMetrics
from tuning.config_overlay import ConfigOverlay


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def base_config():
    """기본 설정"""
    return {
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "strategies": {
            "ensemble": {
                "alpha_winrate": 0.4,
                "beta_rr": 0.2,
                "gamma_sharpe": 0.2,
                "delta_confidence": 0.15,
                "epsilon_regime": 0.05,
                "weights": {
                    "trend": 2.0,
                    "reversion": 2.0,
                    "breakout": 2.0,
                    "scalping": 1.5,
                    "daytrade": 1.5,
                    "swing": 1.5
                }
            }
        }
    }


@pytest.fixture
def config_overlay(base_config):
    """ConfigOverlay 인스턴스"""
    return ConfigOverlay(
        base_config_path="config.yml",
        base_config=base_config
    )


@pytest.fixture
def ensemble_tuner(config_overlay):
    """EnsembleTuner 인스턴스"""
    # 메모리 DB 사용 (파일 잠금 문제 회피)
    storage = "sqlite:///:memory:"
    
    tuner = EnsembleTuner(
        study_name="test_ensemble",
        storage=storage,
        window_hours=24,
        config_overlay=config_overlay
    )
    
    return tuner


# ============================================
# 테스트: 초기화
# ============================================

def test_init_with_config_overlay(config_overlay):
    """ConfigOverlay로 초기화"""
    storage = "sqlite:///:memory:"
    
    tuner = EnsembleTuner(
        study_name="test",
        storage=storage,
        window_hours=24,
        config_overlay=config_overlay
    )
    
    assert tuner.study_name == "test"
    assert tuner.window_hours == 24
    assert tuner.config_overlay == config_overlay
    assert tuner.study is not None


def test_init_with_base_config(base_config):
    """베이스 설정으로 초기화"""
    storage = "sqlite:///:memory:"
    
    tuner = EnsembleTuner(
        study_name="test",
        storage=storage,
        window_hours=24,
        base_config=base_config
    )
    
    assert tuner.config_overlay is not None
    assert tuner.config_overlay.base_config == base_config


# ============================================
# 테스트: 파라미터 샘플링
# ============================================

def test_sample_params_structure(ensemble_tuner):
    """파라미터 샘플링 구조 검증"""
    # Mock trial
    trial = Mock()
    trial.suggest_float = Mock(side_effect=[0.4, 0.2, 0.2, 0.15, 0.05, 0.4, 0.15, 0.15])
    trial.suggest_int = Mock(return_value=20)
    
    params = ensemble_tuner._sample_params(trial)
    
    # 구조 검증 (PR13_ARCHITECTURE_DESIGN.md 라인 204-216)
    assert 'ensemble' in params
    assert 'alpha_winrate' in params['ensemble']
    assert 'beta_rr' in params['ensemble']
    assert 'gamma_sharpe' in params['ensemble']
    assert 'delta_confidence' in params['ensemble']
    assert 'epsilon_regime' in params['ensemble']
    assert 'experience' in params['ensemble']
    assert 'min_trades' in params['ensemble']['experience']
    assert 'max_weight_per_strategy' in params['ensemble']
    assert 'theta_long' in params['ensemble']
    assert 'theta_short' in params['ensemble']


def test_sample_params_valid_weights(ensemble_tuner):
    """가중치 합 제약 조건 검증"""
    import optuna
    
    # 유효한 가중치 (합 = 1.0)
    trial = Mock()
    trial.suggest_float = Mock(side_effect=[0.4, 0.2, 0.2, 0.15, 0.05, 0.4, 0.15, 0.15])
    trial.suggest_int = Mock(return_value=20)
    
    params = ensemble_tuner._sample_params(trial)
    
    total = (
        params['ensemble']['alpha_winrate'] +
        params['ensemble']['beta_rr'] +
        params['ensemble']['gamma_sharpe'] +
        params['ensemble']['delta_confidence'] +
        params['ensemble']['epsilon_regime']
    )
    
    assert 0.9 <= total <= 1.1


def test_sample_params_invalid_weights(ensemble_tuner):
    """가중치 합 제약 조건 위반"""
    import optuna
    
    # 무효한 가중치 (합 = 1.5 > 1.1)
    trial = Mock()
    trial.suggest_float = Mock(side_effect=[0.5, 0.4, 0.3, 0.2, 0.1, 0.4, 0.15, 0.15])
    trial.suggest_int = Mock(return_value=20)
    
    with pytest.raises(optuna.TrialPruned):
        ensemble_tuner._sample_params(trial)


# ============================================
# 테스트: 스코어 계산
# ============================================

def test_calculate_score_perfect(ensemble_tuner):
    """완벽한 메트릭 스코어"""
    metrics = EnsembleMetrics(
        score_total=1.0,
        sharpe=2.0,
        mdd_pct=0.0,
        trades=60,
        winrate=0.8,
        profit_factor=2.0,
        avg_hold_minutes=60.0,
        tp_hit_rate=0.7
    )
    
    score = ensemble_tuner._calculate_score(metrics)
    
    # score = 1.0*0.4 + 1.0*0.3 + 1.0*0.2 + 1.0*0.1 = 1.0
    assert score == pytest.approx(1.0, abs=0.01)


def test_calculate_score_poor(ensemble_tuner):
    """낮은 메트릭 스코어"""
    metrics = EnsembleMetrics(
        score_total=0.3,
        sharpe=0.0,
        mdd_pct=10.0,
        trades=0,
        winrate=0.3,
        profit_factor=0.5,
        avg_hold_minutes=30.0,
        tp_hit_rate=0.2
    )
    
    score = ensemble_tuner._calculate_score(metrics)
    
    # score = 0.3*0.4 + 0.0*0.3 + 0.0*0.2 + 0.0*0.1 = 0.12
    assert score == pytest.approx(0.12, abs=0.01)


def test_calculate_score_medium(ensemble_tuner):
    """중간 메트릭 스코어"""
    metrics = EnsembleMetrics(
        score_total=0.6,
        sharpe=1.0,
        mdd_pct=5.0,
        trades=30,
        winrate=0.55,
        profit_factor=1.2,
        avg_hold_minutes=45.0,
        tp_hit_rate=0.5
    )
    
    score = ensemble_tuner._calculate_score(metrics)
    
    # score_total: 0.6 * 0.4 = 0.24
    # sharpe_norm: 0.5 * 0.3 = 0.15
    # mdd_norm: 0.5 * 0.2 = 0.1
    # trade_term: 0.5 * 0.1 = 0.05
    # total = 0.54
    assert score == pytest.approx(0.54, abs=0.01)


# ============================================
# 테스트: 오버레이 빌드
# ============================================

def test_build_overlay(ensemble_tuner):
    """파라미터를 오버레이로 변환"""
    params = {
        'alpha_winrate': 0.35,
        'beta_rr': 0.25,
        'gamma_sharpe': 0.20,
        'delta_confidence': 0.15,
        'epsilon_regime': 0.05,
        'min_trades': 25,
        'max_weight_per_strategy': 0.4,
        'theta_long': 0.18,
        'theta_short': 0.18
    }
    
    overlay = ensemble_tuner._build_overlay(params)
    
    assert overlay['ensemble']['alpha_winrate'] == 0.35
    assert overlay['ensemble']['beta_rr'] == 0.25
    assert overlay['ensemble']['experience']['min_trades'] == 25
    assert overlay['ensemble']['max_weight_per_strategy'] == 0.4
    assert overlay['ensemble']['theta_long'] == 0.18


# ============================================
# 테스트: 메트릭 수집 (Mock)
# ============================================

def test_fetch_metrics_no_data(ensemble_tuner):
    """거래 데이터 없을 때 기본값 반환"""
    conn_mock = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = {'total_trades': 0}
    conn_mock.cursor.return_value.__enter__.return_value = cursor_mock
    
    metrics = ensemble_tuner._fetch_metrics_from_db(conn_mock, 24)
    
    assert metrics.trades == 0
    assert metrics.score_total == 0.5
    assert metrics.winrate == 0.5


def test_fetch_metrics_with_data(ensemble_tuner):
    """거래 데이터 있을 때 메트릭 계산"""
    conn_mock = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = {
        'total_trades': 50,
        'winrate': 0.6,
        'profit_factor': 1.5,
        'avg_pnl_pct': 0.02,
        'stddev_pnl_pct': 0.01,
        'avg_hold_minutes': 45.0,
        'tp_hit_rate': 0.65
    }
    conn_mock.cursor.return_value.__enter__.return_value = cursor_mock
    
    metrics = ensemble_tuner._fetch_metrics_from_db(conn_mock, 24)
    
    assert metrics.trades == 50
    assert metrics.winrate == 0.6
    assert metrics.profit_factor == 1.5
    assert metrics.sharpe == pytest.approx(2.0, abs=0.1)  # 0.02 / 0.01


# ============================================
# 테스트: 최적화 (Mock)
# ============================================

@patch('tuning.ensemble_tuner.EnsembleTuner._run_paper_experiment')
def test_optimize(mock_run_experiment, ensemble_tuner):
    """최적화 실행"""
    # Mock 메트릭
    mock_run_experiment.return_value = EnsembleMetrics(
        score_total=0.7,
        sharpe=1.2,
        mdd_pct=3.0,
        trades=40,
        winrate=0.6,
        profit_factor=1.5,
        avg_hold_minutes=50.0,
        tp_hit_rate=0.6
    )
    
    # 최적화 (2 trials)
    best_params = ensemble_tuner.optimize(n_trials=2)
    
    assert best_params is not None
    assert 'alpha_winrate' in best_params
    assert ensemble_tuner.get_best_value() > 0


# ============================================
# 테스트: 팩토리 함수
# ============================================

def test_create_ensemble_tuner():
    """팩토리 함수"""
    from tuning.ensemble_tuner import create_ensemble_tuner
    
    storage = "sqlite:///:memory:"
    
    tuner = create_ensemble_tuner(
        study_name="test",
        storage=storage,
        window_hours=12
    )
    
    assert tuner.study_name == "test"
    assert tuner.window_hours == 12


# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
