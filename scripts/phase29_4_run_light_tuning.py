"""
PHASE29-4: V4 경량 파라미터 튜닝 스크립트

목적: 24개 파라미터 조합에 대해 1개월 백테스트 실행 및 결과 수집
"""

import sys
from pathlib import Path
import yaml
import json
import subprocess
from datetime import datetime
import copy

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_tuning_configs():
    """튜닝 Config 조합 생성"""
    
    # Base Config 로드 (Gate Config 기반)
    base_config_path = project_root / "configs" / "backtest" / "phase29_4_0_btc5m_baseline_v4_month_gate.yml"
    
    with open(base_config_path, "r", encoding="utf-8") as f:
        base_config = yaml.safe_load(f)
    
    # 튜닝 파라미터 Grid (24개 조합)
    range_min_scores = [2, 3, 4]  # 3개
    trend_min_scores = [2, 3]  # 2개
    min_rr_requireds = [1.0, 1.2]  # 2개
    cooldown_candles_list = [0, 1]  # 2개
    # 총 3 × 2 × 2 × 2 = 24개
    
    configs = []
    
    for range_score in range_min_scores:
        for trend_score in trend_min_scores:
            for min_rr in min_rr_requireds:
                for cooldown in cooldown_candles_list:
                    # Config 복사
                    config = copy.deepcopy(base_config)
                    
                    # run_id 생성
                    run_id = f"phase29_4_tuning_r{range_score}_t{trend_score}_rr{min_rr}_cd{cooldown}"
                    config["run_id"] = run_id
                    
                    # Score Threshold 설정
                    config["strategies"]["btc5m_baseline_v4"]["range_min_score"] = range_score
                    config["strategies"]["btc5m_baseline_v4"]["trend_min_score"] = trend_score
                    
                    # Guard 설정
                    config["entries"]["min_rr_required"] = min_rr
                    config["entries"]["cooldown_candles"] = cooldown
                    
                    # Output file 설정
                    config["backtest"]["output_file"] = f"reports/backtest/phase29_4_1/{run_id}_summary.json"
                    config["trade_activity_tracker"]["output_file"] = f"reports/backtest/phase29_4_1/{run_id}_summary.json"
                    
                    # Config 저장
                    config_path = project_root / "configs" / "backtest" / f"{run_id}.yml"
                    
                    with open(config_path, "w", encoding="utf-8") as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                    
                    configs.append({
                        "run_id": run_id,
                        "config_path": str(config_path),
                        "range_min_score": range_score,
                        "trend_min_score": trend_score,
                        "min_rr_required": min_rr,
                        "cooldown_candles": cooldown
                    })
                    
                    print(f"✅ Config 생성: {run_id}")
    
    return configs


def run_backtest(config_path):
    """백테스트 실행"""
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_backtest.py"),
        "--config",
        config_path
    ]
    
    print(f"  실행 명령: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=600  # 10분 타임아웃
        )
        
        if result.returncode == 0:
            return True, "SUCCESS"
        else:
            return False, f"ERROR: {result.stderr[:500]}"
    
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (10분 초과)"
    
    except Exception as e:
        return False, f"EXCEPTION: {str(e)}"


def collect_results(configs):
    """백테스트 결과 수집"""
    
    results = []
    
    for config in configs:
        run_id = config["run_id"]
        summary_path = project_root / "reports" / "backtest" / "phase29_4_1" / f"{run_id}_summary.json"
        
        if not summary_path.exists():
            print(f"❌ Summary JSON 없음: {run_id}")
            results.append({
                "run_id": run_id,
                "range_min_score": config["range_min_score"],
                "trend_min_score": config["trend_min_score"],
                "min_rr_required": config["min_rr_required"],
                "cooldown_candles": config["cooldown_candles"],
                "status": "MISSING_JSON",
                "orders_submitted": 0,
                "signal_true": 0,
                "guard_blocks_total": 0
            })
            continue
        
        # Summary JSON 로드
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        
        totals = summary.get("totals", {})
        
        result = {
            "run_id": run_id,
            "range_min_score": config["range_min_score"],
            "trend_min_score": config["trend_min_score"],
            "min_rr_required": config["min_rr_required"],
            "cooldown_candles": config["cooldown_candles"],
            "status": "SUCCESS",
            "orders_submitted": totals.get("orders_submitted", 0),
            "signal_true": totals.get("strategy_signals_true", 0),
            "guard_blocks_total": totals.get("guard_blocks_total", 0),
            "long_signals": totals.get("long_signals", 0),
            "short_signals": totals.get("short_signals", 0),
            "regime_range": totals.get("regime_range", 0),
            "regime_trend": totals.get("regime_trend", 0),
            "guard_pass_rate": (totals.get("orders_submitted", 0) / totals.get("strategy_signals_true", 1)) * 100
        }
        
        results.append(result)
        
        print(f"✅ 결과 수집: {run_id} → {result['orders_submitted']}건 체결")
    
    return results


def save_tuning_results(results):
    """튜닝 결과 저장"""
    
    output_path = project_root / "tuning_results" / "phase29_4_v4_light_tuning.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    tuning_data = {
        "timestamp": datetime.now().isoformat(),
        "total_configs": len(results),
        "results": results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tuning_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 튜닝 결과 저장: {output_path}")
    
    return output_path


def main():
    """메인 함수"""
    
    print("=" * 80)
    print("PHASE29-4: V4 경량 파라미터 튜닝")
    print("=" * 80)
    print()
    
    # 출력 디렉토리 생성
    output_dir = project_root / "reports" / "backtest" / "phase29_4_1"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # STEP 1: Config 생성
    print("=" * 80)
    print("STEP 1: 튜닝 Config 생성 (24개 조합)")
    print("=" * 80)
    print()
    print("  range_min_score: {2, 3, 4} (3개)")
    print("  trend_min_score: {2, 3} (2개)")
    print("  min_rr_required: {1.0, 1.2} (2개)")
    print("  cooldown_candles: {0, 1} (2개)")
    print("  총 조합: 3 × 2 × 2 × 2 = 24개")
    print()
    
    configs = generate_tuning_configs()
    
    print(f"\n✅ Config 생성 완료: {len(configs)}개\n")
    
    # STEP 2: 백테스트 실행
    print("=" * 80)
    print("STEP 2: 백테스트 실행 (24개)")
    print("=" * 80)
    print()
    print("  예상 시간: ~120분 (각 5분 × 24개)")
    print()
    
    for i, config in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}] {config['run_id']}")
        print(f"  Range Score: {config['range_min_score']}, Trend Score: {config['trend_min_score']}")
        print(f"  min_rr: {config['min_rr_required']}, cooldown: {config['cooldown_candles']}")
        
        success, message = run_backtest(config['config_path'])
        
        if success:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")
    
    print("\n✅ 백테스트 실행 완료\n")
    
    # STEP 3: 결과 수집
    print("=" * 80)
    print("STEP 3: 결과 수집")
    print("=" * 80)
    print()
    
    results = collect_results(configs)
    
    # STEP 4: 결과 저장
    print("\n" + "=" * 80)
    print("STEP 4: 결과 저장")
    print("=" * 80)
    print()
    
    output_path = save_tuning_results(results)
    
    # 요약 출력
    print("\n" + "=" * 80)
    print("📊 튜닝 결과 요약")
    print("=" * 80)
    print()
    
    valid_results = [r for r in results if r["status"] == "SUCCESS"]
    
    if valid_results:
        print(f"  성공: {len(valid_results)}개")
        print(f"  실패: {len(results) - len(valid_results)}개")
        print()
        print("  Top 3 (체결 건수 기준):")
        sorted_results = sorted(valid_results, key=lambda x: x["orders_submitted"], reverse=True)
        for i, r in enumerate(sorted_results[:3], 1):
            print(f"    {i}. {r['run_id']}: {r['orders_submitted']}건")
            print(f"       (Range: {r['range_min_score']}, Trend: {r['trend_min_score']}, RR: {r['min_rr_required']}, CD: {r['cooldown_candles']})")
    else:
        print("  ❌ 성공한 백테스트 없음")
    
    print("\n" + "=" * 80)
    print("✅ 경량 튜닝 완료!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
