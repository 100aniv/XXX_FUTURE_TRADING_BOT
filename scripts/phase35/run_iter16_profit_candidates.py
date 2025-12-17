#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER16: Candidate Sweep SSOT Runner
==============================================

목표:
- 전략 수익성 개선을 위한 파라미터 후보군 스윕
- IS/OOS 검증으로 과최적화 방지
- 재현 가능한 산출물 생성 (SSOT)

Usage:
    python scripts/phase35/run_iter16_profit_candidates.py

산출물:
    artifacts/phase35/iter16/<candidate_id>/is/summary.json
    artifacts/phase35/iter16/<candidate_id>/oos/summary.json
    artifacts/phase35/iter16/is_vs_oos_compare.md
    artifacts/phase35/iter16/results_table.json
"""
import sys
import yaml
import json
import copy
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("iter16_candidates")

# =====================================
# ITER16 설정 (SSOT)
# =====================================

# Base Config (SSOT)
BASE_CONFIG_PATH = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"

# 날짜 범위
IS_WINDOW = ("2024-11-01", "2024-11-30")  # In-Sample: 1개월
OOS_WINDOW = ("2024-12-01", "2024-12-14")  # Out-of-Sample: 2주

# Artifacts 경로
ARTIFACTS_DIR = project_root / "artifacts" / "phase35" / "iter16"

# =====================================
# Candidate 정의 (필터/가드/threshold 계열만)
# =====================================
# 원칙: "전략 로직 대수술" 금지. 안전한 knob만 조정.
CANDIDATES = {
    "C0_baseline": {
        "description": "Baseline (변경 없음)",
        "overrides": {}
    },
    "C1_conf_high": {
        "description": "confidence_threshold 상향 (0.70 → 0.80)",
        "overrides": {
            "ensemble.confidence_threshold": 0.80
        }
    },
    "C2_votes_high": {
        "description": "min_votes 상향 (2 → 3, 만장일치)",
        "overrides": {
            "ensemble.min_votes": 3
        }
    },
    "C3_cooldown_high": {
        "description": "cooldown_bars 상향 (3 → 6, 과매매 감소)",
        "overrides": {
            "ensemble.cooldown_bars": 6
        }
    },
    "C4_conf_votes_mid": {
        "description": "confidence+votes 중간 조합 (0.75, 2)",
        "overrides": {
            "ensemble.confidence_threshold": 0.75,
            "ensemble.min_votes": 2
        }
    },
    "C5_conservative": {
        "description": "보수적 조합 (conf=0.80, cooldown=5)",
        "overrides": {
            "ensemble.confidence_threshold": 0.80,
            "ensemble.cooldown_bars": 5
        }
    },
}


def load_base_config() -> Dict[str, Any]:
    """Base Config 로드"""
    if not BASE_CONFIG_PATH.exists():
        logger.error(f"❌ Base config not found: {BASE_CONFIG_PATH}")
        sys.exit(1)
    
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_overrides(config: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Config에 override 적용 (dot notation 지원)
    예: "ensemble.confidence_threshold" → config["ensemble"]["confidence_threshold"]
    """
    result = copy.deepcopy(config)
    
    for key, value in overrides.items():
        parts = key.split(".")
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        
        # 전략 params 섹션에도 동기화 (호환성)
        if parts[0] == "ensemble":
            strategies_path = result.get("strategies", {}).get("phase35_ensemble_v1", {}).get("params", {})
            if "ensemble" not in strategies_path:
                if "strategies" not in result:
                    result["strategies"] = {}
                if "phase35_ensemble_v1" not in result["strategies"]:
                    result["strategies"]["phase35_ensemble_v1"] = {}
                if "params" not in result["strategies"]["phase35_ensemble_v1"]:
                    result["strategies"]["phase35_ensemble_v1"]["params"] = {}
                if "ensemble" not in result["strategies"]["phase35_ensemble_v1"]["params"]:
                    result["strategies"]["phase35_ensemble_v1"]["params"]["ensemble"] = {}
            
            # 동기화
            result["strategies"]["phase35_ensemble_v1"]["params"]["ensemble"][parts[-1]] = value
    
    return result


def apply_date_range(config: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
    """날짜 범위 적용"""
    result = copy.deepcopy(config)
    result["start_date"] = start_date
    result["end_date"] = end_date
    
    if "backtest" not in result:
        result["backtest"] = {}
    result["backtest"]["start_date"] = start_date
    result["backtest"]["end_date"] = end_date
    
    return result


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
    except Exception:
        pass
    return "unknown"


def run_backtest(config: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    """
    백테스트 실행 (run_iter5_isolated_v2.py 로직 재사용)
    """
    from common.config_preflight import reset_usage_tracker
    from common.database import get_db_connection
    from execution.engine import run_v2
    
    reset_usage_tracker()
    
    # ITER19 FIX: 각 후보 실행 전 PostgreSQL trades 테이블 초기화
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM trading.trades")
                conn.commit()
                logger.info(f"   [DB] PostgreSQL trades 테이블 초기화 완료")
    except Exception as e:
        logger.warning(f"   [DB] PostgreSQL 초기화 실패 (무시): {e}")
    
    # Output 경로 설정
    report_path = run_dir / "backtest_report.json"
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["output_file"] = str(report_path)
    
    # Effective config 저장
    effective_config_path = run_dir / "effective_config.yaml"
    with open(effective_config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    # Engine 실행 (ITER19 FIX: clean_state=True로 이전 데이터 초기화)
    run_v2(mode="backtest", config=config, clean_state=True)
    
    # 리포트 로드
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        logger.error(f"❌ Report not found: {report_path}")
        return {}


def create_summary(report_data: Dict[str, Any], config: Dict[str, Any], 
                   candidate_id: str, window_type: str) -> Dict[str, Any]:
    """
    ITER15 계약에 맞는 summary 생성
    (pnl_abs + roi_pct + mdd_abs + mdd_pct, trades alias)
    """
    metrics = report_data.get("metrics", {})
    initial_capital = config.get("initial_capital", 10000)
    
    # ITER15 계약: PnL 절대값 (metrics["pnl"] 우선, 없으면 metrics["roi"])
    if "pnl" in metrics:
        pnl_abs = metrics["pnl"]
    elif "net_pnl" in metrics:
        pnl_abs = metrics["net_pnl"]
    else:
        pnl_abs = metrics.get("roi", 0.0)
    
    # ROI %
    roi_pct = (pnl_abs / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # MDD 절대값
    mdd_abs = metrics.get("mdd", metrics.get("max_drawdown", 0.0))
    mdd_pct = (abs(mdd_abs) / initial_capital) * 100 if initial_capital > 0 else 0.0
    
    # Total Trades
    total_trades = metrics.get("total_trades", 0)
    
    return {
        "candidate_id": candidate_id,
        "window_type": window_type,
        "start_date": config.get("start_date"),
        "end_date": config.get("end_date"),
        "initial_capital": initial_capital,
        "trades": total_trades,
        "total_trades": total_trades,
        "win_rate": metrics.get("winrate", 0.0),
        "profit_factor": metrics.get("pf", 0.0),
        "pnl": round(pnl_abs, 2),
        "roi": round(roi_pct, 2),
        "max_drawdown": round(mdd_abs, 2),
        "mdd_pct": round(mdd_pct, 2),
        "kpi_source": "metrics (SSOT)",
        "kpi_contract": "pnl_abs + roi_pct + mdd_abs + mdd_pct",
        "generated_at": datetime.now().isoformat(),
    }


def run_candidate(candidate_id: str, candidate_def: Dict[str, Any],
                  base_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 후보 실행 (IS + OOS)
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🔬 Candidate: {candidate_id}")
    logger.info(f"   {candidate_def['description']}")
    logger.info(f"   Overrides: {candidate_def['overrides']}")
    logger.info(f"{'='*60}")
    
    # 후보별 디렉토리
    candidate_dir = ARTIFACTS_DIR / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    
    # Config에 override 적용
    config_with_overrides = apply_overrides(base_config, candidate_def["overrides"])
    
    results = {
        "candidate_id": candidate_id,
        "description": candidate_def["description"],
        "overrides": candidate_def["overrides"],
        "is": None,
        "oos": None,
    }
    
    # =====================================
    # IS (In-Sample) 실행
    # =====================================
    logger.info(f"\n📊 [IS] {IS_WINDOW[0]} ~ {IS_WINDOW[1]}")
    is_dir = candidate_dir / "is"
    is_dir.mkdir(parents=True, exist_ok=True)
    
    is_config = apply_date_range(config_with_overrides, IS_WINDOW[0], IS_WINDOW[1])
    
    try:
        is_report = run_backtest(is_config, is_dir)
        is_summary = create_summary(is_report, is_config, candidate_id, "IS")
        
        # Summary 저장
        is_summary_path = is_dir / "summary.json"
        with open(is_summary_path, "w", encoding="utf-8") as f:
            json.dump(is_summary, f, indent=2, ensure_ascii=False)
        
        results["is"] = is_summary
        logger.info(f"   IS Trades: {is_summary['trades']}, PF: {is_summary['profit_factor']:.3f}, ROI: {is_summary['roi']:.2f}%")
    except Exception as e:
        logger.error(f"❌ IS 실행 실패: {e}")
        results["is"] = {"error": str(e)}
    
    # =====================================
    # OOS (Out-of-Sample) 실행
    # =====================================
    logger.info(f"\n📊 [OOS] {OOS_WINDOW[0]} ~ {OOS_WINDOW[1]}")
    oos_dir = candidate_dir / "oos"
    oos_dir.mkdir(parents=True, exist_ok=True)
    
    oos_config = apply_date_range(config_with_overrides, OOS_WINDOW[0], OOS_WINDOW[1])
    
    try:
        oos_report = run_backtest(oos_config, oos_dir)
        oos_summary = create_summary(oos_report, oos_config, candidate_id, "OOS")
        
        # Summary 저장
        oos_summary_path = oos_dir / "summary.json"
        with open(oos_summary_path, "w", encoding="utf-8") as f:
            json.dump(oos_summary, f, indent=2, ensure_ascii=False)
        
        results["oos"] = oos_summary
        logger.info(f"   OOS Trades: {oos_summary['trades']}, PF: {oos_summary['profit_factor']:.3f}, ROI: {oos_summary['roi']:.2f}%")
    except Exception as e:
        logger.error(f"❌ OOS 실행 실패: {e}")
        results["oos"] = {"error": str(e)}
    
    return results


def calculate_delta_metrics(is_data: Dict, oos_data: Dict, baseline_is: Dict) -> Dict[str, float]:
    """
    델타 메트릭 계산 (기준선 대비 변화량)
    """
    if not is_data or not oos_data or not baseline_is:
        return {}
    
    if "error" in is_data or "error" in oos_data:
        return {}
    
    return {
        "delta_pf_vs_baseline": is_data.get("profit_factor", 0) - baseline_is.get("profit_factor", 0),
        "delta_trades_vs_baseline": is_data.get("trades", 0) - baseline_is.get("trades", 0),
        "delta_trades_pct": ((is_data.get("trades", 0) - baseline_is.get("trades", 0)) / baseline_is.get("trades", 1)) * 100 if baseline_is.get("trades", 0) > 0 else 0,
        "is_oos_pf_diff": is_data.get("profit_factor", 0) - oos_data.get("profit_factor", 0),
        "is_oos_roi_diff": is_data.get("roi", 0) - oos_data.get("roi", 0),
    }


def generate_compare_report(all_results: List[Dict], git_commit: str) -> str:
    """
    IS vs OOS 비교 리포트 생성 (Markdown)
    """
    lines = [
        "# PHASE35-4 ITER16: IS vs OOS Comparison Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Git Commit**: {git_commit}",
        f"**IS Window**: {IS_WINDOW[0]} ~ {IS_WINDOW[1]}",
        f"**OOS Window**: {OOS_WINDOW[0]} ~ {OOS_WINDOW[1]}",
        "",
        "---",
        "",
        "## 📊 Results Table",
        "",
        "| Candidate | Description | IS Trades | IS PF | IS ROI% | OOS Trades | OOS PF | OOS ROI% | Δ PF (IS-OOS) |",
        "|-----------|-------------|-----------|-------|---------|------------|--------|----------|---------------|",
    ]
    
    baseline_is = None
    for r in all_results:
        if r["candidate_id"] == "C0_baseline" and r.get("is"):
            baseline_is = r["is"]
            break
    
    for r in all_results:
        cid = r["candidate_id"]
        desc = r["description"][:30] + "..." if len(r["description"]) > 30 else r["description"]
        
        is_data = r.get("is", {})
        oos_data = r.get("oos", {})
        
        if "error" in is_data or "error" in oos_data:
            lines.append(f"| {cid} | {desc} | ERROR | - | - | ERROR | - | - | - |")
            continue
        
        is_trades = is_data.get("trades", 0)
        is_pf = is_data.get("profit_factor", 0)
        is_roi = is_data.get("roi", 0)
        
        oos_trades = oos_data.get("trades", 0)
        oos_pf = oos_data.get("profit_factor", 0)
        oos_roi = oos_data.get("roi", 0)
        
        delta_pf = is_pf - oos_pf
        
        lines.append(f"| {cid} | {desc} | {is_trades:,} | {is_pf:.3f} | {is_roi:.2f}% | {oos_trades:,} | {oos_pf:.3f} | {oos_roi:.2f}% | {delta_pf:+.3f} |")
    
    # 랭킹 (IS PF 기준, OOS와의 차이가 작을수록 좋음)
    lines.extend([
        "",
        "---",
        "",
        "## 🏆 Ranking (Overfitting 방지 기준)",
        "",
        "**선정 기준**:",
        "1. OOS PF가 높을수록 좋음 (실전 성능)",
        "2. IS-OOS PF 차이가 작을수록 좋음 (과최적화 방지)",
        "3. 거래 수 감소 시 MDD 악화 없이 유지",
        "",
    ])
    
    # 유효 결과만 필터링
    valid_results = [r for r in all_results if r.get("is") and r.get("oos") and "error" not in r.get("is", {}) and "error" not in r.get("oos", {})]
    
    # OOS PF 기준 정렬
    sorted_by_oos_pf = sorted(valid_results, key=lambda x: x["oos"].get("profit_factor", 0), reverse=True)
    
    if len(sorted_by_oos_pf) >= 2:
        top1 = sorted_by_oos_pf[0]
        top2 = sorted_by_oos_pf[1]
        
        lines.extend([
            f"### Top 1: {top1['candidate_id']}",
            f"- **설명**: {top1['description']}",
            f"- **OOS PF**: {top1['oos'].get('profit_factor', 0):.3f}",
            f"- **OOS ROI**: {top1['oos'].get('roi', 0):.2f}%",
            f"- **IS-OOS PF 차이**: {top1['is'].get('profit_factor', 0) - top1['oos'].get('profit_factor', 0):.3f}",
            "",
            f"### Top 2: {top2['candidate_id']}",
            f"- **설명**: {top2['description']}",
            f"- **OOS PF**: {top2['oos'].get('profit_factor', 0):.3f}",
            f"- **OOS ROI**: {top2['oos'].get('roi', 0):.2f}%",
            f"- **IS-OOS PF 차이**: {top2['is'].get('profit_factor', 0) - top2['oos'].get('profit_factor', 0):.3f}",
            "",
        ])
    
    # 비용 민감도 메모
    lines.extend([
        "---",
        "",
        "## 💰 거래 비용 민감도 메모",
        "",
        "**가정**:",
        "- Taker Fee: 0.04% (4 bps)",
        "- Slippage: 5 bps",
        "- 총 Round-trip 비용: ~18 bps (0.18%)",
        "",
        "**경고**: 과매매 전략은 거래 비용에 매우 민감함.",
        "- 10,000 trades × 0.18% = 약 18% 추가 손실",
        "- 거래 수 감소가 ROI 개선에 직접적 영향",
        "",
        "**권장**: trades 수가 30% 이상 감소하면서 PF 유지/개선되는 후보 우선 선택",
        "",
    ])
    
    # 다음 ITER 제안
    lines.extend([
        "---",
        "",
        "## 🔮 다음 ITER 제안",
        "",
    ])
    
    if baseline_is and len(sorted_by_oos_pf) > 0:
        best = sorted_by_oos_pf[0]
        baseline_pf = baseline_is.get("profit_factor", 0)
        best_oos_pf = best["oos"].get("profit_factor", 0)
        
        if best_oos_pf > baseline_pf:
            lines.append(f"✅ **PF 개선 확인**: {best['candidate_id']}가 baseline 대비 OOS PF 개선")
            lines.append(f"   - Baseline IS PF: {baseline_pf:.3f}")
            lines.append(f"   - Best OOS PF: {best_oos_pf:.3f}")
            lines.append("")
            lines.append("**다음 ITER 제안**: 해당 후보 기반으로 추가 미세 조정")
        else:
            lines.append("⚠️ **PF 개선 미달**: 모든 후보가 baseline 대비 OOS PF 개선 실패")
            lines.append("")
            lines.append("**가설/분석 필요**:")
            lines.append("1. 현재 필터/threshold 조정만으로는 한계")
            lines.append("2. 전략 로직 자체의 구조적 문제 가능성")
            lines.append("3. 시장 환경(2024-11~12)이 불리했을 가능성")
            lines.append("")
            lines.append("**다음 ITER 제안**:")
            lines.append("- Sub-model 가중치 조정 검토")
            lines.append("- Regime 필터 조건 분석")
            lines.append("- 손절/익절 로직 점검")
    
    return "\n".join(lines)


def main():
    """메인 실행 함수"""
    import time
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE35-4 ITER16: Candidate Sweep SSOT Runner")
    logger.info("=" * 80)
    
    git_commit = get_git_commit()
    logger.info(f"📌 Git Commit: {git_commit}")
    logger.info(f"📁 Artifacts: {ARTIFACTS_DIR}")
    logger.info(f"📅 IS Window: {IS_WINDOW}")
    logger.info(f"📅 OOS Window: {OOS_WINDOW}")
    
    # Artifacts 디렉토리 생성
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Base Config 로드
    base_config = load_base_config()
    logger.info(f"✅ Base config loaded: {BASE_CONFIG_PATH}")
    
    # 후보 정의 저장 (재현성)
    candidates_path = ARTIFACTS_DIR / "candidates_definition.json"
    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(CANDIDATES, f, indent=2, ensure_ascii=False)
    logger.info(f"📄 Candidates definition saved: {candidates_path}")
    
    # 모든 후보 실행
    all_results = []
    for candidate_id, candidate_def in CANDIDATES.items():
        result = run_candidate(candidate_id, candidate_def, base_config)
        all_results.append(result)
    
    # Results Table 저장
    results_table = {
        "generated_at": datetime.now().isoformat(),
        "git_commit": git_commit,
        "is_window": IS_WINDOW,
        "oos_window": OOS_WINDOW,
        "candidates": all_results,
    }
    
    results_table_path = ARTIFACTS_DIR / "results_table.json"
    with open(results_table_path, "w", encoding="utf-8") as f:
        json.dump(results_table, f, indent=2, ensure_ascii=False)
    logger.info(f"\n📊 Results table saved: {results_table_path}")
    
    # IS vs OOS 비교 리포트 생성
    compare_report = generate_compare_report(all_results, git_commit)
    compare_path = ARTIFACTS_DIR / "is_vs_oos_compare.md"
    with open(compare_path, "w", encoding="utf-8") as f:
        f.write(compare_report)
    logger.info(f"📄 Compare report saved: {compare_path}")
    
    # 실행 시간
    elapsed = time.time() - start_time
    logger.info(f"\n⏱️  Total elapsed: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    
    # 요약 출력
    logger.info("\n" + "=" * 80)
    logger.info("📊 Summary")
    logger.info("=" * 80)
    
    for r in all_results:
        is_data = r.get("is", {})
        oos_data = r.get("oos", {})
        
        if "error" in is_data or "error" in oos_data:
            logger.info(f"{r['candidate_id']}: ERROR")
            continue
        
        logger.info(f"{r['candidate_id']}: IS(T={is_data.get('trades', 0):,}, PF={is_data.get('profit_factor', 0):.3f}) | OOS(T={oos_data.get('trades', 0):,}, PF={oos_data.get('profit_factor', 0):.3f})")
    
    logger.info("=" * 80)
    logger.info("✅ ITER16 Candidate Sweep 완료")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
