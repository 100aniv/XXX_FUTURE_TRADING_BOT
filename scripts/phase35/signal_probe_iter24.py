#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER24: SignalProbe - 오프라인 신호 생성 검증

목적:
- 엔진과 분리하여 전략의 신호 생성 능력을 직접 검증
- sub-model별 LONG/SHORT/FLAT 분포 확인
- ensemble no_consensus 비율 확인

SSOT:
- candles 로딩: ITER23 runner와 동일한 방식 재사용
- 전략 인스턴스: phase35_ensemble_v1.Phase35EnsembleV1 직접 생성
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.logger import setup_logger
from strategies.phase35_ensemble_v1 import Phase35EnsembleV1

logger = setup_logger("signal_probe")


def load_candles(symbol: str, timeframe: str, days: int = 7) -> pd.DataFrame:
    """
    SSOT: ITER23 runner와 동일한 방식으로 candles 로딩
    
    Args:
        symbol: 심볼 (예: BTCUSDT)
        timeframe: 타임프레임 (예: 15m)
        days: 최근 N일
    
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    from collectors.historical_collector import HistoricalFeed
    
    data_dir = PROJECT_ROOT / "data"
    
    # CSV 파일 경로 탐색 (여러 패턴 시도)
    csv_patterns = [
        data_dir / f"{symbol}_{timeframe}.csv",
        data_dir / f"{symbol}_{timeframe}_2024-01-01_2024-12-31.csv",
        data_dir / f"{symbol}_{timeframe}_2024-01-01_2024-09-30_TRAIN.csv",
    ]
    
    csv_path = None
    for path in csv_patterns:
        if path.exists():
            csv_path = path
            break
    
    if csv_path is None:
        raise FileNotFoundError(
            f"CSV file not found for {symbol}_{timeframe}. Tried: {[str(p) for p in csv_patterns]}"
        )
    
    feed = HistoricalFeed(
        csv_path=str(csv_path),
        symbol=symbol,
        timeframe=timeframe,
        days=days
    )
    
    df = feed.df.copy()
    
    logger.info(f"📊 Loaded {len(df)} candles from {csv_path} (last {days} days)")
    return df


def probe_strategy_signals(
    config: dict,
    df: pd.DataFrame,
    candidate_id: str,
    output_dir: Path
) -> Dict[str, Any]:
    """
    전략의 신호 생성 능력을 오프라인으로 검증
    
    Args:
        config: 전략 config (sub_models, ensemble 등 포함)
        df: candles DataFrame
        candidate_id: 후보 ID (예: L4_ultra_debug)
        output_dir: 결과 저장 디렉토리
    
    Returns:
        {
            'candidate_id': str,
            'total_bars': int,
            'signal_counts': {'LONG': int, 'SHORT': int, 'FLAT': int},
            'sub_model_stats': {...},
            'ensemble_stats': {...},
            'diagnostics': {...}
        }
    """
    logger.info(f"🔍 [SignalProbe] {candidate_id} - Starting probe on {len(df)} bars")
    
    # 전략 인스턴스 생성
    strategy = Phase35EnsembleV1(config)
    
    signal_counts = {"LONG": 0, "SHORT": 0, "FLAT": 0}
    sub_model_votes_list = []
    
    # 바 단위로 신호 생성
    for i in range(50, len(df)):  # 최소 50 bars for indicators
        df_slice = df.iloc[:i+1].copy()
        
        try:
            signal = strategy.compute_signal(df_slice)
            side = signal.get("side")
            
            if side == "LONG":
                signal_counts["LONG"] += 1
            elif side == "SHORT":
                signal_counts["SHORT"] += 1
            else:
                signal_counts["FLAT"] += 1
            
            # sub_model votes 수집
            if "sub_model_votes" in signal:
                sub_model_votes_list.append(signal["sub_model_votes"])
        
        except Exception as e:
            logger.error(f"❌ Signal computation failed at bar {i}: {e}")
            signal_counts["FLAT"] += 1
    
    # Sub-model 통계
    sub_model_stats = _analyze_sub_model_votes(sub_model_votes_list)
    
    # Ensemble 통계
    ensemble_stats = {
        "total_evaluated": len(df) - 50,
        "signal_distribution": signal_counts,
        "signal_rate": {
            "LONG": signal_counts["LONG"] / (len(df) - 50) if len(df) > 50 else 0,
            "SHORT": signal_counts["SHORT"] / (len(df) - 50) if len(df) > 50 else 0,
            "FLAT": signal_counts["FLAT"] / (len(df) - 50) if len(df) > 50 else 0,
        }
    }
    
    # 전략 diagnostics
    diag = strategy.get_diagnostics() if hasattr(strategy, "get_diagnostics") else {}
    
    result = {
        "candidate_id": candidate_id,
        "total_bars": len(df),
        "evaluated_bars": len(df) - 50,
        "signal_counts": signal_counts,
        "sub_model_stats": sub_model_stats,
        "ensemble_stats": ensemble_stats,
        "diagnostics": diag,
    }
    
    # 결과 저장
    output_path = output_dir / f"signal_probe_{candidate_id}.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(f"✅ SignalProbe result saved: {output_path}")
    
    # AC 체크
    total_signals = signal_counts["LONG"] + signal_counts["SHORT"]
    if total_signals == 0:
        logger.error(f"❌ AC1 FAIL: {candidate_id} - LONG+SHORT = 0 (전략이 신호를 생성하지 못함)")
        logger.error(f"   Top DIAG reasons: {_get_top_diag_reasons(diag, top_n=5)}")
    else:
        logger.info(f"✅ AC1 PASS: {candidate_id} - LONG+SHORT = {total_signals}")
    
    return result


def _analyze_sub_model_votes(votes_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sub-model별 투표 분포 분석
    
    Returns:
        {
            'trend': {'LONG': int, 'SHORT': int, 'FLAT': int, 'reasons': {...}},
            'reversion': {...},
            'breakout': {...}
        }
    """
    stats = {
        "trend": {"LONG": 0, "SHORT": 0, "FLAT": 0, "reasons": {}},
        "reversion": {"LONG": 0, "SHORT": 0, "FLAT": 0, "reasons": {}},
        "breakout": {"LONG": 0, "SHORT": 0, "FLAT": 0, "reasons": {}},
    }
    
    for votes in votes_list:
        for model_name, vote in votes.items():
            if model_name not in stats:
                continue
            
            direction = vote.get("direction")
            if direction == "LONG":
                stats[model_name]["LONG"] += 1
            elif direction == "SHORT":
                stats[model_name]["SHORT"] += 1
            else:
                stats[model_name]["FLAT"] += 1
            
            # FLAT reasons 수집
            if direction is None:
                reasons = vote.get("reasons", [])
                for reason in reasons:
                    stats[model_name]["reasons"][reason] = stats[model_name]["reasons"].get(reason, 0) + 1
    
    return stats


def _get_top_diag_reasons(diag: Dict[str, Any], top_n: int = 5) -> List[tuple]:
    """
    Diagnostics에서 상위 N개 이유 추출
    
    Returns:
        [(reason, count), ...]
    """
    if not diag or "counters" not in diag:
        return []
    
    counters = diag.get("counters", {})
    sorted_reasons = sorted(counters.items(), key=lambda x: x[1], reverse=True)
    return sorted_reasons[:top_n]


def main():
    """
    Main entry point
    
    Usage:
        python scripts/phase35/signal_probe_iter24.py
    """
    from scripts.phase35.run_iter24_signal_diag_ultra_debug import (
        load_base_config,
        RELAXATION_LEVELS,
    )
    
    ARTIFACTS_DIR = PROJECT_ROOT / "artifacts" / "phase35" / "iter24"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Base config 로드
    base_config = load_base_config()
    
    # Candles 로드 (7일)
    df = load_candles(
        symbol=base_config.get("symbol", "BTCUSDT"),
        timeframe=base_config.get("timeframe", "15m"),
        days=7
    )
    
    # 각 후보에 대해 SignalProbe 실행
    candidates = ["L0_baseline", "L3_aggressive", "L4_ultra_debug"]
    
    for candidate_id in candidates:
        logger.info(f"\n{'='*80}")
        logger.info(f"SignalProbe: {candidate_id}")
        logger.info(f"{'='*80}")
        
        # Config override
        config = base_config.copy()
        relaxation = RELAXATION_LEVELS.get(candidate_id, {})
        
        if "sub_models" not in config:
            config["sub_models"] = {}
        
        for sub_model, params in relaxation.items():
            if sub_model in ["trend", "reversion", "breakout"]:
                if sub_model not in config["sub_models"]:
                    config["sub_models"][sub_model] = {}
                config["sub_models"][sub_model].update(params)
            elif sub_model == "regime_filter":
                config["regime_filter"] = config.get("regime_filter", {})
                config["regime_filter"].update(params)
            elif sub_model == "ensemble":
                config["ensemble"] = config.get("ensemble", {})
                config["ensemble"].update(params)
        
        # DecisionTrace 활성화
        config["decision_trace"] = {"enabled": True}
        
        # Probe 실행
        result = probe_strategy_signals(
            config=config,
            df=df,
            candidate_id=candidate_id,
            output_dir=ARTIFACTS_DIR
        )
        
        logger.info(f"📊 {candidate_id} Summary:")
        logger.info(f"   LONG: {result['signal_counts']['LONG']}")
        logger.info(f"   SHORT: {result['signal_counts']['SHORT']}")
        logger.info(f"   FLAT: {result['signal_counts']['FLAT']}")
    
    logger.info("\n✅ SignalProbe completed for all candidates")


if __name__ == "__main__":
    main()
