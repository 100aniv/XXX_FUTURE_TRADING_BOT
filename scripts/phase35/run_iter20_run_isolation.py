#!/usr/bin/env python3
"""
PHASE35-4 ITER20: Run Isolation + Sub-model Relaxation Runner
=============================================================

목표:
1. run_id/trial_id 기반 DB 완전 격리
2. Signal→Trade Evidence SSOT
3. Sub-model 최소 완화 (baseline vs relaxed)

AC:
- AC1: Candidate별 실행이 DB 관점에서 완전 격리
- AC2: 각 run의 report는 해당 trial_id의 trades만 집계
- AC3: trade가 어떤 signal/decision_trace에서 왔는지 추적 가능
- AC4: baseline vs relaxed에서 최소 1개 지표가 달라짐
"""

import logging
import json
import yaml
import sys
import uuid
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from copy import deepcopy

# 프로젝트 루트 설정
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Artifacts 디렉토리
ARTIFACTS_DIR = project_root / "artifacts" / "phase35" / "iter20"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# 기본 Config
BASE_CONFIG_PATH = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"


def get_git_commit() -> str:
    """현재 Git 커밋 해시"""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=project_root
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def load_base_config() -> Dict[str, Any]:
    """기본 Config 로드"""
    with open(BASE_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_candidate_overrides(config: Dict[str, Any], candidate_id: str) -> Dict[str, Any]:
    """
    후보별 Config Override 적용
    
    Candidates:
    - C0_baseline: 기존 그대로
    - C1_relaxed: Sub-model 조건 완화
    """
    config = deepcopy(config)
    
    if candidate_id == "C0_baseline":
        # 기존 그대로
        pass
    
    elif candidate_id == "C1_relaxed":
        # Sub-model 조건 완화
        if "sub_models" not in config:
            config["sub_models"] = {}
        
        # Trend: adx_threshold 20 → 15
        if "trend" not in config["sub_models"]:
            config["sub_models"]["trend"] = {}
        config["sub_models"]["trend"]["adx_threshold"] = 15
        
        # Reversion: rsi 범위 완화
        if "reversion" not in config["sub_models"]:
            config["sub_models"]["reversion"] = {}
        config["sub_models"]["reversion"]["rsi_oversold"] = 35
        config["sub_models"]["reversion"]["rsi_overbought"] = 65
        
        # Breakout: volume_threshold 완화
        if "breakout" not in config["sub_models"]:
            config["sub_models"]["breakout"] = {}
        config["sub_models"]["breakout"]["volume_threshold"] = 1.2
        
        # Regime filter: atr_chop_threshold 완화 (CHOP 판정 줄이기)
        if "regime" not in config:
            config["regime"] = {}
        config["regime"]["atr_chop_threshold"] = 0.003  # 0.005 → 0.003
    
    return config


def run_backtest_with_trial_id(
    config: Dict[str, Any], 
    run_dir: Path, 
    candidate_id: str,
    trial_id: str
) -> Dict[str, Any]:
    """
    백테스트 실행 (trial_id 기반 격리)
    
    Args:
        config: 설정
        run_dir: 결과 저장 디렉토리
        candidate_id: 후보 ID
        trial_id: 고유 trial ID (DB 격리용)
    
    Returns:
        백테스트 결과 리포트
    """
    from common.config_preflight import reset_usage_tracker
    from execution.engine import run_v2
    
    reset_usage_tracker()
    
    # trial_id를 config에 주입
    config["trial_id"] = trial_id
    config["run_id"] = trial_id  # run_id도 동일하게 설정
    
    # Output 경로 설정
    report_path = run_dir / "backtest_report.json"
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["output_file"] = str(report_path)
    
    # decision_trace 활성화
    config["decision_trace"] = True
    
    # Effective config 저장
    effective_config_path = run_dir / "effective_config.yaml"
    with open(effective_config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"   🆔 Trial ID: {trial_id}")
    logger.info(f"   📁 Output: {report_path}")
    
    # Engine 실행
    run_v2(mode="backtest", config=config, clean_state=True)
    
    # 리포트 로드
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    else:
        logger.error(f"❌ Report not found: {report_path}")
        report_data = {}
    
    return report_data


def collect_signal_flow_evidence(trial_id: str, run_dir: Path) -> Dict[str, Any]:
    """
    Signal Flow Evidence 수집 (DB에서 직접 조회)
    
    Args:
        trial_id: 백테스트 trial ID
        run_dir: 결과 저장 디렉토리
    
    Returns:
        signal_flow 통계
    """
    from common.database import get_db_connection
    
    evidence = {
        "trial_id": trial_id,
        "db_trades_count": 0,
        "db_trades_by_side": {},
        "db_trades_by_strategy": {},
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # trial_id로 trades 수 조회
                cur.execute("""
                    SELECT COUNT(*) FROM trading.trades
                    WHERE trial_id = %s AND status = 'CLOSED'
                """, (trial_id,))
                evidence["db_trades_count"] = cur.fetchone()[0]
                
                # side별 분포
                cur.execute("""
                    SELECT side, COUNT(*) FROM trading.trades
                    WHERE trial_id = %s AND status = 'CLOSED'
                    GROUP BY side
                """, (trial_id,))
                evidence["db_trades_by_side"] = {row[0]: row[1] for row in cur.fetchall()}
                
                # strategy별 분포
                cur.execute("""
                    SELECT strategy_id, COUNT(*) FROM trading.trades
                    WHERE trial_id = %s AND status = 'CLOSED'
                    GROUP BY strategy_id
                """, (trial_id,))
                evidence["db_trades_by_strategy"] = {row[0]: row[1] for row in cur.fetchall()}
                
    except Exception as e:
        logger.warning(f"⚠️ DB evidence 수집 실패: {e}")
    
    # 저장
    evidence_path = run_dir / "signal_flow.json"
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    
    return evidence


def verify_run_isolation(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run Isolation 검증
    
    Args:
        results: 각 후보의 결과 리스트
    
    Returns:
        검증 결과
    """
    from common.database import get_db_connection
    
    verification = {
        "ac1_db_isolation": True,
        "ac2_no_cross_contamination": True,
        "details": []
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for result in results:
                    trial_id = result.get("trial_id")
                    expected_count = result.get("evidence", {}).get("db_trades_count", 0)
                    
                    # 해당 trial_id의 실제 trades 수 확인
                    cur.execute("""
                        SELECT COUNT(*) FROM trading.trades
                        WHERE trial_id = %s
                    """, (trial_id,))
                    actual_count = cur.fetchone()[0]
                    
                    is_isolated = actual_count == expected_count
                    verification["details"].append({
                        "trial_id": trial_id,
                        "candidate_id": result.get("candidate_id"),
                        "expected_count": expected_count,
                        "actual_count": actual_count,
                        "isolated": is_isolated
                    })
                    
                    if not is_isolated:
                        verification["ac1_db_isolation"] = False
                
                # 교차 오염 확인: trial_id=NULL인 trades가 없어야 함
                cur.execute("""
                    SELECT COUNT(*) FROM trading.trades
                    WHERE trial_id IS NULL AND mode = 'backtest'
                """)
                null_trial_count = cur.fetchone()[0]
                if null_trial_count > 0:
                    verification["ac2_no_cross_contamination"] = False
                    verification["null_trial_trades"] = null_trial_count
                    
    except Exception as e:
        logger.error(f"❌ Run isolation 검증 실패: {e}")
        verification["error"] = str(e)
    
    return verification


def run_iter20():
    """ITER20 메인 실행"""
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE35-4 ITER20: Run Isolation + Sub-model Relaxation")
    logger.info("=" * 80)
    
    # 후보 정의
    candidates = ["C0_baseline", "C1_relaxed"]
    results = []
    
    for candidate_id in candidates:
        logger.info("\n" + "=" * 60)
        logger.info(f"🔄 Running: {candidate_id}")
        logger.info("=" * 60)
        
        # 고유 trial_id 생성
        trial_id = f"iter20_{candidate_id}_{uuid.uuid4().hex[:8]}"
        
        # 결과 디렉토리
        run_dir = ARTIFACTS_DIR / candidate_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Config 로드 및 override 적용
        config = load_base_config()
        config = apply_candidate_overrides(config, candidate_id)
        
        # Sub-model params 로그
        sub_models = config.get("sub_models", {})
        logger.info(f"   📊 Sub-model params:")
        logger.info(f"      - trend.adx_threshold: {sub_models.get('trend', {}).get('adx_threshold', 20)}")
        logger.info(f"      - reversion.rsi_oversold: {sub_models.get('reversion', {}).get('rsi_oversold', 30)}")
        logger.info(f"      - reversion.rsi_overbought: {sub_models.get('reversion', {}).get('rsi_overbought', 70)}")
        logger.info(f"      - breakout.volume_threshold: {sub_models.get('breakout', {}).get('volume_threshold', 1.5)}")
        logger.info(f"      - regime.atr_chop_threshold: {config.get('regime', {}).get('atr_chop_threshold', 0.005)}")
        
        # 백테스트 실행
        report = run_backtest_with_trial_id(config, run_dir, candidate_id, trial_id)
        
        # Signal flow evidence 수집
        evidence = collect_signal_flow_evidence(trial_id, run_dir)
        
        # 결과 저장
        result = {
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "report": report,
            "evidence": evidence,
            "metrics": report.get("metrics", {}),
        }
        results.append(result)
        
        # 간단 요약
        metrics = result["metrics"]
        logger.info(f"\n   📊 Results:")
        logger.info(f"      - Total Trades: {metrics.get('total_trades', 0)}")
        logger.info(f"      - Win Rate: {metrics.get('winrate', 0):.2f}%")
        logger.info(f"      - Profit Factor: {metrics.get('pf', 0):.4f}")
        logger.info(f"      - DB Trades (trial_id): {evidence.get('db_trades_count', 0)}")
    
    # Run Isolation 검증
    logger.info("\n" + "=" * 60)
    logger.info("🔍 Run Isolation Verification")
    logger.info("=" * 60)
    
    isolation_result = verify_run_isolation(results)
    logger.info(f"   AC1 (DB Isolation): {'✅ PASS' if isolation_result['ac1_db_isolation'] else '❌ FAIL'}")
    logger.info(f"   AC2 (No Cross Contamination): {'✅ PASS' if isolation_result['ac2_no_cross_contamination'] else '❌ FAIL'}")
    
    for detail in isolation_result.get("details", []):
        logger.info(f"      - {detail['candidate_id']}: expected={detail['expected_count']}, actual={detail['actual_count']}, isolated={detail['isolated']}")
    
    # Baseline vs Relaxed 비교
    logger.info("\n" + "=" * 60)
    logger.info("📊 Baseline vs Relaxed Comparison")
    logger.info("=" * 60)
    
    baseline = next((r for r in results if r["candidate_id"] == "C0_baseline"), None)
    relaxed = next((r for r in results if r["candidate_id"] == "C1_relaxed"), None)
    
    comparison = {}
    if baseline and relaxed:
        b_metrics = baseline.get("metrics", {})
        r_metrics = relaxed.get("metrics", {})
        
        comparison = {
            "total_trades": {
                "baseline": b_metrics.get("total_trades", 0),
                "relaxed": r_metrics.get("total_trades", 0),
                "diff": r_metrics.get("total_trades", 0) - b_metrics.get("total_trades", 0)
            },
            "winrate": {
                "baseline": b_metrics.get("winrate", 0),
                "relaxed": r_metrics.get("winrate", 0),
                "diff": r_metrics.get("winrate", 0) - b_metrics.get("winrate", 0)
            },
            "pf": {
                "baseline": b_metrics.get("pf", 0),
                "relaxed": r_metrics.get("pf", 0),
                "diff": r_metrics.get("pf", 0) - b_metrics.get("pf", 0)
            },
        }
        
        logger.info(f"   Total Trades: {comparison['total_trades']['baseline']} → {comparison['total_trades']['relaxed']} ({comparison['total_trades']['diff']:+d})")
        logger.info(f"   Win Rate: {comparison['winrate']['baseline']:.2f}% → {comparison['winrate']['relaxed']:.2f}% ({comparison['winrate']['diff']:+.2f}%)")
        logger.info(f"   Profit Factor: {comparison['pf']['baseline']:.4f} → {comparison['pf']['relaxed']:.4f} ({comparison['pf']['diff']:+.4f})")
        
        # AC4 체크: 최소 1개 지표가 달라져야 함
        ac4_pass = (
            comparison['total_trades']['diff'] != 0 or
            abs(comparison['winrate']['diff']) > 0.01 or
            abs(comparison['pf']['diff']) > 0.0001
        )
        logger.info(f"\n   AC4 (Metrics Differ): {'✅ PASS' if ac4_pass else '❌ FAIL'}")
    
    # 최종 결과 저장
    elapsed = time.time() - start_time
    
    final_result = {
        "generated_at": datetime.now().isoformat(),
        "git_commit": get_git_commit(),
        "elapsed_seconds": elapsed,
        "candidates": [
            {
                "candidate_id": r["candidate_id"],
                "trial_id": r["trial_id"],
                "metrics": r["metrics"],
                "evidence": r["evidence"],
            }
            for r in results
        ],
        "isolation_verification": isolation_result,
        "comparison": comparison,
        "ac_checklist": {
            "ac1_db_isolation": isolation_result.get("ac1_db_isolation", False),
            "ac2_no_cross_contamination": isolation_result.get("ac2_no_cross_contamination", False),
            "ac4_metrics_differ": ac4_pass if baseline and relaxed else False,
        }
    }
    
    results_path = ARTIFACTS_DIR / "iter20_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📁 Results saved: {results_path}")
    logger.info(f"⏱️  Elapsed: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    logger.info("=" * 60)
    
    return final_result


if __name__ == "__main__":
    run_iter20()
