#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V3 전략 조건 통과율 집계 유틸리티 (PHASE29-2A)
================================================
btc5m_baseline_v3 전략의 각 조건/필터별 통과율을 측정하여,
"어디서 병목이 발생하는지" 정량적으로 진단한다.

목적:
- Global Filters (ATR, Volume, Time) 통과율
- Trend Mode 조건별 통과율 (RSI, BB, EMA, DI)
- Range Mode 조건별 통과율 (RSI, BB, ADX, DI)
- Regime 분포 (Trend vs Range)
- 최종 신호 생성율

사용법:
    from scripts.analysis.utils.v3_condition_stats import analyze_v3_conditions
    
    stats = analyze_v3_conditions(df, config)
    print(stats['summary'])
"""
import sys
from pathlib import Path
# Add project root to path when running as standalone script
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))

from typing import Dict, Any, List
import pandas as pd
import numpy as np
import logging
from datetime import time

from strategies.utils.regime_detector import detect_regime
from strategies.utils.dynamic_threshold import (
    get_rsi_threshold,
    get_bb_threshold,
    calculate_bb_bands
)

logger = logging.getLogger(__name__)


def analyze_v3_conditions(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    V3 전략의 조건별 통과율을 분석한다.
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정
    
    Returns:
        dict: 조건별 통과율 통계
            {
                'total_bars': int,
                'filters': {...},  # Global Filters 통과율
                'regime': {...},   # Regime 분포
                'trend_mode': {...},  # Trend 모드 조건 통과율
                'range_mode': {...},  # Range 모드 조건 통과율
                'summary': {...}   # 요약 통계
            }
    """
    min_bars = config.get('min_bars_for_signal', 100)
    if len(df) < min_bars:
        return {
            'error': f'데이터 부족: {len(df)} < {min_bars}',
            'total_bars': len(df)
        }
    
    # 집계 카운터 초기화
    stats = {
        'total_bars': len(df),
        'filters': {
            'atr_filter_pass': 0,
            'volume_filter_pass': 0,
            'time_filter_pass': 0,
            'all_filters_pass': 0
        },
        'regime': {
            'trend_bull': 0,
            'trend_bear': 0,
            'range_sideways': 0,
            'trend_total': 0,
            'range_total': 0
        },
        'trend_mode': {
            'adx_above_threshold': 0,
            'bull_rsi_pullback': 0,
            'bull_bb_lower': 0,
            'bull_ema_pullback': 0,
            'bull_di_confirm': 0,
            'bull_3_conditions': 0,
            'bear_rsi_pullback': 0,
            'bear_bb_upper': 0,
            'bear_ema_pullback': 0,
            'bear_di_confirm': 0,
            'bear_3_conditions': 0
        },
        'range_mode': {
            'adx_below_threshold': 0,
            'di_diff_small': 0,
            'long_rsi_oversold': 0,
            'long_bb_lower': 0,
            'long_adx_range': 0,
            'long_all_conditions': 0,
            'short_rsi_overbought': 0,
            'short_bb_upper': 0,
            'short_adx_range': 0,
            'short_all_conditions': 0
        },
        'final_signals': {
            'long_signal': 0,
            'short_signal': 0,
            'no_signal': 0
        }
    }
    
    # Config 파라미터
    filters_config = config.get('v3_filters', {})
    min_atr_pct = filters_config.get('min_atr_pct', 0.002)
    min_volume_ratio = filters_config.get('min_volume_ratio', 0.8)
    enable_time_filter = filters_config.get('enable_time_filter', False)
    
    adx_trend_threshold = config.get('adx_trend_threshold', 25)
    adx_range_threshold = config.get('adx_range_threshold', 20)
    allow_short = config.get('filters', {}).get('allow_short', True)
    
    # 각 캔들에 대해 조건 평가
    for i in range(min_bars, len(df)):
        df_slice = df.iloc[:i+1].copy()
        last = df_slice.iloc[-1]
        
        price = float(last['close'])
        atr = float(last.get('atr_14', price * 0.002))
        atr_pct = atr / price
        
        # === STEP 1: Regime Detection ===
        regime_info = detect_regime(df_slice, config)
        regime = regime_info['regime']
        trend = regime_info['trend']
        
        mode = "trend" if trend in ["BULL", "BEAR"] else "range"
        
        # Regime 통계
        if mode == "trend":
            stats['regime']['trend_total'] += 1
            if trend == "BULL":
                stats['regime']['trend_bull'] += 1
            elif trend == "BEAR":
                stats['regime']['trend_bear'] += 1
        else:
            stats['regime']['range_total'] += 1
            stats['regime']['range_sideways'] += 1
        
        # === STEP 2: Global Filters ===
        atr_pass = atr_pct >= min_atr_pct
        if atr_pass:
            stats['filters']['atr_filter_pass'] += 1
        
        volume_pass = True
        if filters_config.get('enable_volume_filter', True) and len(df_slice) >= 20:
            volume = float(last.get('volume', 0))
            volume_ma20 = df_slice['volume'].rolling(20).mean().iloc[-1]
            volume_pass = volume >= volume_ma20 * min_volume_ratio
        if volume_pass:
            stats['filters']['volume_filter_pass'] += 1
        
        time_pass = True
        if enable_time_filter:
            if 'timestamp' in df_slice.columns or 'datetime' in df_slice.columns:
                ts_col = 'timestamp' if 'timestamp' in df_slice.columns else 'datetime'
                current_time = pd.to_datetime(last[ts_col]).time()
                blackout_start = time(0, 0)
                blackout_end = time(2, 0)
                time_pass = not (blackout_start <= current_time <= blackout_end)
        if time_pass:
            stats['filters']['time_filter_pass'] += 1
        
        all_filters_pass = atr_pass and volume_pass and time_pass
        if all_filters_pass:
            stats['filters']['all_filters_pass'] += 1
        
        # === STEP 3: Dynamic Threshold & Indicators ===
        rsi_long_threshold, rsi_short_threshold = get_rsi_threshold(df_slice, config, regime)
        bb_mult_main, bb_mult_strong = get_bb_threshold(df_slice, config, regime)
        
        rsi = float(last.get('rsi', 50))
        bb_main = calculate_bb_bands(df_slice, bb_mult_main, bb_period=20)
        
        ema_5 = float(last.get('ema_5', price))
        ema_20 = float(last.get('ema_20', price))
        
        adx = float(regime_info['adx']) if regime_info['adx'] is not None else 20.0
        di_plus = float(regime_info['di_plus']) if regime_info['di_plus'] is not None else 15.0
        di_minus = float(regime_info['di_minus']) if regime_info['di_minus'] is not None else 15.0
        
        # === STEP 4: Trend Mode 조건 평가 ===
        if mode == "trend":
            adx_ok = adx >= adx_trend_threshold
            if adx_ok:
                stats['trend_mode']['adx_above_threshold'] += 1
            
            if trend == "BULL":
                # LONG 조건
                cond_rsi = rsi < rsi_long_threshold
                cond_bb = price < bb_main['lower']
                cond_ema = ema_20 < price < ema_5
                cond_di = di_plus > di_minus
                
                if cond_rsi:
                    stats['trend_mode']['bull_rsi_pullback'] += 1
                if cond_bb:
                    stats['trend_mode']['bull_bb_lower'] += 1
                if cond_ema:
                    stats['trend_mode']['bull_ema_pullback'] += 1
                if cond_di:
                    stats['trend_mode']['bull_di_confirm'] += 1
                
                conditions_met = sum([cond_rsi, cond_bb, cond_ema, cond_di])
                if conditions_met >= 3 and adx_ok and all_filters_pass:
                    stats['trend_mode']['bull_3_conditions'] += 1
                    stats['final_signals']['long_signal'] += 1
                    continue
            
            elif trend == "BEAR" and allow_short:
                # SHORT 조건
                cond_rsi = rsi > rsi_short_threshold
                cond_bb = price > bb_main['upper']
                cond_ema = ema_5 < price < ema_20
                cond_di = di_minus > di_plus
                
                if cond_rsi:
                    stats['trend_mode']['bear_rsi_pullback'] += 1
                if cond_bb:
                    stats['trend_mode']['bear_bb_upper'] += 1
                if cond_ema:
                    stats['trend_mode']['bear_ema_pullback'] += 1
                if cond_di:
                    stats['trend_mode']['bear_di_confirm'] += 1
                
                conditions_met = sum([cond_rsi, cond_bb, cond_ema, cond_di])
                if conditions_met >= 3 and adx_ok and all_filters_pass:
                    stats['trend_mode']['bear_3_conditions'] += 1
                    stats['final_signals']['short_signal'] += 1
                    continue
        
        # === STEP 5: Range Mode 조건 평가 ===
        elif mode == "range":
            adx_ok = adx < adx_range_threshold
            if adx_ok:
                stats['range_mode']['adx_below_threshold'] += 1
            
            di_diff = abs(di_plus - di_minus)
            di_ok = di_diff <= 5
            if di_ok:
                stats['range_mode']['di_diff_small'] += 1
            
            # LONG 조건
            cond_rsi_long = rsi < 30
            cond_bb_long = price < bb_main['lower']
            cond_adx = adx < adx_range_threshold
            
            if cond_rsi_long:
                stats['range_mode']['long_rsi_oversold'] += 1
            if cond_bb_long:
                stats['range_mode']['long_bb_lower'] += 1
            if cond_adx:
                stats['range_mode']['long_adx_range'] += 1
            
            if cond_rsi_long and cond_bb_long and cond_adx and all_filters_pass:
                stats['range_mode']['long_all_conditions'] += 1
                stats['final_signals']['long_signal'] += 1
                continue
            
            # SHORT 조건
            if allow_short:
                cond_rsi_short = rsi > 70
                cond_bb_short = price > bb_main['upper']
                
                if cond_rsi_short:
                    stats['range_mode']['short_rsi_overbought'] += 1
                if cond_bb_short:
                    stats['range_mode']['short_bb_upper'] += 1
                if cond_adx:
                    stats['range_mode']['short_adx_range'] += 1
                
                if cond_rsi_short and cond_bb_short and cond_adx and all_filters_pass:
                    stats['range_mode']['short_all_conditions'] += 1
                    stats['final_signals']['short_signal'] += 1
                    continue
        
        # 신호 없음
        stats['final_signals']['no_signal'] += 1
    
    # === 백분율 계산 ===
    total = stats['total_bars']
    
    stats['summary'] = {
        'total_bars': total,
        'analyzed_bars': total - min_bars,
        
        # Filters
        'atr_filter_pass_pct': stats['filters']['atr_filter_pass'] / (total - min_bars) * 100,
        'volume_filter_pass_pct': stats['filters']['volume_filter_pass'] / (total - min_bars) * 100,
        'time_filter_pass_pct': stats['filters']['time_filter_pass'] / (total - min_bars) * 100,
        'all_filters_pass_pct': stats['filters']['all_filters_pass'] / (total - min_bars) * 100,
        
        # Regime
        'trend_mode_pct': stats['regime']['trend_total'] / (total - min_bars) * 100,
        'range_mode_pct': stats['regime']['range_total'] / (total - min_bars) * 100,
        'bull_pct': stats['regime']['trend_bull'] / (total - min_bars) * 100,
        'bear_pct': stats['regime']['trend_bear'] / (total - min_bars) * 100,
        
        # Final Signals
        'long_signal_pct': stats['final_signals']['long_signal'] / (total - min_bars) * 100,
        'short_signal_pct': stats['final_signals']['short_signal'] / (total - min_bars) * 100,
        'total_signal_pct': (stats['final_signals']['long_signal'] + stats['final_signals']['short_signal']) / (total - min_bars) * 100,
        
        # Trend Mode Bottlenecks
        'trend_adx_pass_rate': stats['trend_mode']['adx_above_threshold'] / stats['regime']['trend_total'] * 100 if stats['regime']['trend_total'] > 0 else 0,
        'trend_bull_signal_rate': stats['trend_mode']['bull_3_conditions'] / stats['regime']['trend_bull'] * 100 if stats['regime']['trend_bull'] > 0 else 0,
        'trend_bear_signal_rate': stats['trend_mode']['bear_3_conditions'] / stats['regime']['trend_bear'] * 100 if stats['regime']['trend_bear'] > 0 else 0,
        
        # Range Mode Bottlenecks
        'range_adx_pass_rate': stats['range_mode']['adx_below_threshold'] / stats['regime']['range_total'] * 100 if stats['regime']['range_total'] > 0 else 0,
        'range_long_signal_rate': stats['range_mode']['long_all_conditions'] / stats['regime']['range_total'] * 100 if stats['regime']['range_total'] > 0 else 0,
        'range_short_signal_rate': stats['range_mode']['short_all_conditions'] / stats['regime']['range_total'] * 100 if stats['regime']['range_total'] > 0 else 0,
    }
    
    return stats


def format_condition_stats_report(stats: Dict[str, Any]) -> str:
    """
    조건 통과율 통계를 읽기 쉬운 텍스트로 포맷팅
    
    Args:
        stats: analyze_v3_conditions() 결과
    
    Returns:
        str: 포맷팅된 리포트
    """
    if 'error' in stats:
        return f"오류: {stats['error']}"
    
    s = stats['summary']
    
    report = []
    report.append("=" * 80)
    report.append("V3 전략 조건 통과율 분석 리포트")
    report.append("=" * 80)
    report.append("")
    
    report.append(f"분석 기간: {s['analyzed_bars']:,} 캔들 (Total: {s['total_bars']:,})")
    report.append("")
    
    # Global Filters
    report.append("### Global Filters")
    report.append(f"  ATR Filter Pass:     {s['atr_filter_pass_pct']:.2f}%")
    report.append(f"  Volume Filter Pass:  {s['volume_filter_pass_pct']:.2f}%")
    report.append(f"  Time Filter Pass:    {s['time_filter_pass_pct']:.2f}%")
    report.append(f"  All Filters Pass:    {s['all_filters_pass_pct']:.2f}% ⬅ **병목 1단계**")
    report.append("")
    
    # Regime Distribution
    report.append("### Regime 분포")
    report.append(f"  Trend Mode:          {s['trend_mode_pct']:.2f}%")
    report.append(f"    - Bull:            {s['bull_pct']:.2f}%")
    report.append(f"    - Bear:            {s['bear_pct']:.2f}%")
    report.append(f"  Range Mode:          {s['range_mode_pct']:.2f}%")
    report.append("")
    
    # Final Signals
    report.append("### 최종 신호 생성율")
    report.append(f"  LONG Signals:        {s['long_signal_pct']:.3f}%")
    report.append(f"  SHORT Signals:       {s['short_signal_pct']:.3f}%")
    report.append(f"  Total Signals:       {s['total_signal_pct']:.3f}% ⬅ **최종 신호율**")
    report.append("")
    
    # Trend Mode Bottlenecks
    report.append("### Trend Mode 병목 분석")
    report.append(f"  ADX ≥ 25 통과율:     {s['trend_adx_pass_rate']:.2f}%")
    report.append(f"  Bull 3-조건 충족:    {s['trend_bull_signal_rate']:.3f}% ⬅ **Trend Bull 병목**")
    report.append(f"  Bear 3-조건 충족:    {s['trend_bear_signal_rate']:.3f}% ⬅ **Trend Bear 병목**")
    report.append("")
    
    # Range Mode Bottlenecks
    report.append("### Range Mode 병목 분석")
    report.append(f"  ADX < 20 통과율:     {s['range_adx_pass_rate']:.2f}%")
    report.append(f"  LONG 조건 충족:      {s['range_long_signal_rate']:.3f}% ⬅ **Range Long 병목**")
    report.append(f"  SHORT 조건 충족:     {s['range_short_signal_rate']:.3f}% ⬅ **Range Short 병목**")
    report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)


if __name__ == "__main__":
    import json
    import argparse
    
    parser = argparse.ArgumentParser(description='V3 전략 조건 통과율 분석')
    parser.add_argument('summary_json', help='백테스트 summary JSON 파일 경로')
    args = parser.parse_args()
    
    # Load summary JSON
    with open(args.summary_json, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # Extract dataframe and config (need to reconstruct from summary)
    # For now, we'll generate a simplified report based on summary data
    # The full analysis would require the detailed candle data
    
    output_base = args.summary_json.replace('_summary.json', '')
    output_txt = f"{output_base}_condition_stats.txt"
    output_json = f"{output_base}_condition_stats.json"
    
    # Create a placeholder message for now
    report_text = f"""
V3 조건 통과율 분석 완료
========================
입력 파일: {args.summary_json}
출력 파일: {output_json}

Note: 상세 조건 통과율 분석을 위해서는 캔들별 지표 데이터가 필요합니다.
Summary JSON만으로는 제한적인 분석만 가능합니다.

Summary 정보:
- Total Trades: {summary.get('total_trades', 0)}
- Win Rate: {summary.get('win_rate', 0):.2f}%
- 분석 기간: {summary.get('config', {}).get('backtest', {}).get('start_date', 'N/A')} ~ {summary.get('config', {}).get('backtest', {}).get('end_date', 'N/A')}
"""
    
    # Write outputs
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump({
            'status': 'completed',
            'input_file': args.summary_json,
            'summary_trades': summary.get('total_trades', 0),
            'win_rate': summary.get('win_rate', 0),
            'note': 'Full condition analysis requires candle-level indicator data'
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 분석 완료")
    print(f"  - Text report: {output_txt}")
    print(f"  - JSON report: {output_json}")
