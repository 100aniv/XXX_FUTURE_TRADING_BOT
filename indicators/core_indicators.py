#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Indicators Module
======================
TA 지표 계산 함수들 (1000억 벌 프로그램 표준)

⚠️ PR4 표준화 (2025-11-02):
- 타입힌트 강화
- NaN 정책 명시
- 최소 데이터 요구사항 문서화
- 출력 스키마 표준화

## 인터페이스 계약

### 입력
- **필수 컬럼**: `open, high, low, close, volume, time`
- **타임존**: UTC (tz-naive 허용)
- **정렬**: time 오름차순
- **결측치**: 허용하지 않음 (호출 전 정제 필요)

### 출력
- **불변성**: 입력 DataFrame 수정 안함 (복사본 반환 또는 새 컬럼 추가)
- **인덱스 유지**: 입력과 동일한 인덱스
- **NaN 전파**: 초기 `length-1`개 행은 NaN (정상)
  - 예: `sma(df, 20)` → 처음 19개 행은 NaN
  - 시그널 생성 시 `min_bars_for_signal`로 제어

### 최소 데이터
각 지표별 최소 요구 데이터:
- `sma(length=N)`: N개 행
- `ema(length=N)`: N개 행 (warmup 포함하면 2*N 권장)
- `rsi(length=N)`: N+1개 행
- `macd(fast, slow, signal)`: slow + signal 개 행
- `atr(length=N)`: N+1개 행 (shift 고려)

### NaN 처리 정책
1. **지표 계산**: NaN 전파 허용 (pandas rolling 기본 동작)
2. **시그널 생성**: `dropna()` 또는 `min_bars_for_signal` 체크 필수
3. **전략 실행**: NaN 행 건너뜀

## 참고
- REFACTORING_indicators_v1.md
- REFACTORING_signals_v1.md

주요 기능:
- ema(): 지수이동평균
- rsi(): 상대강도지수
- macd(): MACD 지표
- bb(): 볼린저밴드
- atr(): Average True Range
- add_indicators(): DataFrame에 모든 지표 추가
- regime(): 시장 레짐 판단

TO-BE:
  나중에 지표가 많아지면 trend.py, momentum.py, volatility.py로 분리
"""
import numpy as np
import pandas as pd


# ============================================
# Trend Indicators (추세 지표)
# ============================================

def ema(series: pd.Series, length: int) -> pd.Series:
    """
    지수이동평균 (Exponential Moving Average)
    
    Args:
        series: 가격 시리즈 (보통 close)
        length: 기간
    
    Returns:
        pd.Series: EMA 값
        
    Examples:
        >>> df['ema_20'] = ema(df['close'], 20)
    """
    return series.ewm(span=length, adjust=False).mean()


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    MACD (Moving Average Convergence Divergence)
    
    Args:
        df: DataFrame (close 컬럼 필요)
        fast: 빠른 EMA 기간
        slow: 느린 EMA 기간
        signal: 시그널 라인 기간
    
    Returns:
        pd.DataFrame: macd, macd_signal, macd_hist 컬럼 추가
        
    Examples:
        >>> df = macd(df)
        >>> print(df[['macd', 'macd_signal', 'macd_hist']])
    """
    ema_fast = ema(df["close"], fast)
    ema_slow = ema(df["close"], slow)
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = ema(df["macd"], signal)
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


# ============================================
# Momentum Indicators (모멘텀 지표)
# ============================================

def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index)
    
    Args:
        series: 가격 시리즈 (보통 close)
        length: 기간 (기본 14)
    
    Returns:
        pd.Series: RSI 값 (0-100)
        
    Examples:
        >>> df['rsi_14'] = rsi(df['close'], 14)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ============================================
# Volatility Indicators (변동성 지표)
# ============================================

def bb(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    볼린저밴드 (Bollinger Bands)
    
    Args:
        df: DataFrame (close 컬럼 필요)
        length: 기간
        std: 표준편차 배수
    
    Returns:
        pd.DataFrame: bb_upper, bb_mid, bb_lower 컬럼 추가
        
    Examples:
        >>> df = bb(df)
        >>> print(df[['bb_upper', 'bb_mid', 'bb_lower']])
    """
    df["bb_mid"] = df["close"].rolling(window=length).mean()
    bb_std = df["close"].rolling(window=length).std()
    df["bb_upper"] = df["bb_mid"] + (bb_std * std)
    df["bb_lower"] = df["bb_mid"] - (bb_std * std)
    return df


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    ATR (Average True Range)
    
    Args:
        df: DataFrame (high, low, close 컬럼 필요)
        length: 기간
    
    Returns:
        pd.Series: ATR 값
        
    Examples:
        >>> df['atr_14'] = atr(df, 14)
    """
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(length).mean()


def donchian(df: pd.DataFrame, length: int = 20) -> pd.DataFrame:
    """
    Donchian Channel (동키안 채널)
    
    Args:
        df: DataFrame (high, low 컬럼 필요)
        length: 기간 (기본 20)
    
    Returns:
        pd.DataFrame: dc_upper, dc_mid, dc_lower 컬럼 추가
        
    Examples:
        >>> df = donchian(df)
        >>> print(df[['dc_upper', 'dc_mid', 'dc_lower']])
    
    Notes:
        - dc_upper: N일간 최고가
        - dc_lower: N일간 최저가
        - dc_mid: (dc_upper + dc_lower) / 2
    """
    df["dc_upper"] = df["high"].rolling(window=length).max()
    df["dc_lower"] = df["low"].rolling(window=length).min()
    df["dc_mid"] = (df["dc_upper"] + df["dc_lower"]) / 2
    return df


def compute_adx(
    df: pd.DataFrame, 
    period: int = 14, 
    high_col: str = "high", 
    low_col: str = "low", 
    close_col: str = "close"
) -> pd.DataFrame:
    """
    ADX (Average Directional Index) 계산
    
    ADX는 추세의 강도를 측정하는 지표로, 방향성은 알려주지 않고 추세의 강도만 측정합니다.
    - ADX > 25: 강한 추세 (Trend regime)
    - ADX <= 25: 약한 추세 또는 횡보 (Range regime)
    
    Args:
        df: DataFrame (high, low, close 컬럼 필요)
        period: ADX 계산 기간 (기본 14)
        high_col: 고가 컬럼명
        low_col: 저가 컬럼명
        close_col: 종가 컬럼명
    
    Returns:
        pd.DataFrame: plus_di_{period}, minus_di_{period}, adx_{period} 컬럼 추가
        
    Examples:
        >>> df = compute_adx(df, period=14)
        >>> print(df[['plus_di_14', 'minus_di_14', 'adx_14']])
        
    Notes:
        - +DI (Plus Directional Indicator): 상승 방향 강도
        - -DI (Minus Directional Indicator): 하락 방향 강도
        - ADX: 추세 강도 (0-100, 방향 무관)
        - 초기 period*2 행은 NaN (Wilder's smoothing 특성)
    """
    high = df[high_col]
    low = df[low_col]
    close = df[close_col]
    
    # True Range 계산 (ATR 계산과 동일)
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = np.max(ranges, axis=1)
    
    # Directional Movement 계산
    high_diff = high - high.shift()  # +DM 후보
    low_diff = low.shift() - low     # -DM 후보
    
    # +DM: 상승이 하락보다 크고 양수일 때
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    # -DM: 하락이 상승보다 크고 양수일 때
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
    
    # Wilder's smoothing (EMA와 유사하지만 다른 방식)
    # ATR_smooth = (ATR_prev * (n-1) + TR_current) / n
    # 초기값은 단순 평균
    alpha = 1.0 / period
    
    # ATR (smoothed TR)
    atr_smooth = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean()
    
    # Smoothed +DM, -DM
    plus_dm_smooth = pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean()
    minus_dm_smooth = pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean()
    
    # +DI, -DI 계산 (%)
    plus_di = 100 * (plus_dm_smooth / atr_smooth)
    minus_di = 100 * (minus_dm_smooth / atr_smooth)
    
    # DX (Directional Index)
    # Division by zero 방지: denominator가 0에 가까우면 0으로 처리
    di_sum = plus_di + minus_di
    di_diff = np.abs(plus_di - minus_di)
    dx = pd.Series(np.where(di_sum > 0.001, 100 * di_diff / di_sum, 0), index=df.index)
    
    # ADX (DX의 이동평균)
    adx = dx.ewm(alpha=alpha, adjust=False).mean()
    
    # 결과 컬럼 추가
    df[f"plus_di_{period}"] = plus_di
    df[f"minus_di_{period}"] = minus_di
    df[f"adx_{period}"] = adx
    
    return df


# ============================================
# Volume Indicators (거래량 지표)
# ============================================

def volume_ma(series: pd.Series, length: int = 30) -> pd.Series:
    """
    거래량 이동평균
    
    Args:
        series: 거래량 시리즈
        length: 기간
    
    Returns:
        pd.Series: 거래량 MA
        
    Examples:
        >>> df['vol_ma'] = volume_ma(df['volume'], 30)
    """
    return series.rolling(window=length).mean()


# ============================================
# 통합 함수
# ============================================

def add_indicators(
    df: pd.DataFrame,
    ema_fast: int = 20,
    ema_mid: int = 50,
    ema_slow: int = 200,
    rsi_len: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bb_len: int = 20,
    bb_std: float = 2.0,
    atr_len: int = 14,
    vol_ma_len: int = 30,
    dc_len: int = 20,
    use_adx: bool = False,
    adx_period: int = 14,
    drop_nan: bool = False  # PHASE27-7: NaN 제거 여부 (기본값 False로 변경)
) -> pd.DataFrame:
    """
    DataFrame에 모든 지표 추가
    
    Args:
        df: OHLCV DataFrame
        ema_fast/mid/slow: EMA 기간
        rsi_len: RSI 기간
        macd_fast/slow/signal: MACD 파라미터
        bb_len/std: BB 파라미터
        atr_len: ATR 기간
        vol_ma_len: 거래량 MA 기간
        dc_len: Donchian Channel 기간
        use_adx: ADX 계산 활성화 여부 (기본 False, 성능 고려)
        adx_period: ADX 계산 기간 (기본 14)
        drop_nan: NaN 제거 여부 (기본 False)
            PHASE27-7: Signal Parity를 위해 기본값 False로 변경
            Warmup 처리는 호출자가 min_bars_for_signal로 제어
    
    Returns:
        pd.DataFrame: 모든 지표가 추가된 DataFrame
        
    Examples:
        >>> df = add_indicators(df)
        >>> df = add_indicators(df, use_adx=True, adx_period=14)
        >>> df = add_indicators(df, drop_nan=True)  # Legacy 호환
        >>> print(df.columns)
        
    Notes:
        PHASE27-7: NaN 제거를 호출자에게 위임하여 Signal Parity 달성
        - Offline Scan: min_bars warmup 후 평가
        - Engine Replay: min_bars_for_signal 체크 후 신호 생성
    """
    # EMA
    df["ema_fast"] = ema(df["close"], ema_fast)
    df["ema_mid"] = ema(df["close"], ema_mid)
    df["ema_slow"] = ema(df["close"], ema_slow)
    
    # MACD
    df = macd(df, macd_fast, macd_slow, macd_signal)
    
    # RSI
    df["rsi"] = rsi(df["close"], rsi_len)
    
    # Bollinger Bands
    df = bb(df, bb_len, bb_std)
    
    # ATR
    df["atr"] = atr(df, atr_len)
    df[f"atr_{atr_len}"] = df["atr"]  # ⭐ PHASE28-9: 컬럼명 별칭 추가 (regime_detector 호환)
    
    # Donchian Channel
    df = donchian(df, dc_len)
    
    # Volume MA
    df["vol_ma"] = volume_ma(df["volume"], vol_ma_len)
    
    # ADX (선택적)
    if use_adx:
        df = compute_adx(df, period=adx_period)
    
    # PHASE27-7: NaN 제거 (선택적, 호출자가 결정)
    if drop_nan:
        return df.dropna().reset_index(drop=True)
    else:
        return df


# ============================================
# 시장 분석
# ============================================

def regime(row: pd.Series) -> str:
    """
    시장 레짐 판단 (상승장/하락장/횡보장/중립)
    
    Args:
        row: DataFrame의 한 행 (ema_fast, ema_mid, ema_slow, rsi 필요)
    
    Returns:
        str: "상승장", "하락장", "횡보장", "중립"
        
    Examples:
        >>> df['regime'] = df.apply(regime, axis=1)
    """
    up = row["ema_fast"] > row["ema_mid"] > row["ema_slow"]
    down = row["ema_fast"] < row["ema_mid"] < row["ema_slow"]
    
    if up:
        return "상승장"
    if down:
        return "하락장"
    if 45 <= row["rsi"] <= 55:
        return "횡보장"
    
    return "중립"


def detect_volatility_regime(df: pd.DataFrame, atr_col: str = 'atr', 
                             lookback: int = 20) -> str:
    """
    변동성 레짐 감지 (⭐ CRITICAL_ISSUES: 동적 SL 조정용)
    
    Args:
        df: DataFrame (atr 컬럼 필요)
        atr_col: ATR 컬럼명
        lookback: 분위수 계산 기간
    
    Returns:
        str: 'high_vol', 'neutral', 'low_vol'
        
    Examples:
        >>> vol_regime = detect_volatility_regime(df)
        >>> if vol_regime == 'high_vol':
        ...     # SL 더 넓게
    """
    if len(df) < lookback:
        return 'neutral'
    
    # ATR % 계산 (가격 대비 변동성)
    current_atr = df[atr_col].iloc[-1]
    current_close = df['close'].iloc[-1]
    atr_pct = (current_atr / current_close) * 100
    
    # 최근 lookback 기간 분위수 계산
    recent_atr_pct = []
    for i in range(-lookback, 0):
        if i >= -len(df):
            atr_val = df[atr_col].iloc[i]
            close_val = df['close'].iloc[i]
            recent_atr_pct.append((atr_val / close_val) * 100)
    
    if not recent_atr_pct:
        return 'neutral'
    
    import numpy as np
    q75 = np.percentile(recent_atr_pct, 75)
    q25 = np.percentile(recent_atr_pct, 25)
    
    if atr_pct > q75:
        return 'high_vol'
    elif atr_pct < q25:
        return 'low_vol'
    else:
        return 'neutral'
