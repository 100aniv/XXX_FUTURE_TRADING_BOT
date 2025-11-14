#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Data Source
====================
CSV/Parquet 데이터 재생

PHASE8 확장:
- load_slice(days, timerange): 데이터 슬라이싱 기능 추가
"""
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple


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
    
    # ============================================
    # PHASE8: 데이터 슬라이싱 기능
    # ============================================
    
    def load_slice(self, days: Optional[int] = None, timerange: Optional[str] = None) -> pd.DataFrame:
        """
        PHASE8: 데이터 슬라이싱 로드
        
        Args:
            days: 최근 N일 (예: 3 → 최근 3일)
            timerange: 날짜 범위 "YYYY-MM-DD:YYYY-MM-DD" (예: "2023-04-01:2023-04-05")
        
        Returns:
            pd.DataFrame: 슬라이싱된 데이터
        
        Examples:
            >>> ds = BacktestDataSource('data/BTCUSDT_5m.csv')
            >>> df = ds.load_slice(days=3)  # 최근 3일
            >>> df = ds.load_slice(timerange='2023-04-01:2023-04-05')  # 특정 구간
        """
        # 전체 데이터 로드
        if self.df is None:
            self.load()
        
        # 슬라이싱 없으면 전체 반환
        if days is None and timerange is None:
            return self.df
        
        # days 우선 처리
        if days is not None:
            end_date = self.df['timestamp'].max()
            start_date = end_date - timedelta(days=days)
            sliced_df = self.df[self.df['timestamp'] >= start_date].copy()
            print(f"✅ [SLICE] 최근 {days}일 데이터 로드: {len(sliced_df)} rows ({start_date.date()} ~ {end_date.date()})")
            return sliced_df
        
        # timerange 처리
        if timerange:
            start_date, end_date = self._parse_timerange(timerange)
            sliced_df = self.df[
                (self.df['timestamp'] >= start_date) & 
                (self.df['timestamp'] <= end_date)
            ].copy()
            print(f"✅ [SLICE] 구간 데이터 로드: {len(sliced_df)} rows ({start_date.date()} ~ {end_date.date()})")
            return sliced_df
        
        return self.df
    
    def _parse_timerange(self, timerange: str) -> Tuple[datetime, datetime]:
        """
        날짜 범위 파싱
        
        Args:
            timerange: "YYYY-MM-DD:YYYY-MM-DD" 형식
        
        Returns:
            Tuple[datetime, datetime]: (start_date, end_date)
        
        Examples:
            >>> start, end = ds._parse_timerange('2023-04-01:2023-04-05')
            >>> print(start, end)
            2023-04-01 00:00:00 2023-04-05 23:59:59
        """
        parts = timerange.split(':')
        if len(parts) != 2:
            raise ValueError(f"timerange 형식 오류: '{timerange}' (예: '2023-04-01:2023-04-05')")
        
        start_str, end_str = parts
        start_date = pd.to_datetime(start_str)
        end_date = pd.to_datetime(end_str) + timedelta(days=1) - timedelta(seconds=1)  # 23:59:59까지
        
        return start_date, end_date
