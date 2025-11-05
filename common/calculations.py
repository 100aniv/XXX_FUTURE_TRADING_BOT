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
    target_volatility: float = 0.015,
    strategy_metrics: dict = None,
    signal_confidence: float = None,
    ensemble_weight: float = None,
    current_dd: float = 0.0
) -> int:
    """
    다차원 레버리지 결정 (상용 프로그램 방식)
    
    고려 요소 (우선순위 순):
    1. 변동성 (ATR) - 기본 레버리지
    2. 전략 성과 (Sharpe, Winrate) - 리스크 조정 수익
    3. 신뢰도 (Signal Confidence) - 신호 품질
    4. 앙상블 가중치 - 전략 중요도
    5. 포트폴리오 상태 (Drawdown) - 손실 보호
    6. 거래 수 (샘플 신뢰도)
    
    Args:
        atr_pct: ATR % (예: 0.02 = 2%)
        min_leverage: 최소 레버리지
        max_leverage: 최대 레버리지
        target_volatility: 목표 변동성 (기본: 0.015 = 1.5%)
        strategy_metrics: {'sharpe': float, 'winrate': float, 'trades': int} (선택)
        signal_confidence: 신호 신뢰도 0-1 (선택)
        ensemble_weight: 앙상블 가중치 0-1 (선택)
        current_dd: 현재 Drawdown % (선택)
    
    Returns:
        int: 최종 레버리지
        
    Examples:
        >>> # 단순 변동성 (하위 호환)
        >>> leverage_suggestion(0.02, 2, 20)
        2
        
        >>> # 다차원 계산
        >>> leverage_suggestion(
        ...     atr_pct=0.02,
        ...     min_leverage=2, max_leverage=20,
        ...     strategy_metrics={'sharpe': 1.2, 'winrate': 0.60, 'trades': 50},
        ...     signal_confidence=0.85,
        ...     ensemble_weight=0.4,
        ...     current_dd=3.0
        ... )
        3  # 우수한 전략 → 레버리지 증가
    """
    if atr_pct <= 0:
        return min_leverage
    
    # 1. 기본 레버리지 (변동성 기반)
    base_lev = target_volatility / atr_pct
    base_lev = max(min_leverage, min(max_leverage, base_lev))
    
    # 단순 모드 (하위 호환)
    if strategy_metrics is None:
        return int(math.floor(base_lev))
    
    # 2. Sharpe Ratio 배수
    sharpe = strategy_metrics.get('sharpe', 0.0)
    if sharpe > 1.5:
        sharpe_mult = 1.3
    elif sharpe > 0.8:
        sharpe_mult = 1.1
    elif sharpe > 0.3:
        sharpe_mult = 1.0
    elif sharpe > 0:
        sharpe_mult = 0.8
    else:
        sharpe_mult = 0.6
    
    # 3. Winrate 배수
    winrate = strategy_metrics.get('winrate', 0.5)
    if winrate > 0.65:
        wr_mult = 1.2
    elif winrate > 0.55:
        wr_mult = 1.1
    elif winrate > 0.45:
        wr_mult = 1.0
    else:
        wr_mult = 0.8
    
    # 4. 신뢰도 배수
    if signal_confidence is not None:
        confidence_mult = 0.7 + (signal_confidence * 0.6)  # 0.7 ~ 1.3
    else:
        confidence_mult = 1.0
    
    # 5. 앙상블 가중치 배수
    if ensemble_weight is not None:
        ensemble_mult = 0.8 + (ensemble_weight * 0.4)  # 0.8 ~ 1.2
    else:
        ensemble_mult = 1.0
    
    # 6. Drawdown 페널티
    if current_dd > 15:
        dd_mult = 0.5
    elif current_dd > 10:
        dd_mult = 0.7
    elif current_dd > 5:
        dd_mult = 0.9
    else:
        dd_mult = 1.0
    
    # 7. 거래 수 신뢰도
    trades = strategy_metrics.get('trades', 0)
    if trades < 10:
        sample_mult = 0.7
    elif trades < 30:
        sample_mult = 0.9
    else:
        sample_mult = 1.0
    
    # 최종 레버리지
    final_lev = base_lev \
        * sharpe_mult \
        * wr_mult \
        * confidence_mult \
        * ensemble_mult \
        * dd_mult \
        * sample_mult
    
    # 범위 제한
    final_lev = max(min_leverage, min(max_leverage, int(final_lev)))
    
    return final_lev


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
