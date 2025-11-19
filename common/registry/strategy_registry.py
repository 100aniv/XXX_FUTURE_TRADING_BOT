#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategy Registry
=================
PHASE19-1: 전략 중앙 레지스트리

전략 자동 스캔, 등록, 관리를 담당한다.
"""
import os
import sys
import importlib
import inspect
from typing import Dict, Type, List, Optional
from pathlib import Path
import logging

from .base_strategy import BaseStrategy
from .strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    전략 중앙 레지스트리
    
    **주요 기능**:
    - 전략 디렉토리 자동 스캔
    - BaseStrategy 상속 클래스 자동 등록
    - 전략 인스턴스 생성 및 관리
    - 메타데이터 조회
    
    **사용 예시**:
    ```python
    # 레지스트리 생성 및 스캔
    registry = StrategyRegistry()
    count = registry.scan()
    print(f"{count}개 전략 로드 완료")
    
    # 전략 인스턴스 생성
    strategy = registry.get('scalping', config={'rsi_oversold': 30})
    
    # 신호 계산
    signal = strategy.compute_signal(df)
    
    # 메타데이터 조회
    metadata = registry.get_metadata('scalping')
    all_metadata = registry.list_metadata()
    ```
    """
    
    def __init__(self, strategies_dir: str = 'strategies'):
        """
        레지스트리 초기화
        
        Args:
            strategies_dir: 전략 디렉토리 경로 (기본: 'strategies')
        """
        self.strategies_dir = strategies_dir
        self._registry: Dict[str, Type[BaseStrategy]] = {}
        self._metadata_cache: Dict[str, StrategyMetadata] = {}
    
    def scan(self) -> int:
        """
        전략 디렉토리 자동 스캔
        
        strategies/ 디렉토리 내부의 모든 .py 파일을 스캔하여
        BaseStrategy를 상속한 클래스를 자동 등록한다.
        
        Returns:
            int: 발견 및 등록된 전략 수
        
        **동작**:
        1. strategies/*.py 파일 탐색
        2. 모듈 동적 임포트
        3. BaseStrategy 상속 클래스 찾기
        4. 자동 등록
        """
        strategies_path = Path(self.strategies_dir)
        if not strategies_path.exists():
            logger.warning(f"⚠️  Strategies directory not found: {self.strategies_dir}")
            return 0
        
        count = 0
        for py_file in strategies_path.glob('*.py'):
            if py_file.name.startswith('__'):
                continue  # __init__.py, __pycache__ 등 제외
            if py_file.name == 'ensemble.py':
                continue  # PHASE19-2에서 재설계 예정
            
            module_name = py_file.stem
            try:
                # 모듈 동적 임포트
                full_module_name = f'{self.strategies_dir}.{module_name}'
                if full_module_name in sys.modules:
                    # 이미 로드된 모듈은 reload
                    module = importlib.reload(sys.modules[full_module_name])
                else:
                    module = importlib.import_module(full_module_name)
                
                # BaseStrategy 상속 클래스 찾기
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # BaseStrategy 자체는 제외
                    if obj is BaseStrategy:
                        continue
                    
                    # BaseStrategy를 상속하고, 해당 모듈에서 정의된 클래스인지 확인
                    if issubclass(obj, BaseStrategy) and obj.__module__ == module.__name__:
                        self.register(obj)
                        count += 1
                        logger.info(f"✅ Registered strategy: {name} from {module_name}.py")
            
            except Exception as e:
                logger.warning(f"⚠️  Failed to load strategy from {module_name}.py: {e}")
                # 디버깅용: 상세 에러 출력
                import traceback
                logger.debug(traceback.format_exc())
        
        logger.info(f"📊 Total strategies registered: {count}/{len(list(strategies_path.glob('*.py')))-1}")  # -1 for __init__.py
        return count
    
    def register(self, strategy_cls: Type[BaseStrategy]) -> None:
        """
        전략 클래스 수동 등록
        
        Args:
            strategy_cls: BaseStrategy를 상속한 전략 클래스
        
        **동작**:
        1. 임시 인스턴스 생성 (빈 config)
        2. metadata 추출 및 검증
        3. 레지스트리에 등록
        """
        try:
            # 임시 인스턴스 생성하여 metadata 가져오기
            temp_instance = strategy_cls({})
            metadata = temp_instance.metadata
            
            # 메타데이터 유효성 검사
            if not metadata.validate():
                logger.warning(f"⚠️  Invalid metadata for {strategy_cls.__name__}, skipping")
                return
            
            strategy_name = metadata.strategy_name
            
            # 중복 등록 확인
            if strategy_name in self._registry:
                logger.warning(f"⚠️  Strategy '{strategy_name}' already registered, overwriting")
            
            # 등록
            self._registry[strategy_name] = strategy_cls
            self._metadata_cache[strategy_name] = metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to register strategy {strategy_cls.__name__}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def get(self, name: str, config: Optional[Dict] = None) -> Optional[BaseStrategy]:
        """
        전략 인스턴스 반환
        
        Args:
            name: 전략 이름 (metadata.strategy_name)
            config: 전략 설정 (None이면 빈 딕셔너리)
        
        Returns:
            BaseStrategy 인스턴스 또는 None (전략이 없을 경우)
        
        **사용 예시**:
        ```python
        strategy = registry.get('scalping', {'rsi_oversold': 30})
        signal = strategy.compute_signal(df)
        ```
        """
        strategy_cls = self._registry.get(name)
        if not strategy_cls:
            logger.warning(f"⚠️  Strategy not found: {name}")
            return None
        
        try:
            return strategy_cls(config or {})
        except Exception as e:
            logger.error(f"❌ Failed to create strategy instance '{name}': {e}")
            return None
    
    def list_strategies(self) -> List[str]:
        """
        등록된 전략 이름 리스트 반환
        
        Returns:
            List[str]: 전략 이름 리스트
        """
        return list(self._registry.keys())
    
    def list_metadata(self) -> Dict[str, StrategyMetadata]:
        """
        전체 전략 메타데이터 반환
        
        Returns:
            Dict[str, StrategyMetadata]: {전략이름: 메타데이터}
        """
        return self._metadata_cache.copy()
    
    def get_metadata(self, name: str) -> Optional[StrategyMetadata]:
        """
        특정 전략의 메타데이터 반환
        
        Args:
            name: 전략 이름
        
        Returns:
            StrategyMetadata 또는 None
        """
        return self._metadata_cache.get(name)
    
    def count(self) -> int:
        """등록된 전략 수 반환"""
        return len(self._registry)
    
    def __repr__(self) -> str:
        strategies = ', '.join(self.list_strategies())
        return f"StrategyRegistry(strategies={self.count()}, names=[{strategies}])"
