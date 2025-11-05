#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metrics Computation Engine
===========================
거래 메트릭 계산 엔진

목적:
- FlowGuardian 게이트용 메트릭 계산
- 최소 메트릭: profit_factor, winrate, exp_score, score_total
- 필요 시 reports/trading_reporter.py 유틸 재사용 가능

제약 (.windsurfrules):
- 계약(IMetrics) 준수 범위 내 구현
- 기존 모듈 로직 변경 금지
"""
import logging
from typing import Dict, Any, List

from core.interfaces import IMetrics

logger = logging.getLogger(__name__)


class MetricsEngine(IMetrics):
    """
    메트릭 계산 엔진
    
    역할:
    - 거래 로그로부터 핵심 메트릭 산출
    - FlowGuardian 게이트 검증용
    
    계산 메트릭:
    - profit_factor: 총이익 / 총손실
    - winrate: 승률 (0.0~1.0)
    - exp_score: 기대값 점수 (winrate * avg_win / abs(avg_loss))
    - score_total: 종합 점수 (가중 평균)
    - total_trades: 총 거래 수
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 설정 딕셔너리 (선택)
        """
        self.config = config or {}
    
    def compute(self, trade_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        거래 메트릭 계산
        
        Args:
            trade_log: {
                "sim": Dict[str, Any],  # 시뮬 결과 (dry_run 반환값)
                "intent": Dict[str, Any],  # 주문 의도
                "signals": Dict[str, Any],  # 시그널
                "trades": List[Dict],  # 거래 내역 (선택)
            }
        
        Returns:
            {
                "profit_factor": float,
                "winrate": float,
                "exp_score": float,
                "score_total": float,
                "total_trades": int,
                "wins": int,
                "losses": int,
                "avg_win": float,
                "avg_loss": float,
            }
        """
        # 거래 내역 추출
        trades = trade_log.get("trades", [])
        sim = trade_log.get("sim", {})
        
        # 시뮬 결과만 있는 경우 (단일 거래)
        if not trades and sim:
            trades = [self._sim_to_trade(sim)]
        
        # 거래 없음 (기본값 반환)
        if not trades:
            logger.warning("⚠️  거래 내역 없음, 기본 메트릭 반환")
            return self._default_metrics()
        
        # 메트릭 계산
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]
        
        total_trades = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        
        # 승률
        winrate = win_count / total_trades if total_trades > 0 else 0.0
        
        # 평균 손익
        avg_win = sum(t["pnl"] for t in wins) / win_count if win_count > 0 else 0.0
        avg_loss = sum(t["pnl"] for t in losses) / loss_count if loss_count > 0 else -1.0
        
        # Profit Factor
        total_profit = sum(t["pnl"] for t in wins)
        total_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else (2.0 if total_profit > 0 else 0.0)
        
        # Expectancy Score (기대값)
        # E = (Win% × Avg Win) - (Loss% × Avg Loss)
        # 정규화: E / Avg Win (상대적 배율)
        if avg_win > 0:
            exp_score = (winrate * avg_win + (1 - winrate) * avg_loss) / avg_win
        else:
            exp_score = 0.0
        
        # Score Total (종합 점수)
        # 가중치: PF(40%) + WR(30%) + EXP(30%)
        # 정규화: 각 지표를 0~1로 스케일
        pf_score = min(profit_factor / 2.0, 1.0)  # PF 2.0 이상 = 만점
        wr_score = winrate  # 이미 0~1
        exp_score_norm = max(0.0, min(exp_score, 1.0))  # 0~1 클램프
        
        score_total = (pf_score * 0.4) + (wr_score * 0.3) + (exp_score_norm * 0.3)
        
        metrics = {
            "profit_factor": profit_factor,
            "winrate": winrate,
            "exp_score": exp_score,
            "score_total": score_total,
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "total_profit": total_profit,
            "total_loss": total_loss,
        }
        
        logger.debug(f"메트릭 계산 완료: PF={profit_factor:.2f}, WR={winrate:.2%}, EXP={exp_score:.2f}, SCORE={score_total:.2f}")
        
        return metrics
    
    def _sim_to_trade(self, sim: Dict[str, Any]) -> Dict[str, Any]:
        """
        시뮬 결과를 거래 형식으로 변환
        
        Args:
            sim: {
                "filled": bool,
                "fill_price": float,
                "pnl": float,
                "commission": float,
                ...
            }
        
        Returns:
            거래 딕셔너리
        """
        return {
            "pnl": sim.get("pnl", 0.0),
            "filled": sim.get("filled", False),
            "commission": sim.get("commission", 0.0),
        }
    
    def _default_metrics(self) -> Dict[str, Any]:
        """
        기본 메트릭 (거래 없음)
        
        Returns:
            기본값 딕셔너리
        """
        return {
            "profit_factor": 1.0,
            "winrate": 0.5,
            "exp_score": 0.0,
            "score_total": 0.5,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "total_profit": 0.0,
            "total_loss": 0.0,
        }


def compute_metrics_from_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    거래 리스트로부터 메트릭 계산 (헬퍼 함수)
    
    Args:
        trades: 거래 내역 리스트
    
    Returns:
        메트릭 딕셔너리
    """
    engine = MetricsEngine()
    return engine.compute({"trades": trades})
