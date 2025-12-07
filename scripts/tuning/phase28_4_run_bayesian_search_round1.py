#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-4: Bayesian Search Round 1 - Automated Execution
==========================================================
Random Search (PHASE28-3) 결과 기반 Bayesian Optimization 실행

주요 기능:
1. 환경 검증 (Python version, DB/Redis 연결)
2. PHASE28-3 결과에서 Top-N 후보 추출
3. Bayesian Search 실행 (Period별)
4. 결과 집계 및 리포트 생성 (Markdown + JSON)

Usage:
    python scripts/tuning/phase28_4_run_bayesian_search_round1.py --config configs/tuning/phase28_4_btc5m_bayesian_search.yml
    python scripts/tuning/phase28_4_run_bayesian_search_round1.py --config configs/tuning/phase28_4_btc5m_bayesian_search_smoke.yml --smoke
"""
import sys
import os
import argparse
import time
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from tuning.algorithms.random_search import ParamSpace
from tuning.algorithms.bayesian_search import BayesianSearchConfig, BayesianSearchTuner
from tuning.cluster.job_queue import JobQueue
from tuning.utils.result_selection import select_top_n_candidates
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ========================================
# Utility Functions
# ========================================

def generate_run_id(base_name: str) -> str:
    """Generate unique run_id with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:21]
    # Hash suffix for uniqueness
    import hashlib
    suffix = hashlib.md5(timestamp.encode()).hexdigest()[:8]
    return f"{base_name}_{suffix}"


# ========================================
# Environment Check
# ========================================

def check_environment():
    """환경 검증: Python version, DB"""
    logger.info("=" * 80)
    logger.info("🔍 Environment Check")
    logger.info("=" * 80)
    
    # Python version
    if sys.version_info < (3, 9):
        logger.error(f"❌ Python 3.9+ required (current: {sys.version})")
        return False
    logger.info(f"✅ Python version: {sys.version.split()[0]}")
    
    # Postgres
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"✅ Postgres reachable: {version.split(',')[0]}")
    except Exception as e:
        logger.error(f"❌ Postgres unreachable: {e}")
        return False
    
    logger.info("=" * 80)
    return True


# ========================================
# Config Loading
# ========================================

def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML config"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"✅ Config loaded: {config_path}")
    return config


def load_param_space(param_space_path: str) -> ParamSpace:
    """Load ParamSpace from YAML"""
    ps_file = Path(param_space_path)
    if not ps_file.exists():
        raise FileNotFoundError(f"ParamSpace YAML not found: {param_space_path}")
    
    with open(ps_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    param_space_dict = data.get('param_space', {})
    param_space = ParamSpace(space=param_space_dict)
    param_space.validate()
    
    logger.info(f"✅ ParamSpace loaded: {len(param_space_dict)} params")
    return param_space


# ========================================
# Top-N Candidate Selection
# ========================================

def extract_top_n_candidates(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """PHASE28-3 결과에서 Top-N 후보 추출"""
    logger.info("=" * 80)
    logger.info("🎯 Extracting Top-N Candidates from PHASE28-3 Results")
    logger.info("=" * 80)
    
    seed_config = config.get('top_n_seed', {})
    results_path = seed_config.get('random_search_results_path')
    top_n = seed_config.get('top_n', 5)
    min_trades = seed_config.get('min_trades', 5)
    max_dd_threshold = seed_config.get('max_drawdown_threshold', -20.0)
    
    candidates = select_top_n_candidates(
        results_json_path=results_path,
        top_n=top_n,
        min_trades=min_trades,
        max_drawdown_threshold=max_dd_threshold
    )
    
    logger.info(f"✅ Top-{len(candidates)} candidates selected")
    for i, candidate in enumerate(candidates, 1):
        logger.info(f"   [{i}] Job: {candidate.get('job_id', 'N/A')}, "
                    f"Sharpe: {candidate.get('sharpe_ratio', 0.0):.4f}, "
                    f"Score: {candidate.get('score', 0.0):.2f}")
    
    logger.info("=" * 80)
    return candidates


# ========================================
# Bayesian Search Execution
# ========================================

def run_bayesian_search_for_period(
    period_name: str,
    period_config: Dict[str, Any],
    param_space: ParamSpace,
    base_config_path: str,
    bayes_config: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    단일 Period에 대해 Bayesian Search 실행
    
    Returns:
        str: run_id
    """
    logger.info("=" * 80)
    logger.info(f"🔍 Bayesian Search: {period_name}")
    logger.info("=" * 80)
    
    # Run ID 생성
    run_id = generate_run_id(f"phase28_4_{period_name}")
    logger.info(f"📝 Run ID: {run_id}")
    
    # Period별 임시 config 파일 생성
    import tempfile
    with open(base_config_path, 'r', encoding='utf-8') as f:
        base_cfg = yaml.safe_load(f)
    
    # Period 날짜 override (backtest 섹션 사용)
    if 'backtest' not in base_cfg:
        base_cfg['backtest'] = {}
    base_cfg['backtest']['start_date'] = period_config['start']
    base_cfg['backtest']['end_date'] = period_config['end']
    
    # 임시 config 저장
    temp_config_fd, temp_config_path = tempfile.mkstemp(suffix='.yml', text=True)
    try:
        with os.fdopen(temp_config_fd, 'w', encoding='utf-8') as f:
            yaml.dump(base_cfg, f)
        
        logger.info(f"📄 Temporary config: {temp_config_path}")
        logger.info(f"📅 Period: {period_config['start']} ~ {period_config['end']}")
        
        # BayesianSearchConfig 생성
        search_config = BayesianSearchConfig(
            run_name=run_id,
            phase=metadata['phase'],
            strategy_family=metadata['strategy_family'],
            strategy_name=metadata['strategy_name'],
            mode='backtest',
            tuning_method='bayesian',
            target_metric=bayes_config['objective']['metric'],
            n_trials=bayes_config['max_trials_per_period'],
            base_config_path=temp_config_path,
            param_space=param_space,
            direction=bayes_config['objective']['direction'],
            seed=bayes_config.get('random_seed', 84)
        )
        
        # Bayesian Search 실행
        tuner = BayesianSearchTuner()
        actual_run_id = tuner.run_sequential(search_config)
        
        logger.info(f"✅ Bayesian Search completed: {actual_run_id}")
        logger.info("=" * 80)
        
        return actual_run_id
    
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


# ========================================
# Result Aggregation
# ========================================

def aggregate_results(run_ids: List[str], output_config: Dict[str, Any]):
    """결과 집계 및 리포트 생성"""
    logger.info("=" * 80)
    logger.info("📊 Aggregating Results")
    logger.info("=" * 80)
    
    # DB에서 결과 조회
    all_results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for run_id in run_ids:
                cur.execute("""
                    SELECT 
                        r.run_id,
                        r.job_id,
                        r.total_trades,
                        r.pnl,
                        r.pnl_pct,
                        r.sharpe_like_ratio,
                        r.win_rate,
                        r.max_drawdown,
                        r.params_json,
                        r.created_at
                    FROM tuning.results r
                    WHERE r.run_id = %s
                    ORDER BY r.sharpe_like_ratio DESC NULLS LAST
                """, (run_id,))
                
                results = cur.fetchall()
                for row in results:
                    all_results.append({
                        'run_id': row[0],
                        'job_id': row[1],
                        'trade_count': row[2],
                        'pnl': float(row[3]) if row[3] is not None else 0.0,
                        'pnl_pct': float(row[4]) if row[4] is not None else 0.0,
                        'sharpe_ratio': float(row[5]) if row[5] is not None else 0.0,
                        'win_rate': float(row[6]) if row[6] is not None else 0.0,
                        'max_drawdown': float(row[7]) if row[7] is not None else 0.0,
                        'params': row[8] if row[8] else {},
                        'created_at': row[9].isoformat() if row[9] else None
                    })
    
    logger.info(f"✅ Total results: {len(all_results)}")
    
    # JSON 저장
    json_output_path = Path(output_config['json']['path'])
    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'phase': 'PHASE28-4',
        'execution_time': datetime.now().isoformat(),
        'summary': {
            'total_trials': len(all_results),
            'run_ids': run_ids
        },
        'results': all_results
    }
    
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON saved: {json_output_path}")
    
    # Markdown 리포트 생성은 별도 스크립트 또는 수동 작성 예정
    logger.info("📝 Markdown report: Manual generation pending")
    
    logger.info("=" * 80)


# ========================================
# Main
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description='PHASE28-4: Bayesian Search Round 1 - Automated Execution',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        type=str,
        default='configs/tuning/phase28_4_btc5m_bayesian_search.yml',
        help='Config YAML path'
    )
    parser.add_argument(
        '--smoke',
        action='store_true',
        help='Smoke test mode (reduced trials)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE28-4: Bayesian Search Round 1")
    logger.info("=" * 80)
    logger.info(f"Config: {args.config}")
    logger.info(f"Smoke Test: {args.smoke}")
    logger.info("=" * 80)
    
    # 1. 환경 검증
    if not check_environment():
        logger.error("❌ Environment check failed")
        sys.exit(1)
    
    # 2. Config 로딩
    config = load_config(args.config)
    
    # 3. ParamSpace 로딩
    param_space_path = config.get('param_space_path', 'configs/tuning/phase28_2_btc5m_baseline_paramspace.yml')
    param_space = load_param_space(param_space_path)
    
    # 4. Top-N 후보 추출
    top_candidates = extract_top_n_candidates(config)
    if not top_candidates:
        logger.warning("⚠️ No valid candidates found. Proceeding with Bayesian Search without seed.")
    
    # 5. Period별 Bayesian Search 실행
    periods = config.get('market_periods', {})
    metadata = config.get('run_metadata', {})
    bayes_config = config.get('bayesian_search', {})
    base_config_path = config.get('base_config', {}).get('path')
    
    run_ids = []
    for period_name, period_config in periods.items():
        if args.smoke and len(run_ids) >= 1:
            logger.info(f"⏭️  Smoke test: Skipping period {period_name}")
            continue
        
        run_id = run_bayesian_search_for_period(
            period_name=period_name,
            period_config=period_config,
            param_space=param_space,
            base_config_path=base_config_path,
            bayes_config=bayes_config,
            metadata=metadata
        )
        run_ids.append(run_id)
    
    # 6. 결과 집계
    output_config = config.get('output', {})
    aggregate_results(run_ids, output_config)
    
    logger.info("=" * 80)
    logger.info("✅ PHASE28-4 Bayesian Search Round 1 Complete")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
