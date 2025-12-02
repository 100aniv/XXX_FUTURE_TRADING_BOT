#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tuning Job Queue
================
PHASE25-1: 중앙 DB 기반 Job Queue

주요 기능:
- Job 생성/할당/상태 관리
- 동시성 안전 (SELECT FOR UPDATE SKIP LOCKED)
- Run 단위 관리

사용법:
    queue = JobQueue()
    
    # Job 생성
    job_id = queue.enqueue_job(run_id='run_001', params={'rsi': 45, 'ema': 21})
    
    # Worker가 Job 할당받기
    job = queue.acquire_next_job(worker_id='worker-001')
    
    # Job 완료 처리
    queue.mark_job_completed(job_id, {'pnl': 123.45, 'sharpe': 1.5})
"""
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from psycopg2.extras import RealDictCursor, Json

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class JobQueue:
    """중앙 DB 기반 Job Queue"""
    
    def create_run(
        self,
        run_id: str,
        phase: str,
        strategy_family: str,
        strategy_name: str,
        mode: str,
        tuning_method: str,
        target_metric: str,
        total_jobs: int,
        seed: Optional[int] = None,
        config_override: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        튜닝 Run 생성
        
        Args:
            run_id: Run ID
            phase: PHASE 번호 (예: 'PHASE25-2')
            strategy_family: 전략 패밀리 (예: 'momentum')
            strategy_name: 전략 이름 (예: 'scalping')
            mode: 실행 모드 ('backtest', 'paper', 'live')
            tuning_method: 튜닝 방법 ('random', 'bayesian', 'grid')
            target_metric: 최적화 목표 (예: 'sharpe_ratio')
            total_jobs: 총 Job 수
            seed: Random seed
            config_override: Config override
            metadata: 추가 메타데이터
            
        Returns:
            bool: 성공 여부
        """
        sql = """
        INSERT INTO tuning.runs (
            run_id, phase, strategy_family, strategy_name, mode,
            tuning_method, target_metric, total_jobs, seed,
            config_override, metadata, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING'
        )
        ON CONFLICT (run_id) DO NOTHING
        RETURNING run_id;
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        run_id, phase, strategy_family, strategy_name, mode,
                        tuning_method, target_metric, total_jobs, seed,
                        Json(config_override) if config_override else None,
                        Json(metadata) if metadata else None
                    ))
                    result = cur.fetchone()
                    
                    if result:
                        logger.info(f"✅ Run 생성: {run_id} ({strategy_name}, {tuning_method}, {total_jobs} jobs)")
                        return True
                    else:
                        logger.warning(f"⏭️  Run 중복 스킵: {run_id}")
                        return False
        except Exception as e:
            logger.error(f"❌ Run 생성 실패: {e}")
            return False
    
    def enqueue_job(
        self,
        run_id: str,
        params: Dict[str, Any],
        job_index: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Job을 큐에 추가
        
        Args:
            run_id: 소속 Run ID
            params: 파라미터 딕셔너리
            job_index: Job index (None이면 자동 계산)
            metadata: 추가 메타데이터
            
        Returns:
            job_id: 생성된 Job ID (실패 시 None)
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # job_index 계산 (Run 내 순번)
        if job_index is None:
            sql_get_index = """
            SELECT COALESCE(MAX(job_index), -1) + 1 AS next_index
            FROM tuning.jobs
            WHERE run_id = %s
            """
        else:
            # job_index가 지정된 경우, 해당 값 사용
            sql_get_index = None
        
        sql_insert = """
        INSERT INTO tuning.jobs (
            job_id, run_id, job_index, params_json, status
        ) VALUES (
            %s, %s, %s, %s, 'PENDING'
        )
        RETURNING job_id;
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # job_index 계산 또는 사용
                    if sql_get_index:
                        cur.execute(sql_get_index, (run_id,))
                        next_index = cur.fetchone()[0]
                    else:
                        next_index = job_index
                    
                    # Job 생성
                    cur.execute(sql_insert, (
                        job_id, run_id, next_index, Json(params)
                    ))
                    result = cur.fetchone()
                    
                    if result:
                        logger.debug(f"✅ Job 생성: {job_id} (run={run_id}, index={next_index})")
                        return job_id
                    else:
                        logger.error(f"❌ Job 생성 실패: {job_id}")
                        return None
        except Exception as e:
            logger.error(f"❌ Job 생성 실패: {e}")
            return None
    
    def acquire_next_job(
        self,
        worker_id: str,
        run_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        다음 실행할 Job을 가져옴 (동시성 안전)
        
        SELECT FOR UPDATE SKIP LOCKED 패턴 사용:
        - 여러 Worker가 동시에 호출해도 중복 할당 방지
        
        Args:
            worker_id: Worker ID
            run_id: 특정 Run만 처리할 경우 Run ID 지정
            
        Returns:
            Job 정보 딕셔너리 (없으면 None)
        """
        sql = """
        SELECT job_id, run_id, job_index, params_json, status, created_at
        FROM tuning.jobs
        WHERE status = 'PENDING'
          AND (run_id = %s OR %s IS NULL)
        ORDER BY created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """
        
        sql_update = """
        UPDATE tuning.jobs
        SET status = 'RUNNING',
            worker_id = %s,
            assigned_at = now(),
            started_at = now(),
            updated_at = now()
        WHERE job_id = %s
        RETURNING job_id;
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Job 조회 (FOR UPDATE SKIP LOCKED)
                    cur.execute(sql, (run_id, run_id))
                    job = cur.fetchone()
                    
                    if not job:
                        logger.debug(f"[{worker_id}] 할당 가능한 Job 없음")
                        return None
                    
                    # 상태 RUNNING으로 변경
                    cur.execute(sql_update, (worker_id, job['job_id']))
                    result = cur.fetchone()
                    
                    if result:
                        logger.info(f"[{worker_id}] Job 할당: {job['job_id']} (run={job['run_id']}, index={job['job_index']})")
                        return dict(job)
                    else:
                        logger.error(f"[{worker_id}] Job 상태 변경 실패: {job['job_id']}")
                        return None
        except Exception as e:
            logger.error(f"❌ Job 할당 실패: {e}")
            return None
    
    def mark_job_completed(
        self,
        job_id: str,
        result_metrics: Dict[str, Any]
    ) -> bool:
        """
        Job 완료 처리 및 결과 저장
        
        Args:
            job_id: Job ID
            result_metrics: 결과 메트릭 딕셔너리
                예: {'pnl': 123.45, 'trade_count': 10, 'win_rate': 0.6, ...}
                
        Returns:
            bool: 성공 여부
        """
        result_id = f"result_{uuid.uuid4().hex[:12]}"
        
        sql_update_job = """
        UPDATE tuning.jobs
        SET status = 'COMPLETED',
            completed_at = now(),
            runtime_sec = EXTRACT(EPOCH FROM (now() - started_at)),
            updated_at = now()
        WHERE job_id = %s
        RETURNING run_id;
        """
        
        sql_insert_result = """
        INSERT INTO tuning.results (
            result_id, job_id, run_id,
            pnl, pnl_pct, trade_count, win_count, lose_count,
            win_rate, sharpe_ratio, max_drawdown,
            max_drawdown_duration_hours, profit_factor,
            avg_win, avg_lose, runtime_sec, metrics_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        sql_update_run = """
        UPDATE tuning.runs
        SET completed_jobs = completed_jobs + 1,
            updated_at = now()
        WHERE run_id = %s
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Job 상태 COMPLETED로 변경
                    cur.execute(sql_update_job, (job_id,))
                    result = cur.fetchone()
                    
                    if not result:
                        logger.error(f"❌ Job 완료 처리 실패: {job_id} (Job 없음)")
                        return False
                    
                    run_id = result[0]
                    
                    # 2. Result 저장
                    cur.execute(sql_insert_result, (
                        result_id, job_id, run_id,
                        result_metrics.get('pnl'),
                        result_metrics.get('pnl_pct'),
                        result_metrics.get('trade_count'),
                        result_metrics.get('win_count'),
                        result_metrics.get('lose_count'),
                        result_metrics.get('win_rate'),
                        result_metrics.get('sharpe_ratio'),
                        result_metrics.get('max_drawdown'),
                        result_metrics.get('max_drawdown_duration_hours'),
                        result_metrics.get('profit_factor'),
                        result_metrics.get('avg_win'),
                        result_metrics.get('avg_lose'),
                        result_metrics.get('runtime_sec'),
                        Json(result_metrics)  # 전체 메트릭을 JSON으로 저장
                    ))
                    
                    # 3. Run completed_jobs 증가
                    cur.execute(sql_update_run, (run_id,))
                    
                    logger.info(f"✅ Job 완료: {job_id} (run={run_id}, pnl={result_metrics.get('pnl', 'N/A'):.2f})")
                    return True
        except Exception as e:
            logger.error(f"❌ Job 완료 처리 실패: {e}")
            return False
    
    def mark_job_failed(
        self,
        job_id: str,
        error_message: str
    ) -> bool:
        """
        Job 실패 처리
        
        Args:
            job_id: Job ID
            error_message: 에러 메시지
            
        Returns:
            bool: 성공 여부
        """
        sql_update_job = """
        UPDATE tuning.jobs
        SET status = 'FAILED',
            error_message = %s,
            completed_at = now(),
            runtime_sec = EXTRACT(EPOCH FROM (now() - started_at)),
            updated_at = now()
        WHERE job_id = %s
        RETURNING run_id;
        """
        
        sql_update_run = """
        UPDATE tuning.runs
        SET failed_jobs = failed_jobs + 1,
            updated_at = now()
        WHERE run_id = %s
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Job 상태 FAILED로 변경
                    cur.execute(sql_update_job, (error_message, job_id))
                    result = cur.fetchone()
                    
                    if not result:
                        logger.error(f"❌ Job 실패 처리 실패: {job_id} (Job 없음)")
                        return False
                    
                    run_id = result[0]
                    
                    # 2. Run failed_jobs 증가
                    cur.execute(sql_update_run, (run_id,))
                    
                    logger.error(f"❌ Job 실패: {job_id} (run={run_id}, error={error_message})")
                    return True
        except Exception as e:
            logger.error(f"❌ Job 실패 처리 실패: {e}")
            return False
    
    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Run 전체 상태 조회
        
        Args:
            run_id: Run ID
            
        Returns:
            Run 상태 딕셔너리 (없으면 None)
        """
        sql = """
        SELECT *
        FROM tuning.runs
        WHERE run_id = %s
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (run_id,))
                    run = cur.fetchone()
                    
                    if run:
                        return dict(run)
                    else:
                        logger.warning(f"⚠️  Run 없음: {run_id}")
                        return None
        except Exception as e:
            logger.error(f"❌ Run 상태 조회 실패: {e}")
            return None
    
    def cancel_run(self, run_id: str) -> bool:
        """
        Run 전체 취소 (PENDING/RUNNING job 모두 CANCELLED로 변경)
        
        Args:
            run_id: Run ID
            
        Returns:
            bool: 성공 여부
        """
        sql_update_jobs = """
        UPDATE tuning.jobs
        SET status = 'CANCELLED',
            updated_at = now()
        WHERE run_id = %s
          AND status IN ('PENDING', 'RUNNING')
        """
        
        sql_update_run = """
        UPDATE tuning.runs
        SET status = 'CANCELLED',
            completed_at = now(),
            updated_at = now()
        WHERE run_id = %s
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Job 상태 CANCELLED로 변경
                    cur.execute(sql_update_jobs, (run_id,))
                    cancelled_count = cur.rowcount
                    
                    # 2. Run 상태 CANCELLED로 변경
                    cur.execute(sql_update_run, (run_id,))
                    
                    logger.info(f"🚫 Run 취소: {run_id} ({cancelled_count}개 Job 취소)")
                    return True
        except Exception as e:
            logger.error(f"❌ Run 취소 실패: {e}")
            return False
    
    def get_run_results(self, run_id: str, order_by: str = 'sharpe_ratio') -> List[Dict[str, Any]]:
        """
        Run의 모든 결과 조회 (메트릭 기준 정렬)
        
        Args:
            run_id: Run ID
            order_by: 정렬 기준 (예: 'sharpe_ratio', 'pnl', 'win_rate')
            
        Returns:
            결과 리스트
        """
        # 허용된 컬럼만 사용 (SQL injection 방지)
        allowed_columns = [
            'sharpe_ratio', 'pnl', 'pnl_pct', 'win_rate',
            'trade_count', 'max_drawdown', 'profit_factor'
        ]
        
        if order_by not in allowed_columns:
            order_by = 'sharpe_ratio'
        
        sql = f"""
        SELECT r.*, j.params_json, j.job_index
        FROM tuning.results r
        JOIN tuning.jobs j ON r.job_id = j.job_id
        WHERE r.run_id = %s
        ORDER BY r.{order_by} DESC NULLS LAST
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (run_id,))
                    results = cur.fetchall()
                    return [dict(r) for r in results]
        except Exception as e:
            logger.error(f"❌ Run 결과 조회 실패: {e}")
            return []
    
    def mark_stale_jobs_as_failed(self, max_runtime_sec: int = 3600) -> int:
        """
        Stale RUNNING job을 FAILED로 전환 (PHASE25-4: Worker Timeout)
        
        Args:
            max_runtime_sec: 최대 허용 실행 시간 (초, 기본 1시간)
        
        Returns:
            int: 실패 처리된 job 수
        
        Description:
            RUNNING 상태이지만 started_at 이후 max_runtime_sec를 초과한 job을
            FAILED로 전환하여 hanging job 방지.
            
        Usage:
            # 주기적으로 호출 (예: 별도 스크립트 또는 Worker loop)
            queue = JobQueue()
            failed_count = queue.mark_stale_jobs_as_failed(max_runtime_sec=3600)
        """
        sql = """
        UPDATE tuning.jobs
        SET status = 'FAILED',
            error_message = 'Job timeout: exceeded max runtime',
            updated_at = now()
        WHERE status = 'RUNNING'
          AND (EXTRACT(EPOCH FROM (now() - started_at)) > %s)
        RETURNING job_id, run_id
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (max_runtime_sec,))
                    failed_jobs = cur.fetchall()
                    
                    count = len(failed_jobs)
                    
                    if count > 0:
                        logger.warning(f"⚠️  Stale job {count}개를 FAILED로 전환 (max_runtime: {max_runtime_sec}s)")
                        for job_id, run_id in failed_jobs:
                            logger.warning(f"   - Job {job_id} (Run: {run_id})")
                    else:
                        logger.debug(f"✅ Stale job 없음 (max_runtime: {max_runtime_sec}s)")
                    
                    return count
        except Exception as e:
            logger.error(f"❌ Stale job 처리 실패: {e}")
            return 0
