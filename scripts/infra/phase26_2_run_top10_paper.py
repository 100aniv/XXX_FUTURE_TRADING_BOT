"""
PHASE26-2: Top10 Multi-Symbol PAPER Load Test Runner
======================================================
PHASE25-0 Long-run harness를 재사용하되, Multi-Symbol 메트릭 추가

핵심 변경:
1. Config 검증: universe 섹션 확인
2. Post-run 분석: Per-symbol 메트릭 수집
3. 리포트: Multi-Symbol 요약 추가

설계 원칙:
- PHASE25-0의 7단계 플로우 그대로 유지
- 최소 코드 추가 (Universe 검증 + Per-symbol 메트릭만)
- 100% 하위 호환 (Universe 없어도 단일 심볼 모드로 fallback)
"""

import sys
from pathlib import Path
from datetime import datetime
import yaml
import json

# PHASE25-0 harness 임포트
sys.path.insert(0, str(Path(__file__).parent))
from phase25_0_long_run_paper import (
    cleanup_environment,
    run_preflight_checks,
    run_clean_state,
    start_long_run,
    monitor_logs,
    analyze_results,
)

# Report 파일 경로 (PHASE26-2 전용)
REPORT_MD = Path(__file__).parent.parent.parent / "docs" / "PHASE26" / "PHASE26-2_TOP10_PAPER_TEST_REPORT.md"
SUMMARY_JSON = Path(__file__).parent.parent.parent / "docs" / "PHASE26" / "phase26_2_top10_paper_summary.json"


def validate_universe_config(config_path: str) -> bool:
    """
    Universe 설정 검증 (PHASE26-2 추가)
    
    Args:
        config_path: Config 파일 경로
    
    Returns:
        bool: 검증 성공 여부
    """
    print("\n[STEP 0] Universe Config 검증")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"  [ERROR] Config 로딩 실패: {e}")
        return False
    
    # universe 섹션 확인
    if 'universe' not in config:
        print("  [WARN] universe 섹션 없음 → 단일 심볼 모드로 fallback")
        return True  # Warning이지만 실행은 허용
    
    universe_cfg = config['universe']
    
    # enabled 확인
    if not universe_cfg.get('enabled', False):
        print("  [WARN] universe.enabled=false → 단일 심볼 모드")
        return True
    
    # provider type 확인
    provider_cfg = universe_cfg.get('provider', {})
    provider_type = provider_cfg.get('type')
    
    if provider_type not in ['static', 'topn_volume']:
        print(f"  [ERROR] 지원하지 않는 provider type: {provider_type}")
        return False
    
    # Provider 타입별 추가 검증
    if provider_type == 'static':
        static_symbols = provider_cfg.get('static_symbols', [])
        if not static_symbols:
            print(f"  [ERROR] static provider인데 static_symbols가 비어있음")
            return False
        print(f"  [OK] Universe Provider: static ({len(static_symbols)}개 심볼)")
    
    elif provider_type == 'topn_volume':
        top_n = provider_cfg.get('top_n', 0)
        if top_n <= 0:
            print(f"  [ERROR] topn_volume provider인데 top_n={top_n}")
            return False
        print(f"  [OK] Universe Provider: topn_volume (Top{top_n})")
    
    return True


def analyze_results_multi_symbol(start_time: datetime, end_time: datetime, config_path: str) -> dict:
    """
    Post-run 메트릭 수집 (PHASE26-2: Per-symbol 추가)
    
    Args:
        start_time: 실행 시작 시각
        end_time: 실행 종료 시각
        config_path: Config 파일 경로
    
    Returns:
        dict: 메트릭 딕셔너리 (기존 + multi_symbol)
    """
    print("\n[STEP 6] Post-run 분석 (Multi-Symbol 메트릭 포함)")
    
    # 기존 PHASE25-0 메트릭 수집
    metrics = analyze_results(start_time, end_time)
    
    # ⭐ Per-symbol 메트릭 추가
    try:
        import psycopg2
        import os
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5433')),
            database=os.getenv('DB_NAME', 'trading_db'),
            user=os.getenv('DB_USER', 'trading_user'),
            password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
        )
        
        with conn.cursor() as cur:
            # Symbol별 trade 카운트
            cur.execute(
                """
                SELECT symbol, COUNT(*) as trade_count
                FROM trading.trades
                WHERE ts_open >= %s AND ts_open <= %s
                GROUP BY symbol
                ORDER BY trade_count DESC;
                """,
                (start_time, end_time)
            )
            per_symbol_trades = {row[0]: row[1] for row in cur.fetchall()}
        
        conn.close()
        
        metrics['multi_symbol'] = {
            'symbol_count': len(per_symbol_trades),
            'per_symbol_trades': per_symbol_trades,
            'symbols': list(per_symbol_trades.keys())
        }
        
        print(f"  [OK] Multi-Symbol 메트릭: {len(per_symbol_trades)}개 심볼")
        for symbol, count in list(per_symbol_trades.items())[:5]:  # Top 5만 출력
            print(f"    - {symbol}: {count} trades")
    
    except Exception as e:
        print(f"  [WARN] Multi-Symbol 메트릭 수집 실패: {e}")
        metrics['multi_symbol'] = {'error': str(e)}
    
    return metrics


def save_report_multi_symbol(metrics: dict, config_path: str, duration_hours: float, monitor_result: dict):
    """
    리포트 저장 (PHASE26-2: Multi-Symbol 섹션 추가)
    
    Args:
        metrics: 메트릭 딕셔너리
        config_path: Config 파일 경로
        duration_hours: 실행 시간 (hours)
        monitor_result: 모니터링 결과
    """
    print("\n[STEP 7] 결과 저장 (Multi-Symbol 리포트)")
    
    # MD 리포트 생성
    try:
        REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
        
        with open(REPORT_MD, 'w', encoding='utf-8') as f:
            f.write("# PHASE26-2: Top10 Multi-Symbol PAPER Load Test - Execution Report\n\n")
            f.write(f"**작성일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**상태**: {monitor_result['status']}\n")
            f.write(f"**Config**: `{Path(config_path).name}`\n\n")
            f.write("---\n\n")
            
            # PHASE25-0 기본 메트릭
            f.write("## 기본 실행 메트릭\n\n")
            f.write(f"- **실행 시간**: {duration_hours:.2f}H (target)\n")
            f.write(f"- **실제 Duration**: {metrics.get('db', {}).get('actual_duration', 'N/A')}\n")
            f.write(f"- **Total Trades**: {metrics.get('db', {}).get('trade_count', 0)}건\n")
            f.write(f"- **Active Positions**: {metrics.get('db', {}).get('active_positions', 0)}건\n")
            f.write(f"- **ERROR Count**: {monitor_result.get('error_count', 0)}건\n")
            f.write(f"- **CRITICAL Count**: {monitor_result.get('critical_count', 0)}건\n\n")
            
            # ⭐ Multi-Symbol 메트릭
            multi_metrics = metrics.get('multi_symbol', {})
            
            if 'error' not in multi_metrics:
                f.write("---\n\n")
                f.write("## PHASE26-2: Multi-Symbol 메트릭\n\n")
                f.write(f"- **심볼 수**: {multi_metrics.get('symbol_count', 0)}개\n")
                
                symbols_str = ', '.join(multi_metrics.get('symbols', []))
                f.write(f"- **심볼 목록**: {symbols_str}\n\n")
                
                f.write("### Per-Symbol Trade 카운트\n\n")
                f.write("| Symbol | Trade Count |\n")
                f.write("|--------|-------------|\n")
                
                per_symbol = multi_metrics.get('per_symbol_trades', {})
                if per_symbol:
                    for symbol, count in per_symbol.items():
                        f.write(f"| {symbol} | {count} |\n")
                else:
                    f.write("| (Empty) | 0 |\n")
                
                f.write("\n")
            else:
                f.write("---\n\n")
                f.write("## Multi-Symbol 메트릭 수집 실패\n\n")
                f.write(f"**오류**: {multi_metrics['error']}\n\n")
            
            # 판정 섹션
            f.write("---\n\n")
            f.write("## 판정\n\n")
            
            if monitor_result['status'] == 'PASS':
                f.write("✅ **PASS**: 모든 Acceptance Criteria 충족\n\n")
            else:
                f.write("❌ **FAIL**: Acceptance Criteria 미충족\n\n")
                f.write("**실패 사유**:\n")
                for reason in monitor_result.get('fail_reasons', []):
                    f.write(f"- {reason}\n")
                f.write("\n")
        
        print(f"  [OK] MD 리포트 저장: {REPORT_MD}")
    
    except Exception as e:
        print(f"  [ERROR] MD 리포트 저장 실패: {e}")
    
    # JSON 요약 저장
    try:
        summary = {
            'timestamp': datetime.now().isoformat(),
            'config_path': str(config_path),
            'duration_hours': duration_hours,
            'status': monitor_result['status'],
            'metrics': metrics,
            'monitor_result': monitor_result
        }
        
        with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"  [OK] JSON 요약 저장: {SUMMARY_JSON}")
    
    except Exception as e:
        print(f"  [ERROR] JSON 요약 저장 실패: {e}")


def main():
    """Main orchestrator (PHASE25-0 플로우 재사용)"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PHASE26-2: Top10 Multi-Symbol PAPER Load Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python scripts/infra/phase26_2_run_top10_paper.py \\
      --config configs/paper/phase26_2_top10_paper_2h.yml \\
      --duration-hours 2.0 \\
      --tag "PHASE26-2_ACCEPTANCE"
        """
    )
    parser.add_argument("--config", required=True, help="Config 파일 경로")
    parser.add_argument("--duration-hours", type=float, default=2.0, help="실행 시간 (hours)")
    parser.add_argument("--tag", default=None, help="Run 태그 (선택)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("PHASE26-2: Top10 Multi-Symbol PAPER Load Test")
    print("=" * 80)
    print(f"Config: {args.config}")
    print(f"Duration: {args.duration_hours}H")
    print(f"Tag: {args.tag or '(None)'}")
    print("=" * 80)
    
    # STEP 0: Universe Config 검증 (PHASE26-2 추가)
    if not validate_universe_config(args.config):
        print("\n❌ [FAIL] Universe Config 검증 실패")
        return 1
    
    # STEP 1: 환경 정리
    if not cleanup_environment():
        print("\n❌ [FAIL] 환경 정리 실패")
        return 1
    
    # STEP 2: Pre-flight Check
    if not run_preflight_checks(args.config):
        print("\n❌ [FAIL] Pre-flight Check 실패")
        return 1
    
    # STEP 3: Clean State
    if not run_clean_state():
        print("\n❌ [FAIL] Clean State 실패")
        return 1
    
    # STEP 4: Long-run 실행
    start_time = datetime.now()
    process = start_long_run(args.config, args.duration_hours, args.tag)
    
    if process is None:
        print("\n❌ [FAIL] Long-run 실행 실패")
        return 1
    
    # STEP 5: 실시간 모니터링
    monitor_result = monitor_logs(args.duration_hours * 3600, start_time)
    end_time = datetime.now()
    
    # STEP 6: Post-run 분석 (Multi-Symbol 메트릭 포함)
    metrics = analyze_results_multi_symbol(start_time, end_time, args.config)
    
    # STEP 7: 결과 저장 (Multi-Symbol 섹션 추가)
    save_report_multi_symbol(metrics, args.config, args.duration_hours, monitor_result)
    
    # Exit code
    if monitor_result['status'] == 'PASS':
        print("\n✅ PHASE26-2 Top10 PAPER Test: PASS")
        return 0
    else:
        print("\n❌ PHASE26-2 Top10 PAPER Test: FAIL")
        return 1


if __name__ == '__main__':
    sys.exit(main())
