#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Time Utilities - UTC Timezone Standardization (PHASE32-1)
==========================================================

SSOT for timezone handling across the entire trading bot.

Design Principle:
- All datetime operations use UTC tz-aware timestamps
- No tz-naive comparisons (prevents "Invalid comparison" errors)
- Consistent conversion: naive → UTC localize, aware → UTC convert

Usage:
    from common.time_utils import ensure_utc_timestamp, ensure_utc_index
    
    # Normalize scalar timestamp
    ts_utc = ensure_utc_timestamp(some_timestamp, ref_index=df.index)
    
    # Normalize DataFrame index
    df = ensure_utc_index(df)
"""
import pandas as pd
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


def ensure_utc_timestamp(
    ts: Union[pd.Timestamp, str, int, float],
    ref_index: Optional[pd.DatetimeIndex] = None
) -> pd.Timestamp:
    """
    Ensure a timestamp is UTC tz-aware.
    
    Args:
        ts: Input timestamp (any format)
        ref_index: Optional reference index to infer timezone
    
    Returns:
        pd.Timestamp: UTC tz-aware timestamp
    
    Raises:
        ValueError: If conversion fails
    """
    try:
        # Convert to pd.Timestamp if not already
        if not isinstance(ts, pd.Timestamp):
            ts = pd.to_datetime(ts)
        
        # If already tz-aware
        if ts.tz is not None:
            # Convert to UTC if not already
            if ts.tz != pd.UTC:
                return ts.tz_convert('UTC')
            return ts
        
        # If tz-naive, localize to UTC
        # (or use ref_index timezone if available)
        if ref_index is not None and hasattr(ref_index, 'tz') and ref_index.tz is not None:
            # Use ref_index timezone first, then convert to UTC
            ts = ts.tz_localize(ref_index.tz)
            return ts.tz_convert('UTC')
        
        # Default: localize to UTC
        return ts.tz_localize('UTC')
    
    except Exception as e:
        logger.error(f"Failed to normalize timestamp {ts}: {e}")
        raise ValueError(f"Cannot convert timestamp to UTC: {ts}") from e


def ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure DataFrame index is UTC tz-aware.
    
    Args:
        df: Input DataFrame with datetime index
    
    Returns:
        pd.DataFrame: DataFrame with UTC tz-aware index
    
    Raises:
        ValueError: If index is not datetime or conversion fails
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"Index must be DatetimeIndex, got {type(df.index)}")
    
    try:
        # If already tz-aware
        if df.index.tz is not None:
            # Convert to UTC if not already
            if df.index.tz != pd.UTC:
                df = df.copy()
                df.index = df.index.tz_convert('UTC')
            return df
        
        # If tz-naive, localize to UTC
        df = df.copy()
        df.index = df.index.tz_localize('UTC')
        return df
    
    except Exception as e:
        logger.error(f"Failed to normalize DataFrame index: {e}")
        raise ValueError("Cannot convert DataFrame index to UTC") from e


def normalize_comparison(
    left: Union[pd.DatetimeIndex, pd.Series],
    right: Union[pd.Timestamp, str, int, float]
) -> tuple:
    """
    Normalize both sides of a datetime comparison to UTC tz-aware.
    
    Args:
        left: Left side (usually DataFrame index or Series)
        right: Right side (usually scalar timestamp)
    
    Returns:
        tuple: (left_normalized, right_normalized)
    
    Example:
        >>> left, right = normalize_comparison(df.index, some_timestamp)
        >>> mask = left >= right  # No "Invalid comparison" error
    """
    # Handle left side (index or Series)
    if isinstance(left, pd.DatetimeIndex):
        if left.tz is None:
            left = left.tz_localize('UTC')
        elif left.tz != pd.UTC:
            left = left.tz_convert('UTC')
    elif isinstance(left, pd.Series):
        if left.dtype == 'datetime64[ns]':
            left = pd.to_datetime(left, utc=True)
    
    # Handle right side (scalar)
    right = ensure_utc_timestamp(right, ref_index=left if isinstance(left, pd.DatetimeIndex) else None)
    
    return left, right
