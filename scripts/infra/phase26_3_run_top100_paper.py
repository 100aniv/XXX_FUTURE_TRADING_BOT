"""
PHASE26-3: Top100 Multi-Symbol PAPER Performance Test Runner
=============================================================
PHASE26-2 harness를 재사용하되, 성능 프로파일링 및 단계별 실행 추가

핵심 기능:
1. 단계별 실행: Top10 → Top20 → Top50 → Top100
2. 성능 프로파일링: Loop latency, Indicator latency, CPU/메모리
3. 자동 분석: Hot path 감지, 성능 비교
4. 리포트 생성: MD + JSON

설계 원칙:
- PHASE26-2의 7단계 플로우 재사용
- 최소 코드 추가 (프로파일링 통합만)
- 100% 하위 호환
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import yaml
import json
import argparse
import time

# PHASE26-2 harness 임포트
sys.path.insert(0, str(Path(__file__).parent))
from phase26_2_run_top10_paper import (
    validate_universe_config,
    analyze_results_multi_symbol,
)

# PHASE25-0 harness 임포트
from phase25_0_long_run_paper import (
    cleanup_environment,
    run_preflight_checks,
    run_clean_state,
    start_long_run,
    monitor_logs,
)

# Report 파일 경로 (PHASE26-3 전용)
REPORT_MD = Path(__file__).parent.parent.parent / "docs" / "PHASE26" / "PHASE26-3_PERFORMANCE_TEST_REPORT.md"
SUMMARY_JSON = Path(__file__).parent.parent.parent / "docs" / "PHASE26" / "phase26_3_top100_performance_summary.json"


def run_single_test(
    config_path: str,
    top_n: int,
    duration_minutes: float,
    tag: str,
    enable_profiling: bool = True
) -> dict:
    """
    단일 Top-N 테스트 실행
    
    Args:
        config_path: Base config 파일 경로
        top_n: Top-N 심볼 수 (10, 20, 50, 100)
        duration_minutes: 실행 시간 (분)
        tag: 실행 태그
        enable_profiling: 프로파일링 활성화 여부
    
    Returns:
        dict: 실행 결과 요약
    """
    print("\n" + "=" * 80)
    print(f"  PHASE26-3: Top{top_n} Multi-Symbol PAPER Performance Test")
    print("=" * 80)
    
    # Config 로딩 및 수정
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] Config 로딩 실패: {e}")
        return {"status": "error", "error": str(e)}
    
    # Universe provider top_n 변경
    if 'universe' in config and config['universe'].get('enabled', False):
        config['universe']['provider']['top_n'] = top_n
    else:
        print(f"[WARN] universe 설정 없음, Top{top_n} 적용 불가")
    
    # Duration 변경
    duration_hours = duration_minutes / 60.0
    config['paper']['duration_hours'] = duration_hours
    
    # run_id 변경
    config['run_id'] = f"PHASE26-3_top{top_n}_{tag}"
    
    # Profiling 설정
    if 'performance' not in config:
        config['performance'] = {}
    config['performance']['profiling_enabled'] = enable_profiling
    config['performance']['profiler_output'] = f"docs/PHASE26/phase26_3_top{top_n}_profile.json"
    
    # 임시 config 저장
    temp_config_path = Path(config_path).parent / f"phase26_3_top{top_n}_temp.yml"
    try:
        with open(temp_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"[ERROR] 임시 config 저장 실패: {e}")
        return {"status": "error", "error": str(e)}
    
    print(f"\n[Top{top_n}] Config 준비 완료: {temp_config_path}")
    
    # STEP 0: Universe Config 검증
    if not validate_universe_config(str(temp_config_path)):
        print(f"[ERROR] Universe config 검증 실패")
        return {"status": "error", "error": "Universe config 검증 실패"}
    
    # STEP 1: Environment Cleanup
    print(f"\n[STEP 1] Environment Cleanup")
    cleanup_environment()
    
    # STEP 2: Preflight Checks
    print(f"\n[STEP 2] Preflight Checks")
    if not run_preflight_checks(str(temp_config_path)):
        print(f"[ERROR] Preflight checks 실패")
        return {"status": "error", "error": "Preflight checks 실패"}
    
    # STEP 3: Clean State
    print(f"\n[STEP 3] Clean State")
    run_clean_state()
    
    # STEP 4: Start Long-run
    print(f"\n[STEP 4] Start Long-run (Top{top_n}, {duration_minutes}분)")
    start_time = datetime.now()
    process = start_long_run(str(temp_config_path), duration_hours)
    
    if not process:
        print(f"[ERROR] 엔진 시작 실패")
        return {"status": "error", "error": "엔진 시작 실패"}
    
    # STEP 5: Monitor Logs
    print(f"\n[STEP 5] Monitor Logs (실시간)")
    target_duration_sec = duration_hours * 3600
    monitor_result = monitor_logs(target_duration_sec, start_time)
    error_count = monitor_result.get("error_count", 0)
    
    end_time = datetime.now()
    
    # STEP 6: Analyze Results
    print(f"\n[STEP 6] Analyze Results")
    analysis = analyze_results_multi_symbol(start_time, end_time, str(temp_config_path))
    
    # Profiling 데이터 로딩 또는 기본 메트릭 생성
    profiling_data = None
    if enable_profiling:
        profiler_output = config['performance'].get('profiler_output')
        if profiler_output and Path(profiler_output).exists():
            try:
                with open(profiler_output, 'r', encoding='utf-8') as f:
                    profiling_data = json.load(f)
                print(f"  [OK] 프로파일링 데이터 로딩: {profiler_output}")
            except Exception as e:
                print(f"  [WARN] 프로파일링 데이터 로딩 실패: {e}")
        else:
            # PHASE26-3: 기본 메트릭 생성 (엔진 통합 프로파일링은 PHASE27 이후)
            print(f"  [INFO] 프로파일링 파일 없음 - 기본 메트릭 생성")
            elapsed_sec = (end_time - start_time).total_seconds()
            profiling_data = {
                "note": "Basic metrics only. Full profiling integration planned for PHASE27",
                "runtime_sec": elapsed_sec,
                "runtime_minutes": elapsed_sec / 60.0,
                "top_n": top_n,
                "config_path": str(temp_config_path),
                "timestamp": datetime.now().isoformat()
            }
            print(f"  [OK] 기본 메트릭 생성 완료")
    
    # 결과 요약
    result = {
        "status": "success",
        "top_n": top_n,
        "duration_minutes": duration_minutes,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "elapsed_minutes": (end_time - start_time).total_seconds() / 60.0,
        "error_count": error_count,
        "analysis": analysis,
        "profiling": profiling_data,
    }
    
    # 임시 config 삭제
    try:
        temp_config_path.unlink()
    except:
        pass
    
    return result


def run_scaling_test(
    base_config_path: str,
    duration_minutes: float = 30.0,
    tag: str = None,
    top_n_stages: list = None
) -> dict:
    """
    단계별 Scaling Test 실행 (Top10 → Top20 → Top50 → Top100)
    
    Args:
        base_config_path: Base config 파일 경로
        duration_minutes: 각 단계당 실행 시간 (분)
        tag: 실행 태그
        top_n_stages: Top-N 단계 리스트 (None이면 [10, 20, 50, 100])
    
    Returns:
        dict: 전체 실행 결과
    """
    if tag is None:
        tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if top_n_stages is None:
        top_n_stages = [10, 20, 50, 100]
    
    print("\n" + "=" * 80)
    print("  PHASE26-3: Multi-Symbol Scaling Test")
    print("  단계별 실행:", " → ".join([f"Top{n}" for n in top_n_stages]))
    print("  각 단계 실행 시간:", f"{duration_minutes}분")
    print("=" * 80)
    
    overall_start = datetime.now()
    results = []
    
    for top_n in top_n_stages:
        print(f"\n{'='*80}")
        print(f"  [Stage {len(results)+1}/{len(top_n_stages)}] Top{top_n} 실행 시작")
        print(f"{'='*80}")
        
        result = run_single_test(
            base_config_path,
            top_n=top_n,
            duration_minutes=duration_minutes,
            tag=tag,
            enable_profiling=True
        )
        
        results.append(result)
        
        if result["status"] != "success":
            print(f"\n[ERROR] Top{top_n} 실행 실패, Scaling Test 중단")
            break
        
        # 다음 단계 전 대기 (리소스 정리)
        if top_n != top_n_stages[-1]:
            print(f"\n[INFO] 다음 단계 준비 중... (10초 대기)")
            time.sleep(10)
    
    overall_end = datetime.now()
    
    # 전체 요약
    summary = {
        "test_type": "scaling_test",
        "tag": tag,
        "start_time": overall_start.isoformat(),
        "end_time": overall_end.isoformat(),
        "total_elapsed_minutes": (overall_end - overall_start).total_seconds() / 60.0,
        "stages": results,
        "success_stages": sum(1 for r in results if r["status"] == "success"),
        "total_stages": len(top_n_stages),
    }
    
    # 성능 비교 분석
    if len(results) >= 2:
        summary["performance_comparison"] = analyze_performance_scaling(results)
    
    return summary


def analyze_performance_scaling(results: list) -> dict:
    """
    단계별 성능 비교 분석
    
    Args:
        results: run_single_test 결과 리스트
    
    Returns:
        dict: 성능 비교 데이터
    """
    comparison = {
        "latency_trend": [],
        "cpu_trend": [],
        "memory_trend": [],
        "trade_activity_trend": [],
    }
    
    for result in results:
        if result["status"] != "success":
            continue
        
        top_n = result["top_n"]
        profiling = result.get("profiling")
        analysis = result.get("analysis", {})
        
        # Loop latency (profiling에서)
        if profiling and "summary" in profiling:
            loop_latencies = profiling["summary"].get("loop_latencies", {})
            if loop_latencies:
                # 전체 심볼의 평균 latency
                avg_latencies = [v["avg_ms"] for v in loop_latencies.values()]
                overall_avg = sum(avg_latencies) / len(avg_latencies) if avg_latencies else 0
                
                comparison["latency_trend"].append({
                    "top_n": top_n,
                    "avg_loop_latency_ms": round(overall_avg, 2)
                })
        
        # CPU/메모리 (profiling에서)
        if profiling and "summary" in profiling:
            sys_resources = profiling["summary"].get("system_resources", {})
            if "cpu" in sys_resources:
                comparison["cpu_trend"].append({
                    "top_n": top_n,
                    "avg_cpu_percent": sys_resources["cpu"]["avg_percent"]
                })
            if "memory" in sys_resources:
                comparison["memory_trend"].append({
                    "top_n": top_n,
                    "avg_memory_mb": sys_resources["memory"]["avg_mb"]
                })
        
        # Trade activity (analysis에서)
        if analysis:
            comparison["trade_activity_trend"].append({
                "top_n": top_n,
                "total_trades": analysis.get("total_trades", 0),
                "active_symbols": analysis.get("active_symbols", 0),
            })
    
    return comparison


def save_scaling_report(summary: dict, output_md: Path, output_json: Path):
    """
    Scaling Test 리포트 저장
    
    Args:
        summary: run_scaling_test 결과
        output_md: MD 리포트 출력 경로
        output_json: JSON 요약 출력 경로
    """
    # JSON 저장
    try:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] JSON 요약 저장: {output_json}")
    except Exception as e:
        print(f"\n[ERROR] JSON 저장 실패: {e}")
    
    # MD 리포트 생성
    try:
        md_content = generate_scaling_report_md(summary)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_content, encoding='utf-8')
        print(f"[OK] MD 리포트 저장: {output_md}")
    except Exception as e:
        print(f"[ERROR] MD 리포트 저장 실패: {e}")


def generate_scaling_report_md(summary: dict) -> str:
    """
    Scaling Test MD 리포트 생성
    
    Args:
        summary: run_scaling_test 결과
    
    Returns:
        str: MD 리포트 내용
    """
    lines = []
    lines.append("# PHASE26-3: Multi-Symbol Scaling Test Report")
    lines.append(f"\n**실행 태그**: {summary['tag']}")
    lines.append(f"**실행 시작**: {summary['start_time']}")
    lines.append(f"**실행 종료**: {summary['end_time']}")
    lines.append(f"**총 실행 시간**: {summary['total_elapsed_minutes']:.1f}분")
    lines.append(f"**성공 단계**: {summary['success_stages']}/{summary['total_stages']}")
    lines.append("\n---\n")
    
    # 단계별 결과
    lines.append("## 단계별 실행 결과\n")
    for i, result in enumerate(summary['stages'], 1):
        top_n = result['top_n']
        status = result['status']
        lines.append(f"### Stage {i}: Top{top_n}\n")
        lines.append(f"- **상태**: {status}")
        lines.append(f"- **실행 시간**: {result.get('elapsed_minutes', 0):.1f}분")
        lines.append(f"- **에러 수**: {result.get('error_count', 0)}건\n")
        
        if status == "success" and 'analysis' in result:
            analysis = result['analysis']
            lines.append(f"- **Trade 수**: {analysis.get('total_trades', 0)}건")
            lines.append(f"- **활성 심볼**: {analysis.get('active_symbols', 0)}개\n")
    
    lines.append("\n---\n")
    
    # 성능 비교
    if 'performance_comparison' in summary:
        comp = summary['performance_comparison']
        lines.append("## 성능 비교 분석\n")
        
        # Latency Trend
        if comp['latency_trend']:
            lines.append("### Loop Latency 추세\n")
            lines.append("| Top-N | 평균 Latency (ms) |")
            lines.append("|-------|-------------------|")
            for item in comp['latency_trend']:
                lines.append(f"| Top{item['top_n']} | {item['avg_loop_latency_ms']} |")
            lines.append("")
        
        # CPU Trend
        if comp['cpu_trend']:
            lines.append("### CPU 사용률 추세\n")
            lines.append("| Top-N | 평균 CPU (%) |")
            lines.append("|-------|--------------|")
            for item in comp['cpu_trend']:
                lines.append(f"| Top{item['top_n']} | {item['avg_cpu_percent']} |")
            lines.append("")
        
        # Memory Trend
        if comp['memory_trend']:
            lines.append("### 메모리 사용량 추세\n")
            lines.append("| Top-N | 평균 메모리 (MB) |")
            lines.append("|-------|------------------|")
            for item in comp['memory_trend']:
                lines.append(f"| Top{item['top_n']} | {item['avg_memory_mb']} |")
            lines.append("")
        
        # Trade Activity
        if comp['trade_activity_trend']:
            lines.append("### Trade Activity 추세\n")
            lines.append("| Top-N | 총 Trade | 활성 심볼 |")
            lines.append("|-------|----------|-----------|")
            for item in comp['trade_activity_trend']:
                lines.append(f"| Top{item['top_n']} | {item['total_trades']} | {item['active_symbols']} |")
            lines.append("")
    
    lines.append("\n---\n")
    lines.append(f"\n**리포트 생성 시각**: {datetime.now().isoformat()}")
    
    return "\n".join(lines)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PHASE26-3: Top100 Multi-Symbol PAPER Performance Test")
    parser.add_argument("--config", required=True, help="Base config 파일 경로")
    parser.add_argument("--duration-minutes", type=float, default=30.0, help="각 단계 실행 시간 (분)")
    parser.add_argument("--tag", default=None, help="실행 태그")
    parser.add_argument("--mode", choices=["single", "scaling"], default="scaling", 
                        help="실행 모드 (single: Top100만, scaling: Top10→20→50→100)")
    parser.add_argument("--top-n", type=int, default=100, help="single 모드 시 Top-N 값")
    
    args = parser.parse_args()
    
    if args.mode == "single":
        # Single Top-N 실행
        result = run_single_test(
            args.config,
            top_n=args.top_n,
            duration_minutes=args.duration_minutes,
            tag=args.tag or datetime.now().strftime("%Y%m%d_%H%M%S"),
            enable_profiling=True
        )
        
        print(f"\n{'='*80}")
        print(f"  Top{args.top_n} 실행 완료: {result['status']}")
        print(f"{'='*80}\n")
        
        # 개별 리포트 저장
        output_md = Path(f"docs/PHASE26/phase26_3_top{args.top_n}_report.md")
        output_json = Path(f"docs/PHASE26/phase26_3_top{args.top_n}_summary.json")
        
        try:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"[OK] 결과 저장: {output_json}")
        except Exception as e:
            print(f"[ERROR] 결과 저장 실패: {e}")
    
    else:
        # Scaling Test 실행
        summary = run_scaling_test(
            args.config,
            duration_minutes=args.duration_minutes,
            tag=args.tag
        )
        
        print(f"\n{'='*80}")
        print(f"  Scaling Test 완료: {summary['success_stages']}/{summary['total_stages']} 성공")
        print(f"{'='*80}\n")
        
        # 리포트 저장
        save_scaling_report(summary, REPORT_MD, SUMMARY_JSON)


if __name__ == "__main__":
    main()
