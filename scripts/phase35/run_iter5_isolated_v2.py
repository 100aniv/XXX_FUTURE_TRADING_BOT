#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER5.5: 7D Smoke Test - Isolated Runner (Config Preflight 통합)
===========================================================================

목표:
- Config Preflight: 필수 키 "한 번에" 검증, 누락 시 전체 리스트 출력 후 종료
- run_id 기반 완전 격리
- 리포트 경로 명시적 전달
- Effective Config 2중 검증

Usage:
    python scripts/phase35/run_iter5_isolated_v2.py [run_number]
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
from common.config_preflight import (
    compute_file_fingerprint,
    assert_required,
    print_fingerprint,
    reset_usage_tracker,
    get_usage_report,
    print_usage_report
)
from common.config_required import REQUIRED_DOTPATHS

logger = setup_logger("run_iter5_isolated")


def load_config(config_path: Path) -> Dict[str, Any]:
    """설정 파일 로드 + Fingerprint 출력"""
    if not config_path.exists():
        logger.error(f"❌ Config not found: {config_path}")
        sys.exit(1)
    
    # Fingerprint 계산 및 출력
    fingerprint = compute_file_fingerprint(config_path)
    print_fingerprint(fingerprint, "Loaded Config")

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


def ensure_required_keys(config: Dict[str, Any]) -> None:
    """
    Config에 필수 키가 없으면 기본값으로 채움
    
    주의: backtest.output_file은 나중에 run_dir 생성 후 설정됨
    """
    # 기본 설정
    if "lookback" not in config:
        config["lookback"] = 100
    if "equity" not in config:
        config["equity"] = config.get("initial_capital", 10000)
    if "mode" not in config:
        config["mode"] = "backtest"
    
    # capital
    if "capital" not in config:
        config["capital"] = {}
    if "initial" not in config["capital"]:
        config["capital"]["initial"] = config.get("initial_capital", 10000)
    
    # risk
    if "risk" not in config:
        config["risk"] = {}
    if "per_trade" not in config["risk"]:
        config["risk"]["per_trade"] = 0.01
    if "max_positions" not in config["risk"]:
        config["risk"]["max_positions"] = 3
    if "max_exposure_per_symbol" not in config["risk"]:
        config["risk"]["max_exposure_per_symbol"] = 0.3
    
    # symbols (단일 심볼 모드)
    if "symbols" not in config:
        config["symbols"] = [config.get("symbol", "BTCUSDT")]
    
    # position_sizing
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
    
    # portfolio
    if "portfolio" not in config:
        config["portfolio"] = {}
    if "max_total_exposure" not in config["portfolio"]:
        config["portfolio"]["max_total_exposure"] = 0.95
    if "max_strategy_positions" not in config["portfolio"]:
        config["portfolio"]["max_strategy_positions"] = 3
    
    # leverage
    if "leverage" not in config:
        config["leverage"] = {}
    if "max" not in config["leverage"]:
        config["leverage"]["max"] = 1
    
    # backtest (output_file은 나중에 설정)
    if "backtest" not in config:
        config["backtest"] = {}


def apply_date_range(config: Dict[str, Any], range_override: str = None) -> None:
    """
    ITER8: 날짜 범위 적용 (YAML 존중 원칙)
    
    규칙:
    1. YAML에 start_date, end_date가 모두 있으면 절대 덮어쓰지 않음
    2. YAML에 없고 --range가 지정되면 그 범위로 설정
    3. YAML에도 없고 --range도 없으면 디폴트 7d
    """
    yaml_has_dates = "start_date" in config and "end_date" in config
    
    if yaml_has_dates:
        logger.info(f"📅 [DATE SSOT] YAML 날짜 사용: {config['start_date']} ~ {config['end_date']}")
        return
    
    # YAML에 날짜가 없으면 range_override 또는 디폴트 적용
    if range_override == '1d':
        config['start_date'] = '2024-12-01'
        config['end_date'] = '2024-12-02'
        logger.warning(f"⚠️  [DATE OVERRIDE] --range 1d 적용: {config['start_date']} ~ {config['end_date']}")
    elif range_override == '7d':
        config['start_date'] = '2024-12-01'
        config['end_date'] = '2024-12-08'
        logger.warning(f"⚠️  [DATE OVERRIDE] --range 7d 적용: {config['start_date']} ~ {config['end_date']}")
    else:
        # 디폴트: 7d
        config['start_date'] = '2024-12-01'
        config['end_date'] = '2024-12-08'
        logger.warning(f"⚠️  [DATE DEFAULT] 7d 디폴트 적용: {config['start_date']} ~ {config['end_date']}")


def main():
    """메인 실행 함수 (ITER8: --range 파라미터 지원)"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PHASE35-2 Runner')
    parser.add_argument('run_number', type=int, nargs='?', default=1, help='Run number')
    parser.add_argument('--range', type=str, choices=['1d', '7d'], default=None, help='Date range override (1d or 7d)')
    args = parser.parse_args()
    
    run_number = args.run_number
    range_override = args.range
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Run ID (ITER8)
    run_id = f"phase35_2_iter8_run{run_number}_{timestamp}"
    
    logger.info("=" * 80)
    logger.info(f"🚀 PHASE35-2 ITER8 - Risk Guard Validation Run #{run_number}")
    logger.info(f"📋 Run ID: {run_id}")
    if range_override:
        logger.info(f"📅 Range Override: {range_override}")
    logger.info(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # =====================================
    # 1. Config 로드 + Preflight 검증
    # =====================================
    # Usage tracker 초기화 (이전 실행 영향 제거)
    reset_usage_tracker()
    
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    logger.info(f"📁 Config Source: {config_path.absolute()}")
    
    config = load_config(config_path)  # Fingerprint printed inside
    
    # Config hash
    config_hash = calculate_hash(config)
    
    # =====================================
    # 1.5. Preflight: 필수 키 보장 + 검증
    # =====================================
    logger.info("🔍 Config Preflight: 필수 키 보장 중...")
    
    # 필수 키 자동 보장 (backtest.output_file 제외)
    ensure_required_keys(config)
    
    # ITER8: 날짜 범위 적용 (YAML 존중)
    apply_date_range(config, range_override)
    
    # Git commit & Seed
    git_commit = get_git_commit()
    seed = 42
    config["seed"] = seed
    
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
    config["backtest"]["output_file"] = str(report_path)
    
    logger.info(f"📊 Report Path: {report_path}")
    
    # =====================================
    # 3.5. Preflight 검증 (누락 시 즉시 종료)
    # =====================================
    logger.info("🔍 Config Preflight: 필수 키 검증 중...")
    try:
        assert_required(config, REQUIRED_DOTPATHS, context="Config Preflight")
        logger.info(f"✅ Config Preflight PASS ({len(REQUIRED_DOTPATHS)}개 필수 키 확인)")
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # =====================================
    # 4. Effective Config 저장 + 2중 검증
    # =====================================
    effective_config_path = run_dir / "effective_config.yaml"
    with open(effective_config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"✅ Effective Config 저장: {effective_config_path}")
    
    # 2중 검증: 저장된 파일을 다시 읽어서 필수 키 확인
    logger.info("🔍 Effective Config 2중 검증 중...")
    saved_fingerprint = compute_file_fingerprint(effective_config_path)
    print_fingerprint(saved_fingerprint, "Saved Effective Config")
    
    with open(effective_config_path, "r", encoding="utf-8") as f:
        saved_config = yaml.safe_load(f)
    
    try:
        assert_required(saved_config, REQUIRED_DOTPATHS, context="Effective Config 2중 검증")
        logger.info(f"✅ Effective Config 2중 검증 PASS")
    except RuntimeError as e:
        logger.error(str(e))
        logger.error("❌ Effective Config 저장 후 필수 키가 사라졌습니다!")
        sys.exit(1)
    
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
        logger.error(f"스택 트레이스:\n{traceback.format_exc()}")
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
    # 9. Config Usage Report (ITER6)
    # =====================================
    usage_report = get_usage_report(REQUIRED_DOTPATHS)
    usage_report_path = run_dir / "config_usage_report.json"
    
    with open(usage_report_path, "w", encoding="utf-8") as f:
        json.dump(usage_report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Config Usage Report 저장: {usage_report_path}")
    print_usage_report(usage_report)
    
    # =====================================
    # 10. 정상 종료
    # =====================================
    sys.exit(0)


if __name__ == "__main__":
    main()
