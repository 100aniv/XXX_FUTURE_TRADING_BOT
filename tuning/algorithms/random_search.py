#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Random Search Tuner
===================
PHASE25-2: Random Search 기반 하이퍼파라미터 튜닝

주요 기능:
- ParamSpace 정의 및 랜덤 샘플링
- Run 생성 및 Job enqueue
- JobQueue와 통합

사용법:
    from tuning.algorithms import RandomSearchTuner, ParamSpace, RandomSearchConfig
    
    # Param space 정의
    param_space = ParamSpace(space={
        'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        'rsi_overbought': {'type': 'int', 'min': 65, 'max': 75},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
    })
    
    # Random Search 설정
    config = RandomSearchConfig(
        run_name='scalping_rsi_tuning',
        phase='PHASE25-2',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='random',
        target_metric='sharpe_ratio',
        n_trials=50,
        base_config_path='configs/paper/phase21_scalping_quick.yml',
        param_space=param_space,
        seed=42
    )
    
    # Tuner 생성 및 실행
    tuner = RandomSearchTuner()
    run_id, job_ids = tuner.create_run_and_jobs(config)
"""
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path

from tuning.cluster.job_queue import JobQueue
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


@dataclass
class ParamSpace:
    """
    하이퍼파라미터 탐색 공간
    
    Attributes:
        space: 파라미터 정의 딕셔너리
            {
                'param_name': {
                    'type': 'int' | 'float' | 'categorical',
                    'min': float (int/float일 때),
                    'max': float (int/float일 때),
                    'values': List[Any] (categorical일 때),
                    'log': bool (optional, log-uniform sampling)
                }
            }
    
    Examples:
        >>> space = ParamSpace(space={
        ...     'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        ...     'ema_fast': {'type': 'int', 'min': 5, 'max': 20},
        ...     'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0, 'log': False},
        ...     'leverage': {'type': 'categorical', 'values': [5, 10, 20]},
        ... })
    """
    space: Dict[str, Dict[str, Any]]
    
    def validate(self) -> bool:
        """
        ParamSpace 검증
        
        Returns:
            bool: 검증 성공 여부
        
        Raises:
            ValueError: 스펙이 유효하지 않을 때
        """
        for param_name, spec in self.space.items():
            if 'type' not in spec:
                raise ValueError(f"❌ '{param_name}': 'type' 필드 필수")
            
            param_type = spec['type']
            
            if param_type in ('int', 'float'):
                if 'min' not in spec or 'max' not in spec:
                    raise ValueError(f"❌ '{param_name}': 'min', 'max' 필드 필수 (type={param_type})")
                if spec['min'] >= spec['max']:
                    raise ValueError(f"❌ '{param_name}': min >= max ({spec['min']} >= {spec['max']})")
            
            elif param_type == 'categorical':
                if 'values' not in spec or not spec['values']:
                    raise ValueError(f"❌ '{param_name}': 'values' 필드 필수이며 비어있으면 안 됨 (type=categorical)")
            
            else:
                raise ValueError(f"❌ '{param_name}': 지원하지 않는 type '{param_type}' (가능: int, float, categorical)")
        
        logger.info(f"✅ ParamSpace 검증 완료 ({len(self.space)}개 파라미터)")
        return True
    
    def sample(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """
        ParamSpace에서 랜덤 샘플링
        
        Args:
            seed: Random seed (재현성)
        
        Returns:
            샘플링된 파라미터 딕셔너리
        
        Examples:
            >>> space = ParamSpace(space={'rsi': {'type': 'int', 'min': 25, 'max': 35}})
            >>> params = space.sample(seed=42)
            >>> print(params)
            {'rsi': 30}
        """
        if seed is not None:
            random.seed(seed)
        
        params = {}
        
        for param_name, spec in self.space.items():
            param_type = spec['type']
            
            if param_type == 'int':
                value = random.randint(spec['min'], spec['max'])
            
            elif param_type == 'float':
                if spec.get('log', False):
                    # Log-uniform sampling
                    import math
                    log_min = math.log(spec['min'])
                    log_max = math.log(spec['max'])
                    value = math.exp(random.uniform(log_min, log_max))
                else:
                    # Uniform sampling
                    value = random.uniform(spec['min'], spec['max'])
            
            elif param_type == 'categorical':
                value = random.choice(spec['values'])
            
            else:
                raise ValueError(f"❌ 지원하지 않는 type '{param_type}'")
            
            params[param_name] = value
        
        return params


@dataclass
class RandomSearchConfig:
    """
    Random Search 튜닝 설정
    
    Attributes:
        run_name: Run 이름 (사람이 읽을 수 있는 이름)
        phase: PHASE 번호 (예: 'PHASE25-2')
        strategy_family: 전략 패밀리 (예: 'momentum', 'volatility')
        strategy_name: 전략 이름 (예: 'scalping', 'trend_follow_v2')
        mode: 실행 모드 ('backtest', 'paper')
        tuning_method: 튜닝 방법 (고정: 'random_search')
        target_metric: 최적화 목표 메트릭 (예: 'sharpe_ratio', 'pnl_pct')
        n_trials: 총 trial 수
        base_config_path: 기본 config YAML 경로
        param_space: ParamSpace 인스턴스
        seed: Random seed (재현성)
        metadata: 추가 메타데이터
    """
    run_name: str
    phase: str
    strategy_family: str
    strategy_name: str
    mode: str
    tuning_method: str
    target_metric: str
    n_trials: int
    base_config_path: str
    param_space: ParamSpace
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """
        Config 검증
        
        Returns:
            bool: 검증 성공 여부
        
        Raises:
            ValueError: 설정이 유효하지 않을 때
        """
        if self.n_trials <= 0:
            raise ValueError(f"❌ n_trials는 1 이상이어야 함 (현재: {self.n_trials})")
        
        if self.mode not in ('backtest', 'paper'):
            raise ValueError(f"❌ mode는 'backtest' 또는 'paper'만 지원 (현재: {self.mode})")
        
        if not Path(self.base_config_path).exists():
            raise ValueError(f"❌ base_config_path 파일 없음: {self.base_config_path}")
        
        # ParamSpace 검증
        self.param_space.validate()
        
        logger.info(f"✅ RandomSearchConfig 검증 완료")
        return True


class RandomSearchTuner:
    """Random Search 튜닝 실행기"""
    
    def __init__(self, job_queue: Optional[JobQueue] = None):
        """
        Args:
            job_queue: JobQueue 인스턴스 (None이면 자동 생성)
        """
        self.job_queue = job_queue or JobQueue()
        logger.info("🎯 RandomSearchTuner 초기화 완료")
    
    def create_run_and_jobs(self, config: RandomSearchConfig) -> Tuple[str, List[str]]:
        """
        Run 생성 및 Job enqueue
        
        Args:
            config: RandomSearchConfig 인스턴스
        
        Returns:
            Tuple[str, List[str]]: (run_id, [job_id1, job_id2, ...])
        
        Raises:
            ValueError: 설정이 유효하지 않을 때
        """
        # 1. Config 검증
        config.validate()
        
        # 2. Run ID 생성
        run_id = f"{config.run_name}_{uuid.uuid4().hex[:8]}"
        logger.info("=" * 80)
        logger.info(f"🚀 Random Search 시작: {run_id}")
        logger.info("=" * 80)
        logger.info(f"📊 전략: {config.strategy_name} ({config.strategy_family})")
        logger.info(f"🎯 Target: {config.target_metric}")
        logger.info(f"🔢 Trials: {config.n_trials}")
        logger.info(f"🛠️  Mode: {config.mode}")
        logger.info(f"📄 Base Config: {config.base_config_path}")
        logger.info(f"🌱 Seed: {config.seed}")
        
        # 3. Run 생성
        metadata = {
            'run_name': config.run_name,
            'base_config_path': config.base_config_path,
            'param_space': config.param_space.space,
            **config.metadata
        }
        
        success = self.job_queue.create_run(
            run_id=run_id,
            phase=config.phase,
            strategy_family=config.strategy_family,
            strategy_name=config.strategy_name,
            mode=config.mode,
            tuning_method=config.tuning_method,
            target_metric=config.target_metric,
            total_jobs=config.n_trials,
            seed=config.seed,
            config_override={'base_config_path': config.base_config_path},
            metadata=metadata
        )
        
        if not success:
            raise RuntimeError(f"❌ Run 생성 실패: {run_id}")
        
        # 4. Random sampling으로 params 생성
        logger.info(f"🎲 Random sampling {config.n_trials}개 params...")
        
        all_params = []
        for trial_idx in range(config.n_trials):
            # Seed 설정 (재현성)
            trial_seed = None
            if config.seed is not None:
                trial_seed = config.seed + trial_idx
            
            # Sample
            params = config.param_space.sample(seed=trial_seed)
            all_params.append(params)
        
        logger.info(f"✅ Sampling 완료: {len(all_params)}개")
        
        # 5. Job enqueue
        logger.info(f"📝 Job enqueue 중...")
        job_ids = []
        
        for job_index, params in enumerate(all_params):
            job_id = self.job_queue.enqueue_job(
                run_id=run_id,
                job_index=job_index,
                params=params
            )
            
            if job_id:
                job_ids.append(job_id)
            else:
                logger.warning(f"⚠️  Job enqueue 실패: run={run_id}, index={job_index}")
        
        logger.info(f"✅ Job enqueue 완료: {len(job_ids)}/{config.n_trials}개")
        logger.info("=" * 80)
        
        return run_id, job_ids
    
    def get_top_k_results(
        self,
        run_id: str,
        k: int = 10,
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run의 상위 k개 결과 조회
        
        Args:
            run_id: Run ID
            k: 상위 k개
            ascending: True이면 오름차순 (작을수록 좋음), False이면 내림차순 (클수록 좋음)
        
        Returns:
            List[Dict[str, Any]]: 상위 k개 결과 리스트
        """
        results = self.job_queue.get_run_results(run_id)
        
        if not results:
            logger.warning(f"⚠️  Run '{run_id}' 결과 없음")
            return []
        
        # target_metric 기준 정렬
        # ascending=True: 작을수록 좋음 (예: max_drawdown)
        # ascending=False: 클수록 좋음 (예: sharpe_ratio, pnl_pct)
        results_sorted = sorted(results, key=lambda x: x.get('sharpe_ratio', 0), reverse=not ascending)
        
        top_k = results_sorted[:k]
        
        logger.info(f"📊 Top {k} 결과 (run={run_id}):")
        for i, result in enumerate(top_k, 1):
            logger.info(f"  [{i}] Sharpe={result.get('sharpe_ratio', 0):.4f}, "
                       f"PnL={result.get('pnl', 0):.2f}, "
                       f"Win Rate={result.get('win_rate', 0):.2%}")
        
        return top_k
