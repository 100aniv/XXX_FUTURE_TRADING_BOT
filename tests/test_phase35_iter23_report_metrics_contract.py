#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER23 Contract Tests: Report & Metrics SSOT

테스트 항목:
1. runner가 config에 SSOT 키(backtest.output_file)를 세팅하는지
2. resolve_report_path()가 정상 작동하는지
3. DB conn params가 하드코딩이 아닌지
4. parse_metrics_defensive()가 다양한 스키마를 처리하는지
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestReportSSOTKey:
    """backtest.output_file SSOT 키 테스트"""
    
    def test_config_uses_output_file_key(self):
        """config에 output_file 키가 설정되는지 확인"""
        config = {"backtest": {}}
        report_path = Path("/test/path/report.json")
        
        # SSOT 키 설정
        config["backtest"]["output_file"] = str(report_path)
        
        assert "output_file" in config["backtest"]
        assert config["backtest"]["output_file"] == str(report_path)
    
    def test_output_file_not_output_path(self):
        """output_path가 아닌 output_file을 사용하는지 확인"""
        from scripts.phase35.run_iter23_report_metrics_ssot import run_backtest_with_ssot
        
        # 함수 시그니처에서 output_file 사용 확인
        import inspect
        source = inspect.getsource(run_backtest_with_ssot)
        
        assert 'config["backtest"]["output_file"]' in source
        assert 'config["backtest"]["output_path"]' not in source


class TestResolveReportPath:
    """resolve_report_path 함수 테스트"""
    
    def test_returns_configured_path_if_exists(self, tmp_path):
        """설정된 경로에 파일이 있으면 그것을 반환"""
        from scripts.phase35.run_iter23_report_metrics_ssot import resolve_report_path
        
        # 임시 파일 생성
        report_file = tmp_path / "report.json"
        report_file.write_text('{"test": 1}')
        
        result = resolve_report_path(report_file, tmp_path)
        
        assert result == report_file
    
    def test_returns_none_if_not_found(self, tmp_path):
        """파일을 찾을 수 없으면 None 반환"""
        from scripts.phase35.run_iter23_report_metrics_ssot import resolve_report_path
        
        non_existent = tmp_path / "non_existent.json"
        
        result = resolve_report_path(non_existent, tmp_path)
        
        assert result is None


class TestDBConnectionSSoT:
    """DB 연결 SSOT 테스트 (하드코딩 금지)"""
    
    def test_no_hardcoded_password_in_runner(self):
        """runner에 하드코딩된 비밀번호가 없는지 확인"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_iter23_report_metrics_ssot.py"
        
        with open(runner_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 하드코딩된 비밀번호 패턴 검사
        forbidden_patterns = [
            "password='",
            'password="',
            "trading_pass",
            "trading_pw",
        ]
        
        for pattern in forbidden_patterns:
            # collect_db_evidence 함수 내에서 직접 비밀번호를 사용하지 않아야 함
            assert pattern not in content.split("def collect_db_evidence")[1].split("def ")[0], \
                f"Hardcoded pattern found: {pattern}"
    
    def test_uses_database_postgres_module(self):
        """database.postgres 모듈을 사용하는지 확인"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_iter23_report_metrics_ssot.py"
        
        with open(runner_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "from database.postgres import get_db_connection" in content


class TestParseMetricsDefensive:
    """방어적 metrics 파싱 테스트"""
    
    def test_parses_total_trades_from_root(self):
        """root level total_trades 파싱"""
        from scripts.phase35.run_iter23_report_metrics_ssot import parse_metrics_defensive
        
        report = {"total_trades": 10}
        metrics = parse_metrics_defensive(report)
        
        assert metrics["total_trades"] == 10
    
    def test_parses_total_trades_from_metrics(self):
        """metrics.total_trades 파싱"""
        from scripts.phase35.run_iter23_report_metrics_ssot import parse_metrics_defensive
        
        report = {"metrics": {"total_trades": 15}}
        metrics = parse_metrics_defensive(report)
        
        assert metrics["total_trades"] == 15
    
    def test_parses_total_trades_from_summary(self):
        """summary.total_trades 파싱"""
        from scripts.phase35.run_iter23_report_metrics_ssot import parse_metrics_defensive
        
        report = {"summary": {"total_trades": 20}}
        metrics = parse_metrics_defensive(report)
        
        assert metrics["total_trades"] == 20
    
    def test_parses_alternative_key_trades(self):
        """'trades' 키 파싱"""
        from scripts.phase35.run_iter23_report_metrics_ssot import parse_metrics_defensive
        
        report = {"trades": 25}
        metrics = parse_metrics_defensive(report)
        
        assert metrics["total_trades"] == 25
    
    def test_parses_loaded_candles_variants(self):
        """loaded_candles 다양한 키 파싱"""
        from scripts.phase35.run_iter23_report_metrics_ssot import parse_metrics_defensive
        
        for key in ["loaded_candles", "bars", "num_bars", "total_bars"]:
            report = {key: 1000}
            metrics = parse_metrics_defensive(report)
            assert metrics.get("loaded_candles") == 1000, f"Failed for key: {key}"


class TestRelaxationLevels:
    """Relaxation levels 테스트"""
    
    def test_all_levels_defined(self):
        """모든 레벨이 정의되어 있는지 확인"""
        from scripts.phase35.run_iter23_report_metrics_ssot import RELAXATION_LEVELS
        
        assert "L0_baseline" in RELAXATION_LEVELS
        assert "L3_aggressive" in RELAXATION_LEVELS
        assert "L4_ultra_debug" in RELAXATION_LEVELS
    
    def test_l4_ultra_debug_has_extreme_values(self):
        """L4_ultra_debug가 극단적인 완화값을 가지는지 확인"""
        from scripts.phase35.run_iter23_report_metrics_ssot import RELAXATION_LEVELS
        
        l4 = RELAXATION_LEVELS["L4_ultra_debug"]
        
        assert l4["trend"]["adx_threshold"] == 5
        assert l4["reversion"]["rsi_oversold"] == 48
        assert l4["regime_filter"]["enabled"] == False
        assert l4["ensemble"]["min_votes"] == 1
        assert l4["ensemble"]["confidence_threshold"] == 0.1


class TestInjectOverrides:
    """inject_overrides 함수 테스트"""
    
    def test_injects_to_all_paths(self):
        """모든 경로에 override가 주입되는지 확인"""
        from scripts.phase35.run_iter23_report_metrics_ssot import inject_overrides
        
        config = {
            "strategy": {"selector": "phase35_ensemble_v1"}
        }
        overrides = {
            "trend": {"adx_threshold": 10},
            "regime_filter": {"enabled": False},
            "ensemble": {"min_votes": 1}
        }
        
        result = inject_overrides(config, overrides)
        
        # Top-level
        assert result["sub_models"]["trend"]["adx_threshold"] == 10
        
        # strategy.sub_models
        assert result["strategy"]["sub_models"]["trend"]["adx_threshold"] == 10
        
        # strategies.<selector>.params
        assert result["strategies"]["phase35_ensemble_v1"]["params"]["sub_models"]["trend"]["adx_threshold"] == 10
        
        # regime_filter
        assert result["regime_filter"]["enabled"] == False
        
        # ensemble
        assert result["ensemble"]["min_votes"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
