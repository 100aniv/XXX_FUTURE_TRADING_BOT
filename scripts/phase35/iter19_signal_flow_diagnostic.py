#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER19: Engine 신호 흐름 진단
================================================================================

목표: Phase35EnsembleV1의 compute_signal이 실제로 호출되고 
      그 결과가 engine에서 어떻게 처리되는지 확인

진단 항목:
1. compute_signal 호출 횟수
2. side가 None인 비율 vs LONG/SHORT 비율
3. side가 있을 때 engine이 실제로 거래를 생성하는지
4. ensemble voting 결과 분포 (NO_CONSENSUS, REGIME_CHOP 등)
"""
import sys
import os
import json
import yaml
import copy
from datetime import datetime
from pathlib import Path
from collections import Counter

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
logger = setup_logger(__name__, log_type="application")

# =====================================
# 진단용 Config
# =====================================
BASE_CONFIG_PATH = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
ARTIFACTS_DIR = project_root / "artifacts" / "phase35" / "iter19_diagnostic"

# 짧은 기간 (3일)
DIAGNOSTIC_WINDOW = ("2024-11-01", "2024-11-03")


def load_base_config() -> dict:
    """Base Config 로드"""
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_diagnostic_backtest():
    """진단용 백테스트 실행"""
    from common.config_preflight import reset_usage_tracker
    from execution.engine import run_v2
    
    reset_usage_tracker()
    
    config = load_base_config()
    config["start_date"] = DIAGNOSTIC_WINDOW[0]
    config["end_date"] = DIAGNOSTIC_WINDOW[1]
    
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["start_date"] = DIAGNOSTIC_WINDOW[0]
    config["backtest"]["end_date"] = DIAGNOSTIC_WINDOW[1]
    
    # Output 경로
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARTIFACTS_DIR / "diagnostic_report.json"
    config["backtest"]["output_file"] = str(report_path)
    
    # 진단 모드 활성화
    config["decision_trace"] = True
    
    logger.info("=" * 78)
    logger.info("🔬 ITER19: Engine 신호 흐름 진단")
    logger.info("=" * 78)
    logger.info(f"📅 Window: {DIAGNOSTIC_WINDOW[0]} ~ {DIAGNOSTIC_WINDOW[1]}")
    logger.info(f"📂 Config: {BASE_CONFIG_PATH}")
    
    # 전략 확인
    strategy_selector = config.get("strategy", {}).get("selector", "scalping")
    logger.info(f"🎯 Strategy Selector: {strategy_selector}")
    
    # Ensemble 파라미터 확인
    ensemble_cfg = config.get("ensemble", {})
    logger.info(f"🔧 Ensemble Config:")
    logger.info(f"   - min_votes: {ensemble_cfg.get('min_votes', 2)}")
    logger.info(f"   - confidence_threshold: {ensemble_cfg.get('confidence_threshold', 0.7)}")
    logger.info(f"   - cooldown_bars: {ensemble_cfg.get('cooldown_bars', 3)}")
    
    # Engine 실행 (ITER19 FIX: clean_state=True)
    logger.info("\n🚀 백테스트 실행 중 (clean_state=True)...")
    run_v2(mode="backtest", config=config, clean_state=True)
    
    # 결과 로드
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        
        metrics = report.get("metrics", {})
        logger.info("\n" + "=" * 78)
        logger.info("📊 백테스트 결과")
        logger.info("=" * 78)
        logger.info(f"   Total Trades: {metrics.get('total_trades', 0)}")
        logger.info(f"   Win Rate: {metrics.get('winrate', 0):.2f}%")
        logger.info(f"   Profit Factor: {metrics.get('pf', 0):.4f}")
        logger.info(f"   PnL: ${metrics.get('pnl', 0):.2f}")
        
        return report
    else:
        logger.error(f"❌ Report not found: {report_path}")
        return None


def analyze_strategy_diagnostics():
    """Phase35EnsembleV1의 진단 카운터 분석"""
    logger.info("\n" + "=" * 78)
    logger.info("🔍 전략 진단 카운터 분석")
    logger.info("=" * 78)
    
    # Phase35EnsembleV1에서 직접 카운터 추출
    try:
        from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
        
        # 전략 인스턴스 생성하여 진단 활성화 상태 확인
        config = load_base_config()
        config["decision_trace"] = True
        
        strategy = Phase35EnsembleV1(config)
        logger.info(f"   _diag_enabled: {strategy._diag_enabled}")
        logger.info(f"   _diag_counters: {strategy._diag_counters}")
        logger.info(f"   _total_signals_checked: {strategy._total_signals_checked}")
        
    except Exception as e:
        logger.error(f"❌ 전략 진단 실패: {e}")


def run_manual_signal_test():
    """수동 신호 테스트: 백테스트 실행 후 report 분석"""
    logger.info("\n" + "=" * 78)
    logger.info("🧪 백테스트 실행 및 신호 흐름 분석")
    logger.info("=" * 78)
    
    from common.config_preflight import reset_usage_tracker
    from execution.engine import run_v2
    from strategies.phase35_ensemble_v1 import Phase35EnsembleV1
    
    reset_usage_tracker()
    
    # Config 로드
    config = load_base_config()
    config["decision_trace"] = True
    config["start_date"] = DIAGNOSTIC_WINDOW[0]
    config["end_date"] = DIAGNOSTIC_WINDOW[1]
    
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["start_date"] = DIAGNOSTIC_WINDOW[0]
    config["backtest"]["end_date"] = DIAGNOSTIC_WINDOW[1]
    
    # Output 경로
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ARTIFACTS_DIR / "diagnostic_report.json"
    config["backtest"]["output_file"] = str(report_path)
    
    # 전략 파라미터 확인
    strategy = Phase35EnsembleV1(config)
    logger.info(f"   min_votes: {strategy._min_votes}")
    logger.info(f"   confidence_threshold: {strategy._confidence_threshold}")
    logger.info(f"   cooldown_bars: {strategy._cooldown_bars}")
    logger.info(f"   effective_params: {strategy.get_effective_params()}")
    
    # Engine 실행 (ITER19 FIX: clean_state=True)
    logger.info("\n🚀 백테스트 실행 중 (clean_state=True)...")
    run_v2(mode="backtest", config=config, clean_state=True)
    
    # 결과 로드
    signal_results = {
        "total_calls": 0,
        "side_none": 0,
        "side_long": 0,
        "side_short": 0,
        "reasons": Counter(),
    }
    
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        
        metrics = report.get("metrics", {})
        trades = report.get("trades", [])
        
        logger.info("\n📊 백테스트 결과:")
        logger.info(f"   Total Trades: {metrics.get('total_trades', 0)}")
        logger.info(f"   Win Rate: {metrics.get('winrate', 0):.2f}%")
        logger.info(f"   Profit Factor: {metrics.get('pf', 0):.4f}")
        logger.info(f"   PnL: ${metrics.get('pnl', 0):.2f}")
        
        # Trades 분석
        if trades:
            long_count = sum(1 for t in trades if t.get("side") == "LONG")
            short_count = sum(1 for t in trades if t.get("side") == "SHORT")
            logger.info(f"   LONG trades: {long_count}")
            logger.info(f"   SHORT trades: {short_count}")
            
            # 전략별 분석
            strategy_counts = Counter(t.get("strategy_id", "unknown") for t in trades)
            logger.info("\n📊 전략별 거래 분포:")
            for strat, count in strategy_counts.most_common():
                logger.info(f"   - {strat}: {count}")
        
        signal_results["total_calls"] = metrics.get("total_trades", 0)
        signal_results["side_long"] = long_count if trades else 0
        signal_results["side_short"] = short_count if trades else 0
    else:
        logger.error(f"❌ Report not found: {report_path}")
    
    # 결과 저장
    results_path = ARTIFACTS_DIR / "signal_flow_diagnostic.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "window": DIAGNOSTIC_WINDOW,
            "signal_results": {
                "total_calls": signal_results["total_calls"],
                "side_none": signal_results["side_none"],
                "side_long": signal_results["side_long"],
                "side_short": signal_results["side_short"],
            },
            "reasons": dict(signal_results["reasons"]),
            "effective_params": strategy.get_effective_params(),
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n📂 결과 저장: {results_path}")
    
    return signal_results


def main():
    """메인 진단 함수"""
    logger.info("=" * 78)
    logger.info("🚀 PHASE35-4 ITER19: Engine 신호 흐름 진단 시작")
    logger.info("=" * 78)
    
    # 1. 수동 신호 테스트 (compute_signal 직접 호출)
    signal_results = run_manual_signal_test()
    
    # 2. 결론 출력
    logger.info("\n" + "=" * 78)
    logger.info("📝 진단 결론")
    logger.info("=" * 78)
    
    if signal_results:
        total = signal_results["total_calls"]
        none_pct = signal_results["side_none"] / max(total, 1) * 100
        signal_pct = (signal_results["side_long"] + signal_results["side_short"]) / max(total, 1) * 100
        
        if none_pct > 95:
            logger.warning("⚠️ 거의 모든 호출에서 side=None 반환 (95%+)")
            logger.warning("   → ensemble voting이 NO_CONSENSUS 또는 REGIME_CHOP 상태")
            logger.warning("   → 파라미터 변경이 영향 없음 (신호 자체가 없음)")
        elif signal_pct > 5:
            logger.info(f"✅ {signal_pct:.1f}% 호출에서 LONG/SHORT 신호 생성")
            logger.info("   → ensemble voting이 작동 중")
            logger.info("   → 파라미터 변경이 영향을 미쳐야 함")
            logger.warning("   → 그러나 실제 거래 수가 변하지 않음 = Engine 문제 가능성")
    
    logger.info("\n✅ 진단 완료")


if __name__ == "__main__":
    main()
