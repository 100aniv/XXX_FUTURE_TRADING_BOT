#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER24: trades=0 근본원인 확정 + UltraDebug E2E

목표:
1. L4_ultra_debug로 E2E trades>0 달성 (신호 생성 → 엔진 → DB)
2. trades=0 근본 원인을 수치로 확정 (sub-model FLAT 이유 TopN + ensemble no_consensus)
3. DecisionTrace/Diag SSOT 산출

SSOT:
- Report 경로: config["backtest"]["output_file"]
- DB 연결: database.postgres.get_db_connection()
- Candles 로딩: ITER23 runner 재사용
"""

import os
import sys
import json
import time
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.logger import setup_logger

logger = setup_logger("iter24_runner")

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "iter24"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# RELAXATION LEVELS (ITER24: L4_ultra_debug 추가)
# ============================================================================
RELAXATION_LEVELS = {
    "L0_baseline": {
        "trend": {"adx_threshold": 25},
        "reversion": {"rsi_oversold": 30, "rsi_overbought": 70},
        "breakout": {"volume_threshold": 1.5},
    },
    "L3_aggressive": {
        "trend": {"adx_threshold": 8},
        "reversion": {"rsi_oversold": 45, "rsi_overbought": 55},
        "breakout": {"volume_threshold": 0.8},
        "regime_filter": {"enabled": False}
    },
    "L4_ultra_debug": {
        "trend": {"adx_threshold": 0},  # ADX 체크 사실상 off
        "reversion": {"rsi_oversold": 49, "rsi_overbought": 51},  # 거의 중앙
        "breakout": {"volume_threshold": 0.0},  # Volume 체크 off
        "regime_filter": {"enabled": False},  # Regime filter 완전 off
        "ensemble": {"min_votes": 1, "confidence_threshold": 0.0}  # 1개 투표만으로 신호 생성
    }
}


def get_git_commit() -> str:
    """현재 Git commit hash 반환"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def load_base_config() -> dict:
    """기본 config 로드"""
    config_path = PROJECT_ROOT / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    
    if not config_path.exists():
        logger.warning(f"⚠️ Config not found: {config_path}, using defaults")
        return {
            "mode": "backtest",
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "lookback": 400,
            "equity": 50000,
            "initial_capital": 50000,
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def run_signal_probe(candidate_id: str, config: dict, run_dir: Path) -> Dict[str, Any]:
    """
    SignalProbe 실행 (오프라인 신호 검증)
    
    Returns:
        {
            'success': bool,
            'signal_counts': {'LONG': int, 'SHORT': int, 'FLAT': int},
            'probe_file': str
        }
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 SignalProbe: {candidate_id}")
    logger.info(f"{'='*80}")
    
    from scripts.phase35.signal_probe_iter24 import probe_strategy_signals, load_candles
    
    # Candles 로드
    df = load_candles(
        symbol=config.get("symbol", "BTCUSDT"),
        timeframe=config.get("timeframe", "15m"),
        days=7
    )
    
    # Probe 실행
    result = probe_strategy_signals(
        config=config,
        df=df,
        candidate_id=candidate_id,
        output_dir=run_dir
    )
    
    signal_counts = result["signal_counts"]
    total_signals = signal_counts["LONG"] + signal_counts["SHORT"]
    
    logger.info(f"📊 SignalProbe Result: LONG={signal_counts['LONG']}, SHORT={signal_counts['SHORT']}, FLAT={signal_counts['FLAT']}")
    
    return {
        "success": total_signals > 0,
        "signal_counts": signal_counts,
        "probe_file": str(run_dir / f"signal_probe_{candidate_id}.json")
    }


def run_backtest_candidate(candidate_id: str, lookback_days: int = 7) -> Dict[str, Any]:
    """
    단일 후보 백테스트 실행 (ITER23 runner 재사용 패턴)
    
    Returns:
        {
            'candidate_id': str,
            'trial_id': str,
            'success': bool,
            'metrics': dict,
            'db_evidence': dict,
            'signal_probe': dict,
            'diag_summary': dict,
            'elapsed': float
        }
    """
    start_time = time.time()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 Running Backtest: {candidate_id}")
    logger.info(f"{'='*80}")
    
    # Base config 로드
    base_config = load_base_config()
    
    # Trial ID 생성
    trial_id = f"iter24_{candidate_id}_{uuid.uuid4().hex[:8]}"
    
    # Run directory
    run_dir = ARTIFACTS_DIR / candidate_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Config override (relaxation)
    config = base_config.copy()
    relaxation = RELAXATION_LEVELS.get(candidate_id, {})
    
    # SSOT: sub_models 경로에 주입
    if "sub_models" not in config:
        config["sub_models"] = {}
    
    for sub_model, params in relaxation.items():
        if sub_model in ["trend", "reversion", "breakout"]:
            if sub_model not in config["sub_models"]:
                config["sub_models"][sub_model] = {}
            config["sub_models"][sub_model].update(params)
        elif sub_model == "regime_filter":
            config["regime_filter"] = config.get("regime_filter", {})
            config["regime_filter"].update(params)
        elif sub_model == "ensemble":
            config["ensemble"] = config.get("ensemble", {})
            config["ensemble"].update(params)
    
    # Backtest 설정
    config["mode"] = "backtest"
    config["trial_id"] = trial_id
    config["backtest"] = config.get("backtest", {})
    config["backtest"]["days"] = lookback_days
    
    # SSOT: Report 경로 (config["backtest"]["output_file"])
    report_path = run_dir / "backtest_report.json"
    config["backtest"]["output_file"] = str(report_path)
    
    # DecisionTrace 활성화
    config["decision_trace"] = {"enabled": True}
    
    # Effective params 저장
    effective_params_path = run_dir / "effective_params.json"
    effective_params_path.write_text(
        json.dumps({
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "lookback_days": lookback_days,
            "sub_models": config.get("sub_models", {}),
            "regime_filter": config.get("regime_filter", {}),
            "ensemble": config.get("ensemble", {}),
        }, indent=2),
        encoding="utf-8"
    )
    
    # (1) SignalProbe 먼저 실행
    signal_probe_result = run_signal_probe(candidate_id, config, run_dir)
    
    if not signal_probe_result["success"]:
        logger.error(f"❌ AC1 FAIL: {candidate_id} - SignalProbe에서 신호 생성 안됨")
        return {
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "success": False,
            "error": "SignalProbe failed: LONG+SHORT = 0",
            "signal_probe": signal_probe_result,
            "elapsed": time.time() - start_time
        }
    
    logger.info(f"✅ AC1 PASS: SignalProbe에서 신호 생성 확인")
    
    # (2) Backtest 실행
    logger.info(f"▶️ Running backtest engine...")
    
    try:
        from execution.engine import run_v2
        
        run_v2(mode="backtest", config=config, clean_state=True)
        
        logger.info(f"✅ Backtest finished")
    
    except Exception as e:
        logger.error(f"❌ Backtest execution failed: {e}")
        return {
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "success": False,
            "error": f"backtest_exception_{type(e).__name__}",
            "signal_probe": signal_probe_result,
            "elapsed": time.time() - start_time
        }
    
    # (3) Report 파일 확인
    metrics = {}
    report_path_final = None
    
    if report_path.exists():
        report_path_final = str(report_path)
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = {
                "total_trades": report_data.get("total_trades", report_data.get("metrics", {}).get("total_trades", 0)),
                "loaded_candles": report_data.get("loaded_candles", report_data.get("metrics", {}).get("loaded_candles", 0)),
            }
        except Exception as e:
            logger.warning(f"⚠️ Report 파싱 실패: {e}")
    else:
        logger.warning(f"⚠️ Report 파일 없음: {report_path}")
    
    # (4) DB evidence 수집 (SSOT: database.postgres)
    db_evidence = collect_db_evidence(trial_id)
    
    # (5) Diagnostics 수집
    diag_summary = collect_diagnostics(run_dir)
    
    elapsed = time.time() - start_time
    
    logger.info(f"✅ {candidate_id} completed in {elapsed:.2f}s")
    logger.info(f"   DB trades: {db_evidence.get('total_trades', 0)}")
    logger.info(f"   Report path: {report_path_final}")
    
    return {
        "candidate_id": candidate_id,
        "trial_id": trial_id,
        "success": report_path_final is not None,
        "metrics": metrics,
        "report_path": report_path_final,
        "db_evidence": db_evidence,
        "signal_probe": signal_probe_result,
        "diag_summary": diag_summary,
        "elapsed": elapsed
    }


def collect_db_evidence(trial_id: str) -> Dict[str, Any]:
    """
    DB에서 trades 증거 수집 (SSOT: database.postgres.get_db_connection)
    
    Returns:
        {
            'trial_id': str,
            'total_trades': int,
            'closed_trades': int,
            'long_trades': int,
            'short_trades': int,
            'db_connection': 'SUCCESS' | 'FAILED'
        }
    """
    try:
        from database.postgres import get_db_connection
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Total trades (ITER25: qualified query)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s",
                (trial_id,)
            )
            total_trades = cur.fetchone()[0]
            
            # Closed trades (ITER25: qualified query)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND status = 'CLOSED'",
                (trial_id,)
            )
            closed_trades = cur.fetchone()[0]
            
            # Long/Short (ITER25: qualified query)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND side = 'LONG'",
                (trial_id,)
            )
            long_trades = cur.fetchone()[0]
            
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND side = 'SHORT'",
                (trial_id,)
            )
            short_trades = cur.fetchone()[0]
            
            cur.close()
        
        return {
            "trial_id": trial_id,
            "total_trades": total_trades,
            "closed_trades": closed_trades,
            "long_trades": long_trades,
            "short_trades": short_trades,
            "db_connection": "SUCCESS"
        }
    
    except Exception as e:
        logger.error(f"❌ DB evidence collection failed: {e}")
        return {
            "trial_id": trial_id,
            "total_trades": 0,
            "closed_trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "db_connection": f"FAILED: {type(e).__name__}"
        }


def collect_diagnostics(run_dir: Path) -> Dict[str, Any]:
    """
    Diagnostics 수집 (SignalProbe 결과에서 추출)
    
    Returns:
        {
            'sub_model_flat_reasons': {...},
            'ensemble_no_consensus': int
        }
    """
    probe_files = list(run_dir.glob("signal_probe_*.json"))
    
    if not probe_files:
        return {}
    
    try:
        probe_data = json.loads(probe_files[0].read_text(encoding="utf-8"))
        
        # Sub-model FLAT reasons
        sub_model_stats = probe_data.get("sub_model_stats", {})
        flat_reasons = {}
        
        for model_name, stats in sub_model_stats.items():
            flat_reasons[model_name] = stats.get("reasons", {})
        
        # Ensemble no_consensus
        diag = probe_data.get("diagnostics", {})
        counters = diag.get("counters", {})
        ensemble_no_consensus = sum(v for k, v in counters.items() if "no_consensus" in k.lower())
        
        return {
            "sub_model_flat_reasons": flat_reasons,
            "ensemble_no_consensus": ensemble_no_consensus,
            "top_blockers": sorted(counters.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    except Exception as e:
        logger.error(f"❌ Diagnostics collection failed: {e}")
        return {}


def run_iter24():
    """
    ITER24 메인 실행
    
    Workflow:
    1. 각 후보에 대해 SignalProbe + Backtest 실행
    2. AC 체크
    3. 결과 저장
    """
    logger.info("="*80)
    logger.info("🚀 PHASE35-4 ITER24 Started")
    logger.info("="*80)
    
    start_time = time.time()
    git_commit = get_git_commit()
    
    logger.info(f"📌 Git commit: {git_commit}")
    logger.info(f"📁 Artifacts: {ARTIFACTS_DIR}")
    
    # 후보 리스트
    candidates = ["L0_baseline", "L3_aggressive", "L4_ultra_debug"]
    
    results = []
    
    for candidate_id in candidates:
        result = run_backtest_candidate(candidate_id, lookback_days=7)
        results.append(result)
    
    # AC 체크
    ac_results = check_acceptance_criteria(results)
    
    # 전체 결과 저장
    final_result = {
        "generated_at": datetime.now().isoformat(),
        "git_commit": git_commit,
        "total_elapsed": time.time() - start_time,
        "candidates": results,
        "ac_results": ac_results,
    }
    
    result_path = ARTIFACTS_DIR / "iter24_results.json"
    result_path.write_text(json.dumps(final_result, indent=2), encoding="utf-8")
    
    logger.info("\n" + "="*80)
    logger.info("📋 AC Results")
    logger.info("="*80)
    for ac, passed in ac_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {ac}: {status}")
    
    logger.info("\n" + "="*80)
    logger.info(f"🏁 ITER24 완료: {time.time() - start_time:.2f}초")
    logger.info(f"📁 Results: {result_path}")
    logger.info("="*80)


def check_acceptance_criteria(results: List[Dict[str, Any]]) -> Dict[str, bool]:
    """
    AC 체크
    
    AC1: L4_ultra_debug SignalProbe에서 LONG+SHORT > 0
    AC2: L4_ultra_debug DB trades > 0
    AC3: L0 또는 L3 중 최소 1개는 trades > 0
    AC4: trades=0인 후보의 diag Top blockers 존재
    """
    ac1 = False
    ac2 = False
    ac3 = False
    ac4 = False
    
    for result in results:
        cid = result["candidate_id"]
        
        # AC1: L4 SignalProbe
        if cid == "L4_ultra_debug":
            signal_probe = result.get("signal_probe", {})
            signal_counts = signal_probe.get("signal_counts", {})
            total_signals = signal_counts.get("LONG", 0) + signal_counts.get("SHORT", 0)
            ac1 = total_signals > 0
        
        # AC2: L4 DB trades
        if cid == "L4_ultra_debug":
            db_trades = result.get("db_evidence", {}).get("total_trades", 0)
            ac2 = db_trades > 0
        
        # AC3: L0 또는 L3
        if cid in ["L0_baseline", "L3_aggressive"]:
            db_trades = result.get("db_evidence", {}).get("total_trades", 0)
            if db_trades > 0:
                ac3 = True
        
        # AC4: trades=0인 후보의 diag
        db_trades = result.get("db_evidence", {}).get("total_trades", 0)
        if db_trades == 0:
            diag_summary = result.get("diag_summary", {})
            if diag_summary.get("top_blockers"):
                ac4 = True
    
    return {
        "ac1_l4_signal_probe": ac1,
        "ac2_l4_db_trades": ac2,
        "ac3_l0_or_l3_trades": ac3,
        "ac4_diag_exists": ac4,
    }


if __name__ == "__main__":
    run_iter24()
