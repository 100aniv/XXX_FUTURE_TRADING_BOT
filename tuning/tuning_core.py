#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 베이지안 튜닝 코어 (Generic Bayesian Tuning Core)
========================================================
모든 전략과 모드(페이퍼/백테스트)에서 재사용 가능한 베이지안 최적화 엔진

주요 기능:
- 페이퍼 모드: Postgres trading.trades 테이블에서 7일 롤링 메트릭 수집
- 백테스트 모드: subprocess로 백테스트 실행, scorecard.csv 파싱, train/val 분할
- Optuna TPE 샘플러 + MedianPruner로 효율적 탐색
- 파라미터 자동 발행 (configs/<전략>/active.yml)

사용법:
    # 페이퍼 모드
    tuner = TunerCore(strategy_id='scalping', study_name='scalp_paper', mode='paper', ...)
    tuner.optimize(n_trials=10)
    
    # 백테스트 모드
    tuner = TunerCore(strategy_id='scalping', study_name='scalp_bt', mode='backtest',
                      symbol='BTCUSDT', timeframe='1m', start_date='2024-10-01', end_date='2024-12-30', ...)
    tuner.optimize(n_trials=30)
"""
from __future__ import annotations
import os
import math
import json
import yaml
import statistics
import subprocess
import csv
import tempfile
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
# Optuna Storage 헬퍼
# -------------------------

def get_optuna_storage() -> str:
    """
    Optuna Storage URL 결정 (PostgreSQL ONLY)
    
    🚫 CRITICAL: SQLite는 절대 허용하지 않음
    - 병렬 실행 시 race condition 발생
    - Study 손실 위험
    - 프로덕션 환경 부적합
    
    우선순위:
    1. 환경변수 TUNING_DB_URL (명시적 지정)
    2. 환경변수 DATABASE_URL (공유 DB)
    3. Postgres 기본값 (Docker: db_postgres, 로컬: localhost)
    
    Returns:
        Storage URL (PostgreSQL connection string ONLY)
    
    Raises:
        ValueError: SQLite 경로 감지 시
    """
    # 1. 환경변수 TUNING_DB_URL 우선
    if "TUNING_DB_URL" in os.environ:
        storage = os.environ["TUNING_DB_URL"]
        
        # SQLite 감지 → 즉시 에러
        if "sqlite" in storage.lower():
            raise ValueError(
                "❌ CRITICAL ERROR: SQLite is FORBIDDEN for tuning storage!\n"
                f"   Detected: {storage}\n"
                "   Solution: Use PostgreSQL URL\n"
                "   Example: postgresql://trading_user:trading_pw_2024@localhost:5432/trading_db"
            )
        
        print(f"📌 [TUNING STORAGE] 환경변수 사용: {storage.split('@')[1] if '@' in storage else storage}")
        return storage
    
    # 2. DATABASE_URL 환경변수 (공유 DB)
    if "DATABASE_URL" in os.environ:
        db_url = os.environ["DATABASE_URL"]
        
        # SQLite 감지 → 즉시 에러
        if "sqlite" in db_url.lower():
            raise ValueError(
                "❌ CRITICAL ERROR: DATABASE_URL contains SQLite path!\n"
                f"   Detected: {db_url}\n"
                "   Solution: Set DATABASE_URL to PostgreSQL"
            )
        
        # localhost vs docker 호스트 판단
        if "localhost" in db_url or "127.0.0.1" in db_url:
            storage = "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"
            print(f"📌 [TUNING STORAGE] Postgres (로컬): localhost:5433/trading_db")
        else:
            storage = "postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db"
            print(f"📌 [TUNING STORAGE] Postgres (Docker): db_postgres:5432/trading_db")
        
        return storage
    
    # 3. 기본값: Docker Postgres
    storage = "postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db"
    print(f"📌 [TUNING STORAGE] Postgres 기본값 (Docker): db_postgres:5432/trading_db")
    print(f"   💡 로컬 환경이면 DATABASE_URL을 localhost로 설정하세요")
    return storage

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


@dataclass
class BacktestMetrics:
    """백테스트 메트릭 데이터 클래스 (scorecard.csv 기반)"""
    pf: float          # Profit Factor
    winrate: float     # 승률 % (0~100)
    trades: int        # 총 거래 수
    mdd_pct: float     # 최대 낙폭 % (양수)
    sharpe: float      # 샤프 비율
    roi_pct: float     # 수익률 %
    tp_hit_rate: float = 0.0  # TP Hit Rate % (PHASE14)


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


def _sample_scalping_phase15(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    """PHASE15: RR 재탐색 + Risk-Reward 구조 최적화
    
    PHASE14 Best를 중심으로 국소적 탐색:
    - rr: 1.0~1.5 (TP Hit 개선 목표)
    - atr_mult_sl: 1.0~1.3 (SL 구조 재점검)
    - max_cross_age_candles: 10~20 (Fresh Trend 수명 재조정)
    - 기타: PHASE14 Best 주변 유지
    """
    # RSI 임계값 (PHASE14 Best 주변)
    rsi_oversold = trial.suggest_int("rsi_oversold", 24, 30)
    rsi_overbought = trial.suggest_int("rsi_overbought", 69, 75)
    
    # EMA 기간 (PHASE14 Best 주변)
    ema_fast = trial.suggest_int("ema_fast", 8, 12)
    ema_slow = trial.suggest_int("ema_slow", 32, 40)
    
    # PHASE15: Fresh Cross Age 재탐색 (10~20)
    max_cross_age_candles = trial.suggest_int("max_cross_age_candles", 10, 20)
    
    # 모멘텀 & 거래량 (PHASE14 Best 주변)
    momentum_lookback = trial.suggest_int("momentum_lookback", 4, 7)
    volume_mult = trial.suggest_float("volume_mult", 1.15, 1.35)
    
    # PHASE15: RR 재탐색 (1.0~1.5, TP Hit 개선 목표)
    rr = trial.suggest_float("rr", 1.0, 1.5)
    
    # PHASE15: SL 구조 재점검 (1.0~1.3)
    atr_mult_sl = trial.suggest_float("atr_mult_sl", 1.0, 1.3)
    
    # max_hold_minutes (PHASE14 Best 주변)
    max_hold_minutes = trial.suggest_int("max_hold_minutes", 20, 35)
    
    # 숏 허용 여부 (유지)
    allow_short = trial.suggest_categorical("allow_short", [True, False])
    
    return {
        "strategies": {
            "scalping": {
                "rsi_oversold": int(rsi_oversold),
                "rsi_overbought": int(rsi_overbought),
                "ema_fast": int(ema_fast),
                "ema_slow": int(ema_slow),
                "max_cross_age_candles": int(max_cross_age_candles),
                "momentum_lookback": int(momentum_lookback),
                "volume_mult": float(volume_mult),
                "rr": float(rr),
                "atr_mult_sl": float(atr_mult_sl),
                "max_hold_minutes": int(max_hold_minutes),
                "filters": {"allow_short": bool(allow_short)},
            }
        }
    }


def _sample_scalping(trial: "optuna.trial.Trial") -> Dict[str, Any]:
    """PHASE10: 1분봉 고빈도 스캘핑 V1 파라미터 샘플링
    
    튜닝 대상 (PHASE9-6 scalping 전략):
    - EMA 교차 (fast/slow)
    - RSI 극단 (oversold/overbought)
    - 모멘텀 패턴 (lookback)
    - 거래량 급증 (volume_mult)
    - 위험 관리 (RR, SL 배수, 최대 보유 시간)
    
    PHASE14 개선: PHASE13 best trial 기반 정밀 탐색
    - RSI: PHASE13 best(24/70) 기준 좁힌 범위 (24~32, 68~75)
    - volume_mult: 너무 낮은 값 제외 (1.05~1.4)
    - max_cross_age_candles: 중간 범위 집중 (10~17)
    - rr: TP Hit 개선 위해 하향 (1.1~1.35)
    - atr_mult_sl: 너무 타이트한 SL 제외 (1.0~1.4)
    - ema: 범위 좁힘 (fast 8~15, slow 30~50)
    """
    # RSI 임계값 (PHASE14: PHASE13 best 기반 정밀 탐색)
    rsi_oversold = trial.suggest_int("rsi_oversold", 24, 32)
    rsi_overbought = trial.suggest_int("rsi_overbought", 68, 75)
    
    # EMA 기간 (PHASE14: 범위 좁힘, fast < slow 보장)
    ema_fast = trial.suggest_int("ema_fast", 8, 15)
    ema_slow = trial.suggest_int("ema_slow", 30, 50)  # fast보다 항상 큼
    
    # PHASE14: Fresh Cross Age (중간 범위 집중)
    max_cross_age_candles = trial.suggest_int("max_cross_age_candles", 10, 17)
    
    # 모멘텀 & 거래량 (PHASE14: 범위 정밀화)
    momentum_lookback = trial.suggest_int("momentum_lookback", 3, 7)
    volume_mult = trial.suggest_float("volume_mult", 1.05, 1.4)
    
    # 위험 관리 (PHASE14: TP Hit 개선 위해 RR 하향)
    rr = trial.suggest_float("rr", 1.1, 1.35)
    atr_mult_sl = trial.suggest_float("atr_mult_sl", 1.0, 1.4)
    max_hold_minutes = trial.suggest_int("max_hold_minutes", 15, 45)
    
    # 숏 허용 여부
    allow_short = trial.suggest_categorical("allow_short", [True, False])
    
    return {
        "strategies": {
            "scalping": {
                "rsi_oversold": int(rsi_oversold),
                "rsi_overbought": int(rsi_overbought),
                "ema_fast": int(ema_fast),
                "ema_slow": int(ema_slow),
                "max_cross_age_candles": int(max_cross_age_candles),
                "momentum_lookback": int(momentum_lookback),
                "volume_mult": float(volume_mult),
                "rr": float(rr),
                "atr_mult_sl": float(atr_mult_sl),
                "max_hold_minutes": int(max_hold_minutes),
                "filters": {"allow_short": bool(allow_short)},
            }
        }
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
        mode: str = "paper",  # paper|backtest
        window_days: int = 7,
        t_min: Optional[int] = None,
        mdd_cap: float = 8.0,
        publish_mode: str = "none",  # none|file
        publish_dir: Optional[str] = None,
        # 백테스트 전용 파라미터
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_path: Optional[str] = None,
        train_val_split: bool = True,  # train/validation 분할 여부
        val_penalty_weight: float = 0.3,  # validation penalty 가중치
        # PHASE15 모드
        phase: str = "14",  # 14|15
    ) -> None:
        if strategy_id not in PARAM_SAMPLERS:
            raise ValueError(f"Unknown strategy: {strategy_id}")
        if mode not in ["paper", "backtest"]:
            raise ValueError(f"Unknown mode: {mode} (paper|backtest)")
        
        self.strategy_id = strategy_id
        self.mode = mode
        self.window_days = int(window_days)
        self.t_min = int(t_min) if t_min is not None else self._default_tmin(strategy_id)
        self.mdd_cap = float(mdd_cap)
        self.publish_mode = publish_mode
        self.publish_dir = publish_dir
        self.phase = phase  # PHASE15 모드
        
        # 백테스트 모드 파라미터
        if mode == "backtest":
            if not all([symbol, timeframe, start_date, end_date]):
                raise ValueError("백테스트 모드는 symbol, timeframe, start_date, end_date 필수")
            self.symbol = symbol
            self.timeframe = timeframe
            self.start_date = start_date
            self.end_date = end_date
            self.data_path = data_path
            self.train_val_split = train_val_split
            self.val_penalty_weight = val_penalty_weight
            
            # train/val 날짜 계산 (10~11월 train, 12월 val)
            if train_val_split:
                self._calculate_train_val_dates()

        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            direction="maximize",
            load_if_exists=True,
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=0),
        )

    def _calculate_train_val_dates(self):
        """train/validation 날짜 자동 분할 (10~11월 train, 12월 val)"""
        from datetime import datetime
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        
        # 전체 기간의 2/3를 train으로
        total_days = (end - start).days
        train_days = int(total_days * 0.67)
        
        train_end = start + timedelta(days=train_days)
        
        self.train_start = self.start_date
        self.train_end = train_end.strftime("%Y-%m-%d")
        self.val_start = (train_end + timedelta(days=1)).strftime("%Y-%m-%d")
        self.val_end = self.end_date
        
        print(f"📅 Train/Val 분할: Train={self.train_start}~{self.train_end}, Val={self.val_start}~{self.val_end}")
    
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
        """Objective 함수 (mode에 따라 분기)"""
        if self.mode == "paper":
            return self._objective_paper(trial)
        elif self.mode == "backtest":
            return self._objective_backtest(trial)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def _objective_paper(self, trial: "optuna.trial.Trial") -> float:
        """페이퍼 모드 objective (기존 로직)"""
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
    
    def _objective_backtest(self, trial: "optuna.trial.Trial") -> float:
        """백테스트 모드 objective
        
        작업 흐름:
        1. 파라미터 샘플링
        2. 임시 config 오버레이 생성
        3. train 백테스트 실행
        4. validation 백테스트 실행 (선택)
        5. scorecard.csv 파싱
        6. composite score 계산
        """
        # 1. 파라미터 샘플링 (PHASE15 모드 지원)
        if self.phase == "15" and self.strategy_id == "scalping":
            sampler = _sample_scalping_phase15
        else:
            sampler = PARAM_SAMPLERS[self.strategy_id]
        overlay = sampler(trial)
        
        # 2. 임시 오버레이 파일 생성
        temp_overlay_path = self._create_temp_overlay(overlay, trial.number)
        
        try:
            # 3. Train 백테스트 실행
            if self.train_val_split:
                train_metrics = self._run_backtest(
                    overlay_path=temp_overlay_path,
                    start_date=self.train_start,
                    end_date=self.train_end,
                    phase="train"
                )
                
                # 4. Validation 백테스트 실행
                val_metrics = self._run_backtest(
                    overlay_path=temp_overlay_path,
                    start_date=self.val_start,
                    end_date=self.val_end,
                    phase="val"
                )
                
                # 5. Train/Val composite score 계산
                train_score = self._score_backtest(train_metrics, "Train")
                val_score = self._score_backtest(val_metrics, "Val")
                
                # Validation penalty: train/val 점수 차이가 크면 페널티
                score_diff = abs(train_score - val_score)
                val_penalty = self.val_penalty_weight * score_diff
                
                final_score = train_score - val_penalty
                
                print(f"\n{'='*80}")
                print(
                    f"🎯 [TUNER BT] Trial#{trial.number} 최종 결과:\n"
                    f"   📈 TRAIN: PF={train_metrics.pf:.3f}, WR={train_metrics.winrate:.1f}%, T={train_metrics.trades}, score={train_score:.3f}\n"
                    f"   📊 VAL:   PF={val_metrics.pf:.3f}, WR={val_metrics.winrate:.1f}%, T={val_metrics.trades}, score={val_score:.3f}\n"
                    f"   ⚖️  VAL PENALTY: {self.val_penalty_weight} * |{train_score:.3f} - {val_score:.3f}| = {val_penalty:.3f}\n"
                    f"   ✅ FINAL SCORE: {train_score:.3f} - {val_penalty:.3f} = {final_score:.3f}"
                )
                print(f"{'='*80}\n", flush=True)
                
                # Prune 조건: train trades가 너무 적으면
                if train_metrics.trades < max(3, int(0.3 * self.t_min)):
                    raise optuna.TrialPruned()
                
                return float(final_score)
            
            else:
                # Train/Val 분할 없이 전체 기간 백테스트
                metrics = self._run_backtest(
                    overlay_path=temp_overlay_path,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    phase="Full"
                )
                
                score = self._score_backtest(metrics, "Full")
                
                print(f"\n{'='*80}")
                print(
                    f"🎯 [TUNER BT] Trial#{trial.number} 최종 결과:\n"
                    f"   📈 FULL: PF={metrics.pf:.3f}, WR={metrics.winrate:.1f}%, T={metrics.trades}, MDD={metrics.mdd_pct:.2f}%, score={score:.3f}"
                )
                print(f"{'='*80}\n", flush=True)
                
                # Prune 조건
                if metrics.trades < max(3, int(0.3 * self.t_min)):
                    raise optuna.TrialPruned()
                
                return float(score)
        
        finally:
            # 임시 파일 정리
            if temp_overlay_path.exists():
                temp_overlay_path.unlink()
    
    def _create_temp_overlay(self, overlay: Dict[str, Any], trial_number: int) -> Path:
        """임시 오버레이 파일 생성 (디버그 로그 포함)"""
        temp_dir = Path(tempfile.gettempdir()) / "tuning_overlays"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / f"trial_{trial_number}_{self.strategy_id}.yml"
        
        # 디버그: 샘플링된 파라미터 출력
        print(f"\n🔧 [OVERLAY] Trial#{trial_number} 파라미터 샘플링 완료:")
        if "strategies" in overlay and self.strategy_id in overlay["strategies"]:
            strategy_params = overlay["strategies"][self.strategy_id]
            print(f"   strategies.{self.strategy_id}:")
            for key, val in strategy_params.items():
                if key == "filters" and isinstance(val, dict):
                    print(f"     filters:")
                    for fk, fv in val.items():
                        print(f"       {fk}: {fv}")
                else:
                    print(f"     {key}: {val}")
        else:
            print(f"   ⚠️  overlay에 strategies.{self.strategy_id} 없음!")
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(overlay, f, allow_unicode=True, sort_keys=False)
        
        print(f"   📄 Overlay 파일: {temp_path}")
        return temp_path
    
    def _run_backtest(self, overlay_path: Path, start_date: str, end_date: str, phase: str) -> BacktestMetrics:
        """subprocess로 백테스트 실행 및 scorecard.csv 파싱"""
        # run_backtest.py 실행 명령 구성
        cmd = [
            "python", "scripts/run_backtest.py",
            "--mode", "backtest_raw",
            "--strategy", self.strategy_id,
            "--symbol", self.symbol,
            "--timeframe", self.timeframe,
            "--start-date", start_date,
            "--end-date", end_date,
        ]
        
        if self.data_path:
            cmd.extend(["--data-path", self.data_path])
        
        # overlay config 전달
        if overlay_path:
            cmd.extend(["--overlay-config", str(overlay_path)])
        
        # 실행 전 로그
        print(f"\n🔧 [TUNER BT] {phase.upper()} 백테스트 실행 중...")
        print(f"   - Strategy: {self.strategy_id}")
        print(f"   - Symbol/TF: {self.symbol} / {self.timeframe}")
        print(f"   - Period: {start_date} ~ {end_date}")
        if self.data_path:
            print(f"   - Data: {self.data_path}")
        
        # 백테스트 실행
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200,  # 20분 타임아웃
                check=False
            )
            
            if result.returncode != 0:
                print(f"❌ [TUNER BT] 백테스트 실행 실패 ({phase})")
                print(f"   Return code: {result.returncode}")
                print(f"   STDERR: {result.stderr[:500]}")
                # 실패 시 페널티 메트릭 반환
                return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
            
            # artifacts 경로에서 최신 run_id 찾기
            artifacts_dir = Path("artifacts/backtest_raw")
            if not artifacts_dir.exists():
                print(f"❌ [TUNER BT] artifacts 디렉토리 없음: {artifacts_dir}")
                return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
            
            # 최신 run_id 디렉토리 찾기 (생성 시간 기준)
            run_dirs = sorted(artifacts_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not run_dirs:
                print(f"❌ [TUNER BT] 백테스트 결과 없음 (artifacts 비어있음)")
                return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
            
            latest_run = run_dirs[0]
            scorecard_path = latest_run / "scorecard.csv"
            
            print(f"✅ [TUNER BT] 백테스트 완료 ({phase})")
            print(f"   - Artifacts: {latest_run.name}")
            print(f"   - Scorecard: {scorecard_path}")
            
            if not scorecard_path.exists():
                print(f"❌ [TUNER BT] scorecard.csv 파일 없음: {scorecard_path}")
                return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
            
            # scorecard.csv 파싱
            metrics = self._parse_scorecard(scorecard_path, phase)
            return metrics
        
        except subprocess.TimeoutExpired:
            print(f"⏱️  [TUNER BT] 백테스트 타임아웃 ({phase}) - 10분 초과")
            return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
        except Exception as e:
            print(f"❌ [TUNER BT] 백테스트 실행 오류 ({phase}): {e}")
            import traceback
            traceback.print_exc()
            return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0)
    
    def _parse_scorecard(self, scorecard_path: Path, phase: str = "unknown") -> BacktestMetrics:
        """scorecard.csv 파싱 (Metric-Value 페어 형식)"""
        try:
            if not scorecard_path.exists():
                raise FileNotFoundError(f"scorecard.csv가 존재하지 않음: {scorecard_path}")
            
            # Metric-Value 페어를 딕셔너리로 변환
            metrics_dict = {}
            with open(scorecard_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    metric = row.get('Metric', '').strip()
                    value = row.get('Value', '').strip()
                    if metric:
                        metrics_dict[metric] = value
            
            # 각 필드 안전하게 파싱 (NaN, 빈 문자열 처리)
            def safe_float(val, default=0.0):
                try:
                    v = float(val) if val else default
                    return default if math.isnan(v) or math.isinf(v) else v
                except (ValueError, TypeError):
                    return default
            
            def safe_int(val, default=0):
                try:
                    return int(float(val)) if val else default
                except (ValueError, TypeError):
                    return default
            
            pf = safe_float(metrics_dict.get('Profit Factor', 0.0), 0.0)
            winrate = safe_float(metrics_dict.get('Winrate (%)', 0.0), 0.0)
            trades = safe_int(metrics_dict.get('Trades Closed', 0), 0)
            mdd_pct = abs(safe_float(metrics_dict.get('Max Drawdown (%)', 0.0), 0.0))
            sharpe = safe_float(metrics_dict.get('Sharpe Ratio', 0.0), 0.0)
            roi_pct = safe_float(metrics_dict.get('ROI (%)', 0.0), 0.0)
            tp_hit_rate = safe_float(metrics_dict.get('TP Hit (%)', 0.0), 0.0)  # PHASE14
            
            # 파싱 결과 로그
            print(f"📊 [TUNER BT] {phase.upper()} Metrics:")
            print(f"   PF={pf:.3f}, WR={winrate:.1f}%, Trades={trades}, MDD={mdd_pct:.2f}%, Sharpe={sharpe:.2f}, ROI={roi_pct:.2f}%, TP Hit={tp_hit_rate:.1f}%")
            
            # Trades가 0이면 경고
            if trades == 0:
                print(f"⚠️  [TUNER BT] {phase} 기간 거래 없음 (전략 조건 너무 엄격)")
            
            return BacktestMetrics(
                pf=pf,
                winrate=winrate,
                trades=trades,
                mdd_pct=mdd_pct,
                sharpe=sharpe,
                roi_pct=roi_pct,
                tp_hit_rate=tp_hit_rate
            )
        except StopIteration:
            print(f"❌ [TUNER BT] scorecard.csv가 비어있음: {scorecard_path}")
            return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0, tp_hit_rate=0.0)
        except Exception as e:
            print(f"❌ [TUNER BT] scorecard.csv 파싱 실패: {e}")
            print(f"   Path: {scorecard_path}")
            import traceback
            traceback.print_exc()
            return BacktestMetrics(pf=0.0, winrate=0.0, trades=0, mdd_pct=100.0, sharpe=-10.0, roi_pct=-100.0, tp_hit_rate=0.0)
    
    def _score_backtest(self, m: BacktestMetrics, phase: str = "unknown") -> float:
        """백테스트 메트릭을 composite score로 변환
        
        PHASE14 개선: TP Hit Incentive 추가
        - 거래 0건: -100.0 (최악의 Trial)
        - 거래 < MIN_TRADES: 강한 패널티 (한 건당 -0.5)
        - 거래 > MAX_TRADES: 과다 거래 패널티 (한 건당 -0.1)
        - Max DD < -15%: DD 패널티 (초과 1%당 -1.5, PHASE14 완화)
        - Winrate < 20%: WR 패널티 (부족 1%당 -0.3, PHASE14 기준 상향)
        - TP Hit > 0%: TP Bonus (1%당 +0.5, PHASE14 신규)
        - 정상: PF + 0.1*Winrate + tp_bonus - penalties
        
        거래수 기준:
        - Full (30d): 15~80건 (PHASE14 30일 기준)
        - Train (7d): 10건 이상
        - Val (3d): 5건 이상
        """
        # 거래수 기준 (phase별 차등, PHASE14: 30일 기준 조정)
        if phase.lower() == "full":
            MIN_TRADES = 15  # PHASE14: 30일 기준 최소값 상향
            MAX_TRADES = 80  # PHASE14: 30일 기준 최대값 하향
        elif phase.lower() == "train":
            MIN_TRADES = 10
            MAX_TRADES = 999
        else:  # val
            MIN_TRADES = 5
            MAX_TRADES = 999
        
        # 1. 거래 0건: 즉시 실격
        if m.trades == 0:
            print(f"   ❌ {phase.upper()} score=-100.0 (거래 없음 - Trial 실격)")
            return -100.0
        
        # 2. 거래 수 부족: 강한 패널티
        if m.trades < MIN_TRADES:
            shortage = MIN_TRADES - m.trades
            trades_penalty = shortage * 0.5
            penalized_score = -trades_penalty
            print(f"   ⚠️  {phase.upper()} score={penalized_score:.3f} (거래 부족: {m.trades}/{MIN_TRADES}건)")
            return penalized_score
        
        # 3. 정상: 기본 점수 계산
        base_score = m.pf + 0.1 * m.winrate
        
        # 4. 거래 과다 패널티
        trades_penalty = 0.0
        if m.trades > MAX_TRADES:
            excess = m.trades - MAX_TRADES
            trades_penalty = excess * 0.1
        
        # 5. DD 패널티 (PHASE14: 패널티 완화 2.0 → 1.5)
        dd_penalty = 0.0
        DD_CAP = -15.0
        if m.mdd_pct < DD_CAP:
            excess_dd = abs(m.mdd_pct) - abs(DD_CAP)
            dd_penalty = excess_dd * 1.5  # PHASE14: 1%당 -1.5점 (완화)
        
        # 6. Winrate 패널티 (PHASE14: 기준 상향 15% → 20%)
        wr_penalty = 0.0
        WR_MIN = 20.0  # PHASE14: 기준 상향
        if m.winrate < WR_MIN:
            shortage_wr = WR_MIN - m.winrate
            wr_penalty = shortage_wr * 0.3
        
        # 7. TP Hit Incentive (PHASE14 신규)
        tp_bonus = 0.0
        if m.tp_hit_rate > 0:
            tp_bonus = m.tp_hit_rate * 0.5  # 1%당 +0.5점
        
        # 8. 최종 점수
        final_score = base_score - trades_penalty - dd_penalty - wr_penalty + tp_bonus
        
        # 점수 계산 과정 로그
        print(f"💯 [TUNER BT] {phase.upper()} Score 계산:")
        print(f"   base_score = PF({m.pf:.3f}) + 0.1*WR({m.winrate:.1f}%) = {base_score:.3f}")
        print(f"   trades: {m.trades}건 (범위: {MIN_TRADES}~{MAX_TRADES}) → penalty: {trades_penalty:.3f}")
        print(f"   MDD: {m.mdd_pct:.2f}% (cap: {DD_CAP}%) → penalty: {dd_penalty:.3f}")
        print(f"   WR: {m.winrate:.1f}% (min: {WR_MIN}%) → penalty: {wr_penalty:.3f}")
        print(f"   TP Hit: {m.tp_hit_rate:.1f}% → bonus: {tp_bonus:.3f}")
        print(f"   final_score = {base_score:.3f} - {trades_penalty:.3f} - {dd_penalty:.3f} - {wr_penalty:.3f} + {tp_bonus:.3f} = {final_score:.3f}")
        
        return final_score

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

