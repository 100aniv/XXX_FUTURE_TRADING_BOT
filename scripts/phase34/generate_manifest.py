#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-4_FIX: Manifest Generator
==================================
Stage-2 18/18 완료 후 manifest 생성
"""
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

REPORTS_DIR = project_root / "reports" / "backtest" / "phase34" / "sweep"
MANIFEST_PATH = REPORTS_DIR / "phase34_batch_results.json"


def generate_manifest():
    """Summary 파일 기준으로 manifest 생성"""
    summary_files = sorted(REPORTS_DIR.glob("p34_*_summary.json"))
    total = 18
    success_count = len(summary_files)

    runs = []
    for sf in summary_files:
        run_id = sf.stem.replace("_summary", "")
        runs.append(
            {
                "run_id": run_id,
                "status": "success",
                "summary_path": str(sf),
                "completed_at": datetime.fromtimestamp(sf.stat().st_mtime).isoformat(),
            }
        )

    manifest = {
        "executed_at": datetime.now().isoformat(),
        "total_configs": total,
        "success_count": success_count,
        "fail_count": total - success_count,
        "timeout_count": 0,
        "runs": runs,
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Manifest generated: {MANIFEST_PATH}")
    print(f"   Total: {total}")
    print(f"   Success: {success_count}/{total}")
    print(f"   Runs: {len(runs)}")

    return 0 if success_count == total else 1


if __name__ == "__main__":
    sys.exit(generate_manifest())
