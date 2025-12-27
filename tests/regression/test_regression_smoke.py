#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSOT Regression Suite - Smoke Tests (PHASE36-1 S4)
=====================================================

초경량 regression 테스트:
- 핵심 모듈 import 검증만 수행 (인스턴스화 없음)
- Signal Telemetry SSOT 싱글톤 검증
- Config 로드 검증

목적: Gate2(regression)의 "0 tests collected" 상태를 제거하는 SSOT 기준선.
"""
import pytest


def test_strategy_imports():
    """전략 모듈 import 검증"""
    from strategies import scalping
    from strategies import ensemble
    
    assert scalping is not None
    assert ensemble is not None


def test_execution_imports():
    """실행 모듈 import 검증"""
    from execution import engine
    from execution import risk_manager
    from execution import position_sizer
    from execution import portfolio_manager
    
    assert engine is not None
    assert risk_manager is not None
    assert position_sizer is not None
    assert portfolio_manager is not None


def test_common_imports():
    """공통 모듈 import 검증"""
    from common.config_loader import load_config
    from common.logger import setup_logger
    from common.signal_telemetry import get_signal_telemetry
    
    assert load_config is not None
    assert setup_logger is not None
    assert get_signal_telemetry is not None


def test_config_loading():
    """설정 파일 로드 검증"""
    from common.config_loader import load_config
    
    config = load_config()
    
    assert config is not None, "설정 로드 실패"
    assert isinstance(config, dict), "설정이 딕셔너리가 아님"
    assert len(config) > 0, "설정이 비어 있음"


def test_signal_telemetry_singleton():
    """Signal Telemetry SSOT 싱글톤 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    
    t1 = get_signal_telemetry()
    t2 = get_signal_telemetry()
    
    assert t1 is t2, "싱글톤 패턴 위반"
    
    t1.signal_evaluated(5)
    counters = t2.get_counters()
    
    assert counters["signal_evaluated_total"] == 5, "카운터 동기화 실패"
