#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER3: 7D Smoke Test SSOT Runner (Run1/Run2)
=======================================================

phase35_2_iter3_ssot.yaml를 사용한 7D Smoke Test 실행
- Run1: 초기 실행
- Run2: 재현성 검증
- Summary JSON 생성 (AC-2/AC-3 판정용)

Usage:
    python scripts/phase35/run_7d_ssot.py [run_number]
"""
import sys
import yaml
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("run_7d_ssot")


def load_config(config_path: Path) -> Dict[str, Any]:
    """설정 파일 로드"""
    if not config_path.exists():
        logger.error(f"❌ Config not found: {config_path}")
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_merge(base: Dict, custom: Dict) -> Dict:
    """Deep merge 함수"""
    merged = base.copy()
    for key, value in custom.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def get_git_commit() -> str:
    """현재 git commit hash 가져오기"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )
        return result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def compute_config_hash(config: Dict[str, Any]) -> str:
    """Config의 hash 계산 (재현성 검증용)"""
    # 중요 파라미터만 선택
    key_params = {
        "ensemble": config.get("ensemble", {}),
        "sub_models": config.get("sub_models", {}),
        "regime": config.get("regime", {}),
        "exit": config.get("exit", {}),
        "risk": config.get("risk", {}),
        "fees": config.get("fees", {}),
        "start_date": config.get("start_date"),
        "end_date": config.get("end_date"),
    }
    config_str = json.dumps(key_params, sort_keys=True)
    return hashlib.md5(config_str.encode("utf-8")).hexdigest()[:8]


def run_backtest(run_number: int = 1) -> int:
    """7D Smoke Test 실행"""
    logger.info("=" * 80)
    logger.info(f"PHASE35-2 ITER3: 7D Smoke Test - Run #{run_number}")
    logger.info("=" * 80)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Config 로드 (ITER3 SSOT만 사용, base.yml 제외)
        ssot_config_path = (
            project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
        )

        logger.info(f"📂 Loading ITER3 SSOT config (no base.yml): {ssot_config_path}")
        if not ssot_config_path.exists():
            logger.error(f"❌ SSOT Config not found: {ssot_config_path}")
            return 1

        with open(ssot_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Run ID 생성 (run_number 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"phase35_2_iter3_run{run_number}_{timestamp}"
        config["run_id"] = run_id
        config["mode"] = "backtest"
        config["env"] = "backtest"

        # Seed 고정 (재현성)
        import random
        import numpy as np

        seed = 42
        random.seed(seed)
        np.random.seed(seed)

        # Backtest 설정 (7D 강제)
        config["start_date"] = "2024-12-01"
        config["end_date"] = "2024-12-08"
        config["initial_capital"] = 10000
        config["symbol"] = "BTCUSDT"
        config["timeframe"] = "15m"

        # 데이터 파일 명시적 지정
        data_file = project_root / "data" / "BTCUSDT_15m_2024-01-01_2024-12-31.csv"
        if data_file.exists():
            config["data_file"] = str(data_file)
            logger.info(f"📁 Data file: {data_file}")
        else:
            logger.error(f"❌ Data file not found: {data_file}")
            return 1

        # Config hash & git commit
        config_hash = compute_config_hash(config)
        git_commit = get_git_commit()

        logger.info("✅ Config 로딩 완료")
        logger.info(f"🆔 Run ID: {run_id}")
        logger.info(f"📅 Period: {config['start_date']} ~ {config['end_date']}")
        logger.info(f"💰 Capital: ${config['initial_capital']}")
        logger.info(
            f"🎯 Strategy: {config.get('strategy', {}).get('selector', 'unknown')}"
        )
        logger.info(f"🔐 Config Hash: {config_hash}")
        logger.info(f"📦 Git Commit: {git_commit}")
        logger.info(f"🎲 Seed: {seed}")

    except Exception as e:
        logger.error(f"❌ Config 로딩 실패: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1

    # Engine 실행
    from execution.engine import run_v2

    try:
        logger.info("🔄 Engine 실행 중...")
        run_v2(
            mode='backtest',
            config=config,
            clean_state=False
        )  # Summary 생성
        summary_dir = project_root / "reports" / "backtest" / "phase35"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summary_dir / f"iter3_run{run_number}_summary.json"

        # 백테스트 결과 파일 찾기
        report_files = sorted((project_root / "reports" / "backtest").glob("*.json"))
        latest_report = report_files[-1] if report_files else None

        summary = {
            "run_number": run_number,
            "run_id": run_id,
            "timestamp": timestamp,
            "config_hash": config_hash,
            "git_commit": git_commit,
            "seed": seed,
            "start_date": config["start_date"],
            "end_date": config["end_date"],
            "initial_capital": config["initial_capital"],
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "pnl": 0.0,
            "roi": 0.0,
        }

        # 결과 추출
        if latest_report and latest_report.exists():
            try:
                with open(latest_report, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                metrics = report_data.get("metrics", {})
                summary.update(
                    {
                        "trades": metrics.get("total_trades", 0),
                        "win_rate": metrics.get("winrate", 0.0),
                        "profit_factor": metrics.get("pf", 0.0),
                        "max_drawdown": metrics.get("mdd", 0.0),
                        "pnl": metrics.get("net_pnl", 0.0),
                        "roi": metrics.get("roi", 0.0),
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️  메트릭 추출 실패: {e}")

        # Summary 저장
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info("=" * 80)
        logger.info(f"✅ Run #{run_number} 완료")
        logger.info(f"📊 Summary: {summary_path}")
        logger.info(f"   Trades: {summary['trades']}")
        logger.info(f"   Win Rate: {summary['win_rate']:.2f}%")
        logger.info(f"   PnL: ${summary['pnl']:.2f}")
        logger.info("=" * 80)
        return 0

    except KeyboardInterrupt:
        logger.warning("⚠️  사용자 중단")
        return 130
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


def extract_metrics(report_file: Path) -> Dict[str, Any]:
    """백테스트 결과에서 메트릭 추출"""
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        metrics = data.get("metrics", {})
        return {
            "trades": metrics.get("total_trades", 0),
            "win_rate": metrics.get("winrate", 0),
            "profit_factor": metrics.get("pf", 0),
            "max_drawdown": metrics.get("mdd", 0),
            "roi": metrics.get("roi", 0),
        }
    except Exception as e:
        logger.warning(f"⚠️  메트릭 추출 실패: {e}")
        return {}


def check_reproducibility(run1_metrics: Dict, run2_metrics: Dict) -> bool:
    """재현성 검증 (허용오차 범위 내)"""
    logger.info("=" * 80)
    logger.info("재현성 검증 (Run1 vs Run2)")
    logger.info("=" * 80)

    tolerances = {
        "trades": 0.10,  # ±10%
        "win_rate": 1.5,  # ±1.5%p
        "profit_factor": 0.05,  # ±0.05
        "max_drawdown": 1.0,  # ±1.0%p
    }

    all_pass = True

    for key, tolerance in tolerances.items():
        r1 = run1_metrics.get(key, 0)
        r2 = run2_metrics.get(key, 0)

        if key == "trades":
            # 상대 오차
            if r1 > 0:
                error = abs(r2 - r1) / r1
                status = "✅ PASS" if error <= tolerance else "❌ FAIL"
                logger.info(
                    f"{key:20s}: Run1={r1:8.0f}, Run2={r2:8.0f}, Error={error*100:5.1f}% {status}"
                )
                if error > tolerance:
                    all_pass = False
        else:
            # 절대 오차
            error = abs(r2 - r1)
            status = "✅ PASS" if error <= tolerance else "❌ FAIL"
            logger.info(
                f"{key:20s}: Run1={r1:8.2f}, Run2={r2:8.2f}, Error={error:5.2f} {status}"
            )
            if error > tolerance:
                all_pass = False

    logger.info("=" * 80)
    return all_pass


def main():
    """메인 함수"""
    # CLI 인자에서 run_number 가져오기
    run_number = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    exit_code = run_backtest(run_number)

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Exit Code: {exit_code}")
    logger.info("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
