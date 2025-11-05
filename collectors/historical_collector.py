#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Historical Collector
====================
CSV 파일에서 과거 데이터를 읽어서 스트리밍

- HistoricalFeed: CSV → 캔들 스트림
- 컬럼명 자동 표준화 (timestamp → time 등)
- 시간대 자동 감지 (초/밀리초)
"""
import pandas as pd
import heapq
from pathlib import Path
from typing import Iterator, Dict, Optional, List
from common.logger import setup_logger

logger = setup_logger(__name__)


def _tf_to_minutes(tf: str) -> int:
    """'5m', '15m', '1h', '4h', '1d' → minutes"""
    if not tf:
        return 0
    tf = str(tf).strip().lower()
    if tf.endswith('m'):
        return int(tf[:-1])
    if tf.endswith('h'):
        return int(tf[:-1]) * 60
    if tf.endswith('d'):
        return int(tf[:-1]) * 60 * 24
    # 숫자만 들어오면 분으로 간주
    try:
        return int(tf)
    except Exception:
        return 0


def _minutes_to_tf(m: int) -> str:
    if m % (60 * 24) == 0:
        return f"{m // (60 * 24)}d"
    if m % 60 == 0 and m >= 60:
        return f"{m // 60}h"
    return f"{m}m"


class HistoricalFeed:
    """
    백테스트용 히스토리 데이터 피드
    CSV 파일을 한 줄씩 읽어서 캔들 스트림 생성
    """
    
    def __init__(self, csv_path: str, symbol: str = None, timeframe: str = None, tz: str = None):
        """
        Args:
            csv_path: CSV 파일 경로
            symbol: 심볼 (예: 'BTCUSDT')
            timeframe: 타임프레임 (예: '5m')
            tz: 시간대 (예: 'Asia/Seoul', None이면 UTC)
        """
        self.csv_path = csv_path
        self.symbol = symbol or 'BTCUSDT'
        self.timeframe = timeframe or '5m'
        self.df = pd.read_csv(csv_path)
        
        # 1. 컬럼명 표준화
        rename_map = {
            "timestamp": "time",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume"
        }
        
        # 실제 존재하는 컬럼만 rename
        actual_rename = {k: v for k, v in rename_map.items() if k in self.df.columns}
        if actual_rename:
            self.df = self.df.rename(columns=actual_rename)
        
        # 2. 시간 컬럼 변환
        if "time" in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df["time"]):
                # 숫자형 → epoch 판단 (초 vs 밀리초)
                sample = int(self.df["time"].iloc[0])
                if sample > 10_000_000_000:  # 밀리초
                    self.df["time"] = pd.to_datetime(self.df["time"], unit="ms", utc=True)
                else:  # 초
                    self.df["time"] = pd.to_datetime(self.df["time"], unit="s", utc=True)
            else:
                # 문자열 → datetime
                self.df["time"] = pd.to_datetime(self.df["time"], utc=True)
            
            # 시간대 변환
            if tz:
                self.df["time"] = self.df["time"].dt.tz_convert(tz)
        
        # 3. 시간순 정렬
        self.df = self.df.sort_values("time").reset_index(drop=True)

        # 3.5 요청 TF로 업샘플(resample) 지원 (예: 15m CSV → 1h/4h)
        try:
            req_min = _tf_to_minutes(self.timeframe)
            # 기준 TF 추정: 가장 빈도가 높은 간격 사용
            diffs = self.df["time"].diff().dropna()
            if not diffs.empty:
                # Timedelta → 분
                base_min = int(diffs.dt.total_seconds().mode().iloc[0] // 60)
            else:
                base_min = 0
            if base_min > 0 and req_min > base_min and (req_min % base_min == 0):
                rule = f"{req_min}T"  # 분 단위 리샘플
                df_idx = self.df.set_index("time")
                resampled = df_idx.resample(rule, label='right', closed='right').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna(subset=['open', 'high', 'low', 'close'])
                resampled = resampled.reset_index()
                self.df = resampled
                logger.info(f"✅ Resample: { _minutes_to_tf(base_min) } → { _minutes_to_tf(req_min) } ({len(self.df):,} bars)")
            elif base_min > req_min and req_min > 0:
                # 다운샘플은 불가 (CSV가 더 희박함). 출력 TF를 CSV 기준으로 교정
                self.timeframe = _minutes_to_tf(base_min)
                logger.warning(f"⚠️ 요청 TF({req_min}m) < CSV TF({base_min}m). 다운샘플 불가 → 실제 TF: {self.timeframe}")
        except Exception as e:
            logger.warning(f"⚠️ Resample 스킵: {e}")

        self.total = len(self.df)
        self.index = 0
        
        logger.info(f"✅ HistoricalFeed 초기화: {self.total:,}개 캔들 ({csv_path})")
    
    def stream(self) -> Iterator[Dict]:
        """
        캔들 스트림 생성 (generator)
        
        Yields:
            캔들 dict {'time': int, 'open': float, 'high': float, ...}
        """
        for i in range(self.total):
            row = self.df.iloc[i]
            
            # timestamp → unix milliseconds
            if isinstance(row["time"], pd.Timestamp):
                ts = int(row["time"].timestamp() * 1000)
            else:
                ts = int(row["time"])
            
            # ⭐ 표준 키 형식: (symbol, timeframe, closed_at)
            candle = {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'closed_at': ts,
                'time': ts,  # 하위 호환성 (추후 제거)
                'open': float(row["open"]),
                'high': float(row["high"]),
                'low': float(row["low"]),
                'close': float(row["close"]),
                'volume': float(row["volume"])
            }
            
            self.index = i + 1
            yield candle
    
    def stream_with_history(self, lookback: int = 400) -> Iterator[tuple]:
        """
        캔들 + 히스토리 윈도우 스트림
        
        Args:
            lookback: 히스토리 개수
        
        Yields:
            (index, df_window) 튜플
            - index: 현재 인덱스
            - df_window: 현재까지의 DataFrame (최대 lookback개)
        """
        for i in range(self.total):
            # 윈도우 슬라이싱
            start = max(0, i - lookback + 1)
            window = self.df.iloc[start:i+1].copy()
            
            self.index = i + 1
            yield i, window
    
    def progress(self) -> float:
        """
        진행률 (0.0 ~ 1.0)
        
        Returns:
            진행률
        """
        return self.index / self.total if self.total > 0 else 0.0
    
    def get_dataframe(self, start_idx: int = 0, end_idx: int = None) -> pd.DataFrame:
        """
        특정 구간의 DataFrame 반환
        
        Args:
            start_idx: 시작 인덱스
            end_idx: 종료 인덱스 (None이면 끝까지)
        
        Returns:
            DataFrame
        """
        if end_idx is None:
            return self.df.iloc[start_idx:].copy()
        else:
            return self.df.iloc[start_idx:end_idx].copy()


def load_historical_data(csv_path: str, tz: str = None) -> HistoricalFeed:
    """
    히스토리 데이터 로드 (편의 함수)
    
    Args:
        csv_path: CSV 파일 경로
        tz: 시간대
    
    Returns:
        HistoricalFeed 인스턴스
    """
    return HistoricalFeed(csv_path, tz)


class MultiSymbolHistoricalFeed:
    """
    멀티 심볼 백테스트용 히스토리 데이터 피드
    여러 CSV 파일을 시간순으로 병합하여 스트리밍
    """
    def __init__(self, symbols: List[str], data_dir: str = 'data',
                 timeframe: str = '5m', start_date: str = None, end_date: str = None):
        """
        Args:
            symbols: 심볼 리스트 (예: ['BTCUSDT', 'ETHUSDT'])
            data_dir: 데이터 디렉토리
            timeframe: 타임프레임
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
        """
        self.symbols = symbols
        self.data_dir = Path(data_dir)
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.dfs: Dict[str, pd.DataFrame] = {}
        self.total_candles = 0

        for symbol in symbols:
            df = self._load_symbol_data(symbol)
            if df is not None and len(df) > 0:
                self.dfs[symbol] = df
                self.total_candles += len(df)
                logger.info(f"  ✅ {symbol}: {len(df):,}개 캔들")
            else:
                logger.warning(f"  ⚠️ {symbol}: 데이터 없음")

        if not self.dfs:
            raise FileNotFoundError(f"❌ 로드된 데이터 없음: {data_dir}")

        logger.info(f"✅ MultiSymbolHistoricalFeed: {len(self.dfs)}개 심볼, {self.total_candles:,}개 캔들")
        self.index = 0

    def _load_symbol_data(self, symbol: str) -> pd.DataFrame:
        """단일 심볼 데이터 로드"""
        pattern = f"{symbol}_{self.timeframe}_*.csv"
        csv_files = list(self.data_dir.glob(pattern))
        if not csv_files:
            return None

        csv_path = sorted(csv_files)[-1]
        df = pd.read_csv(csv_path)

        # 컬럼명 표준화
        if 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'time'})

        # 시간 변환
        if 'time' in df.columns:
            if pd.api.types.is_numeric_dtype(df['time']):
                sample = int(df['time'].iloc[0])
                if sample > 10_000_000_000:  # 밀리초
                    df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
                else:  # 초
                    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
            else:
                df['time'] = pd.to_datetime(df['time'], utc=True)

        # 심볼 컬럼 추가
        df['symbol'] = symbol

        # 시간순 정렬
        df = df.sort_values('time').reset_index(drop=True)

        # 기간 필터링
        if self.start_date:
            df = df[df['time'] >= pd.to_datetime(self.start_date, utc=True)]
        if self.end_date:
            df = df[df['time'] <= pd.to_datetime(self.end_date, utc=True)]

        return df

    def stream(self) -> Iterator[Dict]:
        """
        멀티 심볼 캔들 스트림 (시간순 정렬)
        Yields: 캔들 dict {'symbol': str, 'time': int, 'open': float, ...}
        """
        indices = {symbol: 0 for symbol in self.dfs.keys()}
        heap: List[tuple] = []
        for symbol, df in self.dfs.items():
            if len(df) > 0:
                row = df.iloc[0]
                timestamp = int(row['time'].timestamp() * 1000)
                heapq.heappush(heap, (timestamp, symbol, 0))

        while heap:
            timestamp, symbol, idx = heapq.heappop(heap)
            df = self.dfs[symbol]
            row = df.iloc[idx]

            candle = {
                'symbol': symbol,
                'timeframe': self.timeframe,
                'closed_at': timestamp,
                'time': timestamp,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            }

            self.index += 1
            yield candle

            next_idx = idx + 1
            if next_idx < len(df):
                next_row = df.iloc[next_idx]
                next_timestamp = int(next_row['time'].timestamp() * 1000)
                heapq.heappush(heap, (next_timestamp, symbol, next_idx))

    def progress(self) -> float:
        """진행률 (0.0 ~ 1.0)"""
        return self.index / self.total_candles if self.total_candles > 0 else 0.0

    def get_symbols(self) -> List[str]:
        """로드된 심볼 리스트"""
        return list(self.dfs.keys())
