#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레짐 태깅 도구
==============
데이터에 레짐(시장 상태) 태그 추가

레짐 분류:
- TREND_UP: 상승 추세 (ADX > 25, EMA slope > 0)
- TREND_DOWN: 하락 추세 (ADX > 25, EMA slope < 0)
- RANGE: 레인지 (ADX < 20, BB 밴드 수축)
- HIGH_VOL: 고변동성 (ATR% 상위 25%)
- LOW_VOL: 저변동성 (ATR% 하위 25%)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from indicators import add_indicators

def calculate_adx(df, period=14):
    """ADX 계산 (추세 강도)"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # +DM, -DM 계산
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # TR 계산
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed +DI, -DI
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # DX, ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx

def tag_regime(input_file: str):
    """레짐 태깅"""
    print("="*60)
    print("🏷️  레짐 태깅")
    print("="*60)
    
    # 데이터 로드
    print(f"\n📥 로드: {Path(input_file).name}")
    df = pd.read_csv(input_file)
    
    # 지표 추가
    print("📊 지표 계산 중...")
    df = add_indicators(df)
    
    # ADX 계산
    df['adx'] = calculate_adx(df, period=14)
    
    # EMA slope (추세 방향)
    df['ema_slope'] = df['ema_fast'].diff(5)  # 5캔들 기울기
    
    # ATR 퍼센트
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # BB 밴드폭
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close'] * 100
    
    # 레짐 태깅
    print("🏷️  레짐 분류 중...")
    df['regime'] = 'UNKNOWN'
    
    # 1) TREND_UP
    trend_up_mask = (df['adx'] > 25) & (df['ema_slope'] > 0)
    df.loc[trend_up_mask, 'regime'] = 'TREND_UP'
    
    # 2) TREND_DOWN
    trend_down_mask = (df['adx'] > 25) & (df['ema_slope'] < 0)
    df.loc[trend_down_mask, 'regime'] = 'TREND_DOWN'
    
    # 3) RANGE
    range_mask = (df['adx'] < 20) & (df['bb_width'] < df['bb_width'].quantile(0.4))
    df.loc[range_mask, 'regime'] = 'RANGE'
    
    # 4) HIGH_VOL
    high_vol_mask = df['atr_pct'] > df['atr_pct'].quantile(0.75)
    df.loc[high_vol_mask & (df['regime'] == 'UNKNOWN'), 'regime'] = 'HIGH_VOL'
    
    # 5) LOW_VOL
    low_vol_mask = df['atr_pct'] < df['atr_pct'].quantile(0.25)
    df.loc[low_vol_mask & (df['regime'] == 'UNKNOWN'), 'regime'] = 'LOW_VOL'
    
    # 통계 출력
    print("\n📊 레짐 분포:")
    regime_counts = df['regime'].value_counts()
    for regime, count in regime_counts.items():
        pct = count / len(df) * 100
        print(f"   {regime}: {count:,}개 ({pct:.1f}%)")
    
    # 저장
    output_file = Path(input_file).parent / f"{Path(input_file).stem}_TAGGED.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✅ 저장: {output_file.name}")
    
    # 요약 파일 생성
    summary_file = Path(input_file).parent / 'regime_summary.csv'
    summary = df.groupby('regime').agg({
        'close': ['count', 'mean', 'std'],
        'atr_pct': 'mean',
        'adx': 'mean',
        'bb_width': 'mean'
    }).round(4)
    summary.to_csv(summary_file)
    print(f"✅ 요약: {summary_file.name}")
    
    print("\n" + "="*60)
    print("✅ 태깅 완료!")
    print("="*60)
    
    return output_file

if __name__ == '__main__':
    # Train 데이터 태깅
    data_dir = Path(__file__).parent.parent / 'data'
    train_file = data_dir / 'BTCUSDT_5m_2024-01-01_2024-09-30_TRAIN.csv'
    
    if train_file.exists():
        tag_regime(str(train_file))
    else:
        print(f"❌ 파일 없음: {train_file}")
        print("먼저 split_train_oos.py를 실행하세요.")
