#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Metrics Calculator
===============================
PHASE29-5: 백테스트 성능 지표 계산 모듈

목적:
- Summary JSON에 포함할 표준 성능 지표 계산
- Win Rate, Max Drawdown, PnL, Sharpe Ratio 등

사용처:
- execution/engine.py: 백테스트 종료 시 Summary 생성
- analytics/report_generator.py: 리포트 생성 시 재사용

"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from common.database import get_db_connection

logger = logging.getLogger(__name__)


def compute_performance_metrics_from_db(
    trial_id: Optional[str] = None,
    table_name: str = "trades",
    schema: str = "trading",
    initial_equity: float = 10000.0
) -> Dict[str, Any]:
    """
    PostgreSQL에서 거래 데이터를 읽어 성능 지표 계산
    
    Args:
        trial_id: 백테스트 trial ID (선택, None이면 전체)
        table_name: 테이블명 (기본: trades)
        schema: 스키마명 (기본: trading)
        initial_equity: 초기 자본 (기본: 10000 USDT)
    
    Returns:
        성능 지표 딕셔너리:
        {
            'num_trades': int,
            'pnl_total': float,
            'pnl_avg_per_trade': float,
            'win_rate': float (0~1),
            'max_drawdown': float (비율, 예: 0.15 = -15%),
            'max_drawdown_abs': float (절대값, USDT),
            'sharpe_ratio': float (연율 기준),
            'profit_factor': float,
            'num_wins': int,
            'num_losses': int,
            'avg_win': float,
            'avg_loss': float,
            'max_consecutive_losses': int,
            'roi': float (비율)
        }
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # WHERE 조건
                where_clause = "WHERE status = 'CLOSED'"
                params = []
                if trial_id:
                    where_clause += " AND trial_id = %s"
                    params.append(trial_id)
                
                # 1. 기본 통계: 총 거래 수
                cur.execute(f"""
                    SELECT COUNT(*) FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                num_trades = cur.fetchone()[0]
                
                if num_trades == 0:
                    logger.warning("⚠️ 성능 지표 계산: 거래 데이터 없음")
                    return _empty_metrics()
                
                # 2. 승/패 카운트 및 Win Rate
                cur.execute(f"""
                    SELECT 
                        COUNT(*) FILTER (WHERE pnl > 0) as wins,
                        COUNT(*) FILTER (WHERE pnl < 0) as losses,
                        COUNT(*) FILTER (WHERE pnl = 0) as breakeven
                    FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                row = cur.fetchone()
                num_wins, num_losses, num_breakeven = row[0], row[1], row[2]
                
                # Win Rate 계산 (breakeven 제외)
                total_non_be = num_wins + num_losses
                win_rate = (num_wins / total_non_be) if total_non_be > 0 else 0.0
                
                # 3. PnL 통계
                cur.execute(f"""
                    SELECT 
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl,
                        AVG(pnl) FILTER (WHERE pnl > 0) as avg_win,
                        AVG(pnl) FILTER (WHERE pnl < 0) as avg_loss,
                        SUM(pnl) FILTER (WHERE pnl > 0) as total_profit,
                        SUM(pnl) FILTER (WHERE pnl < 0) as total_loss
                    FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                row = cur.fetchone()
                pnl_total = float(row[0]) if row[0] else 0.0
                pnl_avg = float(row[1]) if row[1] else 0.0
                avg_win = float(row[2]) if row[2] else 0.0
                avg_loss = float(row[3]) if row[3] else 0.0
                total_profit = float(row[4]) if row[4] else 0.0
                total_loss = abs(float(row[5])) if row[5] else 0.0
                
                # 4. Profit Factor
                profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
                
                # 5. ROI
                roi = (pnl_total / initial_equity) if initial_equity > 0 else 0.0
                
                # 6. Max Drawdown (Equity Curve 기반)
                cur.execute(f"""
                    SELECT pnl FROM {schema}.{table_name}
                    {where_clause}
                    ORDER BY ts_close
                """, params)
                equity_curve = []
                equity = initial_equity
                for row in cur.fetchall():
                    equity += float(row[0])
                    equity_curve.append(equity)
                
                max_dd_ratio, max_dd_abs = _calculate_max_drawdown(equity_curve, initial_equity)
                
                # 7. 연속 손실
                cur.execute(f"""
                    SELECT pnl FROM {schema}.{table_name}
                    {where_clause}
                    ORDER BY ts_close
                """, params)
                max_consecutive_losses = _calculate_max_consecutive_losses(cur.fetchall())
                
                # 8. Sharpe Ratio (Trade 기반, 간단 버전)
                sharpe_ratio = _calculate_sharpe_ratio(
                    equity_curve, initial_equity, num_trades
                )
                
                # 결과 조합
                return {
                    'num_trades': num_trades,
                    'pnl_total': pnl_total,
                    'pnl_avg_per_trade': pnl_avg,
                    'win_rate': win_rate,
                    'max_drawdown': max_dd_ratio,
                    'max_drawdown_abs': max_dd_abs,
                    'sharpe_ratio': sharpe_ratio,
                    'profit_factor': profit_factor,
                    'num_wins': num_wins,
                    'num_losses': num_losses,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'max_consecutive_losses': max_consecutive_losses,
                    'roi': roi
                }
                
    except Exception as e:
        logger.error(f"❌ 성능 지표 계산 실패: {e}", exc_info=True)
        return _empty_metrics()


def compute_performance_metrics_from_trades(
    trades: List[Dict[str, Any]],
    initial_equity: float = 10000.0
) -> Dict[str, Any]:
    """
    Trade 리스트에서 직접 성능 지표 계산 (DB 없이)
    
    Args:
        trades: 종료된 포지션 리스트
            각 trade는 {'pnl': float, 'exit_time': timestamp} 필드 필요
        initial_equity: 초기 자본
    
    Returns:
        성능 지표 딕셔너리 (compute_performance_metrics_from_db와 동일 구조)
    """
    try:
        num_trades = len(trades)
        if num_trades == 0:
            logger.warning("⚠️ 성능 지표 계산: 거래 데이터 없음")
            return _empty_metrics()
        
        # 시간 순 정렬 (exit_time 기준)
        sorted_trades = sorted(trades, key=lambda t: t.get('exit_time', 0))
        
        # PnL 리스트 추출
        pnl_list = [t.get('pnl', 0.0) for t in sorted_trades]
        
        # 1. Win/Loss 카운트
        num_wins = sum(1 for pnl in pnl_list if pnl > 0)
        num_losses = sum(1 for pnl in pnl_list if pnl < 0)
        total_non_be = num_wins + num_losses
        win_rate = (num_wins / total_non_be) if total_non_be > 0 else 0.0
        
        # 2. PnL 통계
        pnl_total = sum(pnl_list)
        pnl_avg = pnl_total / num_trades if num_trades > 0 else 0.0
        
        wins = [pnl for pnl in pnl_list if pnl > 0]
        losses = [pnl for pnl in pnl_list if pnl < 0]
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(losses) / len(losses)) if losses else 0.0
        
        total_profit = sum(wins)
        total_loss = abs(sum(losses))
        
        # 3. Profit Factor
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
        
        # 4. ROI
        roi = (pnl_total / initial_equity) if initial_equity > 0 else 0.0
        
        # 5. Equity Curve 생성
        equity_curve = []
        equity = initial_equity
        for pnl in pnl_list:
            equity += pnl
            equity_curve.append(equity)
        
        # 6. Max Drawdown
        max_dd_ratio, max_dd_abs = _calculate_max_drawdown(equity_curve, initial_equity)
        
        # 7. 연속 손실
        max_consecutive_losses = _calculate_max_consecutive_losses_from_list(pnl_list)
        
        # 8. Sharpe Ratio
        sharpe_ratio = _calculate_sharpe_ratio(equity_curve, initial_equity, num_trades)
        
        return {
            'num_trades': num_trades,
            'pnl_total': pnl_total,
            'pnl_avg_per_trade': pnl_avg,
            'win_rate': win_rate,
            'max_drawdown': max_dd_ratio,
            'max_drawdown_abs': max_dd_abs,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'num_wins': num_wins,
            'num_losses': num_losses,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_consecutive_losses': max_consecutive_losses,
            'roi': roi
        }
        
    except Exception as e:
        logger.error(f"❌ 성능 지표 계산 실패 (from trades): {e}", exc_info=True)
        return _empty_metrics()


# ============================================================
# 내부 헬퍼 함수
# ============================================================

def _empty_metrics() -> Dict[str, Any]:
    """빈 성능 지표 딕셔너리 반환"""
    return {
        'num_trades': 0,
        'pnl_total': 0.0,
        'pnl_avg_per_trade': 0.0,
        'win_rate': 0.0,
        'max_drawdown': 0.0,
        'max_drawdown_abs': 0.0,
        'sharpe_ratio': None,
        'profit_factor': 0.0,
        'num_wins': 0,
        'num_losses': 0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'max_consecutive_losses': 0,
        'roi': 0.0
    }


def _calculate_max_drawdown(
    equity_curve: List[float],
    initial_equity: float
) -> Tuple[float, float]:
    """
    Max Drawdown 계산 (Running Peak 기준)
    
    Args:
        equity_curve: Equity 시계열 리스트
        initial_equity: 초기 자본
    
    Returns:
        (max_dd_ratio, max_dd_abs)
        - max_dd_ratio: 최대 낙폭 비율 (양수, 예: 0.15 = -15%)
        - max_dd_abs: 최대 낙폭 절대값 (음수, USDT)
    """
    if not equity_curve:
        return 0.0, 0.0
    
    peak = initial_equity
    max_dd_ratio = 0.0
    max_dd_abs = 0.0
    
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        
        # Drawdown 계산 (음수)
        dd_abs = equity - peak
        dd_ratio = (dd_abs / peak) if peak > 0 else 0.0
        
        # 최대 낙폭 갱신 (절대값이 더 큰 경우)
        if dd_abs < max_dd_abs:
            max_dd_abs = dd_abs
            max_dd_ratio = abs(dd_ratio)
    
    return max_dd_ratio, max_dd_abs


def _calculate_max_consecutive_losses(rows) -> int:
    """
    연속 손실 최대값 계산 (DB 쿼리 결과용)
    
    Args:
        rows: DB cursor.fetchall() 결과 [(pnl,), ...]
    
    Returns:
        최대 연속 손실 횟수
    """
    max_consecutive = 0
    current_consecutive = 0
    
    for row in rows:
        pnl = float(row[0])
        if pnl < 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive


def _calculate_max_consecutive_losses_from_list(pnl_list: List[float]) -> int:
    """
    연속 손실 최대값 계산 (PnL 리스트용)
    
    Args:
        pnl_list: PnL 값 리스트
    
    Returns:
        최대 연속 손실 횟수
    """
    max_consecutive = 0
    current_consecutive = 0
    
    for pnl in pnl_list:
        if pnl < 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive


def _calculate_sharpe_ratio(
    equity_curve: List[float],
    initial_equity: float,
    num_trades: int
) -> Optional[float]:
    """
    Sharpe Ratio 계산 (Trade 기반, 간단 버전)
    
    Args:
        equity_curve: Equity 시계열 리스트
        initial_equity: 초기 자본
        num_trades: 거래 수
    
    Returns:
        Sharpe Ratio (연율 기준) 또는 None (표본 부족 시)
    """
    if num_trades < 2 or not equity_curve:
        return None
    
    try:
        # Trade 단위 수익률 계산
        returns = []
        prev_equity = initial_equity
        for equity in equity_curve:
            ret = (equity - prev_equity) / prev_equity if prev_equity > 0 else 0.0
            returns.append(ret)
            prev_equity = equity
        
        if not returns:
            return None
        
        # 평균 및 표준편차
        import math
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_ret = math.sqrt(variance)
        
        if std_ret == 0:
            return None
        
        # Sharpe Ratio (연율화: sqrt(252) 적용)
        sharpe = (mean_ret / std_ret) * math.sqrt(252)
        
        return sharpe
        
    except Exception as e:
        logger.warning(f"⚠️ Sharpe Ratio 계산 실패: {e}")
        return None
