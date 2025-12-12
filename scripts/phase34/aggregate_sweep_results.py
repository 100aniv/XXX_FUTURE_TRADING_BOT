#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-1: Sweep Results Aggregator
====================================
배치 실행 결과를 집계하고 Pareto 분석

Usage:
    python scripts/phase34/aggregate_sweep_results.py
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("aggregate_sweep")

# 경로
META_PATH = project_root / "configs" / "backtest" / "phase34_sweep" / "sweep_meta.json"
MANIFEST_PATH = project_root / "reports" / "backtest" / "phase34" / "sweep" / "batch_manifest.json"
REPORTS_DIR = project_root / "reports" / "backtest" / "phase34" / "sweep"
OUTPUT_CSV = REPORTS_DIR / "sweep_results.csv"
OUTPUT_JSON = REPORTS_DIR / "sweep_results.json"
PARETO_CSV = REPORTS_DIR / "pareto_frontier.csv"


def load_manifest() -> dict:
    """배치 매니페스트 로드"""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_summary(summary_path: Path) -> Dict[str, Any]:
    """개별 summary 로드"""
    if not summary_path.exists():
        return None
    
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {summary_path.name}: {e}")
        return None


def extract_metrics(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Summary에서 핵심 메트릭 추출"""
    if not summary:
        return {
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "total_pnl": 0.0,
            "final_equity": 0.0,
            "blocked_rate": 100.0,
            "low_confidence_ratio": 100.0,
            "exceptions": 999
        }
    
    # 기본 메트릭
    metrics = {
        "trades": summary.get("total_trades", 0),
        "win_rate": summary.get("win_rate", 0.0),
        "profit_factor": summary.get("profit_factor", 0.0),
        "max_drawdown": summary.get("max_drawdown_pct", 0.0),
        "total_pnl": summary.get("total_pnl", 0.0),
        "final_equity": summary.get("final_equity", 0.0),
        "exceptions": 0  # 기본값
    }
    
    # DecisionTrace에서 차단율 계산
    decision_trace = summary.get("decision_trace", {})
    if decision_trace:
        for strategy, trace in decision_trace.items():
            total_checks = trace.get("total_checks", 0)
            total_blocks = trace.get("total_blocks", 0)
            
            if total_checks > 0:
                metrics["blocked_rate"] = (total_blocks / total_checks) * 100
            else:
                metrics["blocked_rate"] = 100.0
            
            # low_confidence 비율
            block_reasons = trace.get("block_reasons", {})
            low_conf_count = sum(
                count for reason, count in block_reasons.items()
                if "low_confidence" in reason
            )
            
            if total_blocks > 0:
                metrics["low_confidence_ratio"] = (low_conf_count / total_blocks) * 100
            else:
                metrics["low_confidence_ratio"] = 0.0
            
            break  # 첫 번째 전략만 (단일 전략)
    else:
        metrics["blocked_rate"] = 100.0
        metrics["low_confidence_ratio"] = 100.0
    
    # Strategy call counters에서 예외 확인
    call_counters = summary.get("strategy_call_counters", {})
    if call_counters:
        for strategy, counters in call_counters.items():
            metrics["exceptions"] = counters.get("exceptions", 0)
            break
    
    return metrics


def aggregate_results() -> pd.DataFrame:
    """전체 결과 집계"""
    logger.info("=" * 80)
    logger.info("PHASE34-1: Aggregating Sweep Results")
    logger.info("=" * 80)
    
    # 메타 및 매니페스트 로드
    meta = load_manifest()
    results = meta.get("results", [])
    
    logger.info(f"📋 Total experiments: {len(results)}")
    
    # 데이터 수집
    rows = []
    
    for result in results:
        exp_id = result["id"]
        params = result["params"]
        
        # Summary 로드
        summary_file = project_root / "reports" / "backtest" / "phase34" / "sweep" / f"{exp_id}_summary.json"
        summary = load_summary(summary_file)
        
        # 메트릭 추출
        metrics = extract_metrics(summary)
        
        # 행 생성
        row = {
            "exp_id": exp_id,
            "confidence_trend": params["confidence_trend"],
            "confidence_range": params["confidence_range"],
            "hysteresis": params["hysteresis"],
            "higher_tf_weight": params["higher_tf_weight"],
            "local_tf_weight": params["local_tf_weight"],
            **metrics,
            "duration_sec": result.get("duration_seconds", 0),
            "success": result.get("success", False)
        }
        
        rows.append(row)
        
        # 로그
        status = "✅" if result.get("success") else "❌"
        logger.info(
            f"{status} {exp_id}: trades={metrics['trades']}, "
            f"WR={metrics['win_rate']:.1f}%, PF={metrics['profit_factor']:.2f}, "
            f"blocked={metrics['blocked_rate']:.1f}%"
        )
    
    # DataFrame 생성
    df = pd.DataFrame(rows)
    
    # 정렬 (차단율 오름차순, trades 내림차순)
    df = df.sort_values(by=["blocked_rate", "trades"], ascending=[True, False])
    
    return df


def calculate_pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pareto Frontier 계산
    목표: 차단율 최소화 + 품질 유지 (WR, PF)
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Pareto Frontier Analysis")
    logger.info("=" * 80)
    
    # AC 필터링
    ac1 = df["exceptions"] == 0
    ac2 = df["trades"] >= 7000  # 3M 기준 최소
    ac3 = (df["win_rate"] >= 25) & (df["profit_factor"] >= 0.8)
    
    valid = df[ac1 & ac2 & ac3].copy()
    
    logger.info(f"🔍 AC 통과: {len(valid)}/{len(df)}")
    
    if len(valid) == 0:
        logger.warning("⚠️  No experiments passed all AC criteria")
        return pd.DataFrame()
    
    # Pareto 점수 계산 (차단율 감소가 주목표)
    valid["pareto_score"] = (
        -valid["blocked_rate"] * 2.0 +  # 차단율 감소 (가중치 2배)
        valid["win_rate"] * 0.5 +        # 승률 유지
        valid["profit_factor"] * 10.0    # PF 유지
    )
    
    # Top 5 선정
    top5 = valid.nlargest(5, "pareto_score")
    
    logger.info("")
    logger.info("🏆 Top 5 Candidates:")
    for idx, row in top5.iterrows():
        logger.info(
            f"  {row['exp_id']}: "
            f"blocked={row['blocked_rate']:.1f}%, "
            f"trades={row['trades']}, "
            f"WR={row['win_rate']:.1f}%, "
            f"PF={row['profit_factor']:.2f}, "
            f"score={row['pareto_score']:.1f}"
        )
    
    return top5


def save_results(df: pd.DataFrame, top5: pd.DataFrame):
    """결과 저장"""
    # CSV 저장
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"💾 CSV: {OUTPUT_CSV}")
    
    # JSON 저장
    df.to_json(OUTPUT_JSON, orient="records", indent=2)
    logger.info(f"💾 JSON: {OUTPUT_JSON}")
    
    # Pareto CSV
    if not top5.empty:
        top5.to_csv(PARETO_CSV, index=False)
        logger.info(f"💾 Pareto: {PARETO_CSV}")


def main():
    """메인"""
    # 집계
    df = aggregate_results()
    
    # Pareto 분석
    top5 = calculate_pareto_frontier(df)
    
    # 저장
    save_results(df, top5)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ Aggregation Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
