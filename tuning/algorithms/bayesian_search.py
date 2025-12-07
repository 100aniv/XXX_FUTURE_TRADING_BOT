#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian Search Tuner (Optuna 기반)
===================================
PHASE25-3: Bayesian Optimization을 이용한 하이퍼파라미터 튜닝

주요 기능:
- Optuna TPE 알고리즘 활용
- ParamSpace를 Optuna suggest API로 변환
- Sequential 튜닝 (단일 프로세스)
- JobQueue와 통합

사용법:
    from tuning.algorithms import BayesianSearchTuner, ParamSpace, BayesianSearchConfig
    
    # Param space 정의
    param_space = ParamSpace(space={
        'rsi_oversold': {'type': 'int', 'min': 25, 'max': 35},
        'rsi_overbought': {'type': 'int', 'min': 65, 'max': 75},
        'stop_loss_pct': {'type': 'float', 'min': 0.5, 'max': 2.0},
    })
    
    # Bayesian Search 설정
    config = BayesianSearchConfig(
        run_name='scalping_bayes_tuning',
        phase='PHASE25-3',
        strategy_family='momentum',
        strategy_name='scalping',
        mode='backtest',
        tuning_method='bayesian',
        target_metric='sharpe_ratio',
        n_trials=30,
        base_config_path='configs/backtest/scalping_mini.yml',
        param_space=param_space,
        direction='maximize',
        seed=42
    )
    
    # Tuner 생성 및 실행
    tuner = BayesianSearchTuner()
    run_id = tuner.run_sequential(config)
    
    # 결과 조회
    top_results = tuner.get_top_k_results(run_id, k=10)
"""
import time
import uuid
import json
import traceback
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    optuna = None

from tuning.cluster.job_queue import JobQueue
from tuning.algorithms.random_search import ParamSpace
from common.logger import setup_logger
from database import get_db_connection

logger = setup_logger(__name__, log_type="application")


@dataclass
class BayesianSearchConfig:
    """
    Bayesian Search 설정
    
    Attributes:
        run_name: Run 이름
        phase: PHASE 번호
        strategy_family: 전략 패밀리
        strategy_name: 전략 이름
        mode: 실행 모드 ('backtest', 'paper', 'live')
        tuning_method: 'bayesian'
        target_metric: 최적화 목표 메트릭
        n_trials: Trial 수
        base_config_path: 기본 Config 파일 경로
        param_space: ParamSpace 인스턴스
        direction: 'maximize' or 'minimize'
        seed: Random seed
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
    direction: str = "maximize"
    seed: Optional[int] = None
    
    def validate(self) -> bool:
        """
        Config 검증
        
        Returns:
            bool: 검증 성공 여부
        
        Raises:
            ValueError: Config가 유효하지 않을 때
        """
        if self.tuning_method != 'bayesian':
            raise ValueError(f"tuning_method must be 'bayesian', got '{self.tuning_method}'")
        
        if self.direction not in ('maximize', 'minimize'):
            raise ValueError(f"direction must be 'maximize' or 'minimize', got '{self.direction}'")
        
        if self.n_trials <= 0:
            raise ValueError(f"n_trials must be > 0, got {self.n_trials}")
        
        # ParamSpace 검증
        self.param_space.validate()
        
        # Base config 파일 존재 확인
        config_path = Path(self.base_config_path)
        if not config_path.exists():
            raise ValueError(f"base_config_path does not exist: {self.base_config_path}")
        
        logger.info("✅ BayesianSearchConfig 검증 완료")
        return True


class BayesianSearchTuner:
    """Bayesian Optimization 기반 하이퍼파라미터 튜너"""
    
    def __init__(self, job_queue: Optional[JobQueue] = None):
        """
        Args:
            job_queue: JobQueue 인스턴스 (없으면 자동 생성)
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError(
                "❌ Optuna가 설치되지 않았습니다. "
                "설치 방법: pip install optuna"
            )
        
        self.job_queue = job_queue or JobQueue()
        logger.info("🎯 BayesianSearchTuner 초기화 완료 (Optuna 사용)")
    
    def _suggest_params_from_space(
        self,
        trial: "optuna.Trial",
        param_space: ParamSpace
    ) -> Dict[str, Any]:
        """
        ParamSpace를 Optuna suggest API로 변환하여 파라미터 제안
        
        Args:
            trial: Optuna Trial
            param_space: ParamSpace 인스턴스
        
        Returns:
            제안된 파라미터 딕셔너리
        """
        params = {}
        
        for param_name, spec in param_space.space.items():
            param_type = spec['type']
            
            if param_type == 'int':
                params[param_name] = trial.suggest_int(
                    param_name,
                    spec['min'],
                    spec['max'],
                    log=spec.get('log', False)
                )
            elif param_type == 'float':
                params[param_name] = trial.suggest_float(
                    param_name,
                    spec['min'],
                    spec['max'],
                    log=spec.get('log', False)
                )
            elif param_type == 'categorical':
                params[param_name] = trial.suggest_categorical(
                    param_name,
                    spec['values']
                )
            else:
                raise ValueError(f"Unsupported param type: {param_type}")
        
        return params
    
    def _run_single_trial(
        self,
        run_id: str,
        job_index: int,
        params: Dict[str, Any],
        config: BayesianSearchConfig
    ) -> Dict[str, Any]:
        """
        단일 Trial 실행 (백테스트 + 메트릭 계산)
        
        Args:
            run_id: Run ID
            job_index: Job index
            params: 하이퍼파라미터 조합
            config: BayesianSearchConfig
        
        Returns:
            결과 메트릭 딕셔너리
        """
        import yaml
        from execution.engine import run_v2
        from common.config_loader import deep_merge
        
        start_time = time.time()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"🔬 Trial {job_index} 시작: {job_id}")
        logger.debug(f"  Params: {params}")
        
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
            # 2. PHASE28-4: 공통 config builder 사용 (TuningWorker와 100% 동일)
            from tuning.utils.config_builder import build_tuning_config
            
            # Period override는 필요 없음 (임시 config 파일에 이미 날짜 포함)
            final_config = build_tuning_config(
                base_config_path=config.base_config_path,
                strategy_params=params,
                trial_id=job_id,
                run_id=run_id,
                mode=config.mode,
                period_override=None  # 임시 config에 이미 period 날짜 포함
            )
            
            # 3. 백테스트 실행
            logger.info(f"  백테스트 실행 중 (mode={config.mode})...")
            run_v2(mode=config.mode, config=final_config, clean_state=True)
            
            # 5. 메트릭 추출
            metrics = self._extract_metrics_from_db(run_id, job_id)
            
            # 6. Job 완료 처리
            runtime_sec = time.time() - start_time
            metrics['runtime_sec'] = round(runtime_sec, 3)
            
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
            
            logger.info(f"✅ Trial {job_index} 완료: {job_id}")
            logger.info(f"  {config.target_metric}={metrics.get(config.target_metric, 0.0):.4f}")
            
            return metrics
        
        except Exception as e:
            # 실패 처리
            error_msg = f"{type(e).__name__}: {str(e)}"
            runtime_sec = time.time() - start_time
            
            logger.error(f"❌ Trial {job_index} 실패: {job_id}")
            logger.error(f"  Error: {error_msg}")
            logger.error(f"  Traceback:\n{traceback.format_exc()}")
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE tuning.jobs
                        SET status = 'FAILED',
                            error_message = %s,
                            completed_at = NOW()
                        WHERE job_id = %s
                    """, (error_msg[:500], job_id))
                    
                    # Run 통계 업데이트
                    cur.execute("""
                        UPDATE tuning.runs
                        SET failed_jobs = failed_jobs + 1
                        WHERE run_id = %s
                    """, (run_id,))
                conn.commit()
            
            # Penalty 반환 (최악의 값)
            penalty_metrics = {
                'pnl': -999999.0,
                'pnl_pct': -999.0,
                'sharpe_ratio': -10.0,
                'win_rate': 0.0,
                'trade_count': 0,
                'runtime_sec': round(runtime_sec, 3),
                'error': error_msg
            }
            return penalty_metrics
    
    def _extract_metrics_from_db(self, run_id: str, job_id: str) -> Dict[str, Any]:
        """
        DB에서 백테스트 결과 메트릭 추출 (PHASE28-4: TuningWorker와 동일)
        
        Args:
            run_id: Run ID
            job_id: Job ID (trial_id로 사용)
        
        Returns:
            메트릭 딕셔너리
        """
        import time
        import numpy as np
        
        # PHASE28-4: trial_id 기반 필터링 (TuningWorker와 동일)
        sql_trades = """
            SELECT pnl, pnl_pct, ts_close as exit_time
            FROM trading.trades
            WHERE trial_id = %s
              AND status = 'CLOSED'
            ORDER BY ts_close ASC
        """
        
        # Retry 로직 (DB commit 대기)
        max_retries = 3
        retry_delay = 0.5
        trades_rows = []
        
        for attempt in range(max_retries):
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql_trades, (job_id,))
                    trades_rows = cur.fetchall()
            
            if len(trades_rows) > 0:
                break
            
            if attempt < max_retries - 1:
                logger.warning(f"  No trades found for trial_id={job_id}, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
        
        # Trades 파싱 (Decimal → float)
        trades = [
            {
                'pnl': float(row[0]) if row[0] is not None else 0.0,
                'pnl_pct': float(row[1]) if row[1] is not None else 0.0,
                'exit_time': row[2]
            }
            for row in trades_rows
        ]
        
        trade_count = len(trades)
        
        if trade_count == 0:
            logger.warning(f"  No trades found for trial_id={job_id}")
            return {
                'pnl': 0.0,
                'pnl_pct': 0.0,
                'trade_count': 0,
                'win_count': 0,
                'lose_count': 0,
                'win_rate': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration_hours': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_lose': 0.0
            }
        
        # 메트릭 계산
        win_count = sum(1 for t in trades if t['pnl'] > 0)
        lose_count = trade_count - win_count
        win_rate = win_count / trade_count if trade_count > 0 else 0.0
        
        total_pnl = sum(t['pnl'] for t in trades)
        avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if win_count > 0 else 0.0
        avg_lose = np.mean([t['pnl'] for t in trades if t['pnl'] <= 0]) if lose_count > 0 else 0.0
        
        # Profit Factor
        profit_factor = 0.0
        if win_count > 0 and lose_count > 0 and avg_lose != 0:
            profit_factor = abs((avg_win * win_count) / (avg_lose * lose_count))
        
        # Sharpe Ratio (trade별 pnl_pct 기반 근사)
        returns = [float(t['pnl_pct']) / 100.0 for t in trades if 'pnl_pct' in t]
        sharpe_ratio = 0.0
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * np.sqrt(365)
        
        # Max Drawdown (cumulative PnL 기반)
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cumulative += t['pnl']
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)
        
        # pnl_pct 평균
        avg_pnl_pct = np.mean([t['pnl_pct'] for t in trades]) if trade_count > 0 else 0.0
        
        return {
            'pnl': float(round(total_pnl, 2)),
            'pnl_pct': float(round(avg_pnl_pct, 2)),
            'trade_count': int(trade_count),
            'win_count': int(win_count),
            'lose_count': int(lose_count),
            'win_rate': float(round(win_rate, 4)),
            'sharpe_ratio': float(round(sharpe_ratio, 4)),
            'max_drawdown': float(round(max_dd, 2)),
            'max_drawdown_duration_hours': 0.0,  # TODO: duration 계산
            'profit_factor': float(round(profit_factor, 4)),
            'avg_win': float(round(avg_win, 2)),
            'avg_lose': float(round(avg_lose, 2))
        }
    
    def _objective(
        self,
        trial: "optuna.Trial",
        config: BayesianSearchConfig,
        run_id: str
    ) -> float:
        """
        Optuna objective 함수
        
        Args:
            trial: Optuna Trial
            config: BayesianSearchConfig
            run_id: Run ID
        
        Returns:
            target_metric 값
        """
        # 1. 파라미터 제안
        params = self._suggest_params_from_space(trial, config.param_space)
        
        # 2. Trial 실행
        job_index = trial.number
        metrics = self._run_single_trial(run_id, job_index, params, config)
        
        # 3. Target metric 반환
        target_value = metrics.get(config.target_metric, 0.0)
        
        return target_value
    
    def run_sequential(self, config: BayesianSearchConfig) -> str:
        """
        Sequential Bayesian Search 실행
        
        Args:
            config: BayesianSearchConfig
        
        Returns:
            run_id
        """
        # 1. Config 검증
        config.validate()
        
        # 2. Run 생성
        run_id = f"{config.run_name}_{uuid.uuid4().hex[:8]}"
        
        logger.info("=" * 80)
        logger.info(f"🚀 Bayesian Search 시작: {run_id}")
        logger.info("=" * 80)
        logger.info(f"📊 전략: {config.strategy_name} ({config.strategy_family})")
        logger.info(f"🎯 Target: {config.target_metric} ({config.direction})")
        logger.info(f"🔢 Trials: {config.n_trials}")
        logger.info(f"🛠️  Mode: {config.mode}")
        logger.info(f"📄 Base Config: {config.base_config_path}")
        logger.info(f"🌱 Seed: {config.seed}")
        
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
            metadata={'base_config_path': config.base_config_path}
        )
        
        if not success:
            raise RuntimeError(f"❌ Run 생성 실패: {run_id}")
        
        logger.info(f"✅ Run 생성 완료: {run_id}")
        
        # 3. Optuna Study 생성
        sampler = optuna.samplers.TPESampler(seed=config.seed) if config.seed else optuna.samplers.TPESampler()
        
        study = optuna.create_study(
            direction=config.direction,
            sampler=sampler,
            study_name=run_id
        )
        
        logger.info(f"✅ Optuna Study 생성 완료 (TPE sampler)")
        
        # 4. Optimization 실행
        logger.info("=" * 80)
        logger.info("🔬 Optimization 시작...")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        study.optimize(
            lambda trial: self._objective(trial, config, run_id),
            n_trials=config.n_trials,
            show_progress_bar=False
        )
        
        elapsed = time.time() - start_time
        
        logger.info("=" * 80)
        logger.info(f"✅ Optimization 완료 ({elapsed:.1f}초)")
        logger.info("=" * 80)
        
        # 5. Best trial 정보 업데이트
        if study.best_trial:
            best_trial = study.best_trial
            logger.info(f"🏆 Best Trial: #{best_trial.number}")
            logger.info(f"  {config.target_metric}={best_trial.value:.4f}")
            logger.info(f"  Params: {best_trial.params}")
            
            # Run에 best 정보 업데이트
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT job_id FROM tuning.jobs
                        WHERE run_id = %s AND job_index = %s
                    """, (run_id, best_trial.number))
                    best_job_row = cur.fetchone()
                    
                    if best_job_row:
                        best_job_id = best_job_row[0]
                        cur.execute("""
                            UPDATE tuning.runs
                            SET best_job_id = %s,
                                best_metric_value = %s,
                                status = 'COMPLETED',
                                completed_at = NOW()
                            WHERE run_id = %s
                        """, (best_job_id, best_trial.value, run_id))
                    else:
                        # Best job이 없으면 COMPLETED만 설정
                        cur.execute("""
                            UPDATE tuning.runs
                            SET status = 'COMPLETED',
                                completed_at = NOW()
                            WHERE run_id = %s
                        """, (run_id,))
                conn.commit()
        
        logger.info(f"✅ Run 완료: {run_id}")
        
        return run_id
    
    def get_top_k_results(
        self,
        run_id: str,
        k: int = 10,
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run의 상위 K개 결과 조회
        
        Args:
            run_id: Run ID
            k: 결과 개수
            ascending: True면 오름차순, False면 내림차순
        
        Returns:
            결과 리스트 (job_id, params, 메트릭 포함)
        """
        order = "ASC" if ascending else "DESC"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # target_metric 조회
                cur.execute("""
                    SELECT target_metric FROM tuning.runs WHERE run_id = %s
                """, (run_id,))
                row = cur.fetchone()
                if not row:
                    return []
                target_metric = row[0]
                
                # 결과 조회
                metric_col = target_metric
                cur.execute(f"""
                    SELECT
                        j.job_id,
                        j.job_index,
                        j.params_json,
                        r.pnl,
                        r.pnl_pct,
                        r.trade_count,
                        r.win_rate,
                        r.sharpe_ratio,
                        r.{metric_col}
                    FROM tuning.jobs j
                    JOIN tuning.results r ON j.job_id = r.job_id
                    WHERE j.run_id = %s AND j.status = 'COMPLETED'
                    ORDER BY r.{metric_col} {order}
                    LIMIT %s
                """, (run_id, k))
                
                rows = cur.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        'job_id': row[0],
                        'job_index': row[1],
                        'params': row[2],
                        'pnl': row[3],
                        'pnl_pct': row[4],
                        'trade_count': row[5],
                        'win_rate': row[6],
                        'sharpe_ratio': row[7],
                        target_metric: row[8]
                    })
                
                return results
