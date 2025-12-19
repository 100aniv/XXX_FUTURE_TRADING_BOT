#!/usr/bin/env python3
"""
PHASE35-5: Validation Pack Runner (7D/1M/3M)
=============================================
목표: 단일 SSOT runner로 7D/1M/3M 백테스트 결과팩 생성

재사용 SSOT:
- ITER27: persist_trace 계측, DB evidence, to_native() 수정
- ITER26: load_candles_ssot, extract_date_range_from_df
- Signal Probe: load_candles 패턴

옵션:
--window 7d|1m|3m : 백테스트 기간
--profile L4       : 신호 프로파일 (기본 L4_ultra_debug)
--symbol BTCUSDT   : 심볼 (기본 BTCUSDT)
--timeframe 15m    : 타임프레임 (기본 15m)
"""
import sys
import os
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Artifacts 경로 (PHASE35-5 표준)
# ============================================================================
BASE_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "phase35_5"
BASE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

RUNS_DIR = BASE_ARTIFACTS_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_DIR = BASE_ARTIFACTS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# persist_trace 계측 (ITER27 SSOT)
# ============================================================================
PERSIST_TRACE = defaultdict(int)

def reset_trace():
    global PERSIST_TRACE
    PERSIST_TRACE = defaultdict(int)

def inc_trace(key: str, amount: int = 1):
    PERSIST_TRACE[key] += amount

def get_trace() -> dict:
    return dict(PERSIST_TRACE)

# ============================================================================
# 원본 함수 래핑 (ITER27 SSOT)
# ============================================================================
_original_save_trade_to_db = None

def instrumented_save_trade_to_db(*args, **kwargs):
    """계측된 save_trade_to_db (ITER27 SSOT)"""
    inc_trace("db_persist_called")
    logger.info(f"🔬 [TRACE] save_trade_to_db called: position_id={args[0][:8] if args else 'N/A'}...")
    
    try:
        result = _original_save_trade_to_db(*args, **kwargs)
        inc_trace("db_insert_success")
        logger.info("🔬 [TRACE] DB INSERT success")
        return result
    except Exception as e:
        inc_trace("db_insert_fail")
        logger.error(f"🔬 [TRACE] DB INSERT fail: {e}")
        raise

# ============================================================================
# DB 유틸리티 (ITER27 SSOT)
# ============================================================================
def get_db_evidence(trial_id: str = None) -> dict:
    """DB 증거 수집"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total trades
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                total_trades = cur.fetchone()[0]
                
                # Trial-specific trades
                if trial_id:
                    cur.execute(
                        "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s",
                        (trial_id,)
                    )
                    trial_trades = cur.fetchone()[0]
                else:
                    trial_trades = total_trades
                
                # Latest trades
                cur.execute("""
                    SELECT trade_id, symbol, side, entry_price, quantity, status, created_at
                    FROM trading.trades
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                latest_trades = []
                for row in cur.fetchall():
                    latest_trades.append({
                        "trade_id": row[0][:8] + "...",
                        "symbol": row[1],
                        "side": row[2],
                        "entry_price": float(row[3]) if row[3] else None,
                        "quantity": float(row[4]) if row[4] else None,
                        "status": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })
                
                # Executions & decisions
                cur.execute("SELECT COUNT(*) FROM trading.executions")
                total_executions = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM trading.decisions")
                total_decisions = cur.fetchone()[0]
                
                return {
                    "total_trades": total_trades,
                    "total_executions": total_executions,
                    "total_decisions": total_decisions,
                    "trial_trades": trial_trades,
                    "latest_trades": latest_trades,
                    "db_connection": "SUCCESS"
                }
    except Exception as e:
        return {
            "db_connection": "FAIL",
            "error": str(e)
        }

def get_git_commit() -> str:
    """Git commit hash 추출"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        return "unknown"

# ============================================================================
# SSOT 재사용: 캔들 로딩 (ITER26/Signal Probe)
# ============================================================================
def load_candles_ssot(symbol: str, timeframe: str, days: int):
    """SignalProbe SSOT 캔들 로딩"""
    from scripts.phase35.signal_probe_iter24 import load_candles
    return load_candles(symbol, timeframe, days)

def extract_date_range_from_df(df) -> dict:
    """df에서 날짜 범위 추출 (ITER26 SSOT)"""
    import pandas as pd
    
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'time'
    
    if df[ts_col].dtype == 'int64' or df[ts_col].dtype == 'float64':
        min_ts = pd.to_datetime(df[ts_col].min(), unit='ms', utc=True)
        max_ts = pd.to_datetime(df[ts_col].max(), unit='ms', utc=True)
    else:
        min_ts = pd.to_datetime(df[ts_col].min(), utc=True)
        max_ts = pd.to_datetime(df[ts_col].max(), utc=True)
    
    return {
        "start_date": min_ts.strftime("%Y-%m-%d"),
        "end_date": max_ts.strftime("%Y-%m-%d"),
        "start_dt_iso": min_ts.isoformat(),
        "end_dt_iso": max_ts.isoformat(),
        "total_candles": len(df)
    }

def load_base_config():
    """기본 Config 로드"""
    import yaml
    config_path = PROJECT_ROOT / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config

# ============================================================================
# L4_ULTRA_DEBUG Profile (ITER27 SSOT)
# ============================================================================
L4_ULTRA_DEBUG_OVERRIDES = {
    "trend": {"adx_threshold": 0},
    "reversion": {"rsi_oversold": 49, "rsi_overbought": 51},
    "breakout": {"volume_threshold": 0.0},
    "regime_filter": {"enabled": False},
    "ensemble": {"min_votes": 1, "confidence_threshold": 0.0, "cooldown_bars": 0},
    "risk": {
        "cooldown_after_loss": 0,
        "max_trades_per_day": 1000,
        "max_consecutive_losses": None,
        "cooldown_after_consecutive": 0,
    },
    "execution": {"reject_cooldown_seconds": 0},
    "database": {"enabled": True}  # ⭐ DB 강제 활성화
}

# ============================================================================
# 메인 실행
# ============================================================================
def run_validation_pack(
    window: str = "7d",
    profile: str = "L4",
    symbol: str = "BTCUSDT",
    timeframe: str = "15m"
) -> dict:
    """
    Validation Pack 실행
    
    Args:
        window: "7d", "1m", "3m"
        profile: "L4" (기본, L4_ultra_debug)
        symbol: "BTCUSDT"
        timeframe: "15m"
    
    Returns:
        실행 결과 dict
    """
    global _original_save_trade_to_db
    
    start_time = time.time()
    git_commit = get_git_commit()
    trial_id = f"phase35_5_{profile}_{window}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Window → days 변환
    window_days_map = {
        "7d": 7,
        "1m": 30,
        "3m": 90
    }
    days = window_days_map.get(window, 7)
    
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE35-5: Validation Pack Runner")
    logger.info(f"   Window: {window} ({days} days)")
    logger.info(f"   Profile: {profile}")
    logger.info(f"   Symbol: {symbol}")
    logger.info(f"   Timeframe: {timeframe}")
    logger.info(f"   Trial ID: {trial_id}")
    logger.info(f"   Git: {git_commit}")
    logger.info("=" * 80)
    
    # Reset trace
    reset_trace()
    
    # ============================================================
    # STEP 1: 캔들 로딩 (SSOT)
    # ============================================================
    logger.info("\n📊 STEP 1: Loading candles...")
    df = load_candles_ssot(symbol, timeframe, days=days)
    df_range = extract_date_range_from_df(df)
    
    logger.info(f"✅ Loaded {df_range['total_candles']} candles")
    logger.info(f"   Period: {df_range['start_date']} ~ {df_range['end_date']}")
    
    # ============================================================
    # STEP 2: Config 준비
    # ============================================================
    logger.info("\n🔧 STEP 2: Preparing config...")
    config = load_base_config()
    
    # Window 기간 주입
    config["backtest"] = config.get("backtest", {})
    config["backtest"]["start_date"] = df_range["start_date"]
    config["backtest"]["end_date"] = df_range["end_date"]
    
    # L4 profile 적용
    if profile == "L4":
        for key, value in L4_ULTRA_DEBUG_OVERRIDES.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value
            else:
                config[key] = value
        
        # strategies.phase35_ensemble_v1.params에도 적용
        if "strategies" not in config:
            config["strategies"] = {}
        if "phase35_ensemble_v1" not in config["strategies"]:
            config["strategies"]["phase35_ensemble_v1"] = {}
        if "params" not in config["strategies"]["phase35_ensemble_v1"]:
            config["strategies"]["phase35_ensemble_v1"]["params"] = {}
        
        strat_params = config["strategies"]["phase35_ensemble_v1"]["params"]
        for key in ["ensemble", "trend", "reversion", "breakout", "regime_filter"]:
            if key in L4_ULTRA_DEBUG_OVERRIDES:
                strat_params[key] = L4_ULTRA_DEBUG_OVERRIDES[key]
    
    # Trial ID 설정
    config["trial_id"] = trial_id
    config["mode"] = "backtest"
    config["symbol"] = symbol
    config["timeframe"] = timeframe
    
    logger.info(f"✅ Config ready: {profile} profile, window={window}")
    
    # ============================================================
    # STEP 3: save_trade_to_db 계측 (ITER27 SSOT)
    # ============================================================
    logger.info("\n🔬 STEP 3: Instrumenting save_trade_to_db...")
    
    from execution import engine as engine_module
    _original_save_trade_to_db = engine_module.save_trade_to_db
    engine_module.save_trade_to_db = instrumented_save_trade_to_db
    
    logger.info("✅ save_trade_to_db instrumented")
    
    # ============================================================
    # STEP 4: Engine 실행
    # ============================================================
    logger.info("\n🚀 STEP 4: Running engine...")
    
    try:
        from execution import engine
        engine.run_v2(mode="backtest", config=config, clean_state=True)
        logger.info("✅ Engine run completed")
    except Exception as e:
        logger.error(f"❌ Engine run failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # 원본 함수 복원
        engine_module.save_trade_to_db = _original_save_trade_to_db
        logger.info("✅ save_trade_to_db restored")
    
    # ============================================================
    # STEP 5: 결과 수집
    # ============================================================
    logger.info("\n📊 STEP 5: Collecting results...")
    
    persist_trace = get_trace()
    db_evidence = get_db_evidence(trial_id)
    
    # Report path 추출 (다중 경로 시도)
    report_path = None
    
    # 1) config에서 output_file 확인
    if "backtest" in config and "output_file" in config["backtest"]:
        report_path = Path(config["backtest"]["output_file"])
    
    # 2) reports/backtest/에서 최신 파일 찾기 (fallback)
    if report_path is None or not report_path.exists():
        reports_dir = PROJECT_ROOT / "reports" / "backtest"
        if reports_dir.exists():
            # 최근 5분 이내 생성된 backtest_*.json 찾기
            current_time = time.time()
            recent_reports = []
            for f in reports_dir.glob("backtest_*.json"):
                if current_time - f.stat().st_mtime < 300:  # 5분 이내
                    recent_reports.append(f)
            
            if recent_reports:
                # 가장 최근 파일 선택
                report_path = max(recent_reports, key=lambda x: x.stat().st_mtime)
                logger.info(f"✅ Report found (fallback): {report_path}")
    
    if report_path and report_path.exists():
        logger.info(f"✅ Report confirmed: {report_path}")
    else:
        logger.warning(f"⚠️ Report not found")
    
    # ============================================================
    # STEP 6: AC 체크
    # ============================================================
    logger.info("\n🎯 STEP 6: Checking acceptance criteria...")
    
    ac_results = {
        "ac1_db_schema_exists": db_evidence["db_connection"] == "SUCCESS",
        "ac2_trades_gt_zero": db_evidence["total_trades"] > 0,
        "ac3_persist_trace_valid": (
            persist_trace.get("db_persist_called", 0) > 0 and
            persist_trace.get("db_insert_success", 0) > 0
        ),
        "ac4_report_generated": report_path is not None and report_path.exists(),
        "info_db_persist_called": persist_trace.get("db_persist_called", 0),
        "info_db_insert_success": persist_trace.get("db_insert_success", 0),
        "info_trades_count": db_evidence["total_trades"]
    }
    
    for ac, value in ac_results.items():
        if ac.startswith("info_"):
            logger.info(f"   {ac}: {value} (info)")
        else:
            status = "✅ PASS" if value else "❌ FAIL"
            logger.info(f"   {ac}: {status}")
    
    # ============================================================
    # STEP 7: 증거 저장
    # ============================================================
    logger.info("\n📁 STEP 7: Saving evidence...")
    
    elapsed = time.time() - start_time
    all_pass = all(v for k, v in ac_results.items() if not k.startswith("info_"))
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "trial_id": trial_id,
        "window": window,
        "days": days,
        "profile": profile,
        "symbol": symbol,
        "timeframe": timeframe,
        "elapsed_seconds": elapsed,
        "df_range": df_range,
        "persist_trace": persist_trace,
        "db_evidence": db_evidence,
        "report_path": str(report_path) if report_path else None,
        "ac_results": ac_results,
        "all_pass": all_pass
    }
    
    # 결과 JSON 저장
    result_filename = f"phase35_5_{profile}_{window}.json"
    result_path = RESULTS_DIR / result_filename
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"📁 Results saved: {result_path}")
    
    # persist_trace JSON 저장
    trace_filename = f"phase35_5_{profile}_{window}_trace.json"
    trace_path = RUNS_DIR / trace_filename
    with open(trace_path, "w") as f:
        json.dump(persist_trace, f, indent=2)
    
    logger.info(f"📁 Trace saved: {trace_path}")
    
    # ============================================================
    # 최종 판정
    # ============================================================
    logger.info("\n" + "=" * 80)
    if all_pass:
        logger.info(f"✅ PHASE35-5 {window} {profile}: PASS")
    else:
        logger.error(f"❌ PHASE35-5 {window} {profile}: FAIL")
    logger.info(f"⏱️ Elapsed: {elapsed:.2f}s")
    logger.info("=" * 80)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="PHASE35-5 Validation Pack Runner")
    parser.add_argument("--window", choices=["7d", "1m", "3m"], default="7d",
                        help="Backtest window (7d/1m/3m)")
    parser.add_argument("--profile", default="L4",
                        help="Signal profile (default: L4)")
    parser.add_argument("--symbol", default="BTCUSDT",
                        help="Symbol (default: BTCUSDT)")
    parser.add_argument("--timeframe", default="15m",
                        help="Timeframe (default: 15m)")
    
    args = parser.parse_args()
    
    result = run_validation_pack(
        window=args.window,
        profile=args.profile,
        symbol=args.symbol,
        timeframe=args.timeframe
    )
    
    sys.exit(0 if result["all_pass"] else 1)


if __name__ == "__main__":
    main()
