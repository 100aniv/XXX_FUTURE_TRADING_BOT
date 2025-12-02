#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Grid Search Tuner
=======================
PHASE25-4: Local Grid Search 기반 하이퍼파라미터 튜닝

주요 기능:
- Random/Bayesian에서 얻은 Best K 후보 주변 국소 그리드 탐색
- 각 후보의 파라미터를 중심으로 그리드 생성
- JobQueue와 통합

알고리즘:
1. Base run (Random/Bayesian)에서 Top K 후보 조회
2. 각 후보 주변 그리드 생성:
   - int: center ± step * (grid_steps // 2)
   - float: center ± delta * (grid_steps // 2), delta = (max - min) * step_factor
   - categorical: 중심값만 사용
3. 생성된 조합을 tuning.jobs에 enqueue

사용법:
    from tuning.algorithms import LocalGridSearchTuner, LocalGridSearchConfig
    
    # Config 설정
    config = LocalGridSearchConfig(
        run_name='scalping_local_grid',
        phase='PHASE25-4',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='local_grid',
        target_metric='sharpe_ratio',
        base_run_id='<Random or Bayesian run_id>',
        top_k=3,
        grid_steps=3,
        step_factor=0.1,
        base_config_path='configs/paper/phase21_scalping_quick.yml'
    )
    
    # Tuner 생성 및 실행
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
