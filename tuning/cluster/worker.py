#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tuning Worker
=============
PHASE25-1: 튜닝 Job을 처리하는 Worker

주요 기능:
- Job Queue에서 Job 할당받기
- Job 처리 (PHASE25-1에서는 dummy 실행)
- 결과 저장

사용법:
    from tuning.cluster import JobQueue, TuningWorker
    
    queue = JobQueue()
    worker = TuningWorker(worker_id='worker-001', job_queue=queue)
    
    # 한 번만 실행
    worker.loop(once=True)
    
    # 계속 루프 (Ctrl+C로 종료)
    worker.loop()
"""
import time
from typing import Dict, Any, Optional

from tuning.cluster.job_queue import JobQueue
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class TuningWorker:
    """튜닝 Job을 처리하는 Worker"""
    
    def __init__(
        self,
        worker_id: str,
        job_queue: JobQueue,
        run_id: Optional[str] = None,
        use_dummy: bool = False
    ):
        """
        Args:
            worker_id: Worker ID (예: "worker-001")
            job_queue: JobQueue 인스턴스
            run_id: 특정 Run만 처리할 경우 지정
            use_dummy: True이면 dummy 메트릭 생성 (PHASE25-1 하위 호환)
        """
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.run_id = run_id
        self.use_dummy = use_dummy
        self.running = False
        self.jobs_processed = 0
        
        logger.info(f"🚀 Worker 초기화: {self.worker_id}")
        if self.run_id:
            logger.info(f"   Target Run: {self.run_id}")
        if self.use_dummy:
            logger.info(f"   Mode: DUMMY (PHASE25-1 테스트 호환)")
    
    def loop(self, once: bool = False, poll_interval_sec: int = 5):
        """
        Worker 메인 루프
        
        Args:
            once: True이면 1개 job만 처리 후 종료, False이면 계속 loop
            poll_interval_sec: Job이 없을 때 대기 시간 (초)
        """
        self.running = True
        logger.info(f"[{self.worker_id}] Worker 시작 (once={once})")
        
        while self.running:
            # Job 할당받기
            job = self.job_queue.acquire_next_job(
                worker_id=self.worker_id,
                run_id=self.run_id
            )
            
            if job is None:
                if once:
                    logger.info(f"[{self.worker_id}] 할당 가능한 Job 없음, 종료")
                    break
                
                logger.debug(f"[{self.worker_id}] 할당 가능한 Job 없음, {poll_interval_sec}초 대기")
                time.sleep(poll_interval_sec)
                continue
            
            # Job 처리
            try:
                result = self.process_job(job)
                self.job_queue.mark_job_completed(job['job_id'], result)
                self.jobs_processed += 1
            except Exception as e:
                logger.error(f"[{self.worker_id}] Job 처리 실패: {job['job_id']}, 에러: {e}")
                self.job_queue.mark_job_failed(job['job_id'], str(e))
            
            if once:
                logger.info(f"[{self.worker_id}] 1개 Job 처리 완료, 종료")
                break
        
        logger.info(f"[{self.worker_id}] Worker 종료 (처리: {self.jobs_processed}개)")
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Job 처리 (PHASE25-2: 실제 백테스트 엔진 호출)
        
        Args:
            job: Job 정보 딕셔너리
                {'job_id', 'run_id', 'params_json', ...}
        
        Returns:
            result_metrics: 결과 메트릭 딕셔너리
        """
        # PHASE25-1 하위 호환: dummy 모드
        if self.use_dummy:
            return self._process_job_dummy(job)
        
        # PHASE25-2: 실제 엔진 호출
        import time
        import yaml
        from pathlib import Path
        from database import get_db_connection
        from execution.engine import run_v2
        from common.config_loader import deep_merge
        
        start_time = time.time()
        
        job_id = job['job_id']
        run_id = job['run_id']
        params = job['params_json']
        
        logger.info(f"[{self.worker_id}] Job 처리 시작: {job_id}")
        logger.debug(f"[{self.worker_id}]   Run: {run_id}")
        logger.debug(f"[{self.worker_id}]   Params: {params}")
        
        # ========================================
        # PHASE25-2: 실제 엔진 호출
        # ========================================
        
        try:
            # 1. Run 메타데이터에서 base_config_path 조회
            sql = """
            SELECT config_override, metadata, mode
            FROM tuning.runs
            WHERE run_id = %s
            """
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (run_id,))
                    row = cur.fetchone()
                    
                    if not row:
                        raise ValueError(f"Run not found: {run_id}")
                    
                    config_override = row[0] or {}
                    metadata = row[1] or {}
                    mode = row[2]
            
            base_config_path = config_override.get('base_config_path')
            if not base_config_path:
                # Fallback: metadata에서 찾기
                base_config_path = metadata.get('base_config_path')
            
            if not base_config_path:
                raise ValueError(f"base_config_path not found in run metadata: {run_id}")
            
            logger.debug(f"[{self.worker_id}]   Base config: {base_config_path}")
            logger.debug(f"[{self.worker_id}]   Mode: {mode}")
            
            # 2. Base config 로드
            config_path = Path(base_config_path)
            if not config_path.exists():
                raise FileNotFoundError(f"Config file not found: {base_config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                base_config = yaml.safe_load(f)
            
            # 3. Params override 적용
            # params는 strategy params 영역에 적용
            config = deep_merge(base_config, {})
            
            # Strategy params override
            strategy_section = config.get('strategy', {})
            selected = strategy_section.get('selected', 'scalping')
            
            if selected in strategy_section:
                strategy_config = strategy_section[selected]
                if 'params' not in strategy_config:
                    strategy_config['params'] = {}
                
                # Params 덮어쓰기
                for key, value in params.items():
                    strategy_config['params'][key] = value
            
            # Mode 설정
            config['mode'] = mode
            
            # Duration 짧게 (백테스트 빠르게)
            # backtest 모드라면 기간은 이미 config에 있을 것
            # paper 모드라면 아주 짧게 (30초)
            if mode == 'paper':
                config['duration_hours'] = 0.0083  # 30초
            
            logger.debug(f"[{self.worker_id}]   Final config (strategy params): {strategy_section.get(selected, {}).get('params', {})}")
            
            # 4. 엔진 호출
            logger.info(f"[{self.worker_id}] 백테스트 실행 중...")
            
            # run_v2 호출 (clean_state=True로 DB/Redis 충돌 방지)
            run_v2(
                mode=mode,
                config=config,
                clean_state=True
            )
            
            logger.info(f"[{self.worker_id}] 백테스트 완료")
            
            # 5. 결과 메트릭 추출
            # 백테스트 결과는 DB의 trading.trades, portfolio 테이블에서 추출
            runtime_sec = time.time() - start_time
            
            result_metrics = self._extract_metrics_from_db(run_id, job_id, runtime_sec)
            
            logger.info(f"[{self.worker_id}] Job 처리 완료: {job_id}")
            logger.info(f"[{self.worker_id}]   PnL: {result_metrics.get('pnl', 0):.2f} USDT")
            logger.info(f"[{self.worker_id}]   Sharpe: {result_metrics.get('sharpe_ratio', 0):.4f}")
            logger.info(f"[{self.worker_id}]   Win Rate: {result_metrics.get('win_rate', 0):.2%}")
            logger.info(f"[{self.worker_id}]   Runtime: {runtime_sec:.1f}s")
            
            return result_metrics
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Job 처리 실패: {job_id}, 에러: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _extract_metrics_from_db(self, run_id: str, job_id: str, runtime_sec: float) -> Dict[str, Any]:
        """
        DB에서 백테스트 결과 메트릭 추출
        
        Args:
            run_id: Run ID
            job_id: Job ID
            runtime_sec: 실행 시간 (초)
        
        Returns:
            Dict[str, Any]: 메트릭 딕셔너리
        """
        from database import get_db_connection
        
        # 현재는 간단하게 최근 trades 및 portfolio 데이터 기반으로 계산
        # 실제로는 run_id 기준으로 필터링해야 하나, PHASE25-2에서는 단일 워커 가정
        
        sql_trades = """
        SELECT
            COUNT(*) AS trade_count,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) AS win_count,
            SUM(CASE WHEN pnl_usdt <= 0 THEN 1 ELSE 0 END) AS lose_count,
            SUM(pnl_usdt) AS total_pnl,
            AVG(CASE WHEN pnl_usdt > 0 THEN pnl_usdt ELSE NULL END) AS avg_win,
            AVG(CASE WHEN pnl_usdt <= 0 THEN pnl_usdt ELSE NULL END) AS avg_lose
        FROM trading.trades
        WHERE exit_time >= now() - interval '10 minutes'
        """
        
        sql_portfolio = """
        SELECT
            total_equity,
            total_pnl,
            total_pnl_pct
        FROM portfolio
        WHERE symbol = 'BTCUSDT'  -- 단일 심볼 가정
        ORDER BY updated_at DESC
        LIMIT 1
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Trades 메트릭
                    cur.execute(sql_trades)
                    trades_row = cur.fetchone()
                    
                    trade_count = trades_row[0] or 0
                    win_count = trades_row[1] or 0
                    lose_count = trades_row[2] or 0
                    total_pnl = trades_row[3] or 0.0
                    avg_win = trades_row[4] or 0.0
                    avg_lose = trades_row[5] or 0.0
                    
                    # Portfolio 메트릭
                    cur.execute(sql_portfolio)
                    portfolio_row = cur.fetchone()
                    
                    if portfolio_row:
                        equity = portfolio_row[0] or 0.0
                        pnl = portfolio_row[1] or 0.0
                        pnl_pct = portfolio_row[2] or 0.0
                    else:
                        equity = 0.0
                        pnl = total_pnl
                        pnl_pct = 0.0
            
            # 계산된 메트릭
            win_rate = win_count / trade_count if trade_count > 0 else 0.0
            
            # Sharpe ratio (간단 근사치)
            # 실제로는 일별 수익률의 표준편차가 필요하나, 여기서는 단순 계산
            sharpe_ratio = pnl_pct / 10.0 if pnl_pct != 0 else 0.0  # 임시 근사
            
            # Max Drawdown (임시)
            max_drawdown = abs(pnl * 0.3) if pnl < 0 else 0.0
            
            # Profit Factor
            profit_factor = 0.0
            if win_count > 0 and lose_count > 0 and avg_lose != 0:
                profit_factor = abs((avg_win * win_count) / (avg_lose * lose_count))
            
            result = {
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2),
                'trade_count': trade_count,
                'win_count': win_count,
                'lose_count': lose_count,
                'win_rate': round(win_rate, 4),
                'sharpe_ratio': round(sharpe_ratio, 4),
                'max_drawdown': round(max_drawdown, 2),
                'max_drawdown_duration_hours': 0.0,  # 추후 구현
                'profit_factor': round(profit_factor, 4),
                'avg_win': round(avg_win, 2),
                'avg_lose': round(avg_lose, 2),
                'runtime_sec': round(runtime_sec, 3)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"메트릭 추출 실패: {e}")
            # Fallback: 빈 메트릭
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
                'avg_lose': 0.0,
                'runtime_sec': round(runtime_sec, 3)
            }
    
    def _process_job_dummy(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Job 처리 (PHASE25-1: dummy 메트릭 생성)
        
        Args:
            job: Job 정보 딕셔너리
        
        Returns:
            result_metrics: 결과 메트릭 딕셔너리
        """
        import random
        
        job_id = job['job_id']
        run_id = job['run_id']
        params = job['params_json']
        
        logger.info(f"[{self.worker_id}] Job 처리 시작 (DUMMY): {job_id}")
        logger.debug(f"[{self.worker_id}]   Run: {run_id}")
        logger.debug(f"[{self.worker_id}]   Params: {params}")
        
        # 1~3초 sleep + 랜덤 메트릭 생성
        sleep_time = random.uniform(1.0, 3.0)
        time.sleep(sleep_time)
        
        # Dummy 메트릭 생성
        trade_count = random.randint(10, 50)
        win_count = random.randint(int(trade_count * 0.3), int(trade_count * 0.7))
        lose_count = trade_count - win_count
        win_rate = win_count / trade_count if trade_count > 0 else 0
        
        avg_win = random.uniform(10, 50)
        avg_lose = random.uniform(-10, -30)
        
        pnl = win_count * avg_win + lose_count * avg_lose
        pnl_pct = random.uniform(-10, 30)
        
        sharpe_ratio = random.uniform(-0.5, 2.5)
        max_drawdown = random.uniform(5, 25)
        max_drawdown_duration_hours = random.uniform(1, 48)
        
        profit_factor = abs(avg_win * win_count / (avg_lose * lose_count)) if lose_count > 0 else 0
        
        dummy_result = {
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl_pct, 2),
            'trade_count': trade_count,
            'win_count': win_count,
            'lose_count': lose_count,
            'win_rate': round(win_rate, 4),
            'sharpe_ratio': round(sharpe_ratio, 4),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_duration_hours': round(max_drawdown_duration_hours, 2),
            'profit_factor': round(profit_factor, 4),
            'avg_win': round(avg_win, 2),
            'avg_lose': round(avg_lose, 2),
            'runtime_sec': round(sleep_time, 3)
        }
        
        logger.info(f"[{self.worker_id}] Job 처리 완료 (DUMMY): {job_id}")
        logger.info(f"[{self.worker_id}]   PnL: {dummy_result['pnl']:.2f} USDT")
        logger.info(f"[{self.worker_id}]   Sharpe: {dummy_result['sharpe_ratio']:.4f}")
        logger.info(f"[{self.worker_id}]   Win Rate: {dummy_result['win_rate']:.2%}")
        
        return dummy_result
    
    def stop(self):
        """Worker 중지"""
        logger.info(f"[{self.worker_id}] Worker 중지 요청")
        self.running = False
