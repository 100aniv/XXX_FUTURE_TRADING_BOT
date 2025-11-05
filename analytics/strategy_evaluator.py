"""
Strategy Evaluator - Strategy Performance Comparison

전략별 성능 비교 및 랭킹:
- 전략간 KPI 비교
- 성과 랭킹 및 스코어링
- 최적 전략 추천
- PostgreSQL DB 기반
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
from common.database import get_db_connection

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """
    전략 평가기
    
    PostgreSQL DB에서 여러 전략의 성과를 비교하고 랭킹을 산출합니다.
    """
    
    def __init__(self):
        """
        DB 연결은 common.database.get_db_connection() 사용 (환경변수 기반)
        """
        pass
    
    def compare_strategies(
        self,
        strategies: List[str] = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict[str, Any]]:
        """
        전략간 성과 비교
        
        Args:
            strategies: 비교할 전략 리스트 (None이면 전체)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            List[{
                strategy: str,
                trades: int,
                win_rate: float,
                pnl: float,
                mdd: float,
                sharpe: float,
                kpi_score: float,
                rank: int
            }]
        """
        try:
            # 날짜 범위 설정
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            # PostgreSQL DB 연결
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 전략별 성과 조회
                    if strategies:
                        placeholders = ','.join('%s' * len(strategies))
                        query = f"""
                            SELECT 
                                strategy_id,
                                COUNT(*) as trades,
                                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as win_rate,
                                SUM(pnl) as total_pnl,
                                AVG(pnl) as avg_pnl
                            FROM trading.trades
                            WHERE status = 'CLOSED'
                              AND DATE(ts_close) BETWEEN %s AND %s
                              AND strategy_id IN ({placeholders})
                            GROUP BY strategy_id
                        """
                        cur.execute(query, (start_date, end_date, *strategies))
                    else:
                        cur.execute("""
                            SELECT 
                                strategy_id,
                                COUNT(*) as trades,
                                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float / COUNT(*) as win_rate,
                                SUM(pnl) as total_pnl,
                                AVG(pnl) as avg_pnl
                            FROM trading.trades
                            WHERE status = 'CLOSED'
                              AND DATE(ts_close) BETWEEN %s AND %s
                            GROUP BY strategy_id
                        """, (start_date, end_date))
                    
                    results = cur.fetchall()
            
            if not results:
                logger.info(f"📊 전략 비교: {start_date} ~ {end_date} - 데이터 없음")
                return []
            
            # 결과 포맷팅 및 스코어 계산
            comparisons = []
            for row in results:
                # KPI 스코어 계산 (승률 40% + PnL 40% + 거래수 20%)
                win_rate = float(row['win_rate'] or 0)
                pnl = float(row['total_pnl'] or 0)
                trades = int(row['trades'] or 0)
                
                # 정규화 (0-100)
                win_score = win_rate * 100
                pnl_score = min(100, max(0, 50 + pnl / 100))  # PnL 기준 정규화
                trade_score = min(100, trades / 10 * 100)  # 거래 10개 = 100점
                
                kpi_score = (win_score * 0.4) + (pnl_score * 0.4) + (trade_score * 0.2)
                
                comparisons.append({
                    "strategy": row['strategy_id'],
                    "trades": trades,
                    "win_rate": round(win_rate, 4),
                    "pnl": round(pnl, 2),
                    "avg_pnl": round(float(row['avg_pnl'] or 0), 2),
                    "mdd": 0.0,  # TODO: MDD 계산
                    "sharpe": 0.0,  # TODO: Sharpe 계산
                    "kpi_score": round(kpi_score, 2),
                    "rank": 0  # 아래에서 설정
                })
            
            # 랭킹 부여 (kpi_score 기준 내림차순)
            comparisons.sort(key=lambda x: x['kpi_score'], reverse=True)
            for idx, comp in enumerate(comparisons):
                comp['rank'] = idx + 1
            
            logger.info(f"📊 전략 비교: {start_date} ~ {end_date} - {len(comparisons)}개 전략")
            
            return comparisons
        except Exception as e:
            logger.error(f"❌ compare_strategies 실패: {e}")
            return []
    
    def get_best_strategy(
        self,
        metric: str = "kpi_score",
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        최적 전략 추천
        
        Args:
            metric: 평가 지표 (kpi_score, pnl, win_rate, sharpe 등)
            start_date: 시작일
            end_date: 종료일
        
        Returns:
            {strategy, metric_value, trades, pnl, ...}
        """
        try:
            comparisons = self.compare_strategies(None, start_date, end_date)
            
            if not comparisons:
                return {}
            
            # 지표 기준 정렬
            sorted_strategies = sorted(
                comparisons,
                key=lambda x: x.get(metric, 0),
                reverse=True
            )
            
            return sorted_strategies[0] if sorted_strategies else {}
        except Exception as e:
            logger.error(f"❌ get_best_strategy 실패: {e}")
            return {}
    
    def calculate_kpi_score(self, strategy_kpis: Dict[str, Any]) -> float:
        """
        전략 KPI 종합 점수 계산
        
        Args:
            strategy_kpis: 전략 KPI dict
        
        Returns:
            종합 점수 (0-100)
        """
        try:
            # 가중 평균 점수 계산
            win_rate = strategy_kpis.get("win_rate", 0) * 100
            pnl_factor = min(100, max(0, strategy_kpis.get("profit_factor", 0) * 20))
            mdd_penalty = max(0, 100 - abs(strategy_kpis.get("mdd", 0)))
            sharpe_score = min(100, max(0, strategy_kpis.get("sharpe", 0) * 50))
            
            score = (
                win_rate * 0.3 +
                pnl_factor * 0.3 +
                mdd_penalty * 0.2 +
                sharpe_score * 0.2
            )
            
            return round(score, 1)
        except Exception as e:
            logger.warning(f"⚠️ calculate_kpi_score 실패: {e}")
            return 0.0


# 편의 함수
def compare_strategies(
    strategies: List[str] = None,
    db_path: str = None,
    start_date: str = None,
    end_date: str = None
) -> List[Dict[str, Any]]:
    """전략 비교 (편의 함수)"""
    evaluator = StrategyEvaluator(db_path)
    return evaluator.compare_strategies(strategies, start_date, end_date)


def get_best_strategy(
    metric: str = "kpi_score",
    db_path: str = None,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    """최적 전략 추천 (편의 함수)"""
    evaluator = StrategyEvaluator(db_path)
    return evaluator.get_best_strategy(metric, start_date, end_date)


__all__ = [
    "StrategyEvaluator",
    "compare_strategies",
    "get_best_strategy"
]
