#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Indicators Helper
==========================
PHASE29-3.3: 백테스트 데이터에 지표 추가

백테스트 raw OHLCV 데이터에 V4 전략 필수 지표를 계산하여 추가한다.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

from indicators.core_indicators import (
    ema,
    rsi,
    atr,
    compute_adx,
    volume_ma
)


def add_v4_indicators(df: pd.DataFrame, config: Dict[str, Any] = None) -> pd.DataFrame:
    """
    V4 전략 필수 지표를 데이터프레임에 추가
    
    Args:
        df: OHLCV 데이터프레임 (timestamp, open, high, low, close, volume)
        config: 지표 설정 (indicators 섹션)
    
    Returns:
        pd.DataFrame: 지표가 추가된 데이터프레임
    
    V4 필수 지표:
        - rsi_14: RSI (14)
        - adx_14, di_plus_14, di_minus_14: ADX + DI
        - ema_5, ema_20, ema_200: EMA
        - atr_14: ATR (14)
        - volume_ma_20: Volume MA (20)
    """
    # Config 기본값
    if config is None:
        config = {}
    
    indicators_cfg = config.get('indicators', {})
    
    # RSI 설정
    rsi_length = indicators_cfg.get('rsi', {}).get('length', 14)
    
    # EMA 설정
    ema_cfg = indicators_cfg.get('ema', {})
    ema_fast = ema_cfg.get('fast', 5)
    ema_mid = ema_cfg.get('mid', 20)
    ema_slow = ema_cfg.get('slow', 200)
    
    # ATR 설정
    atr_length = indicators_cfg.get('atr', {}).get('length', 14)
    
    # Volume MA 설정
    vol_ma_length = indicators_cfg.get('volume', {}).get('ma_length', 20)
    
    # ADX 설정
    adx_period = indicators_cfg.get('adx', {}).get('period', 14)
    
    # 데이터프레임 복사
    df = df.copy()
    
    # 1. RSI 계산
    df[f'rsi_{rsi_length}'] = rsi(df['close'], length=rsi_length)
    
    # 2. EMA 계산
    df[f'ema_{ema_fast}'] = ema(df['close'], length=ema_fast)
    df[f'ema_{ema_mid}'] = ema(df['close'], length=ema_mid)
    df[f'ema_{ema_slow}'] = ema(df['close'], length=ema_slow)
    
    # 3. ATR 계산
    df[f'atr_{atr_length}'] = atr(df, length=atr_length)
    
    # 4. Volume MA 계산
    df[f'volume_ma_{vol_ma_length}'] = volume_ma(df['volume'], length=vol_ma_length)
    
    # 5. ADX + DI 계산 (compute_adx는 df에 직접 컬럼 추가)
    df = compute_adx(df, period=adx_period)
    # compute_adx는 plus_di_{period}, minus_di_{period}, adx_{period} 형식으로 추가하므로
    # 별칭 생성 (di_plus_14, di_minus_14)
    if f'plus_di_{adx_period}' in df.columns and f'di_plus_{adx_period}' not in df.columns:
        df[f'di_plus_{adx_period}'] = df[f'plus_di_{adx_period}']
        df[f'di_minus_{adx_period}'] = df[f'minus_di_{adx_period}']
    
    return df


def validate_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    지표 컬럼 존재 여부 및 상태 검증
    
    Args:
        df: 지표가 추가된 데이터프레임
    
    Returns:
        dict: 검증 결과
            - valid: bool
            - missing: List[str]
            - stats: Dict[str, Dict]
    """
    required = [
        'rsi_14', 'adx_14', 'di_plus_14', 'di_minus_14',
        'ema_5', 'ema_20', 'ema_200',
        'atr_14', 'volume_ma_20'
    ]
    
    result = {
        'valid': True,
        'missing': [],
        'stats': {}
    }
    
    for col in required:
        if col not in df.columns:
            result['valid'] = False
            result['missing'].append(col)
        else:
            col_data = df[col]
            null_count = col_data.isnull().sum()
            null_pct = (null_count / len(col_data)) * 100
            
            result['stats'][col] = {
                'exists': True,
                'null_count': int(null_count),
                'null_pct': round(null_pct, 2),
                'mean': float(col_data.mean()) if null_count < len(col_data) else None,
                'std': float(col_data.std()) if null_count < len(col_data) else None
            }
    
    return result
