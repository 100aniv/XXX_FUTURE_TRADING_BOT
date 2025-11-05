"""
Trade Analyzer - Trading Performance Analysis

거래 성과 분석 및 KPI 집계:
- 일일/주간 KPI 계산
- PnL, 승률, RR, MDD, 슬리피지 등
- PostgreSQL DB 기반 거래 분석
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
from common.database import get_db_connection

logger = logging.getLogger(__name__)


class TradeAnalyzer:
    """
    거래 분석기
    
    PostgreSQL DB에서 거래 기록을 읽어 성과를 집계합니다.
    """
    
    def __init__(self):
        """
        DB 연결은 common.database.get_db_connection() 사용 (환경변수 기반)
        """
        pass
    
    def get_daily_kpis(
        self,
        date: str = None,
        enable_slippage: bool = True,
        enable_sharpe: bool = False
    ) -> Dict[str, Any]:
        """
        일일 KPI 집계
        
        Args:
            date: 날짜 (YYYY-MM-DD, None이면 오늘)
            enable_slippage: 슬리피지 계산 여부
            enable_sharpe: Sharpe-like 지표 계산 여부
        
        Returns:
            {
                trades: int,
                win_rate: float,
                pnl_sum: float,
                pnl_avg: float,
                rr_avg: float,
                mdd: float,
                slippage_avg: float (optional),
                sharpe_like: float (optional)
            }
        """
        try:
            target_date = date or datetime.now().strftime("%Y-%m-%d")
            
            # PostgreSQL DB 연결
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 닫힌 거래만 조회 (status='CLOSED', ts_close가 target_date)
                    cur.execute("""
                        SELECT 
                            trade_id, symbol, side, entry_price, exit_price, quantity,
                            pnl, pnl_pct, fees, strategy_id, exit_reason,
                            ts_open, ts_close
                        FROM trading.trades
                        WHERE status = 'CLOSED'
                          AND DATE(ts_close) = %s
                        ORDER BY ts_close
                    """, (target_date,))
                    
                    trades_list = cur.fetchall()
            
            if not trades_list:
                logger.info(f"📊 일일 KPI: {target_date} - 거래 없음")
                return {
                    "trades": 0,
                    "win_rate": 0.0,
                    "pnl_sum": 0.0,
                    "pnl_avg": 0.0,
                    "rr_avg": 0.0,
                    "mdd": 0.0,
                    "slippage_avg": 0.0 if enable_slippage else None,
                    "sharpe_like": 0.0 if enable_sharpe else None
                }
            
            # KPI 계산
            total_trades = len(trades_list)
            pnl_list = [float(t['pnl'] or 0) for t in trades_list]
            wins = [p for p in pnl_list if p > 0]
            losses = [p for p in pnl_list if p < 0]
            
            pnl_sum = sum(pnl_list)
            pnl_avg = pnl_sum / total_trades if total_trades > 0 else 0.0
            win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
            
            # RR 평균 (승리 평균 / 손실 평균 절댓값)
            avg_win = sum(wins) / len(wins) if wins else 0.0
            avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
            rr_avg = avg_win / avg_loss if avg_loss > 0 else 0.0
            
            # MDD 계산 (누적 PnL 기준)
            cumulative_pnl = []
            cum = 0
            for p in pnl_list:
                cum += p
                cumulative_pnl.append(cum)
            
            peak = cumulative_pnl[0] if cumulative_pnl else 0
            mdd = 0.0
            for cum_val in cumulative_pnl:
                if cum_val > peak:
                    peak = cum_val
                drawdown = peak - cum_val
                if drawdown > mdd:
                    mdd = drawdown
            
            # 슬리피지 (구현 예정)
            slippage_avg = 0.0 if enable_slippage else None
            
            # Sharpe-like (구현 예정)
            sharpe_like = 0.0 if enable_sharpe else None
            
            logger.info(f"📊 일일 KPI: {target_date} - 거래 {total_trades}건, PnL {pnl_sum:.2f}, 승률 {win_rate:.1%}")
            
            return {
                "trades": total_trades,
                "win_rate": round(win_rate, 4),
                "pnl_sum": round(pnl_sum, 2),
                "pnl_avg": round(pnl_avg, 2),
                "rr_avg": round(rr_avg, 2),
                "mdd": round(mdd, 2),
                "slippage_avg": slippage_avg,
                "sharpe_like": sharpe_like
            }
        except Exception as e:
            logger.error(f"❌ get_daily_kpis 실패: {e}")
            return {
                "trades": 0,
                "win_rate": 0.0,
                "pnl_sum": 0.0,
                "pnl_avg": 0.0,
                "rr_avg": 0.0,
                "mdd": 0.0
            }
    
    def get_weekly_kpis(
        self,
        week_start: str = None,
        enable_slippage: bool = True,
        enable_sharpe: bool = False
    ) -> Dict[str, Any]:
        """
        주간 KPI 집계
        
        Args:
            week_start: 주 시작일 (YYYY-MM-DD, None이면 이번 주)
            enable_slippage: 슬리피지 계산 여부
            enable_sharpe: Sharpe-like 지표 계산 여부
        
        Returns:
            {
                trades: int,
                win_rate: float,
                pnl_sum: float,
                pnl_avg: float,
                rr_avg: float,
                mdd: float,
                best_day: {date, pnl},
                worst_day: {date, pnl}
            }
        """
        try:
            # 주 시작일 계산 (월요일 기준)
            if week_start:
                start_date = datetime.strptime(week_start, "%Y-%m-%d")
            else:
                today = datetime.now()
                start_date = today - timedelta(days=today.weekday())  # 이번 주 월요일
            
            end_date = start_date + timedelta(days=6)  # 일요일
            
            # PostgreSQL DB 연결
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 주간 거래 조회
                    cur.execute("""
                        SELECT 
                            trade_id, symbol, side, entry_price, exit_price, quantity,
                            pnl, pnl_pct, fees, strategy_id, exit_reason,
                            ts_open, ts_close, DATE(ts_close) as close_date
                        FROM trading.trades
                        WHERE status = 'CLOSED'
                          AND DATE(ts_close) BETWEEN %s AND %s
                        ORDER BY ts_close
                    """, (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
                    
                    trades_list = cur.fetchall()
            
            if not trades_list:
                logger.info(f"📊 주간 KPI: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} - 거래 없음")
                return {
                    "trades": 0,
                    "win_rate": 0.0,
                    "pnl_sum": 0.0,
                    "pnl_avg": 0.0,
                    "rr_avg": 0.0,
                    "mdd": 0.0,
                    "best_day": {"date": None, "pnl": 0.0},
                    "worst_day": {"date": None, "pnl": 0.0}
                }
            
            # KPI 계산 (일일과 동일)
            total_trades = len(trades_list)
            pnl_list = [float(t['pnl'] or 0) for t in trades_list]
            wins = [p for p in pnl_list if p > 0]
            losses = [p for p in pnl_list if p < 0]
            
            pnl_sum = sum(pnl_list)
            pnl_avg = pnl_sum / total_trades if total_trades > 0 else 0.0
            win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
            
            avg_win = sum(wins) / len(wins) if wins else 0.0
            avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
            rr_avg = avg_win / avg_loss if avg_loss > 0 else 0.0
            
            # MDD
            cumulative_pnl = []
            cum = 0
            for p in pnl_list:
                cum += p
                cumulative_pnl.append(cum)
            
            peak = cumulative_pnl[0] if cumulative_pnl else 0
            mdd = 0.0
            for cum_val in cumulative_pnl:
                if cum_val > peak:
                    peak = cum_val
                drawdown = peak - cum_val
                if drawdown > mdd:
                    mdd = drawdown
            
            # 일별 PnL 집계 (best/worst day)
            daily_pnl = {}
            for t in trades_list:
                date_key = t['close_date']
                pnl_val = float(t['pnl'] or 0)
                if date_key not in daily_pnl:
                    daily_pnl[date_key] = 0.0
                daily_pnl[date_key] += pnl_val
            
            best_day = {"date": None, "pnl": 0.0}
            worst_day = {"date": None, "pnl": 0.0}
            
            if daily_pnl:
                best_date = max(daily_pnl, key=daily_pnl.get)
                worst_date = min(daily_pnl, key=daily_pnl.get)
                best_day = {"date": best_date, "pnl": round(daily_pnl[best_date], 2)}
                worst_day = {"date": worst_date, "pnl": round(daily_pnl[worst_date], 2)}
            
            logger.info(f"📊 주간 KPI: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} - 거래 {total_trades}건, PnL {pnl_sum:.2f}")
            
            return {
                "trades": total_trades,
                "win_rate": round(win_rate, 4),
                "pnl_sum": round(pnl_sum, 2),
                "pnl_avg": round(pnl_avg, 2),
                "rr_avg": round(rr_avg, 2),
                "mdd": round(mdd, 2),
                "best_day": best_day,
                "worst_day": worst_day
            }
        except Exception as e:
            logger.error(f"❌ get_weekly_kpis 실패: {e}")
            return {
                "trades": 0,
                "win_rate": 0.0,
                "pnl_sum": 0.0,
                "pnl_avg": 0.0,
                "rr_avg": 0.0,
                "mdd": 0.0
            }
    
    def get_trade_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        기간별 거래 요약
        
        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            거래 요약 정보
        """
        try:
            logger.info(f"📊 거래 요약 (구현 예정): {start_date} ~ {end_date}")
            
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0
            }
        except Exception as e:
            logger.error(f"❌ get_trade_summary 실패: {e}")
            return {}


# 편의 함수
def get_daily_kpis(
    db_path: str = None,
    date: str = None,
    enable_slippage: bool = True,
    enable_sharpe: bool = False
) -> Dict[str, Any]:
    """일일 KPI 집계 (편의 함수)"""
    analyzer = TradeAnalyzer(db_path)
    return analyzer.get_daily_kpis(date, enable_slippage, enable_sharpe)


def get_weekly_kpis(
    db_path: str = None,
    week_start: str = None,
    enable_slippage: bool = True,
    enable_sharpe: bool = False
) -> Dict[str, Any]:
    """주간 KPI 집계 (편의 함수)"""
    analyzer = TradeAnalyzer(db_path)
    return analyzer.get_weekly_kpis(week_start, enable_slippage, enable_sharpe)


__all__ = [
    "TradeAnalyzer",
    "get_daily_kpis",
    "get_weekly_kpis"
]
