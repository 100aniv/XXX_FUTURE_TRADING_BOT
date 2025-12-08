#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-2A: V3 전략 조건 통과율 진단 스크립트
===============================================
btc5m_baseline_v3 전략의 조건별 통과율을 분석하여,
"어디서 신호가 차단되는지" 정량적으로 파악한다.

목적:
- 1일/1주 백테스트 기간 동안 각 조건/필터별 통과율 측정
- Trend/Range 모드별 병목 지점 식별
- 완화 후보 조건 제안

실행 방법:
    python scripts/analysis/phase29_2a_v3_condition_diagnostics.py
"""
import sys
import os
from pathlib import Path
import json
import pandas as pd
import yaml
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.analysis.utils.v3_condition_stats import (
    analyze_v3_conditions,
    format_condition_stats_report
)
import numpy as np


def load_config(config_path: str) -> dict:
    """Config YAML 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """EMA 계산"""
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ATR 계산"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_adx_components(df: pd.DataFrame, period: int = 14):
    """ADX, DI+, DI- 계산"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # +DM, -DM
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    
    # ATR
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # DI+, DI-
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # DX, ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def add_indicators(df: pd.DataFrame, indicators_cfg: dict) -> pd.DataFrame:
    """
    DataFrame에 필요한 지표를 추가한다.
    """
    # EMA
    ema_cfg = indicators_cfg.get('ema', {})
    df['ema_5'] = calculate_ema(df, ema_cfg.get('fast', 5))
    df['ema_20'] = calculate_ema(df, ema_cfg.get('mid', 20))
    df['ema_200'] = calculate_ema(df, ema_cfg.get('slow', 200))
    
    # RSI
    rsi_cfg = indicators_cfg.get('rsi', {})
    df['rsi'] = calculate_rsi(df, rsi_cfg.get('length', 14))
    
    # Bollinger Bands
    bb_cfg = indicators_cfg.get('bollinger', {})
    bb_period = bb_cfg.get('length', 20)
    bb_std = bb_cfg.get('std', 2.0)
    sma = df['close'].rolling(window=bb_period).mean()
    std = df['close'].rolling(window=bb_period).std()
    df['bb_upper'] = sma + (std * bb_std)
    df['bb_mid'] = sma
    df['bb_lower'] = sma - (std * bb_std)
    
    # ATR
    atr_cfg = indicators_cfg.get('atr', {})
    df['atr_14'] = calculate_atr(df, atr_cfg.get('length', 14))
    
    # ADX + DI
    adx_cfg = indicators_cfg.get('adx', {})
    adx_period = adx_cfg.get('period', 14)
    adx, di_plus, di_minus = calculate_adx_components(df, adx_period)
    df['adx'] = adx
    df['di_plus'] = di_plus
    df['di_minus'] = di_minus
    
    return df


def prepare_data(config: dict) -> pd.DataFrame:
    """
    백테스트 데이터를 로드하고 지표를 추가한다.
    
    Args:
        config: 백테스트 설정
    
    Returns:
        pd.DataFrame: OHLCV + 지표
    """
    backtest_cfg = config['backtest']
    data_path = Path(project_root) / backtest_cfg['data_dir'] / backtest_cfg['data_file']
    
    # 데이터 로드 (pandas 직접 사용)
    df = pd.read_csv(data_path)
    
    # 컬럼명 정규화 (소문자)
    df.columns = [c.lower() for c in df.columns]
    
    # 날짜 필터링
    start_date = pd.to_datetime(backtest_cfg['start_date'])
    end_date = pd.to_datetime(backtest_cfg['end_date'])
    
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df[(df['datetime'] >= start_date) & (df['datetime'] < end_date)].copy()
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] < end_date)].copy()
    
    df = df.reset_index(drop=True)
    
    # 지표 추가
    indicators_cfg = config.get('indicators', {})
    df = add_indicators(df, indicators_cfg)
    
    return df


def analyze_period(period_name: str, config_path: str, output_dir: Path):
    """
    특정 기간의 조건 통과율을 분석한다.
    
    Args:
        period_name: 기간 이름 (예: "1day", "1week")
        config_path: Config 파일 경로
        output_dir: 출력 디렉토리
    """
    print(f"\n{'='*80}")
    print(f"📊 PHASE29-2A: {period_name.upper()} 조건 통과율 분석 시작")
    print(f"{'='*80}\n")
    
    # Config 로드
    config = load_config(config_path)
    strategy_config = config['strategies']['btc5m_baseline_v3']
    
    # 데이터 준비
    print("📂 데이터 로드 및 지표 계산 중...")
    df = prepare_data(config)
    print(f"✅ 데이터 준비 완료: {len(df):,} 캔들")
    
    # 조건 통과율 분석
    print("\n🔍 조건별 통과율 분석 중...")
    stats = analyze_v3_conditions(df, strategy_config)
    
    if 'error' in stats:
        print(f"❌ 분석 실패: {stats['error']}")
        return
    
    # 결과 출력
    report_text = format_condition_stats_report(stats)
    print("\n" + report_text)
    
    # JSON 저장
    output_json = output_dir / f"phase29_2a_v3_condition_stats_{period_name}.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON 저장: {output_json}")
    
    # Markdown 저장
    output_md = output_dir / f"phase29_2a_v3_condition_stats_{period_name}.md"
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(f"# V3 조건 통과율 분석 - {period_name.upper()}\n\n")
        f.write(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("```\n")
        f.write(report_text)
        f.write("\n```\n\n")
        
        # 상세 통계 표
        s = stats['summary']
        f.write("## 📊 상세 통계\n\n")
        
        # Global Filters
        f.write("### Global Filters\n\n")
        f.write("| Filter | Pass Count | Pass Rate |\n")
        f.write("|--------|------------|----------|\n")
        f.write(f"| ATR Filter | {stats['filters']['atr_filter_pass']:,} | {s['atr_filter_pass_pct']:.2f}% |\n")
        f.write(f"| Volume Filter | {stats['filters']['volume_filter_pass']:,} | {s['volume_filter_pass_pct']:.2f}% |\n")
        f.write(f"| Time Filter | {stats['filters']['time_filter_pass']:,} | {s['time_filter_pass_pct']:.2f}% |\n")
        f.write(f"| **All Filters** | **{stats['filters']['all_filters_pass']:,}** | **{s['all_filters_pass_pct']:.2f}%** |\n\n")
        
        # Regime Distribution
        f.write("### Regime 분포\n\n")
        f.write("| Regime | Count | Percentage |\n")
        f.write("|--------|-------|------------|\n")
        f.write(f"| Trend Bull | {stats['regime']['trend_bull']:,} | {s['bull_pct']:.2f}% |\n")
        f.write(f"| Trend Bear | {stats['regime']['trend_bear']:,} | {s['bear_pct']:.2f}% |\n")
        f.write(f"| Range | {stats['regime']['range_sideways']:,} | {s['range_mode_pct']:.2f}% |\n\n")
        
        # Trend Mode Conditions
        f.write("### Trend Mode 조건별 통과율\n\n")
        f.write("| 조건 | Count | Rate (전체 대비) |\n")
        f.write("|------|-------|------------------|\n")
        trend_total = stats['regime']['trend_total']
        if trend_total > 0:
            f.write(f"| ADX ≥ 25 | {stats['trend_mode']['adx_above_threshold']:,} | {stats['trend_mode']['adx_above_threshold']/trend_total*100:.2f}% |\n")
            f.write(f"| Bull RSI Pullback | {stats['trend_mode']['bull_rsi_pullback']:,} | {stats['trend_mode']['bull_rsi_pullback']/trend_total*100:.2f}% |\n")
            f.write(f"| Bull BB Lower | {stats['trend_mode']['bull_bb_lower']:,} | {stats['trend_mode']['bull_bb_lower']/trend_total*100:.2f}% |\n")
            f.write(f"| Bull EMA Pullback | {stats['trend_mode']['bull_ema_pullback']:,} | {stats['trend_mode']['bull_ema_pullback']/trend_total*100:.2f}% |\n")
            f.write(f"| Bull DI Confirm | {stats['trend_mode']['bull_di_confirm']:,} | {stats['trend_mode']['bull_di_confirm']/trend_total*100:.2f}% |\n")
            f.write(f"| **Bull 3+ Conditions** | **{stats['trend_mode']['bull_3_conditions']:,}** | **{s['trend_bull_signal_rate']:.3f}%** |\n\n")
        
        # Range Mode Conditions
        f.write("### Range Mode 조건별 통과율\n\n")
        f.write("| 조건 | Count | Rate (전체 대비) |\n")
        f.write("|------|-------|------------------|\n")
        range_total = stats['regime']['range_total']
        if range_total > 0:
            f.write(f"| ADX < 20 | {stats['range_mode']['adx_below_threshold']:,} | {stats['range_mode']['adx_below_threshold']/range_total*100:.2f}% |\n")
            f.write(f"| DI Diff ≤ 5 | {stats['range_mode']['di_diff_small']:,} | {stats['range_mode']['di_diff_small']/range_total*100:.2f}% |\n")
            f.write(f"| Long RSI < 30 | {stats['range_mode']['long_rsi_oversold']:,} | {stats['range_mode']['long_rsi_oversold']/range_total*100:.2f}% |\n")
            f.write(f"| Long BB Lower | {stats['range_mode']['long_bb_lower']:,} | {stats['range_mode']['long_bb_lower']/range_total*100:.2f}% |\n")
            f.write(f"| **Long All Conditions** | **{stats['range_mode']['long_all_conditions']:,}** | **{s['range_long_signal_rate']:.3f}%** |\n\n")
        
        # Final Signals
        f.write("### 최종 신호 생성\n\n")
        f.write("| 신호 | Count | Rate |\n")
        f.write("|------|-------|------|\n")
        f.write(f"| LONG | {stats['final_signals']['long_signal']:,} | {s['long_signal_pct']:.3f}% |\n")
        f.write(f"| SHORT | {stats['final_signals']['short_signal']:,} | {s['short_signal_pct']:.3f}% |\n")
        f.write(f"| **Total** | **{stats['final_signals']['long_signal'] + stats['final_signals']['short_signal']:,}** | **{s['total_signal_pct']:.3f}%** |\n\n")
    
    print(f"✅ Markdown 저장: {output_md}")
    
    return stats


def generate_comparison_report(stats_day: dict, stats_week: dict, output_dir: Path):
    """
    1일과 1주 분석 결과를 비교하는 리포트를 생성한다.
    """
    output_path = output_dir / "phase29_2a_v3_condition_comparison.md"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# PHASE29-2A: V3 조건 통과율 비교 분석\n\n")
        f.write(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 📊 핵심 발견 (Key Findings)\n\n")
        
        s_day = stats_day['summary']
        s_week = stats_week['summary']
        
        # 신호 생성율 비교
        f.write("### 1. 최종 신호 생성율\n\n")
        f.write("| 항목 | 1일 | 1주 |\n")
        f.write("|------|-----|-----|\n")
        f.write(f"| 총 신호율 | {s_day['total_signal_pct']:.3f}% | {s_week['total_signal_pct']:.3f}% |\n")
        f.write(f"| LONG 신호 | {s_day['long_signal_pct']:.3f}% | {s_week['long_signal_pct']:.3f}% |\n")
        f.write(f"| SHORT 신호 | {s_day['short_signal_pct']:.3f}% | {s_week['short_signal_pct']:.3f}% |\n\n")
        
        # 병목 지점 비교
        f.write("### 2. 병목 지점 (Bottlenecks)\n\n")
        f.write("| 항목 | 1일 | 1주 | 비고 |\n")
        f.write("|------|-----|-----|------|\n")
        f.write(f"| Global Filters 통과 | {s_day['all_filters_pass_pct']:.1f}% | {s_week['all_filters_pass_pct']:.1f}% | - |\n")
        f.write(f"| Trend Bull 신호율 | {s_day['trend_bull_signal_rate']:.3f}% | {s_week['trend_bull_signal_rate']:.3f}% | ⚠️ 극단적 병목 |\n")
        f.write(f"| Trend Bear 신호율 | {s_day['trend_bear_signal_rate']:.3f}% | {s_week['trend_bear_signal_rate']:.3f}% | ⚠️ 극단적 병목 |\n")
        f.write(f"| Range Long 신호율 | {s_day['range_long_signal_rate']:.3f}% | {s_week['range_long_signal_rate']:.3f}% | ⚠️ 극단적 병목 |\n\n")
        
        # Regime 분포
        f.write("### 3. Regime 분포\n\n")
        f.write("| Regime | 1일 | 1주 |\n")
        f.write("|--------|-----|-----|\n")
        f.write(f"| Trend Mode | {s_day['trend_mode_pct']:.1f}% | {s_week['trend_mode_pct']:.1f}% |\n")
        f.write(f"| Range Mode | {s_day['range_mode_pct']:.1f}% | {s_week['range_mode_pct']:.1f}% |\n\n")
        
        # 주요 병목 조건 식별
        f.write("## 🚨 주요 병목 조건 Top 3\n\n")
        
        # Trend Mode에서 가장 낮은 통과율 조건
        trend_bull = stats_week['regime']['trend_bull']
        if trend_bull > 0:
            ema_pullback_rate = stats_week['trend_mode']['bull_ema_pullback'] / trend_bull * 100
            rsi_pullback_rate = stats_week['trend_mode']['bull_rsi_pullback'] / trend_bull * 100
            bb_lower_rate = stats_week['trend_mode']['bull_bb_lower'] / trend_bull * 100
            
            f.write("### Trend Bull 모드\n\n")
            f.write(f"1. **EMA Pullback 조건**: {ema_pullback_rate:.2f}% (Price가 EMA 5와 EMA 20 사이)\n")
            f.write(f"2. **RSI Pullback 조건**: {rsi_pullback_rate:.2f}% (RSI < Dynamic Threshold)\n")
            f.write(f"3. **BB Lower 조건**: {bb_lower_rate:.2f}% (Price < BB Lower)\n\n")
        
        # Range Mode에서 가장 낮은 통과율 조건
        range_total = stats_week['regime']['range_total']
        if range_total > 0:
            rsi_oversold_rate = stats_week['range_mode']['long_rsi_oversold'] / range_total * 100
            bb_lower_rate = stats_week['range_mode']['long_bb_lower'] / range_total * 100
            
            f.write("### Range 모드\n\n")
            f.write(f"1. **RSI < 30 조건**: {rsi_oversold_rate:.2f}% (극단적 과매도)\n")
            f.write(f"2. **BB Lower 조건**: {bb_lower_rate:.2f}% (밴드 하단)\n")
            f.write(f"3. **AND 결합 효과**: 3개 조건 동시 충족률 {s_week['range_long_signal_rate']:.3f}%\n\n")
        
        # 완화 권장사항
        f.write("## 💡 조건 완화 권장사항\n\n")
        f.write("### 우선순위 1: Trend Mode EMA Pullback 조건\n")
        f.write("- **현재**: `ema_20 < price < ema_5` (매우 좁은 구간)\n")
        f.write("- **제안**: `price < ema_5` 또는 `price < ema_20 * 1.005` (5% 여유)\n")
        f.write("- **기대 효과**: Trend 신호 2~3배 증가 예상\n\n")
        
        f.write("### 우선순위 2: AND → OR 조건 완화\n")
        f.write("- **현재**: 최소 3개 조건 충족 (4개 중 3개)\n")
        f.write("- **제안**: 최소 2개 조건 충족 또는 핵심 조건 2개 필수\n")
        f.write("- **기대 효과**: 신호율 5~10배 증가 예상\n\n")
        
        f.write("### 우선순위 3: Range Mode RSI Threshold 완화\n")
        f.write("- **현재**: RSI < 30 (극단적 과매도)\n")
        f.write("- **제안**: RSI < 35 또는 Dynamic RSI < 40\n")
        f.write("- **기대 효과**: Range 신호 2~3배 증가 예상\n\n")
        
    print(f"\n✅ 비교 리포트 저장: {output_path}")


def main():
    """메인 실행 함수"""
    output_dir = Path(project_root) / "reports" / "analysis" / "PHASE29"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1일 분석
    day_config = str(Path(project_root) / "configs" / "backtest" / "phase29_2a_btc5m_baseline_v3_debug_day.yml")
    stats_day = analyze_period("1day", day_config, output_dir)
    
    # 1주 분석
    week_config = str(Path(project_root) / "configs" / "backtest" / "phase29_2a_btc5m_baseline_v3_debug_week.yml")
    stats_week = analyze_period("1week", week_config, output_dir)
    
    # 비교 리포트 생성
    if stats_day and stats_week:
        generate_comparison_report(stats_day, stats_week, output_dir)
    
    print(f"\n{'='*80}")
    print("✅ PHASE29-2A 조건 통과율 진단 완료")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
