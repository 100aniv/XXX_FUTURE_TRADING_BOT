#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-1: Batch Sweep Runner
==============================
18개 실험을 순차 실행 (Watchdog 기반)

Usage:
    python scripts/phase34/run_batch_sweep.py
"""
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("batch_sweep")

# 경로
META_PATH = project_root / "configs" / "backtest" / "phase34_sweep" / "sweep_meta.json"
REPORTS_DIR = project_root / "reports" / "backtest" / "phase34" / "sweep"
MANIFEST_PATH = REPORTS_DIR / "batch_manifest.json"

# Timeout (3M backtest = 900s per PHASE34-0 doc)
TIMEOUT_PER_RUN = 900


def load_meta() -> dict:
    """메타 파일 로드"""
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_single_experiment(exp: Dict[str, Any], exp_idx: int, total: int) -> Dict[str, Any]:
    """단일 실험 실행"""
    exp_id = exp["id"]
    config_file = project_root / exp["config_file"]
    summary_file = project_root / exp["summary_file"]
    
    logger.info("=" * 80)
    logger.info(f"🧪 [{exp_idx}/{total}] {exp_id}")
    logger.info(f"   Config: {config_file.name}")
    logger.info(f"   Timeout: {TIMEOUT_PER_RUN}s")
    logger.info("=" * 80)
    
    # 결과 디렉토리 생성
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Watchdog 커맨드 구성
    backtest_cmd = f"python scripts/run_backtest.py --config {config_file}"
    watchdog_cmd = [
        sys.executable,
        "scripts/utils/run_watchdog.py",
        "--command", backtest_cmd,
        "--timeout", str(TIMEOUT_PER_RUN),
        "--summary-path", str(summary_file),
        "--run-id", exp_id
    ]
    
    # 실행
    start_time = time.time()
    result = {
        "id": exp_id,
        "params": exp["params"],
        "start_time": datetime.now().isoformat(),
        "success": False,
        "exit_code": None,
        "duration_seconds": 0,
        "summary_exists": False,
        "error": None
    }
    
    try:
        proc = subprocess.run(
            watchdog_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_RUN + 60  # Watchdog 자체 타임아웃 + 여유
        )
        
        result["exit_code"] = proc.returncode
        result["duration_seconds"] = time.time() - start_time
        result["summary_exists"] = summary_file.exists()
        
        # 성공 판정: exit code 0 + summary 존재
        if proc.returncode == 0 and summary_file.exists():
            result["success"] = True
            logger.info(f"✅ {exp_id} SUCCESS ({result['duration_seconds']:.1f}s)")
        else:
            result["success"] = False
            result["error"] = f"Exit={proc.returncode}, Summary={summary_file.exists()}"
            logger.warning(f"⚠️  {exp_id} FAIL: {result['error']}")
            
            # stderr 로깅 (처음 500자)
            if proc.stderr:
                logger.warning(f"   stderr: {proc.stderr[:500]}")
        
    except subprocess.TimeoutExpired:
        result["error"] = f"Watchdog timeout (>{TIMEOUT_PER_RUN + 60}s)"
        result["duration_seconds"] = time.time() - start_time
        logger.error(f"❌ {exp_id} TIMEOUT: {result['error']}")
        
    except Exception as e:
        result["error"] = str(e)
        result["duration_seconds"] = time.time() - start_time
        logger.error(f"❌ {exp_id} EXCEPTION: {e}")
    
    return result


def run_batch_sweep():
    """배치 실행"""
    logger.info("=" * 80)
    logger.info("PHASE34-1: Batch Sweep Runner")
    logger.info("=" * 80)
    
    # 메타 로드
    meta = load_meta()
    experiments = meta["experiments"]
    total = len(experiments)
    
    logger.info(f"📋 Total experiments: {total}")
    logger.info(f"⏱️  Timeout per run: {TIMEOUT_PER_RUN}s")
    logger.info(f"🕒 Estimated total: {(TIMEOUT_PER_RUN * total) / 3600:.1f}h")
    logger.info("")
    
    # 배치 매니페스트
    manifest = {
        "batch_start": datetime.now().isoformat(),
        "total_experiments": total,
        "timeout_per_run": TIMEOUT_PER_RUN,
        "results": []
    }
    
    # 순차 실행
    success_count = 0
    fail_count = 0
    
    for idx, exp in enumerate(experiments, start=1):
        result = run_single_experiment(exp, idx, total)
        manifest["results"].append(result)
        
        if result["success"]:
            success_count += 1
        else:
            fail_count += 1
        
        # 중간 저장 (실패 시 복구 가능)
        manifest["batch_end"] = datetime.now().isoformat()
        manifest["success_count"] = success_count
        manifest["fail_count"] = fail_count
        
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        
        # 실험 간 쿨다운 (5초)
        if idx < total:
            time.sleep(5)
    
    # 최종 요약
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Batch Sweep Complete")
    logger.info("=" * 80)
    logger.info(f"✅ Success: {success_count}/{total}")
    logger.info(f"❌ Failed: {fail_count}/{total}")
    logger.info(f"📋 Manifest: {MANIFEST_PATH}")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_batch_sweep()
