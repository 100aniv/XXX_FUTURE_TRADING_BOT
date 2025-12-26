#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSOT Regression Suite - Smoke Tests (PHASE36-1 S4)
"""
import pytest


def test_strategy_imports():
    from strategies import scalping
    from strategies import ensemble
    assert scalping is not None
    assert ensemble is not None


def test_execution_imports():
    from execution import engine
    from execution import risk_manager
    from execution import position_sizer
    from execution import portfolio_manager
    assert engine is not None
    assert risk_manager is not None
    assert position_sizer is not None
    assert portfolio_manager is not None


def test_common_imports():
    from common.config_loader import load_config
    from common.logger import setup_logger
    from common.signal_telemetry import get_signal_telemetry
    assert load_config is not None
    assert setup_logger is not None
    assert get_signal_telemetry is not None


def test_config_loading():
    from common.config_loader import load_config
    config = load_config()
    assert config is not None
    assert isinstance(config, dict)
    assert len(config) > 0


def test_signal_telemetry_singleton():
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    reset_signal_telemetry()
    t1 = get_signal_telemetry()
    t2 = get_signal_telemetry()
    assert t1 is t2
    t1.signal_evaluated(5)
    counters = t2.get_counters()
    assert counters["signal_evaluated_total"] == 5
