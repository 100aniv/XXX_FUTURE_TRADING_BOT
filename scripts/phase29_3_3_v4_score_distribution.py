#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3.3: V4 Score Distribution Analysis
===========================================
V4 전략의 Score/필터 분포를 정량 분석

목적:
- Regime 분포 (Trend vs Range)
- 필터 통과율 및 실패 이유
- Trend/Range Mode별 Score 분포
- 최종 신호 생성 비율 분석
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from common.backtest_indicators import add_v4_indicators
from strategies.utils.regime_detector import detect_regime
from strategies.btc5m_baseline_v4 import (
    _apply_filters,
    _calculate_trend_score,
    _calculate_range_score
)
from strategies.utils.dynamic_threshold import get_rsi_threshold, get_bb_threshold, calculate_bb_bands

logger = setup_logger('phase29_3_3_score_dist', log_type='application')


def load_and_prepare_data(data_file: str, start_date: str, end_date: str, config: dict) -> pd.DataFrame:
    """
    데이터 로딩 및 지표 추가
    
    Args:
        data_file: 데이터 파일 경로
        start_date: 시작 날짜
        end_date: 종료 날짜
        config: Config 딕셔너리
    
    Returns:
        pd.DataFrame: 지표가 추가된 데이터
    """
    logger.info(f"📂 데이터 로딩: {data_file}")
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"데이터 파일 없음: {data_file}")
    
    df = pd.read_csv(data_file)
    logger.info(f"✅ 전체 데이터 로딩: {len(df):,} rows")
    
    # 날짜 컬럼 파싱
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    elif 'date' in df.columns:
        df['timestamp'] = pd.to_datetime(df['date'])
    
    # 날짜 필터링
    df = df[
        (df['timestamp'] >= start_date) & 
        (df['timestamp'] < end_date)
    ].reset_index(drop=True)
    
    logger.info(f"✅ 날짜 필터링 후: {len(df):,} rows ({start_date} ~ {end_date})")
    
    # 지표 추가
    logger.info("🔧 지표 계산 중...")
    df = add_v4_indicators(df, config)
    logger.info("✅ 지표 계산 완료")
    
    return df


def analyze_score_distribution(df: pd.DataFrame, config: dict) -> dict:
    """
    Score & 필터 분포 분석
    
    Args:
        df: 지표가 포함된 데이터프레임
        config: V4 전략 Config
    
    Returns:
        dict: 분석 결과
    """
    logger.info("=" * 80)
    logger.info("📊 Score & 필터 분포 분석 시작")
    logger.info("=" * 80)
    
    results = {
        'total_candles': len(df),
        'regime_distribution': {},
        'filter_stats': {
            'total_pass': 0,
            'total_fail': 0,
            'fail_reasons': Counter()
        },
        'trend_score_distribution': {},
        'range_score_distribution': {},
        'signal_stats': {
            'total_signals': 0,
            'long_signals': 0,
            'short_signals': 0
        }
    }
    
    # 캔들별 분석
    regime_counter = Counter()
    mode_counter = Counter()
    
    trend_scores = []
    range_scores = []
    
    for i in range(len(df)):
        # 최소 데이터 확보
        if i < 200:
            continue
        
        df_slice = df.iloc[:i+1].copy()
        last = df_slice.iloc[-1]
        price = float(last['close'])
        atr = float(last.get('atr_14', price * 0.002))
        atr_pct = atr / price
        
        # Regime Detection
        regime_info = detect_regime(df_slice, config)
        regime = regime_info['regime']
        trend = regime_info['trend']
        
        regime_counter[regime] += 1
        
        # Mode 판정
        mode = "trend" if trend in ["BULL", "BEAR"] else "range"
        mode_counter[mode] += 1
        
        # 필터 적용
        filter_result = _apply_filters(df_slice, config, atr, atr_pct, regime_info)
        
        if filter_result['passed']:
            results['filter_stats']['total_pass'] += 1
        else:
            results['filter_stats']['total_fail'] += 1
            # 실패 이유 추출
            reason = filter_result['reason'].split(':')[0] if ':' in filter_result['reason'] else filter_result['reason']
            results['filter_stats']['fail_reasons'][reason] += 1
            continue  # 필터 실패 시 Score 계산 안 함
        
        # Score 계산
        rsi = float(last.get('rsi_14', 50))
        adx = float(last.get('adx_14', regime_info.get('adx', 25)))
        di_plus = float(last.get('di_plus_14', 25))
        di_minus = float(last.get('di_minus_14', 25))
        ema_5 = float(last.get('ema_5', price))
        ema_20 = float(last.get('ema_20', price))
        
        # BB 계산
        bb_mult_main, bb_mult_strong = get_bb_threshold(df_slice, config, regime)
        bb_main = calculate_bb_bands(df_slice, bb_mult_main, bb_period=20)
        
        # RSI Threshold
        if mode == "trend":
            rsi_long_threshold, rsi_short_threshold = get_rsi_threshold(df_slice, config, regime)
        else:
            rsi_long_threshold = config.get('range_rsi_threshold', 40)
            rsi_short_threshold = 100 - rsi_long_threshold
        
        if mode == "trend":
            score, conditions, side = _calculate_trend_score(
                price, rsi, bb_main, ema_5, ema_20, adx, di_plus, di_minus,
                rsi_long_threshold, rsi_short_threshold, regime_info, config
            )
            trend_scores.append(score)
            
            trend_min_score = config.get('trend_min_score', 3)
            if score >= trend_min_score and side is not None:
                results['signal_stats']['total_signals'] += 1
                if side == "LONG":
                    results['signal_stats']['long_signals'] += 1
                else:
                    results['signal_stats']['short_signals'] += 1
        
        else:  # range
            score, conditions, side = _calculate_range_score(
                price, rsi, bb_main, adx, di_plus, di_minus,
                rsi_long_threshold, rsi_short_threshold, regime_info, config
            )
            range_scores.append(score)
            
            range_min_score = config.get('range_min_score', 2)
            if score >= range_min_score and side is not None:
                results['signal_stats']['total_signals'] += 1
                if side == "LONG":
                    results['signal_stats']['long_signals'] += 1
                else:
                    results['signal_stats']['short_signals'] += 1
    
    # Regime 분포
    total_regimes = sum(regime_counter.values())
    results['regime_distribution'] = {
        regime: {
            'count': count,
            'percentage': round((count / total_regimes) * 100, 2)
        }
        for regime, count in regime_counter.most_common()
    }
    
    results['mode_distribution'] = {
        mode: {
            'count': count,
            'percentage': round((count / total_regimes) * 100, 2)
        }
        for mode, count in mode_counter.most_common()
    }
    
    # Trend Score 분포
    if trend_scores:
        results['trend_score_distribution'] = {
            'total': len(trend_scores),
            'score_gte_1': sum(1 for s in trend_scores if s >= 1),
            'score_gte_2': sum(1 for s in trend_scores if s >= 2),
            'score_gte_3': sum(1 for s in trend_scores if s >= 3),
            'score_gte_4': sum(1 for s in trend_scores if s >= 4),
            'mean': round(np.mean(trend_scores), 2),
            'std': round(np.std(trend_scores), 2),
            'max': max(trend_scores)
        }
        
        for threshold in [1, 2, 3, 4]:
            count = results['trend_score_distribution'][f'score_gte_{threshold}']
            pct = (count / len(trend_scores)) * 100
            results['trend_score_distribution'][f'score_gte_{threshold}_pct'] = round(pct, 2)
    
    # Range Score 분포
    if range_scores:
        results['range_score_distribution'] = {
            'total': len(range_scores),
            'score_gte_1': sum(1 for s in range_scores if s >= 1),
            'score_gte_2': sum(1 for s in range_scores if s >= 2),
            'score_gte_3': sum(1 for s in range_scores if s >= 3),
            'mean': round(np.mean(range_scores), 2),
            'std': round(np.std(range_scores), 2),
            'max': max(range_scores)
        }
        
        for threshold in [1, 2, 3]:
            count = results['range_score_distribution'][f'score_gte_{threshold}']
            pct = (count / len(range_scores)) * 100
            results['range_score_distribution'][f'score_gte_{threshold}_pct'] = round(pct, 2)
    
    # 필터 통과율
    total_analyzed = results['filter_stats']['total_pass'] + results['filter_stats']['total_fail']
    results['filter_stats']['pass_rate'] = round(
        (results['filter_stats']['total_pass'] / total_analyzed) * 100, 2
    ) if total_analyzed > 0 else 0
    
    # 신호 비율
    results['signal_stats']['signal_rate'] = round(
        (results['signal_stats']['total_signals'] / total_analyzed) * 100, 2
    ) if total_analyzed > 0 else 0
    
    return results


def print_analysis(results: dict):
    """
    분석 결과 출력
    
    Args:
        results: analyze_score_distribution 결과
    """
    logger.info("\n" + "=" * 80)
    logger.info("📊 분석 결과 요약")
    logger.info("=" * 80)
    
    # 전체 캔들
    logger.info(f"\n📋 전체 캔들 수: {results['total_candles']:,}")
    
    # Regime 분포
    logger.info(f"\n🎯 Regime 분포:")
    for regime, data in results['regime_distribution'].items():
        logger.info(f"  - {regime:20s}: {data['count']:5,}개 ({data['percentage']:5.2f}%)")
    
    # Mode 분포
    logger.info(f"\n🎯 Mode 분포:")
    for mode, data in results['mode_distribution'].items():
        logger.info(f"  - {mode:20s}: {data['count']:5,}개 ({data['percentage']:5.2f}%)")
    
    # 필터 통과율
    logger.info(f"\n🔎 필터 통과율:")
    logger.info(f"  - Total PASS: {results['filter_stats']['total_pass']:,}개 ({results['filter_stats']['pass_rate']:.2f}%)")
    logger.info(f"  - Total FAIL: {results['filter_stats']['total_fail']:,}개")
    
    if results['filter_stats']['fail_reasons']:
        logger.info(f"\n  실패 이유 Top 5:")
        for reason, count in results['filter_stats']['fail_reasons'].most_common(5):
            pct = (count / results['filter_stats']['total_fail']) * 100
            logger.info(f"    - {reason:30s}: {count:5,}건 ({pct:5.2f}%)")
    
    # Trend Score 분포
    if results['trend_score_distribution']:
        logger.info(f"\n📈 Trend Mode Score 분포:")
        trend_dist = results['trend_score_distribution']
        logger.info(f"  - Total: {trend_dist['total']:,}개")
        logger.info(f"  - Mean: {trend_dist['mean']:.2f} | Std: {trend_dist['std']:.2f} | Max: {trend_dist['max']}")
        logger.info(f"  - Score ≥ 1: {trend_dist['score_gte_1']:,}개 ({trend_dist['score_gte_1_pct']:.2f}%)")
        logger.info(f"  - Score ≥ 2: {trend_dist['score_gte_2']:,}개 ({trend_dist['score_gte_2_pct']:.2f}%)")
        logger.info(f"  - Score ≥ 3 (Threshold): {trend_dist['score_gte_3']:,}개 ({trend_dist['score_gte_3_pct']:.2f}%)")
        logger.info(f"  - Score ≥ 4: {trend_dist['score_gte_4']:,}개 ({trend_dist['score_gte_4_pct']:.2f}%)")
    
    # Range Score 분포
    if results['range_score_distribution']:
        logger.info(f"\n📉 Range Mode Score 분포:")
        range_dist = results['range_score_distribution']
        logger.info(f"  - Total: {range_dist['total']:,}개")
        logger.info(f"  - Mean: {range_dist['mean']:.2f} | Std: {range_dist['std']:.2f} | Max: {range_dist['max']}")
        logger.info(f"  - Score ≥ 1: {range_dist['score_gte_1']:,}개 ({range_dist['score_gte_1_pct']:.2f}%)")
        logger.info(f"  - Score ≥ 2 (Threshold): {range_dist['score_gte_2']:,}개 ({range_dist['score_gte_2_pct']:.2f}%)")
        logger.info(f"  - Score ≥ 3: {range_dist['score_gte_3']:,}개 ({range_dist['score_gte_3_pct']:.2f}%)")
    
    # 신호 통계
    logger.info(f"\n🎯 신호 생성 통계:")
    logger.info(f"  - Total Signals: {results['signal_stats']['total_signals']:,}개 ({results['signal_stats']['signal_rate']:.2f}%)")
    logger.info(f"  - LONG: {results['signal_stats']['long_signals']:,}개")
    logger.info(f"  - SHORT: {results['signal_stats']['short_signals']:,}개")


def main():
    """
    메인 실행 함수
    """
    logger.info("=" * 80)
    logger.info("🚀 PHASE29-3.3: V4 Score Distribution Analysis 시작")
    logger.info("=" * 80)
    
    # Config 로딩
    import yaml
    config_path = project_root / "configs" / "backtest" / "phase29_3_1_btc5m_baseline_v4_week.yml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        full_config = yaml.safe_load(f)
    
    strategy_config = full_config.get('strategies', {}).get('btc5m_baseline_v4', {})
    strategy_config['indicators'] = full_config.get('indicators', {})
    
    # 백테스트 설정
    data_file = project_root / "data" / "BTCUSDT_5m_2024-01-01_2024-12-31.csv"
    start_date = "2024-11-24 00:00:00"
    end_date = "2024-12-01 00:00:00"
    
    try:
        # 1. 데이터 로딩 및 지표 추가
        df = load_and_prepare_data(str(data_file), start_date, end_date, strategy_config)
        
        # 2. Score & 필터 분포 분석
        results = analyze_score_distribution(df, strategy_config)
        
        # 3. 결과 출력
        print_analysis(results)
        
        # 4. JSON 저장
        output_dir = project_root / "reports" / "phase29_3_3"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "v4_score_distribution_week.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ 결과 저장: {output_file}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ PHASE29-3.3: V4 Score Distribution Analysis 완료")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
