#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funding Fee Calculator
=======================
선물 거래의 펀딩비 계산

바이낸스 기준:
- 8시간마다 펀딩비 정산 (00:00, 08:00, 16:00 UTC)
- 평균 펀딩비: 0.01% ~ 0.03%
- 포지션 가치 기준으로 차감/지급
"""
from datetime import datetime, timedelta
from typing import List, Dict


def calculate_funding_fee(
    position_value: float,
    funding_rate: float = 0.0001,  # 기본 0.01%
    holding_hours: int = 0
) -> float:
    """
    펀딩비 계산
    
    Args:
        position_value: 포지션 가치 (USDT)
        funding_rate: 펀딩 비율 (0.0001 = 0.01%)
        holding_hours: 포지션 보유 시간 (시간)
    
    Returns:
        float: 총 펀딩비 (음수 = 지불, 양수 = 수령)
    
    Example:
        >>> calculate_funding_fee(10000, 0.0001, 24)  # 10000 USDT, 24시간
        -3.0  # $3 지불 (24시간 = 3번 정산)
    """
    # 8시간마다 정산
    funding_periods = holding_hours // 8
    
    if funding_periods <= 0:
        return 0.0
    
    # 펀딩비 = 포지션가치 * 펀딩비율 * 정산횟수
    # LONG 포지션: 음수 (지불)
    # SHORT 포지션: 양수 (수령)
    total_funding = position_value * funding_rate * funding_periods
    
    return -total_funding  # LONG 기준 (음수)


def estimate_funding_for_trade(
    entry_time: datetime,
    exit_time: datetime,
    position_value: float,
    side: str = "LONG",
    avg_funding_rate: float = 0.0001
) -> Dict:
    """
    거래의 펀딩비 추정
    
    Args:
        entry_time: 진입 시간
        exit_time: 청산 시간
        position_value: 포지션 가치
        side: LONG or SHORT
        avg_funding_rate: 평균 펀딩 비율
    
    Returns:
        dict: {
            'funding_fee': float,  # 펀딩비
            'funding_periods': int,  # 정산 횟수
            'holding_hours': float  # 보유 시간
        }
    """
    holding_time = exit_time - entry_time
    holding_hours = holding_time.total_seconds() / 3600
    
    funding_periods = int(holding_hours // 8)
    
    # LONG: 펀딩비 지불 (음수)
    # SHORT: 펀딩비 수령 (양수) - 일반적으로
    multiplier = -1 if side == "LONG" else 1
    
    funding_fee = position_value * avg_funding_rate * funding_periods * multiplier
    
    return {
        'funding_fee': funding_fee,
        'funding_periods': funding_periods,
        'holding_hours': holding_hours
    }


if __name__ == '__main__':
    # 테스트
    print("="*60)
    print("펀딩비 계산 테스트")
    print("="*60)
    
    # 예시 1: 24시간 LONG 포지션
    fee1 = calculate_funding_fee(10000, 0.0001, 24)
    print(f"\n10,000 USDT, 24시간 보유:")
    print(f"  펀딩비: ${fee1:.2f}")
    print(f"  정산 횟수: {24//8}회")
    
    # 예시 2: 72시간 (3일)
    fee2 = calculate_funding_fee(5000, 0.0001, 72)
    print(f"\n5,000 USDT, 72시간 보유:")
    print(f"  펀딩비: ${fee2:.2f}")
    print(f"  정산 횟수: {72//8}회")
    
    # 예시 3: 실제 거래
    entry = datetime(2024, 1, 1, 10, 0)
    exit = datetime(2024, 1, 3, 18, 0)
    result = estimate_funding_for_trade(entry, exit, 8000, "LONG")
    print(f"\n실제 거래 (LONG):")
    print(f"  진입: {entry}")
    print(f"  청산: {exit}")
    print(f"  보유시간: {result['holding_hours']:.1f}시간")
    print(f"  정산횟수: {result['funding_periods']}회")
    print(f"  펀딩비: ${result['funding_fee']:.2f}")
