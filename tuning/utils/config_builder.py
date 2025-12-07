"""
PHASE28-4: Tuning Config Builder - Random Search와 Bayesian Search 공통 helper

TuningWorker (Random Search)와 BayesianSearchTuner (Bayesian Search)가
100% 동일한 config merge 로직을 사용하도록 공통 helper 함수를 제공합니다.

Author: AI Assistant (Windsurf)
Date: 2025-12-07
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from common.config_loader import deep_merge
from common.logger import setup_logger

logger = setup_logger(__name__)


def build_tuning_config(
    base_config_path: str,
    strategy_params: Dict[str, Any],
    trial_id: str,
    run_id: str,
    mode: str = 'backtest',
    period_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tuning 실행을 위한 최종 config 생성 (Random Search & Bayesian Search 공통)
    
    이 함수는 TuningWorker.process_job()와 BayesianSearchTuner._run_single_trial()
    에서 동일한 config merge 로직을 사용하도록 보장합니다.
    
    Args:
        base_config_path: 기본 config YAML 파일 경로
        strategy_params: ParamSpace에서 샘플링된 파라미터 (dict)
        trial_id: Trial/Job ID (DB 연결용)
        run_id: Run ID (DB 연결용)
        mode: 실행 모드 ('backtest' or 'paper')
        period_override: 날짜 범위 override (optional)
            - start_date: str (YYYY-MM-DD)
            - end_date: str (YYYY-MM-DD)
    
    Returns:
        Dict[str, Any]: 최종 backtest config
    
    Examples:
        >>> config = build_tuning_config(
        ...     base_config_path='configs/backtest/phase28_2_btc5m_tuning_base.yml',
        ...     strategy_params={'rsi_long_threshold': 42, 'rsi_short_threshold': 58},
        ...     trial_id='job_abc123',
        ...     run_id='phase28_4_bull_xyz',
        ...     mode='backtest',
        ...     period_override={'start_date': '2024-10-01', 'end_date': '2024-10-31'}
        ... )
        >>> assert config['trial_id'] == 'job_abc123'
        >>> assert config['strategies']['btc5m_baseline_v1']['rsi_long_threshold'] == 42
    
    Implementation Notes:
        - TuningWorker.process_job()의 Line 239-302 로직과 100% 동일
        - strategies.{selector}에 파라미터 직접 삽입
        - merge_strategy_config()는 engine.py에서 자동 호출됨
        - trial_id/run_id 설정으로 DB 연결 보장
    """
    # 1. Base config 로드
    config_path = Path(base_config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {base_config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        base_config = yaml.safe_load(f)
    
    # 2. Deep copy (원본 보호)
    config = deep_merge(base_config, {})
    
    # 3. Strategy selector 확인
    strategy_section = config.get('strategy', {})
    selector = strategy_section.get('selected', strategy_section.get('selector', 'btc5m_baseline_v1'))
    strategies_section = config.get('strategies', {})
    
    logger.debug(f"[CONFIG_BUILDER] Strategy selector: {selector}")
    logger.debug(f"[CONFIG_BUILDER] Strategy params to apply: {strategy_params}")
    logger.debug(f"[CONFIG_BUILDER] strategies section keys: {list(strategies_section.keys())}")
    logger.debug(f"[CONFIG_BUILDER] selector in strategies? {selector in strategies_section}")
    
    # 4. Params override 적용
    # PHASE28-2: Strategy params override (2가지 구조 지원)
    
    # 방식 1: strategy.{selected}.params (PHASE25 원래 구조)
    if selector in strategy_section:
        strategy_config = strategy_section[selector]
        if 'params' not in strategy_config:
            strategy_config['params'] = {}
        
        # Params 덮어쓰기
        for key, value in strategy_params.items():
            strategy_config['params'][key] = value
        
        logger.debug(f"[CONFIG_BUILDER]   Applied to strategy.{selector}.params")
    
    # 방식 2: strategies.{strategy_name} (PHASE27/28-1 구조)
    # merge_strategy_config()가 top-level로 복사하므로, strategies 섹션에도 적용
    if selector in strategies_section:
        # strategies.{strategy_name}에 직접 적용 (params 키 없이)
        for key, value in strategy_params.items():
            strategies_section[selector][key] = value
        
        logger.debug(f"[CONFIG_BUILDER] Applied {len(strategy_params)} params to strategies.{selector}")
    
    # 5. Mode 설정
    config['mode'] = mode
    
    # 6. Trial ID / Run ID 설정 (DB 연결 및 메트릭 추출 필수)
    config['trial_id'] = trial_id
    config['run_id'] = run_id
    
    logger.debug(f"[CONFIG_BUILDER]   trial_id: {trial_id}")
    logger.debug(f"[CONFIG_BUILDER]   run_id: {run_id}")
    
    # 7. Period Override (Bayesian Search에서 Period별 날짜 범위 적용)
    if period_override:
        if 'start_date' in period_override:
            if 'backtest' not in config:
                config['backtest'] = {}
            config['backtest']['start_date'] = period_override['start_date']
            logger.debug(f"[CONFIG_BUILDER]   Override start_date: {period_override['start_date']}")
        
        if 'end_date' in period_override:
            if 'backtest' not in config:
                config['backtest'] = {}
            config['backtest']['end_date'] = period_override['end_date']
            logger.debug(f"[CONFIG_BUILDER]   Override end_date: {period_override['end_date']}")
    
    # 8. Duration 짧게 (백테스트 빠르게, paper 모드만)
    if mode == 'paper':
        config['duration_hours'] = 0.0083  # 30초
    
    logger.debug(f"[CONFIG_BUILDER] Config build complete for {selector} (mode={mode})")
    
    return config
