#!/usr/bin/env python3
"""
PHASE28-4: 최소 Bayesian Search 파라미터 전달 테스트
1 trial만 실행해서 파라미터가 제대로 전달되는지 확인
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from tuning.algorithms.random_search import ParamSpace
from tuning.algorithms.bayesian_search import BayesianSearchConfig, BayesianSearchTuner
from common.logger import setup_logger

logger = setup_logger(__name__)

# 1. ParamSpace 로드
param_space_yaml = project_root / "configs" / "tuning" / "phase28_2_btc5m_baseline_paramspace.yml"
with open(param_space_yaml, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

param_space = ParamSpace(space=data['param_space'])
param_space.validate()

# 2. Base config
base_config_path = str(project_root / "configs" / "backtest" / "phase28_2_btc5m_tuning_base.yml")

# 3. BayesianSearchConfig 생성 (1 trial만)
config = BayesianSearchConfig(
    run_name="test_minimal_bayesian_param_check",
    phase="PHASE28-4",
    strategy_family="baseline",
    strategy_name="btc5m_baseline_v1",
    mode="backtest",
    tuning_method="bayesian",
    target_metric="sharpe_like_ratio",
    n_trials=1,  # ← 최소 1 trial
    base_config_path=base_config_path,
    param_space=param_space,
    direction="maximize",
    seed=999
)

# 4. Bayesian Search 실행
logger.info("=" * 80)
logger.info("🧪 MINIMAL BAYESIAN PARAMETER TEST")
logger.info("=" * 80)
logger.info(f"  Trial count: {config.n_trials}")
logger.info(f"  Base config: {config.base_config_path}")
logger.info("=" * 80)

tuner = BayesianSearchTuner()
run_id = tuner.run_sequential(config)

logger.info("=" * 80)
logger.info(f"✅ Test completed: {run_id}")
logger.info("=" * 80)

# 5. DB에서 결과 확인
from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        # Job 상태
        cur.execute("""
            SELECT job_id, status, params_json
            FROM tuning.jobs
            WHERE run_id = %s
            ORDER BY created_at DESC
        """, (run_id,))
        jobs = cur.fetchall()
        
        logger.info(f"\nJobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job[0]}: {job[1]}")
            if job[2]:
                params = job[2]
                logger.info(f"    Params: rsi_long={params.get('rsi_long_threshold')}, bb_std={params.get('bb_std_main')}")
        
        # Result 확인
        cur.execute("""
            SELECT r.result_id, r.pnl, r.sharpe_ratio, r.trade_count
            FROM tuning.results r
            JOIN tuning.jobs j ON r.job_id = j.job_id
            WHERE j.run_id = %s
        """, (run_id,))
        results = cur.fetchall()
        
        logger.info(f"\nResults: {len(results)}")
        for r in results:
            logger.info(f"  - {r[0]}: PnL={r[1]:.2f}, Sharpe={r[2]:.4f}, Trades={r[3]}")

print("\n" + "=" * 80)
if len(results) > 0:
    print("✅ SUCCESS: Bayesian Search completed and metrics extracted!")
else:
    print("❌ FAILED: No results found (check logs for errors)")
print("=" * 80)
