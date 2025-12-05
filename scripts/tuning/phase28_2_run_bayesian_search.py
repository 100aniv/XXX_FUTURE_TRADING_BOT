#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-2: Bayesian Search Runner for btc5m_baseline_v1 (Skeleton)
===================================================================
btc5m_baseline_v1 전략의 Bayesian Search 스켈레톤 (dry-run용)

주요 기능:
- ParamSpace YAML 로드
- Bayesian Search 기반 파라미터 탐색 (Optuna TPE)
- 매우 작은 규모 (3-5 trials)로 end-to-end 동작 검증

참고:
- 본격적인 Bayesian 튜닝은 PHASE28-3에서 수행
- PHASE28-2에서는 인프라 동작 확인만

사용법:
    python scripts/tuning/phase28_2_run_bayesian_search.py --dry-run
    python scripts/tuning/phase28_2_run_bayesian_search.py --trials 5 --period neutral
"""
import argparse
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tuning.algorithms.bayesian_search import BayesianSearchTuner, BayesianSearchConfig
from tuning.algorithms.random_search import ParamSpace
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def load_param_space_yaml(yaml_path: str) -> Dict[str, Any]:
    """ParamSpace YAML 로드"""
    config_path = Path(yaml_path)
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {yaml_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    logger.info(f"✅ ParamSpace YAML 로드 완료: {yaml_path}")
    return data


def create_param_space(param_space_dict: Dict[str, Dict[str, Any]]) -> ParamSpace:
    """YAML의 param_space를 ParamSpace 객체로 변환"""
    space = {}
    
    for param_name, spec in param_space_dict.items():
        space[param_name] = {
            'type': spec['type']
        }
        
        if spec['type'] in ('int', 'float'):
            space[param_name]['min'] = spec['min']
            space[param_name]['max'] = spec['max']
            if 'log' in spec:
                space[param_name]['log'] = spec['log']
        
        elif spec['type'] == 'categorical':
            space[param_name]['values'] = spec['values']
    
    param_space = ParamSpace(space=space)
    param_space.validate()
    
    logger.info(f"✅ ParamSpace 생성 완료 ({len(space)}개 파라미터)")
    return param_space


def run_bayesian_search(
    yaml_path: str,
    period_filter: str = None,
    n_trials_override: int = None,
    dry_run: bool = False
) -> List[str]:
    """
    Bayesian Search 실행 (Skeleton/Dry-run)
    
    Args:
        yaml_path: ParamSpace YAML 경로
        period_filter: 특정 period만 실행 ('bull', 'range', 'neutral', 또는 None=all)
        n_trials_override: Trial 수 오버라이드 (None이면 YAML 기본값 사용)
        dry_run: True이면 스켈레톤만 실행 (실제 백테스트 없음)
    
    Returns:
        List[str]: 생성된 run_id 리스트
    """
    # ========================================
    # 1. YAML 로드
    # ========================================
    config_data = load_param_space_yaml(yaml_path)
    
    run_metadata = config_data['run_metadata']
    target = config_data['target']
    base_config_info = config_data['base_config']
    market_periods = config_data['market_periods']
    param_space_dict = config_data['param_space']
    
    # Trial 수 결정
    n_trials = n_trials_override or run_metadata['bayesian_search']['n_trials']
    seed = run_metadata['bayesian_search']['seed']
    
    logger.info("=" * 80)
    logger.info("PHASE28-2: Bayesian Search for btc5m_baseline_v1 (SKELETON)")
    logger.info("=" * 80)
    logger.info(f"⚠️  WARNING: This is a SKELETON implementation")
    logger.info(f"   - 본격적인 Bayesian 튜닝은 PHASE28-3에서 수행")
    logger.info(f"   - PHASE28-2에서는 end-to-end 동작 확인만")
    logger.info("=" * 80)
    logger.info(f"Phase: {run_metadata['phase']}")
    logger.info(f"Strategy: {run_metadata['strategy_name']}")
    logger.info(f"Target Metric: {run_metadata['target_metric']}")
    logger.info(f"Total Trials per Period: {n_trials}")
    logger.info(f"Dry Run: {dry_run}")
    
    # ========================================
    # 2. ParamSpace 생성
    # ========================================
    param_space = create_param_space(param_space_dict)
    
    # ========================================
    # 3. 각 Market Period별로 Bayesian Search 실행
    # ========================================
    created_runs = []
    
    # PHASE28-2에서는 1개 period만 테스트 (시간 절약)
    if not period_filter:
        period_filter = 'neutral'  # 기본값: neutral period만
        logger.info(f"🔍 Period 필터 미지정 → 기본값 '{period_filter}' 사용")
    
    for period_name, period_config in market_periods.items():
        # Period 필터링
        if period_filter and period_name != period_filter:
            logger.info(f"⏭️  Period '{period_name}' 스킵 (필터: {period_filter})")
            continue
        
        logger.info("=" * 80)
        logger.info(f"📅 Market Period: {period_name}")
        logger.info(f"   - {period_config['name']}")
        logger.info(f"   - {period_config['start']} ~ {period_config['end']}")
        
        # Run name
        run_name = f"{run_metadata['run_name']}_bayesian_{period_name}"
        
        # BayesianSearchConfig 생성
        search_config = BayesianSearchConfig(
            run_name=run_name,
            phase=run_metadata['phase'],
            strategy_family=run_metadata['strategy_family'],
            strategy_name=run_metadata['strategy_name'],
            mode=target['mode'],
            tuning_method='bayesian',
            target_metric=run_metadata['target_metric'],
            n_trials=n_trials,
            base_config_path=base_config_info['path'],
            param_space=param_space,
            direction='maximize',  # sharpe_like_ratio는 maximize
            seed=seed
        )
        
        # BayesianSearchTuner로 실행
        tuner = BayesianSearchTuner()
        
        try:
            if dry_run:
                logger.info(f"🔍 Dry Run 모드: Bayesian Search 스킵")
                logger.info(f"   - Run name: {run_name}")
                logger.info(f"   - Trials: {n_trials}")
                logger.info(f"   - Param space: {list(param_space.space.keys())}")
                created_runs.append(run_name + "_dryrun")
                continue
            
            # Bayesian Search 실행 (Sequential)
            logger.info(f"🚀 Bayesian Search 시작: {run_name}")
            logger.info(f"   ⏱️  예상 시간: {n_trials} trials × ~30-60초 = {n_trials * 0.5}-{n_trials} 분")
            
            run_id = tuner.run_sequential(search_config)
            
            logger.info(f"✅ Bayesian Search 완료: {run_id}")
            
            created_runs.append(run_id)
            
        except Exception as e:
            logger.error(f"❌ Bayesian Search 실패: {period_name}, 에러: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # ========================================
    # 4. 결과 요약
    # ========================================
    logger.info("=" * 80)
    logger.info("✅ Bayesian Search (Skeleton) 완료")
    logger.info(f"   - 생성된 Runs: {len(created_runs)}개")
    for run_id in created_runs:
        logger.info(f"     - {run_id}")
    logger.info("=" * 80)
    
    if not dry_run:
        logger.info("📊 결과 확인:")
        logger.info("   - DB: tuning.runs, tuning.results 테이블")
        logger.info("   - 집계 스크립트: scripts/research/phase28_2_summarize_tuning_results.py")
    
    return created_runs


def main():
    """메인 엔트리 포인트"""
    parser = argparse.ArgumentParser(
        description="PHASE28-2: Bayesian Search for btc5m_baseline_v1 (Skeleton)"
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='configs/tuning/phase28_2_btc5m_baseline_paramspace.yml',
        help='ParamSpace YAML 경로'
    )
    
    parser.add_argument(
        '--trials',
        type=int,
        default=None,
        help='Trial 수 (None이면 YAML 기본값 5 사용)'
    )
    
    parser.add_argument(
        '--period',
        type=str,
        choices=['bull', 'range', 'neutral'],
        default=None,
        help='특정 period만 실행 (None이면 neutral 기본값)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run (실제 실행하지 않음, 구조만 확인)'
    )
    
    args = parser.parse_args()
    
    try:
        created_runs = run_bayesian_search(
            yaml_path=args.config,
            period_filter=args.period,
            n_trials_override=args.trials,
            dry_run=args.dry_run
        )
        
        if not created_runs:
            logger.warning("⚠️  생성된 Run이 없습니다")
            sys.exit(1)
        
        logger.info("✅ PHASE28-2 Bayesian Search (Skeleton) 성공")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ PHASE28-2 Bayesian Search 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
