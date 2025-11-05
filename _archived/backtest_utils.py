#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 유틸리티
=================
백테스트 관련 공통 함수
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

from .logger import setup_logger
from .config import load_backtest_config

logger = setup_logger(__name__)


def get_backtest_period() -> Tuple[str, str]:
    """
    백테스트 기간 가져오기
    
    우선순위:
    1. 환경변수 (BACKTEST_START_DATE, BACKTEST_END_DATE)
    2. 프리셋 (BACKTEST_PERIOD)
    3. 기본값 (10년)
    
    Returns:
        (start_date, end_date)
    """
    backtest_cfg = load_backtest_config()
    
    # 직접 날짜 지정 (최우선)
    start_date = os.getenv('BACKTEST_START_DATE')
    end_date = os.getenv('BACKTEST_END_DATE')
    
    if start_date and end_date:
        logger.info(f"📅 직접 지정 기간: {start_date} ~ {end_date}")
        return start_date, end_date
    
    # 프리셋 사용
    period = os.getenv('BACKTEST_PERIOD', 'ten_years')
    
    periods = backtest_cfg.get('periods', {})
    logger.info(f"🔍 디버그: period={period}, periods.keys()={list(periods.keys())}")
    
    if period in periods:
        period_cfg = periods[period]
        start_date = period_cfg['start_date']
        end_date = period_cfg['end_date']
        logger.info(f"📅 프리셋 기간: {period} ({start_date} ~ {end_date})")
        return start_date, end_date
    
    # 기본값 (실제 데이터 파일명에 맞춤)
    logger.warning(f"⚠️ 알 수 없는 기간: {period}, 기본값 사용")
    return '2015-01-01', '2025-10-19'


def get_data_paths(symbol: str, start_date: str, end_date: str) -> Dict[str, Path]:
    """
    전략별 데이터 경로 생성
    
    Args:
        symbol: 심볼 (BTCUSDT, ETHUSDT 등)
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
    
    Returns:
        전략별 데이터 경로 딕셔너리
    """
    base_dir = Path("data/historical")
    
    return {
        'scalping':  base_dir / f"{symbol}_5m_{start_date}_{end_date}.csv",
        'daytrade':  base_dir / f"{symbol}_15m_{start_date}_{end_date}.csv",
        'swing':     base_dir / f"{symbol}_1h_{start_date}_{end_date}.csv",
        'trend':     base_dir / f"{symbol}_4h_{start_date}_{end_date}.csv",
        'reversion': base_dir / f"{symbol}_15m_{start_date}_{end_date}.csv",
        'breakout':  base_dir / f"{symbol}_1h_{start_date}_{end_date}.csv",
    }


def save_backtest_results(results: Dict, metadata: Dict = None, output_dir: str = 'reports/backtest'):
    """
    백테스트 결과 저장 (JSON + HTML 리포트)
    
    Args:
        results: 백테스트 결과 딕셔너리
        metadata: 메타데이터 (기간, 심볼, 설정 등)
        output_dir: 출력 디렉토리
    
    Returns:
        저장된 파일 경로들
    """
    import json
    from reports.trading_reporter import TradingReporter
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 메타데이터 추가
    full_results = {
        'metadata': metadata or {},
        'results': results,
        'generated_at': datetime.now().isoformat(),
    }
    
    # JSON 저장
    json_file = output_path / f"backtest_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"💾 JSON 저장: {json_file}")
    
    # HTML 리포트 생성
    try:
        html_file = output_path / f"backtest_{timestamp}.html"
        reporter = TradingReporter(full_results, mode='backtest')
        reporter.generate_html(str(html_file))
        logger.info(f"📊 HTML 리포트: {html_file}")
    except Exception as e:
        logger.error(f"⚠️ HTML 리포트 생성 실패: {e}")
    
    return json_file
