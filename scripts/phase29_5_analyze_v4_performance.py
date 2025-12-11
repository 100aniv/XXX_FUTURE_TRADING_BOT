#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-5: V4 Performance Metrics Analysis
===========================================

목적:
- V4 1M + 24개 튜닝 결과의 성능 지표 분석
- Win Rate / Max DD / PnL / Sharpe 기반 랭킹
- AC3 기준 (Win Rate >= 45%, Max DD <= 15%) 평가

입력:
- reports/backtest/phase29_4_0/*.json (1M Gate/Baseline)
- reports/backtest/phase29_4_1/*.json (24개 튜닝)

출력:
- reports/analysis/PHASE29/phase29_5_v4_performance.json
- reports/analysis/PHASE29/phase29_5_v4_performance.md

Usage:
    python scripts/phase29_5_analyze_v4_performance.py
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 1. Data Loading
# ============================================================

def load_summary_jsons(phase29_4_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    PHASE29-4 백테스트 결과 로드
    
    Args:
        phase29_4_dir: phase29_4_0 또는 phase29_4_1 디렉토리
    
    Returns:
        {run_id: summary_data} 딕셔너리
    """
    results = {}
    
    if not phase29_4_dir.exists():
        print(f"⚠️ 디렉토리 없음: {phase29_4_dir}")
        return results
    
    summary_files = list(phase29_4_dir.glob("*_summary.json"))
    
    for summary_file in summary_files:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            run_id = data.get('run_id', summary_file.stem.replace('_summary', ''))
            results[run_id] = data
            
        except Exception as e:
            print(f"⚠️ 파일 로드 실패: {summary_file.name} - {e}")
    
    return results


# ============================================================
# 2. Performance Analysis
# ============================================================

def extract_performance_metrics(summary_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summary JSON에서 Performance 지표 추출
    
    Args:
        summary_data: Summary JSON 데이터
    
    Returns:
        Performance 지표 딕셔너리
    """
    performance = summary_data.get('performance', {})
    
    # 기본값 설정 (performance 블록이 없거나 빈 경우)
    return {
        'num_trades': performance.get('num_trades', 0),
        'pnl_total': performance.get('pnl_total', 0.0),
        'pnl_avg_per_trade': performance.get('pnl_avg_per_trade', 0.0),
        'win_rate': performance.get('win_rate', 0.0),
        'max_drawdown': performance.get('max_drawdown', 0.0),
        'max_drawdown_abs': performance.get('max_drawdown_abs', 0.0),
        'sharpe_ratio': performance.get('sharpe_ratio'),
        'profit_factor': performance.get('profit_factor', 0.0),
        'roi': performance.get('roi', 0.0),
        'num_wins': performance.get('num_wins', 0),
        'num_losses': performance.get('num_losses', 0),
        'max_consecutive_losses': performance.get('max_consecutive_losses', 0),
    }


def parse_tuning_params(run_id: str) -> Dict[str, Any]:
    """
    Run ID에서 튜닝 파라미터 추출
    
    예: phase29_4_tuning_r2_t3_rr1.2_cd1
    → {range_min_score: 2, trend_min_score: 3, min_rr_required: 1.2, cooldown_candles: 1}
    
    Args:
        run_id: Run ID 문자열
    
    Returns:
        튜닝 파라미터 딕셔너리
    """
    params = {}
    
    # 기본 패턴 파싱
    if 'tuning_r' in run_id:
        parts = run_id.split('_')
        for part in parts:
            if part.startswith('r') and part[1:].isdigit():
                params['range_min_score'] = int(part[1:])
            elif part.startswith('t') and part[1:].isdigit():
                params['trend_min_score'] = int(part[1:])
            elif part.startswith('rr'):
                params['min_rr_required'] = float(part[2:])
            elif part.startswith('cd') and part[2:].isdigit():
                params['cooldown_candles'] = int(part[2:])
    
    return params


def evaluate_ac3_criteria(perf: Dict[str, Any]) -> Dict[str, Any]:
    """
    AC3 기준 평가 (Win Rate >= 45%, Max DD <= 15%)
    
    Args:
        perf: Performance 지표 딕셔너리
    
    Returns:
        {pass: bool, win_rate_pass: bool, max_dd_pass: bool, comments: str}
    """
    win_rate = perf['win_rate']
    max_dd = perf['max_drawdown']
    
    win_rate_pass = win_rate >= 0.45  # 45%
    max_dd_pass = max_dd <= 0.15  # 15%
    
    comments = []
    if not win_rate_pass:
        comments.append(f"Win Rate {win_rate*100:.1f}% < 45%")
    if not max_dd_pass:
        comments.append(f"Max DD {max_dd*100:.1f}% > 15%")
    
    ac3_pass = win_rate_pass and max_dd_pass
    
    return {
        'pass': ac3_pass,
        'win_rate_pass': win_rate_pass,
        'max_dd_pass': max_dd_pass,
        'comments': ' | '.join(comments) if comments else 'PASS'
    }


# ============================================================
# 3. Ranking & Sorting
# ============================================================

def rank_combinations(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    성능 지표 기반 랭킹
    
    정렬 기준:
    1. AC3 통과 여부 (PASS 우선)
    2. Sharpe Ratio (높을수록 우선)
    3. PnL Total (높을수록 우선)
    4. Max DD (낮을수록 우선)
    
    Args:
        results: 결과 리스트
    
    Returns:
        정렬된 결과 리스트
    """
    def sort_key(item):
        perf = item['performance']
        ac3 = item['ac3_evaluation']
        
        # AC3 통과 여부 (True=1, False=0, 내림차순)
        ac3_pass = 1 if ac3['pass'] else 0
        
        # Sharpe (None은 -999로 처리, 내림차순)
        sharpe = perf['sharpe_ratio'] if perf['sharpe_ratio'] is not None else -999
        
        # PnL (내림차순)
        pnl = perf['pnl_total']
        
        # Max DD (오름차순, 낮을수록 좋음)
        max_dd = perf['max_drawdown']
        
        return (-ac3_pass, -sharpe, -pnl, max_dd)
    
    return sorted(results, key=sort_key)


# ============================================================
# 4. Report Generation
# ============================================================

def generate_markdown_report(
    month_gate_result: Dict[str, Any],
    tuning_results: List[Dict[str, Any]],
    ranked_results: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """
    Markdown 리포트 생성
    
    Args:
        month_gate_result: 1M Gate 결과
        tuning_results: 24개 튜닝 결과
        ranked_results: 랭킹된 결과
        output_path: 출력 파일 경로
    """
    lines = []
    
    # Header
    lines.append("# PHASE29-5: V4 Performance Metrics Analysis")
    lines.append("")
    lines.append(f"**생성 시각**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 1. Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    
    total_combos = len(tuning_results)
    ac3_pass_count = sum(1 for r in tuning_results if r['ac3_evaluation']['pass'])
    
    lines.append(f"- **총 조합 수**: {total_combos}개 (1M Gate 포함 시 {total_combos + 1}개)")
    lines.append(f"- **AC3 통과**: {ac3_pass_count}개 (Win Rate >= 45% & Max DD <= 15%)")
    lines.append(f"- **AC3 실패**: {total_combos - ac3_pass_count}개")
    lines.append("")
    
    # 2. 1M Gate Baseline
    lines.append("## 2. 1M Gate Baseline Performance")
    lines.append("")
    
    if month_gate_result:
        perf = month_gate_result['performance']
        ac3 = month_gate_result['ac3_evaluation']
        
        lines.append("| 지표 | 값 |")
        lines.append("|------|------|")
        lines.append(f"| Run ID | `{month_gate_result['run_id']}` |")
        lines.append(f"| 거래 수 | {perf['num_trades']}건 |")
        lines.append(f"| Win Rate | {perf['win_rate']*100:.2f}% |")
        lines.append(f"| Max Drawdown | {perf['max_drawdown']*100:.2f}% |")
        lines.append(f"| PnL Total | {perf['pnl_total']:.2f} USDT |")
        lines.append(f"| Sharpe Ratio | {perf['sharpe_ratio']:.3f if perf['sharpe_ratio'] is not None else 'N/A'} |")
        lines.append(f"| Profit Factor | {perf['profit_factor']:.2f} |")
        lines.append(f"| ROI | {perf['roi']*100:.2f}% |")
        lines.append(f"| AC3 평가 | {'✅ PASS' if ac3['pass'] else '❌ FAIL'} ({ac3['comments']}) |")
        lines.append("")
    else:
        lines.append("⚠️ 1M Gate 결과 없음")
        lines.append("")
    
    # 3. Top 5 Combinations
    lines.append("## 3. Top 5 Tuning Combinations")
    lines.append("")
    lines.append("**정렬 기준**: AC3 통과 > Sharpe Ratio > PnL Total > Max DD (낮을수록)")
    lines.append("")
    
    lines.append("| Rank | Run ID | Range | Trend | min_rr | CD | Trades | Win Rate | Max DD | PnL | Sharpe | AC3 |")
    lines.append("|------|--------|-------|-------|--------|----|---------|-----------|---------|----- |--------|-----|")
    
    for i, result in enumerate(ranked_results[:5], 1):
        params = result['params']
        perf = result['performance']
        ac3 = result['ac3_evaluation']
        
        ac3_status = '✅' if ac3['pass'] else '❌'
        sharpe_str = f"{perf['sharpe_ratio']:.2f}" if perf['sharpe_ratio'] is not None else 'N/A'
        
        lines.append(
            f"| {i} | `{result['run_id'][:30]}...` | "
            f"{params.get('range_min_score', '-')} | "
            f"{params.get('trend_min_score', '-')} | "
            f"{params.get('min_rr_required', '-')} | "
            f"{params.get('cooldown_candles', '-')} | "
            f"{perf['num_trades']} | "
            f"{perf['win_rate']*100:.1f}% | "
            f"{perf['max_drawdown']*100:.1f}% | "
            f"{perf['pnl_total']:.1f} | "
            f"{sharpe_str} | "
            f"{ac3_status} |"
        )
    
    lines.append("")
    
    # 4. AC3 Pass/Fail Distribution
    lines.append("## 4. AC3 Pass/Fail Distribution")
    lines.append("")
    
    lines.append(f"- ✅ **PASS**: {ac3_pass_count}개")
    lines.append(f"- ❌ **FAIL**: {total_combos - ac3_pass_count}개")
    lines.append("")
    
    if ac3_pass_count > 0:
        lines.append("### AC3 통과 조합 분석")
        lines.append("")
        
        # 파라미터 분포 분석
        pass_combos = [r for r in tuning_results if r['ac3_evaluation']['pass']]
        
        # Range Score 분포
        range_dist = defaultdict(int)
        for r in pass_combos:
            range_score = r['params'].get('range_min_score')
            if range_score:
                range_dist[range_score] += 1
        
        lines.append("**Range Min Score 분포**:")
        for score in sorted(range_dist.keys()):
            lines.append(f"- `range_min_score={score}`: {range_dist[score]}개")
        lines.append("")
        
        # min_rr 분포
        rr_dist = defaultdict(int)
        for r in pass_combos:
            rr = r['params'].get('min_rr_required')
            if rr:
                rr_dist[rr] += 1
        
        lines.append("**min_rr_required 분포**:")
        for rr in sorted(rr_dist.keys()):
            lines.append(f"- `min_rr={rr}`: {rr_dist[rr]}개")
        lines.append("")
    
    # 5. Performance Metrics Summary
    lines.append("## 5. Performance Metrics Summary (All Combinations)")
    lines.append("")
    
    if tuning_results:
        avg_win_rate = sum(r['performance']['win_rate'] for r in tuning_results) / len(tuning_results)
        avg_max_dd = sum(r['performance']['max_drawdown'] for r in tuning_results) / len(tuning_results)
        avg_pnl = sum(r['performance']['pnl_total'] for r in tuning_results) / len(tuning_results)
        
        lines.append(f"- **평균 Win Rate**: {avg_win_rate*100:.2f}%")
        lines.append(f"- **평균 Max DD**: {avg_max_dd*100:.2f}%")
        lines.append(f"- **평균 PnL**: {avg_pnl:.2f} USDT")
        lines.append("")
    
    # 6. Next Steps
    lines.append("## 6. Next Steps")
    lines.append("")
    lines.append("1. **AC3 통과 조합** → PHASE30 앙상블 통합 후보")
    lines.append("2. **상위 3-5개 조합** → Paper Trading 검증")
    lines.append("3. **AC3 실패 조합** → 파라미터 재조정 또는 제외")
    lines.append("")
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def generate_json_report(
    month_gate_result: Dict[str, Any],
    tuning_results: List[Dict[str, Any]],
    ranked_results: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """
    JSON 리포트 생성
    
    Args:
        month_gate_result: 1M Gate 결과
        tuning_results: 24개 튜닝 결과
        ranked_results: 랭킹된 결과
        output_path: 출력 파일 경로
    """
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_combinations': len(tuning_results),
            'ac3_pass_count': sum(1 for r in tuning_results if r['ac3_evaluation']['pass']),
            'ac3_fail_count': sum(1 for r in tuning_results if not r['ac3_evaluation']['pass'])
        },
        'month_gate_baseline': month_gate_result,
        'tuning_results': tuning_results,
        'ranked_results': ranked_results,
        'top_5': ranked_results[:5]
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


# ============================================================
# 5. Main
# ============================================================

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="PHASE29-5: V4 Performance Analysis")
    parser.add_argument(
        '--phase29-4-0-dir',
        type=Path,
        default=PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_0',
        help='PHASE29-4-0 디렉토리 (1M Gate/Baseline)'
    )
    parser.add_argument(
        '--phase29-4-1-dir',
        type=Path,
        default=PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_1',
        help='PHASE29-4-1 디렉토리 (24개 튜닝)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=PROJECT_ROOT / 'reports' / 'analysis' / 'PHASE29',
        help='출력 디렉토리'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PHASE29-5: V4 Performance Metrics Analysis")
    print("=" * 80)
    print()
    
    # STEP 1: Load 1M Gate/Baseline
    print("STEP 1: 1M Gate/Baseline 로드")
    print(f"  경로: {args.phase29_4_0_dir}")
    
    month_results = load_summary_jsons(args.phase29_4_0_dir)
    
    # 1M Gate 결과 찾기 (gate가 포함된 run_id)
    month_gate_result = None
    for run_id, data in month_results.items():
        if 'gate' in run_id.lower():
            perf = extract_performance_metrics(data)
            ac3 = evaluate_ac3_criteria(perf)
            month_gate_result = {
                'run_id': run_id,
                'performance': perf,
                'ac3_evaluation': ac3
            }
            print(f"  ✅ 1M Gate 발견: {run_id}")
            break
    
    if not month_gate_result:
        print("  ⚠️ 1M Gate 결과 없음")
    
    print()
    
    # STEP 2: Load 24개 튜닝 결과
    print("STEP 2: 24개 튜닝 결과 로드")
    print(f"  경로: {args.phase29_4_1_dir}")
    
    tuning_summaries = load_summary_jsons(args.phase29_4_1_dir)
    
    tuning_results = []
    for run_id, data in tuning_summaries.items():
        perf = extract_performance_metrics(data)
        params = parse_tuning_params(run_id)
        ac3 = evaluate_ac3_criteria(perf)
        
        tuning_results.append({
            'run_id': run_id,
            'params': params,
            'performance': perf,
            'ac3_evaluation': ac3
        })
    
    print(f"  ✅ {len(tuning_results)}개 로드 완료")
    print()
    
    # STEP 3: Ranking
    print("STEP 3: 성능 기반 랭킹")
    
    ranked_results = rank_combinations(tuning_results)
    
    ac3_pass_count = sum(1 for r in tuning_results if r['ac3_evaluation']['pass'])
    print(f"  AC3 통과: {ac3_pass_count}개")
    print(f"  AC3 실패: {len(tuning_results) - ac3_pass_count}개")
    print()
    
    # STEP 4: Generate Reports
    print("STEP 4: 리포트 생성")
    
    md_output = args.output_dir / 'phase29_5_v4_performance.md'
    json_output = args.output_dir / 'phase29_5_v4_performance.json'
    
    generate_markdown_report(month_gate_result, tuning_results, ranked_results, md_output)
    print(f"  ✅ Markdown: {md_output}")
    
    generate_json_report(month_gate_result, tuning_results, ranked_results, json_output)
    print(f"  ✅ JSON: {json_output}")
    print()
    
    # Summary
    print("=" * 80)
    print("✅ 분석 완료")
    print("=" * 80)
    print()
    print(f"총 조합: {len(tuning_results)}개")
    print(f"AC3 통과: {ac3_pass_count}개")
    print()
    
    if ranked_results:
        print("Top 3:")
        for i, r in enumerate(ranked_results[:3], 1):
            perf = r['performance']
            ac3_status = '✅' if r['ac3_evaluation']['pass'] else '❌'
            print(f"  {i}. {r['run_id']}")
            print(f"     Win Rate: {perf['win_rate']*100:.1f}%, Max DD: {perf['max_drawdown']*100:.1f}%, "
                  f"PnL: {perf['pnl_total']:.1f}, AC3: {ac3_status}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
