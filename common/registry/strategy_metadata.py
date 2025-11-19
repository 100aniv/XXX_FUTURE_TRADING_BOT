#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Metadata
=================
PHASE19-1: 전략 메타데이터 표준

모든 전략은 이 메타데이터를 제공해야 한다.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class StrategyMetadata:
    """
    전략 메타데이터
    
    **필수 필드**:
    - strategy_name: 전략 고유 이름 (소문자, 공백 없음)
    - strategy_type: 전략 분류 (scalping, reversion, trend, breakout, swing, daytrade)
    - supported_symbols: 지원 심볼 리스트 (빈 리스트 = 모든 심볼)
    - supported_timeframes: 지원 타임프레임 리스트
    - version: 전략 버전 (SemVer 형식)
    - description: 전략 설명
    
    **사용 예시**:
    ```python
    metadata = StrategyMetadata(
        strategy_name='scalping',
        strategy_type='scalping',
        supported_symbols=['BTCUSDT', 'ETHUSDT'],
        supported_timeframes=['1m', '3m', '5m'],
        version='v3.0',
        description='3분봉 기반 EMA Fresh Trend'
    )
    ```
    """
    strategy_name: str
    strategy_type: str
    supported_symbols: List[str] = field(default_factory=list)
    supported_timeframes: List[str] = field(default_factory=list)
    version: str = 'v1.0'
    description: str = ''
    
    def validate(self) -> bool:
        """
        메타데이터 유효성 검사
        
        Returns:
            bool: 유효하면 True
        """
        if not self.strategy_name:
            return False
        if not isinstance(self.strategy_name, str):
            return False
        if not self.strategy_type:
            return False
        if not isinstance(self.strategy_type, str):
            return False
        if not isinstance(self.supported_symbols, list):
            return False
        if not isinstance(self.supported_timeframes, list):
            return False
        # 타임프레임이 비어있으면 경고 (모든 TF 지원으로 간주)
        # 하지만 유효성은 PASS
        return True
    
    def supports_symbol(self, symbol: str) -> bool:
        """
        특정 심볼 지원 여부
        
        Args:
            symbol: 심볼 (예: 'BTCUSDT')
        
        Returns:
            bool: 지원하면 True (빈 리스트는 모든 심볼 지원)
        """
        if not self.supported_symbols:
            return True  # 빈 리스트 = 모든 심볼 지원
        return symbol in self.supported_symbols
    
    def supports_timeframe(self, timeframe: str) -> bool:
        """
        특정 타임프레임 지원 여부
        
        Args:
            timeframe: 타임프레임 (예: '1m', '5m')
        
        Returns:
            bool: 지원하면 True (빈 리스트는 모든 TF 지원)
        """
        if not self.supported_timeframes:
            return True  # 빈 리스트 = 모든 타임프레임 지원
        return timeframe in self.supported_timeframes
    
    def __repr__(self) -> str:
        return (
            f"StrategyMetadata(name={self.strategy_name}, type={self.strategy_type}, "
            f"symbols={len(self.supported_symbols)}, timeframes={len(self.supported_timeframes)}, "
            f"version={self.version})"
        )
