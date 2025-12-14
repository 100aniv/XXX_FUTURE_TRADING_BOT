"""
Strategies Module
=================
각 전략의 신호 생성 로직을 담당합니다.

전략:
- scalping: 스캘핑 전략 (1분/3분) - BB 터치 + EMA 정렬
- swing_bb: 스윙 BB 반등 전략 (5분) - BB 반등 + EMA 정렬 (⭐ PHASE9-5: 기존 scalping 로직 분리)
- daytrade: 단타 전략 (5분) - 레짐 기반 + EMA 정렬
- swing: 스윙 전략 (15분) - 레짐 기반 + EMA 정렬
- trend: 추세 전략 (1시간) - EMA 크로스 + MACD
- reversion: 반전 전략 (5분) - RSI 극단 + BB 터치
- breakout: 돌파 전략 (15분) - Donchian 돌파 + ATR 급등
- ensemble: 앙상블 통합 전략 (포트폴리오 매니저) ✅
"""
from typing import Dict, Any
from common.logger import setup_logger

from . import scalping
from . import swing_bb
from . import daytrade
from . import swing
from . import trend
from . import reversion
from . import breakout
from . import ensemble

# PHASE23-2: V2 전략 import
from .core import scalping_v3
from .research import volatility_breakout_v2
from .research import mean_reversion_v2
from .research import trend_follow_v2
from .research import volume_based_v2

# PHASE27-3: Baseline 전략 import
from . import btc5m_baseline_v1

# PHASE28-7: Baseline V2 전략 import
from . import btc5m_baseline_v2

# PHASE29-1: Baseline V3 전략 import
from . import btc5m_baseline_v3

# PHASE29-3.1: Baseline V4 전략 import
from . import btc5m_baseline_v4

# PHASE30-1: Core V1 전략 import
from . import btc15m_core_v1

# PHASE30-3: Core V2 전략 import
from . import btc15m_core_v2

# PHASE35-1: Ensemble V1 전략 import
from . import phase35_ensemble_v1

logger = setup_logger('strategies', log_type='application')


def get_all_strategies() -> Dict[str, Any]:
    """
    전체 전략 모듈 딕셔너리 반환 (하드코딩 제거)
    
    Returns:
        전략명: 모듈 딕셔너리
    
    Examples:
        >>> strategies = get_all_strategies()
        >>> print(strategies.keys())
        dict_keys(['scalping', 'swing_bb', 'daytrade', 'swing', 'trend', 'reversion', 'breakout'])
    """
    return {
        # Legacy strategies
        'scalping': scalping,
        'swing_bb': swing_bb,
        'daytrade': daytrade,
        'swing': swing,
        'trend': trend,
        'reversion': reversion,
        'breakout': breakout,
        # V2 strategies (PHASE23-2)
        'scalping_v3': scalping_v3,
        'volatility_breakout_v2': volatility_breakout_v2,
        'mean_reversion_v2': mean_reversion_v2,
        'trend_follow_v2': trend_follow_v2,
        'volume_based_v2': volume_based_v2,
        # PHASE27-3: Baseline 전략
        'btc5m_baseline_v1': btc5m_baseline_v1,
        # PHASE28-7: Baseline V2 전략
        'btc5m_baseline_v2': btc5m_baseline_v2,
        # PHASE29-1: Baseline V3 전략
        'btc5m_baseline_v3': btc5m_baseline_v3,
        # PHASE29-3.1: Baseline V4 전략
        'btc5m_baseline_v4': btc5m_baseline_v4,
        # PHASE30-1: Core V1 전략
        'btc15m_core_v1': btc15m_core_v1,
        # PHASE30-3: Core V2 전략 (PHASE32-1: 등록)
        'btc15m_core_v2': btc15m_core_v2,
        # PHASE35-1: Ensemble V1 전략
        'phase35_ensemble_v1': phase35_ensemble_v1
    }


def load_strategies(config: dict, all_strategies: dict = None) -> Dict[str, Dict[str, Any]]:
    """
    설정 기반 전략 로딩 (PHASE23-2: BaseStrategy 인스턴스 반환)
    
    Args:
        config: 전체 설정 딕셔너리
        all_strategies: 전체 전략 모듈 딕셔너리 (None이면 get_all_strategies() 사용)
    
    Returns:
        로드된 전략 딕셔너리
        {
            "strategy_name": {
                "instance": <BaseStrategy 인스턴스>,
                "params": {<strategy-specific params>},
                "enabled": True
            },
            ...
        }
    """
    import os
    from common.registry.base_strategy import BaseStrategy
    
    # 전략 딕셔너리 자동 로드
    if all_strategies is None:
        all_strategies = get_all_strategies()
    
    def _get_strategy_class(module, strategy_name: str):
        """
        모듈에서 BaseStrategy 클래스 찾기
        
        Args:
            module: 전략 모듈
            strategy_name: 전략 이름
        
        Returns:
            BaseStrategy 클래스 또는 None
        """
        # 1) 전략명 기반 클래스 이름 직접 시도 (예: btc5m_baseline_v1 -> BTC5mBaselineV1)
        # 일반적인 naming convention을 시도
        class_name_candidates = [
            # Special case: btc5m_baseline_v1/v2 -> BTC5mBaselineV1/V2 (대문자 약어 유지)
            'BTC5mBaselineV1' if strategy_name == 'btc5m_baseline_v1' else None,
            'BTC5mBaselineV2' if strategy_name == 'btc5m_baseline_v2' else None,
            # CamelCase (btc5m_baseline_v1 -> Btc5mBaselineV1)
            ''.join(word.capitalize() for word in strategy_name.split('_')),
            # Pascal case with underscore preserved (btc5m_baseline_v1 -> Btc5mBaselineV1)
            strategy_name.title().replace('_', ''),
            # Simple capitalize
            strategy_name.capitalize(),
            # Upper first letter of each word (btc5m_baseline_v1 -> Btc5m_Baseline_V1)
            strategy_name.title(),
        ]
        
        # None 제거
        class_name_candidates = [c for c in class_name_candidates if c is not None]
        
        for class_name in class_name_candidates:
            if hasattr(module, class_name):
                attr = getattr(module, class_name)
                if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr is not BaseStrategy:
                    logger.info(f"✅ [PHASE27-5A] {strategy_name} 클래스 찾기 성공: {class_name}")
                    return attr
        
        # 2) 모듈 내의 모든 클래스 탐색 (폴백)
        for attr_name in dir(module):
            if attr_name.startswith('_'):  # private 속성 제외
                continue
            try:
                attr = getattr(module, attr_name, None)
                if attr is None:
                    continue
                # BaseStrategy 상속 클래스 찾기
                if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr is not BaseStrategy:
                    logger.info(f"✅ [PHASE27-5A] {strategy_name} 클래스 탐색 성공: {attr_name}")
                    return attr
            except (TypeError, AttributeError):
                # getattr 또는 issubclass에서 발생할 수 있는 예외 무시
                continue
        
        logger.warning(f"⚠️  [PHASE27-5A] {strategy_name}에서 BaseStrategy 클래스를 찾을 수 없음")
        return None
    
    strategies = {}
    
    # 전략 설정 (환경변수 우선)
    strategy_cfg = config.get('strategy', {})
    use_ensemble = strategy_cfg.get('use_ensemble', True)
    selector = os.getenv('STRATEGY_SELECTOR', strategy_cfg.get('selector', None))
    
    # 단일 전략 모드: selector로 1개만 선택
    if not use_ensemble and selector:
        logger.info(f"🔍 [PHASE23-2] 단일 전략 모드: selector={selector}")
        if selector in all_strategies:
            # PHASE23-2: BaseStrategy 인스턴스 생성
            strategies_cfg = config.get('strategies', {})
            logger.info(f"🔍 [PHASE23-2 DEBUG] strategies_cfg keys: {list(strategies_cfg.keys())}")
            strategy_config = strategies_cfg.get(selector, {})
            
            # PHASE29-2C-R: params 키가 없으면 strategy_config 전체를 파라미터로 간주
            if 'params' in strategy_config:
                strategy_params = strategy_config['params']
            else:
                # 메타 키 제외한 나머지를 파라미터로 사용
                known_meta_keys = {'enabled', 'timeframe', 'filters'}
                strategy_params = {k: v for k, v in strategy_config.items() if k not in known_meta_keys}
            
            # PHASE35-2: Ensemble strategies need full strategy config preserved for nested access
            if selector == 'phase35_ensemble_v1':
                # Preserve entire strategy section from config for ensemble to access nested configs
                strategy_params['strategy'] = config.get('strategy', {})
            
            logger.info(f"🔍 [PHASE29-2C-R DEBUG] {selector}: strategy_config keys={list(strategy_config.keys())}, params keys={list(strategy_params.keys())}")
            logger.info(f"🔍 [PHASE29-2C-R DEBUG] {selector}: sample params={dict(list(strategy_params.items())[:3])}")
            
            # 모듈에서 BaseStrategy 클래스 찾기
            strategy_module = all_strategies[selector]
            strategy_class = _get_strategy_class(strategy_module, selector)
            
            if strategy_class:
                # Config 병합: 글로벌 config + 전략별 params
                merged_config = {**config, **strategy_params}
                instance = strategy_class(config=merged_config)
                logger.info(f"✅ [PHASE23-2] {selector} 인스턴스 생성 성공: {type(instance).__name__}")
                
                # PHASE29-3: Deprecated 전략 체크
                if hasattr(instance, 'deprecated') and instance.deprecated:
                    logger.warning(f"⚠️  [PHASE29-3] 전략 '{selector}'는 DEPRECATED 상태입니다.")
                    logger.warning(f"    이유: {getattr(instance, 'deprecation_reason', 'No reason provided')}")
                    logger.warning(f"    이 전략은 로드되지 않습니다. 다른 전략을 선택하세요.")
                    return {}  # 빈 딕셔너리 반환으로 전략 로드 중단
            else:
                # 폴백: 모듈 그대로 사용 (legacy)
                logger.warning(f"⚠️  [PHASE23-2] {selector}에서 BaseStrategy 클래스 찾을 수 없음, 모듈 그대로 사용")
                instance = strategy_module
            
            strategies[selector] = {
                "instance": instance,
                "params": strategy_params,
                "enabled": True
            }
            logger.info(f"✅ 단일 전략 모드: {selector}")
        else:
            logger.error(f"❌ 전략 '{selector}' 없음, daytrade로 fallback")
            strategies_cfg = config.get('strategies', {})
            daytrade_config = strategies_cfg.get('daytrade', {})
            
            # PHASE29-2C-R: params 키가 없으면 config 전체를 파라미터로 간주
            if 'params' in daytrade_config:
                strategy_params = daytrade_config['params']
            else:
                known_meta_keys = {'enabled', 'timeframe', 'filters'}
                strategy_params = {k: v for k, v in daytrade_config.items() if k not in known_meta_keys}
            
            strategy_module = all_strategies.get('daytrade')
            strategy_class = _get_strategy_class(strategy_module, 'daytrade')
            if strategy_class:
                merged_config = {**config, **strategy_params}
                instance = strategy_class(config=merged_config)
            else:
                instance = strategy_module
            
            strategies['daytrade'] = {
                "instance": instance,
                "params": strategy_params,
                "enabled": True
            }
    
    # 앙상블 모드: enabled=true인 모든 전략 로드
    else:
        strategies_cfg = config.get('strategies', {})
        logger.info(f"🔍 [PHASE23-2 DEBUG] strategies_cfg keys: {list(strategies_cfg.keys())}")
        
        # ⭐ PHASE35-1-FIX: Strict Mode - 요청된 전략 목록 추적
        requested_strategies = [name for name, cfg in strategies_cfg.items() if cfg.get('enabled', False)]
        loaded_strategies_names = []
        
        for name, module in all_strategies.items():
            strategy_config = strategies_cfg.get(name, {})
            enabled = strategy_config.get('enabled', True)
            
            # PHASE29-2C-R: params 키가 없으면 strategy_config 전체를 파라미터로 간주
            if 'params' in strategy_config:
                params = strategy_config['params']
            else:
                # 메타 키 제외한 나머지를 파라미터로 사용
                known_meta_keys = {'enabled', 'timeframe', 'filters'}
                params = {k: v for k, v in strategy_config.items() if k not in known_meta_keys}
            
            logger.info(f"🔍 [PHASE29-2C-R DEBUG] {name}: enabled={enabled}, params keys={list(params.keys())}")
            
            if enabled:
                # PHASE23-2: BaseStrategy 인스턴스 생성
                strategy_class = _get_strategy_class(module, name)
                
                if strategy_class:
                    merged_config = {**config, **params}
                    instance = strategy_class(config=merged_config)
                    logger.info(f"✅ [PHASE23-2] {name} 인스턴스 생성 성공: {type(instance).__name__}")
                    
                    # PHASE29-3: Deprecated 전략 체크
                    if hasattr(instance, 'deprecated') and instance.deprecated:
                        logger.warning(f"⚠️  [PHASE29-3] 전략 '{name}'는 DEPRECATED 상태로 앙상블에서 제외됩니다.")
                        logger.warning(f"    이유: {getattr(instance, 'deprecation_reason', 'No reason provided')}")
                        continue  # 이 전략을 스킵하고 다음 전략으로
                else:
                    # 폴백: 모듈 그대로 사용 (legacy)
                    logger.warning(f"⚠️  [PHASE23-2] {name}에서 BaseStrategy 클래스 찾을 수 없음, 모듈 그대로 사용")
                    instance = module
                
                if enabled:
                    strategies[name] = {
                        "instance": instance,
                        "params": params,
                        "enabled": True
                    }
                    loaded_strategies_names.append(name)
                    logger.info(f"✅ 전략 활성화: {name}")
            else:
                logger.info(f"⏸ 전략 비활성화: {name}")
        
        # ⭐ PHASE35-1-FIX: Strict Mode - 요청된 전략이 모두 로드되었는지 검증
        if requested_strategies:
            missing_strategies = set(requested_strategies) - set(loaded_strategies_names)
            if missing_strategies:
                error_msg = (
                    f"❌ [PHASE35 STRICT MODE] 요청된 전략이 로드되지 않음: {missing_strategies}\n"
                    f"   요청: {requested_strategies}\n"
                    f"   로드: {loaded_strategies_names}\n"
                    f"   사용 가능: {list(all_strategies.keys())}\n"
                    f"   → Config에 enabled=true로 설정된 전략이 all_strategies에 등록되지 않았습니다."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"✅ [STRICT MODE] All {len(requested_strategies)} requested strategies loaded")
    
    if not strategies:
        logger.warning("⚠️ 활성 전략 없음, daytrade를 기본으로 로드")
        strategies_cfg = config.get('strategies', {})
        daytrade_config = strategies_cfg.get('daytrade', {})
        
        # PHASE29-2C-R: params 키가 없으면 config 전체를 파라미터로 간주
        if 'params' in daytrade_config:
            strategy_params = daytrade_config['params']
        else:
            known_meta_keys = {'enabled', 'timeframe', 'filters'}
            strategy_params = {k: v for k, v in daytrade_config.items() if k not in known_meta_keys}
        
        # PHASE23-2: BaseStrategy 인스턴스 생성
        strategy_module = all_strategies.get('daytrade')
        strategy_class = _get_strategy_class(strategy_module, 'daytrade')
        if strategy_class:
            merged_config = {**config, **strategy_params}
            instance = strategy_class(config=merged_config)
        else:
            instance = strategy_module
        
        strategies['daytrade'] = {
            "instance": instance,
            "params": strategy_params,
            "enabled": True
        }
    
    return strategies


from strategies.btc15m_core_v1 import Btc15mCoreV1
from strategies.btc15m_core_v2 import BTC15mCoreV2Strategy

__all__ = [
    'Btc15mCoreV1',
    'BTC15mCoreV2Strategy',
    'scalping',
    'swing_bb',
    'daytrade',
    'swing',
    'trend',
    'reversion',
    'breakout',
    'ensemble',
    'get_all_strategies',
    'load_strategies',
]
