#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Grid Search Tuner
=======================
PHASE25-4: Local Grid Search 기반 하이퍼파라미터 튜닝
PHASE28-5: Sequential Local Grid Search (Bayesian Best 주변 탐색)

주요 기능:
- Random/Bayesian에서 얻은 Best K 후보 주변 국소 그리드 탐색
- 각 후보의 파라미터를 중심으로 그리드 생성
- JobQueue 통합 (클러스터 방식) 또는 Sequential 실행 (PHASE28-5)

알고리즘:
1. Base run (Random/Bayesian)에서 Top K 후보 조회
2. 각 후보 주변 그리드 생성:
   - int: center ± delta
   - float: center ± (range * ratio)
   - categorical: center 주변 이웃
3. 생성된 조합을 실행 (클러스터 또는 Sequential)

사용법 (PHASE28-5 Sequential):
    from tuning.algorithms.local_grid_search import LocalGridSearchTuner
    
    # DB에서 seed trials 조회
    seed_trials = [...]  # params_json 포함
    
    # Tuner 실행
    tuner = LocalGridSearchTuner()
    run_ids = tuner.run_from_seeds(
        run_id_prefix='phase28_5_localgrid',
        seed_trials=seed_trials,
        param_space=param_space,
        grid_config={...},
        base_config_path='configs/...',
        mode='backtest',
        strategy_name='btc5m_baseline_v1'
    )

사용법 (PHASE25-4 클러스터):
    from tuning.algorithms import LocalGridSearchTuner, LocalGridSearchConfig
    
    config = LocalGridSearchConfig(...)
    tuner = LocalGridSearchTuner()
    run_id = tuner.create_run_and_jobs(config)
"""
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import itertools

from tuning.cluster.job_queue import JobQueue
from tuning.algorithms.random_search import ParamSpace
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


@dataclass
class LocalGridSearchConfig:
    """
    Local Grid Search 설정
    
    Attributes:
        run_name: Run 이름
        phase: Phase 정보 (예: 'PHASE25-4')
        strategy_family: 전략 패밀리 (예: 'momentum')
        strategy_name: 전략 이름 (예: 'scalping')
        mode: 실행 모드 ('backtest', 'paper', 'live')
        tuning_method: 튜닝 방법 ('local_grid' 고정)
        target_metric: 최적화 대상 메트릭 (예: 'sharpe_ratio')
        base_run_id: 기준 Run ID (Random/Bayesian run)
        top_k: 상위 K개 후보 선택
        grid_steps: 그리드 스텝 수 (홀수 권장, 예: 3 → center + ±1)
        step_factor: 스텝 크기 비율 (float 파라미터용, 예: 0.1 = 10%)
        base_config_path: 베이스 Config 파일 경로
        seed: Random seed (사용 안 함, 호환성 유지용)
    
    Examples:
        >>> config = LocalGridSearchConfig(
        ...     run_name='scalping_local_grid',
        ...     phase='PHASE25-4',
        ...     strategy_family='momentum',
        ...     strategy_name='scalping',
        ...     mode='backtest',
        ...     target_metric='sharpe_ratio',
        ...     base_run_id='run-abc123',
        ...     top_k=3,
        ...     grid_steps=3,
        ...     step_factor=0.1,
        ...     base_config_path='configs/paper/phase21_scalping_quick.yml'
        ... )
    """
    run_name: str
    phase: str
    strategy_family: str
    strategy_name: str
    mode: str
    tuning_method: str = 'local_grid'
    target_metric: str = 'sharpe_ratio'
    base_run_id: str = ''
    top_k: int = 3
    grid_steps: int = 3
    step_factor: float = 0.1
    base_config_path: str = ''
    seed: Optional[int] = None
    
    def validate(self) -> bool:
        """
        Config 검증
        
        Returns:
            bool: 검증 성공 여부
        
        Raises:
            ValueError: Config가 유효하지 않을 때
        """
        if not self.run_name:
            raise ValueError("❌ run_name 필수")
        
        if not self.base_run_id:
            raise ValueError("❌ base_run_id 필수 (Random/Bayesian run ID)")
        
        if self.top_k <= 0:
            raise ValueError(f"❌ top_k는 양수여야 함: {self.top_k}")
        
        if self.grid_steps <= 0:
            raise ValueError(f"❌ grid_steps는 양수여야 함: {self.grid_steps}")
        
        if self.grid_steps % 2 == 0:
            logger.warning(f"⚠️  grid_steps는 홀수 권장 (현재: {self.grid_steps})")
        
        if not (0 < self.step_factor <= 1.0):
            raise ValueError(f"❌ step_factor는 (0, 1] 범위여야 함: {self.step_factor}")
        
        if self.tuning_method != 'local_grid':
            raise ValueError(f"❌ tuning_method는 'local_grid'여야 함: {self.tuning_method}")
        
        if not self.base_config_path:
            raise ValueError("❌ base_config_path 필수")
        
        return True


class LocalGridSearchTuner:
    """
    Local Grid Search 튜너
    
    Random/Bayesian에서 얻은 Best K 후보 주변을 국소 그리드 탐색.
    
    Usage:
        tuner = LocalGridSearchTuner()
        run_id = tuner.create_run_and_jobs(config)
    """
    
    def __init__(self, job_queue: Optional[JobQueue] = None):
        """
        Args:
            job_queue: JobQueue 인스턴스 (None이면 내부 생성)
        """
        self.job_queue = job_queue or JobQueue()
        logger.info("✅ LocalGridSearchTuner 초기화")
    
    def create_run_and_jobs(self, config: LocalGridSearchConfig) -> str:
        """
        Local Grid Search Run 생성 및 Jobs enqueue
        
        Process:
        1. Config 검증
        2. Base run에서 Top K 후보 조회
        3. 각 후보 주변 그리드 생성
        4. tuning.runs 레코드 생성
        5. tuning.jobs enqueue
        
        Args:
            config: LocalGridSearchConfig
        
        Returns:
            str: 생성된 run_id
        
        Raises:
            ValueError: Config 또는 base_run이 유효하지 않을 때
        """
        # 1. Config 검증
        config.validate()
        logger.info(f"[LocalGrid] Run 생성 시작: {config.run_name}")
        logger.info(f"[LocalGrid]   Base Run: {config.base_run_id}")
        logger.info(f"[LocalGrid]   Top K: {config.top_k}")
        logger.info(f"[LocalGrid]   Grid Steps: {config.grid_steps}")
        logger.info(f"[LocalGrid]   Step Factor: {config.step_factor}")
        
        # 2. Base run 메타데이터 및 ParamSpace 조회
        base_metadata = self._get_base_run_metadata(config.base_run_id)
        
        if not base_metadata:
            raise ValueError(f"❌ Base run을 찾을 수 없음: {config.base_run_id}")
        
        # ParamSpace 복원
        param_space_dict = base_metadata.get('param_space', {})
        if not param_space_dict:
            raise ValueError(f"❌ Base run에 param_space 정보 없음: {config.base_run_id}")
        
        param_space = ParamSpace(space=param_space_dict)
        param_space.validate()
        
        logger.info(f"[LocalGrid]   ParamSpace: {list(param_space.space.keys())}")
        
        # 3. Base run에서 Top K 후보 조회
        top_k_candidates = self._get_top_k_candidates(
            base_run_id=config.base_run_id,
            target_metric=config.target_metric,
            k=config.top_k
        )
        
        if not top_k_candidates:
            raise ValueError(f"❌ Base run에 결과 없음: {config.base_run_id}")
        
        logger.info(f"[LocalGrid]   Top K 후보 조회: {len(top_k_candidates)}개")
        
        # 4. 각 후보 주변 그리드 생성
        all_grid_params = []
        
        for idx, candidate in enumerate(top_k_candidates):
            candidate_params = candidate['params_json']
            logger.info(f"[LocalGrid]   후보 {idx+1}: {candidate_params}")
            
            grid_params = self._generate_grid_around_candidate(
                params=candidate_params,
                param_space=param_space,
                grid_steps=config.grid_steps,
                step_factor=config.step_factor
            )
            
            logger.info(f"[LocalGrid]     → Grid: {len(grid_params)}개 조합")
            all_grid_params.extend(grid_params)
        
        # 중복 제거 (dict를 tuple로 변환하여 set 사용)
        unique_grid_params = []
        seen = set()
        
        for params in all_grid_params:
            params_tuple = tuple(sorted(params.items()))
            if params_tuple not in seen:
                seen.add(params_tuple)
                unique_grid_params.append(params)
        
        logger.info(f"[LocalGrid]   총 Grid 조합: {len(unique_grid_params)}개 (중복 제거 후)")
        
        # 5. Run 생성
        run_id = str(uuid.uuid4())
        
        metadata = {
            'base_run_id': config.base_run_id,
            'top_k': config.top_k,
            'grid_steps': config.grid_steps,
            'step_factor': config.step_factor,
            'param_space': param_space_dict,
            'base_config_path': config.base_config_path
        }
        
        config_override = {
            'base_config_path': config.base_config_path
        }
        
        self.job_queue.create_run(
            run_id=run_id,
            run_name=config.run_name,
            phase=config.phase,
            strategy_family=config.strategy_family,
            strategy_name=config.strategy_name,
            mode=config.mode,
            tuning_method=config.tuning_method,
            target_metric=config.target_metric,
            total_jobs=len(unique_grid_params),
            metadata=metadata,
            config_override=config_override
        )
        
        logger.info(f"✅ Run 생성: {run_id}")
        
        # 6. Jobs enqueue
        for params in unique_grid_params:
            self.job_queue.enqueue_job(
                run_id=run_id,
                params=params
            )
        
        logger.info(f"✅ Jobs enqueue 완료: {len(unique_grid_params)}개")
        
        return run_id
    
    def _get_base_run_metadata(self, base_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Base run의 메타데이터 조회
        
        Args:
            base_run_id: Base run ID
        
        Returns:
            Dict[str, Any]: 메타데이터 (param_space 포함)
        """
        from database import get_db_connection
        
        sql = """
        SELECT metadata
        FROM tuning.runs
        WHERE run_id = %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (base_run_id,))
                row = cur.fetchone()
        
        if row and row[0]:
            return row[0]
        
        return None
    
    def _get_top_k_candidates(
        self,
        base_run_id: str,
        target_metric: str,
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Base run에서 Top K 후보 조회
        
        Args:
            base_run_id: Base run ID
            target_metric: 최적화 대상 메트릭
            k: 상위 K개
        
        Returns:
            List[Dict]: Top K 후보 리스트
                [{'params_json': {...}, 'metrics': {...}}, ...]
        """
        from database import get_db_connection
        
        # target_metric에 따라 정렬 방향 결정
        # sharpe_ratio, profit_factor, win_rate → DESC (높을수록 좋음)
        # max_drawdown, max_drawdown_duration_hours → ASC (낮을수록 좋음)
        
        ascending_metrics = ['max_drawdown', 'max_drawdown_duration_hours']
        order_direction = 'ASC' if target_metric in ascending_metrics else 'DESC'
        
        sql = f"""
        SELECT j.params_json, r.metrics
        FROM tuning.jobs j
        JOIN tuning.results r ON j.job_id = r.job_id
        WHERE j.run_id = %s
          AND j.status = 'COMPLETED'
          AND r.metrics->>%s IS NOT NULL
        ORDER BY (r.metrics->>%s)::float {order_direction}
        LIMIT %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (base_run_id, target_metric, target_metric, k))
                rows = cur.fetchall()
        
        candidates = []
        for row in rows:
            candidates.append({
                'params_json': row[0],
                'metrics': row[1]
            })
        
        return candidates
    
    def _generate_grid_around_candidate(
        self,
        params: Dict[str, Any],
        param_space: ParamSpace,
        grid_steps: int,
        step_factor: float
    ) -> List[Dict[str, Any]]:
        """
        단일 후보 주변 그리드 생성
        
        Args:
            params: 중심 파라미터
            param_space: ParamSpace (범위 정의)
            grid_steps: 그리드 스텝 수
            step_factor: 스텝 크기 비율
        
        Returns:
            List[Dict]: 그리드 파라미터 조합 리스트
        
        Examples:
            >>> params = {'rsi_oversold': 30, 'stop_loss_pct': 1.0}
            >>> param_space = ParamSpace(space={
            ...     'rsi_oversold': {'type': 'int', 'min': 20, 'max': 40},
            ...     'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0}
            ... })
            >>> grid = _generate_grid_around_candidate(params, param_space, grid_steps=3, step_factor=0.1)
            >>> len(grid)
            9  # 3 x 3
        """
        # 각 파라미터별 그리드 값 생성
        param_grids = {}
        
        for param_name, spec in param_space.space.items():
            center_value = params.get(param_name)
            
            if center_value is None:
                # 파라미터가 없으면 스킵 (Base run과 일치하지 않는 경우)
                logger.warning(f"⚠️  파라미터 '{param_name}'가 후보에 없음, 스킵")
                continue
            
            param_type = spec['type']
            
            if param_type == 'int':
                # int: center ± step * (grid_steps // 2)
                half_steps = grid_steps // 2
                step = 1  # int는 step = 1
                
                grid_values = []
                for i in range(-half_steps, half_steps + 1):
                    value = center_value + i * step
                    
                    # 범위 제한
                    value = max(spec['min'], min(spec['max'], value))
                    grid_values.append(value)
                
                param_grids[param_name] = sorted(set(grid_values))
            
            elif param_type == 'float':
                # float: center ± delta * (grid_steps // 2)
                half_steps = grid_steps // 2
                param_range = spec['max'] - spec['min']
                delta = param_range * step_factor
                
                grid_values = []
                for i in range(-half_steps, half_steps + 1):
                    value = center_value + i * delta
                    
                    # 범위 제한
                    value = max(spec['min'], min(spec['max'], value))
                    grid_values.append(round(value, 4))
                
                param_grids[param_name] = sorted(set(grid_values))
            
            elif param_type == 'categorical':
                # categorical: 중심값만 사용
                param_grids[param_name] = [center_value]
            
            else:
                logger.warning(f"⚠️  알 수 없는 파라미터 타입: {param_type}")
                param_grids[param_name] = [center_value]
        
        # 조합 생성 (Cartesian product)
        param_names = sorted(param_grids.keys())
        param_values_list = [param_grids[name] for name in param_names]
        
        grid_combinations = []
        for combo in itertools.product(*param_values_list):
            params_dict = dict(zip(param_names, combo))
            grid_combinations.append(params_dict)
        
        return grid_combinations
    
    def get_top_k_results(
        self,
        run_id: str,
        k: int = 10,
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run 결과에서 Top K 조회
        
        Args:
            run_id: Run ID
            k: 상위 K개
            ascending: True이면 오름차순 (MaxDD 같은 경우)
        
        Returns:
            List[Dict]: Top K 결과
                [{'job_id', 'params_json', 'metrics', ...}, ...]
        """
        from database import get_db_connection
        
        # target_metric 조회
        sql_run = """
        SELECT target_metric
        FROM tuning.runs
        WHERE run_id = %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_run, (run_id,))
                run_row = cur.fetchone()
        
        if not run_row:
            logger.warning(f"❌ Run을 찾을 수 없음: {run_id}")
            return []
        
        target_metric = run_row[0]
        order_direction = 'ASC' if ascending else 'DESC'
        
        sql = f"""
        SELECT
            j.job_id,
            j.params_json,
            r.metrics,
            r.created_at
        FROM tuning.jobs j
        JOIN tuning.results r ON j.job_id = r.job_id
        WHERE j.run_id = %s
          AND j.status = 'COMPLETED'
          AND r.metrics->>%s IS NOT NULL
        ORDER BY (r.metrics->>%s)::float {order_direction}
        LIMIT %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (run_id, target_metric, target_metric, k))
                rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'job_id': row[0],
                'params_json': row[1],
                'metrics': row[2],
                'created_at': row[3]
            })
        
        return results
    
    # ========================================
    # PHASE28-5: Sequential Local Grid Search
    # ========================================
    
    def run_from_seeds(
        self,
        run_id_prefix: str,
        seed_trials: List[Dict[str, Any]],
        param_space: ParamSpace,
        grid_config: Dict[str, Any],
        base_config_path: str,
        mode: str = 'backtest',
        strategy_name: str = 'btc5m_baseline_v1',
        target_metric: str = 'sharpe_ratio'
    ) -> List[str]:
        """
        PHASE28-5: Seed trials 기반 Sequential Local Grid Search
        
        BayesianSearchTuner.run_sequential()과 유사한 구조로,
        각 seed 주변 grid를 생성하여 순차 실행
        
        Args:
            run_id_prefix: Run ID prefix (예: 'phase28_5_localgrid')
            seed_trials: Seed trial 리스트 [{'params_json': {...}, ...}, ...]
            param_space: ParamSpace 인스턴스
            grid_config: Grid 생성 설정
                {
                    'core_params': ['rsi_long_threshold', ...],  # Grid 대상
                    'int_delta': 2,
                    'float_ratio': 0.05,
                    'discrete_neighbors': 1,
                    'max_jobs': 30
                }
            base_config_path: Base config 파일 경로
            mode: 실행 모드 ('backtest')
            strategy_name: 전략 이름
            target_metric: 목표 메트릭
        
        Returns:
            생성된 run_id 리스트
        """
        import time
        import json
        import uuid
        from database import get_db_connection
        
        logger.info("=" * 80)
        logger.info(f"🔍 [PHASE28-5] Local Grid Search: Sequential Execution")
        logger.info("=" * 80)
        logger.info(f"Run ID Prefix: {run_id_prefix}")
        logger.info(f"Seed Trials: {len(seed_trials)}")
        logger.info(f"Grid Config: {grid_config}")
        logger.info(f"Base Config: {base_config_path}")
        logger.info("=" * 80)
        
        run_ids = []
        
        for seed_idx, seed_trial in enumerate(seed_trials, 1):
            seed_params = seed_trial['params_json']
            
            logger.info(f"\n🌱 Seed {seed_idx}/{len(seed_trials)}")
            logger.info(f"  Params: {seed_params}")
            
            # 1. Grid 생성
            grid_params_list = self._build_grid_phase28_5(
                seed_params=seed_params,
                param_space=param_space,
                grid_config=grid_config
            )
            
            logger.info(f"  Generated Grid: {len(grid_params_list)} combinations")
            
            # max_jobs 제한
            max_jobs = grid_config.get('max_jobs', 30)
            if len(grid_params_list) > max_jobs:
                import random
                random.shuffle(grid_params_list)
                grid_params_list = grid_params_list[:max_jobs]
                logger.warning(f"  ⚠️  Grid size exceeds max_jobs, sampled {max_jobs} combinations")
            
            # 2. Run 생성
            run_id = f"{run_id_prefix}_seed{seed_idx}_{uuid.uuid4().hex[:8]}"
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO tuning.runs (
                            run_id, phase, strategy_family, strategy_name,
                            mode, tuning_method, target_metric, total_jobs,
                            completed_jobs, failed_jobs, status,
                            metadata, config_override, created_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, NOW()
                        )
                    """, (
                        run_id,
                        "PHASE28-5",
                        "mean_reversion",
                        strategy_name,
                        mode,
                        "grid",  # tuning_method: 'random', 'bayesian', 'grid', 'manual'
                        target_metric,
                        len(grid_params_list),
                        0,  # completed_jobs
                        0,  # failed_jobs
                        'RUNNING',  # status
                        json.dumps({
                            'seed_idx': seed_idx,
                            'seed_params': seed_params,
                            'grid_config': grid_config,
                            'param_space': param_space.space
                        }),
                        json.dumps({'base_config_path': base_config_path})
                    ))
                conn.commit()
            
            logger.info(f"  ✅ Run created: {run_id}")
            run_ids.append(run_id)
            
            # 3. 각 grid point 순차 실행
            for job_idx, grid_params in enumerate(grid_params_list):
                try:
                    self._run_single_trial_phase28_5(
                        run_id=run_id,
                        job_index=job_idx,
                        params=grid_params,
                        base_config_path=base_config_path,
                        mode=mode,
                        strategy_name=strategy_name,
                        target_metric=target_metric
                    )
                except Exception as e:
                    logger.error(f"  ❌ Trial {job_idx} failed: {e}")
                    continue
            
            logger.info(f"  ✅ Seed {seed_idx} completed: {len(grid_params_list)} trials")
        
        logger.info("=" * 80)
        logger.info(f"🎉 [PHASE28-5] Local Grid Search completed: {len(run_ids)} runs")
        logger.info("=" * 80)
        
        return run_ids
    
    def _build_grid_phase28_5(
        self,
        seed_params: Dict[str, Any],
        param_space: ParamSpace,
        grid_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        PHASE28-5: Seed 주변 grid 생성 (core params만 변경)
        
        Args:
            seed_params: Seed trial의 파라미터
            param_space: ParamSpace
            grid_config: Grid 생성 설정
        
        Returns:
            파라미터 조합 리스트
        """
        import itertools
        
        core_params = grid_config.get('core_params', [])
        int_delta = grid_config.get('int_delta', 2)
        float_ratio = grid_config.get('float_ratio', 0.05)
        discrete_neighbors = grid_config.get('discrete_neighbors', 1)
        
        # 각 파라미터별 grid 값 생성
        param_grids = {}
        
        for param_name in seed_params.keys():
            center_value = seed_params[param_name]
            spec = param_space.space.get(param_name)
            
            if not spec:
                # ParamSpace에 없는 파라미터는 고정
                param_grids[param_name] = [center_value]
                continue
            
            # Core params가 아니면 고정
            if param_name not in core_params:
                param_grids[param_name] = [center_value]
                continue
            
            param_type = spec['type']
            
            if param_type == 'int':
                # int: center ± int_delta (3 points only: -delta, 0, +delta)
                grid_values = []
                for multiplier in [-1, 0, 1]:
                    value = center_value + multiplier * int_delta
                    value = max(spec['min'], min(spec['max'], value))
                    grid_values.append(value)
                param_grids[param_name] = sorted(set(grid_values))
            
            elif param_type == 'float':
                # float: center ± (range * float_ratio)
                param_range = spec['max'] - spec['min']
                delta = param_range * float_ratio
                
                grid_values = []
                for multiplier in [-1, 0, 1]:
                    value = center_value + multiplier * delta
                    value = max(spec['min'], min(spec['max'], value))
                    grid_values.append(round(value, 4))
                param_grids[param_name] = sorted(set(grid_values))
            
            elif param_type == 'categorical':
                # categorical: center 주변 이웃 (3 points only: -neighbors, 0, +neighbors)
                candidates = spec.get('values', [center_value])
                try:
                    center_idx = candidates.index(center_value)
                except ValueError:
                    # center_value가 candidates에 없으면 고정
                    param_grids[param_name] = [center_value]
                    continue
                
                grid_values = []
                for multiplier in [-1, 0, 1]:
                    offset = multiplier * discrete_neighbors
                    idx = center_idx + offset
                    if 0 <= idx < len(candidates):
                        grid_values.append(candidates[idx])
                param_grids[param_name] = list(set(grid_values))
            
            else:
                # 알 수 없는 타입은 고정
                param_grids[param_name] = [center_value]
        
        # Cartesian product
        param_names = sorted(param_grids.keys())
        param_values_list = [param_grids[name] for name in param_names]
        
        grid_combinations = []
        for combo in itertools.product(*param_values_list):
            params_dict = dict(zip(param_names, combo))
            grid_combinations.append(params_dict)
        
        return grid_combinations
    
    def _run_single_trial_phase28_5(
        self,
        run_id: str,
        job_index: int,
        params: Dict[str, Any],
        base_config_path: str,
        mode: str,
        strategy_name: str,
        target_metric: str
    ) -> Dict[str, Any]:
        """
        PHASE28-5: 단일 trial 실행 (BayesianSearchTuner._run_single_trial과 동일 구조)
        
        Args:
            run_id: Run ID
            job_index: Job index
            params: 파라미터
            base_config_path: Base config 경로
            mode: 실행 모드
            strategy_name: 전략 이름
            target_metric: 목표 메트릭
        
        Returns:
            메트릭 딕셔너리
        """
        import time
        import json
        import traceback
        from execution.engine import run_v2
        from tuning.utils.config_builder import build_tuning_config
        from database import get_db_connection
        
        start_time = time.time()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"  🔬 Trial {job_index}: {job_id}")
        
        # 1. Job 레코드 생성
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tuning.jobs (
                        job_id, run_id, job_index, params_json, status
                    ) VALUES (%s, %s, %s, %s, 'RUNNING')
                """, (job_id, run_id, job_index, json.dumps(params)))
            conn.commit()
        
        try:
            # 2. Config 생성 (build_tuning_config 재사용)
            final_config = build_tuning_config(
                base_config_path=base_config_path,
                strategy_params=params,
                trial_id=job_id,
                run_id=run_id,
                mode=mode,
                period_override=None
            )
            
            # 3. 백테스트 실행
            run_v2(mode=mode, config=final_config, clean_state=True)
            
            # 4. 메트릭 추출 (BayesianSearchTuner와 동일)
            metrics = self._extract_metrics_from_db_phase28_5(run_id, job_id)
            
            # 5. Runtime 추가
            runtime_sec = time.time() - start_time
            metrics['runtime_sec'] = round(runtime_sec, 3)
            
            # 6. DB 저장
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Job 완료
                    cur.execute("""
                        UPDATE tuning.jobs
                        SET status = 'COMPLETED',
                            completed_at = NOW()
                        WHERE job_id = %s
                    """, (job_id,))
                    
                    # Result 삽입
                    cur.execute("""
                        INSERT INTO tuning.results (
                            result_id, job_id, run_id,
                            pnl, pnl_pct, trade_count, win_count, lose_count,
                            win_rate, sharpe_ratio, max_drawdown,
                            max_drawdown_duration_hours, profit_factor,
                            avg_win, avg_lose, runtime_sec, metrics_json
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s
                        )
                    """, (
                        f"result_{uuid.uuid4().hex[:12]}", job_id, run_id,
                        metrics.get('pnl', 0.0),
                        metrics.get('pnl_pct', 0.0),
                        metrics.get('trade_count', 0),
                        metrics.get('win_count', 0),
                        metrics.get('lose_count', 0),
                        metrics.get('win_rate', 0.0),
                        metrics.get('sharpe_ratio', 0.0),
                        metrics.get('max_drawdown', 0.0),
                        metrics.get('max_drawdown_duration_hours', 0.0),
                        metrics.get('profit_factor', 0.0),
                        metrics.get('avg_win', 0.0),
                        metrics.get('avg_lose', 0.0),
                        runtime_sec,
                        json.dumps(metrics)
                    ))
                    
                    # Run 통계 업데이트
                    cur.execute("""
                        UPDATE tuning.runs
                        SET completed_jobs = completed_jobs + 1
                        WHERE run_id = %s
                    """, (run_id,))
                conn.commit()
            
            logger.info(f"    ✅ Trial {job_index} completed: {target_metric}={metrics.get(target_metric, 0.0):.4f}")
            return metrics
        
        except Exception as e:
            # 실패 처리
            error_msg = f"{type(e).__name__}: {str(e)}"
            runtime_sec = time.time() - start_time
            
            logger.error(f"    ❌ Trial {job_index} failed: {error_msg}")
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE tuning.jobs
                        SET status = 'FAILED',
                            error_message = %s,
                            completed_at = NOW()
                        WHERE job_id = %s
                    """, (error_msg[:500], job_id))
                conn.commit()
            
            # 실패한 경우에도 빈 메트릭 반환
            return {
                'pnl': 0.0,
                'sharpe_ratio': 0.0,
                'trade_count': 0,
                'runtime_sec': runtime_sec,
                'error': error_msg
            }
    
    def _extract_metrics_from_db_phase28_5(
        self,
        run_id: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        PHASE28-5: DB에서 메트릭 추출 (BayesianSearchTuner와 동일)
        
        Args:
            run_id: Run ID
            job_id: Job ID
        
        Returns:
            메트릭 딕셔너리
        """
        from database import get_db_connection
        
        # trading.trades 테이블에서 trial_id 기준으로 집계
        sql = """
        SELECT
            COUNT(*) as trade_count,
            COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0) as win_count,
            COALESCE(SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END), 0) as lose_count,
            COALESCE(SUM(pnl), 0.0) as pnl,
            COALESCE(AVG(CASE WHEN pnl > 0 THEN pnl ELSE NULL END), 0.0) as avg_win,
            COALESCE(AVG(CASE WHEN pnl <= 0 THEN pnl ELSE NULL END), 0.0) as avg_lose
        FROM trading.trades
        WHERE trial_id = %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (job_id,))
                row = cur.fetchone()
        
        trade_count = row[0] if row else 0
        win_count = row[1] if row else 0
        lose_count = row[2] if row else 0
        pnl = float(row[3]) if row else 0.0
        avg_win = float(row[4]) if row else 0.0
        avg_lose = float(row[5]) if row else 0.0
        
        # 계산된 메트릭
        win_rate = (win_count / trade_count) if trade_count > 0 else 0.0
        profit_factor = (abs(avg_win * win_count) / abs(avg_lose * lose_count)) if lose_count > 0 and avg_lose != 0 else 0.0
        
        # PnL %
        initial_balance = 50000.0  # Base config 기준
        pnl_pct = (pnl / initial_balance) if initial_balance > 0 else 0.0
        
        # Sharpe-like (간단 버전)
        sharpe_ratio = 0.0
        if trade_count > 0 and avg_lose != 0:
            sharpe_ratio = pnl / abs(avg_lose * lose_count) if lose_count > 0 else (pnl / abs(avg_win) if avg_win != 0 else 0.0)
        
        # Max Drawdown (간략 계산)
        max_drawdown = abs(pnl) if pnl < 0 else 0.0
        
        metrics = {
            'trade_count': trade_count,
            'win_count': win_count,
            'lose_count': lose_count,
            'win_rate': round(win_rate, 4),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 4),
            'avg_win': round(avg_win, 2),
            'avg_lose': round(avg_lose, 2),
            'profit_factor': round(profit_factor, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_duration_hours': 0.0
        }
        
        return metrics
