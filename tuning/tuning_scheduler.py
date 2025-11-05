#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tuning Scheduler
================
- Runs periodic Bayesian tuning per strategy based on recent trade activity
- Publishes params to configs/<strategy>/active.yml (file-first approach)
- Sends Telegram notification on start/finish

Notes:
- Redis hot-reload is optional and not used here (restart-based apply is default)
- Storage: OPTUNA_STORAGE env (PostgreSQL)
- Window: TUNE_WINDOW_DAYS env (default 7)
"""
from __future__ import annotations
import os
import time
from datetime import datetime
from pathlib import Path

import schedule

from tuning.tuning_core import TunerCore
from database import get_db_connection
from common.messaging import tg
from common.config_loader import load_config

# Load base config (telegram/db) and tuning schedules
CFG = load_config()
TUNING_CFG = CFG.get("tuning", {}) or {}
SCHEDULES = TUNING_CFG.get("schedules", {}) or {}


def _ensure_sqlite_dir(storage: str) -> None:
    if isinstance(storage, str) and storage.startswith("sqlite:///"):
        db_path = storage.replace("sqlite:///", "", 1)
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass


def _get_active_risk_profile(cfg: dict) -> dict:
    """Return risk profile for current mode (paper/live), falling back to base risk."""
    mode = (cfg.get("mode") or "paper").lower()
    risk = cfg.get("risk", {}) or {}
    profiles = risk.get("profiles", {}) or {}
    if mode in profiles:
        prof = profiles.get(mode, {}) or {}
        # Merge with base keys for missing fields
        merged = {**risk, **prof}
        return merged
    return risk


def _consecutive_losses_today(strategy_id: str) -> int:
    """Compute consecutive losing trades for today (most recent first)."""
    sql = """
        SELECT COALESCE(pnl, 0)
        FROM trading.trades
        WHERE status = 'CLOSED'
          AND strategy_id = %s
          AND ts_close >= CURRENT_DATE
        ORDER BY ts_close DESC
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (strategy_id,))
                losses = 0
                for (pnl,) in cur.fetchall():
                    try:
                        v = float(pnl)
                    except Exception:
                        v = 0.0
                    if v < 0:
                        losses += 1
                    else:
                        break
                return losses
    except Exception:
        return 0


def _recent_closed_trade_count(strategy_id: str, recent_hours: int) -> int:
    sql = f"""
        SELECT COUNT(*)
        FROM trading.trades
        WHERE status = 'CLOSED'
          AND strategy_id = %s
          AND ts_close >= NOW() - INTERVAL '{int(recent_hours)} hours'
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (strategy_id,))
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


def _check_needs_tuning(strategy_id: str) -> tuple:
    """
    튜닝 필요 여부 판단 (config 기반)
    Returns: (needs_tuning, reason)
    """
    # 오늘 일일 PnL 합계
    sql = """
        SELECT COALESCE(SUM(pnl), 0) as daily_pnl
        FROM trading.trades
        WHERE status = 'CLOSED'
          AND strategy_id = %s
          AND ts_close >= CURRENT_DATE
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (strategy_id,))
                row = cur.fetchone()
                daily_pnl = float(row[0]) if row and row[0] is not None else 0.0
    except Exception as e:
        print(f"[SCHED] check_needs_tuning/daily_pnl error: {e}")
        daily_pnl = 0.0

    # 리스크 임계치 읽기 (현재 모드 프로파일)
    prof = _get_active_risk_profile(CFG)
    try:
        equity = float(CFG.get('capital', {}).get('initial', 0))
    except Exception:
        equity = 0.0

    max_daily_loss_pct = prof.get('max_daily_loss_pct', None)
    daily_limit_amt = None
    if max_daily_loss_pct is not None:
        try:
            v = float(max_daily_loss_pct)
            v = v / 100.0 if v > 1 else v
            daily_limit_amt = equity * v
        except Exception:
            daily_limit_amt = None

    # 연속 손실 임계치
    try:
        max_consec = prof.get('max_consecutive_losses', None)
        max_consec = int(max_consec) if max_consec is not None else None
    except Exception:
        max_consec = None
    consec_today = _consecutive_losses_today(strategy_id) if max_consec is not None else 0

    # 트리거 판단
    if daily_limit_amt is not None and daily_pnl <= -abs(daily_limit_amt):
        return True, f"daily_loss_limit_hit (pnl={daily_pnl:.2f} ≤ -{daily_limit_amt:.2f})"

    if max_consec is not None and consec_today >= max_consec:
        return True, f"consecutive_losses_hit ({consec_today} ≥ {max_consec})"

    return False, "ok"


def run_tuning_job(strategy_id: str, recent_hours: int, t_min_recent: int, trials: int) -> None:
    # 게이팅 1: 최근 거래 기반
    recent_trades = _recent_closed_trade_count(strategy_id, recent_hours)
    has_enough_trades = recent_trades >= int(t_min_recent)
    
    # 게이팅 2: 리스크 한도 도달 시 튜닝 트리거
    needs_tuning, reason = _check_needs_tuning(strategy_id)
    
    # 튜닝 실행 조건:
    # 1) 거래 충분 OR
    # 2) 리스크 한도 도달 (파라미터 개선 필요)
    if not has_enough_trades and not needs_tuning:
        print(f"[SCHED] skip {strategy_id}: trades={recent_trades}<{t_min_recent}, no risk trigger")
        return
    
    if needs_tuning:
        print(f"[SCHED] ⚠️ trigger tuning: {strategy_id} | reason={reason}")
    else:
        print(f"[SCHED] regular tuning: {strategy_id} | trades={recent_trades}")

    storage = os.getenv("OPTUNA_STORAGE", "postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db")
    window_days = int(os.getenv("TUNE_WINDOW_DAYS", "7"))

    study_name = f"{strategy_id}_paper_auto_{datetime.now().strftime('%Y%m%d')}"

    tuner = TunerCore(
        strategy_id=strategy_id,
        study_name=study_name,
        storage=storage,
        window_days=window_days,
        publish_mode="file",
        publish_dir=None,
    )

    print(f"[SCHED] start tuning: {strategy_id} | trials={trials} | window_days={window_days}")
    # Telegram: start
    try:
        start_msg = (
            f"🔧 [{strategy_id.upper()}] Tuning started\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Reason: {reason if needs_tuning else 'scheduled'}\n"
            f"Trials: {trials} | Window: {window_days}d\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        tg(start_msg, CFG)
    except Exception:
        pass
    tuner.optimize(n_trials=int(trials))
    print(f"[SCHED] finished tuning: {strategy_id}")

    # Telegram notify (best-effort)
    try:
        msg = (
            f"🎯 [{strategy_id.upper()}] Tuning finished\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Trials: {trials}\n"
            f"Window: {window_days}d | Recent: {recent_hours}h (min {t_min_recent})\n"
            f"Published: configs/{strategy_id}/active.yml\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        tg(msg, CFG)
    except Exception:
        pass


def _register_jobs():
    # ⭐ config.yml의 schedules에 정의된 전략만 실행
    for strategy_id, conf in SCHEDULES.items():
        # read interval
        job = None
        if "every_minutes" in conf:
            job = schedule.every(int(conf["every_minutes"]))
            job = job.minutes
        elif "every_hours" in conf:
            job = schedule.every(int(conf["every_hours"]))
            job = job.hours
        elif "every_days" in conf:
            job = schedule.every(int(conf["every_days"]))
            job = job.days
        else:
            job = schedule.every(1).hours

        job.do(
            run_tuning_job,
            strategy_id=strategy_id,
            recent_hours=int(conf.get("recent_hours", 1)),
            t_min_recent=int(conf.get("t_min_recent", 1)),
            trials=int(conf.get("trials", 10)),
        )
        mins = conf.get('every_minutes')
        hrs = conf.get('every_hours')
        days = conf.get('every_days')
        print(f"[SCHED] registered {strategy_id} every: minutes={mins}, hours={hrs}, days={days}")


def main():
    _register_jobs()
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
