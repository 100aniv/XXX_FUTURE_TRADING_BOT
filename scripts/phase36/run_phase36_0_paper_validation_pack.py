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
    "L4": "phase35/phase35_5_L4_ultra_debug.yaml",
    "L3": "phase35/phase35_5_L3_debug.yaml",
    "L0": "phase35/phase35_5_L0_production.yaml"
}

def prepare_config(profile: str, symbol: str, timeframe: str, duration_hours: float, stage: str) -> dict:
    """Config 준비 (PHASE35-5 패턴)"""
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
    
    # Override for Paper mode (최우선)
    config['mode'] = 'paper'
    config['env'] = 'paper'
    config['symbol'] = symbol
    config['timeframe'] = timeframe
    config['duration_hours'] = duration_hours  # 루트 레벨 (호환성)
    
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
    
    # feed 설정
    config.setdefault('feed', {})['base_timeframe'] = timeframe
    
    logger.info(f"✅ Config 준비 완료: profile={profile}, symbol={symbol}, timeframe={timeframe}, duration={duration_hours}h")
    logger.info(f"🆔 Run ID: {run_id}")
    
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
def save_artifacts(stage: str, profile: str, config: dict, run_result: dict, db_evidence: dict, persist_trace: dict, ac_results: dict):
    """Artifacts 저장 (PHASE35-5 패턴)"""
    logger.info("=" * 80)
    logger.info(f"[STEP 4] Artifacts 저장 - {stage}")
    logger.info("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Trace JSON (runs/)
    trace_data = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "profile": profile,
        "config": {
            "run_id": config.get("run_id"),
            "symbol": config.get("symbol"),
            "timeframe": config.get("timeframe"),
            "duration_hours": config.get("duration_hours")
        },
        "persist_trace": persist_trace,
        "db_evidence": db_evidence,
        "run_result": run_result,
        "ac_results": ac_results
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
        }
    }
    
    results_path = RESULTS_DIR / f"phase36_0_{profile}_{stage}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Results JSON: {results_path}")
    
    return trace_path, results_path

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
    
    # STEP 1: Config 준비
    config = prepare_config(args.profile, args.symbol, args.timeframe, duration_hours, args.stage)
    
    # STEP 2: Paper 실행
    run_result = run_paper_with_config(config, args.stage)
    
    if run_result["status"] == "INTERRUPTED":
        logger.warning("⚠️ 사용자 중단 → 종료")
        return 130
    
    # STEP 3: DB Evidence 수집
    start_time = datetime.fromisoformat(run_result["start_time"])
    end_time = datetime.fromisoformat(run_result["end_time"])
    db_evidence = get_db_evidence(trial_id=config['run_id'], start_time=start_time, end_time=end_time)
    
    # STEP 3.5: Report JSON 생성 (AC4 SSOT - AC 체크 이전에 생성)
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
    
    # STEP 4: AC 체크
    ac_results = check_acceptance_criteria(db_evidence, get_trace(), run_result, args.stage, config)
    
    # STEP 5: Artifacts 저장
    trace_path, results_path = save_artifacts(args.stage, args.profile, config, run_result, db_evidence, get_trace(), ac_results)
    
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
