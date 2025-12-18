#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER24 Contract Tests

테스트 범위:
1. regime_filter.enabled = False일 때 sub-model이 regime mismatch여도 평가 진행
2. get_diagnostics() 메서드가 필수 키 포함
3. L4_ultra_debug config로 SignalProbe에서 신호 생성 확인 (합성 데이터)
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from strategies.phase35_ensemble_v1 import Phase35EnsembleV1


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def base_config():
    """기본 config"""
    return {
        "mode": "backtest",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "lookback": 400,
        "equity": 50000,
        "decision_trace": {"enabled": True},
        "sub_models": {
            "trend": {"adx_threshold": 25},
            "reversion": {"rsi_oversold": 30, "rsi_overbought": 70},
            "breakout": {"volume_threshold": 1.5},
        },
        "regime_filter": {"enabled": True},
        "ensemble": {"min_votes": 2, "confidence_threshold": 0.5},
    }


@pytest.fixture
def synthetic_df():
    """합성 데이터 (100 bars, 단조 증가 추세)"""
    np.random.seed(42)
    
    n_bars = 100
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="15T")
    
    # 단조 증가 추세
    close_prices = np.linspace(50000, 55000, n_bars)
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": close_prices - np.random.uniform(10, 50, n_bars),
        "high": close_prices + np.random.uniform(10, 100, n_bars),
        "low": close_prices - np.random.uniform(10, 100, n_bars),
        "close": close_prices,
        "volume": np.random.uniform(100, 1000, n_bars),
    })
    
    return df


# ============================================================================
# TEST 1: regime_filter.enabled = False
# ============================================================================

def test_regime_filter_disabled_trend_sub_model(base_config, synthetic_df):
    """
    regime_filter.enabled = False일 때,
    regime이 TREND가 아니어도 trend sub-model이 평가 진행
    """
    # regime_filter 비활성화
    config = base_config.copy()
    config["regime_filter"]["enabled"] = False
    
    strategy = Phase35EnsembleV1(config)
    
    # regime을 강제로 RANGE로 설정하고 _sub_model_trend 직접 호출
    # (regime != "TREND"이지만 enabled=False이므로 차단되지 않아야 함)
    df = synthetic_df.copy()
    
    # 인디케이터 계산을 위한 최소 데이터
    trend_cfg = config["sub_models"]["trend"]
    
    result = strategy._sub_model_trend(df, regime="RANGE", cfg=trend_cfg)
    
    # regime_filter.enabled=False이므로 regime_not_trend로 차단되지 않음
    # ADX/EMA 조건에 따라 LONG/SHORT/FLAT 가능
    # 단, "regime_not_trend" 이유로 차단되지는 않아야 함
    assert result["reasons"] != ["regime_not_trend"], (
        "regime_filter.enabled=False일 때 regime_not_trend로 차단되면 안됨"
    )


def test_regime_filter_enabled_trend_sub_model(base_config, synthetic_df):
    """
    regime_filter.enabled = True (기본값)일 때,
    regime이 TREND가 아니면 trend sub-model이 차단
    """
    config = base_config.copy()
    config["regime_filter"]["enabled"] = True
    
    strategy = Phase35EnsembleV1(config)
    
    df = synthetic_df.copy()
    trend_cfg = config["sub_models"]["trend"]
    
    result = strategy._sub_model_trend(df, regime="RANGE", cfg=trend_cfg)
    
    # regime_filter.enabled=True이므로 regime_not_trend로 차단
    assert result["direction"] is None
    assert "regime_not_trend" in result["reasons"]


# ============================================================================
# TEST 2: get_diagnostics() 메서드
# ============================================================================

def test_get_diagnostics_method_exists(base_config):
    """get_diagnostics() 메서드가 존재하고 dict 반환"""
    strategy = Phase35EnsembleV1(base_config)
    
    assert hasattr(strategy, "get_diagnostics"), "get_diagnostics() 메서드가 없음"
    
    diag = strategy.get_diagnostics()
    assert isinstance(diag, dict), "get_diagnostics()는 dict를 반환해야 함"


def test_diagnostics_captures_flat_reasons(base_config, synthetic_df):
    """
    compute_signal 호출 후 diagnostics에 FLAT 이유가 기록되는지 확인
    """
    config = base_config.copy()
    config["decision_trace"]["enabled"] = True
    
    strategy = Phase35EnsembleV1(config)
    
    # 신호 생성 (일부는 FLAT일 것)
    df = synthetic_df.copy()
    
    for i in range(50, 60):  # 10번 호출
        df_slice = df.iloc[:i+1].copy()
        signal = strategy.compute_signal(df_slice)
    
    diag = strategy.get_diagnostics()
    
    # counters 키가 있어야 함
    assert "counters" in diag, "diagnostics에 counters가 없음"
    
    counters = diag["counters"]
    
    # FLAT 관련 카운터가 최소 1개 이상 있어야 함
    flat_counters = [k for k in counters.keys() if "SUB_" in k or "ENSEMBLE_" in k or "REGIME_" in k]
    assert len(flat_counters) > 0, f"FLAT 관련 카운터가 없음: {counters}"


# ============================================================================
# TEST 3: L4_ultra_debug로 신호 생성 확인 (합성 데이터)
# ============================================================================

def test_l4_ultra_debug_generates_signals(synthetic_df):
    """
    L4_ultra_debug config로 합성 데이터에서 신호 생성 확인
    """
    config = {
        "mode": "backtest",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "lookback": 400,
        "equity": 50000,
        "decision_trace": {"enabled": True},
        "sub_models": {
            "trend": {"adx_threshold": 0},  # ADX 체크 off
            "reversion": {"rsi_oversold": 49, "rsi_overbought": 51},  # 거의 중앙
            "breakout": {"volume_threshold": 0.0},  # Volume 체크 off
        },
        "regime_filter": {"enabled": False},  # Regime filter off
        "ensemble": {"min_votes": 1, "confidence_threshold": 0.0},  # 1개 투표로 신호
    }
    
    strategy = Phase35EnsembleV1(config)
    
    signal_counts = {"LONG": 0, "SHORT": 0, "FLAT": 0}
    
    df = synthetic_df.copy()
    
    for i in range(50, len(df)):
        df_slice = df.iloc[:i+1].copy()
        signal = strategy.compute_signal(df_slice)
        
        side = signal.get("side")
        if side == "LONG":
            signal_counts["LONG"] += 1
        elif side == "SHORT":
            signal_counts["SHORT"] += 1
        else:
            signal_counts["FLAT"] += 1
    
    total_signals = signal_counts["LONG"] + signal_counts["SHORT"]
    
    # L4_ultra_debug는 신호를 생성해야 함 (합성 추세 데이터이므로 최소 1개 이상)
    assert total_signals > 0, (
        f"L4_ultra_debug로 신호가 생성되지 않음: {signal_counts}"
    )


# ============================================================================
# TEST 4: DIAG 카운터 증가 확인
# ============================================================================

def test_diag_inc_called_on_sub_model_flat(base_config, synthetic_df):
    """
    sub-model이 FLAT 반환 시 _diag_inc이 호출되는지 확인
    """
    config = base_config.copy()
    config["decision_trace"]["enabled"] = True
    
    # regime_filter 비활성화 (regime 차단이 아닌 ADX로만 차단되게)
    config["regime_filter"]["enabled"] = False
    
    # ADX threshold를 매우 높게 설정하여 trend sub-model이 FLAT 반환하도록
    config["sub_models"]["trend"]["adx_threshold"] = 100
    
    strategy = Phase35EnsembleV1(config)
    
    df = synthetic_df.copy()
    
    # compute_signal 호출
    signal = strategy.compute_signal(df)
    
    diag = strategy.get_diagnostics()
    counters = diag.get("counters", {})
    
    # SUB_TREND_ADX_WEAK 카운터가 증가했어야 함
    assert "SUB_TREND_ADX_WEAK" in counters, (
        f"SUB_TREND_ADX_WEAK 카운터가 없음: {counters.keys()}"
    )
    assert counters["SUB_TREND_ADX_WEAK"] > 0


# ============================================================================
# TEST 5: regime_filter.enabled SSOT 확인
# ============================================================================

def test_regime_filter_enabled_ssot_read_from_config():
    """
    regime_filter.enabled가 config에서 올바르게 읽히는지 확인
    """
    # enabled = False
    config1 = {
        "mode": "backtest",
        "regime_filter": {"enabled": False},
        "decision_trace": {"enabled": False},
    }
    
    strategy1 = Phase35EnsembleV1(config1)
    rf_cfg = strategy1.config.get("regime_filter", {})
    assert rf_cfg.get("enabled", True) is False
    
    # enabled = True (기본값)
    config2 = {
        "mode": "backtest",
        "decision_trace": {"enabled": False},
    }
    
    strategy2 = Phase35EnsembleV1(config2)
    rf_cfg2 = strategy2.config.get("regime_filter", {})
    assert rf_cfg2.get("enabled", True) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
