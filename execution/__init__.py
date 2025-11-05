"""
Execution Module
================
백테스트, 페이퍼, 라이브 트레이딩 실행 엔진

- engine: 공통 트레이딩 루프 (engine.run)
- adapters: Broker, Clock 어댑터
- position_sizer: 포지션 크기 계산
- risk_manager: 리스크 관리

Feed는 collectors 모듈에서 가져옴
"""
from . import engine, adapters
from .position_sizer import PositionSizer
from .risk_manager import RiskManager

__all__ = [
    'engine',
    'adapters',
    'PositionSizer',
    'RiskManager'
]
