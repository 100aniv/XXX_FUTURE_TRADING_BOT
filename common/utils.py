#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common Utility Functions
========================
Signal Bot 공통 헬퍼 함수들

- bootstrap_history(): Binance에서 초기 히스토리 로드
- buffer_to_df(): deque 버퍼 → pandas DataFrame 변환
- make_streams(): WebSocket stream URL 생성
- qty_notional_margin(): 수량, 명목가치, 마진 계산
- maybe_regime_alert(): 시장 레짐 전환 알림
- parse_timeframe_ms(): 타임프레임을 밀리초로 변환
"""
from typing import List, Dict, Any, Optional
from collections import deque
import pandas as pd
import re
from binance.client import Client as BinanceClient

from common.calculations import position_size
from common.logger import setup_logger

logger = setup_logger('utils', log_type='application')


# ⚠️ DEPRECATED: bootstrap_history는 collectors.rest_collector로 이동됨
# 하위 호환성 유지를 위한 lazy wrapper (순환 import 방지)
def bootstrap_history(symbol: str, timeframe: str, lookback: int, buffers: Dict[str, deque]) -> None:
    from collectors.rest_collector import bootstrap_history as _bootstrap_history
    return _bootstrap_history(symbol, timeframe, lookback, buffers)


def buffer_to_df(symbol: str, buffers: Dict[str, deque]) -> pd.DataFrame:
    """
    deque 버퍼를 pandas DataFrame으로 변환
    
    Args:
        symbol: 심볼
        buffers: 버퍼 딕셔너리
    
    Returns:
        DataFrame: OHLCV 데이터
    """
    arr = list(buffers[symbol])
    return pd.DataFrame(arr) if arr else pd.DataFrame()


def make_streams(symbols: List[str], timeframes) -> str:
    """
    WebSocket stream URL 생성 (Multi-Timeframe 지원)
    
    Args:
        symbols: 심볼 리스트
        timeframes: 타임프레임 (str 또는 List[str])
    
    Returns:
        str: WebSocket stream path
    
    Examples:
        make_streams(['BTCUSDT'], '5m') → 'btcusdt@kline_5m'
        make_streams(['BTCUSDT'], ['3m', '5m']) → 'btcusdt@kline_3m/btcusdt@kline_5m'
    """
    # PR7-4: Multi-TF 지원
    if isinstance(timeframes, str):
        timeframes = [timeframes]
    
    parts = []
    for s in symbols:
        for tf in timeframes:
            parts.append(f"{s.lower()}@kline_{tf}")
    
    return "/".join(parts)


def qty_notional_margin(entry: float, sl: float, lev: int, equity_usdt: float, risk_per_trade: float):
    """
    수량, 명목가치, 마진 계산
    
    Args:
        entry: 진입가
        sl: 손절가
        lev: 레버리지
        equity_usdt: 계좌 자산 (USDT)
        risk_per_trade: 거래당 리스크 비율
    
    Returns:
        tuple: (qty, notional, margin)
    """
    qty, _ = position_size(entry, sl, equity_usdt, risk_per_trade)
    notional = qty * entry
    margin = notional / max(lev, 1)
    return qty, notional, margin


def maybe_regime_alert(symbol: str, reg: str, last_regime: Dict[str, str], enable_regime_alert: bool, tg_callback):
    """
    시장 레짐 전환 알림
    
    Args:
        symbol: 심볼
        reg: 현재 레짐
        last_regime: 마지막 레짐 딕셔너리 (심볼별)
        enable_regime_alert: 알림 활성화 여부
        tg_callback: 텔레그램 전송 함수
    """
    if not enable_regime_alert:
        return
    
    last_reg = last_regime.get(symbol)
    if last_reg is None:
        last_regime[symbol] = reg
        return
    
    # 모든 레짐 전환 알림 (간소화)
    if reg != last_reg:
        last_regime[symbol] = reg
        emoji = {"상승장":"📈", "하락장":"📉", "횡보장":"⚪", "중립":"🟡"}.get(reg, "🟡")
        tg_callback(f"{symbol} 시장 전환: {last_reg} → {reg} {emoji}")


def parse_timeframe_ms(timeframe: str) -> int:
    """
    타임프레임을 밀리초로 동적 변환
    
    Args:
        timeframe: 타임프레임 문자열 (예: "5m", "1h", "4h", "1d")
    
    Returns:
        int: 밀리초 단위 시간
    
    Examples:
        >>> parse_timeframe_ms("5m")
        300000
        >>> parse_timeframe_ms("4h")
        14400000
        >>> parse_timeframe_ms("1d")
        86400000
    """
    if not timeframe:
        logger.warning("⚠️ 타임프레임이 비어있음, 기본값(5m) 사용")
        return 300000  # 기본 5분
    
    tf = str(timeframe).strip().lower()
    
    # 숫자와 단위 추출
    match = re.match(r'(\d+)([mhdw])', tf)
    if not match:
        logger.warning(f"⚠️ 알 수 없는 타임프레임: {timeframe}, 기본값(5m) 사용")
        return 300000
    
    value = int(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        'm': 60 * 1000,                    # 분
        'h': 60 * 60 * 1000,               # 시간
        'd': 24 * 60 * 60 * 1000,          # 일
        'w': 7 * 24 * 60 * 60 * 1000       # 주
    }
    
    return value * multipliers.get(unit, 60 * 1000)
