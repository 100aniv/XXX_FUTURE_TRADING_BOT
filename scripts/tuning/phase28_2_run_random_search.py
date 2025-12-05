#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-2: Random Search Runner for btc5m_baseline_v1
======================================================
btc5m_baseline_v1 전략의 첫 번째 튜닝 라운드 (Random Search)

주요 기능:
- ParamSpace YAML 로드
- 각 시장 구간별로 Run 생성
- Random Search 기반 파라미터 탐색
- JobQueue + Worker로 백테스트 실행
- 결과를 tuning.results에 저장

사용법:
    python scripts/tuning/phase28_2_run_random_search.py --trials 25
    python scripts/tuning/phase28_2_run_random_search.py --trials 25 --period bull
    python scripts/tuning/phase28_2_run_random_search.py --dry-run
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

from tuning.algorithms.random_search import RandomSearchTuner, RandomSearchConfig, ParamSpace
from tuning.cluster.job_queue import JobQueue
from tuning.cluster.worker import TuningWorker
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def load_param_space_yaml(yaml_path: str) -> Dict[str, Any]:
    """
    ParamSpace YAML 로드
    
    Args:
        yaml_path: YAML 파일 경로
    
    Returns:
        Dict[str, Any]: YAML 내용
    """
    config_path = Path(yaml_path)
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found: {yaml_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    logger.info(f"✅ ParamSpace YAML 로드 완료: {yaml_path}")
    return data


def create_param_space(param_space_dict: Dict[str, Dict[str, Any]]) -> ParamSpace:
    """
    YAML의 param_space를 ParamSpace 객체로 변환
    
    Args:
        param_space_dict: YAML의 param_space 섹션
    
    Returns:
        ParamSpace: ParamSpace 인스턴스
    """
    # ParamSpace 클래스는 'space' 키로 파라미터 정의를 받음
    space = {}
    
    for param_name, spec in param_space_dict.items():
        # YAML 스펙에서 'baseline', 'description' 제외하고 복사
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
    for param_name in space.keys():
        logger.info(f"   - {param_name}")
    
    return param_space


def run_random_search(
    yaml_path: str,
    period_filter: str = None,
    n_trials_override: int = None,
    dry_run: bool = False
) -> List[str]:
    """
    Random Search 실행
    
    Args:
        yaml_path: ParamSpace YAML 경로
        period_filter: 특정 period만 실행 ('bull', 'range', 'neutral', 또는 None=all)
        n_trials_override: Trial 수 오버라이드 (None이면 YAML 기본값 사용)
        dry_run: True이면 jobs 생성만 하고 실행하지 않음
    
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
    n_trials = n_trials_override or run_metadata['random_search']['n_trials']
    seed = run_metadata['random_search']['seed']
    
    logger.info("=" * 80)
    logger.info("PHASE28-2: Random Search for btc5m_baseline_v1")
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
    # 3. 각 Market Period별로 Run 생성
    # ========================================
    job_queue = JobQueue()
    created_runs = []
    
    for period_name, period_config in market_periods.items():
        # Period 필터링
        if period_filter and period_name != period_filter:
            logger.info(f"⏭️  Period '{period_name}' 스킵 (필터: {period_filter})")
            continue
        
        logger.info("=" * 80)
        logger.info(f"📅 Market Period: {period_name}")
        logger.info(f"   - {period_config['name']}")
        logger.info(f"   - {period_config['start']} ~ {period_config['end']}")
        logger.info(f"   - Weight: {period_config['weight']}")
        
        # Run name
        run_name = f"{run_metadata['run_name']}_{period_name}"
        
        # Config override: base_config_path + period start/end
        config_override = {
            'base_config_path': base_config_info['path'],
            'start_date': period_config['start'],
            'end_date': period_config['end'],
            'symbol': target['symbol'],
            'timeframe': target['timeframe']
        }
        
        # Metadata
        metadata = {
            'phase': run_metadata['phase'],
            'strategy_name': run_metadata['strategy_name'],
            'period_name': period_name,
            'period_weight': period_config['weight'],
            'n_trials': n_trials,
            'seed': seed
        }
        
        # RandomSearchConfig 생성
        search_config = RandomSearchConfig(
            run_name=run_name,
            phase=run_metadata['phase'],
            strategy_family=run_metadata['strategy_family'],
            strategy_name=run_metadata['strategy_name'],
            mode=target['mode'],
            tuning_method='random',
            target_metric=run_metadata['target_metric'],
            n_trials=n_trials,
            base_config_path=base_config_info['path'],
            param_space=param_space,
            seed=seed,
            metadata=metadata
        )
        
        # RandomSearchTuner로 Run + Jobs 생성
        tuner = RandomSearchTuner(job_queue=job_queue)
        
        try:
            run_id, job_ids = tuner.create_run_and_jobs(search_config)
            
            logger.info(f"✅ Run 생성 완료: {run_id}")
            logger.info(f"   - Jobs 생성: {len(job_ids)}개")
            
            created_runs.append(run_id)
            
            # Dry run이면 여기서 종료
            if dry_run:
                logger.info("🔍 Dry Run 모드: Job 실행 스킵")
                continue
            
            # ========================================
            # 4. Worker로 Jobs 처리
            # ========================================
            logger.info(f"🚀 Worker 시작: {run_id}")
            
            worker_id = f"worker_{period_name}_{datetime.now().strftime('%H%M%S')}"
            worker = TuningWorker(
                worker_id=worker_id,
                job_queue=job_queue,
                run_id=run_id,  # 이 run의 jobs만 처리
                use_dummy=False  # 실제 백테스트 실행
            )
            
            # Loop: 이 run의 모든 jobs 처리
            # once=False이면 할당 가능한 job이 없을 때까지 계속 처리
            # 하지만 실제로는 run_id로 필터링했으므로 해당 run의 jobs만 처리됨
            worker.loop(once=False, poll_interval_sec=1)
            
            logger.info(f"✅ Worker 완료: {run_id} ({worker.jobs_processed}개 처리)")
            
        except Exception as e:
            logger.error(f"❌ Run 생성/처리 실패: {period_name}, 에러: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # ========================================
    # 5. 결과 요약
    # ========================================
    logger.info("=" * 80)
    logger.info("✅ Random Search 완료")
    logger.info(f"   - 생성된 Runs: {len(created_runs)}개")
    for run_id in created_runs:
        logger.info(f"     - {run_id}")
    logger.info("=" * 80)
    
    if not dry_run:
        logger.info("📊 결과 확인:")
        logger.info("   - DB: tuning.runs, tuning.jobs, tuning.results 테이블")
        logger.info("   - 집계 스크립트: scripts/research/phase28_2_summarize_tuning_results.py")
    
    return created_runs


def main():
    """메인 엔트리 포인트"""
    parser = argparse.ArgumentParser(
        description="PHASE28-2: Random Search for btc5m_baseline_v1"
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
        help='Trial 수 (None이면 YAML 기본값 사용)'
    )
    
    parser.add_argument(
        '--period',
        type=str,
        choices=['bull', 'range', 'neutral'],
        default=None,
        help='특정 period만 실행 (None이면 전체)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run (Jobs 생성만, 실행하지 않음)'
    )
    
    args = parser.parse_args()
    
    try:
        created_runs = run_random_search(
            yaml_path=args.config,
            period_filter=args.period,
            n_trials_override=args.trials,
            dry_run=args.dry_run
        )
        
        if not created_runs:
            logger.warning("⚠️  생성된 Run이 없습니다")
            sys.exit(1)
        
        logger.info("✅ PHASE28-2 Random Search 성공")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ PHASE28-2 Random Search 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
