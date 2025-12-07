"""
PHASE28-4: Minimal Bayesian Search 디버그 테스트 (1 trial)

목적: 파라미터 전달 경로 완전 추적
- Config Builder → Engine → merge_strategy_config → Strategy
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import yaml
from pathlib import Path
from tuning.algorithms.bayesian_search import BayesianSearchTuner, BayesianSearchConfig
from tuning.algorithms.random_search import ParamSpace

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 80)
    logger.info("PHASE28-4 Bayesian Search 디버그 테스트 시작 (1 trial)")
    logger.info("=" * 80)
    
    # 1. Config 로드
    base_config_path = "configs/backtest/phase28_2_btc5m_tuning_base.yml"
    param_space_path = "configs/tuning/phase28_2_btc5m_baseline_paramspace.yml"
    
    logger.info(f"📄 Base config: {base_config_path}")
    logger.info(f"📄 Param space: {param_space_path}")
    
    # 2. ParamSpace 로드
    with open(param_space_path, 'r', encoding='utf-8') as f:
        param_space_yaml = yaml.safe_load(f)
    
    # YAML 구조 확인: 'param_space' 키 안에 실제 space가 있을 수 있음
    if 'param_space' in param_space_yaml:
        param_space_dict = param_space_yaml['param_space']
    else:
        param_space_dict = param_space_yaml
    
    param_space = ParamSpace(space=param_space_dict)
    logger.info(f"✅ ParamSpace 로드 완료: {len(param_space.space)} params")
    
    # 3. Bayesian Search Config 생성
    config = BayesianSearchConfig(
        run_name="phase28_4_debug_test",
        phase="PHASE28-4",
        strategy_family="baseline",
        strategy_name="btc5m_baseline_v1",
        mode='backtest',
        tuning_method='bayesian',
        target_metric='sharpe_ratio',
        n_trials=1,  # 1 trial만
        base_config_path=base_config_path,
        param_space=param_space,
        direction='maximize'
    )
    
    logger.info(f"✅ BayesianSearchConfig 생성 완료")
    logger.info(f"   n_trials: {config.n_trials}")
    logger.info(f"   target_metric: {config.target_metric}")
    
    # 4. Bayesian Search 실행
    logger.info("=" * 80)
    logger.info("🚀 Bayesian Search 실행 시작...")
    logger.info("=" * 80)
    
    tuner = BayesianSearchTuner()
    results = tuner.run_sequential(config=config)
    
    logger.info("=" * 80)
    logger.info("✅ Bayesian Search 완료")
    logger.info("=" * 80)
    logger.info(f"Results: {results}")

if __name__ == "__main__":
    main()
