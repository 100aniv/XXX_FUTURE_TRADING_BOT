#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER6: KPI SSOT (Single Source of Truth)
===================================================

목적:
- 모든 KPI 계산을 한 곳에서 수행 (summary.json과 report.md 일치 보장)
- PnL/ROI/WinRate/ProfitFactor/MaxDD 등 핵심 지표 통일
- 계산 로직 모순 방지 (예: pnl=0인데 ROI 음수 같은 케이스)

의존성: 순수 Python 표준 라이브러리만 사용
"""
from typing import Dict, Any, List, Optional


def compute_kpis(
    trades: List[Dict[str, Any]],
    initial_capital: float,
    final_equity: Optional[float] = None,
    fees_total: float = 0.0,
    slippage_total: float = 0.0
) -> Dict[str, Any]:
    """
    백테스트/페이퍼 트레이딩 KPI 계산 (SSOT)
    
    Args:
        trades: 거래 리스트 (각 거래는 {"pnl": float, "is_win": bool, ...} 포함)
        initial_capital: 초기 자본
        final_equity: 최종 equity (없으면 initial + sum(pnl) - fees - slippage)
        fees_total: 총 수수료
        slippage_total: 총 슬리피지
    
    Returns:
        {
            "total_trades": int,
            "winning_trades": int,
            "losing_trades": int,
            "winrate": float,           # % (0~100)
            "total_pnl": float,         # 순이익 (fees/slippage 제외 전)
            "net_pnl": float,           # 순이익 (fees/slippage 제외 후)
            "fees_total": float,
            "slippage_total": float,
            "roi": float,               # % (net_pnl / initial_capital * 100)
            "profit_factor": float,     # gross_profit / gross_loss (0이면 Inf)
            "max_drawdown": float,      # % (최대 낙폭, 음수)
            "avg_win": float,
            "avg_loss": float,
            "win_loss_ratio": float,
            "final_equity": float
        }
    """
    total_trades = len(trades)
    
    if total_trades == 0:
        # 거래 없음
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "winrate": 0.0,
            "total_pnl": 0.0,
            "net_pnl": 0.0,
            "fees_total": 0.0,
            "slippage_total": 0.0,
            "roi": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_loss_ratio": 0.0,
            "final_equity": initial_capital
        }
    
    # ===== PnL 집계 =====
    total_pnl = sum(t.get("pnl", 0.0) for t in trades)
    net_pnl = total_pnl - fees_total - slippage_total
    
    # ===== Win/Loss 분리 =====
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    
    winning_trades = len(wins)
    losing_trades = len(losses)
    winrate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    gross_profit = sum(t.get("pnl", 0) for t in wins)
    gross_loss = abs(sum(t.get("pnl", 0) for t in losses))
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
    avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    
    # ===== Equity & ROI =====
    if final_equity is None:
        final_equity = initial_capital + net_pnl
    
    roi = (net_pnl / initial_capital * 100) if initial_capital > 0 else 0.0
    
    # ===== Max Drawdown (간단 버전: equity curve 없으면 근사치) =====
    # 실제로는 equity_curve를 받아야 정확하지만, trades만으로 근사
    # 누적 PnL 기반 최대 낙폭 계산
    cumulative_pnl = 0.0
    peak_pnl = 0.0
    max_drawdown_abs = 0.0
    
    for trade in trades:
        cumulative_pnl += trade.get("pnl", 0.0)
        if cumulative_pnl > peak_pnl:
            peak_pnl = cumulative_pnl
        drawdown = cumulative_pnl - peak_pnl
        if drawdown < max_drawdown_abs:
            max_drawdown_abs = drawdown
    
    # 퍼센트로 변환 (초기 자본 대비)
    max_drawdown_pct = (max_drawdown_abs / initial_capital * 100) if initial_capital > 0 else 0.0
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "winrate": round(winrate, 2),
        "total_pnl": round(total_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "fees_total": round(fees_total, 2),
        "slippage_total": round(slippage_total, 2),
        "roi": round(roi, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 0.0,
        "max_drawdown": round(max_drawdown_pct, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "final_equity": round(final_equity, 2)
    }


def validate_kpi_consistency(kpi1: Dict[str, Any], kpi2: Dict[str, Any], tolerance: float = 0.01) -> bool:
    """
    두 KPI 딕셔너리가 일치하는지 검증 (테스트용)
    
    Args:
        kpi1: 첫 번째 KPI
        kpi2: 두 번째 KPI
        tolerance: 허용 오차 (백분율, 예: 0.01 = 1%)
    
    Returns:
        True if consistent, False otherwise
    """
    keys_to_check = ["total_trades", "winrate", "total_pnl", "net_pnl", "roi", "profit_factor", "max_drawdown"]
    
    for key in keys_to_check:
        val1 = kpi1.get(key, 0)
        val2 = kpi2.get(key, 0)
        
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if val1 == 0 and val2 == 0:
                continue
            if abs(val1 - val2) / max(abs(val1), abs(val2), 1) > tolerance:
                return False
        elif val1 != val2:
            return False
    
    return True
