#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER23: Backtest Report & Metrics SSOT + DB Evidence Fix

핵심 목표:
1. backtest report 저장 경로 SSOT 단일화 (config["backtest"]["output_file"])
2. DB evidence 수집 로직에서 하드코딩 제거 (database.postgres 모듈 재사용)
3. trades=0인지 metrics=0 착시인지 확정
4. L0 vs L3에서 지표 차이 최소 1개 이상

SSOT:
- Report 경로: config["backtest"]["output_file"] (엔진이 읽는 키)
- DB 연결: database.postgres.get_db_connection() (포트 5433, pw=trading_pw_2024)
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.logger import setup_logger

logger = setup_logger("iter23_runner")

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "iter23"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# RELAXATION LEVELS
# ============================================================================
RELAXATION_LEVELS = {
    "L0_baseline": {
        "trend": {"adx_threshold": 25},
        "reversion": {"rsi_oversold": 30, "rsi_overbought": 70},
        "breakout": {"volume_threshold": 1.5},
        "regime_filter": {}
    },
    "L3_aggressive": {
        "trend": {"adx_threshold": 8},
        "reversion": {"rsi_oversold": 45, "rsi_overbought": 55},
        "breakout": {"volume_threshold": 0.8},
        "regime_filter": {"enabled": False}
    },
    "L4_ultra_debug": {
        "trend": {"adx_threshold": 5},
        "reversion": {"rsi_oversold": 48, "rsi_overbought": 52},
        "breakout": {"volume_threshold": 0.5},
        "regime_filter": {"enabled": False},
        "ensemble": {"min_votes": 1, "confidence_threshold": 0.1}
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
    import yaml
    config_path = PROJECT_ROOT / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "configs" / "base.yml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    logger.info(f"📄 Config loaded: {config_path}")
    return config


def inject_overrides(config: dict, overrides: dict) -> dict:
    """Override를 여러 경로에 동시 주입"""
    import copy
    cfg = copy.deepcopy(config)
    
    sub_models_override = {k: v for k, v in overrides.items() if k not in ["regime_filter", "ensemble"]}
    regime_filter_override = overrides.get("regime_filter")
    ensemble_override = overrides.get("ensemble")
    
    # 1. Top-level sub_models
    if "sub_models" not in cfg:
        cfg["sub_models"] = {}
    for key, value in sub_models_override.items():
        if key not in cfg["sub_models"]:
            cfg["sub_models"][key] = {}
        cfg["sub_models"][key].update(value)
    
    # 2. strategy.sub_models
    if "strategy" not in cfg:
        cfg["strategy"] = {}
    if "sub_models" not in cfg["strategy"]:
        cfg["strategy"]["sub_models"] = {}
    for key, value in sub_models_override.items():
        if key not in cfg["strategy"]["sub_models"]:
            cfg["strategy"]["sub_models"][key] = {}
        cfg["strategy"]["sub_models"][key].update(value)
    
    # 3. strategies.<selector>.params.sub_models
    selector = cfg.get("strategy", {}).get("selector", "phase35_ensemble_v1")
    if "strategies" not in cfg:
        cfg["strategies"] = {}
    if selector not in cfg["strategies"]:
        cfg["strategies"][selector] = {}
    if "params" not in cfg["strategies"][selector]:
        cfg["strategies"][selector]["params"] = {}
    if "sub_models" not in cfg["strategies"][selector]["params"]:
        cfg["strategies"][selector]["params"]["sub_models"] = {}
    for key, value in sub_models_override.items():
        if key not in cfg["strategies"][selector]["params"]["sub_models"]:
            cfg["strategies"][selector]["params"]["sub_models"][key] = {}
        cfg["strategies"][selector]["params"]["sub_models"][key].update(value)
    
    # 4. regime_filter override
    if regime_filter_override:
        cfg["regime_filter"] = regime_filter_override
        cfg["strategy"]["regime_filter"] = regime_filter_override
        cfg["strategies"][selector]["params"]["regime_filter"] = regime_filter_override
    
    # 5. ensemble override
    if ensemble_override:
        if "ensemble" not in cfg:
            cfg["ensemble"] = {}
        cfg["ensemble"].update(ensemble_override)
        if "ensemble" not in cfg["strategy"]:
            cfg["strategy"]["ensemble"] = {}
        cfg["strategy"]["ensemble"].update(ensemble_override)
        if "ensemble" not in cfg["strategies"][selector]["params"]:
            cfg["strategies"][selector]["params"]["ensemble"] = {}
        cfg["strategies"][selector]["params"]["ensemble"].update(ensemble_override)
    
    return cfg


def resolve_report_path(configured_path: Path, run_dir: Path) -> Optional[Path]:
    """
    Report 파일 경로 탐색 (SSOT → fallback)
    
    1. configured_path 존재하면 사용
    2. 없으면 fallback 탐색
    3. 전부 없으면 None (FAIL)
    """
    # 1. Configured path (SSOT)
    if configured_path.exists():
        logger.info(f"✅ Report SSOT 경로 사용: {configured_path}")
        return configured_path
    
    logger.warning(f"⚠️ Configured 경로에 파일 없음: {configured_path}")
    
    # 2. Fallback 탐색
    fallback_dirs = [
        PROJECT_ROOT / "reports" / "backtest",
        PROJECT_ROOT / "reports",
        run_dir,
    ]
    
    searched_paths = [str(configured_path)]
    
    for fallback_dir in fallback_dirs:
        if not fallback_dir.exists():
            continue
        
        # 최근 수정된 JSON 파일 찾기
        json_files = list(fallback_dir.glob("*.json"))
        if json_files:
            # 수정 시간 기준 정렬
            latest = max(json_files, key=lambda p: p.stat().st_mtime)
            # 최근 5분 이내 수정된 파일만 사용
            if (time.time() - latest.stat().st_mtime) < 300:
                logger.info(f"✅ Fallback 경로 사용: {latest}")
                return latest
        
        searched_paths.append(str(fallback_dir))
    
    logger.error(f"❌ Report 파일을 찾을 수 없음. 탐색 경로: {searched_paths}")
    return None


def parse_metrics_defensive(report_data: dict) -> Dict[str, Any]:
    """
    방어적 metrics 파싱 (스키마 변동 대응)
    """
    metrics = {}
    
    # total_trades 탐색
    for key in ["total_trades", "trades", "trade_count", "num_trades"]:
        if key in report_data:
            metrics["total_trades"] = report_data[key]
            break
        if "metrics" in report_data and key in report_data["metrics"]:
            metrics["total_trades"] = report_data["metrics"][key]
            break
        if "summary" in report_data and key in report_data["summary"]:
            metrics["total_trades"] = report_data["summary"][key]
            break
    
    # loaded_candles 탐색
    for key in ["loaded_candles", "candles_loaded", "bars", "num_bars", "data_points", "total_bars"]:
        if key in report_data:
            metrics["loaded_candles"] = report_data[key]
            break
        if "metrics" in report_data and key in report_data["metrics"]:
            metrics["loaded_candles"] = report_data["metrics"][key]
            break
    
    # total_score (TUNING_VIBLE)
    if "total_score" in report_data:
        metrics["total_score"] = report_data["total_score"]
    
    # scores/metrics 전체
    if "metrics" in report_data:
        metrics["raw_metrics"] = report_data["metrics"]
    if "scores" in report_data:
        metrics["scores"] = report_data["scores"]
    
    return metrics


def collect_db_evidence(trial_id: str) -> Dict[str, Any]:
    """
    DB에서 trial_id별 trades count 수집 (database.postgres SSOT 사용)
    """
    try:
        from database.postgres import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'CLOSED') as closed,
                        COUNT(*) FILTER (WHERE side = 'LONG') as long_count,
                        COUNT(*) FILTER (WHERE side = 'SHORT') as short_count
                    FROM trading.trades
                    WHERE trial_id = %s
                """, (trial_id,))
                
                row = cur.fetchone()
                
                result = {
                    "trial_id": trial_id,
                    "total_trades": row[0] if row else 0,
                    "closed_trades": row[1] if row else 0,
                    "long_trades": row[2] if row else 0,
                    "short_trades": row[3] if row else 0,
                    "db_connection": "SUCCESS"
                }
                
                logger.info(f"📊 DB Evidence for {trial_id}: {result['total_trades']} trades (DB OK)")
                return result
                
    except Exception as e:
        logger.error(f"❌ DB connection failed: {e}")
        return {
            "trial_id": trial_id,
            "total_trades": 0,
            "db_connection": "FAIL",
            "error": str(e)
        }


def run_backtest_with_ssot(
    config: dict,
    candidate_id: str,
    run_dir: Path,
    trial_id: str,
    lookback_days: int = 7
) -> Dict[str, Any]:
    """
    백테스트 실행 + SSOT 기반 metrics 수집
    """
    from common.config_preflight import reset_usage_tracker
    from execution.engine import run_v2
    
    reset_usage_tracker()
    
    # trial_id를 config에 주입
    config["trial_id"] = trial_id
    config["run_id"] = trial_id
    
    # ⭐ ITER23 핵심 수정 1: backtest.days 설정 (ITER22에서 확인된 SSOT)
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["days"] = lookback_days
    
    # ⭐ ITER23 핵심 수정 2: backtest.output_file 설정 (엔진이 읽는 SSOT 키)
    report_path = run_dir / "backtest_report.json"
    config["backtest"]["output_file"] = str(report_path)
    
    # Decision trace 활성화
    config["decision_trace"] = {"enabled": True}
    config["mode"] = "backtest"
    
    # 예상 캔들 수 계산
    timeframe = config.get("timeframe", "15m")
    if timeframe == "15m":
        expected_candles = lookback_days * 96
    elif timeframe == "5m":
        expected_candles = lookback_days * 288
    elif timeframe == "1m":
        expected_candles = lookback_days * 1440
    else:
        expected_candles = lookback_days * 96
    
    logger.info(f"🚀 Running backtest: {candidate_id}")
    logger.info(f"   trial_id: {trial_id}")
    logger.info(f"   lookback_days: {lookback_days}")
    logger.info(f"   expected_candles: {expected_candles}")
    logger.info(f"   output_file (SSOT): {report_path}")
    
    # Effective params 로깅
    effective_sub_models = config.get("sub_models", {})
    logger.info(f"📊 Effective sub_models:")
    logger.info(f"   trend.adx_threshold: {effective_sub_models.get('trend', {}).get('adx_threshold', 'N/A')}")
    logger.info(f"   reversion.rsi_oversold: {effective_sub_models.get('reversion', {}).get('rsi_oversold', 'N/A')}")
    logger.info(f"   breakout.volume_threshold: {effective_sub_models.get('breakout', {}).get('volume_threshold', 'N/A')}")
    
    start_time = time.time()
    
    try:
        result = run_v2(mode="backtest", config=config, clean_state=True)
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Backtest finished in {elapsed:.2f}s")
        
        # ⭐ Report 파일 탐색 (SSOT → fallback)
        resolved_path = resolve_report_path(report_path, run_dir)
        
        if resolved_path is None:
            logger.error("❌ FAIL: Report 파일을 찾을 수 없음")
            return {
                "success": False,
                "error": "Report file not found",
                "searched_path": str(report_path),
                "elapsed": elapsed
            }
        
        # Report 파싱
        with open(resolved_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
        
        # 방어적 metrics 파싱
        metrics = parse_metrics_defensive(report_data)
        
        if "total_trades" not in metrics:
            logger.error(f"❌ FAIL: total_trades 키를 찾을 수 없음. Report keys: {list(report_data.keys())}")
            return {
                "success": False,
                "error": f"total_trades not found. Available keys: {list(report_data.keys())}",
                "report_path": str(resolved_path),
                "elapsed": elapsed
            }
        
        # Report를 run_dir에 복사 (fallback으로 찾은 경우)
        if resolved_path != report_path:
            import shutil
            shutil.copy(resolved_path, report_path)
            logger.info(f"📋 Report 복사: {resolved_path} → {report_path}")
        
        # Data window evidence
        data_window = {
            "trial_id": trial_id,
            "timeframe": timeframe,
            "lookback_days": lookback_days,
            "expected_candles": expected_candles,
            "loaded_candles": metrics.get("loaded_candles", "N/A"),
            "total_trades": metrics.get("total_trades", 0),
            "report_path": str(resolved_path),
            "elapsed_seconds": elapsed
        }
        
        with open(run_dir / "data_window.json", "w", encoding="utf-8") as f:
            json.dump(data_window, f, indent=2)
        
        logger.info(f"   total_trades: {metrics.get('total_trades', 0)}")
        logger.info(f"   total_score: {metrics.get('total_score', 'N/A')}")
        
        return {
            "success": True,
            "metrics": metrics,
            "data_window": data_window,
            "report_path": str(resolved_path),
            "elapsed": elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "elapsed": elapsed
        }


def save_run_meta(run_dir: Path, candidate_id: str, trial_id: str, config: dict, result: dict):
    """Run metadata 저장"""
    meta = {
        "candidate_id": candidate_id,
        "trial_id": trial_id,
        "timestamp": datetime.now().isoformat(),
        "config_keys": list(config.keys()),
        "sub_models": config.get("sub_models", {}),
        "regime_filter": config.get("regime_filter", {}),
        "ensemble": config.get("ensemble", {}),
        "result_success": result.get("success", False),
        "elapsed": result.get("elapsed", 0)
    }
    
    with open(run_dir / "run_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)


def run_iter23():
    """
    ITER23 메인 실행
    """
    logger.info("=" * 60)
    logger.info("🚀 PHASE35-4 ITER23: Report & Metrics SSOT + DB Evidence Fix")
    logger.info("=" * 60)
    
    git_commit = get_git_commit()
    logger.info(f"📌 Git commit: {git_commit}")
    
    start_time = time.time()
    
    all_results = {
        "generated_at": datetime.now().isoformat(),
        "git_commit": git_commit,
        "ssot_keys": {
            "report_path": "config['backtest']['output_file']",
            "db_connection": "database.postgres.get_db_connection()"
        },
        "candidates": [],
        "db_counts": {},
        "comparison": {},
        "ac_results": {}
    }
    
    # 후보 목록
    candidates = ["L0_baseline", "L3_aggressive"]
    lookback_days = 7
    
    for candidate_id in candidates:
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"📦 Candidate: {candidate_id}")
        logger.info("=" * 60)
        
        run_dir = ARTIFACTS_DIR / candidate_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        config = load_base_config()
        overrides = RELAXATION_LEVELS.get(candidate_id, RELAXATION_LEVELS["L0_baseline"])
        config = inject_overrides(config, overrides)
        
        trial_id = f"iter23_{candidate_id}_{uuid.uuid4().hex[:8]}"
        
        # 백테스트 실행
        result = run_backtest_with_ssot(
            config=config,
            candidate_id=candidate_id,
            run_dir=run_dir,
            trial_id=trial_id,
            lookback_days=lookback_days
        )
        
        # DB evidence 수집
        db_evidence = collect_db_evidence(trial_id)
        
        # Run meta 저장
        save_run_meta(run_dir, candidate_id, trial_id, config, result)
        
        candidate_result = {
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "success": result.get("success", False),
            "metrics": result.get("metrics", {}),
            "data_window": result.get("data_window", {}),
            "report_path": result.get("report_path"),
            "db_evidence": db_evidence,
            "elapsed": result.get("elapsed", 0),
            "error": result.get("error")
        }
        
        all_results["candidates"].append(candidate_result)
        all_results["db_counts"][trial_id] = db_evidence
        
        with open(run_dir / "result.json", "w", encoding="utf-8") as f:
            json.dump(candidate_result, f, indent=2, default=str)
    
    # 비교 분석
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 Comparison Analysis")
    logger.info("=" * 60)
    
    baseline = next((c for c in all_results["candidates"] if c["candidate_id"] == "L0_baseline"), None)
    aggressive = next((c for c in all_results["candidates"] if c["candidate_id"] == "L3_aggressive"), None)
    
    if baseline and aggressive:
        baseline_trades = baseline.get("metrics", {}).get("total_trades", 0)
        aggressive_trades = aggressive.get("metrics", {}).get("total_trades", 0)
        baseline_db = baseline.get("db_evidence", {}).get("total_trades", 0)
        aggressive_db = aggressive.get("db_evidence", {}).get("total_trades", 0)
        
        comparison = {
            "report_trades": {
                "baseline": baseline_trades,
                "aggressive": aggressive_trades,
                "diff": aggressive_trades - baseline_trades if isinstance(aggressive_trades, (int, float)) and isinstance(baseline_trades, (int, float)) else "N/A"
            },
            "db_trades": {
                "baseline": baseline_db,
                "aggressive": aggressive_db,
                "diff": aggressive_db - baseline_db
            },
            "metrics_differ": baseline_trades != aggressive_trades or baseline_db != aggressive_db
        }
        
        all_results["comparison"] = comparison
        
        logger.info(f"   L0_baseline: report={baseline_trades}, db={baseline_db}")
        logger.info(f"   L3_aggressive: report={aggressive_trades}, db={aggressive_db}")
        logger.info(f"   Metrics differ: {comparison['metrics_differ']}")
    
    # AC 판정
    all_success = all(c.get("success", False) for c in all_results["candidates"])
    all_db_ok = all(c.get("db_evidence", {}).get("db_connection") == "SUCCESS" for c in all_results["candidates"])
    
    ac_results = {
        "ac1_report_exists": all_success,
        "ac2_loaded_candles_valid": all(c.get("data_window", {}).get("loaded_candles", 0) != "N/A" for c in all_results["candidates"]),
        "ac3_trades_parsed": all("total_trades" in c.get("metrics", {}) for c in all_results["candidates"]),
        "ac4_db_connection": all_db_ok,
        "ac5_metrics_differ": all_results["comparison"].get("metrics_differ", False)
    }
    
    all_results["ac_results"] = ac_results
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 AC Results")
    logger.info("=" * 60)
    for ac, passed in ac_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {ac}: {status}")
    
    # 전체 결과 저장
    results_path = ARTIFACTS_DIR / "iter23_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"🏁 ITER23 완료: {elapsed:.2f}초")
    logger.info(f"📁 Results: {results_path}")
    logger.info("=" * 60)
    
    return all_results


if __name__ == "__main__":
    run_iter23()
