#!/usr/bin/env python3
"""
Indicators Contract Tests (PR4)
================================
지표 인터페이스 계약 검증

테스트 항목:
1. 최소 데이터 요구사항
2. NaN 전파 정책
3. 출력 스키마
4. 불변성
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from indicators import (
    ema, rsi, macd, bb, atr, donchian, add_indicators, regime, volume_ma
)


def sma(series, length):
    """Simple Moving Average (테스트용 helper)"""
    return series.rolling(window=length).mean()


class TestIndicatorsContract:
    """지표 인터페이스 계약 테스트"""
    
    @pytest.fixture
    def sample_df(self):
        """테스트용 샘플 DataFrame"""
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        np.random.seed(42)
        
        close = 100 + np.cumsum(np.random.randn(200) * 0.5)
        high = close + np.random.rand(200) * 2
        low = close - np.random.rand(200) * 2
        open_price = close + np.random.randn(200) * 0.5
        volume = np.random.rand(200) * 1000
        
        return pd.DataFrame({
            'time': dates,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def test_ema_min_bars(self, sample_df):
        """EMA: 최소 데이터 요구사항"""
        # 20개 행으로 EMA(20) 계산
        result = ema(sample_df['close'].head(20), 20)
        
        # 결과 길이 확인
        assert len(result) == 20
        
        # EMA는 첫 값부터 계산됨 (SMA와 다름)
        assert not pd.isna(result.iloc[0])
        
        # 모든 값 계산됨
        assert not result.isna().any()
    
    def test_sma_nan_propagation(self, sample_df):
        """SMA: NaN 전파 정책"""
        result = sma(sample_df['close'], 20)
        
        # 처음 19개는 NaN
        assert result.iloc[:19].isna().all()
        
        # 20번째부터는 값 존재
        assert not pd.isna(result.iloc[19])
    
    def test_rsi_min_bars(self, sample_df):
        """RSI: 최소 데이터 요구사항"""
        # 14+1개 행 필요
        result = rsi(sample_df['close'].head(15), 14)
        
        assert len(result) == 15
        # 초기 NaN 존재
        assert pd.isna(result.iloc[0])
        # 마지막은 계산됨
        assert not pd.isna(result.iloc[-1])
    
    def test_macd_output_schema(self, sample_df):
        """MACD: 출력 스키마 검증"""
        result = macd(sample_df)
        
        # 3개 컬럼 추가 확인
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_hist' in result.columns
        
        # 인덱스 유지
        assert len(result) == len(sample_df)
    
    def test_bb_output_schema(self, sample_df):
        """Bollinger Bands: 출력 스키마 검증"""
        result = bb(sample_df)
        
        # 3개 컬럼 추가
        assert 'bb_upper' in result.columns
        assert 'bb_mid' in result.columns
        assert 'bb_lower' in result.columns
        
        # 값 범위 검증 (upper > mid > lower)
        valid_rows = result.dropna()
        assert (valid_rows['bb_upper'] >= valid_rows['bb_mid']).all()
        assert (valid_rows['bb_mid'] >= valid_rows['bb_lower']).all()
    
    def test_atr_min_bars(self, sample_df):
        """ATR: 최소 데이터 요구사항"""
        result = atr(sample_df.head(15), 14)
        
        # 결과 길이
        assert len(result) == 15
        
        # 처음 몇 개 NaN (shift + rolling)
        assert pd.isna(result.iloc[0])
        
        # ATR은 항상 양수
        valid_values = result.dropna()
        assert (valid_values >= 0).all()
    
    def test_immutability(self, sample_df):
        """불변성: 입력 DataFrame 수정 안함"""
        original = sample_df.copy()
        
        # 지표 계산
        _ = ema(sample_df['close'], 20)
        _ = macd(sample_df.copy())
        _ = bb(sample_df.copy())
        
        # 원본 변경 없음 확인
        pd.testing.assert_frame_equal(sample_df, original)
    
    def test_add_indicators_complete(self, sample_df):
        """add_indicators: 전체 지표 추가 및 NaN 제거"""
        result = add_indicators(sample_df)
        
        # NaN 제거됨
        assert not result.isna().any().any()
        
        # 필수 컬럼 존재
        expected_cols = [
            'ema_fast', 'ema_mid', 'ema_slow',
            'macd', 'macd_signal', 'macd_hist',
            'rsi',
            'bb_upper', 'bb_mid', 'bb_lower',
            'atr',
            'dc_upper', 'dc_mid', 'dc_lower',
            'vol_ma'
        ]
        for col in expected_cols:
            assert col in result.columns
        
        # 행 개수 감소 (NaN 제거로 인해)
        assert len(result) < len(sample_df)
    
    def test_regime_output(self, sample_df):
        """regime: 출력 스키마 검증"""
        df_with_indicators = add_indicators(sample_df)
        df_with_indicators['regime'] = df_with_indicators.apply(regime, axis=1)
        
        # regime 컬럼 존재
        assert 'regime' in df_with_indicators.columns
        
        # 허용된 값만 존재
        allowed = {"상승장", "하락장", "횡보장", "중립"}
        assert set(df_with_indicators['regime'].unique()).issubset(allowed)


class TestIndicatorsEdgeCases:
    """지표 경계 조건 테스트"""
    
    def test_empty_dataframe(self):
        """빈 DataFrame 처리"""
        df = pd.DataFrame(columns=['close'])
        result = ema(df['close'], 20)
        assert len(result) == 0
    
    def test_insufficient_data(self):
        """불충분한 데이터 (NaN 전파)"""
        df = pd.DataFrame({'close': [100, 101, 102]})
        result = sma(df['close'], 20)
        
        # 모두 NaN
        assert result.isna().all()
    
    def test_zero_volume(self):
        """거래량 0 처리"""
        df = pd.DataFrame({
            'volume': [0, 0, 0, 100, 200]
        })
        result = volume_ma(df['volume'], 3)
        
        # 계산은 되지만 0 포함
        assert not result.dropna().empty
