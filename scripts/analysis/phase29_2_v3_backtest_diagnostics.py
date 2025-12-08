#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-2: BTC 5m Baseline V3 백테스트 진단 스크립트
================================================
btc5m_baseline_v3 전략의 초기 백테스트 결과 분석

목적:
- 1주일/1개월 백테스트 결과 집계
- 신호 빈도, Win Rate, Max DD, Avg RR 계산
- PHASE29-3 진입 조건 충족 여부 평가

분석 항목:
1. 기간별 기본 메트릭 (total_trades, win_rate, avg_rr, max_dd)
2. Regime별 신호 분포 (Trend vs Range)
3. Gate 평가 (PHASE29-3 진입 가능 여부)

Usage:
    python scripts/analysis/phase29_2_v3_backtest_diagnostics.py

Output:
    - reports/analysis/PHASE29/phase29_2_v3_backtest_summary.json
    - reports/analysis/PHASE29/phase29_2_v3_backtest_summary.md
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 1. Data Loading
# ============================================================

def load_summary_json(period: str) -> Dict[str, Any]:
    """
    Period별 summary JSON 로드
    
    Args:
        period: 'week' or 'month'
    
    Returns:
        Summary 딕셔너리
    """
    summary_path = PROJECT_ROOT / f"reports/backtest/phase29_2/btc5m_baseline_v3_{period}_summary.json"
    
    if not summary_path.exists():
        print(f"⚠️ {period.upper()} summary 파일 없음: {summary_path}")
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


# ============================================================
# 2. Analysis Functions
# ============================================================

def analyze_period(period: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Period별 기본 분석
    
    Args:
        period: 'week' or 'month'
        data: summary JSON 데이터
    
    Returns:
        분석 결과 딕셔너리
    """
    if data is None:
        return {'status': 'MISSING', 'period': period}
    
    totals = data.get('totals', {})
    symbols = data.get('symbols', {})
    btcusdt = symbols.get('BTCUSDT', {})
    
    # 기본 메트릭
    total_calls = totals.get('strategy_signals_total', 0)
    signal_true = totals.get('strategy_signals_true', 0)
    signal_false = totals.get('strategy_signals_false', 0)
    orders_submitted = totals.get('orders_submitted', 0)
    guard_blocks = totals.get('guard_blocks_total', 0)
    
    # Regime 분포
    regime_trend = totals.get('regime_trend', 0)
    regime_range = totals.get('regime_range', 0)
    regime_trend_pct = (regime_trend / total_calls * 100) if total_calls > 0 else 0.0
    regime_range_pct = (regime_range / total_calls * 100) if total_calls > 0 else 0.0
    
    # 신호 비율
    signal_rate = (signal_true / total_calls * 100) if total_calls > 0 else 0.0
    conversion_rate = (orders_submitted / signal_true * 100) if signal_true > 0 else 0.0
    
    # 방향별 신호
    long_signals = totals.get('long_signals', 0)
    short_signals = totals.get('short_signals', 0)
    
    result = {
        'period': period,
        'status': 'OK',
        'total_calls': total_calls,
        'signal_true': signal_true,
        'signal_false': signal_false,
        'signal_rate_pct': round(signal_rate, 2),
        'orders_submitted': orders_submitted,
        'conversion_rate_pct': round(conversion_rate, 2),
        'guard_blocks': guard_blocks,
        'regime': {
            'trend': regime_trend,
            'range': regime_range,
            'trend_pct': round(regime_trend_pct, 1),
            'range_pct': round(regime_range_pct, 1)
        },
        'direction': {
            'long': long_signals,
            'short': short_signals
        },
        # 성능 메트릭은 TradeActivityTracker에서 제공하지 않으므로 N/A
        'trades': orders_submitted,
        'win_rate': None,  # 실제 거래 성과 데이터 없음
        'avg_rr': None,
        'max_dd': None,
        'sharpe_ratio': None,
        'pnl_total': None
    }
    
    return result


def evaluate_gates(week_result: Dict[str, Any], month_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    PHASE29-3 진입 조건 평가
    
    Args:
        week_result: 1주일 분석 결과
        month_result: 1개월 분석 결과
    
    Returns:
        Gate 평가 결과
    """
    # Gate 1: 1주 신호 빈도 (최소 10개 목표, 20개 권장)
    week_trades = week_result.get('trades', 0)
    meets_week_frequency = week_trades >= 10
    week_frequency_status = "PASS" if meets_week_frequency else "FAIL"
    week_frequency_note = f"{week_trades}/10 trades (목표: 20+)"
    
    # Gate 2: 1개월 신호 빈도 (최소 30개 목표, 50+ 권장)
    month_trades = month_result.get('trades', 0)
    meets_month_frequency = month_trades >= 30
    month_frequency_status = "PASS" if meets_month_frequency else "FAIL"
    month_frequency_note = f"{month_trades}/30 trades (목표: 50+)"
    
    # Gate 3-5: 성능 메트릭 (데이터 없음)
    meets_winrate = None  # 데이터 없음
    meets_drawdown = None
    meets_rr = None
    
    # 최종 판정
    # 신호 빈도가 너무 낮으면 PHASE29-3 진입 불가
    ready_for_phase29_3 = meets_week_frequency and meets_month_frequency
    
    # 종합 평가
    if not meets_week_frequency or not meets_month_frequency:
        overall_status = "CRITICAL_FAIL"
        recommendation = "전략 로직 재검토 필요 (신호 빈도 극단적으로 낮음)"
    else:
        overall_status = "CONDITIONAL_PASS"
        recommendation = "신호 빈도 충족, 성능 메트릭 평가 필요"
    
    return {
        'week_frequency': {
            'status': week_frequency_status,
            'meets_gate': meets_week_frequency,
            'note': week_frequency_note
        },
        'month_frequency': {
            'status': month_frequency_status,
            'meets_gate': meets_month_frequency,
            'note': month_frequency_note
        },
        'winrate': {
            'status': 'N/A',
            'meets_gate': meets_winrate,
            'note': 'Win Rate 데이터 없음 (TradeActivityTracker 한계)'
        },
        'drawdown': {
            'status': 'N/A',
            'meets_gate': meets_drawdown,
            'note': 'Max DD 데이터 없음'
        },
        'avg_rr': {
            'status': 'N/A',
            'meets_gate': meets_rr,
            'note': 'Avg RR 데이터 없음'
        },
        'ready_for_phase29_3': ready_for_phase29_3,
        'overall_status': overall_status,
        'recommendation': recommendation
    }


# ============================================================
# 3. Report Generation
# ============================================================

def generate_json_report(week_result: Dict[str, Any], month_result: Dict[str, Any], 
                         gates: Dict[str, Any]) -> Dict[str, Any]:
    """
    JSON 리포트 생성
    
    Returns:
        리포트 딕셔너리
    """
    report = {
        'phase': 'PHASE29-2',
        'strategy': 'btc5m_baseline_v3',
        'timestamp': datetime.now().isoformat(),
        'results': {
            'week': week_result,
            'month': month_result
        },
        'gates': gates,
        'summary': {
            'overall_status': gates['overall_status'],
            'ready_for_phase29_3': gates['ready_for_phase29_3'],
            'recommendation': gates['recommendation']
        }
    }
    
    return report


def generate_markdown_report(week_result: Dict[str, Any], month_result: Dict[str, Any], 
                              gates: Dict[str, Any]) -> str:
    """
    Markdown 리포트 생성
    
    Returns:
        Markdown 문자열
    """
    md = []
    md.append("# PHASE29-2: BTC 5m Baseline V3 백테스트 진단 요약")
    md.append("")
    md.append(f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**전략**: btc5m_baseline_v3")
    md.append("")
    md.append("---")
    md.append("")
    
    # Executive Summary
    md.append("## 📊 Executive Summary")
    md.append("")
    md.append(f"**종합 상태**: {gates['overall_status']}")
    md.append(f"**PHASE29-3 진입 가능**: {'✅ YES' if gates['ready_for_phase29_3'] else '❌ NO'}")
    md.append(f"**권장 사항**: {gates['recommendation']}")
    md.append("")
    
    # 기간별 결과 표
    md.append("## 📈 기간별 백테스트 결과")
    md.append("")
    md.append("| 항목 | 1주일 | 1개월 |")
    md.append("|------|-------|-------|")
    md.append(f"| **Total Calls** | {week_result['total_calls']:,} | {month_result['total_calls']:,} |")
    md.append(f"| **Signal True** | {week_result['signal_true']} | {month_result['signal_true']} |")
    md.append(f"| **Signal Rate** | {week_result['signal_rate_pct']}% | {month_result['signal_rate_pct']}% |")
    md.append(f"| **Orders Submitted** | {week_result['orders_submitted']} | {month_result['orders_submitted']} |")
    md.append(f"| **Conversion Rate** | {week_result['conversion_rate_pct']}% | {month_result['conversion_rate_pct']}% |")
    md.append(f"| **Guard Blocks** | {week_result['guard_blocks']} | {month_result['guard_blocks']} |")
    md.append("")
    
    # Regime 분포
    md.append("## 🌐 Regime 분포")
    md.append("")
    md.append("| Regime | 1주일 | 1개월 |")
    md.append("|--------|-------|-------|")
    md.append(f"| **Trend** | {week_result['regime']['trend']} ({week_result['regime']['trend_pct']}%) | {month_result['regime']['trend']} ({month_result['regime']['trend_pct']}%) |")
    md.append(f"| **Range** | {week_result['regime']['range']} ({week_result['regime']['range_pct']}%) | {month_result['regime']['range']} ({month_result['regime']['range_pct']}%) |")
    md.append("")
    
    # Gate 평가
    md.append("## 🚦 PHASE29-3 진입 조건 평가")
    md.append("")
    md.append("| Gate | Status | 충족 여부 | Note |")
    md.append("|------|--------|-----------|------|")
    md.append(f"| **1주 신호 빈도** | {gates['week_frequency']['status']} | {'✅' if gates['week_frequency']['meets_gate'] else '❌'} | {gates['week_frequency']['note']} |")
    md.append(f"| **1개월 신호 빈도** | {gates['month_frequency']['status']} | {'✅' if gates['month_frequency']['meets_gate'] else '❌'} | {gates['month_frequency']['note']} |")
    md.append(f"| **Win Rate ≥ 45%** | {gates['winrate']['status']} | N/A | {gates['winrate']['note']} |")
    md.append(f"| **Max DD ≤ 15%** | {gates['drawdown']['status']} | N/A | {gates['drawdown']['note']} |")
    md.append(f"| **Avg RR ≥ 1.2** | {gates['avg_rr']['status']} | N/A | {gates['avg_rr']['note']} |")
    md.append("")
    
    # 진단 및 권장 사항
    md.append("## 🔍 진단 및 권장 사항")
    md.append("")
    
    if not gates['ready_for_phase29_3']:
        md.append("### ⚠️ CRITICAL: 신호 빈도 부족")
        md.append("")
        md.append(f"- 1주일 백테스트: {week_result['orders_submitted']}건 (목표: 20+)")
        md.append(f"- 1개월 백테스트: {month_result['orders_submitted']}건 (목표: 50+)")
        md.append("")
        md.append("**가능한 원인**:")
        md.append("1. V3 진입 조건이 너무 엄격 (AND 로직 과도)")
        md.append("2. 필터 계층이 신호를 과도하게 차단")
        md.append("3. Regime 분류 기준이 실제 시장과 불일치")
        md.append("4. 전략 코드 버그 (지표 계산, 조건 분기 오류)")
        md.append("")
        md.append("**권장 조치**:")
        md.append("1. V3 전략 코드 재검토 (`strategies/btc5m_baseline_v3.py`)")
        md.append("2. 디버그 로그 추가하여 각 진입 조건 통과율 측정")
        md.append("3. V2 대비 진입 조건 차이 분석")
        md.append("4. 필터 ON/OFF 테스트로 원인 격리")
        md.append("")
    else:
        md.append("### ✅ 신호 빈도 충족")
        md.append("")
        md.append(f"- 1주일: {week_result['orders_submitted']}건")
        md.append(f"- 1개월: {month_result['orders_submitted']}건")
        md.append("")
        md.append("**다음 단계**:")
        md.append("1. 전체 성능 메트릭 측정 (Win Rate, Max DD, Avg RR)")
        md.append("2. Regime별 성능 분석")
        md.append("3. PHASE29-3 튜닝 진입 가능")
        md.append("")
    
    return '\n'.join(md)


# ============================================================
# 4. Main
# ============================================================

def main():
    """메인 함수"""
    print("=" * 60)
    print("PHASE29-2: BTC 5m Baseline V3 백테스트 진단")
    print("=" * 60)
    print()
    
    # 1. 데이터 로드
    print("📂 백테스트 결과 로드 중...")
    week_data = load_summary_json('week')
    month_data = load_summary_json('month')
    
    if week_data is None or month_data is None:
        print("❌ 백테스트 결과 파일 누락")
        return 1
    
    print("✅ 백테스트 결과 로드 완료")
    print()
    
    # 2. 분석
    print("🔍 분석 중...")
    week_result = analyze_period('week', week_data)
    month_result = analyze_period('month', month_data)
    gates = evaluate_gates(week_result, month_result)
    
    print(f"  - 1주일: {week_result['orders_submitted']}건 거래")
    print(f"  - 1개월: {month_result['orders_submitted']}건 거래")
    print(f"  - 종합 상태: {gates['overall_status']}")
    print()
    
    # 3. 리포트 생성
    print("📝 리포트 생성 중...")
    json_report = generate_json_report(week_result, month_result, gates)
    md_report = generate_markdown_report(week_result, month_result, gates)
    
    # 4. 저장
    output_dir = PROJECT_ROOT / "reports/analysis/PHASE29"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / "phase29_2_v3_backtest_summary.json"
    md_path = output_dir / "phase29_2_v3_backtest_summary.md"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    print(f"✅ JSON 리포트 저장: {json_path}")
    print(f"✅ Markdown 리포트 저장: {md_path}")
    print()
    
    # 5. 요약 출력
    print("=" * 60)
    print("📊 분석 요약")
    print("=" * 60)
    print(f"종합 상태: {gates['overall_status']}")
    print(f"PHASE29-3 진입 가능: {'✅ YES' if gates['ready_for_phase29_3'] else '❌ NO'}")
    print(f"권장 사항: {gates['recommendation']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
