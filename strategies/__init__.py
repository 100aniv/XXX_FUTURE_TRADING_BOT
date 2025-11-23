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
        'scalping': scalping,
        'swing_bb': swing_bb,
        'daytrade': daytrade,
        'swing': swing,
        'trend': trend,
        'reversion': reversion,
        'breakout': breakout
    }


def load_strategies(config: dict, all_strategies: dict = None) -> Dict[str, Dict[str, Any]]:
    """
    설정 기반 전략 로딩 (PHASE22-4: Config Integration Fix)
    
    Args:
        config: 전체 설정 딕셔너리
        all_strategies: 전체 전략 모듈 딕셔너리 (None이면 get_all_strategies() 사용)
    
    Returns:
        로드된 전략 딕셔너리
        {
            "strategy_name": {
                "module": <module>,
                "params": {<strategy-specific params>},
                "enabled": True
            },
            ...
        }
    """
    import os
    
    # 전략 딕셔너리 자동 로드
    if all_strategies is None:
        all_strategies = get_all_strategies()
    
    strategies = {}
    
    # 전략 설정 (환경변수 우선)
    strategy_cfg = config.get('strategy', {})
    use_ensemble = strategy_cfg.get('use_ensemble', True)
    selector = os.getenv('STRATEGY_SELECTOR', strategy_cfg.get('selector', None))
    
    # 단일 전략 모드: selector로 1개만 선택
    if not use_ensemble and selector:
        logger.info(f"🔍 [PHASE22-4 DEBUG] 단일 전략 모드: selector={selector}")
        if selector in all_strategies:
            # PHASE22-4: params 추출
            strategies_cfg = config.get('strategies', {})
            logger.info(f"🔍 [PHASE22-4 DEBUG] strategies_cfg keys: {list(strategies_cfg.keys())}")
            strategy_config = strategies_cfg.get(selector, {})
            strategy_params = strategy_config.get('params', {})
            logger.info(f"🔍 [PHASE22-4 DEBUG] {selector}: strategy_config={strategy_config}, params={strategy_params}")
            
            strategies[selector] = {
                "module": all_strategies[selector],
                "params": strategy_params,
                "enabled": True
            }
            logger.info(f"✅ 단일 전략 모드: {selector}")
        else:
            logger.error(f"❌ 전략 '{selector}' 없음, daytrade로 fallback")
            strategies_cfg = config.get('strategies', {})
            strategy_params = strategies_cfg.get('daytrade', {}).get('params', {})
            strategies['daytrade'] = {
                "module": all_strategies.get('daytrade'),
                "params": strategy_params,
                "enabled": True
            }
    
    # 앙상블 모드: enabled=true인 모든 전략 로드
    else:
        strategies_cfg = config.get('strategies', {})
        logger.info(f"🔍 [PHASE22-4 DEBUG] strategies_cfg keys: {list(strategies_cfg.keys())}")
        for name, module in all_strategies.items():
            strategy_config = strategies_cfg.get(name, {})
            enabled = strategy_config.get('enabled', True)
            params = strategy_config.get('params', {})
            logger.info(f"🔍 [PHASE22-4 DEBUG] {name}: strategy_config={strategy_config}, params={params}")
            
            if enabled:
                # PHASE22-4: module + params + enabled 포함
                strategies[name] = {
                    "module": module,
                    "params": params,
                    "enabled": True
                }
                logger.info(f"✅ 전략 활성화: {name}")
            else:
                logger.info(f"⏸ 전략 비활성화: {name}")
    
    if not strategies:
        logger.warning("⚠️ 활성 전략 없음, daytrade를 기본으로 로드")
        strategies_cfg = config.get('strategies', {})
        strategy_params = strategies_cfg.get('daytrade', {}).get('params', {})
        strategies['daytrade'] = {
            "module": all_strategies.get('daytrade'),
            "params": strategy_params,
            "enabled": True
        }
    
    return strategies


__all__ = [
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
