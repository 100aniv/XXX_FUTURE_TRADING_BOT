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
    
    def _validate_tuning_config(self, config: dict):
        """
        PHASE28-2: 튜닝 config 필수 키 검증
        
        Base config가 엔진/PositionSizer/PortfolioManager/RiskManager가 요구하는
        모든 필수 키를 포함하는지 검증한다.
        
        누락된 키가 있으면 명확한 ConfigError를 발생시킨다.
        
        Args:
            config: 검증할 config 딕셔너리
        
        Raises:
            ValueError: 필수 키 누락 시
        """
        required_keys = {
            # Engine 필수
            'timeframe': 'config["timeframe"]',
            'lookback': 'config["lookback"]',
            'equity': 'config["equity"]',
            # Capital
            'capital.initial': 'config["capital"]["initial"]',
            # Risk (Engine + PositionSizer)
            'risk.per_trade': 'config["risk"]["per_trade"]',
            'risk.max_positions': 'config["risk"]["max_positions"]',
            'risk.max_exposure_per_symbol': 'config["risk"]["max_exposure_per_symbol"]',
            'risk.max_total_exposure': 'config["risk"]["max_total_exposure"]',
            # PositionSizing
            'position_sizing.quality_weight_min': 'config["position_sizing"]["quality_weight_min"]',
            'position_sizing.quality_weight_max': 'config["position_sizing"]["quality_weight_max"]',
            'position_sizing.min_position_value': 'config["position_sizing"]["min_position_value"]',
            'position_sizing.max_position_value': 'config["position_sizing"]["max_position_value"]',
            # Portfolio
            'portfolio.max_symbol_exposure_pct': 'config["portfolio"]["max_symbol_exposure_pct"]',
            'portfolio.max_exposure_pct': 'config["portfolio"]["max_exposure_pct"]',
            'portfolio.max_total_exposure': 'config["portfolio"]["max_total_exposure"]',
        }
        
        missing_keys = []
        
        for key_path, config_ref in required_keys.items():
            parts = key_path.split('.')
            value = config
            try:
                for part in parts:
                    value = value[part]
            except (KeyError, TypeError):
                missing_keys.append(f"  - {key_path} ({config_ref})")
        
        if missing_keys:
            error_msg = (
                "❌ Tuning Config 필수 키 누락!\n"
                "Base config가 엔진/PositionSizer/PortfolioManager가 요구하는 필수 키를 포함해야 합니다.\n"
                "누락된 키:\n" + "\n".join(missing_keys) + "\n\n"
                "해결 방법:\n"
                "  1. configs/backtest/phase28_2_btc5m_tuning_base.yml을 확인하세요.\n"
                "  2. docs/PHASE28/PHASE28_2_CONFIG_SSOT_ANALYSIS.md를 참고하세요.\n"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"✅ Config validation passed (모든 필수 키 존재)")
    
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
        from datetime import datetime
        from database import get_db_connection
        from execution.engine import run_v2
        from tuning.utils.config_builder import build_tuning_config
        
        start_time = time.time()
        start_datetime = datetime.now()
        
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
            
            # 2. PHASE28-4: 공통 config builder 사용 (Random Search & Bayesian Search 통합)
            config = build_tuning_config(
                base_config_path=base_config_path,
                strategy_params=params,
                trial_id=job_id,
                run_id=run_id,
                mode=mode,
                period_override=None  # Random Search는 base config의 날짜 사용
            )
            
            # 3. PHASE28-2: Config SSOT 검증
            # Base config가 모든 필수 키를 포함하도록 강제
            self._validate_tuning_config(config)
            
            logger.debug(f"[{self.worker_id}]   Config build complete via build_tuning_config()")
            
            # 4. 엔진 호출
            logger.info(f"[{self.worker_id}] 백테스트 실행 중...")
            
            # run_v2 호출 (clean_state=True로 DB/Redis 충돌 방지)
            run_v2(
                mode=mode,
                config=config,
                clean_state=True
            )
            
            logger.info(f"[{self.worker_id}] 백테스트 완료")
            
            # PHASE28-2: DB commit 보장을 위한 대기
            # Engine의 DB transaction이 완전히 commit되도록 1초 대기
            time.sleep(1.0)
            
            # 5. 결과 메트릭 추출
            # 백테스트 결과는 DB의 trading.trades, portfolio 테이블에서 추출
            end_datetime = datetime.now()
            runtime_sec = time.time() - start_time
            
            result_metrics = self._extract_metrics_from_db(
                run_id, job_id, runtime_sec, start_datetime, end_datetime
            )
            
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
    
    def _extract_metrics_from_db(
        self,
        run_id: str,
        job_id: str,
        runtime_sec: float,
        start_time: 'datetime',
        end_time: 'datetime'
    ) -> Dict[str, Any]:
        """
        DB에서 백테스트 결과 메트릭 추출 (PHASE25-4: 시간 기반 isolation + 정교한 계산)
        
        Args:
            run_id: Run ID
            job_id: Job ID
            runtime_sec: 실행 시간 (초)
            start_time: Job 시작 시각
            end_time: Job 종료 시각
        
        Returns:
            Dict[str, Any]: 메트릭 딕셔너리
        """
        from database import get_db_connection
        import numpy as np
        
        # PHASE28-2: trial_id 기반 isolation (정확한 job별 거래 추출)
        # 시간 기반 방식은 동시 실행 시 충돌 가능, trial_id로 완벽한 격리
        
        sql_trades_detailed = """
        SELECT
            pnl,
            pnl_pct,
            ts_close as exit_time
        FROM trading.trades
        WHERE trial_id = %s
          AND status = 'CLOSED'
        ORDER BY ts_close ASC
        """
        
        # PHASE28-2: portfolio 테이블 제거 (존재하지 않음)
        # 모든 메트릭은 trading.trades에서 계산
        
        try:
            # PHASE28-2: 재시도 로직 (DB commit 대기)
            # Engine의 DB transaction이 완전히 commit될 때까지 최대 3번 재시도
            max_retries = 3
            retry_delay = 0.5  # 초
            trades_rows = []
            
            for attempt in range(max_retries):
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Trades 상세 조회 (trial_id 기반)
                        logger.debug(f"[{self.worker_id}] Extracting metrics for trial_id={job_id} (attempt {attempt+1}/{max_retries})")
                        cur.execute(sql_trades_detailed, (job_id,))
                        trades_rows = cur.fetchall()
                        logger.debug(f"[{self.worker_id}] Found {len(trades_rows)} trades for trial_id={job_id}")
                
                if len(trades_rows) > 0:
                    # 거래 발견, 재시도 종료
                    break
                
                if attempt < max_retries - 1:
                    # 다음 재시도 전 대기
                    logger.warning(f"[{self.worker_id}] No trades found for trial_id={job_id}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
            
            # Trades 파싱
            # PHASE28-2: Decimal → float 변환
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
                # Trades 없음
                logger.warning(f"[{self.worker_id}] Trades 없음 (trial_id: {job_id})")
                return self._get_empty_metrics(runtime_sec)
            
            # 기본 메트릭 계산
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
            
            # Sharpe Ratio 개선 (일별 수익률 기반 근사)
            sharpe_ratio = self._calculate_sharpe_ratio(trades)
            
            # Max Drawdown 개선 (cumulative PnL 기반)
            max_drawdown, max_dd_duration_hours = self._calculate_max_drawdown(trades)
            
            # PHASE28-2: pnl_pct 계산 (trades 기반)
            # portfolio 테이블이 없으므로 trades의 pnl_pct 평균 사용
            avg_pnl_pct = np.mean([t['pnl_pct'] for t in trades]) if trade_count > 0 else 0.0
            
            # PHASE28-2: numpy 타입을 Python 기본 타입으로 변환
            result = {
                'pnl': float(round(total_pnl, 2)),
                'pnl_pct': float(round(avg_pnl_pct, 2)),
                'trade_count': int(trade_count),
                'win_count': int(win_count),
                'lose_count': int(lose_count),
                'win_rate': float(round(win_rate, 4)),
                'sharpe_ratio': float(round(sharpe_ratio, 4)),
                'max_drawdown': float(round(max_drawdown, 2)),
                'max_drawdown_duration_hours': float(round(max_dd_duration_hours, 2)),
                'profit_factor': float(round(profit_factor, 4)),
                'avg_win': float(round(avg_win, 2)),
                'avg_lose': float(round(avg_lose, 2)),
                'runtime_sec': float(round(runtime_sec, 3))
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [PHASE28-2 DEBUG] 메트릭 추출 실패: {e}")
            import traceback
            error_trace = traceback.format_exc()
            logger.error(error_trace)
            
            # PHASE28-2: 예외를 DB에 저장
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO tuning.worker_errors (job_id, error_message, error_trace, created_at)
                            VALUES (%s, %s, %s, NOW())
                        """, (job_id, str(e), error_trace))
            except:
                pass  # DB 저장 실패해도 무시
            
            # Fallback: 빈 메트릭
            return self._get_empty_metrics(runtime_sec)
    
    def _calculate_sharpe_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """
        Sharpe Ratio 계산 (일별 수익률 기반 근사)
        
        Args:
            trades: 거래 목록 [{'pnl_usdt': ..., 'pnl_pct': ..., 'exit_time': ...}, ...]
        
        Returns:
            float: Sharpe Ratio (연율화)
        
        Note:
            - 완벽한 Sharpe는 equity curve 필요
            - 여기서는 trade별 pnl_pct를 일별로 근사하여 계산
        """
        import numpy as np
        
        if len(trades) < 2:
            return 0.0
        
        # Trade별 수익률 추출 (pnl_pct)
        # PHASE28-2: Decimal → float 변환
        returns = [float(t['pnl_pct']) / 100.0 for t in trades if 'pnl_pct' in t]
        
        if not returns:
            return 0.0
        
        # 평균 및 표준편차
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Sharpe Ratio (연율화: sqrt(365))
        # 주의: trade별 수익률을 일별로 근사하므로 정확하지 않음
        sharpe = (mean_return / std_return) * np.sqrt(365)
        
        return sharpe
    
    def _calculate_max_drawdown(self, trades: List[Dict[str, Any]]) -> tuple:
        """
        Max Drawdown 계산 (cumulative PnL 기반)
        
        Args:
            trades: 거래 목록 (시간 순 정렬 필요)
        
        Returns:
            (max_drawdown_pct, max_drawdown_duration_hours)
        """
        if not trades:
            return 0.0, 0.0
        
        # Cumulative PnL 계산
        cumulative_pnl = []
        running_pnl = 0.0
        for trade in trades:
            running_pnl += trade['pnl']
            cumulative_pnl.append(running_pnl)
        
        # Running Peak 및 Drawdown 계산
        peak = cumulative_pnl[0]
        max_dd_pct = 0.0
        dd_start_idx = 0
        dd_end_idx = 0
        
        for i, pnl in enumerate(cumulative_pnl):
            if pnl > peak:
                peak = pnl
                dd_start_idx = i
            
            # Drawdown (절대값)
            dd = peak - pnl
            
            # Drawdown % (peak 기준)
            dd_pct = (dd / abs(peak)) * 100 if peak != 0 else 0.0
            
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                dd_end_idx = i
        
        # Duration 계산 (시간)
        if dd_end_idx > dd_start_idx and len(trades) > dd_end_idx:
            start_time = trades[dd_start_idx]['exit_time']
            end_time = trades[dd_end_idx]['exit_time']
            duration_hours = (end_time - start_time).total_seconds() / 3600
        else:
            duration_hours = 0.0
        
        return max_dd_pct, duration_hours
    
    def _get_empty_metrics(self, runtime_sec: float) -> Dict[str, Any]:
        """
        빈 메트릭 반환 (fallback)
        
        Args:
            runtime_sec: 실행 시간 (초)
        
        Returns:
            Dict[str, Any]: 빈 메트릭 딕셔너리
        """
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
