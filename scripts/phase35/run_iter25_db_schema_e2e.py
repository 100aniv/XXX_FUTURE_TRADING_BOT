#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-4 ITER25: DB Schema E2E Validation
===========================================
DB 스키마/테이블 SSOT 확정 및 E2E trades>0 복구

목표:
- DB introspection으로 현재 상태 확인
- trading.trades 테이블 존재 보장
- L4_ultra_debug 백테스트 실행
- DB trades count>0 달성 (E2E 완료)
"""
import json
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트를 PYTHONPATH에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.postgres import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def ensure_trading_schema() -> bool:
    """
    trading 스키마 및 trades 테이블 존재 보장
    
    init_db.sql 스키마 정의를 기반으로 최소 보장
    
    Returns:
        bool: 성공 여부
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. trading 스키마 생성
                cur.execute("CREATE SCHEMA IF NOT EXISTS trading;")
                logger.info("✅ trading 스키마 확인/생성 완료")
                
                # 2. trading.trades 테이블 생성 (init_db.sql 기준)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trading.trades(
                      trade_id         TEXT PRIMARY KEY,
                      decision_id      TEXT,
                      symbol           TEXT NOT NULL,
                      side             TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
                      entry_price      NUMERIC NOT NULL,
                      exit_price       NUMERIC,
                      quantity         NUMERIC NOT NULL,
                      leverage         INTEGER NOT NULL,
                      sl_price         NUMERIC,
                      tp_price         NUMERIC,
                      ts_open          TIMESTAMPTZ NOT NULL,
                      ts_close         TIMESTAMPTZ,
                      pnl              NUMERIC,
                      pnl_pct          NUMERIC,
                      fees             NUMERIC DEFAULT 0,
                      status           TEXT NOT NULL CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
                      strategy_id      TEXT NOT NULL,
                      exit_reason      TEXT,
                      created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                      trial_id         TEXT,
                      mode             TEXT DEFAULT 'paper'
                    );
                """)
                logger.info("✅ trading.trades 테이블 확인/생성 완료")
                
                # 3. 인덱스 생성 (필수만)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts 
                    ON trading.trades (symbol, ts_open DESC);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_status 
                    ON trading.trades (status, ts_open DESC);
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_trial_id 
                    ON trading.trades (trial_id);
                """)
                logger.info("✅ trading.trades 인덱스 확인/생성 완료")
                
        return True
    
    except Exception as e:
        logger.error(f"❌ trading 스키마/테이블 생성 실패: {e}")
        return False


def run_l4_backtest(lookback_days: int = 7) -> Dict[str, Any]:
    """
    L4_ultra_debug 백테스트 실행 (ITER24 로직 재사용)
    
    Args:
        lookback_days: 백테스트 기간 (일)
    
    Returns:
        실행 결과 dict
    """
    from scripts.phase35.run_iter24_signal_diag_ultra_debug import (
        RELAXATION_LEVELS, load_base_config
    )
    
    candidate_id = "L4_ultra_debug"
    trial_id = f"iter25_{candidate_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("=" * 80)
    logger.info(f"🚀 Running Backtest: {candidate_id}")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # (1) Config 준비
    config = load_base_config()
    overrides = RELAXATION_LEVELS[candidate_id]
    
    # Deep merge
    for key, value in overrides.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    # backtest 키 확인/생성
    if "backtest" not in config:
        config["backtest"] = {}
    config["backtest"]["lookback_days"] = lookback_days
    
    # trial_id 주입
    if "trial_id" not in config:
        config["trial_id"] = trial_id
    else:
        config["trial_id"] = trial_id
    
    # Artifacts 디렉토리 준비
    run_dir = PROJECT_ROOT / "artifacts" / "phase35" / "iter25" / candidate_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Config 저장
    config_path = run_dir / "config.yml"
    import yaml
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    # (2) Backtest 실행 (run_v2)
    logger.info(f"🏃 Executing backtest: {candidate_id}")
    try:
        from execution.engine import run_v2
        run_v2(mode="backtest", config=config, clean_state=True)
        logger.info("✅ Backtest finished")
    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}")
        return {
            "candidate_id": candidate_id,
            "trial_id": trial_id,
            "success": False,
            "error": str(e),
            "elapsed": time.time() - start_time
        }
    
    # (3) Report 파일 확인
    report_path = Path(config.get("backtest", {}).get("output_file", "backtest_report.json"))
    if not report_path.is_absolute():
        report_path = run_dir / report_path.name
    
    metrics = {}
    report_path_final = None
    
    if report_path.exists():
        report_path_final = str(report_path)
        try:
            report_data = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = {
                "total_trades": report_data.get("total_trades", report_data.get("metrics", {}).get("total_trades", 0)),
                "loaded_candles": report_data.get("loaded_candles", report_data.get("metrics", {}).get("loaded_candles", 0)),
            }
        except Exception as e:
            logger.warning(f"⚠️ Report 파싱 실패: {e}")
    else:
        logger.warning(f"⚠️ Report 파일 없음: {report_path}")
    
    # (4) DB evidence 수집 (ITER25: qualified query)
    db_evidence = collect_db_evidence_iter25(trial_id)
    
    elapsed = time.time() - start_time
    
    logger.info(f"✅ {candidate_id} completed in {elapsed:.2f}s")
    logger.info(f"   DB trades: {db_evidence.get('total_trades', 0)}")
    logger.info(f"   Report path: {report_path_final}")
    
    return {
        "candidate_id": candidate_id,
        "trial_id": trial_id,
        "success": True,
        "metrics": metrics,
        "report_path": report_path_final,
        "db_evidence": db_evidence,
        "elapsed": elapsed
    }


def collect_db_evidence_iter25(trial_id: str) -> Dict[str, Any]:
    """
    DB evidence 수집 (ITER25: qualified query 통일)
    
    Args:
        trial_id: Trial ID
    
    Returns:
        {
            'trial_id': str,
            'total_trades': int,
            'closed_trades': int,
            'long_trades': int,
            'short_trades': int,
            'db_connection': 'SUCCESS' | 'FAILED'
        }
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Total trades (ITER25: qualified)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s",
                (trial_id,)
            )
            total_trades = cur.fetchone()[0]
            
            # Closed trades (ITER25: qualified)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND status = 'CLOSED'",
                (trial_id,)
            )
            closed_trades = cur.fetchone()[0]
            
            # Long/Short (ITER25: qualified)
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND side = 'LONG'",
                (trial_id,)
            )
            long_trades = cur.fetchone()[0]
            
            cur.execute(
                "SELECT COUNT(*) FROM trading.trades WHERE trial_id = %s AND side = 'SHORT'",
                (trial_id,)
            )
            short_trades = cur.fetchone()[0]
            
            cur.close()
        
        return {
            "trial_id": trial_id,
            "total_trades": total_trades,
            "closed_trades": closed_trades,
            "long_trades": long_trades,
            "short_trades": short_trades,
            "db_connection": "SUCCESS"
        }
    
    except Exception as e:
        logger.error(f"❌ DB evidence collection failed: {e}")
        return {
            "trial_id": trial_id,
            "total_trades": 0,
            "closed_trades": 0,
            "long_trades": 0,
            "short_trades": 0,
            "db_connection": f"FAILED: {type(e).__name__}"
        }


def check_ac(result: Dict[str, Any]) -> Dict[str, bool]:
    """
    AC 체크 (ITER25)
    
    AC1: trading.trades 테이블 존재 (introspection)
    AC2: L4 DB trades>0
    AC3: Report 파일 생성
    AC4: 실행 증거 저장
    
    Returns:
        AC 체크 결과
    """
    ac_results = {}
    
    # AC1: trades 테이블 존재 (introspection에서 확인)
    introspection_path = PROJECT_ROOT / "artifacts" / "phase35" / "iter25" / "db_introspection.json"
    ac1_pass = False
    if introspection_path.exists():
        try:
            introspection = json.loads(introspection_path.read_text(encoding="utf-8"))
            ac1_pass = introspection.get("introspection", {}).get("trades_trading_schema") is not None
        except:
            pass
    ac_results["ac1_trades_table_exists"] = ac1_pass
    
    # AC2: DB trades>0
    db_trades = result.get("db_evidence", {}).get("total_trades", 0)
    ac_results["ac2_l4_db_trades"] = db_trades > 0
    
    # AC3: Report 파일 생성
    report_path = result.get("report_path")
    ac_results["ac3_report_generated"] = report_path is not None and Path(report_path).exists()
    
    # AC4: 실행 증거 저장 (iter25_results.json)
    results_path = PROJECT_ROOT / "artifacts" / "phase35" / "iter25" / "iter25_results.json"
    ac_results["ac4_evidence_saved"] = results_path.exists()
    
    return ac_results


def run_iter25():
    """ITER25 메인 실행"""
    logger.info("=" * 80)
    logger.info("🚀 PHASE35-4 ITER25 Started")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # Git commit
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True
        ).strip()
        logger.info(f"📌 Git commit: {git_commit}")
    except:
        git_commit = "unknown"
    
    # Artifacts 디렉토리
    artifacts_dir = PROJECT_ROOT / "artifacts" / "phase35" / "iter25"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Artifacts: {artifacts_dir}")
    
    # (1) DB Introspection
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Step 1: DB Introspection")
    logger.info("=" * 80)
    
    from scripts.phase35.db_introspect_iter25 import introspect_db
    introspection_result = introspect_db()
    
    introspection_path = artifacts_dir / "db_introspection.json"
    with open(introspection_path, "w", encoding="utf-8") as f:
        json.dump(introspection_result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Introspection 저장: {introspection_path}")
    
    # (2) Trading Schema 확인/생성
    logger.info("\n" + "=" * 80)
    logger.info("🔧 Step 2: Ensure Trading Schema")
    logger.info("=" * 80)
    
    if not ensure_trading_schema():
        logger.error("❌ FAIL: Trading schema 생성 실패")
        sys.exit(1)
    
    # (3) L4 Backtest 실행
    logger.info("\n" + "=" * 80)
    logger.info("🏃 Step 3: Run L4_ultra_debug Backtest")
    logger.info("=" * 80)
    
    result = run_l4_backtest(lookback_days=7)
    
    # (4) AC 체크
    logger.info("\n" + "=" * 80)
    logger.info("📋 AC Results")
    logger.info("=" * 80)
    
    ac_results = check_ac(result)
    for ac, passed in ac_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   {ac}: {status}")
    
    # (5) 최종 결과 저장
    final_result = {
        "generated_at": datetime.utcnow().isoformat(),
        "git_commit": git_commit,
        "total_elapsed": time.time() - start_time,
        "l4_result": result,
        "ac_results": ac_results
    }
    
    results_path = artifacts_dir / "iter25_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "=" * 80)
    logger.info(f"🏁 ITER25 완료: {time.time() - start_time:.2f}초")
    logger.info(f"📁 Results: {results_path}")
    logger.info("=" * 80)
    
    # 최종 판정
    all_pass = all(ac_results.values())
    if all_pass:
        logger.info("✅ ITER25 PASS")
        sys.exit(0)
    else:
        logger.error("❌ ITER25 FAIL")
        sys.exit(1)


if __name__ == "__main__":
    run_iter25()
