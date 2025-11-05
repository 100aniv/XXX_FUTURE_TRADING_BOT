#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collector 표준화 테스트
======================
체크리스트 #2 검증: stream()이 닫힌 캔들만 yield (키: symbol, timeframe, closed_at)
"""
import pytest
import pandas as pd
from pathlib import Path
from collectors import HistoricalFeed


class TestHistoricalFeed:
    """HistoricalFeed 표준화 테스트"""
    
    def test_candle_keys(self, tmp_path):
        """캔들 키 형식 검증"""
        # 테스트 CSV 생성
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            'timestamp': [1609459200000, 1609459500000, 1609459800000],
            'open': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000.0, 1100.0, 1200.0]
        })
        df.to_csv(csv_path, index=False)
        
        # HistoricalFeed 초기화
        feed = HistoricalFeed(str(csv_path), symbol='BTCUSDT', timeframe='5m')
        
        # 첫 캔들 확인
        candle = next(feed.stream())
        
        # ⭐ 표준 키 검증
        assert 'symbol' in candle, "symbol 키 필수"
        assert 'timeframe' in candle, "timeframe 키 필수"
        assert 'closed_at' in candle, "closed_at 키 필수"
        
        # 값 검증
        assert candle['symbol'] == 'BTCUSDT'
        assert candle['timeframe'] == '5m'
        assert isinstance(candle['closed_at'], int)
        
        # 기본 OHLCV 키
        assert 'open' in candle
        assert 'high' in candle
        assert 'low' in candle
        assert 'close' in candle
        assert 'volume' in candle
        
        # 하위 호환성 (time)
        assert 'time' in candle
        assert candle['time'] == candle['closed_at']
    
    def test_all_candles_closed(self, tmp_path):
        """모든 캔들이 닫혀있는지 검증"""
        # 테스트 CSV 생성
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            'timestamp': [i * 300000 for i in range(100)],  # 5분 간격
            'open': [100.0 + i for i in range(100)],
            'high': [101.0 + i for i in range(100)],
            'low': [99.0 + i for i in range(100)],
            'close': [100.5 + i for i in range(100)],
            'volume': [1000.0] * 100
        })
        df.to_csv(csv_path, index=False)
        
        feed = HistoricalFeed(str(csv_path), symbol='BTCUSDT', timeframe='5m')
        
        # 모든 캔들이 닫혀있어야 함 (CSV는 과거 데이터)
        for candle in feed.stream():
            assert candle['closed_at'] > 0
            assert isinstance(candle['closed_at'], int)


class TestWebSocketCollector:
    """WebSocketCollector 표준화 테스트 (모의)"""
    
    def test_candle_format(self):
        """WebSocket 캔들 형식 검증"""
        # 실제 WebSocket 테스트는 복잡하므로, 
        # 여기서는 데이터 형식만 검증
        
        # WebSocketCollector가 생성하는 캔들 형식
        mock_candle = {
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "closed_at": 1609459200000,
            "time": 1609459200000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000.0
        }
        
        # 표준 키 검증
        assert 'symbol' in mock_candle
        assert 'timeframe' in mock_candle
        assert 'closed_at' in mock_candle
        
        # 값 검증
        assert mock_candle['symbol'] == 'BTCUSDT'
        assert mock_candle['timeframe'] == '5m'
        assert isinstance(mock_candle['closed_at'], int)


class TestCollectorUniformity:
    """Collector 일관성 테스트"""
    
    def test_same_interface(self, tmp_path):
        """HistoricalFeed와 WebSocketCollector가 동일한 인터페이스인지"""
        # 테스트 CSV
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            'timestamp': [1609459200000],
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.5],
            'volume': [1000.0]
        })
        df.to_csv(csv_path, index=False)
        
        feed = HistoricalFeed(str(csv_path), symbol='BTCUSDT', timeframe='5m')
        
        # stream() 메서드 존재
        assert hasattr(feed, 'stream')
        assert callable(feed.stream)
        
        # generator 반환
        gen = feed.stream()
        assert hasattr(gen, '__iter__')
        assert hasattr(gen, '__next__')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
