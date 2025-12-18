#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER26: SSOT Contract Tests
=====================================
SignalProbe ↔ Engine 동일 캔들 구간 SSOT 검증
"""
import pytest
import inspect
from pathlib import Path


def test_iter26_uses_signal_probe_load_candles():
    """
    ITER26 runner가 SignalProbe의 load_candles를 재사용하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import load_candles_ssot
    
    source = inspect.getsource(load_candles_ssot)
    
    # signal_probe_iter24의 load_candles 재사용 확인
    assert "from scripts.phase35.signal_probe_iter24 import load_candles" in source or \
           "signal_probe_iter24" in source, (
        "load_candles_ssot()는 signal_probe_iter24.load_candles()를 재사용해야 함"
    )


def test_iter26_extracts_date_range_from_df():
    """
    extract_date_range_from_df()가 start_date/end_date를 추출하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import extract_date_range_from_df
    
    source = inspect.getsource(extract_date_range_from_df)
    
    # start_date, end_date 추출 확인
    assert "start_date" in source, "extract_date_range_from_df()에 start_date 추출 필요"
    assert "end_date" in source, "extract_date_range_from_df()에 end_date 추출 필요"
    assert "min()" in source or ".min" in source, "df.time.min() 사용 필요"
    assert "max()" in source or ".max" in source, "df.time.max() 사용 필요"


def test_iter26_injects_dates_to_engine_config():
    """
    run_iter26_e2e()가 Engine config에 start_date/end_date를 주입하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import run_iter26_e2e
    
    source = inspect.getsource(run_iter26_e2e)
    
    # config에 start_date/end_date 주입 확인
    assert 'config["start_date"]' in source or "config['start_date']" in source, (
        "config['start_date'] 주입 필요"
    )
    assert 'config["end_date"]' in source or "config['end_date']" in source, (
        "config['end_date'] 주입 필요"
    )
    
    # backtest 섹션에도 주입 확인
    assert 'config["backtest"]["start_date"]' in source or "config['backtest']['start_date']" in source, (
        "config['backtest']['start_date'] 주입 필요"
    )
    assert 'config["backtest"]["end_date"]' in source or "config['backtest']['end_date']" in source, (
        "config['backtest']['end_date'] 주입 필요"
    )


def test_iter26_uses_run_v2():
    """
    ITER26 runner가 execution.engine.run_v2를 사용하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import run_iter26_e2e
    
    source = inspect.getsource(run_iter26_e2e)
    
    assert "from execution.engine import run_v2" in source or \
           "run_v2(mode=" in source, (
        "run_iter26_e2e()는 execution.engine.run_v2를 사용해야 함"
    )


def test_iter26_uses_qualified_queries():
    """
    ITER26 runner가 qualified query (trading.trades)를 사용하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import collect_db_evidence
    
    source = inspect.getsource(collect_db_evidence)
    
    assert "FROM trading.trades" in source, (
        "collect_db_evidence()는 'FROM trading.trades' (qualified) 사용 필요"
    )


def test_iter26_has_all_ac_checks():
    """
    ITER26 runner가 AC1~AC5 체크를 포함하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import run_iter26_e2e
    
    source = inspect.getsource(run_iter26_e2e)
    
    required_acs = [
        "ac1_db_schema_exists",
        "ac2_trades_gt_zero",
        "ac3_report_generated",
        "ac4_artifacts_saved",
        "ac5_df_range_matches_engine"
    ]
    
    for ac in required_acs:
        assert ac in source, f"run_iter26_e2e()에 '{ac}' 체크 필요"


def test_iter26_saves_evidence_json():
    """
    ITER26 runner가 증거를 JSON으로 저장하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import run_iter26_e2e
    
    source = inspect.getsource(run_iter26_e2e)
    
    # iter26_results.json 저장 확인
    assert "iter26_results.json" in source, (
        "run_iter26_e2e()는 iter26_results.json 저장 필요"
    )
    
    # df_range 증거 저장 확인
    assert "df_range" in source, (
        "run_iter26_e2e()는 df_range 증거 저장 필요"
    )
    
    # engine_config_injected 증거 저장 확인
    assert "engine_config_injected" in source, (
        "run_iter26_e2e()는 engine_config_injected 증거 저장 필요"
    )


def test_iter26_l4_ultra_debug_config():
    """
    L4_ULTRA_DEBUG_OVERRIDES가 올바른 설정을 포함하는지 확인
    """
    from scripts.phase35.run_iter26_e2e_same_window_as_signal_probe import L4_ULTRA_DEBUG_OVERRIDES
    
    # 필수 키 확인
    assert "trend" in L4_ULTRA_DEBUG_OVERRIDES, "L4_ULTRA_DEBUG에 trend 설정 필요"
    assert "reversion" in L4_ULTRA_DEBUG_OVERRIDES, "L4_ULTRA_DEBUG에 reversion 설정 필요"
    assert "breakout" in L4_ULTRA_DEBUG_OVERRIDES, "L4_ULTRA_DEBUG에 breakout 설정 필요"
    assert "regime_filter" in L4_ULTRA_DEBUG_OVERRIDES, "L4_ULTRA_DEBUG에 regime_filter 설정 필요"
    assert "ensemble" in L4_ULTRA_DEBUG_OVERRIDES, "L4_ULTRA_DEBUG에 ensemble 설정 필요"
    
    # regime_filter disabled 확인
    assert L4_ULTRA_DEBUG_OVERRIDES["regime_filter"].get("enabled") == False, (
        "L4_ULTRA_DEBUG의 regime_filter.enabled=False 필요"
    )
    
    # ensemble min_votes=1 확인
    assert L4_ULTRA_DEBUG_OVERRIDES["ensemble"].get("min_votes") == 1, (
        "L4_ULTRA_DEBUG의 ensemble.min_votes=1 필요"
    )


def test_historical_feed_date_inclusive():
    """
    HistoricalFeed의 end_date가 inclusive인지 확인 (SSOT 증거)
    """
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    historical_collector_path = PROJECT_ROOT / "collectors" / "historical_collector.py"
    
    assert historical_collector_path.exists(), f"historical_collector.py 없음: {historical_collector_path}"
    
    content = historical_collector_path.read_text(encoding="utf-8")
    
    # end_date inclusive 로직 확인
    assert "end_dt_inclusive" in content or "days=1" in content, (
        "HistoricalFeed의 end_date inclusive 처리 로직 필요"
    )
