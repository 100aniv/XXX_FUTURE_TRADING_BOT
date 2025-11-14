#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scorecard Generator (PHASE8)
=============================
백테스트 결과로부터 scorecard 생성
"""
from typing import Dict, Any, List
from pathlib import Path
from .metrics import calculate_metrics, calculate_sharpe_ratio
from .writer_csv import save_scorecard_csv
from .writer_md import save_scorecard_md


class ScorecardGenerator:
    """Scorecard 생성기"""
    
    def __init__(self, strategy_name: str, symbol: str, timeframe: str, period_info: Dict[str, Any] = None):
        """
        Args:
            strategy_name: 전략 이름 (예: 'scalping')
            symbol: 심볼 (예: 'BTCUSDT')
            timeframe: 타임프레임 (예: '5m')
            period_info: 실제 사용 기간 정보 (start_date, end_date, actual_days)
        """
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.timeframe = timeframe
        self.period_info = period_info or {}
    
    def generate(
        self, 
        trades: List[Dict[str, Any]], 
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Scorecard 생성 및 저장
        
        Args:
            trades: 거래 목록
            output_dir: 출력 디렉토리 (artifacts/{env}/{run_id}/)
        
        Returns:
            Dict[str, Any]: 생성된 scorecard 데이터
        
        Examples:
            >>> gen = ScorecardGenerator('scalping', 'BTCUSDT', '5m')
            >>> trades = [...]  # 백테스트 결과
            >>> output_dir = Path('artifacts/backtest_clean/20251114_135030_a7f3/')
            >>> scorecard = gen.generate(trades, output_dir)
        """
        # 지표 계산
        metrics = calculate_metrics(trades)
        sharpe = calculate_sharpe_ratio(trades)
        
        # Scorecard 데이터 구성
        scorecard = {
            'strategy': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'trades_closed': metrics['trades_closed'],
            'winrate': metrics['winrate'],
            'profit_factor': metrics['profit_factor'],
            'max_drawdown': metrics['max_drawdown'],
            'loss_over_8pct': metrics['loss_over_8pct'],
            'tp_hit': metrics['tp_hit'],
            'sharpe_ratio': sharpe,
            # ⭐ PHASE8-4: 실제 사용 기간 정보 포함
            'period_start': self.period_info.get('start_date', 'N/A'),
            'period_end': self.period_info.get('end_date', 'N/A'),
            'period_days': self.period_info.get('actual_days', 0)
        }
        
        # CSV 저장
        csv_path = save_scorecard_csv(scorecard, output_dir)
        
        # Markdown 저장
        md_path = save_scorecard_md(scorecard, output_dir)
        
        print(f"✅ [SCORECARD] 생성 완료:")
        print(f"  - CSV: {csv_path}")
        print(f"  - MD:  {md_path}")
        
        return scorecard
