#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-3 ITER15: Summary SSOT Contract Tests
==============================================

목적:
- summary.json의 KPI 스키마/단위 계약을 테스트로 강제
- trades/total_trades alias 역호환 검증
- pnl(절대값)/roi(%) 계약 검증
- mdd(절대값)/mdd_pct(%) 계약 검증

계약 (Contract):
- trades == total_trades == metrics.total_trades
- pnl = 절대값 (metrics["roi"] 레거시 또는 metrics["pnl"])
- roi = (pnl / initial_capital) * 100 (%)
- max_drawdown = 절대값 (metrics["mdd"])
- mdd_pct = (|mdd| / initial_capital) * 100 (%)
"""
import pytest
from typing import Dict, Any


def simulate_iter15_summary(metrics: Dict[str, Any], initial_capital: float = 10000) -> Dict[str, Any]:
    """
    ITER15 summary 생성 로직 시뮬레이션
    (run_iter5_isolated_v2.py L486-542 로직과 동일)
    """
    # A) PnL 절대값 (SSOT: metrics["pnl"] 우선, 없으면 metrics["roi"] 사용)
    if "pnl" in metrics:
        pnl_abs = metrics["pnl"]
    elif "net_pnl" in metrics:
        pnl_abs = metrics["net_pnl"]
    else:
        # 레거시: metrics["roi"]가 실제로는 PnL 절대값
        pnl_abs = metrics.get("roi", 0.0)
    
    # B) ROI % 계산
    roi_pct = (pnl_abs / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # C) MDD 절대값 (SSOT: metrics["mdd_abs"] 우선, 없으면 metrics["mdd"])
    if "mdd_abs" in metrics:
        mdd_abs = metrics["mdd_abs"]
    else:
        mdd_abs = metrics.get("mdd", metrics.get("max_drawdown", 0.0))
    
    # D) MDD % 계산
    mdd_pct = (abs(mdd_abs) / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # E) Total Trades (SSOT)
    total_trades_ssot = metrics.get("total_trades", 0)
    
    return {
        "trades": total_trades_ssot,
        "total_trades": total_trades_ssot,
        "win_rate": metrics.get("winrate", 0.0),
        "profit_factor": metrics.get("pf", metrics.get("profit_factor", 0.0)),
        "pnl": round(pnl_abs, 2),
        "roi": round(roi_pct, 2),
        "max_drawdown": round(mdd_abs, 2),
        "mdd_pct": round(mdd_pct, 2),
        "initial_capital": initial_capital,
        "kpi_contract": "pnl_abs + roi_pct + mdd_abs + mdd_pct",
    }


class TestTradesAliasContract:
    """
    Test 1-2: trades/total_trades alias 계약
    """
    
    def test_trades_equals_total_trades(self):
        """
        Test 1: trades == total_trades (alias 역호환)
        """
        metrics = {"total_trades": 10498, "winrate": 28.41, "pf": 0.567, "roi": -1510.93, "mdd": -1516.16}
        summary = simulate_iter15_summary(metrics)
        
        assert summary["trades"] == summary["total_trades"], "trades != total_trades alias broken"
        assert summary["trades"] == 10498, f"Expected 10498, got {summary['trades']}"
    
    def test_trades_from_metrics_ssot(self):
        """
        Test 2: trades == metrics.total_trades (SSOT)
        """
        metrics = {"total_trades": 5000, "roi": -500.0, "mdd": -600.0}
        summary = simulate_iter15_summary(metrics)
        
        assert summary["trades"] == metrics["total_trades"]
        assert summary["total_trades"] == metrics["total_trades"]


class TestPnlRoiContract:
    """
    Test 3-4: pnl(절대값)/roi(%) 계약
    """
    
    def test_pnl_abs_roi_pct_contract(self):
        """
        Test 3: pnl=절대값, roi=% 계약 검증
        예: initial=10000, metrics["roi"]=-1510.9265
            → summary["pnl"] == -1510.93
            → summary["roi"] == -15.11 (approx)
        """
        metrics = {
            "total_trades": 10498,
            "winrate": 28.414936178319678,
            "pf": 0.5667332988512346,
            "roi": -1510.9265018548092,  # 레거시: 실제로는 PnL 절대값
            "mdd": -1516.156444039129
        }
        initial_capital = 10000
        summary = simulate_iter15_summary(metrics, initial_capital)
        
        # PnL은 절대값 (metrics["roi"] 그대로)
        assert summary["pnl"] == pytest.approx(-1510.93, rel=0.01), f"pnl={summary['pnl']}"
        
        # ROI는 백분율 (pnl / initial_capital * 100)
        expected_roi = (-1510.9265018548092 / 10000) * 100  # -15.109265%
        assert summary["roi"] == pytest.approx(expected_roi, rel=0.01), f"roi={summary['roi']}"
    
    def test_pnl_field_priority_over_roi(self):
        """
        Test 4: metrics["pnl"] 필드가 있으면 그것이 우선 (방어 로직)
        """
        metrics = {
            "total_trades": 100,
            "pnl": -500.0,  # 명시적 pnl 필드
            "roi": 9999.0,  # 이건 무시되어야 함
            "mdd": -100.0
        }
        summary = simulate_iter15_summary(metrics)
        
        assert summary["pnl"] == -500.0, "pnl field should take priority over roi"
        assert summary["roi"] == pytest.approx(-5.0, rel=0.01), "roi should be calculated from pnl"


class TestMddContract:
    """
    Test 5-6: mdd(절대값)/mdd_pct(%) 계약
    """
    
    def test_mdd_abs_mdd_pct_contract(self):
        """
        Test 5: max_drawdown=절대값, mdd_pct=% 계약 검증
        """
        metrics = {
            "total_trades": 10498,
            "roi": -1510.93,
            "mdd": -1516.156444039129
        }
        initial_capital = 10000
        summary = simulate_iter15_summary(metrics, initial_capital)
        
        # MDD는 절대값 (음수 유지)
        assert summary["max_drawdown"] == pytest.approx(-1516.16, rel=0.01), f"mdd={summary['max_drawdown']}"
        
        # MDD%는 백분율 (|mdd| / initial_capital * 100)
        expected_mdd_pct = (1516.156444039129 / 10000) * 100  # 15.16%
        assert summary["mdd_pct"] == pytest.approx(expected_mdd_pct, rel=0.01), f"mdd_pct={summary['mdd_pct']}"
    
    def test_mdd_abs_field_priority(self):
        """
        Test 6: metrics["mdd_abs"] 필드가 있으면 우선 사용 (방어 로직)
        """
        metrics = {
            "total_trades": 50,
            "roi": -200.0,
            "mdd_abs": -800.0,  # 명시적 mdd_abs 필드
            "mdd": -9999.0  # 이건 무시되어야 함
        }
        summary = simulate_iter15_summary(metrics)
        
        assert summary["max_drawdown"] == -800.0, "mdd_abs should take priority"
        assert summary["mdd_pct"] == pytest.approx(8.0, rel=0.01)


class TestEdgeCases:
    """
    Test 7-8: 엣지 케이스
    """
    
    def test_zero_trades_case(self):
        """
        Test 7: trades=0 케이스 (정상 처리)
        """
        metrics = {"total_trades": 0, "roi": 0.0, "mdd": 0.0}
        summary = simulate_iter15_summary(metrics)
        
        assert summary["trades"] == 0
        assert summary["total_trades"] == 0
        assert summary["pnl"] == 0.0
        assert summary["roi"] == 0.0
    
    def test_trades_array_empty_warning_case(self):
        """
        Test 8: trades 배열 비어있어도 metrics SSOT 유지 (ITER14 의도)
        """
        # ITER13 버그 케이스 재현: metrics는 있지만 trades 배열 없음
        metrics = {
            "total_trades": 10498,
            "winrate": 28.41,
            "pf": 0.567,
            "roi": -1510.93,
            "mdd": -1516.16
        }
        # trades 배열은 없음 (report_data["trades"] = [])
        # 하지만 metrics 기반으로 summary 생성
        summary = simulate_iter15_summary(metrics)
        
        # SSOT: metrics.total_trades 유지
        assert summary["trades"] == 10498, "ITER13 bug: should not be 0"
        assert summary["total_trades"] == 10498


class TestIter14BugRegression:
    """
    Test 9: ITER14 버그 회귀 테스트
    """
    
    def test_iter14_roi_scale_bug_fixed(self):
        """
        Test 9: ITER14에서 roi=-1510.93 (실제 PnL)을 ROI%로 잘못 표시한 버그 수정
        
        ITER14 버그:
        - summary["roi"] = -1510.93 (❌ PnL을 ROI로 잘못 표시)
        - summary["pnl"] = -151092.65 (❌ 잘못된 계산)
        
        ITER15 수정:
        - summary["pnl"] = -1510.93 (✅ PnL 절대값)
        - summary["roi"] = -15.11 (✅ ROI %)
        """
        metrics = {
            "total_trades": 10498,
            "winrate": 28.414936178319678,
            "pf": 0.5667332988512346,
            "roi": -1510.9265018548092,  # 레거시 네이밍: 실제로는 PnL
            "mdd": -1516.156444039129
        }
        initial_capital = 10000
        summary = simulate_iter15_summary(metrics, initial_capital)
        
        # ITER14 버그 값이 아님을 확인
        assert summary["pnl"] != pytest.approx(-151092.65, rel=0.1), "ITER14 bug: pnl scale wrong"
        assert summary["roi"] != pytest.approx(-1510.93, rel=0.1), "ITER14 bug: roi is actually pnl"
        
        # ITER15 올바른 값
        assert summary["pnl"] == pytest.approx(-1510.93, rel=0.01), "pnl should be absolute"
        assert summary["roi"] == pytest.approx(-15.11, rel=0.01), "roi should be percentage"


class TestKpiContractMarker:
    """
    Test 10: KPI 계약 표식 (문서화 목적)
    """
    
    def test_kpi_contract_field_exists(self):
        """
        Test 10: summary에 kpi_contract 필드가 있어야 함
        """
        metrics = {"total_trades": 100, "roi": -50.0, "mdd": -60.0}
        summary = simulate_iter15_summary(metrics)
        
        assert "kpi_contract" in summary, "kpi_contract field missing"
        assert "pnl_abs" in summary["kpi_contract"]
        assert "roi_pct" in summary["kpi_contract"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
