"""
Report Generator - Performance Report Generation

리포트 생성 및 배포:
- HTML/CSV/JSON 리포트 생성
- Telegram 메시지 발송
- 파일 저장 (reports/ 디렉터리)
"""

import logging
import json
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
from common.database import get_db_connection

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    리포트 생성기
    
    일일/주간 리포트를 생성하고 파일 저장 또는 텔레그램으로 발송합니다.
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Args:
            output_dir: 리포트 출력 디렉터리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(
        self,
        kpis: Dict[str, Any],
        strategy_rank: List[Dict[str, Any]] = None,
        sinks: List[str] = None
    ) -> Dict[str, Any]:
        """
        일일 리포트 생성
        
        Args:
            kpis: 일일 KPI dict
            strategy_rank: 전략 랭킹 리스트
            sinks: 출력 채널 (log, telegram, json, html)
        
        Returns:
            {status, json_path, html_path, telegram_sent}
        """
        try:
            sinks = sinks or ["log"]
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            result = {
                "status": "success",
                "json_path": None,
                "html_path": None,
                "telegram_sent": False
            }
            
            # JSON 저장
            if "json" in sinks:
                json_path = self.output_dir / f"daily_{date_str}.json"
                json_data = {
                    "date": date_str,
                    "kpis": kpis,
                    "strategy_rank": strategy_rank or [],
                    "generated_at": datetime.now().isoformat()
                }
                json_path.write_text(
                    json.dumps(json_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                result["json_path"] = str(json_path)
                logger.info(f"📊 일일 리포트 JSON 저장: {json_path}")
            
            # HTML 생성 (선택)
            if "html" in sinks:
                html_path = self.output_dir / f"daily_{date_str}.html"
                html_content = self._generate_html(kpis, strategy_rank, "일일 리포트")
                html_path.write_text(html_content, encoding='utf-8')
                result["html_path"] = str(html_path)
                logger.info(f"📊 일일 리포트 HTML 저장: {html_path}")
            
            # Telegram 발송 (선택)
            if "telegram" in sinks:
                message = self._format_telegram_message(kpis, strategy_rank, "일일")
                try:
                    from common.messaging import send_telegram_message
                    send_telegram_message(message)
                    result["telegram_sent"] = True
                    logger.info("📊 일일 리포트 Telegram 발송 완료")
                except Exception as e:
                    logger.warning(f"⚠️ Telegram 발송 실패: {e}")
            
            # Log 출력
            if "log" in sinks:
                logger.info(f"📊 일일 리포트: 거래={kpis.get('trades', 0)}건, 승률={kpis.get('win_rate', 0):.1%}, PnL={kpis.get('pnl_sum', 0):.2f}")
            
            return result
        except Exception as e:
            logger.error(f"❌ generate_daily_report 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def generate_weekly_report(
        self,
        kpis: Dict[str, Any],
        strategy_rank: List[Dict[str, Any]] = None,
        sinks: List[str] = None
    ) -> Dict[str, Any]:
        """
        주간 리포트 생성
        
        Args:
            kpis: 주간 KPI dict
            strategy_rank: 전략 랭킹 리스트
            sinks: 출력 채널
        
        Returns:
            {status, json_path, html_path, telegram_sent}
        """
        try:
            sinks = sinks or ["log"]
            week_str = datetime.now().strftime("%Y-W%V")
            
            result = {
                "status": "success",
                "json_path": None,
                "html_path": None,
                "telegram_sent": False
            }
            
            # JSON 저장
            if "json" in sinks:
                json_path = self.output_dir / f"weekly_{week_str}.json"
                json_data = {
                    "week": week_str,
                    "kpis": kpis,
                    "strategy_rank": strategy_rank or [],
                    "generated_at": datetime.now().isoformat()
                }
                json_path.write_text(
                    json.dumps(json_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                result["json_path"] = str(json_path)
                logger.info(f"📊 주간 리포트 JSON 저장: {json_path}")
            
            # HTML 생성 (선택)
            if "html" in sinks:
                html_path = self.output_dir / f"weekly_{week_str}.html"
                html_content = self._generate_html(kpis, strategy_rank, "주간 리포트")
                html_path.write_text(html_content, encoding='utf-8')
                result["html_path"] = str(html_path)
                logger.info(f"📊 주간 리포트 HTML 저장: {html_path}")
            
            # Telegram 발송 (선택)
            if "telegram" in sinks:
                message = self._format_telegram_message(kpis, strategy_rank, "주간")
                try:
                    from common.messaging import send_telegram_message
                    send_telegram_message(message)
                    result["telegram_sent"] = True
                    logger.info("📊 주간 리포트 Telegram 발송 완료")
                except Exception as e:
                    logger.warning(f"⚠️ Telegram 발송 실패: {e}")
            
            # Log 출력
            if "log" in sinks:
                logger.info(f"📊 주간 리포트: 거래={kpis.get('trades', 0)}건, 승률={kpis.get('win_rate', 0):.1%}, PnL={kpis.get('pnl_sum', 0):.2f}")
            
            return result
        except Exception as e:
            logger.error(f"❌ generate_weekly_report 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_html(
        self,
        kpis: Dict[str, Any],
        strategy_rank: List[Dict[str, Any]],
        title: str
    ) -> str:
        """HTML 리포트 생성 (간소화)"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <h2>KPI 요약</h2>
    <table>
        <tr><th>지표</th><th>값</th></tr>
        <tr><td>거래 수</td><td>{kpis.get('trades', 0)}</td></tr>
        <tr><td>승률</td><td>{kpis.get('win_rate', 0):.2%}</td></tr>
        <tr><td>총 PnL</td><td>{kpis.get('pnl_sum', 0):.2f}</td></tr>
        <tr><td>평균 PnL</td><td>{kpis.get('pnl_avg', 0):.2f}</td></tr>
        <tr><td>MDD</td><td>{kpis.get('mdd', 0):.2f}%</td></tr>
    </table>
    
    <h2>전략 랭킹</h2>
    <table>
        <tr><th>전략</th><th>점수</th><th>거래</th><th>PnL</th></tr>
        {''.join([f"<tr><td>{s.get('name', 'N/A')}</td><td>{s.get('score', 0)}</td><td>{s.get('trades', 0)}</td><td>{s.get('pnl', 0):.2f}</td></tr>" for s in (strategy_rank or [])])}
    </table>
    
    <p><em>생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
</body>
</html>
"""
        return html
    
    def _format_telegram_message(
        self,
        kpis: Dict[str, Any],
        strategy_rank: List[Dict[str, Any]],
        period: str
    ) -> str:
        """Telegram 메시지 포맷"""
        msg = f"📊 **{period} 리포트**\n\n"
        msg += f"거래: {kpis.get('trades', 0)}건\n"
        msg += f"승률: {kpis.get('win_rate', 0):.1%}\n"
        msg += f"PnL: {kpis.get('pnl_sum', 0):.2f}\n"
        msg += f"MDD: {kpis.get('mdd', 0):.2f}%\n"
        
        if strategy_rank:
            msg += f"\n**전략 랭킹 TOP 3:**\n"
            for i, s in enumerate(strategy_rank[:3], 1):
                msg += f"{i}. {s.get('name', 'N/A')}: {s.get('score', 0)}\n"
        
        return msg
    
    def generate_backtest_report(
        self,
        trial_id: str = None,
        table_name: str = "trades",
        schema: str = "trading",
        output_file: str = None,
        sinks: List[str] = None
    ) -> Dict[str, Any]:
        """
        백테스트 리포트 생성 (PostgreSQL 기반, TUNING_VIBLE 100점 계산)
        
        Args:
            trial_id: 백테스트 trial ID (필터링용, 선택)
            table_name: 테이블명 (기본: trades)
            schema: 스키마명 (기본: trading)
            output_file: 출력 HTML 파일 경로 (선택)
            sinks: 출력 채널 (log, json, html)
        
        Returns:
            {status, total_score, metrics, json_path, html_path}
        """
        try:
            sinks = sinks or ["log"]
            
            # TUNING_VIBLE 점수 계산 (PostgreSQL)
            total_score, score_details = self._calculate_tuning_score_postgres(
                trial_id, table_name, schema
            )
            
            if not score_details:
                logger.warning("⚠️ 거래 데이터 없음 - 리포트 생성 중단")
                return {"status": "no_data", "total_score": 0}
            
            result = {
                "status": "success",
                "total_score": total_score,
                "metrics": score_details.get("metrics", {}),
                "scores": score_details,
                "json_path": None,
                "html_path": None
            }
            
            # JSON 저장
            if "json" in sinks:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_path = self.output_dir / f"backtest_{trial_id or timestamp}.json"
                json_data = {
                    "trial_id": trial_id,
                    "total_score": total_score,
                    "metrics": score_details.get("metrics", {}),
                    "scores": {k: v for k, v in score_details.items() if k != "metrics"},
                    "generated_at": datetime.now().isoformat()
                }
                json_path.write_text(
                    json.dumps(json_data, indent=2, ensure_ascii=False),
                    encoding='utf-8'
                )
                result["json_path"] = str(json_path)
                logger.info(f"📊 백테스트 리포트 JSON 저장: {json_path}")
            
            # HTML 생성
            if "html" in sinks or output_file:
                if not output_file:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = self.output_dir / f"backtest_{trial_id or timestamp}.html"
                else:
                    output_file = Path(output_file)
                
                html_content = self._generate_backtest_html(
                    total_score, score_details, trial_id
                )
                output_file.write_text(html_content, encoding='utf-8')
                result["html_path"] = str(output_file)
                logger.info(f"📊 백테스트 리포트 HTML 저장: {output_file}")
            
            # Log 출력
            if "log" in sinks:
                self._log_tuning_score(total_score, score_details)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ generate_backtest_report 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def _calculate_tuning_score_postgres(
        self,
        trial_id: Optional[str],
        table_name: str,
        schema: str
    ) -> Tuple[float, Dict[str, Any]]:
        """
        TUNING_VIBLE 기준 100점 만점 계산 (PostgreSQL)
        
        가중치:
        - 승률 × RR (30점): Expectancy 근사값
        - 승률 (15점): 최소 승률
        - 손익비 RR (15점): 평균승/평균손
        - MDD (15점): 최대 낙폭
        - 연속 손실 (10점): 리스크 관리
        - Profit Factor (10점): 총이익/총손실
        - ROI (5점): 수익률
        
        Returns:
            (총점, 세부 점수 딕셔너리)
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # WHERE 조건
                where_clause = "WHERE status = 'CLOSED'"
                params = []
                if trial_id:
                    where_clause += " AND trial_id = %s"
                    params.append(trial_id)
                
                # 기본 통계
                cur.execute(f"""
                    SELECT COUNT(*) FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                total = cur.fetchone()[0]
                
                if total == 0:
                    return 0.0, {}
                
                # 승/패 카운트
                cur.execute(f"""
                    SELECT 
                        COUNT(*) FILTER (WHERE pnl > 0) as wins,
                        COUNT(*) FILTER (WHERE pnl < 0) as losses
                    FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                row = cur.fetchone()
                total_wins, total_losses = row[0], row[1]
                
                # 승률
                winrate = (total_wins / total) * 100 if total > 0 else 0
                
                # RR (손익비)
                cur.execute(f"""
                    SELECT 
                        AVG(pnl) FILTER (WHERE pnl > 0) as avg_win,
                        AVG(pnl) FILTER (WHERE pnl < 0) as avg_loss
                    FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                row = cur.fetchone()
                avg_win = float(row[0]) if row[0] else 0
                avg_loss = float(row[1]) if row[1] else -1
                rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
                
                # 승률 × RR
                exp_score = (winrate / 100) * rr
                
                # MDD 계산 (equity curve)
                cur.execute(f"""
                    SELECT pnl FROM {schema}.{table_name}
                    {where_clause}
                    ORDER BY ts_close
                """, params)
                equity_curve = []
                equity = 10000
                for row in cur.fetchall():
                    equity += float(row[0])
                    equity_curve.append(equity)
                
                peak = equity_curve[0] if equity_curve else 10000
                mdd = 0
                for eq in equity_curve:
                    if eq > peak:
                        peak = eq
                    drawdown = ((eq - peak) / peak) * 100
                    if drawdown < mdd:
                        mdd = drawdown
                
                # 연속 손실
                cur.execute(f"""
                    SELECT pnl FROM {schema}.{table_name}
                    {where_clause}
                    ORDER BY ts_close
                """, params)
                max_consecutive_losses = 0
                current_consecutive = 0
                for row in cur.fetchall():
                    if float(row[0]) < 0:
                        current_consecutive += 1
                        max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
                    else:
                        current_consecutive = 0
                
                # Profit Factor
                cur.execute(f"""
                    SELECT 
                        SUM(pnl) FILTER (WHERE pnl > 0) as total_profit,
                        SUM(pnl) FILTER (WHERE pnl < 0) as total_loss
                    FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                row = cur.fetchone()
                total_profit = float(row[0]) if row[0] else 0
                total_loss = abs(float(row[1])) if row[1] else 1
                profit_factor = total_profit / total_loss if total_loss > 0 else 0
                
                # ROI
                cur.execute(f"""
                    SELECT SUM(pnl) FROM {schema}.{table_name}
                    {where_clause}
                """, params)
                total_pnl = float(cur.fetchone()[0] or 0)
                roi = (total_pnl / 10000) * 100
                
                # 점수 계산 (100점 만점)
                scores = {}
                
                # 1. 승률 × RR (30점) - 목표 2.0 이상
                scores['exp_score'] = min(30, (exp_score / 2.0) * 30) if exp_score > 0 else 0
                
                # 2. 승률 (15점) - 목표 50% 이상
                scores['winrate'] = min(15, (winrate / 50) * 15) if winrate > 0 else 0
                
                # 3. RR (15점) - 목표 1.5 이상
                scores['rr'] = min(15, (rr / 1.5) * 15) if rr > 0 else 0
                
                # 4. MDD (15점) - 목표 -20% 이상
                if mdd >= -20:
                    scores['mdd'] = 15
                elif mdd >= -40:
                    scores['mdd'] = 15 * (1 - (abs(mdd) - 20) / 20)
                else:
                    scores['mdd'] = 0
                
                # 5. 연속 손실 (10점) - 목표 6 이하
                if max_consecutive_losses <= 6:
                    scores['consecutive'] = 10
                elif max_consecutive_losses <= 10:
                    scores['consecutive'] = 10 * (1 - (max_consecutive_losses - 6) / 4)
                else:
                    scores['consecutive'] = 0
                
                # 6. Profit Factor (10점) - 목표 1.3 이상
                scores['pf'] = min(10, (profit_factor / 1.3) * 10) if profit_factor > 0 else 0
                
                # 7. ROI (5점) - 목표 10% 이상
                scores['roi'] = min(5, (roi / 10) * 5) if roi > 0 else 0
                
                total_score = sum(scores.values())
                
                # 세부 정보 추가
                scores['metrics'] = {
                    'exp_score': exp_score,
                    'winrate': winrate,
                    'rr': rr,
                    'mdd': mdd,
                    'consecutive': max_consecutive_losses,
                    'pf': profit_factor,
                    'roi': roi,
                    'total_trades': total
                }
                
                return total_score, scores
    
    def _generate_backtest_html(
        self,
        total_score: float,
        score_details: Dict[str, Any],
        trial_id: Optional[str]
    ) -> str:
        """백테스트 HTML 리포트 생성 (TUNING_VIBLE 상세)"""
        m = score_details.get('metrics', {})
        
        # 등급 판정
        if total_score >= 80:
            grade = "🎉 S등급 (라이브 진입 가능)"
            grade_color = "#4CAF50"
        elif total_score >= 70:
            grade = "✅ A등급 (Paper 검증 추천)"
            grade_color = "#8BC34A"
        elif total_score >= 60:
            grade = "⚠️ B등급 (개선 필요)"
            grade_color = "#FFC107"
        else:
            grade = "❌ C등급 (재튜닝 필요)"
            grade_color = "#F44336"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>백테스트 리포트 - TUNING_VIBLE</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ background: {grade_color}; color: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .summary h2 {{ margin: 0 0 10px 0; }}
        .summary .score {{ font-size: 48px; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .pass {{ color: #4CAF50; font-weight: bold; }}
        .fail {{ color: #F44336; font-weight: bold; }}
        .footer {{ margin-top: 30px; text-align: center; color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 TUNING_VIBLE 백테스트 리포트</h1>
        
        <div class="summary">
            <h2>{grade}</h2>
            <div class="score">{total_score:.1f} / 100점</div>
            <p>Trial ID: {trial_id or 'N/A'}</p>
            <p>총 거래: {m.get('total_trades', 0)}건</p>
        </div>
        
        <h2>📊 세부 평가 지표</h2>
        <table>
            <tr>
                <th>지표</th>
                <th>목표</th>
                <th>현재</th>
                <th>배점</th>
                <th>획득</th>
                <th>상태</th>
            </tr>
            <tr>
                <td>승률 × RR</td>
                <td>≥ 2.0</td>
                <td>{m.get('exp_score', 0):.2f}</td>
                <td>30점</td>
                <td>{score_details.get('exp_score', 0):.1f}점</td>
                <td class="{'pass' if m.get('exp_score', 0) >= 2.0 else 'fail'}">{'✅ PASS' if m.get('exp_score', 0) >= 2.0 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>승률</td>
                <td>≥ 50%</td>
                <td>{m.get('winrate', 0):.1f}%</td>
                <td>15점</td>
                <td>{score_details.get('winrate', 0):.1f}점</td>
                <td class="{'pass' if m.get('winrate', 0) >= 50 else 'fail'}">{'✅ PASS' if m.get('winrate', 0) >= 50 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>손익비 (RR)</td>
                <td>≥ 1.5</td>
                <td>{m.get('rr', 0):.2f}</td>
                <td>15점</td>
                <td>{score_details.get('rr', 0):.1f}점</td>
                <td class="{'pass' if m.get('rr', 0) >= 1.5 else 'fail'}">{'✅ PASS' if m.get('rr', 0) >= 1.5 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>MDD</td>
                <td>≥ -20%</td>
                <td>{m.get('mdd', 0):.1f}%</td>
                <td>15점</td>
                <td>{score_details.get('mdd', 0):.1f}점</td>
                <td class="{'pass' if m.get('mdd', 0) >= -20 else 'fail'}">{'✅ PASS' if m.get('mdd', 0) >= -20 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>연속 손실 Max</td>
                <td>≤ 6</td>
                <td>{m.get('consecutive', 0)}</td>
                <td>10점</td>
                <td>{score_details.get('consecutive', 0):.1f}점</td>
                <td class="{'pass' if m.get('consecutive', 0) <= 6 else 'fail'}">{'✅ PASS' if m.get('consecutive', 0) <= 6 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>Profit Factor</td>
                <td>≥ 1.3</td>
                <td>{m.get('pf', 0):.2f}</td>
                <td>10점</td>
                <td>{score_details.get('pf', 0):.1f}점</td>
                <td class="{'pass' if m.get('pf', 0) >= 1.3 else 'fail'}">{'✅ PASS' if m.get('pf', 0) >= 1.3 else '❌ FAIL'}</td>
            </tr>
            <tr>
                <td>ROI</td>
                <td>≥ 10%</td>
                <td>{m.get('roi', 0):.1f}%</td>
                <td>5점</td>
                <td>{score_details.get('roi', 0):.1f}점</td>
                <td class="{'pass' if m.get('roi', 0) >= 10 else 'fail'}">{'✅ PASS' if m.get('roi', 0) >= 10 else '❌ FAIL'}</td>
            </tr>
            <tr style="font-weight: bold; background: #e8f5e9;">
                <td>총점</td>
                <td>-</td>
                <td>-</td>
                <td>100점</td>
                <td>{total_score:.1f}점</td>
                <td>-</td>
            </tr>
        </table>
        
        <div class="footer">
            <p>Generated by Analytics Module (PostgreSQL)</p>
            <p>© 2025 Trading Bot System</p>
            <p><em>생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def _log_tuning_score(self, total_score: float, score_details: Dict[str, Any]):
        """TUNING_VIBLE 점수 로그 출력"""
        m = score_details.get('metrics', {})
        
        logger.info('=' * 100)
        logger.info('🎯 TUNING_VIBLE 100점 만점 검증')
        logger.info('=' * 100)
        logger.info('')
        logger.info(f'📊 총 거래: {m.get("total_trades", 0)}건')
        logger.info('')
        logger.info(f'| {"지표":25s} | {"목표":15s} | {"현재":15s} | {"배점":8s} | {"획득":8s} | {"상태":8s} |')
        logger.info('-' * 100)
        
        def log_metric(name, target, current, max_score, earned_score, passed):
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f'| {name:25s} | {target:15s} | {current:15s} | {max_score:6.0f}점 | {earned_score:6.1f}점 | {status:8s} |')
        
        log_metric("승률 × RR", "≥ 2.0", f"{m.get('exp_score', 0):.2f}", 30, score_details.get('exp_score', 0), m.get('exp_score', 0) >= 2.0)
        log_metric("승률", "≥ 50%", f"{m.get('winrate', 0):.1f}%", 15, score_details.get('winrate', 0), m.get('winrate', 0) >= 50)
        log_metric("손익비 (RR)", "≥ 1.5", f"{m.get('rr', 0):.2f}", 15, score_details.get('rr', 0), m.get('rr', 0) >= 1.5)
        log_metric("MDD", "≥ -20%", f"{m.get('mdd', 0):.1f}%", 15, score_details.get('mdd', 0), m.get('mdd', 0) >= -20)
        log_metric("연속 손실 Max", "≤ 6", f"{m.get('consecutive', 0)}", 10, score_details.get('consecutive', 0), m.get('consecutive', 0) <= 6)
        log_metric("Profit Factor", "≥ 1.3", f"{m.get('pf', 0):.2f}", 10, score_details.get('pf', 0), m.get('pf', 0) >= 1.3)
        log_metric("ROI", "≥ 10%", f"{m.get('roi', 0):.1f}%", 5, score_details.get('roi', 0), m.get('roi', 0) >= 10)
        
        logger.info('-' * 100)
        logger.info(f'| {"총점":25s} | {"":15s} | {"":15s} | {"100":6s}점 | {total_score:6.1f}점 | {"":8s} |')
        logger.info('-' * 100)
        logger.info('')
        
        # 등급 판정
        if total_score >= 80:
            grade = "🎉 S등급 (라이브 진입 가능)"
        elif total_score >= 70:
            grade = "✅ A등급 (Paper 검증 추천)"
        elif total_score >= 60:
            grade = "⚠️ B등급 (개선 필요)"
        else:
            grade = "❌ C등급 (재튜닝 필요)"
        
        logger.info(f'🏆 등급: {grade}')
        logger.info('=' * 100)


# 편의 함수
def generate_daily_report(
    kpis: Dict[str, Any],
    strategy_rank: List[Dict[str, Any]] = None,
    sinks: List[str] = None,
    output_dir: str = "reports"
) -> Dict[str, Any]:
    """일일 리포트 생성 (편의 함수)"""
    generator = ReportGenerator(output_dir)
    return generator.generate_daily_report(kpis, strategy_rank, sinks)


def generate_weekly_report(
    kpis: Dict[str, Any],
    strategy_rank: List[Dict[str, Any]] = None,
    sinks: List[str] = None,
    output_dir: str = "reports"
) -> Dict[str, Any]:
    """주간 리포트 생성 (편의 함수)"""
    generator = ReportGenerator(output_dir)
    return generator.generate_weekly_report(kpis, strategy_rank, sinks)


def generate_backtest_report(
    trial_id: str = None,
    table_name: str = "trades",
    schema: str = "trading",
    output_file: str = None,
    sinks: List[str] = None,
    output_dir: str = "reports"
) -> Dict[str, Any]:
    """백테스트 리포트 생성 (편의 함수, PostgreSQL 기반)"""
    generator = ReportGenerator(output_dir)
    return generator.generate_backtest_report(
        trial_id, table_name, schema, output_file, sinks
    )


__all__ = [
    "ReportGenerator",
    "generate_daily_report",
    "generate_weekly_report",
    "generate_backtest_report"
]
