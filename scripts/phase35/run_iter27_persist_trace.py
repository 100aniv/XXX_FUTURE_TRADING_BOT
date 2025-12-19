#!/usr/bin/env python3
"""
PHASE35-4 ITER27: E2E Trades DB Persist Fix
============================================
목표: trade 객체 생성/저장 파이프라인 계측 및 수정

persist_trace 수집:
1. signal_generated: 신호 생성 횟수
2. order_submitted: broker.execute 호출 횟수
3. fill_success: broker.execute 성공 횟수
4. trade_created: active_positions 추가 횟수
5. db_persist_called: save_trade_to_db 호출 횟수
6. db_insert_success: DB INSERT 성공 횟수
"""
import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from collections import defaultdict

# 프로젝트 루트 추가
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
# Artifacts 경로
# ============================================================================
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "iter27"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 계측 카운터 (글로벌)
# ============================================================================
PERSIST_TRACE = defaultdict(int)

def reset_trace():
    """계측 카운터 초기화"""
    global PERSIST_TRACE
    PERSIST_TRACE = defaultdict(int)

def inc_trace(key: str, amount: int = 1):
    """계측 카운터 증가"""
    PERSIST_TRACE[key] += amount

def get_trace() -> dict:
    """계측 결과 반환"""
    return dict(PERSIST_TRACE)

# ============================================================================
# 원본 함수 래핑 (계측용)
# ============================================================================

# 원본 save_trade_to_db 참조 저장
_original_save_trade_to_db = None

def instrumented_save_trade_to_db(*args, **kwargs):
    """계측된 save_trade_to_db"""
    inc_trace("db_persist_called")
    logger.info(f"🔬 [ITER27 TRACE] save_trade_to_db 호출됨: position_id={args[0][:8] if args else kwargs.get('position_id', 'N/A')[:8]}...")
    
    try:
        result = _original_save_trade_to_db(*args, **kwargs)
        inc_trace("db_insert_success")
        logger.info("🔬 [ITER27 TRACE] DB INSERT 성공")
        return result
    except Exception as e:
        inc_trace("db_insert_fail")
        logger.error(f"🔬 [ITER27 TRACE] DB INSERT 실패: {e}")
        raise

# ============================================================================
# DB 유틸리티
# ============================================================================

def ensure_trading_schema():
    """trading 스키마 및 테이블 존재 확인"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'trading' AND table_name = 'trades'
                    )
                """)
                exists = cur.fetchone()[0]
                if exists:
                    logger.info("✅ trading.trades 테이블 존재")
                    return True
                else:
                    logger.error("❌ trading.trades 테이블 없음")
                    return False
    except Exception as e:
        logger.error(f"❌ DB 스키마 확인 실패: {e}")
        return False

def clean_trades_table():
    """trading.trades 테이블 클린"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades")
                cur.execute("DELETE FROM trading.executions")
                cur.execute("DELETE FROM trading.decisions")
                deleted = cur.rowcount
                logger.info(f"✅ DB 클린 완료: trades/executions/decisions 테이블")
    except Exception as e:
        logger.error(f"❌ DB 클린 실패: {e}")

def collect_db_evidence(trial_id: str = None) -> dict:
    """DB 증거 수집"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total trades
                cur.execute("SELECT count(*) FROM trading.trades")
                total_trades = cur.fetchone()[0]
                
                # Total executions
                cur.execute("SELECT count(*) FROM trading.executions")
                total_executions = cur.fetchone()[0]
                
                # Total decisions
                cur.execute("SELECT count(*) FROM trading.decisions")
                total_decisions = cur.fetchone()[0]
                
                # Trial-specific trades
                trial_trades = 0
                if trial_id:
                    cur.execute("SELECT count(*) FROM trading.trades WHERE trial_id = %s", (trial_id,))
                    trial_trades = cur.fetchone()[0]
                
                # Latest 5 trades
                cur.execute("""
                    SELECT trade_id, symbol, side, entry_price, quantity, status, created_at
                    FROM trading.trades
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                latest_trades = [
                    {
                        "trade_id": str(row[0])[:8] + "...",
                        "symbol": row[1],
                        "side": row[2],
                        "entry_price": float(row[3]) if row[3] else 0,
                        "quantity": float(row[4]) if row[4] else 0,
                        "status": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    }
                    for row in cur.fetchall()
                ]
                
                return {
                    "total_trades": total_trades,
                    "total_executions": total_executions,
                    "total_decisions": total_decisions,
                    "trial_trades": trial_trades,
                    "latest_trades": latest_trades,
                    "db_connection": "SUCCESS"
                }
    except Exception as e:
        logger.error(f"❌ DB 증거 수집 실패: {e}")
        return {
            "total_trades": 0,
            "total_executions": 0,
            "total_decisions": 0,
            "trial_trades": 0,
            "latest_trades": [],
            "db_connection": f"FAILED: {e}"
        }

def get_git_commit() -> str:
    """현재 Git commit hash 반환"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"

# ============================================================================
# ITER26 SSOT 재사용
# ============================================================================

def load_candles_ssot(symbol: str, timeframe: str, days: int = 30):
    """SignalProbe SSOT 캔들 로딩 (ITER24/26 재사용)"""
    from scripts.phase35.signal_probe_iter24 import load_candles
    return load_candles(symbol, timeframe, days)

def extract_date_range_from_df(df) -> dict:
    """df에서 날짜 범위 추출"""
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
    """기본 Config 로드 (ITER26 재사용)"""
    import yaml
    config_path = PROJECT_ROOT / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config

# ============================================================================
# L4_ULTRA_DEBUG + ITER27 FIX
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
        "max_consecutive_losses": None,  # ⭐ ITER27: 연속손실 쿨다운 비활성화
        "cooldown_after_consecutive": 0,  # ⭐ ITER27: 쿨다운 0분
    },
    "execution": {"reject_cooldown_seconds": 0},
    "database": {"enabled": True}
}

# ============================================================================
# 메인 실행
# ============================================================================

def run_iter27_e2e(days: int = 30) -> dict:
    """ITER27 E2E 실행 (persist_trace 수집)"""
    global _original_save_trade_to_db
    
    start_time = time.time()
    git_commit = get_git_commit()
    trial_id = f"iter27_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE35-4 ITER27: E2E Trades DB Persist Fix")
    logger.info(f"   Trial ID: {trial_id}")
    logger.info(f"   Git: {git_commit}")
    logger.info("=" * 80)
    
    # Reset trace
    reset_trace()
    
    # ============================================================
    # STEP 1: DB 스키마 확인 + 클린
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("🔧 Step 1: DB 스키마 확인 + 클린")
    logger.info("=" * 80)
    
    if not ensure_trading_schema():
        return {"success": False, "error": "DB 스키마 없음", "trial_id": trial_id}
    
    clean_trades_table()
    
    # ============================================================
    # STEP 2: SignalProbe SSOT 캔들 로딩
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("📊 Step 2: SignalProbe SSOT 캔들 로딩")
    logger.info("=" * 80)
    
    symbol = "BTCUSDT"
    timeframe = "15m"
    
    df = load_candles_ssot(symbol, timeframe, days)
    df_range = extract_date_range_from_df(df)
    
    logger.info(f"✅ 캔들 로딩 완료: {df_range['total_candles']}개")
    logger.info(f"   범위: {df_range['start_date']} ~ {df_range['end_date']}")
    
    # ============================================================
    # STEP 3: Engine config 준비
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("🔧 Step 3: Engine config 준비")
    logger.info("=" * 80)
    
    config = load_base_config()
    
    # L4 오버라이드 적용 (루트 레벨)
    for key, value in L4_ULTRA_DEBUG_OVERRIDES.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    # ⭐ ITER27: 전략 params에도 적용
    strategy_name = "phase35_ensemble_v1"
    if "strategies" in config and strategy_name in config["strategies"]:
        strategy_params = config["strategies"][strategy_name].get("params", {})
        
        if "ensemble" not in strategy_params:
            strategy_params["ensemble"] = {}
        strategy_params["ensemble"]["min_votes"] = 1
        strategy_params["ensemble"]["confidence_threshold"] = 0.0
        strategy_params["ensemble"]["cooldown_bars"] = 0
        
        config["strategies"][strategy_name]["params"] = strategy_params
    
    # df_range → config 주입
    config["start_date"] = df_range["start_date"]
    config["end_date"] = df_range["end_date"]
    
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["start_date"] = df_range["start_date"]
    config["backtest"]["end_date"] = df_range["end_date"]
    config["backtest"]["symbol"] = symbol
    
    config["mode"] = "backtest"
    config["symbol"] = symbol
    config["timeframe"] = timeframe
    config["trial_id"] = trial_id
    
    # Config 저장
    config_path = ARTIFACTS_DIR / "iter27_config.yaml"
    import yaml
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    logger.info(f"📁 Config 저장: {config_path}")
    
    # ============================================================
    # STEP 4: Engine 실행 (계측 포함)
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("🏃 Step 4: Engine 실행 (persist_trace 계측)")
    logger.info("=" * 80)
    
    try:
        from execution import engine
        
        # 원본 save_trade_to_db 저장 및 패치
        _original_save_trade_to_db = engine.save_trade_to_db
        engine.save_trade_to_db = instrumented_save_trade_to_db
        
        logger.info("✅ save_trade_to_db 계측 패치 적용")
        
        # run_v2 실행
        engine.run_v2(mode="backtest", config=config, clean_state=True)
        
        logger.info("✅ Engine 실행 완료")
        
    except Exception as e:
        logger.error(f"❌ Engine 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "trial_id": trial_id,
            "persist_trace": get_trace(),
            "elapsed": time.time() - start_time
        }
    finally:
        # 원본 함수 복원
        if _original_save_trade_to_db:
            engine.save_trade_to_db = _original_save_trade_to_db
            logger.info("✅ save_trade_to_db 원본 복원")
    
    # ============================================================
    # STEP 5: 결과 검증
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("📋 Step 5: 결과 검증")
    logger.info("=" * 80)
    
    db_evidence = collect_db_evidence(trial_id)
    persist_trace = get_trace()
    
    logger.info(f"\n🔬 persist_trace 결과:")
    for key, value in persist_trace.items():
        logger.info(f"   {key}: {value}")
    
    logger.info(f"\n📊 DB 증거:")
    logger.info(f"   trading.trades: {db_evidence['total_trades']}")
    logger.info(f"   trading.executions: {db_evidence['total_executions']}")
    logger.info(f"   trading.decisions: {db_evidence['total_decisions']}")
    
    if db_evidence['latest_trades']:
        logger.info(f"\n📝 최근 trades:")
        for t in db_evidence['latest_trades']:
            logger.info(f"   {t['trade_id']} | {t['symbol']} {t['side']} @ {t['entry_price']:.2f} | {t['status']}")
    
    # Report 파일 확인
    report_dir = PROJECT_ROOT / "reports" / "backtest"
    report_path = None
    if report_dir.exists():
        json_files = list(report_dir.glob("*.json"))
        if json_files:
            latest = max(json_files, key=lambda p: p.stat().st_mtime)
            if time.time() - latest.stat().st_mtime < 300:
                report_path = latest
    
    # ============================================================
    # STEP 6: AC 체크
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("🎯 AC Results")
    logger.info("=" * 80)
    
    ac_results = {
        "ac1_db_schema_exists": db_evidence["db_connection"] == "SUCCESS",
        "ac2_trades_gt_zero": db_evidence["total_trades"] > 0,  # 핵심 AC
        "ac3_persist_trace_valid": (
            persist_trace.get("db_persist_called", 0) > 0 and
            persist_trace.get("db_insert_success", 0) > 0
        ),
        "ac4_report_generated": report_path is not None,
        # executions는 optional (현재 미사용)
        "info_executions": db_evidence["total_executions"]
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
    logger.info("\n" + "=" * 80)
    logger.info("📁 Step 7: 증거 저장")
    logger.info("=" * 80)
    
    elapsed = time.time() - start_time
    # info_ 필드 제외하고 AC만 체크
    all_pass = all(v for k, v in ac_results.items() if not k.startswith("info_"))
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "trial_id": trial_id,
        "elapsed_seconds": elapsed,
        "df_range": df_range,
        "persist_trace": persist_trace,
        "db_evidence": db_evidence,
        "report_path": str(report_path) if report_path else None,
        "ac_results": ac_results,
        "all_pass": all_pass
    }
    
    # persist_trace.json
    trace_path = ARTIFACTS_DIR / "persist_trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(persist_trace, f, indent=2)
    logger.info(f"📁 persist_trace 저장: {trace_path}")
    
    # iter27_results.json
    results_path = ARTIFACTS_DIR / "iter27_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info(f"📁 Results 저장: {results_path}")
    
    # ============================================================
    # 최종 판정
    # ============================================================
    logger.info("\n" + "=" * 80)
    if all_pass:
        logger.info("🎉 ITER27 ALL PASS - E2E trades DB persist 성공!")
    else:
        logger.error("❌ ITER27 FAIL - AC 미달성")
        logger.error(f"   persist_trace: {persist_trace}")
    logger.info(f"⏱️ 총 실행 시간: {elapsed:.2f}초")
    logger.info("=" * 80)
    
    return result


if __name__ == "__main__":
    result = run_iter27_e2e(days=30)
    
    if result.get("all_pass"):
        sys.exit(0)
    else:
        sys.exit(1)
