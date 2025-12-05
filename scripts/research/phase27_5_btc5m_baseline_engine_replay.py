#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-5: Engine Replay Harness for Signal Parity Validation
==============================================================
Offline Signal Scan ↔ Engine Replay 신호 정합성 검증

목적:
- PHASE27-4 Offline Scan과 동일한 30일 데이터를 Engine으로 Replay
- TradeActivityTracker를 통해 신호 수 집계
- Offline vs Replay 신호 수 비교 (±5~10% 허용)

설계 원칙:
- 기존 run_v2() + Backtest Adapter 재사용
- 새로운 "미니 엔진" 생성 금지
- PHASE23-1 단일 엔진 구조 준수

Usage:
    python scripts/research/phase27_5_btc5m_baseline_engine_replay.py
"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("phase27_5_engine_replay")


def main():
    """
    Engine Replay 실행
    
    동작:
    1. Config 로드: configs/backtest/phase27_5_baseline_replay_30d.yml
    2. run_v2(mode='backtest') 호출
    3. TradeActivityTracker Summary JSON 생성
    """
    logger.info("=" * 80)
    logger.info("🚀 PHASE27-5: Engine Replay for Signal Parity Validation")
    logger.info("=" * 80)
    
    # Config 경로
    config_path = project_root / "configs" / "backtest" / "phase27_5_baseline_replay_30d.yml"
    
    if not config_path.exists():
        logger.error(f"❌ Config 파일 없음: {config_path}")
        return 1
    
    logger.info(f"📋 Config: {config_path}")
    
    # run_v2.py 진입점 호출
    logger.info("🔧 run_v2() 호출 (mode=backtest)")
    
    import subprocess
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_v2.py"),
        "--mode", "backtest",
        "--config", str(config_path)
    ]
    
    logger.info(f"📝 Command: {' '.join(cmd)}")
    
    # 실행
    result = subprocess.run(cmd, cwd=str(project_root))
    
    if result.returncode == 0:
        logger.info("=" * 80)
        logger.info("✅ Engine Replay 완료")
        logger.info("=" * 80)
        
        # Summary JSON 확인
        summary_file = project_root / "docs" / "PHASE27" / "phase27_5_btc5m_engine_replay_summary.json"
        if summary_file.exists():
            logger.info(f"✅ TradeActivityTracker Summary 생성: {summary_file}")
            
            # Summary 내용 간단 출력
            import json
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            
            logger.info("📊 Summary:")
            if 'strategy_signals' in summary:
                signals = summary['strategy_signals']
                logger.info(f"  - Strategy Signals (True): {signals.get('true', 0)}")
                logger.info(f"  - Strategy Signals (False): {signals.get('false', 0)}")
                logger.info(f"  - LONG: {signals.get('long', 0)}")
                logger.info(f"  - SHORT: {signals.get('short', 0)}")
            
            if 'ensemble_decisions' in summary:
                ensemble = summary['ensemble_decisions']
                logger.info(f"  - Ensemble Tier1: {ensemble.get('tier1', 0)}")
                logger.info(f"  - Ensemble Tier2: {ensemble.get('tier2', 0)}")
                logger.info(f"  - Ensemble Skip: {ensemble.get('skip', 0)}")
            
            logger.info("")
            logger.info("🔍 다음 단계: Signal Parity 테스트 실행")
            logger.info("   pytest tests/test_phase27_5_signal_parity.py")
        else:
            logger.warning(f"⚠️  TradeActivityTracker Summary 파일 없음: {summary_file}")
            logger.warning("   Config에서 trade_activity_tracker.enabled: true 확인 필요")
        
        return 0
    else:
        logger.error("❌ Engine Replay 실패")
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
