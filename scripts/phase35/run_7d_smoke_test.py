#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2: 7-Day Smoke Test Runner
===================================

AC-BT0~BT3 검증을 위한 7일 백테스트 자동 실행

Usage:
    python scripts/phase35/run_7d_smoke_test.py
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def run_backtest():
    """7일 스모크 테스트 실행"""
    print("=" * 80)
    print("PHASE35-2: 7-Day Smoke Test")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Config 경로
    config_path = project_root / "configs" / "phase35" / "ensemble_v1.yaml"
    
    if not config_path.exists():
        print(f"❌ Config not found: {config_path}")
        return 1
    
    print(f"Config: {config_path}")
    print()
    
    # run_backtest.py 실행
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_backtest.py"),
        "--config", str(config_path),
        "--start-date", "2024-12-01",
        "--end-date", "2024-12-08",
        "--initial-capital", "10000"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print()
    print("Running backtest...")
    print("-" * 80)
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=False,
            text=True
        )
        
        print("-" * 80)
        print()
        
        if result.returncode == 0:
            print("✅ Backtest completed successfully")
            return 0
        else:
            print(f"❌ Backtest failed with exit code {result.returncode}")
            return result.returncode
    
    except Exception as e:
        print(f"❌ Backtest execution error: {e}")
        return 1


def main():
    """메인 함수"""
    exit_code = run_backtest()
    
    print()
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Exit Code: {exit_code}")
    print("=" * 80)
    
    if exit_code == 0:
        print()
        print("📊 Next Steps:")
        print("1. Check results: reports/backtest/phase35/")
        print("2. Review DecisionTrace: reports/backtest/phase35/traces/")
        print("3. Verify AC-BT0~BT3 criteria")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
