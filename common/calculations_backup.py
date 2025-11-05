#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
거래 계산 유틸리티
==================
거래 관련 계산 함수 모음
- Signal Bot, Trading Bot 공통 사용

주요 기능:
- round_tick(): 가격 반올림 (tick size)
- position_size(): 포지션 크기 계산 (리스크 기반)
- leverage_suggestion(): 레버리지 제안 (ATR 기반)
- price_levels(): 진입/손절/익절 가격 계산
"""
import math
from typing import Tuple


def round_tick(symbol: str, price: float) -> float:
    """
    심볼별 가격 반올림 (tick size)
    
    Args:
        symbol: 거래 심볼 (예: BTCUSDT)
        price: 원본 가격
    
    Returns:
        float: 반올림된 가격
        
    Examples:
        >>> round_tick("BTCUSDT", 50123.456)
        50123.46  # BTC는 0.01 단위
        
        >>> round_tick("ETHUSDT", 3456.789)
        3456.79  # ETH는 0.01 단위
    """
    s = symbol.upper()
    step = 0.01
    
    if "BTC" in s:
        step = 0.01
    elif "ETH" in s or "BNB" in s or "SOL" in s:
        step = 0.01
    elif "XRP" in s or "ADA" in s or "DOGE" in s:
        if price < 1:
            step = 0.0001
        else:
            step = 0.001
    else:
        step = 0.001
    
    return round(price / step) * step


def position_size(
    entry: float,
    sl: float,
    equity: float,
    risk_frac: float
) -> Tuple[float, float]:
    """
    포지션 크기 계산 (리스크 기반)
    
    Args:
        entry: 진입 가격
        sl: 손절 가격
        equity: 계좌 자산 (USDT)
        risk_frac: 리스크 비율 (0.01 = 1%)
    
    Returns:
        tuple: (수량, 리스크 금액)
        
    Examples:
        >>> position_size(100, 95, 10000, 0.01)
        (20.0, 100.0)  # 수량 20개, 리스크 $100
    """
    risk_usdt = equity * risk_frac
    dist = abs(entry - sl)
    
    if dist <= 0:
        return 0.0, 0.0
    
    qty = risk_usdt / dist
    return qty, risk_usdt


def leverage_suggestion(
    atr_pct: float,
    min_leverage: int,
    max_leverage: int,
    target_volatility: float = 0.015
) -> int:
    """
    레버리지 제안 (ATR 기반)
    
    변동성이 높으면 낮은 레버리지
    변동성이 낮으면 높은 레버리지
    
    Args:
        atr_pct: ATR % (예: 0.02 = 2%)
        min_leverage: 최소 레버리지 (config.yml 필수)
        max_leverage: 최대 레버리지 (config.yml 필수)
        target_volatility: 목표 변동성 (선택적, 기본: 0.015 = 1.5%)
    
    Returns:
        int: 제안 레버리지
        
    Examples:
        >>> leverage_suggestion(0.01)  # 1% 변동성
        10  # 높은 레버리지
        
        >>> leverage_suggestion(0.03)  # 3% 변동성
        2   # 낮은 레버리지
    """
    if atr_pct <= 0:
        return min_leverage
    
    lev = max(min_leverage, min(max_leverage, math.floor(target_volatility / atr_pct)))
    return int(lev)


def price_levels(
    side: str,
    price: float,
    atr: float,
    rr: float,
    atr_mult_sl: float = 1.5
) -> Tuple[float, float, float]:
    """
    진입/손절/익절 가격 계산
    
    Args:
        side: "LONG" 또는 "SHORT"
        price: 현재 가격
        atr: ATR 값
        rr: Risk/Reward 비율
        atr_mult_sl: 손절 ATR 배수
    
    Returns:
        tuple: (진입가, 손절가, 익절가)
        
    Examples:
        >>> price_levels("LONG", 100, 2, 2.0)
        (100, 97.0, 106.0)  # 진입 100, 손절 97, 익절 106
    """
    if side == "LONG":
        entry = price
        sl = price - atr_mult_sl * atr
        tp = price + rr * (entry - sl)
    else:  # SHORT
        entry = price
        sl = price + atr_mult_sl * atr
        tp = price - rr * (sl - entry)
    
    return entry, sl, tp


def tp_from_rr(signal_info: dict, rr: float) -> float:
    """
    RR (Risk/Reward) 기반 TP 계산
    
    Args:
        signal_info: 신호 정보 딕셔너리 (entry, sl, side 포함)
        rr: Risk/Reward 비율
    
    Returns:
        float: TP 가격
        
    Examples:
        >>> tp_from_rr({"entry": 100, "sl": 95, "side": "LONG"}, 2.0)
        110.0  # LONG: 100 + (100-95) * 2 = 110
        
        >>> tp_from_rr({"entry": 100, "sl": 105, "side": "SHORT"}, 2.0)
        90.0   # SHORT: 100 - (105-100) * 2 = 90
    """
    entry = signal_info.get("entry", 0)
    sl = signal_info.get("sl", 0)
    side = signal_info.get("side", "LONG")
    
    risk_dist = abs(entry - sl)
    
    if side == "LONG":
        return entry + (risk_dist * rr)
    else:  # SHORT
        return entry - (risk_dist * rr)


def calculate_funding_fee(
    position_value: float,
    holding_hours: float,
    funding_rate: float = 0.0001,  # 0.01%
    side: str = "LONG"
) -> float:
    """
    선물 펀딩비 계산 (바이낸스 기준)
    
    Args:
        position_value: 포지션 가치 (USDT)
        holding_hours: 보유 시간 (시간)
        funding_rate: 펀딩 비율 (기본 0.01%)
        side: LONG or SHORT
    
    Returns:
        float: 펀딩비 (음수 = 지불, 양수 = 수령)
    
    Example:
        >>> calculate_funding_fee(10000, 24, 0.0001, "LONG")
        -3.0  # LONG 포지션, 24시간 = 3번 정산, $3 지불
    """
    # 8시간마다 정산
    funding_periods = int(holding_hours // 8)
    
    if funding_periods <= 0:
        return 0.0
    
    # LONG: 펀딩비 지불 (음수)
    # SHORT: 펀딩비 수령 (양수) - 일반적으로
    multiplier = -1 if side == "LONG" else 1
    
    total_funding = position_value * funding_rate * funding_periods * multiplier
    
    return total_funding
