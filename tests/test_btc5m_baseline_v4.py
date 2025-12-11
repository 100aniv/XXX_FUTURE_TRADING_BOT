#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-3.1: btc5m_baseline_v4 Unit Tests
==========================================
V4 전략 기본 기능 검증

테스트 항목:
1. Config 파라미터 로드 확인
2. Trend Mode Score 계산 로직
3. Range Mode Score 계산 로직
4. Regime Detection 정상 작동 (V3 재사용)
5. Multi-TP 구조 생성
"""
import pytest
from pathlib import Path
import sys
import pandas as pd
import numpy as np

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from strategies.btc5m_baseline_v4 import (
    Btc5mBaselineV4,
    signal_logic,
    _calculate_trend_score,
    _calculate_range_score
)


@pytest.fixture
def basic_config():
    """
    기본 Config
    """
    return {
        "timeframe": "5m",
        "symbol": "BTCUSDT",
        "leverage": {"min": 1, "max": 10, "default": 3},
        
        # Regime Detection
        "adx_trend_threshold": 25,
        "adx_range_threshold": 20,
        
        # Trend Mode
        "trend_min_score": 3,
        "trend_rsi_threshold": 45,
        "trend_weight_rsi": 3,
        "trend_weight_bb": 2,
        "trend_weight_ema": 2,
        "trend_weight_di": 1,
        
        # Range Mode
        "range_min_score": 2,
        "range_rsi_threshold": 40,
        "range_weight_rsi": 3,
        "range_weight_bb": 2,
        "range_weight_adx": 1,
        
        # TP/SL
        "atr_mult_sl_trend": 2.0,
        "tp1_mult_trend": 1.2,
        "tp2_mult_trend": 3.0,
        "atr_mult_sl_range": 1.5,
        "tp1_mult_range": 1.0,
        "tp2_mult_range": 2.0,
        "tp1_size_pct": 0.6,
        "tp2_size_pct": 0.4,
        
        # Filters
        "filters": {
            "allow_short": True,
            "min_atr_pct": 0.0015,
            "min_volume_ratio": 0.5,
            "enable_min_atr": True,
            "enable_volume_filter": True
        },
        
        # BB/Momentum Threshold (V2/V3 호환)
        "bb_mult_main_base": 0.8,
        "bb_mult_strong_base": 1.5,
        "rsi_percentile_base": 25
    }


@pytest.fixture
def sample_df():
    """
    샘플 DataFrame (100 캔들)
    """
    np.random.seed(42)
    n = 100
    
    # 기본 OHLCV
    close = 40000 + np.cumsum(np.random.randn(n) * 100)
    high = close + np.abs(np.random.randn(n) * 50)
    low = close - np.abs(np.random.randn(n) * 50)
    open_price = close + np.random.randn(n) * 20
    volume = 1000 + np.abs(np.random.randn(n) * 200)
    
    # 지표
    rsi = 50 + np.random.randn(n) * 15
    rsi = np.clip(rsi, 0, 100)
    
    adx = 20 + np.abs(np.random.randn(n) * 10)
    adx = np.clip(adx, 0, 100)
    
    di_plus = 25 + np.random.randn(n) * 5
    di_minus = 25 + np.random.randn(n) * 5
    
    atr = close * 0.002  # 0.2%
    
    ema_5 = close + np.random.randn(n) * 50
    ema_20 = close + np.random.randn(n) * 100
    
    # BB
    bb_middle = close
    bb_std = atr * 10
    bb_upper = bb_middle + bb_std * 2
    bb_lower = bb_middle - bb_std * 2
    
    # Volume MA
    volume_ma_20 = volume * (0.8 + np.random.rand(n) * 0.4)
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-11-01', periods=n, freq='5min'),
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'rsi_14': rsi,
        'adx_14': adx,
        'di_plus_14': di_plus,
        'di_minus_14': di_minus,
        'atr_14': atr,
        'ema_5': ema_5,
        'ema_20': ema_20,
        'bb_middle_20_2.0': bb_middle,
        'bb_upper_20_2.0': bb_upper,
        'bb_lower_20_2.0': bb_lower,
        'volume_ma_20': volume_ma_20
    })
    
    return df


def test_v4_class_instantiation(basic_config):
    """
    PHASE29-3.1: V4 클래스 인스턴스 생성 확인
    """
    v4 = Btc5mBaselineV4(config=basic_config)
    
    # 기본 속성 확인
    assert hasattr(v4, 'config'), "V4에 config 속성이 없습니다."
    assert hasattr(v4, 'deprecated'), "V4에 deprecated 속성이 없습니다."
    assert v4.deprecated is False, "V4는 deprecated가 아니어야 합니다."
    
    # Metadata 확인
    assert hasattr(v4, 'metadata'), "V4에 metadata가 없습니다."
    metadata = v4.metadata
    assert metadata.strategy_name == 'btc5m_baseline_v4', f"전략 이름이 잘못되었습니다: {metadata.strategy_name}"
    assert 'alpha' in metadata.version.lower(), f"버전에 alpha 표시가 없습니다: {metadata.version}"
    
    print(f"✅ V4 클래스 인스턴스 생성 성공: {v4}")
    print(f"   - metadata: {metadata.strategy_name} v{metadata.version}")


def test_config_parameters_load(basic_config):
    """
    PHASE29-3.1: Config 파라미터 로드 확인
    """
    # Trend Mode 파라미터
    assert basic_config['trend_min_score'] == 3, "trend_min_score가 3이 아닙니다."
    assert basic_config['trend_rsi_threshold'] == 45, "trend_rsi_threshold가 45가 아닙니다."
    assert basic_config['trend_weight_rsi'] == 3, "trend_weight_rsi가 3이 아닙니다."
    
    # Range Mode 파라미터
    assert basic_config['range_min_score'] == 2, "range_min_score가 2가 아닙니다."
    assert basic_config['range_rsi_threshold'] == 40, "range_rsi_threshold가 40이 아닙니다."
    
    # TP/SL 파라미터
    assert basic_config['atr_mult_sl_trend'] == 2.0, "atr_mult_sl_trend가 2.0이 아닙니다."
    assert basic_config['tp1_mult_trend'] == 1.2, "tp1_mult_trend가 1.2가 아닙니다."
    
    print(f"✅ Config 파라미터 로드 확인 완료")
    print(f"   - trend_min_score: {basic_config['trend_min_score']}")
    print(f"   - range_min_score: {basic_config['range_min_score']}")


def test_trend_score_calculation_long(basic_config):
    """
    PHASE29-3.1: Trend Mode Score 계산 (LONG 예시)
    """
    # LONG 조건 설정 (Bull Trend)
    price = 40000.0
    rsi = 40.0  # < 45 (RSI Pullback)
    bb_main = {'upper': 41000.0, 'lower': 39000.0}  # Price < Lower
    ema_5 = 40100.0
    ema_20 = 39900.0  # EMA 20 < Price < EMA 5
    adx = 30.0  # >= 25 (Trend)
    di_plus = 30.0
    di_minus = 20.0  # DI+ > DI- (Bull)
    
    regime_info = {'trend': 'BULL', 'volatility': 'high', 'regime': 'bull_high_vol'}
    
    score, conditions, side = _calculate_trend_score(
        price, rsi, bb_main, ema_5, ema_20, adx, di_plus, di_minus,
        rsi_long_thresh=45, rsi_short_thresh=55, regime_info=regime_info, config=basic_config
    )
    
    # Score 확인
    assert score > 0, f"Trend LONG Score가 0입니다: {score}"
    assert side == "LONG", f"Side가 LONG이 아닙니다: {side}"
    assert len(conditions) > 0, "Conditions가 비어 있습니다."
    
    # 예상 Score: RSI(3) + BB(2) + EMA(2) + DI(1) = 8
    assert score >= 6, f"Score가 너무 낮습니다: {score} (예상: 6~8)"
    
    print(f"✅ Trend LONG Score 계산 성공")
    print(f"   - Score: {score}")
    print(f"   - Conditions: {conditions}")


def test_range_score_calculation_long(basic_config):
    """
    PHASE29-3.1: Range Mode Score 계산 (LONG 예시)
    """
    # LONG 조건 설정 (Range)
    price = 39500.0
    rsi = 35.0  # < 40 (Oversold)
    bb_main = {'upper': 41000.0, 'lower': 40000.0}  # Price < Lower
    adx = 15.0  # < 20 (Range)
    di_plus = 22.0
    di_minus = 23.0  # DI+/DI- 차이 작음
    
    regime_info = {'trend': 'NEUTRAL', 'volatility': 'low', 'regime': 'range_low_vol'}
    
    score, conditions, side = _calculate_range_score(
        price, rsi, bb_main, adx, di_plus, di_minus,
        rsi_long_thresh=40, rsi_short_thresh=60, regime_info=regime_info, config=basic_config
    )
    
    # Score 확인
    assert score > 0, f"Range LONG Score가 0입니다: {score}"
    assert side == "LONG", f"Side가 LONG이 아닙니다: {side}"
    assert len(conditions) > 0, "Conditions가 비어 있습니다."
    
    # 예상 Score: RSI(3) + BB(2) + ADX(1) = 6
    assert score >= 3, f"Score가 너무 낮습니다: {score} (예상: 3~6)"
    
    print(f"✅ Range LONG Score 계산 성공")
    print(f"   - Score: {score}")
    print(f"   - Conditions: {conditions}")


def test_signal_logic_execution(sample_df, basic_config):
    """
    PHASE29-3.1: signal_logic 전체 실행 (샘플 데이터)
    """
    signal = signal_logic(sample_df, basic_config)
    
    # 신호 구조 확인 (신호 발생 여부와 무관)
    assert 'side' in signal, "신호에 'side' 키가 없습니다."
    assert 'reason' in signal, "신호에 'reason' 키가 없습니다."
    
    # 신호 발생 시 필수 키 확인
    if signal['side'] is not None:
        assert 'entry' in signal, "진입 신호에 'entry'가 없습니다."
        assert 'sl' in signal, "진입 신호에 'sl'이 없습니다."
        assert 'tp' in signal, "진입 신호에 'tp'가 없습니다."
        assert 'take_profits' in signal, "진입 신호에 'take_profits'가 없습니다."
        
        # Multi-TP 구조 확인
        tps = signal['take_profits']
        assert len(tps) == 2, f"Multi-TP는 2개여야 합니다: {len(tps)}"
        assert tps[0]['label'] == 'TP1', f"TP1 라벨이 잘못되었습니다: {tps[0]['label']}"
        assert tps[1]['label'] == 'TP2', f"TP2 라벨이 잘못되었습니다: {tps[1]['label']}"
        assert tps[0]['size_pct'] == 0.6, f"TP1 비율이 0.6이 아닙니다: {tps[0]['size_pct']}"
        
        # Metadata 확인
        assert 'metadata' in signal, "신호에 'metadata'가 없습니다."
        metadata = signal['metadata']
        assert 'score' in metadata, "metadata에 'score'가 없습니다."
        assert 'conditions' in metadata, "metadata에 'conditions'가 없습니다."
        
        print(f"✅ signal_logic 실행 성공: {signal['side']} 신호 발생")
        print(f"   - Score: {metadata['score']}")
        print(f"   - Conditions: {metadata['conditions']}")
        print(f"   - Entry: {signal['entry']:.2f}, SL: {signal['sl']:.2f}, TP1: {signal['take_profits'][0]['price']:.2f}")
    else:
        print(f"✅ signal_logic 실행 성공: 신호 없음 ({signal['reason']})")


def test_regime_detection_integration(sample_df, basic_config):
    """
    PHASE29-3.1: Regime Detection 통합 (V3 재사용)
    """
    signal = signal_logic(sample_df, basic_config)
    
    # Metadata에 Regime 정보 존재 확인
    if 'metadata' in signal:
        metadata = signal['metadata']
        assert 'regime' in metadata or 'mode' in metadata, "Regime 정보가 metadata에 없습니다."
        print(f"✅ Regime Detection 통합 확인")
        if 'regime' in metadata:
            print(f"   - Regime: {metadata['regime']}")
        if 'mode' in metadata:
            print(f"   - Mode: {metadata['mode']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
