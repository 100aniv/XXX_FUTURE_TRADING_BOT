#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE29-0: Strategy Drawdown Diagnostics
=========================================
btc5m_baseline_v2 전략의 드로우다운 원인 정량 분석 스크립트

목적:
- PHASE28-10~13 백테스트 결과를 집계하여 전략 성능 진단
- Profile별 비교 (E/H/I/J)
- 근본 원인 가설 도출

분석 항목:
1. 전환율 및 Guard 차단 분석
2. Regime별 성능 (Trend vs Range)
3. 진입 방향별 성능 (LONG vs SHORT)
4. Drawdown 기여도 분석

Usage:
    python scripts/analysis/phase29_0_strategy_dd_diagnostics.py

Output:
    - reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.json
    - reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.md
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

def load_summary_json(profile_name: str, phase: str = "phase28_13") -> Dict[str, Any]:
    """
    Profile별 summary JSON 로드
    
    Args:
        profile_name: 프로파일 이름 (e/h/i/j)
        phase: Phase 번호 (기본 phase28_13)
    
    Returns:
        Summary 딕셔너리
    """
    # PHASE28-12 (Profile E/G), PHASE28-13 (Profile H/I/J)
    if profile_name in ['e', 'g']:
        summary_path = PROJECT_ROOT / f"reports/backtest/phase28_12/profile_{profile_name}_summary.json"
    else:
        summary_path = PROJECT_ROOT / f"reports/backtest/{phase}/profile_{profile_name}_summary.json"
    
    if not summary_path.exists():
        print(f"⚠️ Profile {profile_name.upper()} summary 파일 없음: {summary_path}")
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


# ============================================================
# 2. Analysis Functions
# ============================================================

def analyze_profile_basic(profile_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Profile 기본 분석 (전환율, Guard 차단, Regime 분포)
    
    Args:
        profile_name: 프로파일 이름
        data: summary JSON 데이터
    
    Returns:
        분석 결과 딕셔너리
    """
    if data is None:
        return {'status': 'MISSING'}
    
    totals = data.get('totals', {})
    symbols = data.get('symbols', {})
    btcusdt = symbols.get('BTCUSDT', {})
    
    # 기본 메트릭
    signal_true = totals.get('strategy_signals_true', 0)
    signal_false = totals.get('strategy_signals_false', 0)
    total_calls = totals.get('strategy_signals_total', signal_true + signal_false)
    orders_submitted = totals.get('orders_submitted', 0)
    guard_blocks_total = totals.get('guard_blocks_total', 0)
    
    # 전환율
    conversion_rate = (orders_submitted / signal_true * 100) if signal_true > 0 else 0.0
    
    # Regime 분포
    regime_range = totals.get('regime_range', 0)
    regime_trend = totals.get('regime_trend', 0)
    
    # 진입 방향
    long_signals = totals.get('long_signals', 0)
    short_signals = totals.get('short_signals', 0)
    
    # Guard 차단 분석
    guard_blocks = btcusdt.get('guard_blocks', {})
    guard_breakdown = []
    for reason, count in sorted(guard_blocks.items(), key=lambda x: x[1], reverse=True):
        pct = (count / signal_true * 100) if signal_true > 0 else 0.0
        guard_breakdown.append({
            'reason': reason,
            'count': count,
            'percent': round(pct, 2)
        })
    
    return {
        'profile_name': profile_name,
        'run_id': data.get('run_id', 'N/A'),
        'timestamp': data.get('timestamp', 'N/A'),
        'total_calls': total_calls,
        'signal_true': signal_true,
        'signal_false': signal_false,
        'orders_submitted': orders_submitted,
        'guard_blocks_total': guard_blocks_total,
        'conversion_rate_pct': round(conversion_rate, 2),
        'regime_range': regime_range,
        'regime_range_pct': round((regime_range / total_calls * 100), 2) if total_calls > 0 else 0.0,
        'regime_trend': regime_trend,
        'regime_trend_pct': round((regime_trend / total_calls * 100), 2) if total_calls > 0 else 0.0,
        'long_signals': long_signals,
        'long_pct': round((long_signals / signal_true * 100), 2) if signal_true > 0 else 0.0,
        'short_signals': short_signals,
        'short_pct': round((short_signals / signal_true * 100), 2) if signal_true > 0 else 0.0,
        'guard_breakdown': guard_breakdown[:5]  # Top 5
    }


def compare_profiles(profiles: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Profile 간 비교 분석
    
    Args:
        profiles: {profile_name: analysis_result, ...}
    
    Returns:
        비교 결과
    """
    # Profile E (SOFT) vs H (OFF) 비교
    profile_e = profiles.get('e', {})
    profile_h = profiles.get('h', {})
    
    if profile_e.get('status') == 'MISSING' or profile_h.get('status') == 'MISSING':
        return {'comparison': 'Profile E or H missing'}
    
    # 전환율 비교
    conversion_e = profile_e.get('conversion_rate_pct', 0.0)
    conversion_h = profile_h.get('conversion_rate_pct', 0.0)
    conversion_improvement = (conversion_h / conversion_e) if conversion_e > 0 else 0.0
    
    # Guard 차단 비교
    guard_e = profile_e.get('guard_blocks_total', 0)
    guard_h = profile_h.get('guard_blocks_total', 0)
    guard_reduction_pct = ((guard_e - guard_h) / guard_e * 100) if guard_e > 0 else 0.0
    
    # Signal True 비교 (백테스트 완료율)
    signal_e = profile_e.get('signal_true', 0)
    signal_h = profile_h.get('signal_true', 0)
    completion_ratio = (signal_h / signal_e) if signal_e > 0 else 0.0
    
    return {
        'profile_e_conversion': conversion_e,
        'profile_h_conversion': conversion_h,
        'conversion_improvement': round(conversion_improvement, 2),
        'profile_e_guard_blocks': guard_e,
        'profile_h_guard_blocks': guard_h,
        'guard_reduction_pct': round(guard_reduction_pct, 2),
        'profile_e_signal_true': signal_e,
        'profile_h_signal_true': signal_h,
        'backtest_completion_ratio': round(completion_ratio, 2),
        'interpretation': (
            f"Daily Loss Guard OFF로 전환율 {conversion_improvement:.1f}배 증가, "
            f"Guard 차단 {guard_reduction_pct:.1f}% 감소. "
            f"하지만 백테스트 {completion_ratio*100:.1f}%만 완료 (Drawdown Guard 조기 차단)."
        )
    }


def generate_hypotheses(profiles: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    백테스트 결과 기반 근본 원인 가설 생성
    
    Args:
        profiles: {profile_name: analysis_result, ...}
    
    Returns:
        가설 리스트
    """
    hypotheses = []
    
    # 공통 패턴 분석
    profile_h = profiles.get('h', {})
    
    if profile_h.get('status') != 'MISSING':
        # 1. Drawdown Guard 10% 조기 차단
        signal_h = profile_h.get('signal_true', 0)
        signal_e = profiles.get('e', {}).get('signal_true', 0)
        if signal_e > 0:
            completion_ratio = signal_h / signal_e
            if completion_ratio < 0.5:
                hypotheses.append(
                    f"❌ **Drawdown Guard 조기 차단**: 백테스트 {completion_ratio*100:.1f}%만 완료. "
                    f"전략이 10% 손실 이후 시스템 정지 → 전략 기대값<0 추정."
                )
        
        # 2. Regime 편향
        regime_trend_pct = profile_h.get('regime_trend_pct', 0.0)
        if regime_trend_pct > 90:
            hypotheses.append(
                f"📊 **Regime 편향**: Trend Regime {regime_trend_pct:.1f}% 지배. "
                f"Range 구간 진입 부족 → 추세 추종 전략의 한계 (Trend 구간에서도 손실)."
            )
        
        # 3. Long/Short 불균형
        long_pct = profile_h.get('long_pct', 0.0)
        short_pct = profile_h.get('short_pct', 0.0)
        if abs(long_pct - short_pct) > 20:
            bias = "LONG" if long_pct > short_pct else "SHORT"
            hypotheses.append(
                f"⚖️ **방향 편향**: {bias} 신호 {max(long_pct, short_pct):.1f}% vs {min(long_pct, short_pct):.1f}%. "
                f"방향 불균형 → 일방향 손실 집중 가능성."
            )
        
        # 4. 전환율 vs 생존 기간 트레이드오프
        conversion_h = profile_h.get('conversion_rate_pct', 0.0)
        if conversion_h > 25:
            hypotheses.append(
                f"🔄 **전환율 vs 생존 기간 트레이드오프**: 전환율 {conversion_h:.1f}%로 극대화되었으나, "
                f"생존 기간은 단축됨 (더 많은 거래 = 더 빠른 손실 누적)."
            )
        
        # 5. Guard 차단 패턴
        guard_breakdown = profile_h.get('guard_breakdown', [])
        if guard_breakdown:
            top_guard = guard_breakdown[0]
            if top_guard['percent'] > 50:
                hypotheses.append(
                    f"🚫 **Guard 차단 집중**: `{top_guard['reason']}` {top_guard['percent']:.1f}% 차단. "
                    f"특정 Guard가 지배적 → 전략 로직과 Guard 설정 불일치."
                )
    
    # 기본 가설 (데이터 없을 때)
    if not hypotheses:
        hypotheses.append(
            "⚠️ 데이터 부족: 충분한 분석 데이터가 없습니다. Profile H/I/J 백테스트 결과를 확인하세요."
        )
    
    return hypotheses


# ============================================================
# 3. Report Generation
# ============================================================

def generate_json_report(analysis: Dict[str, Any], output_path: Path):
    """JSON 리포트 생성"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON 리포트 저장: {output_path}")


def generate_markdown_report(analysis: Dict[str, Any], output_path: Path):
    """Markdown 리포트 생성"""
    profiles = analysis['profiles']
    comparison = analysis['comparison']
    hypotheses = analysis['hypotheses']
    
    lines = [
        "# PHASE29-0: btc5m_baseline_v2 전략 드로우다운 진단 리포트",
        "",
        f"**생성 시각**: {analysis['timestamp']}",
        f"**분석 대상**: PHASE28-10~13 백테스트 결과 (Profile E/H/I/J)",
        "",
        "---",
        "",
        "## 📊 Profile 요약 테이블",
        "",
        "| Profile | Mode | Signals | Orders | 전환율 | Guard 차단 | Regime Trend % | Long/Short |",
        "|---------|------|---------|--------|--------|------------|----------------|------------|"
    ]
    
    profile_names = {
        'e': 'E (SOFT)',
        'h': 'H (OFF)',
        'i': 'I (OFF+LIGHT)',
        'j': 'J (OFF+AGGRESSIVE)'
    }
    
    for profile_key in ['e', 'h', 'i', 'j']:
        profile = profiles.get(profile_key, {})
        if profile.get('status') == 'MISSING':
            lines.append(f"| **{profile_names[profile_key]}** | - | - | - | - | - | - | - |")
            continue
        
        mode = "SOFT" if profile_key == 'e' else "OFF"
        signals = profile.get('signal_true', 0)
        orders = profile.get('orders_submitted', 0)
        conversion = profile.get('conversion_rate_pct', 0.0)
        guard_blocks = profile.get('guard_blocks_total', 0)
        regime_trend_pct = profile.get('regime_trend_pct', 0.0)
        long_pct = profile.get('long_pct', 0.0)
        short_pct = profile.get('short_pct', 0.0)
        
        lines.append(
            f"| **{profile_names[profile_key]}** | {mode} | {signals:,} | {orders:,} | "
            f"**{conversion:.2f}%** | {guard_blocks:,} | {regime_trend_pct:.1f}% | "
            f"{long_pct:.1f}% / {short_pct:.1f}% |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 🔍 Profile E vs H 비교 분석",
        "",
        f"- **전환율**: {comparison['profile_e_conversion']:.2f}% → {comparison['profile_h_conversion']:.2f}% "
        f"(**{comparison['conversion_improvement']:.1f}배 증가**)",
        f"- **Guard 차단**: {comparison['profile_e_guard_blocks']:,} → {comparison['profile_h_guard_blocks']:,} "
        f"({comparison['guard_reduction_pct']:.1f}% 감소)",
        f"- **백테스트 완료율**: {comparison['backtest_completion_ratio']*100:.1f}% "
        f"({comparison['profile_h_signal_true']:,} / {comparison['profile_e_signal_true']:,} signals)",
        "",
        f"**해석**: {comparison['interpretation']}",
        "",
        "---",
        "",
        "## 🧪 근본 원인 가설",
        ""
    ])
    
    for idx, hypothesis in enumerate(hypotheses, start=1):
        lines.append(f"### {idx}. {hypothesis}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "## 💡 다음 단계 (PHASE29-1+)",
        "",
        "1. **전략 리디자인 설계**: `docs/PHASE29/PHASE29_0_BTC5M_BASELINE_V2_STRATEGY_REDESIGN_KR.md` 작성",
        "2. **Win Rate 개선**: Entry 조건 강화, TP/SL 구조 재설계",
        "3. **Risk/Reward 조정**: per-trade 리스크 축소 (예: 0.3~0.5% per trade)",
        "4. **Drawdown Guard 한도 상향**: 10% → 15~20% (전략 개선 후 재검토)",
        "5. **Multi-TP 레벨 최적화**: Partial TP + BE 이동 구조",
        "",
        "---",
        "",
        "## 📝 Notes",
        "",
        "- 이 리포트는 **정량 분석** 기반 진단입니다.",
        "- 실제 거래 로그 (trades.csv) 분석은 포함되지 않았습니다 (summary JSON만 사용).",
        "- 추가 분석이 필요한 경우, `scripts/analysis/` 하위에 새로운 스크립트를 추가하세요.",
        ""
    ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Markdown 리포트 저장: {output_path}")


# ============================================================
# 4. Main
# ============================================================

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("PHASE29-0: Strategy Drawdown Diagnostics")
    print("=" * 80)
    print()
    
    # 1. Profile 데이터 로드
    print("📂 Profile 데이터 로딩...")
    profiles_raw = {}
    for profile_name in ['e', 'h', 'i', 'j']:
        data = load_summary_json(profile_name)
        profiles_raw[profile_name] = data
        if data is None:
            print(f"   ⚠️  Profile {profile_name.upper()}: MISSING")
        else:
            totals = data.get('totals', {})
            signal_true = totals.get('strategy_signals_true', 0)
            orders = totals.get('orders_submitted', 0)
            print(f"   ✅ Profile {profile_name.upper()}: {signal_true:,} signals → {orders:,} orders")
    
    print()
    
    # 2. Profile 분석
    print("🔍 Profile 기본 분석 수행...")
    profiles_analyzed = {}
    for profile_name, data in profiles_raw.items():
        profiles_analyzed[profile_name] = analyze_profile_basic(profile_name, data)
    
    print("   ✅ Profile 기본 분석 완료")
    print()
    
    # 3. Profile 비교
    print("📊 Profile 비교 분석...")
    comparison = compare_profiles(profiles_analyzed)
    print(f"   ✅ 전환율 개선: {comparison.get('conversion_improvement', 0)}배")
    print()
    
    # 4. 가설 생성
    print("🧪 근본 원인 가설 생성...")
    hypotheses = generate_hypotheses(profiles_analyzed)
    print(f"   ✅ {len(hypotheses)}개 가설 생성")
    print()
    
    # 5. 종합 분석 결과
    analysis_result = {
        'timestamp': datetime.now().isoformat(),
        'phase': 'PHASE29-0',
        'objective': 'btc5m_baseline_v2 Strategy Drawdown Diagnostics',
        'profiles': profiles_analyzed,
        'comparison': comparison,
        'hypotheses': hypotheses
    }
    
    # 6. 리포트 생성
    print("📝 리포트 생성...")
    output_json_path = PROJECT_ROOT / "reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.json"
    output_md_path = PROJECT_ROOT / "reports/analysis/PHASE29/phase29_0_dd_diagnostics_summary.md"
    
    generate_json_report(analysis_result, output_json_path)
    generate_markdown_report(analysis_result, output_md_path)
    
    print()
    print("=" * 80)
    print("✅ PHASE29-0 Strategy Drawdown Diagnostics Complete!")
    print("=" * 80)
    print()
    print("📄 Outputs:")
    print(f"   - JSON: {output_json_path}")
    print(f"   - Markdown: {output_md_path}")
    print()


if __name__ == "__main__":
    main()
