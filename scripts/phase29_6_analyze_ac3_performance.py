#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-6: AC3 Performance Analysis
====================================

목적:
- V4 1M + Top 3 튜닝 조합의 실제 성능 지표 분석
- AC3 기준 재평가 (Win Rate >= 45%, Max DD <= 15%)
- Markdown + JSON 리포트 생성
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_summary_json(path: Path) -> Dict[str, Any]:
    """Summary JSON 로드"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_ac3(perf: Dict[str, Any]) -> Dict[str, Any]:
    """AC3 기준 평가"""
    win_rate = perf.get('win_rate', 0.0)
    max_dd = perf.get('max_drawdown', 0.0)
    
    ac3_pass = (win_rate >= 0.45 and max_dd <= 0.15)
    
    return {
        'pass': ac3_pass,
        'win_rate_pass': win_rate >= 0.45,
        'max_dd_pass': max_dd <= 0.15,
        'win_rate_margin': win_rate - 0.45,
        'max_dd_margin': 0.15 - max_dd
    }


def main():
    print("=" * 80)
    print("PHASE29-6: AC3 Performance Analysis")
    print("=" * 80)
    print()
    
    # 분석 대상 파일
    targets = [
        {
            'name': '1M Gate Baseline',
            'path': PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_0' / 'btc5m_baseline_v4_month_gate_summary.json',
            'config': 'baseline (no guard)'
        },
        {
            'name': 'Top 1: r2_t2_rr1.0_cd0',
            'path': PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_1' / 'phase29_4_tuning_r2_t2_rr1.0_cd0_summary.json',
            'config': 'range=2, trend=2, RR=1.0, CD=0'
        },
        {
            'name': 'Top 2: r2_t2_rr1.0_cd1',
            'path': PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_1' / 'phase29_4_tuning_r2_t2_rr1.0_cd1_summary.json',
            'config': 'range=2, trend=2, RR=1.0, CD=1'
        },
        {
            'name': 'Top 3: r2_t3_rr1.0_cd0',
            'path': PROJECT_ROOT / 'reports' / 'backtest' / 'phase29_4_1' / 'phase29_4_tuning_r2_t3_rr1.0_cd0_summary.json',
            'config': 'range=2, trend=3, RR=1.0, CD=0'
        }
    ]
    
    results = []
    
    for target in targets:
        print(f"📄 {target['name']}")
        print(f"   Config: {target['config']}")
        
        if not target['path'].exists():
            print(f"   ⚠️ 파일 없음: {target['path']}")
            print()
            continue
        
        try:
            summary = load_summary_json(target['path'])
            perf = summary.get('performance', {})
            
            if not perf or perf.get('num_trades', 0) == 0:
                print(f"   ⚠️ Performance 데이터 없음")
                print()
                continue
            
            # AC3 평가
            ac3_eval = evaluate_ac3(perf)
            
            result = {
                'name': target['name'],
                'config': target['config'],
                'run_id': summary.get('run_id', 'unknown'),
                'num_trades': perf.get('num_trades', 0),
                'win_rate': perf.get('win_rate', 0.0),
                'max_drawdown': perf.get('max_drawdown', 0.0),
                'pnl_total': perf.get('pnl_total', 0.0),
                'sharpe_ratio': perf.get('sharpe_ratio'),
                'profit_factor': perf.get('profit_factor', 0.0),
                'roi': perf.get('roi', 0.0),
                'ac3': ac3_eval
            }
            
            results.append(result)
            
            # 콘솔 출력
            print(f"   Trades: {result['num_trades']}")
            print(f"   Win Rate: {result['win_rate']*100:.1f}% {'✅' if ac3_eval['win_rate_pass'] else '❌'}")
            print(f"   Max DD: {result['max_drawdown']*100:.1f}% {'✅' if ac3_eval['max_dd_pass'] else '❌'}")
            print(f"   PnL: {result['pnl_total']:.2f} USDT")
            print(f"   AC3: {'✅ PASS' if ac3_eval['pass'] else '❌ FAIL'}")
            print()
        
        except Exception as e:
            print(f"   ❌ 분석 실패: {e}")
            print()
    
    # AC3 통과 개수
    ac3_pass_count = sum(1 for r in results if r['ac3']['pass'])
    
    print("=" * 80)
    print("📊 종합 결과")
    print("=" * 80)
    print()
    print(f"총 분석: {len(results)}개")
    print(f"AC3 PASS: {ac3_pass_count}개")
    print(f"AC3 FAIL: {len(results) - ac3_pass_count}개")
    print()
    
    # Markdown 리포트 생성
    md_output = PROJECT_ROOT / 'reports' / 'analysis' / 'PHASE29' / 'phase29_6_ac3_performance.md'
    md_output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(md_output, 'w', encoding='utf-8') as f:
        f.write("# PHASE29-6: AC3 Performance Analysis\n\n")
        f.write(f"**분석일**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **총 분석**: {len(results)}개\n")
        f.write(f"- **AC3 PASS**: {ac3_pass_count}개\n")
        f.write(f"- **AC3 FAIL**: {len(results) - ac3_pass_count}개\n\n")
        
        f.write("**AC3 기준**:\n")
        f.write("- Win Rate >= 45%\n")
        f.write("- Max Drawdown <= 15%\n\n")
        
        f.write("---\n\n")
        
        f.write("## 상세 결과\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"### {i}. {result['name']}\n\n")
            f.write(f"**Config**: {result['config']}\n\n")
            f.write("| 지표 | 값 | AC3 |\n")
            f.write("|------|-----|-----|\n")
            f.write(f"| Trades | {result['num_trades']} | - |\n")
            f.write(f"| Win Rate | {result['win_rate']*100:.1f}% | {'✅' if result['ac3']['win_rate_pass'] else '❌'} |\n")
            f.write(f"| Max DD | {result['max_drawdown']*100:.1f}% | {'✅' if result['ac3']['max_dd_pass'] else '❌'} |\n")
            f.write(f"| PnL Total | {result['pnl_total']:.2f} USDT | - |\n")
            sharpe_str = f"{result['sharpe_ratio']:.2f}" if result['sharpe_ratio'] is not None else 'N/A'
            f.write(f"| Sharpe Ratio | {sharpe_str} | - |\n")
            f.write(f"| Profit Factor | {result['profit_factor']:.2f} | - |\n")
            f.write(f"| ROI | {result['roi']*100:.1f}% | - |\n")
            f.write(f"| **AC3 판정** | **{'PASS' if result['ac3']['pass'] else 'FAIL'}** | {'✅' if result['ac3']['pass'] else '❌'} |\n\n")
        
        f.write("---\n\n")
        
        f.write("## PHASE29-4 AC3 최종 판정\n\n")
        
        if ac3_pass_count >= 1:
            f.write(f"✅ **PASS** - {ac3_pass_count}개 조합이 AC3 기준 충족\n\n")
        else:
            f.write("❌ **FAIL** - AC3 기준을 충족하는 조합 없음\n\n")
    
    print(f"✅ Markdown 리포트: {md_output}")
    
    # JSON 리포트 생성
    json_output = PROJECT_ROOT / 'reports' / 'analysis' / 'PHASE29' / 'phase29_6_ac3_performance.json'
    
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'total_analyzed': len(results),
            'ac3_pass': ac3_pass_count,
            'ac3_fail': len(results) - ac3_pass_count,
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ JSON 리포트: {json_output}")
    print()
    
    return ac3_pass_count > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
