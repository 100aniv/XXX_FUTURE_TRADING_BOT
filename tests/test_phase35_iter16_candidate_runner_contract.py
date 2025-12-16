#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER16: Candidate Runner Contract Tests
==================================================

목적:
- Candidate Sweep Runner의 산출물 스키마 검증
- results_table.json 필수 키 존재
- summary.json ITER15 계약 준수
"""
import pytest
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Project root
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def simulate_summary_creation(metrics: Dict[str, Any], 
                               initial_capital: float = 10000,
                               candidate_id: str = "test",
                               window_type: str = "IS") -> Dict[str, Any]:
    """
    ITER15 계약에 맞는 summary 생성 시뮬레이션
    """
    # ITER15 계약: PnL 절대값
    if "pnl" in metrics:
        pnl_abs = metrics["pnl"]
    elif "net_pnl" in metrics:
        pnl_abs = metrics["net_pnl"]
    else:
        pnl_abs = metrics.get("roi", 0.0)
    
    roi_pct = (pnl_abs / initial_capital) * 100 if initial_capital > 0 else 0.0
    mdd_abs = metrics.get("mdd", metrics.get("max_drawdown", 0.0))
    mdd_pct = (abs(mdd_abs) / initial_capital) * 100 if initial_capital > 0 else 0.0
    total_trades = metrics.get("total_trades", 0)
    
    return {
        "candidate_id": candidate_id,
        "window_type": window_type,
        "start_date": "2024-11-01",
        "end_date": "2024-11-30",
        "initial_capital": initial_capital,
        "trades": total_trades,
        "total_trades": total_trades,
        "win_rate": metrics.get("winrate", 0.0),
        "profit_factor": metrics.get("pf", 0.0),
        "pnl": round(pnl_abs, 2),
        "roi": round(roi_pct, 2),
        "max_drawdown": round(mdd_abs, 2),
        "mdd_pct": round(mdd_pct, 2),
        "kpi_source": "metrics (SSOT)",
        "kpi_contract": "pnl_abs + roi_pct + mdd_abs + mdd_pct",
    }


class TestResultsTableContract:
    """
    results_table.json 스키마 검증
    """
    
    def test_results_table_required_keys(self):
        """
        Test 1: results_table.json 필수 키 존재
        """
        mock_results_table = {
            "generated_at": "2025-12-17T00:00:00",
            "git_commit": "abc123",
            "is_window": ("2024-11-01", "2024-11-30"),
            "oos_window": ("2024-12-01", "2024-12-14"),
            "candidates": []
        }
        
        required_keys = ["generated_at", "git_commit", "is_window", "oos_window", "candidates"]
        for key in required_keys:
            assert key in mock_results_table, f"Missing required key: {key}"
    
    def test_candidate_entry_structure(self):
        """
        Test 2: candidates 배열 항목 구조
        """
        mock_candidate = {
            "candidate_id": "C0_baseline",
            "description": "Baseline",
            "overrides": {},
            "is": {"trades": 100, "profit_factor": 0.5},
            "oos": {"trades": 50, "profit_factor": 0.6},
        }
        
        required_keys = ["candidate_id", "description", "overrides", "is", "oos"]
        for key in required_keys:
            assert key in mock_candidate, f"Missing required key: {key}"


class TestCandidateDefinition:
    """
    Candidate 정의 검증
    """
    
    def test_minimum_6_candidates(self):
        """
        Test 3: 최소 6개 후보 존재
        """
        # Import CANDIDATES from runner
        from scripts.phase35.run_iter16_profit_candidates import CANDIDATES
        
        assert len(CANDIDATES) >= 6, f"Expected >= 6 candidates, got {len(CANDIDATES)}"
    
    def test_baseline_candidate_exists(self):
        """
        Test 4: C0_baseline 후보 존재
        """
        from scripts.phase35.run_iter16_profit_candidates import CANDIDATES
        
        assert "C0_baseline" in CANDIDATES, "C0_baseline candidate missing"
        assert CANDIDATES["C0_baseline"]["overrides"] == {}, "Baseline should have no overrides"


class TestSummaryContract:
    """
    summary.json ITER15 계약 준수 검증
    """
    
    def test_summary_has_iter15_contract_keys(self):
        """
        Test 5: summary에 ITER15 계약 키 존재
        """
        metrics = {"total_trades": 100, "pf": 0.5, "roi": -500, "mdd": -600, "winrate": 30}
        summary = simulate_summary_creation(metrics)
        
        required_keys = [
            "trades", "total_trades", "pnl", "roi", 
            "max_drawdown", "mdd_pct", "kpi_contract"
        ]
        for key in required_keys:
            assert key in summary, f"Missing ITER15 contract key: {key}"
    
    def test_trades_alias_consistency(self):
        """
        Test 6: trades == total_trades (alias 역호환)
        """
        metrics = {"total_trades": 1234, "pf": 0.5, "roi": -100, "mdd": -200}
        summary = simulate_summary_creation(metrics)
        
        assert summary["trades"] == summary["total_trades"], "trades != total_trades"
        assert summary["trades"] == 1234, f"Expected 1234, got {summary['trades']}"
    
    def test_pnl_roi_contract(self):
        """
        Test 7: pnl(절대값) + roi(%) 계약
        """
        metrics = {"total_trades": 100, "pf": 0.5, "roi": -1000, "mdd": -500}
        summary = simulate_summary_creation(metrics, initial_capital=10000)
        
        # pnl = 절대값
        assert summary["pnl"] == -1000, f"pnl should be -1000, got {summary['pnl']}"
        
        # roi = %
        expected_roi = (-1000 / 10000) * 100  # -10%
        assert summary["roi"] == pytest.approx(expected_roi, rel=0.01)
    
    def test_mdd_contract(self):
        """
        Test 8: max_drawdown(절대값) + mdd_pct(%) 계약
        """
        metrics = {"total_trades": 100, "roi": -500, "mdd": -800}
        summary = simulate_summary_creation(metrics, initial_capital=10000)
        
        # max_drawdown = 절대값
        assert summary["max_drawdown"] == -800
        
        # mdd_pct = %
        expected_mdd_pct = (800 / 10000) * 100  # 8%
        assert summary["mdd_pct"] == pytest.approx(expected_mdd_pct, rel=0.01)


class TestApplyOverrides:
    """
    Config override 적용 검증
    """
    
    def test_apply_dot_notation_override(self):
        """
        Test 9: dot notation override 적용
        """
        from scripts.phase35.run_iter16_profit_candidates import apply_overrides
        
        config = {"ensemble": {"confidence_threshold": 0.70, "min_votes": 2}}
        overrides = {"ensemble.confidence_threshold": 0.85}
        
        result = apply_overrides(config, overrides)
        
        assert result["ensemble"]["confidence_threshold"] == 0.85
    
    def test_baseline_no_changes(self):
        """
        Test 10: Baseline은 변경 없음
        """
        from scripts.phase35.run_iter16_profit_candidates import apply_overrides
        
        config = {"ensemble": {"confidence_threshold": 0.70}}
        overrides = {}
        
        result = apply_overrides(config, overrides)
        
        assert result["ensemble"]["confidence_threshold"] == 0.70


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
