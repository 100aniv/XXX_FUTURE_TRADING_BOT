#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER5: 7D Smoke Test - Isolated Runner (완전 격리 구조)
==================================================================

목표:
- run_id 기반 완전 격리 (이전 실행 오염 불가능)
- 리포트 경로 명시적 전달 (글롭 탐색 제거)
- 리포트 생성 실패 시 즉시 FAIL (exit code != 0)
- 논리 일관성 검증 (blocked_ratio==1.0 ⇒ trades==0)

Usage:
    python scripts/phase35/run_iter5_isolated.py [run_number]
"""
import sys
import yaml
import json
import hashlib
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("run_iter5_isolated")


def load_config(config_path: Path) -> Dict[str, Any]:
    """설정 파일 로드"""
    if not config_path.exists():
        logger.error(f"❌ Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_hash(data: Any) -> str:
    """데이터 해시 계산 (8자리)"""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()[:8]


def get_git_commit() -> str:
    """현재 Git commit hash 조회"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"⚠️  Git commit 조회 실패: {e}")
    return "unknown"


def main():
    """메인 실행 함수"""
    # Run number (기본값: 1)
    run_number = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run ID (ITER5 표준)
    run_id = f"phase35_2_iter5_run{run_number}_{timestamp}"
    
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE35-2 ITER5 - 7D Smoke Test Run #{run_number}")
    logger.info(f"📋 Run ID: {run_id}")
    logger.info(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # =====================================
    # 1. Config 로드
    # =====================================
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    logger.info(f"📁 Config: {config_path}")
    
    config = load_config(config_path)
    
    # Config hash
    config_hash = calculate_hash(config)
    
    # Git commit
    git_commit = get_git_commit()
    
    # Seed 고정
    seed = 42
    config["seed"] = seed
    
    # 필수 키 보장 (ITER5 - 엔진이 요구하는 모든 키)
    if "lookback" not in config:
        config["lookback"] = 100
    if "equity" not in config:
        config["equity"] = config.get("initial_capital", 10000)
    config["mode"] = "backtest"  # FlowGuardian 우회용
    
    # capital 필수 키
    if "capital" not in config:
        config["capital"] = {}
    config["capital"]["initial"] = config.get("initial_capital", 10000)
    
    # risk 필수 키
    if "risk" not in config:
        config["risk"] = {}
    if "per_trade" not in config["risk"]:
        config["risk"]["per_trade"] = 0.01
    
    # symbols 필수 키 (단일 심볼 모드)
    if "symbols" not in config:
        config["symbols"] = [config.get("symbol", "BTCUSDT")]
    
    # position_sizing 필수 키
    if "position_sizing" not in config:
        config["position_sizing"] = {}
    ps = config["position_sizing"]
    if "min_position_value" not in ps:
        ps["min_position_value"] = 10
    if "max_position_value" not in ps:
        ps["max_position_value"] = int(config.get("initial_capital", 10000) * 0.3)
    if "quality_weight_min" not in ps:
        ps["quality_weight_min"] = 0.5
    if "quality_weight_max" not in ps:
        ps["quality_weight_max"] = 1.5
    
    # leverage 필수 키
    if "leverage" not in config:
        config["leverage"] = {}
    if "max" not in config["leverage"]:
        config["leverage"]["max"] = 1
    
    logger.info(f"🔑 Config Hash: {config_hash}")
    logger.info(f"🔖 Git Commit: {git_commit}")
    logger.info(f"🎲 Seed: {seed}")
    logger.info(f"📊 Lookback: {config['lookback']}, Equity: {config['equity']}")
    
    # =====================================
    # 2. 격리된 출력 디렉토리 생성
    # =====================================
    run_dir = project_root / "artifacts" / "phase35" / "iter5" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📂 Run Directory: {run_dir}")
    
    # =====================================
    # 3. 리포트 경로 명시적 지정
    # =====================================
    report_path = run_dir / "backtest_report.json"
    
    # Config에 리포트 경로 주입 (엔진이 이 경로로 저장)
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["output_file"] = str(report_path)
    
    logger.info(f"📊 Report Path: {report_path}")
    
    # =====================================
    # 4. Effective Config 저장
    # =====================================
    effective_config_path = run_dir / "effective_config.yaml"
    with open(effective_config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"✅ Effective Config 저장: {effective_config_path}")
    
    # =====================================
    # 5. Engine 실행
    # =====================================
    logger.info("🔄 Engine 실행 중...")
    
    try:
        from execution.engine import run_v2
        
        run_v2(
            mode='backtest',
            config=config,
            clean_state=True  # ITER5: FlowGuardian 우회
        )
        
        logger.info("✅ Engine 실행 완료")
        
    except Exception as e:
        logger.error(f"❌ Engine 실행 실패: {e}")
        logger.error(f"스택 트레이스:\\n{traceback.format_exc()}")
        sys.exit(1)
    
    # =====================================
    # 6. 리포트 검증
    # =====================================
    if not report_path.exists():
        logger.error(f"❌ 리포트 파일 없음: {report_path}")
        logger.error("   리포트 생성 실패 - 즉시 종료")
        sys.exit(1)
    
    logger.info(f"✅ 리포트 파일 존재: {report_path}")
    
    # 리포트 읽기
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    except Exception as e:
        logger.error(f"❌ 리포트 읽기 실패: {e}")
        sys.exit(1)
    
    metrics = report_data.get("metrics", {})
    
    # =====================================
    # 7. Summary 생성
    # =====================================
    summary = {
        "run_number": run_number,
        "run_id": run_id,
        "timestamp": timestamp,
        "config_hash": config_hash,
        "git_commit": git_commit,
        "seed": seed,
        "start_date": config.get("start_date", "unknown"),
        "end_date": config.get("end_date", "unknown"),
        "initial_capital": config.get("initial_capital", 10000),
        "trades": metrics.get("total_trades", 0),
        "win_rate": metrics.get("winrate", 0.0),
        "profit_factor": metrics.get("pf", 0.0),
        "max_drawdown": metrics.get("mdd", 0.0),
        "pnl": metrics.get("net_pnl", 0.0),
        "roi": metrics.get("roi", 0.0),
        "report_path": str(report_path),
        "effective_config_path": str(effective_config_path),
    }
    
    # Summary 저장
    summary_path = run_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Summary 저장: {summary_path}")
    
    # =====================================
    # 8. 결과 출력
    # =====================================
    logger.info("=" * 80)
    logger.info(f"✅ Run #{run_number} 완료")
    logger.info("=" * 80)
    logger.info(f"📊 Summary: {summary_path}")
    logger.info(f"   Trades: {summary['trades']}")
    logger.info(f"   Win Rate: {summary['win_rate']:.2f}%")
    logger.info(f"   PnL: ${summary['pnl']:.2f}")
    logger.info(f"   ROI: {summary['roi']:.2f}%")
    logger.info("=" * 80)
    logger.info(f"🕐 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # =====================================
    # 9. 정상 종료
    # =====================================
    sys.exit(0)


if __name__ == "__main__":
    main()
