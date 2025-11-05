#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 베이지안 튜닝 코어 (Generic Bayesian Tuning Core)
========================================================
모든 전략과 모드(페이퍼/백테스트)에서 재사용 가능한 베이지안 최적화 엔진

주요 기능:
- 페이퍼 모드: Postgres trading.trades 테이블에서 7일 롤링 메트릭 수집
- 백테스트 모드: 향후 추가 가능 (메트릭 fetcher 교체 방식)
- Optuna TPE 샘플러 + MedianPruner로 효율적 탐색
- 파라미터 자동 발행 (configs/<전략>/active.yml)

사용법:
    from common.tuning_core import TunerCore
    tuner = TunerCore(strategy_id='scalping', study_name='scalp_paper', ...)
    tuner.optimize(n_trials=10)
"""
from __future__ import annotations
import os
import math
import json
import yaml
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List, Tuple

# Optuna (필수 라이브러리)
try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler
except Exception as e:
    raise

# DB 유틸리티 (Postgres)
from database import get_db_connection
from common.config_loader import deep_merge, load_config

# -------------------------
# 롤링 메트릭 유틸리티
# -------------------------

@dataclass
class RollingMetrics:
    """롤링 윈도우 메트릭 데이터 클래스"""
    sharpe: float      # 샤프 비율 (일별 수익률 기준)
    trades: int        # 총 거래 수
    mdd_pct: float     # 최대 낙폭 % (양수, 예: 7.5 = -7.5% 낙폭)
    roi_pct: float     # 수익률 %
    days: int          # 실제 거래 일수


def _daily_returns_from_trades(rows: List[Tuple[datetime, float]], capital: float = 10000.0) -> List[float]:
    """거래 내역을 일별 수익률로 변환
    
    Args:
        rows: (종료시각, PnL) 튜플 리스트
        capital: 초기 자본금 (기본: 10000 USDT)
    
    Returns:
        일별 수익률 리스트 (소수, 예: 0.05 = 5%)
    """
    # 날짜별 PnL 집계
    by_day: Dict[date, float] = {}
    for ts_close, pnl in rows:
        d = ts_close.date()
        by_day[d] = by_day.get(d, 0.0) + float(pnl or 0.0)
    # 수익률로 변환
    returns: List[float] = []
    for d in sorted(by_day.keys()):
        daily_pnl = by_day[d]
        returns.append(daily_pnl / capital)
    return returns


def _sharpe(daily_returns: List[float]) -> float:
    """샤프 비율 계산 (일별 기준, 연율화 안함)
    
    Args:
        daily_returns: 일별 수익률 리스트
    
    Returns:
        샤프 비율 (평균 / 표준편차)
    """
    if not daily_returns:
        return 0.0
    mu = statistics.mean(daily_returns)
    sigma = statistics.pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    if sigma == 0:
        return 0.0
    # 일별 샤프 (연율화 안함)
    return mu / sigma


def _mdd_pct_from_trades(rows: List[Tuple[datetime, float]], capital: float = 10000.0) -> float:
    """최대 낙폭(MDD) 계산
    
    Args:
        rows: (종료시각, PnL) 튜플 리스트
        capital: 초기 자본금
    
    Returns:
        최대 낙폭 % (양수, 예: 7.5 = -7.5% 낙폭)
    """
    eq = capital
    peak = capital
    worst = 0.0
    for _, pnl in sorted(rows, key=lambda x: x[0]):
        eq += float(pnl or 0.0)
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak  # 0..1 범위
        if dd > worst:
            worst = dd
    return worst * 100.0


def fetch_metrics_rolling(strategy_id: str, window_days: int = 7, capital: float = 10000.0) -> RollingMetrics:
    """Postgres trading.trades에서 롤링 윈도우 메트릭 수집
    
    Args:
        strategy_id: 전략 ID (scalping, daytrade, trend, swing, reversion, breakout)
        window_days: 롤링 윈도우 일수 (기본: 7일)
        capital: 초기 자본금 (기본: 10000 USDT)
    
    Returns:
        RollingMetrics 객체 (DB 없거나 비어있으면 0으로 초기화)
    """
    try:
        since_sql = f"now() - interval '{int(window_days)} days'"
        rows: List[Tuple[datetime, float]] = []
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT ts_close, COALESCE(pnl, 0)
                    FROM trading.trades
                    WHERE status = 'CLOSED'
                      AND strategy_id = %s
                      AND ts_close >= {since_sql}
                    ORDER BY ts_close
                    """,
                    (strategy_id,)
                )
                for r in cur.fetchall() or []:
                    rows.append((r[0], float(r[1] or 0.0)))
        trades = len(rows)
        daily_returns = _daily_returns_from_trades(rows, capital=capital)
        sharpe = _sharpe(daily_returns)
        mdd_pct = _mdd_pct_from_trades(rows, capital=capital)
        roi_pct = (sum(p for _, p in rows) / capital) * 100.0 if capital > 0 else 0.0
        # count distinct days
        days = len({ts.date() for ts, _ in rows})
        return RollingMetrics(sharpe=sharpe, trades=trades, mdd_pct=mdd_pct, roi_pct=roi_pct, days=days)
    except Exception:
        return RollingMetrics(sharpe=0.0, trades=0, mdd_pct=0.0, roi_pct=0.0, days=0)


# -------------------------
# Param space registry
# -------------------------

ParamSampler = Callable[["optuna.trial.Trial"], Dict[str, Any]]


def _sample_scalping(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    rsi_low = trial.suggest_float("rsi_low", 20.0, 40.0)
    rsi_high = trial.suggest_float("rsi_high", 55.0, 75.0)
    allow_short = trial.suggest_categorical("allow_short", [True, False])
    volume_mult = trial.suggest_float("volume_mult", 0.8, 2.0)
    min_rr = trial.suggest_float("min_rr_required", 1.0, 1.6)
    return {
        "strategies": {
            "scalping": {
                "rsi_low": float(rsi_low),
                "rsi_high": float(rsi_high),
                "filters": {"allow_short": bool(allow_short)},
                "volume_mult": float(volume_mult),
            }
        },
        "entries": {"min_rr_required": float(min_rr)},
    }


def _sample_daytrade(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    macd_fast = trial.suggest_int("macd_fast", 8, 18)
    macd_slow = trial.suggest_int("macd_slow", 20, 34)
    macd_signal = trial.suggest_int("macd_signal", 6, 12)
    bb_mult = trial.suggest_float("bb_mult", 1.8, 2.8)
    min_rr = trial.suggest_float("min_rr_required", 1.3, 1.8)
    return {
        "strategies": {
            "daytrade": {
                "macd_fast": macd_fast,
                "macd_slow": macd_slow,
                "macd_signal": macd_signal,
                "bb_mult": float(bb_mult),
            }
        },
        "entries": {"min_rr_required": float(min_rr)},
    }


def _sample_trend(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    rsi_long_min = trial.suggest_float("rsi_long_min", 30.0, 55.0)
    rsi_long_max = trial.suggest_float("rsi_long_max", 60.0, 80.0)
    ema_strict = trial.suggest_categorical("ema_strict", [False, True])
    allow_short = trial.suggest_categorical("allow_short", [True, False])
    return {
        "strategies": {
            "trend": {
                "rsi_long_min": float(rsi_long_min),
                "rsi_long_max": float(rsi_long_max),
                "ema_strict": bool(ema_strict),
                "filters": {"allow_short": bool(allow_short)},
            }
        }
    }


def _sample_swing(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    donchian_n = trial.suggest_int("donchian_n", 20, 60)
    trail_k = trial.suggest_float("trail_k", 1.5, 3.5)
    return {
        "strategies": {"swing": {"donchian_n": donchian_n}},
        "exits": {"trailing": {"type": "atr", "k": float(trail_k)}},
    }


def _sample_reversion(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    z_period = trial.suggest_int("zscore_period", 20, 80)
    entry_z = trial.suggest_float("entry_z", 1.0, 2.5)
    exit_z = trial.suggest_float("exit_z", 0.2, 1.0)
    return {"strategies": {"reversion": {"zscore_period": z_period, "entry_z": float(entry_z), "exit_z": float(exit_z)}}}


def _sample_breakout(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    dc_n = trial.suggest_int("donchian_n", 20, 60)
    atr_mult_sl = trial.suggest_float("atr_mult_sl", 1.0, 2.0)
    return {"strategies": {"breakout": {"donchian_n": dc_n, "atr_mult_sl": float(atr_mult_sl)}}}


PARAM_SAMPLERS: Dict[str, ParamSampler] = {
    "scalping": _sample_scalping,
    "daytrade": _sample_daytrade,
    "trend": _sample_trend,
    "swing": _sample_swing,
    "reversion": _sample_reversion,
    "breakout": _sample_breakout,
}


# -------------------------
# Publisher (file-based)
# -------------------------

def publish_params_file(strategy_id: str, overlay: Dict[str, Any], out_dir: Path | None = None) -> Path:
    base = Path("configs") / strategy_id
    if out_dir:
        base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)

    # 1) Load base config (config.yml or CONFIG_PATH) to avoid duplication and ensure completeness
    base_cfg: Dict[str, Any] = load_config() or {}

    # 2) Enforce single-strategy mode and explicitly disable others
    single_mode: Dict[str, Any] = {"strategy": {"use_ensemble": False, "selector": strategy_id}, "strategies": {}}
    for name in PARAM_SAMPLERS.keys():
        single_mode["strategies"][name] = {"enabled": name == strategy_id}

    # 3) Merge: base -> single_mode -> user overlay
    full_cfg = deep_merge(base_cfg, single_mode)
    full_cfg = deep_merge(full_cfg, overlay)

    # 4) Write active.yml
    out_path = base / "active.yml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(full_cfg, f, allow_unicode=True, sort_keys=False)

    # 5) Metadata
    meta = {
        "strategy": strategy_id,
        "published_at": datetime.now().isoformat(),
        "file": str(out_path),
        "overlay_keys": list(overlay.keys()),
    }
    with open(base / "last_published.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return out_path


# -------------------------
# Tuner Core
# -------------------------

class TunerCore:
    def __init__(
        self,
        strategy_id: str,
        study_name: str,
        storage: str,
        window_days: int = 7,
        t_min: Optional[int] = None,
        mdd_cap: float = 8.0,
        publish_mode: str = "none",  # none|file
        publish_dir: Optional[str] = None,
    ) -> None:
        if strategy_id not in PARAM_SAMPLERS:
            raise ValueError(f"Unknown strategy: {strategy_id}")
        self.strategy_id = strategy_id
        self.window_days = int(window_days)
        self.t_min = int(t_min) if t_min is not None else self._default_tmin(strategy_id)
        self.mdd_cap = float(mdd_cap)
        self.publish_mode = publish_mode
        self.publish_dir = publish_dir

        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction="maximize",
            load_if_exists=True,
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=0),
        )

    @staticmethod
    def _default_tmin(strategy_id: str) -> int:
        return {
            "scalping": 50,
            "daytrade": 10,
            "reversion": 10,
            "swing": 5,
            "trend": 5,
            "breakout": 8,
        }.get(strategy_id, 10)

    def _score(self, m: RollingMetrics) -> float:
        # score = Sharpe * min(1, trades/T_min) * (1 - max(0, mdd_pct - mdd_cap)/mdd_cap)
        if m.trades <= 0:
            return 0.0
        trade_term = min(1.0, m.trades / float(self.t_min)) if self.t_min > 0 else 1.0
        dd_penalty = 0.0
        if m.mdd_pct > self.mdd_cap:
            dd_penalty = (m.mdd_pct - self.mdd_cap) / self.mdd_cap
        score = float(m.sharpe) * trade_term * (1.0 - max(0.0, dd_penalty))
        return max(0.0, score)

    def _objective(self, trial: "optuna.trial.Trial") -> float:
        # sample params and build overlay
        sampler = PARAM_SAMPLERS[self.strategy_id]
        overlay = sampler(trial)
        # publish immediately (file) if requested
        if self.publish_mode == "file":
            publish_params_file(self.strategy_id, overlay, Path(self.publish_dir) if self.publish_dir else None)
        # evaluate current rolling metrics (paper mode)
        m = fetch_metrics_rolling(self.strategy_id, window_days=self.window_days)
        score = self._score(m)
        # optional progress
        print(
            f"[TUNER] {self.strategy_id} | 7d: trades={m.trades}, sharpe={m.sharpe:.2f}, mdd={m.mdd_pct:.1f}%, roi={m.roi_pct:.1f}% | score={score:.3f}",
            flush=True,
        )
        # prune very low trades
        trial.report(score, step=m.days)
        if m.trades < max(3, int(0.3 * self.t_min)):
            raise optuna.TrialPruned()
        return float(score)

    def optimize(self, n_trials: int = 1) -> None:
        for _ in range(int(n_trials)):
            try:
                trial = self.study.ask()
                value = self._objective(trial)
                self.study.tell(trial, value)
            except optuna.TrialPruned:
                self.study.tell(trial, state=optuna.trial.TrialState.PRUNED)
            except Exception as e:
                self.study.tell(trial, state=optuna.trial.TrialState.FAIL)

