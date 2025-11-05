#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Data Source
====================
CSV/Parquet 데이터 재생
"""
import pandas as pd
from pathlib import Path


class BacktestDataSource:
    """백테스트 데이터 소스 (CSV)"""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.df = None
    
    def load(self):
        """데이터 로드"""
        self.df = pd.read_csv(self.data_path)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        return self.df
    
    def load_data(self):
        """데이터 로드 (load()와 동일)"""
        return self.load()
    
    def get_dataframe(self):
        """전체 DataFrame 반환"""
        return self.df
    
    def fetch(self, candle_range: dict = None):
        """
        IDataSource 계약 준수: 데이터 조회
        
        Args:
            candle_range: {"symbol": str, "tf": str, "limit": int, ...} (무시됨, 파일 기반)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if self.df is None:
            self.load()
        return self.df
