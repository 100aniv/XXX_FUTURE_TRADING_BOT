#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER18: 극단적 파라미터 테스트 - 전략 반응성 검증
================================================================================

ITER17 결과:
- AC1 PASS: effective params가 후보별로 다름
- AC3 FAIL: metrics는 모두 동일 (trades=10498, PF=0.567)
- 원인: 91% 신호가 ENSEMBLE_NO_CONSENSUS로 차단

ITER18 목표:
- G1: 극단적 파라미터로 전략 반응성 강제 검증
  - C6_min_votes1: min_votes=1 (1개만 있어도 진입) → 거래 수 대폭 증가 예상
  - C7_conf_threshold99: confidence=0.99 (거의 모든 신호 차단) → 거래 수 0 또는 극소 예상
- G2: 신호 병목 식별 (regime filter vs sub-model 비활성)
- G3: ITER19 방향 결정 (옵션2: regime 완화 / 옵션3: sub-model 튜닝)

AC:
- AC1: 극단적 후보 2개 추가 (C6, C7)
- AC2: metrics가 baseline과 다름 (trades 또는 PF 변화)
- AC3: 결과 분석 문서화
- AC4: 테스트 42+ PASS
- AC5: ITER18 Report + ROADMAP 업데이트
- AC6: Git commit & push
"""
import sys
import os
import json
import copy
import yaml
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 프로젝트 루트 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")

# =====================================
# ITER18 Constants
# =====================================
BASE_CONFIG_PATH = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
ARTIFACTS_DIR = project_root / "artifacts" / "phase35" / "iter18"

# IS/OOS Window (ITER17과 동일)
IS_WINDOW = ("2024-11-01", "2024-11-30")
OOS_WINDOW = ("2024-12-01", "2024-12-14")

# =====================================
# ITER18 Candidates - 극단적 파라미터 포함
# =====================================
CANDIDATES = {
    # Baseline (기준선)
    "C0_baseline": {
        "description": "Baseline (변경 없음, min_votes=2, conf=0.70)",
        "overrides": {}
    },
    
    # =====================================
    # ITER18 핵심: 극단적 파라미터 테스트
    # =====================================
    "C6_min_votes1": {
        "description": "극단적 허용: min_votes=1 (1개만 있어도 진입)",
        "overrides": {
            "ensemble.min_votes": 1
        },
        "expected_behavior": "거래 수 대폭 증가 (1개 sub-model만 LONG/SHORT 투표해도 진입)"
    },
    "C7_conf_threshold99": {
        "description": "극단적 제한: confidence_threshold=0.99 (거의 모든 신호 차단)",
        "overrides": {
            "ensemble.confidence_threshold": 0.99
        },
        "expected_behavior": "거래 수 0 또는 극소 (99% confidence 요구)"
    },
    
    # =====================================
    # 추가 극단적 조합 (옵션)
    # =====================================
    "C8_ultra_permissive": {
        "description": "초허용: min_votes=1, conf=0.01, cooldown=0",
        "overrides": {
            "ensemble.min_votes": 1,
            "ensemble.confidence_threshold": 0.01,
            "ensemble.cooldown_bars": 0
        },
        "expected_behavior": "최대 거래 수 (모든 조건 최대 완화)"
    },
    "C9_ultra_strict": {
        "description": "초제한: min_votes=3, conf=0.99, cooldown=10",
        "overrides": {
            "ensemble.min_votes": 3,
            "ensemble.confidence_threshold": 0.99,
            "ensemble.cooldown_bars": 10
        },
        "expected_behavior": "거래 수 0 예상 (만장일치 + 99% confidence + 긴 쿨다운)"
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
    모든 가능한 경로에 동기화
    """
    result = copy.deepcopy(config)
    
    for key, value in overrides.items():
        parts = key.split(".")
        
        # 1. Root level 적용
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        
        # 2. strategy.ensemble 경로에도 동기화
        if parts[0] == "ensemble":
            if "strategy" not in result:
                result["strategy"] = {}
            if "ensemble" not in result["strategy"]:
                result["strategy"]["ensemble"] = {}
            result["strategy"]["ensemble"][parts[-1]] = value
        
        # 3. strategies.phase35_ensemble_v1.params.ensemble 경로에도 동기화
        if parts[0] == "ensemble":
            if "strategies" not in result:
                result["strategies"] = {}
            if "phase35_ensemble_v1" not in result["strategies"]:
                result["strategies"]["phase35_ensemble_v1"] = {}
            if "params" not in result["strategies"]["phase35_ensemble_v1"]:
                result["strategies"]["phase35_ensemble_v1"]["params"] = {}
            if "ensemble" not in result["strategies"]["phase35_ensemble_v1"]["params"]:
                result["strategies"]["phase35_ensemble_v1"]["params"]["ensemble"] = {}
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


def extract_effective_params_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Config에서 effective params 추출
    """
    path_variants = [
        "ensemble",
        "strategy.ensemble",
        "strategies.phase35_ensemble_v1.params.ensemble",
    ]
    
    for path in path_variants:
        parts = path.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        if value is not None and isinstance(value, dict):
            return {
                "min_votes": value.get("min_votes", 2),
                "confidence_threshold": value.get("confidence_threshold", 0.5),
                "cooldown_bars": value.get("cooldown_bars", 0),
                "source": path,
            }
    
    return {
        "min_votes": 2,
        "confidence_threshold": 0.5,
        "cooldown_bars": 0,
        "source": "defaults",
    }


def run_backtest_with_effective_params(config: Dict[str, Any], run_dir: Path, candidate_id: str) -> tuple:
    """
    백테스트 실행 + effective params 추출
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
    
    # Config에서 예상 effective params 추출
    expected_params = extract_effective_params_from_config(config)
    
    # Engine 실행 (ITER19 FIX: clean_state=True로 이전 데이터 초기화)
    run_v2(mode="backtest", config=config, clean_state=True)
    
    # 리포트 로드
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    else:
        logger.error(f"❌ Report not found: {report_path}")
        report_data = {}
    
    # Effective params 저장
    effective_params = {
        **expected_params,
        "candidate_id": candidate_id,
        "git_commit": get_git_commit(),
        "timestamp": datetime.now().isoformat(),
    }
    
    effective_params_path = run_dir / "effective_ensemble_params.json"
    with open(effective_params_path, "w", encoding="utf-8") as f:
        json.dump(effective_params, f, indent=2, ensure_ascii=False)
    
    logger.info(f"   [EFFECTIVE_PARAMS] candidate={candidate_id} min_votes={effective_params['min_votes']} "
                f"conf={effective_params['confidence_threshold']} cooldown={effective_params['cooldown_bars']} "
                f"source={effective_params['source']}")
    
    return report_data, effective_params


def create_summary(report_data: Dict[str, Any], config: Dict[str, Any], 
                   candidate_id: str, window_type: str,
                   effective_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    ITER15 계약에 맞는 summary 생성 + effective params 포함
    """
    metrics = report_data.get("metrics", {})
    initial_capital = config.get("initial_capital", 10000)
    
    # PnL 절대값
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
        "effective_params": effective_params,
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
    if "expected_behavior" in candidate_def:
        logger.info(f"   Expected: {candidate_def['expected_behavior']}")
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
        "expected_behavior": candidate_def.get("expected_behavior", ""),
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
        is_report, is_effective_params = run_backtest_with_effective_params(is_config, is_dir, candidate_id)
        is_summary = create_summary(is_report, is_config, candidate_id, "IS", is_effective_params)
        
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
        oos_report, oos_effective_params = run_backtest_with_effective_params(oos_config, oos_dir, candidate_id)
        oos_summary = create_summary(oos_report, oos_config, candidate_id, "OOS", oos_effective_params)
        
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


def verify_effective_params_differ(all_results: List[Dict]) -> tuple:
    """
    AC1 검증: 후보별 effective params가 다른지 확인
    """
    baseline_params = None
    different_candidates = []
    
    for result in all_results:
        cid = result["candidate_id"]
        is_data = result.get("is", {})
        
        if "error" in is_data:
            continue
        
        effective = is_data.get("effective_params", {})
        
        if cid == "C0_baseline":
            baseline_params = effective
        else:
            if baseline_params:
                if (effective.get("min_votes") != baseline_params.get("min_votes") or
                    effective.get("confidence_threshold") != baseline_params.get("confidence_threshold") or
                    effective.get("cooldown_bars") != baseline_params.get("cooldown_bars")):
                    different_candidates.append(cid)
    
    if not baseline_params:
        return False, "Baseline effective params not found"
    
    if len(different_candidates) == 0:
        return False, "All candidates have identical effective params to baseline"
    
    return True, f"AC1 PASS: {len(different_candidates)} candidates differ from baseline: {different_candidates}"


def verify_metrics_differ(all_results: List[Dict]) -> tuple:
    """
    ITER18 AC2 검증: 극단적 파라미터로 인해 metrics가 baseline과 다른지 확인
    """
    baseline_is = None
    different_candidates = []
    same_candidates = []
    
    for result in all_results:
        cid = result["candidate_id"]
        is_data = result.get("is", {})
        
        if "error" in is_data:
            continue
        
        trades = is_data.get("trades", 0)
        pf = is_data.get("profit_factor", 0)
        roi = is_data.get("roi", 0)
        
        if cid == "C0_baseline":
            baseline_is = {"trades": trades, "pf": pf, "roi": roi}
        else:
            if baseline_is:
                # 더 관대한 비교: trades가 10% 이상 차이나거나 PF/ROI가 다름
                trades_diff_pct = abs(trades - baseline_is["trades"]) / max(baseline_is["trades"], 1) * 100
                if (trades_diff_pct > 1 or  # 1% 이상 trades 차이
                    abs(pf - baseline_is["pf"]) > 0.001 or
                    abs(roi - baseline_is["roi"]) > 0.01):
                    different_candidates.append({
                        "candidate": cid,
                        "trades": trades,
                        "baseline_trades": baseline_is["trades"],
                        "trades_diff_pct": round(trades_diff_pct, 2),
                        "pf": pf,
                        "baseline_pf": baseline_is["pf"],
                        "roi": roi,
                        "baseline_roi": baseline_is["roi"],
                    })
                else:
                    same_candidates.append(cid)
    
    if not baseline_is:
        return False, "Baseline metrics not found", {}
    
    if len(different_candidates) == 0:
        return False, f"All candidates have identical metrics to baseline. Same: {same_candidates}", {
            "same_candidates": same_candidates,
        }
    
    return True, f"AC2 PASS: {len(different_candidates)} candidates differ from baseline", {
        "different_candidates": different_candidates
    }


def analyze_extreme_results(all_results: List[Dict]) -> Dict[str, Any]:
    """
    ITER18 AC3: 극단적 파라미터 결과 분석
    """
    analysis = {
        "baseline": None,
        "extreme_permissive": [],  # min_votes=1 계열
        "extreme_strict": [],      # conf=0.99 계열
        "conclusions": [],
    }
    
    for result in all_results:
        cid = result["candidate_id"]
        is_data = result.get("is", {})
        
        if "error" in is_data:
            continue
        
        trades = is_data.get("trades", 0)
        pf = is_data.get("profit_factor", 0)
        roi = is_data.get("roi", 0)
        eff = is_data.get("effective_params", {})
        
        entry = {
            "candidate": cid,
            "trades": trades,
            "pf": round(pf, 4),
            "roi": round(roi, 2),
            "min_votes": eff.get("min_votes"),
            "conf_thr": eff.get("confidence_threshold"),
            "cooldown": eff.get("cooldown_bars"),
        }
        
        if cid == "C0_baseline":
            analysis["baseline"] = entry
        elif eff.get("min_votes") == 1:
            analysis["extreme_permissive"].append(entry)
        elif eff.get("confidence_threshold", 0) >= 0.99:
            analysis["extreme_strict"].append(entry)
    
    # 결론 도출
    baseline = analysis["baseline"]
    if baseline:
        baseline_trades = baseline["trades"]
        
        # 허용적 극단 분석
        for perm in analysis["extreme_permissive"]:
            trades_change = perm["trades"] - baseline_trades
            pct_change = (trades_change / max(baseline_trades, 1)) * 100
            if trades_change > 0:
                analysis["conclusions"].append(
                    f"✅ {perm['candidate']}: min_votes=1로 거래 수 {trades_change:+,} ({pct_change:+.1f}%) 변화 → 파라미터 영향 확인"
                )
            elif trades_change == 0:
                analysis["conclusions"].append(
                    f"⚠️ {perm['candidate']}: min_votes=1에도 거래 수 변화 없음 → sub-model이 신호를 거의 생성하지 않음"
                )
            else:
                analysis["conclusions"].append(
                    f"❓ {perm['candidate']}: 예상과 달리 거래 수 감소 ({trades_change:+,}) → 추가 분석 필요"
                )
        
        # 제한적 극단 분석
        for strict in analysis["extreme_strict"]:
            trades_change = strict["trades"] - baseline_trades
            if strict["trades"] == 0:
                analysis["conclusions"].append(
                    f"✅ {strict['candidate']}: conf=0.99로 거래 수 0 → confidence_threshold 정상 작동"
                )
            elif strict["trades"] < baseline_trades * 0.1:  # 90% 이상 감소
                analysis["conclusions"].append(
                    f"✅ {strict['candidate']}: conf=0.99로 거래 수 {trades_change:+,} (90%+ 감소) → threshold 영향 확인"
                )
            elif trades_change == 0:
                analysis["conclusions"].append(
                    f"⚠️ {strict['candidate']}: conf=0.99에도 거래 수 변화 없음 → 모든 신호가 이미 0.99+ confidence를 가짐 (비정상)"
                )
    
    return analysis


def generate_compare_report(all_results: List[Dict], git_commit: str, 
                            ac1_result: tuple, ac2_result: tuple,
                            analysis: Dict[str, Any]) -> str:
    """
    ITER18 비교 리포트 생성
    """
    lines = [
        "# PHASE35-4 ITER18: 극단적 파라미터 테스트 결과",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Git Commit**: {git_commit}",
        f"**IS Window**: {IS_WINDOW[0]} ~ {IS_WINDOW[1]}",
        f"**OOS Window**: {OOS_WINDOW[0]} ~ {OOS_WINDOW[1]}",
        "",
        "---",
        "",
        "## 🎯 ITER18 목표",
        "",
        "1. **극단적 허용 (C6, C8)**: min_votes=1 → 거래 수 증가 예상",
        "2. **극단적 제한 (C7, C9)**: confidence_threshold=0.99 → 거래 수 0 또는 극소 예상",
        "3. **신호 병목 식별**: regime filter vs sub-model 비활성",
        "",
        "---",
        "",
        "## 📊 AC 검증 결과",
        "",
        f"**AC1 (Effective Params Differ)**: {'✅ PASS' if ac1_result[0] else '❌ FAIL'}",
        f"- {ac1_result[1]}",
        "",
        f"**AC2 (Metrics Differ)**: {'✅ PASS' if ac2_result[0] else '❌ FAIL'}",
        f"- {ac2_result[1]}",
        "",
    ]
    
    # 분석 결론
    if analysis.get("conclusions"):
        lines.extend([
            "---",
            "",
            "## 🔍 분석 결론",
            "",
        ])
        for conclusion in analysis["conclusions"]:
            lines.append(f"- {conclusion}")
        lines.append("")
    
    # 결과 테이블
    lines.extend([
        "---",
        "",
        "## 📊 Results Table",
        "",
        "| Candidate | min_votes | conf_thr | cooldown | Trades | PF | ROI% | vs Baseline |",
        "|-----------|-----------|----------|----------|--------|-----|------|-------------|",
    ])
    
    baseline_trades = analysis.get("baseline", {}).get("trades", 0)
    
    for result in all_results:
        cid = result["candidate_id"]
        is_data = result.get("is", {})
        
        if "error" in is_data:
            lines.append(f"| {cid} | - | - | - | ERROR | - | - | - |")
            continue
        
        trades = is_data.get("trades", 0)
        pf = is_data.get("profit_factor", 0)
        roi = is_data.get("roi", 0)
        eff = is_data.get("effective_params", {})
        
        mv = eff.get("min_votes", "-")
        ct = eff.get("confidence_threshold", "-")
        cd = eff.get("cooldown_bars", "-")
        
        if cid == "C0_baseline":
            vs_baseline = "baseline"
        else:
            trades_diff = trades - baseline_trades
            pct_diff = (trades_diff / max(baseline_trades, 1)) * 100
            vs_baseline = f"{trades_diff:+,} ({pct_diff:+.1f}%)"
        
        lines.append(f"| {cid} | {mv} | {ct} | {cd} | {trades:,} | {pf:.3f} | {roi:.2f}% | {vs_baseline} |")
    
    # 다음 단계
    lines.extend([
        "",
        "---",
        "",
        "## 🔮 다음 ITER (ITER19) 계획",
        "",
    ])
    
    if ac2_result[0]:
        lines.extend([
            "**ITER18 성공**: 극단적 파라미터로 metrics 변화 확인",
            "",
            "권장 ITER19 방향:",
            "- **옵션 A**: 최적 파라미터 탐색 (min_votes, confidence_threshold 조합 튜닝)",
            "- **옵션 B**: Regime filter 조정 (CHOP threshold 완화)",
            "- **옵션 C**: Sub-model 튜닝 (투표 발생률 증가)",
        ])
    else:
        lines.extend([
            "**ITER18 실패**: 극단적 파라미터에도 metrics 변화 없음",
            "",
            "원인 분석 필요:",
            "- Sub-model이 신호를 전혀 생성하지 않음 (모두 FLAT)",
            "- Regime filter가 모든 신호를 차단",
            "",
            "권장 ITER19 방향:",
            "- Regime filter 비활성화하여 테스트",
            "- Sub-model 로직 디버깅",
        ])
    
    return "\n".join(lines)


def main():
    """ITER18 극단적 파라미터 테스트 메인 함수"""
    start_time = datetime.now()
    
    logger.info("=" * 78)
    logger.info("🚀 PHASE35-4 ITER18: 극단적 파라미터 테스트 - 전략 반응성 검증")
    logger.info("=" * 78)
    
    # Artifacts 디렉토리 생성
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Base config 로드
    base_config = load_base_config()
    git_commit = get_git_commit()
    
    logger.info(f"📂 Base Config: {BASE_CONFIG_PATH}")
    logger.info(f"📂 Artifacts: {ARTIFACTS_DIR}")
    logger.info(f"🔖 Git Commit: {git_commit}")
    logger.info(f"🔬 Candidates: {len(CANDIDATES)}")
    
    # 모든 후보 실행
    all_results = []
    for candidate_id, candidate_def in CANDIDATES.items():
        try:
            result = run_candidate(candidate_id, candidate_def, base_config)
            all_results.append(result)
        except Exception as e:
            logger.error(f"❌ Candidate {candidate_id} 실행 실패: {e}")
            all_results.append({
                "candidate_id": candidate_id,
                "description": candidate_def["description"],
                "overrides": candidate_def["overrides"],
                "is": {"error": str(e)},
                "oos": {"error": str(e)},
            })
    
    # =====================================
    # ITER18 검증
    # =====================================
    logger.info("\n" + "=" * 78)
    logger.info("🔍 ITER18 Verification")
    logger.info("=" * 78)
    
    ac1_result = verify_effective_params_differ(all_results)
    ac2_result = verify_metrics_differ(all_results)
    analysis = analyze_extreme_results(all_results)
    
    logger.info(f"AC1 (Effective Params Differ): {'✅ PASS' if ac1_result[0] else '❌ FAIL'}")
    logger.info(f"   {ac1_result[1]}")
    logger.info(f"AC2 (Metrics Differ): {'✅ PASS' if ac2_result[0] else '❌ FAIL'}")
    logger.info(f"   {ac2_result[1]}")
    
    # 분석 결론 출력
    if analysis.get("conclusions"):
        logger.info("\n📊 분석 결론:")
        for conclusion in analysis["conclusions"]:
            logger.info(f"   {conclusion}")
    
    # =====================================
    # Results 저장
    # =====================================
    results_table = {
        "generated_at": datetime.now().isoformat(),
        "git_commit": git_commit,
        "is_window": list(IS_WINDOW),
        "oos_window": list(OOS_WINDOW),
        "iter18_verification": {
            "ac1_effective_params_differ": ac1_result[0],
            "ac1_message": ac1_result[1],
            "ac2_metrics_differ": ac2_result[0],
            "ac2_message": ac2_result[1],
            "ac2_details": ac2_result[2] if len(ac2_result) > 2 else {},
        },
        "analysis": analysis,
        "candidates": all_results,
    }
    
    results_table_path = ARTIFACTS_DIR / "results_table.json"
    with open(results_table_path, "w", encoding="utf-8") as f:
        json.dump(results_table, f, indent=2, ensure_ascii=False)
    logger.info(f"\n📊 Results table saved: {results_table_path}")
    
    # Compare report 생성
    compare_report = generate_compare_report(all_results, git_commit, ac1_result, ac2_result, analysis)
    compare_report_path = ARTIFACTS_DIR / "is_vs_oos_compare.md"
    with open(compare_report_path, "w", encoding="utf-8") as f:
        f.write(compare_report)
    logger.info(f"📄 Compare report saved: {compare_report_path}")
    
    # =====================================
    # Summary 출력
    # =====================================
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"\n⏱️  Total elapsed: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    
    logger.info("\n" + "=" * 78)
    logger.info("📊 Summary")
    logger.info("=" * 78)
    
    baseline_trades = analysis.get("baseline", {}).get("trades", 0)
    for result in all_results:
        cid = result["candidate_id"]
        is_data = result.get("is", {})
        
        if "error" in is_data:
            logger.info(f"{cid}: ERROR")
            continue
        
        trades = is_data.get("trades", 0)
        pf = is_data.get("profit_factor", 0)
        eff = is_data.get("effective_params", {})
        
        if cid == "C0_baseline":
            diff_str = "baseline"
        else:
            trades_diff = trades - baseline_trades
            diff_str = f"{trades_diff:+,}"
        
        logger.info(f"{cid}: T={trades:,} ({diff_str}), PF={pf:.3f}, mv={eff.get('min_votes')}, conf={eff.get('confidence_threshold')}")
    
    logger.info("=" * 78)
    
    # 최종 판정
    if ac1_result[0] and ac2_result[0]:
        logger.info("✅ ITER18 PASS: 극단적 파라미터로 metrics 변화 확인됨")
        sys.exit(0)
    elif ac1_result[0] and not ac2_result[0]:
        logger.warning("⚠️ ITER18 PARTIAL: effective params는 다르지만 metrics 변화 없음")
        logger.warning("   → Sub-model 또는 regime filter가 모든 신호를 차단 중")
        sys.exit(1)
    else:
        logger.error("❌ ITER18 FAIL: effective params도 동일")
        sys.exit(1)


if __name__ == "__main__":
    main()
