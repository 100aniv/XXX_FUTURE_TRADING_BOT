#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-2: BTCUSDT 5m 데이터 프로파일링
========================================
최근 N일 BTCUSDT 5m 데이터를 분석하여 지표 분포 통계 수집

목적:
- RSI, BB, ADX, Volume, ATR 등의 실제 시장 분포 파악
- 퍼센타일 기반 threshold 도출
- 전략 재설계의 데이터 기반 (Data-Driven Design)

출력:
- JSON: docs/PHASE27/phase27_2_btc5m_data_profile.json
- 콘솔: 핵심 통계 요약
"""
import sys
from pathlib import Path
import argparse
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from collectors.historical_collector import HistoricalFeed
from indicators import add_indicators
from common.logger import setup_logger

logger = setup_logger(__name__)


def parse_args():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description='BTCUSDT 5m 데이터 프로파일링')
    parser.add_argument('--days', type=int, default=30, help='분석 기간 (일)')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='심볼')
    parser.add_argument('--timeframe', type=str, default='5m', help='타임프레임')
    parser.add_argument('--data-path', type=str, default=None, help='CSV 데이터 경로 (없으면 Binance API 사용)')
    parser.add_argument('--output', type=str, default='docs/PHASE27/phase27_2_btc5m_data_profile.json', help='출력 파일 경로')
    return parser.parse_args()


def load_data(symbol: str, timeframe: str, days: int, data_path: str = None) -> pd.DataFrame:
    """
    히스토리컬 데이터 로드
    
    Args:
        symbol: 심볼 (예: 'BTCUSDT')
        timeframe: 타임프레임 (예: '5m')
        days: 최근 N일
        data_path: CSV 경로 (None이면 default 경로 사용)
    
    Returns:
        DataFrame: OHLCV 데이터
    """
    logger.info(f"데이터 로드 시작: {symbol} {timeframe}, 최근 {days}일")
    
    # Default CSV 경로
    if data_path is None:
        # data/ 디렉토리에서 데이터 찾기
        data_dir = project_root / 'data'
        possible_files = [
            data_dir / f'{symbol}_{timeframe}.csv',
            data_dir / f'{symbol.lower()}_{timeframe}.csv',
            data_dir / 'historical' / f'{symbol}_{timeframe}.csv',
        ]
        
        for path in possible_files:
            if path.exists():
                data_path = str(path)
                logger.info(f"데이터 파일 발견: {data_path}")
                break
        
        if data_path is None:
            raise FileNotFoundError(
                f"데이터 파일을 찾을 수 없습니다. "
                f"다음 경로를 확인하거나 --data-path로 명시하세요:\n"
                f"{[str(p) for p in possible_files]}"
            )
    
    # HistoricalFeed로 데이터 로드
    feed = HistoricalFeed(
        csv_path=data_path,
        symbol=symbol,
        timeframe=timeframe,
        days=days
    )
    
    df = feed.df.copy()
    logger.info(f"데이터 로드 완료: {len(df)} 캔들")
    
    # 시간 범위 출력
    if 'time' in df.columns:
        start_time = df['time'].iloc[0]
        end_time = df['time'].iloc[-1]
        logger.info(f"기간: {start_time} ~ {end_time}")
    
    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    지표 계산
    
    Args:
        df: OHLCV 데이터
    
    Returns:
        DataFrame: 지표가 추가된 데이터
    """
    logger.info("지표 계산 시작...")
    
    # 지표 추가 (add_indicators는 개별 파라미터로 받음)
    df_with_indicators = add_indicators(
        df,
        ema_fast=8,
        ema_mid=21,
        ema_slow=50,
        rsi_len=14,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        bb_len=20,
        bb_std=2.0,
        atr_len=14,
        vol_ma_len=20,
        dc_len=20
    )
    
    # BB 추가 std 계산 (1.0, 1.5, 2.0)
    bb_period = 20
    bb_ma = df_with_indicators['close'].rolling(window=bb_period).mean()
    bb_std_series = df_with_indicators['close'].rolling(window=bb_period).std()
    
    for std_mult in [1.0, 1.5, 2.0]:
        df_with_indicators[f'bb_upper_{std_mult}'] = bb_ma + (bb_std_series * std_mult)
        df_with_indicators[f'bb_lower_{std_mult}'] = bb_ma - (bb_std_series * std_mult)
        df_with_indicators[f'bb_width_{std_mult}'] = (
            (df_with_indicators[f'bb_upper_{std_mult}'] - df_with_indicators[f'bb_lower_{std_mult}']) 
            / df_with_indicators['close']
        )
    
    logger.info(f"지표 계산 완료: {len(df_with_indicators)} 캔들")
    
    # NaN 제거 (초기 rolling window)
    df_clean = df_with_indicators.dropna()
    logger.info(f"NaN 제거 후: {len(df_clean)} 캔들")
    
    return df_clean


def compute_statistics(df: pd.DataFrame) -> dict:
    """
    지표 통계 계산
    
    Args:
        df: 지표가 포함된 DataFrame
    
    Returns:
        dict: 통계 결과
    """
    logger.info("통계 계산 시작...")
    
    stats = {}
    
    # === RSI ===
    if 'rsi' in df.columns:
        rsi_series = df['rsi']
        stats['rsi'] = {
            'min': float(rsi_series.min()),
            'max': float(rsi_series.max()),
            'mean': float(rsi_series.mean()),
            'median': float(rsi_series.median()),
            'std': float(rsi_series.std()),
            'p05': float(rsi_series.quantile(0.05)),
            'p10': float(rsi_series.quantile(0.10)),
            'p25': float(rsi_series.quantile(0.25)),
            'p50': float(rsi_series.quantile(0.50)),
            'p75': float(rsi_series.quantile(0.75)),
            'p90': float(rsi_series.quantile(0.90)),
            'p95': float(rsi_series.quantile(0.95)),
            'below_30_pct': float((rsi_series < 30).sum() / len(rsi_series) * 100),
            'above_70_pct': float((rsi_series > 70).sum() / len(rsi_series) * 100),
        }
    
    # === Bollinger Bands ===
    for std_mult in [1.0, 1.5, 2.0]:
        bb_width_col = f'bb_width_{std_mult}'
        bb_upper_col = f'bb_upper_{std_mult}'
        bb_lower_col = f'bb_lower_{std_mult}'
        
        if bb_width_col in df.columns:
            bb_width_series = df[bb_width_col]
            
            # BB 돌파 빈도 (가격이 upper/lower 밖으로 나간 비율)
            touch_upper = (df['close'] >= df[bb_upper_col]).sum()
            touch_lower = (df['close'] <= df[bb_lower_col]).sum()
            
            stats[f'bb_{std_mult}'] = {
                'width_min': float(bb_width_series.min()),
                'width_max': float(bb_width_series.max()),
                'width_mean': float(bb_width_series.mean()),
                'width_median': float(bb_width_series.median()),
                'width_p25': float(bb_width_series.quantile(0.25)),
                'width_p75': float(bb_width_series.quantile(0.75)),
                'touch_upper_pct': float(touch_upper / len(df) * 100),
                'touch_lower_pct': float(touch_lower / len(df) * 100),
            }
    
    # === ADX ===
    # Note: ADX는 현재 core_indicators에 없음, 향후 추가 필요
    # if 'adx' in df.columns:
    #     adx_series = df['adx']
    #     stats['adx'] = {...}
    
    # === ATR ===
    if 'atr' in df.columns:
        atr_series = df['atr']
        atr_pct_series = atr_series / df['close']  # ATR % of price
        
        stats['atr'] = {
            'min': float(atr_series.min()),
            'max': float(atr_series.max()),
            'mean': float(atr_series.mean()),
            'median': float(atr_series.median()),
            'std': float(atr_series.std()),
            'pct_mean': float(atr_pct_series.mean() * 100),  # % of price
            'pct_median': float(atr_pct_series.median() * 100),
            'pct_p25': float(atr_pct_series.quantile(0.25) * 100),
            'pct_p75': float(atr_pct_series.quantile(0.75) * 100),
        }
    
    # === Volume ===
    if 'volume' in df.columns and 'vol_ma' in df.columns:
        volume_series = df['volume']
        volume_ma_series = df['vol_ma']
        volume_ratio_series = volume_series / volume_ma_series  # Volume / MA
        
        stats['volume'] = {
            'mean': float(volume_series.mean()),
            'median': float(volume_series.median()),
            'ratio_mean': float(volume_ratio_series.mean()),
            'ratio_median': float(volume_ratio_series.median()),
            'ratio_p25': float(volume_ratio_series.quantile(0.25)),
            'ratio_p75': float(volume_ratio_series.quantile(0.75)),
            'ratio_p90': float(volume_ratio_series.quantile(0.90)),
            'spike_1_2x_pct': float((volume_ratio_series > 1.2).sum() / len(volume_ratio_series) * 100),
            'spike_1_5x_pct': float((volume_ratio_series > 1.5).sum() / len(volume_ratio_series) * 100),
            'spike_2_0x_pct': float((volume_ratio_series > 2.0).sum() / len(volume_ratio_series) * 100),
        }
    
    # === Price Movement ===
    if 'close' in df.columns:
        price_series = df['close']
        price_change_pct = price_series.pct_change() * 100  # % change per candle
        
        stats['price'] = {
            'mean': float(price_series.mean()),
            'min': float(price_series.min()),
            'max': float(price_series.max()),
            'change_pct_mean': float(price_change_pct.mean()),
            'change_pct_std': float(price_change_pct.std()),
            'change_pct_p25': float(price_change_pct.quantile(0.25)),
            'change_pct_median': float(price_change_pct.quantile(0.50)),
            'change_pct_p75': float(price_change_pct.quantile(0.75)),
        }
    
    logger.info("통계 계산 완료")
    
    return stats


def print_summary(stats: dict, symbol: str, timeframe: str, days: int):
    """통계 요약 출력"""
    print("\n" + "=" * 80)
    print(f"BTCUSDT 5m 데이터 프로파일링 결과 ({days}일)")
    print("=" * 80)
    
    if 'rsi' in stats:
        rsi = stats['rsi']
        print(f"\n[RSI]")
        print(f"  범위: {rsi['min']:.1f} - {rsi['max']:.1f}")
        print(f"  평균: {rsi['mean']:.1f}, 중앙값: {rsi['median']:.1f}")
        print(f"  퍼센타일: p25={rsi['p25']:.1f}, p50={rsi['p50']:.1f}, p75={rsi['p75']:.1f}")
        print(f"  극단값: <30 발생률 {rsi['below_30_pct']:.2f}%, >70 발생률 {rsi['above_70_pct']:.2f}%")
    
    if 'bb_2.0' in stats:
        print(f"\n[Bollinger Bands]")
        for std_mult in [1.0, 1.5, 2.0]:
            bb = stats.get(f'bb_{std_mult}', {})
            if bb:
                print(f"  BB({std_mult} std):")
                print(f"    Width: 평균 {bb['width_mean']*100:.2f}%, 중앙값 {bb['width_median']*100:.2f}%")
                print(f"    돌파: Upper {bb['touch_upper_pct']:.2f}%, Lower {bb['touch_lower_pct']:.2f}%")
    
    if 'adx' in stats:
        adx = stats['adx']
        print(f"\n[ADX (추세 강도)]")
        print(f"  범위: {adx['min']:.1f} - {adx['max']:.1f}")
        print(f"  평균: {adx['mean']:.1f}, 중앙값: {adx['median']:.1f}")
        print(f"  약한 추세(<20): {adx['below_20_pct']:.1f}%")
        print(f"  중간 추세(<25): {adx['below_25_pct']:.1f}%")
        print(f"  강한 추세(>30): {adx['above_30_pct']:.1f}%")
    
    if 'atr' in stats:
        atr = stats['atr']
        print(f"\n[ATR (변동성)]")
        print(f"  가격 대비: 평균 {atr['pct_mean']:.2f}%, 중앙값 {atr['pct_median']:.2f}%")
        print(f"  퍼센타일: p25={atr['pct_p25']:.2f}%, p75={atr['pct_p75']:.2f}%")
    
    if 'volume' in stats:
        vol = stats['volume']
        print(f"\n[Volume]")
        print(f"  Volume/MA 비율: 평균 {vol['ratio_mean']:.2f}x, 중앙값 {vol['ratio_median']:.2f}x")
        print(f"  스파이크 발생률: >1.2x {vol['spike_1_2x_pct']:.1f}%, >1.5x {vol['spike_1_5x_pct']:.1f}%, >2.0x {vol['spike_2_0x_pct']:.1f}%")
    
    if 'price' in stats:
        price = stats['price']
        print(f"\n[가격 변동]")
        print(f"  캔들당 변화율: 평균 {price['change_pct_mean']:.3f}%, 표준편차 {price['change_pct_std']:.3f}%")
        print(f"  퍼센타일: p25={price['change_pct_p25']:.3f}%, p75={price['change_pct_p75']:.3f}%")
    
    print("\n" + "=" * 80)


def save_results(stats: dict, symbol: str, timeframe: str, days: int, output_path: str):
    """결과를 JSON 파일로 저장"""
    output = {
        'metadata': {
            'symbol': symbol,
            'timeframe': timeframe,
            'days': days,
            'timestamp': datetime.now().isoformat(),
        },
        'statistics': stats,
    }
    
    # 출력 디렉토리 생성
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # JSON 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"결과 저장 완료: {output_file}")


def main():
    """메인 실행 함수"""
    args = parse_args()
    
    try:
        # 1. 데이터 로드
        df = load_data(args.symbol, args.timeframe, args.days, args.data_path)
        
        # 2. 지표 계산
        df_with_indicators = compute_indicators(df)
        
        # 3. 통계 계산
        stats = compute_statistics(df_with_indicators)
        
        # 4. 결과 출력
        print_summary(stats, args.symbol, args.timeframe, args.days)
        
        # 5. 결과 저장
        save_results(stats, args.symbol, args.timeframe, args.days, args.output)
        
        print(f"\n✅ 프로파일링 완료! 결과: {args.output}")
        
        return 0
    
    except Exception as e:
        logger.error(f"프로파일링 실패: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
