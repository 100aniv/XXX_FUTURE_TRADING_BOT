#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Strategy Interface
=======================
PHASE19-1: 전략 기본 인터페이스

모든 전략은 이 클래스를 상속해야 한다.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from .strategy_metadata import StrategyMetadata


class BaseStrategy(ABC):
    """
    전략 기본 인터페이스 (Abstract Base Class)
    
    **필수 구현 메서드**:
    - `metadata` 프로퍼티: StrategyMetadata 반환
    - `compute_signal(df)`: 신호 계산
    
    **사용 예시**:
    ```python
    class MyStrategy(BaseStrategy):
        @property
        def metadata(self):
            return StrategyMetadata(
                strategy_name='my_strategy',
                strategy_type='scalping',
                ...
            )
        
        def compute_signal(self, df):
            # 전략 로직
            return {'direction': 'LONG', ...}
    ```
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화
        
        Args:
            config: 전략 설정 (CFG에서 로드)
                    기존 signal_logic(df, config)의 config와 동일
        """
        self.config = config
        self._validate_metadata()
    
    @property
    @abstractmethod
    def metadata(self) -> StrategyMetadata:
        """
        전략 메타데이터 반환 (필수 구현)
        
        Returns:
            StrategyMetadata 인스턴스
        """
        pass
    
    @abstractmethod
    def compute_signal(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        신호 계산 (필수 구현)
        
        Args:
            df: OHLCV + 지표가 포함된 DataFrame
                기존 signal_logic(df, config)의 df와 동일
            **kwargs: 하위 호환성 위한 키워드 인자 (config= 등)
                      실제로는 self.config 사용 권장
        
        Returns:
            dict: 신호 정보
            {
                'direction': 'LONG' | 'SHORT' | None,
                'reason': str,
                'entry': float,
                'sl': float,
                'tp': float,
                ...
            }
        
        **참고**:
        - 기존 signal_logic() 함수를 호출하는 래퍼로 구현 가능
        - 예: `return signal_logic(df, self.config)`
        - **kwargs는 하위 호환성을 위한 것으로, self.config 사용 권장
        """
        pass
    
    def validate(self) -> bool:
        """
        전략 유효성 검사
        
        Returns:
            bool: 유효하면 True
        """
        return self.metadata.validate()
    
    def _validate_metadata(self):
        """
        메타데이터 유효성 검사 (초기화 시 자동 실행)
        
        Raises:
            ValueError: 메타데이터가 유효하지 않을 경우
        """
        if not self.validate():
            raise ValueError(
                f"Invalid metadata for strategy: {self.metadata.strategy_name if hasattr(self, 'metadata') else 'unknown'}"
            )
    
    def __repr__(self) -> str:
        try:
            metadata = self.metadata
            return f"{self.__class__.__name__}(name={metadata.strategy_name}, version={metadata.version})"
        except Exception:
            return f"{self.__class__.__name__}(metadata=unavailable)"
