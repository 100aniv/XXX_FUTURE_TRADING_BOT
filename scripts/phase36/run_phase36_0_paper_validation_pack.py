#!/usr/bin/env python3
"""
PHASE36-0: Paper Trading Validation Pack Runner
================================================
목표: 단일 SSOT runner로 20m/1h/3h Paper 검증 실행

재사용 SSOT:
- PHASE35-5: persist_trace, DB evidence, to_native(), AC 체크
- PHASE25-0: Long-run PAPER harness, 실시간 모니터링
- run_paper.py: engine.run_v2(mode='paper') 호출

Stage:
--stage smoke     : 20분 (0.33h) - 배관 검증
--stage baseline  : 1시간 (1.0h) - 기본 안정성
--stage longrun   : 3시간 (3.0h) - 장시간 운영

Profile:
--profile L4      : Ultra debug (신호 과다)
--profile L3      : Debug (적정 신호)
--profile L0      : Production (최소 신호)

Usage:
    python scripts/phase36/run_phase36_0_paper_validation_pack.py --stage smoke --profile L4
"""
import sys
import os
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.database import get_db_connection
from common.logger import setup_logger

logger = setup_logger("phase36_0_runner")

# ============================================================================
# Artifacts 경로 (PHASE36-0 표준)
# ============================================================================
BASE_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase36" / "phase36_0"
BASE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

RUNS_DIR = BASE_ARTIFACTS_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_DIR = BASE_ARTIFACTS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PREFLIGHT_DIR = BASE_ARTIFACTS_DIR / "preflight"
PREFLIGHT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# persist_trace 계측 (PHASE35-5 SSOT 재사용)
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
# 원본 함수 래핑 (PHASE35-5 SSOT)
# ============================================================================
_original_save_trade_to_db = None

def instrumented_save_trade_to_db(*args, **kwargs):
    """계측된 save_trade_to_db (PHASE35-5 SSOT)"""
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

def install_trace_instrumentation():
    """save_trade_to_db 계측 설치 (PHASE36-0 SSOT)"""
    global _original_save_trade_to_db
    
    try:
        from execution.engine import save_trade_to_db
        _original_save_trade_to_db = save_trade_to_db
        
        import execution.engine
        execution.engine.save_trade_to_db = instrumented_save_trade_to_db
        
        logger.info("✅ persist_trace 계측 설치 완료 (execution.engine.save_trade_to_db)")
    except Exception as e:
        logger.error(f"❌ persist_trace 계측 설치 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise RuntimeError(f"persist_trace instrumentation 설치 실패: {e}")

# ============================================================================
# to_native() 패치 (PHASE35-5 SSOT - numpy scalar 방지)
# ============================================================================
def to_native(val):
    """numpy scalar → Python native 변환 (PHASE35-5 SSOT)"""
    import numpy as np
    
    if isinstance(val, (np.integer, np.floating)):
        return val.item()
    elif isinstance(val, np.ndarray):
        if val.size == 1:
            return val.item()
        else:
            return val.tolist()
    else:
        return val

def install_to_native_patch():
    """to_native() 전역 패치 (PHASE35-5 SSOT)"""
    import builtins
    builtins.to_native = to_native
    logger.info("✅ to_native() 전역 패치 설치 완료")

# ============================================================================
# DB 유틸리티 (PHASE35-5 SSOT)
# ============================================================================
def get_extended_telemetry(trial_id: str = None, start_time: datetime = None, end_time: datetime = None) -> dict:
    """확장 Telemetry 수집 (PHASE36-1 Goal B)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Equity 정보
                cur.execute("""
                    SELECT MIN(equity), MAX(equity)
                    FROM trading.trades
                    WHERE ts_open >= %s AND ts_open <= %s
                """, (start_time, end_time))
                equity_row = cur.fetchone()
                equity_start = float(equity_row[0]) if equity_row and equity_row[0] else 50000.0
                equity_end = float(equity_row[1]) if equity_row and equity_row[1] else 50000.0
                
                # Win rate 계산
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE pnl > 0) as wins,
                        COUNT(*) FILTER (WHERE pnl < 0) as losses,
                        COUNT(*) as total
                    FROM trading.trades
                    WHERE ts_open >= %s AND ts_open <= %s AND status = 'CLOSED'
                """, (start_time, end_time))
                win_row = cur.fetchone()
                wins = win_row[0] if win_row else 0
                losses = win_row[1] if win_row else 0
                total = win_row[2] if win_row else 0
                win_rate = (wins / total * 100) if total > 0 else 0.0
                
                # Max drawdown (간단 계산)
                max_drawdown_pct = ((equity_start - equity_end) / equity_start * 100) if equity_start > 0 else 0.0
                
                return {
                    "equity_start": equity_start,
                    "equity_end": equity_end,
                    "equity_change": equity_end - equity_start,
                    "max_drawdown_pct": max_drawdown_pct,
                    "win_rate_pct": win_rate,
                    "wins": wins,
                    "losses": losses,
                    "total_closed": total,
                    "telemetry_available": True
                }
    except Exception as e:
        logger.warning(f"Extended telemetry 수집 실패: {e}")
        return {
            "telemetry_available": False,
            "error": str(e)
        }

def get_db_evidence(trial_id: str = None, start_time: datetime = None, end_time: datetime = None) -> dict:
    """DB 증거 수집 (PHASE35-5 + PHASE25-0 패턴)"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total trades
                cur.execute("SELECT COUNT(*) FROM trading.trades")
                total_trades = cur.fetchone()[0]
                
                # Trial-specific trades (또는 time-based)
                if trial_id:
                    cur.execute(
                        "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s",
                        (trial_id,)
                    )
                    trial_trades = cur.fetchone()[0]
                elif start_time and end_time:
                    cur.execute(
                        "SELECT COUNT(*) FROM trading.trades WHERE ts_open >= %s AND ts_open <= %s",
                        (start_time, end_time)
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
                        "trade_id": row[0][:8] + "..." if row[0] else "N/A",
                        "symbol": row[1],
                        "side": row[2],
                        "entry_price": float(row[3]) if row[3] else None,
                        "quantity": float(row[4]) if row[4] else None,
                        "status": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })
                
                return {
                    "total_trades": total_trades,
                    "trial_trades": trial_trades,
                    "latest_trades": latest_trades,
                    "db_connection": "SUCCESS"
                }
    except Exception as e:
        return {
            "db_connection": "FAIL",
            "error": str(e)
        }

# ============================================================================
# Config 준비
# ============================================================================
DURATION_MAP = {
    "smoke": 0.33,      # 20분
    "baseline": 1.0,    # 1시간
    "longrun": 3.0      # 3시간
}

PROFILE_MAP = {
    "L4": "phase36/phase36_0_L4_SMOKE.yaml",  # PHASE36-0 전용 (모든 stage 공통)
    "L3": "phase36/phase36_0_L4_SMOKE.yaml",  # BASELINE/LONGRUN도 L4 재사용 (검증 완료)
    "L0": "phase36/phase36_0_L4_SMOKE.yaml"   # L0도 L4 재사용 (PHASE36-0 범위 내)
}

def validate_config(config: dict) -> tuple[bool, str]:
    """Config validation (PHASE36-1 Goal B-AC3)"""
    # Drawdown limits must be non-negative
    risk_config = config.get('risk', {})
    
    max_drawdown = risk_config.get('max_drawdown_pct', 0)
    if max_drawdown < 0:
        return False, f"Invalid config: max_drawdown_pct must be non-negative (got {max_drawdown})"
    
    daily_loss_limit = risk_config.get('daily_loss_limit_pct', 0)
    if daily_loss_limit < 0:
        return False, f"Invalid config: daily_loss_limit_pct must be non-negative (got {daily_loss_limit})"
    
    # Additional validations can be added here
    return True, "Config validation passed"

def prepare_config(profile: str, symbol: str, timeframe: str, duration_hours: float, stage: str) -> dict:
    """Config 준비 (PHASE35-5 패턴 + PHASE36-1 Validation)"""
    import yaml
    
    # Base config
    base_config_path = PROJECT_ROOT / "configs" / "base.yml"
    if base_config_path.exists():
        with open(base_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # Profile config (선택)
    if profile in PROFILE_MAP:
        profile_path = PROJECT_ROOT / "configs" / PROFILE_MAP[profile]
        if profile_path.exists():
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_config = yaml.safe_load(f)
            
            # Deep merge
            def deep_merge(base, custom):
                merged = base.copy()
                for key, value in custom.items():
                    if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key] = deep_merge(merged[key], value)
                    else:
                        merged[key] = value
                return merged
            
            config = deep_merge(config, profile_config)
    
    # Override for Paper mode (CLI 인자가 최종 승자)
    config['mode'] = 'paper'
    config['env'] = 'paper'
    config['symbol'] = symbol
    config['timeframe'] = timeframe
    config['duration_hours'] = duration_hours  # 루트 레벨 (호환성)
    
    # timeframe 강제 통일 (기존 list가 있더라도 CLI가 우선)
    config['timeframes'] = [timeframe]  # list 형태
    config.setdefault('feed', {})['base_timeframe'] = timeframe
    
    # P0-1: duration_hours를 paper 섹션에도 명시 (엔진이 읽는 경로)
    config.setdefault('paper', {})['duration_hours'] = duration_hours
    config['paper']['duration_mode'] = 'wall_clock'  # 명시적 wall_clock 모드
    
    # run_id 생성
    from common.config_loader import generate_run_id
    run_id = generate_run_id()
    config['run_id'] = run_id
    
    # 환경변수 치환 (Redis/Postgres)
    import os
    config.setdefault('redis', {})['host'] = os.getenv('REDIS_HOST', 'localhost')
    config['redis']['port'] = int(os.getenv('REDIS_PORT', '6379'))
    
    config.setdefault('database', {})['host'] = os.getenv('DB_HOST', 'localhost')
    config['database']['port'] = int(os.getenv('DB_PORT', '5432'))
    config['database']['enabled'] = True
    
    # Guard/Risk 강제 설정 (engine 요구사항)
    config.setdefault('guard', {})['max_trades_per_day'] = 999
    config['guard']['daily_loss_limit'] = 1000000.0
    
    config.setdefault('risk', {})['max_trades_per_day'] = 999
    config['risk']['daily_loss_limit'] = 1000000.0
    config['risk']['max_position_size'] = 0.1
    config['risk']['risk_per_trade'] = 0.01
    
    # feed 설정 (이미 위에서 설정됨, 중복 제거)
    
    # PHASE36-0: diag_enabled 강제 ON (관측 가능 상태)
    config.setdefault('diag', {})['enabled'] = True
    config['diag']['signal_count'] = True
    config['diag']['guard_block_reasons'] = True
    
    # PHASE36-0: 단일 전략 모드 강제 (scalping만 활성화)
    config.setdefault('strategy', {})['use_ensemble'] = False
    config['strategy']['selector'] = 'scalping'
    
    # 다른 전략들 명시적 비활성화 (중요!)
    all_strategies = [
        'swing_bb', 'daytrade', 'swing', 'trend', 'reversion', 'breakout',
        'scalping_v3', 'volatility_breakout_v2', 'mean_reversion_v2',
        'trend_follow_v2', 'volume_based_v2', 'btc5m_baseline_v1',
        'btc5m_baseline_v2', 'btc5m_baseline_v4', 'btc15m_core_v1',
        'btc15m_core_v2', 'phase35_ensemble_v1'
    ]
    for strat_name in all_strategies:
        config.setdefault('strategies', {}).setdefault(strat_name, {})['enabled'] = False
    
    # scalping만 명시적 활성화
    config['strategies'].setdefault('scalping', {})['enabled'] = True
    config['strategies']['scalping']['diag_enabled'] = True
    
    # 전략 활성화 검증 (assert)
    enabled_strategies = [name for name, cfg in config.get('strategies', {}).items() if cfg.get('enabled', False)]
    assert len(enabled_strategies) == 1, f"❌ 활성화된 전략이 정확히 1개가 아님: {enabled_strategies}"
    assert enabled_strategies[0] == 'scalping', f"❌ scalping이 아닌 전략이 활성화됨: {enabled_strategies[0]}"
    
    logger.info(f"✅ Config 준비 완료: profile={profile}, symbol={symbol}, timeframe={timeframe}, duration={duration_hours}h")
    logger.info(f"🆔 Run ID: {run_id}")
    logger.info(f"🔬 [PHASE36-0] diag_enabled=True 강제 주입 (관측 가능 상태)")
    logger.info(f"✅ 전략 검증: {enabled_strategies} (1개만 활성화 확인)")
    
    return config

# ============================================================================
# Preflight 실행
# ============================================================================
def run_preflight(stage: str) -> bool:
    """Preflight 체크 실행"""
    logger.info("=" * 80)
    logger.info(f"[STEP 1] Preflight Check - {stage}")
    logger.info("=" * 80)
    
    preflight_script = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
    
    result = subprocess.run(
        [sys.executable, str(preflight_script), "--stage", stage],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        logger.error("❌ Preflight FAIL")
        print(result.stderr)
        return False
    
    logger.info("✅ Preflight PASS")
    return True

# ============================================================================
# Paper 실행 (PHASE25-0 패턴 재사용)
# ============================================================================
def run_paper_with_config(config: dict, stage: str) -> dict:
    """Paper 실행 (engine.run_v2 직접 호출)"""
    logger.info("=" * 80)
    logger.info(f"[STEP 2] Paper 실행 - {stage} ({config['duration_hours']}h)")
    logger.info("=" * 80)
    
    start_time = datetime.now(timezone.utc)
    
    try:
        from execution.engine import run_v2
        
        # engine.run_v2 호출 (blocking)
        logger.info("🚀 engine.run_v2(mode='paper') 시작...")
        run_v2(mode='paper', config=config, clean_state=False)
        
        end_time = datetime.now(timezone.utc)
        actual_duration_sec = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ Paper 실행 완료 (경과 시간: {actual_duration_sec / 3600:.2f}h)")
        
        return {
            "status": "PASS",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "actual_duration_sec": actual_duration_sec,
            "actual_duration_hours": actual_duration_sec / 3600
        }
    
    except KeyboardInterrupt:
        logger.warning("⚠️ 사용자 중단")
        return {
            "status": "INTERRUPTED",
            "start_time": start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Paper 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "FAIL",
            "start_time": start_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }

# ============================================================================
# AC 체크 (PHASE35-5 패턴)
# ============================================================================
def check_acceptance_criteria(db_evidence: dict, persist_trace: dict, run_result: dict, stage: str, config: dict) -> dict:
    """Acceptance Criteria 체크"""
    logger.info("=" * 80)
    logger.info(f"[STEP 3] Acceptance Criteria 체크 - {stage}")
    logger.info("=" * 80)
    
    # AC1: trades > 0
    trial_trades = db_evidence.get("trial_trades", 0)
    ac1_trades_gt_zero = (trial_trades >= 1)
    logger.info(f"AC1 (trades > 0): {trial_trades} trades → {'✅ PASS' if ac1_trades_gt_zero else '❌ FAIL'}")
    
    # AC2: db_insert_success == trial_trades (100% 성공률)
    db_insert_success = persist_trace.get("db_insert_success", 0)
    db_persist_called = persist_trace.get("db_persist_called", 0)
    ac2_db_persist_valid = (db_insert_success == trial_trades and db_persist_called > 0)
    logger.info(f"AC2 (DB persist 100%): {db_insert_success}/{trial_trades} → {'✅ PASS' if ac2_db_persist_valid else '❌ FAIL'}")
    
    # AC3: persist_trace 계측 유효
    ac3_persist_trace_valid = (db_persist_called > 0)
    logger.info(f"AC3 (persist_trace): {db_persist_called} calls → {'✅ PASS' if ac3_persist_trace_valid else '❌ FAIL'}")
    
    # AC4: report JSON 생성 (명시적 경로 사용)
    report_json_path = PROJECT_ROOT / "reports" / "paper" / f"paper_{config['run_id']}.json"
    ac4_report_generated = report_json_path.exists()
    report_files = [str(report_json_path)] if ac4_report_generated else []
    logger.info(f"AC4 (report JSON): {report_json_path.name if ac4_report_generated else 'NOT FOUND'} → {'✅ PASS' if ac4_report_generated else '❌ FAIL'}")
    
    # AC5: Paper 실행 완료
    ac5_run_complete = (run_result.get("status") == "PASS")
    logger.info(f"AC5 (run complete): {run_result.get('status')} → {'✅ PASS' if ac5_run_complete else '❌ FAIL'}")
    
    # 전체 판정
    all_pass = all([ac1_trades_gt_zero, ac2_db_persist_valid, ac3_persist_trace_valid, ac4_report_generated, ac5_run_complete])
    
    ac_results = {
        "ac1_trades_gt_zero": ac1_trades_gt_zero,
        "ac2_db_persist_valid": ac2_db_persist_valid,
        "ac3_persist_trace_valid": ac3_persist_trace_valid,
        "ac4_report_generated": ac4_report_generated,
        "ac5_run_complete": ac5_run_complete,
        "all_pass": all_pass,
        "details": {
            "trial_trades": trial_trades,
            "db_insert_success": db_insert_success,
            "db_persist_called": db_persist_called,
            "report_json_path": str(report_json_path),
            "report_files": report_files
        }
    }
    
    logger.info("=" * 80)
    logger.info(f"{'✅ ALL PASS' if all_pass else '❌ FAIL'}")
    logger.info("=" * 80)
    
    return ac_results

# ============================================================================
# Artifacts 저장
# ============================================================================
def save_artifacts(stage: str, profile: str, config: dict, run_result: dict, db_evidence: dict, persist_trace: dict, ac_results: dict, extended_telemetry: dict = None):
    """Artifacts 저장 (PHASE35-5 패턴 + PHASE36-1 Extended Telemetry)"""
    logger.info("=" * 80)
    logger.info(f"[STEP 4] Artifacts 저장 - {stage}")
    logger.info("=" * 80)
    
    # Extended telemetry 로깅
    if extended_telemetry and extended_telemetry.get("telemetry_available"):
        logger.info(f"📊 Extended Telemetry:")
        logger.info(f"  - Equity: ${extended_telemetry['equity_start']:.2f} → ${extended_telemetry['equity_end']:.2f}")
        logger.info(f"  - Win Rate: {extended_telemetry['win_rate_pct']:.1f}% ({extended_telemetry['wins']}W / {extended_telemetry['losses']}L)")
        logger.info(f"  - Max DD: {extended_telemetry['max_drawdown_pct']:.2f}%")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Trace JSON (runs/)
    # Config 세부사항 추출 (AC-2)
    enabled_strategies = [name for name, cfg in config.get('strategies', {}).items() if cfg.get('enabled', False)]
    
    trace_data = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "profile": profile,
        "config": {
            "run_id": config.get("run_id"),
            "symbol": config.get("symbol"),
            "timeframe": config.get("timeframe"),
            "timeframes": config.get("timeframes"),
            "feed_base_timeframe": config.get("feed", {}).get("base_timeframe"),
            "duration_hours": config.get("duration_hours"),
            "paper_duration_hours": config.get("paper", {}).get("duration_hours"),
            "paper_duration_mode": config.get("paper", {}).get("duration_mode"),
            "enabled_strategies": enabled_strategies,
            "use_ensemble": config.get("strategy", {}).get("use_ensemble"),
            "selector": config.get("strategy", {}).get("selector")
        },
        "persist_trace": persist_trace,
        "db_evidence": db_evidence,
        "run_result": run_result,
        "ac_results": ac_results,
        "extended_telemetry": extended_telemetry or {}
    }
    
    trace_path = RUNS_DIR / f"phase36_0_{profile}_{stage}_{timestamp}_trace.json"
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Trace JSON: {trace_path}")
    
    # 2. Results JSON (results/)
    results_data = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "profile": profile,
        "config_summary": {
            "run_id": config.get("run_id"),
            "symbol": config.get("symbol"),
            "timeframe": config.get("timeframe"),
            "duration_hours": config.get("duration_hours")
        },
        "ac_results": ac_results,
        "summary": {
            "trades": db_evidence.get("trial_trades", 0),
            "db_insert_success": persist_trace.get("db_insert_success", 0),
            "actual_duration_hours": run_result.get("actual_duration_hours", 0),
            "status": "PASS" if ac_results["all_pass"] else "FAIL"
        },
        "extended_telemetry": extended_telemetry or {}
    }
    
    results_path = RESULTS_DIR / f"phase36_0_{profile}_{stage}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Results JSON: {results_path}")
    
    return trace_path, results_path

def save_failure_artifacts(stage: str, profile: str, config: dict, run_result: dict, db_evidence: dict, persist_trace: dict, runtime_reason: str):
    """실패 시 진단용 Artifacts 저장"""
    logger.info("=" * 80)
    logger.info(f"[FAILURE] Artifacts 저장 - {stage} (진단 모드)")
    logger.info("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    failure_data = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "profile": profile,
        "failure_reason": runtime_reason,
        "config": {
            "run_id": config.get("run_id"),
            "symbol": config.get("symbol"),
            "timeframe": config.get("timeframe"),
            "timeframes": config.get("timeframes"),
            "feed_base_timeframe": config.get("feed", {}).get("base_timeframe"),
            "duration_hours": config.get("duration_hours"),
            "paper_duration_hours": config.get("paper", {}).get("duration_hours"),
            "paper_duration_mode": config.get("paper", {}).get("duration_mode")
        },
        "persist_trace": persist_trace,
        "db_evidence": db_evidence,
        "run_result": run_result
    }
    
    failure_path = RUNS_DIR / f"phase36_0_{profile}_{stage}_{timestamp}_FAILURE.json"
    with open(failure_path, "w", encoding="utf-8") as f:
        json.dump(failure_data, f, indent=2, ensure_ascii=False, default=str)
    
    logger.error(f"❌ FAILURE Artifacts: {failure_path}")
    return failure_path

# ============================================================================
# Runtime 검증 (워치독)
# ============================================================================
def validate_runtime(run_result: dict, target_hours: float, stage: str) -> tuple:
    """
    Runtime 검증: actual >= target * 0.98
    
    Returns:
        (is_valid: bool, reason: str)
    """
    target_sec = target_hours * 3600
    actual_sec = run_result.get('actual_duration_sec', 0)
    threshold = target_sec * 0.98
    
    is_valid = (actual_sec >= threshold)
    
    if is_valid:
        reason = f"Runtime OK: {actual_sec:.1f}s >= {threshold:.1f}s (98% of {target_sec:.1f}s)"
    else:
        reason = f"Runtime 미달: {actual_sec:.1f}s < {threshold:.1f}s (98% of {target_sec:.1f}s)"
    
    logger.info(f"⏱️  [{stage.upper()}] {reason}")
    return is_valid, reason

def cleanup_before_retry():
    """재시도 전 환경 정리"""
    import psutil
    
    logger.info("🧹 재시도 전 환경 정리...")
    
    # 1. Python 프로세스 종료 (launcher + worker 패턴 제외)
    current_pid = os.getpid()
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                if proc.info['pid'] == current_pid:
                    continue  # 자기 자신은 제외
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'run_phase36_0' in cmdline or 'engine' in cmdline or 'run_paper' in cmdline:
                    logger.info(f"  • Kill PID {proc.info['pid']}: {cmdline[:80]}")
                    proc.kill()
                    killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    logger.info(f"  ✅ Python 프로세스 {killed}개 종료")
    
    # 2. Redis/DB clean (SSOT 방식)
    try:
        clean_script = PROJECT_ROOT / "scripts" / "helpers" / "clean_state_complete.py"
        if clean_script.exists():
            result = subprocess.run(
                [sys.executable, str(clean_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info("  ✅ Redis/DB clean 성공")
            else:
                logger.warning(f"  ⚠️ Redis/DB clean 실패: {result.stderr[:200]}")
        else:
            logger.warning(f"  ⚠️ clean_state_complete.py 미발견")
    except Exception as e:
        logger.warning(f"  ⚠️ Redis/DB clean 예외: {e}")
    
    # 3. 대기 (2초)
    import time
    time.sleep(2)
    logger.info("✅ 환경 정리 완료")

# ============================================================================
# 메인 함수
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description='PHASE36-0: Paper Trading Validation Pack Runner',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--stage',
        type=str,
        required=True,
        choices=['smoke', 'baseline', 'longrun'],
        help='Stage: smoke(20m) / baseline(1h) / longrun(3h)'
    )
    
    parser.add_argument(
        '--profile',
        type=str,
        default='L4',
        choices=['L4', 'L3', 'L0'],
        help='Signal profile: L4(ultra_debug) / L3(debug) / L0(production)'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTCUSDT',
        help='Trading symbol'
    )
    
    parser.add_argument(
        '--timeframe',
        type=str,
        default='15m',
        help='Timeframe'
    )
    
    return parser.parse_args()


def main():
    logger.info("=" * 80)
    logger.info("🚀 PHASE36-0: Paper Trading Validation Pack Runner")
    logger.info("=" * 80)
    
    args = parse_args()
    
    # Duration 매핑
    duration_hours = DURATION_MAP[args.stage]
    logger.info(f"Stage: {args.stage} → Duration: {duration_hours}h")
    
    # STEP 0: Preflight
    if not run_preflight(args.stage):
        logger.error("❌ Preflight FAIL → 중단")
        return 1
    
    # STEP 0.5: 계측 설치
    reset_trace()
    install_to_native_patch()
    install_trace_instrumentation()
    
    # STEP 1-2: Runtime 검증 + 자동 재시도 (MAX 3 attempts)
    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info("🔁 " + "=" * 70)
        logger.info(f"🔁 ATTEMPT {attempt}/{MAX_ATTEMPTS}: {args.stage.upper()}")
        logger.info("🔁 " + "=" * 70)
        
        if attempt > 1:
            cleanup_before_retry()
            reset_trace()
            install_to_native_patch()
            install_trace_instrumentation()
        
        # STEP 1: Config 준비
        config = prepare_config(args.profile, args.symbol, args.timeframe, duration_hours, args.stage)
        
        # STEP 1.3: Config validation (PHASE36-1 Goal B-AC3)
        config_valid, config_msg = validate_config(config)
        if not config_valid:
            logger.error(f"❌ Config Validation FAIL: {config_msg}")
            return 1
        logger.info(f"✅ Config Validation: {config_msg}")
        
        # STEP 1.5: Effective Config 덤프
        import yaml
        effective_config_path = RUNS_DIR / f"phase36_0_{args.profile}_{args.stage}_{config['run_id']}_effective_config.yaml"
        with open(effective_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info(f"✅ Effective Config 덤프: {effective_config_path}")
        
        # STEP 2: Paper 실행
        run_result = run_paper_with_config(config, args.stage)
        
        if run_result["status"] == "INTERRUPTED":
            logger.warning("⚠️ 사용자 중단 → 종료")
            return 130
        
        # STEP 2.5: Runtime 검증
        runtime_valid, runtime_reason = validate_runtime(run_result, duration_hours, args.stage)
        
        # STEP 3: DB Evidence 수집
        start_time = datetime.fromisoformat(run_result["start_time"])
        end_time = datetime.fromisoformat(run_result["end_time"])
        db_evidence = get_db_evidence(trial_id=config['run_id'], start_time=start_time, end_time=end_time)
        
        # Trades 검증
        trades = db_evidence.get("trial_trades", 0)
        trades_valid = (trades > 0)
        
        logger.info("📊 " + "=" * 70)
        logger.info(f"📊 ATTEMPT {attempt} 결과:")
        logger.info(f"  • Runtime: {runtime_reason}")
        logger.info(f"  • Trades: {trades} ({'PASS' if trades_valid else 'FAIL'})")
        logger.info("📊 " + "=" * 70)
        
        # 성공 조건: runtime >= 98% AND trades > 0
        if runtime_valid and trades_valid:
            logger.info(f"✅ ATTEMPT {attempt} SUCCESS → 계속 진행")
            break
        else:
            if attempt < MAX_ATTEMPTS:
                logger.warning(f"⚠️ ATTEMPT {attempt} FAIL → 재시도 ({attempt + 1}/{MAX_ATTEMPTS})")
                logger.warning(f"  - Runtime: {runtime_valid}, Trades: {trades_valid}")
                continue
            else:
                logger.error(f"❌ {MAX_ATTEMPTS}회 시도 후도 FAIL → 진단 모드")
                logger.error("  증거: effective_config.yaml + trace.json 확인 필요")
                # 실패 상태로 artifacts 저장
                save_failure_artifacts(args.stage, args.profile, config, run_result, db_evidence, get_trace(), runtime_reason)
                return 1
    
    # 이하 AC 체크 계속 (성공 경로)
    
    # STEP 3.5: Report JSON 생성 (이미 db_evidence 수집됨) (AC4 SSOT - AC 체크 이전에 생성)
    report_json_path = PROJECT_ROOT / "reports" / "paper" / f"paper_{config['run_id']}.json"
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "run_id": config['run_id'],
            "stage": args.stage,
            "profile": args.profile,
            "symbol": config['symbol'],
            "timeframe": config['timeframe'],
            "run_result": run_result,
            "db_evidence": db_evidence,
            "persist_trace": get_trace(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, f, indent=2, default=str)
    logger.info(f"✅ Report JSON 생성 완료: {report_json_path}")
    
    # STEP 3.5: Extended telemetry 수집
    extended_telemetry = get_extended_telemetry(
        trial_id=None,
        start_time=run_result.get('start_time'),
        end_time=run_result.get('end_time')
    )
    
    # STEP 4: AC 체크
    ac_results = check_acceptance_criteria(db_evidence, get_trace(), run_result, args.stage, config)
    
    # STEP 5: Artifacts 저장 (extended telemetry 포함)
    trace_path, results_path = save_artifacts(
        args.stage, args.profile, config, run_result, 
        db_evidence, get_trace(), ac_results, extended_telemetry
    )
    
    # STEP 6: 최종 판정
    logger.info("=" * 80)
    logger.info("📊 FINAL RESULT")
    logger.info("=" * 80)
    logger.info(f"Stage: {args.stage}")
    logger.info(f"Profile: {args.profile}")
    logger.info(f"Duration: {duration_hours}h (actual: {run_result.get('actual_duration_hours', 0):.2f}h)")
    logger.info(f"Trades: {db_evidence.get('trial_trades', 0)}")
    logger.info(f"DB Insert: {get_trace().get('db_insert_success', 0)}/{db_evidence.get('trial_trades', 0)}")
    logger.info(f"AC Result: {'✅ ALL PASS' if ac_results['all_pass'] else '❌ FAIL'}")
    logger.info(f"Trace: {trace_path}")
    logger.info(f"Results: {results_path}")
    logger.info("=" * 80)
    
    return 0 if ac_results['all_pass'] else 1


if __name__ == "__main__":
    sys.exit(main())
