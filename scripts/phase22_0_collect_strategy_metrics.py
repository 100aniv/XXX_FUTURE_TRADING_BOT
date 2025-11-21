#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-0: Strategy Metrics Collector
======================================
PHASE21 리포트 및 DB에서 전략별 성능 메트릭 수집

주요 메트릭:
- total_pnl
- win_rate
- trade_count
- max_drawdown (가능하면)

출력: artifacts/phase22_0_strategy_metrics.json
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def collect_from_db() -> Dict[str, Any]:
    """
    PostgreSQL에서 전략별 메트릭 수집
    
    Returns:
        Dict[strategy_name, metrics_dict]
    """
    results = {}
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # PHASE21 테스트는 주로 2025-11-21에 수행됨
                query = """
                SELECT 
                    strategy,
                    COUNT(*) as trade_count,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count,
                    MIN(pnl) as worst_trade,
                    MAX(pnl) as best_trade
                FROM paper_trades
                WHERE created_at >= '2025-11-21 00:00:00'
                GROUP BY strategy
                ORDER BY strategy;
                """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                for row in rows:
                    strategy, trade_count, total_pnl, avg_pnl, win_count, worst_trade, best_trade = row
                    
                    win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0
                    
                    results[strategy] = {
                        'trade_count': trade_count,
                        'total_pnl': float(total_pnl) if total_pnl else 0.0,
                        'avg_pnl': float(avg_pnl) if avg_pnl else 0.0,
                        'win_rate': round(win_rate, 2),
                        'win_count': win_count,
                        'worst_trade': float(worst_trade) if worst_trade else 0.0,
                        'best_trade': float(best_trade) if best_trade else 0.0,
                        'data_source': 'postgres'
                    }
                
                logger.info(f"✅ DB에서 {len(results)}개 전략 메트릭 수집 완료")
        
    except Exception as e:
        logger.error(f"❌ DB 쿼리 실패: {e}")
        results = {}
    
    return results


def add_manual_data(db_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    PHASE21 리포트에서 수동으로 확인한 데이터 추가
    
    DB에 없는 전략이나 보완이 필요한 경우 사용
    """
    # PHASE21 리포트 기준 (docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md)
    manual_data = {
        'scalping': {
            'timeframe': '3m',
            'classification': 'ACTIVE',
            'phase21_tests': [
                {'duration': '90s', 'trades': 31, 'pnl': -707.65},
                {'duration': '2min', 'trades': 33, 'pnl': -746.34},
                {'duration': '2min', 'trades': 28, 'pnl': 24.09}  # PHASE21-1A
            ],
            'note': 'High-frequency confirmed'
        },
        'reversion': {
            'timeframe': '5m',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '15min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Mean reversion conditions rarely met in short tests'
        },
        'swing_bb': {
            'timeframe': '5m',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '5-15min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Bollinger Band conditions strict'
        },
        'breakout': {
            'timeframe': '15m',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '5-15min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Requires clear breakout patterns'
        },
        'daytrade': {
            'timeframe': '15m',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '5-15min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Intraday trend requires longer test'
        },
        'trend': {
            'timeframe': '1h',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '5min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Long-term strategy, needs days for meaningful signals'
        },
        'swing': {
            'timeframe': '1h',
            'classification': 'LOW_FREQ',
            'phase21_tests': [
                {'duration': '5-15min', 'trades': 0, 'pnl': 0.0}
            ],
            'note': 'Long-term strategy, needs days for meaningful signals'
        }
    }
    
    # DB 데이터와 수동 데이터 병합
    merged = {}
    all_strategies = set(db_results.keys()) | set(manual_data.keys())
    
    for strategy in all_strategies:
        merged[strategy] = manual_data.get(strategy, {})
        
        if strategy in db_results:
            merged[strategy]['db_metrics'] = db_results[strategy]
        else:
            merged[strategy]['db_metrics'] = {
                'trade_count': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'data_source': 'manual_only'
            }
    
    return merged


def classify_strategy(data: Dict[str, Any]) -> str:
    """
    전략을 KEEP/RESERVE/DROP으로 분류
    
    분류 기준:
    - KEEP: trade_count >= 20 AND (win_rate >= 45 OR avg_pnl >= 0)
    - RESERVE: 데이터 부족하지만 인프라 검증 PASS (1h 전략 등)
    - DROP: 명백한 문제 (현재는 없음)
    """
    db_metrics = data.get('db_metrics', {})
    trade_count = db_metrics.get('trade_count', 0)
    win_rate = db_metrics.get('win_rate', 0)
    avg_pnl = db_metrics.get('avg_pnl', 0)
    classification = data.get('classification', 'UNKNOWN')
    timeframe = data.get('timeframe', '')
    
    # KEEP 기준: 충분한 거래 + 합리적 성능
    if trade_count >= 20:
        if win_rate >= 45 or avg_pnl >= 0:
            return 'KEEP'
        else:
            return 'RESERVE'  # 데이터는 있지만 성능 재평가 필요
    
    # RESERVE 기준: 데이터 부족하지만 전략 자체는 유효
    # - ACTIVE 전략 (scalping)은 우선 KEEP
    # - LOW_FREQ + 1h 타임프레임은 RESERVE (12~24h 테스트 필요)
    # - 나머지 LOW_FREQ는 RESERVE
    if classification == 'ACTIVE':
        return 'KEEP'
    elif '1h' in timeframe:
        return 'RESERVE'
    elif classification == 'LOW_FREQ':
        return 'RESERVE'
    
    # 기본값
    return 'RESERVE'


def main():
    """메인 실행 로직"""
    logger.info("=" * 60)
    logger.info("PHASE22-0: Strategy Metrics Collection Started")
    logger.info("=" * 60)
    
    # 1. DB에서 메트릭 수집
    logger.info("\n[1/4] Collecting metrics from PostgreSQL...")
    db_results = collect_from_db()
    
    # 2. 수동 데이터 병합
    logger.info("\n[2/4] Merging with PHASE21 report data...")
    merged_data = add_manual_data(db_results)
    
    # 3. 분류 수행
    logger.info("\n[3/4] Classifying strategies (KEEP/RESERVE/DROP)...")
    for strategy, data in merged_data.items():
        status = classify_strategy(data)
        data['status'] = status
        logger.info(f"  - {strategy:12s} → {status}")
    
    # 4. 결과 저장
    output_dir = project_root / 'artifacts'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'phase22_0_strategy_metrics.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n[4/4] Results saved to: {output_file}")
    logger.info("\n" + "=" * 60)
    logger.info("✅ PHASE22-0: Strategy Metrics Collection Complete")
    logger.info("=" * 60)
    
    # 요약 출력
    print("\n" + "=" * 60)
    print("STRATEGY CLASSIFICATION SUMMARY")
    print("=" * 60)
    for strategy in sorted(merged_data.keys()):
        data = merged_data[strategy]
        db_metrics = data.get('db_metrics', {})
        print(f"\n{strategy.upper()}")
        print(f"  Timeframe: {data.get('timeframe', 'N/A')}")
        print(f"  Classification: {data.get('classification', 'N/A')}")
        print(f"  Trades: {db_metrics.get('trade_count', 0)}")
        print(f"  PnL: ${db_metrics.get('total_pnl', 0.0):.2f}")
        print(f"  Win-rate: {db_metrics.get('win_rate', 0.0):.2f}%")
        print(f"  → STATUS: {data.get('status', 'UNKNOWN')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
