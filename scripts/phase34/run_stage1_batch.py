#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-3: Stage-1 (7D) Batch Runner
=====================================
18개 Stage-1 실험을 순차 실행 (빠른 스크리닝)

Usage:
    python scripts/phase34/run_stage1_batch.py
"""
import sys
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("stage1_batch")

# 경로
META_PATH = project_root / "configs" / "backtest" / "phase34_stage1" / "stage1_meta.json"
RESULTS_DIR = project_root / "reports" / "backtest" / "phase34" / "stage1"
MANIFEST_PATH = RESULTS_DIR / "stage1_manifest.json"

# Stage-1 타임아웃 (7일 = ~60초 예상)
TIMEOUT_PER_RUN = 120  # 여유롭게 2분


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
    logger.info(f"   기간: 7일 (빠른 스크리닝)")
    logger.info("=" * 80)
    
    # 결과 디렉토리 생성
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 백테스트 직접 실행 (Watchdog 불필요 - 짧은 실행)
    backtest_cmd = [
        sys.executable,
        "scripts/run_backtest.py",
        "--config", str(config_file)
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
        "error": None,
        "metrics": None
    }
    
    try:
        proc = subprocess.run(
            backtest_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_RUN
        )
        
        result["exit_code"] = proc.returncode
        result["duration_seconds"] = time.time() - start_time
        result["summary_exists"] = summary_file.exists()
        
        # Summary 파싱
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    result["metrics"] = summary.get("metrics", {})
            except Exception as e:
                logger.warning(f"Summary 파싱 실패: {e}")
        
        # 성공 판정
        if proc.returncode == 0 and summary_file.exists():
            result["success"] = True
            trades = result["metrics"].get("total_trades", 0) if result["metrics"] else 0
            logger.info(f"✅ {exp_id} SUCCESS ({result['duration_seconds']:.1f}s, {trades} trades)")
        else:
            result["success"] = False
            result["error"] = f"Exit={proc.returncode}, Summary={summary_file.exists()}"
            logger.warning(f"⚠️  {exp_id} FAIL: {result['error']}")
        
    except subprocess.TimeoutExpired:
        result["error"] = f"Timeout (>{TIMEOUT_PER_RUN}s)"
        result["duration_seconds"] = time.time() - start_time
        logger.error(f"❌ {exp_id} TIMEOUT")
        
    except Exception as e:
        result["error"] = str(e)
        result["duration_seconds"] = time.time() - start_time
        logger.error(f"❌ {exp_id} EXCEPTION: {e}")
    
    return result


def run_batch():
    """배치 실행"""
    logger.info("=" * 80)
    logger.info("PHASE34-3: Stage-1 (7D) Batch Runner")
    logger.info("=" * 80)
    
    # 메타 로드
    meta = load_meta()
    experiments = meta["experiments"]
    total = len(experiments)
    
    logger.info(f"📋 Total experiments: {total}")
    logger.info(f"⏱️  Timeout per run: {TIMEOUT_PER_RUN}s")
    logger.info(f"🕒 Estimated total: {(TIMEOUT_PER_RUN * total) / 60:.1f}min")
    logger.info("")
    
    # 매니페스트
    manifest = {
        "stage": "stage1",
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
        
        # 중간 저장
        manifest["batch_end"] = datetime.now().isoformat()
        manifest["success_count"] = success_count
        manifest["fail_count"] = fail_count
        
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # 쿨다운 (3초)
        if idx < total:
            time.sleep(3)
    
    # 최종 요약
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Stage-1 Batch Complete")
    logger.info("=" * 80)
    logger.info(f"✅ Success: {success_count}/{total}")
    logger.info(f"❌ Failed: {fail_count}/{total}")
    
    # 통계
    valid_results = [r for r in manifest["results"] if r["success"] and r.get("metrics")]
    if valid_results:
        avg_trades = sum(r["metrics"]["total_trades"] for r in valid_results) / len(valid_results)
        logger.info(f"📈 평균 거래 수: {avg_trades:.0f}")
    
    logger.info(f"📋 Manifest: {MANIFEST_PATH}")
    logger.info("=" * 80)
    
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run_batch())
