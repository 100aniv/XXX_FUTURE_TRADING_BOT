-- ================================================================
-- PHASE25-1: Tuning Cluster Infrastructure
-- ================================================================
-- 튜닝 클러스터 관련 스키마 및 테이블 생성
--
-- 테이블:
-- - tuning.runs: 튜닝 세션 (예: "scalping Random Search 100 trials")
-- - tuning.jobs: 개별 파라미터 실행 (1 job = 1 backtest/paper)
-- - tuning.results: 실행 결과 메트릭
--
-- Date: 2025-12-03
-- Author: PHASE25-1 Implementation
-- ================================================================

-- 1. tuning 스키마 생성
CREATE SCHEMA IF NOT EXISTS tuning;

-- 2. tuning.runs 테이블
CREATE TABLE IF NOT EXISTS tuning.runs (
    run_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('backtest', 'paper', 'live')),
    tuning_method TEXT NOT NULL CHECK (tuning_method IN ('random', 'bayesian', 'grid', 'manual')),
    target_metric TEXT NOT NULL,
    total_jobs INTEGER NOT NULL DEFAULT 0,
    completed_jobs INTEGER NOT NULL DEFAULT 0,
    failed_jobs INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')) DEFAULT 'PENDING',
    best_job_id TEXT,
    best_metric_value NUMERIC,
    seed INTEGER,
    config_override JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- 3. tuning.jobs 테이블
CREATE TABLE IF NOT EXISTS tuning.jobs (
    job_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES tuning.runs(run_id) ON DELETE CASCADE,
    job_index INTEGER NOT NULL,
    params_json JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')) DEFAULT 'PENDING',
    worker_id TEXT,
    assigned_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    runtime_sec NUMERIC,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_id, job_index)
);

-- 4. tuning.results 테이블
CREATE TABLE IF NOT EXISTS tuning.results (
    result_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES tuning.jobs(job_id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES tuning.runs(run_id) ON DELETE CASCADE,
    pnl NUMERIC,
    pnl_pct NUMERIC,
    trade_count INTEGER,
    win_count INTEGER,
    lose_count INTEGER,
    win_rate NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    max_drawdown_duration_hours NUMERIC,
    profit_factor NUMERIC,
    avg_win NUMERIC,
    avg_lose NUMERIC,
    runtime_sec NUMERIC,
    metrics_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. 인덱스 생성

-- runs 인덱스
CREATE INDEX IF NOT EXISTS idx_tuning_runs_status ON tuning.runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tuning_runs_strategy ON tuning.runs(strategy_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tuning_runs_phase ON tuning.runs(phase, created_at DESC);

-- jobs 인덱스
CREATE INDEX IF NOT EXISTS idx_tuning_jobs_status ON tuning.jobs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tuning_jobs_run ON tuning.jobs(run_id, job_index);
CREATE INDEX IF NOT EXISTS idx_tuning_jobs_worker ON tuning.jobs(worker_id, updated_at DESC);

-- results 인덱스
CREATE INDEX IF NOT EXISTS idx_tuning_results_run ON tuning.results(run_id, sharpe_ratio DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_tuning_results_job ON tuning.results(job_id);

-- 6. FK 추가 (best_job_id)
-- Note: best_job_id는 circular dependency를 피하기 위해 FK 제약조건 추가하지 않음
-- 대신 application level에서 관리

-- ================================================================
-- 마이그레이션 완료
-- ================================================================
