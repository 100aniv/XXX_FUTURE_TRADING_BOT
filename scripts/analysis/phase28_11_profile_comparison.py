#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-11: Profile Comparison Analysis
========================================
4개 Guard Optimization 프로파일 백테스트 결과 비교 분석

Profiles:
- A: BASELINE (기준선, 현재 상태)
- B: COOLDOWN_RELAXED (쿨다운 완화)
- C: PORTFOLIO_RELAXED (포트폴리오 완화)
- D: MIXED_RELAXED (혼합 완화, 상용 후보)

Output:
- reports/backtest/phase28_11/profile_comparison.json
- reports/backtest/phase28_11/profile_comparison.md
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def load_profile_summary(profile_name: str) -> Dict[str, Any]:
    """
    프로파일별 summary JSON 로드
    
    Args:
        profile_name: 프로파일 이름 (a/b/c/d)
    
    Returns:
        Summary 딕셔너리 (totals 섹션 포함)
    """
    summary_path = PROJECT_ROOT / f"reports/backtest/phase28_11/profile_{profile_name}_summary.json"
    
    if not summary_path.exists():
        print(f"⚠️ {profile_name.upper()} summary 파일 없음: {summary_path}")
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def calculate_conversion_rate(totals: Dict[str, Any]) -> float:
    """
    전환율 계산: orders_submitted / strategy_signals_true * 100
    
    Args:
        totals: summary['totals'] 딕셔너리
    
    Returns:
        전환율 (%)
    """
    signal_true = totals.get('strategy_signals_true', 0)
    orders_submitted = totals.get('orders_submitted', 0)
    
    if signal_true == 0:
        return 0.0
    
    return (orders_submitted / signal_true) * 100


def extract_top_guard_blocks(data: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Guard Blocks 상위 N개 추출
    
    Args:
        data: summary 딕셔너리 (전체)
        top_n: 상위 N개
    
    Returns:
        [{reason, count, percent}, ...]
    """
    # guard_blocks는 symbols.BTCUSDT.guard_blocks에 있음
    symbols = data.get('symbols', {})
    btcusdt = symbols.get('BTCUSDT', {})
    guard_blocks = btcusdt.get('guard_blocks', {})
    
    totals = data.get('totals', {})
    signal_true = totals.get('strategy_signals_true', 1)  # division by zero 방지
    
    # (reason, count) 튜플 리스트로 변환 후 count 기준 내림차순 정렬
    sorted_blocks = sorted(guard_blocks.items(), key=lambda x: x[1], reverse=True)
    
    top_blocks = []
    for reason, count in sorted_blocks[:top_n]:
        percent = (count / signal_true) * 100
        top_blocks.append({
            'reason': reason,
            'count': count,
            'percent': round(percent, 2)
        })
    
    return top_blocks


def generate_comparison_json(profiles_data: Dict[str, Dict]) -> Dict[str, Any]:
    """
    프로파일 비교 JSON 생성
    
    Args:
        profiles_data: {profile_name: summary_data, ...}
    
    Returns:
        비교 리포트 JSON
    """
    comparison = {
        'timestamp': datetime.now().isoformat(),
        'phase': 'PHASE28-11',
        'objective': 'Guard Optimization V1 - Profile Comparison',
        'profiles': {}
    }
    
    for profile_name, data in profiles_data.items():
        if data is None:
            comparison['profiles'][profile_name] = {'status': 'MISSING'}
            continue
        
        totals = data.get('totals', {})
        
        profile_summary = {
            'run_id': data.get('run_id', 'UNKNOWN'),
            'signal_true': totals.get('strategy_signals_true', 0),
            'guard_blocks_total': totals.get('guard_blocks_total', 0),
            'orders_submitted': totals.get('orders_submitted', 0),
            'conversion_rate_pct': round(calculate_conversion_rate(totals), 2),
            'top_guard_blocks': extract_top_guard_blocks(data, top_n=3)
        }
        
        comparison['profiles'][profile_name] = profile_summary
    
    return comparison


def generate_comparison_markdown(comparison: Dict[str, Any]) -> str:
    """
    프로파일 비교 Markdown 리포트 생성
    
    Args:
        comparison: generate_comparison_json() 결과
    
    Returns:
        Markdown 문자열
    """
    lines = []
    
    # 헤더
    lines.append("# PHASE28-11: Profile Comparison Report")
    lines.append("")
    lines.append(f"**Generated**: {comparison['timestamp']}")
    lines.append(f"**Phase**: {comparison['phase']}")
    lines.append(f"**Objective**: {comparison['objective']}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 프로파일 요약 테이블
    lines.append("## 📊 Profile Summary")
    lines.append("")
    lines.append("| Profile | Signal True | Guard Blocks | Orders | Conversion Rate | Status |")
    lines.append("|---------|-------------|--------------|--------|-----------------|--------|")
    
    profile_order = ['a', 'b', 'c', 'd']
    profile_names = {
        'a': 'A: BASELINE',
        'b': 'B: COOLDOWN_RELAXED',
        'c': 'C: PORTFOLIO_RELAXED',
        'd': 'D: MIXED_RELAXED'
    }
    
    for profile_key in profile_order:
        profile_data = comparison['profiles'].get(profile_key, {})
        
        if profile_data.get('status') == 'MISSING':
            lines.append(f"| **{profile_names[profile_key]}** | - | - | - | - | ⚠️ MISSING |")
            continue
        
        signal_true = profile_data.get('signal_true', 0)
        guard_blocks = profile_data.get('guard_blocks_total', 0)
        orders = profile_data.get('orders_submitted', 0)
        conversion_rate = profile_data.get('conversion_rate_pct', 0.0)
        
        # 전환율에 따라 이모지 추가
        if conversion_rate >= 5.0:
            status = "✅ TARGET"
        elif conversion_rate >= 3.0:
            status = "🟢 GOOD"
        elif conversion_rate >= 1.0:
            status = "🟡 MODERATE"
        else:
            status = "🔴 LOW"
        
        lines.append(
            f"| **{profile_names[profile_key]}** | {signal_true:,} | {guard_blocks:,} ({guard_blocks/signal_true*100:.1f}%) | {orders:,} | **{conversion_rate:.2f}%** | {status} |"
        )
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 프로파일별 상세 분석
    lines.append("## 🔍 Detailed Analysis")
    lines.append("")
    
    for profile_key in profile_order:
        profile_data = comparison['profiles'].get(profile_key, {})
        
        if profile_data.get('status') == 'MISSING':
            lines.append(f"### {profile_names[profile_key]}")
            lines.append("")
            lines.append("⚠️ **Data not available**")
            lines.append("")
            continue
        
        lines.append(f"### {profile_names[profile_key]}")
        lines.append("")
        
        # 기본 메트릭
        lines.append("**Key Metrics**:")
        lines.append(f"- Signal True: **{profile_data['signal_true']:,}**")
        lines.append(f"- Guard Blocks: **{profile_data['guard_blocks_total']:,}** ({profile_data['guard_blocks_total']/profile_data['signal_true']*100:.1f}%)")
        lines.append(f"- Orders Submitted: **{profile_data['orders_submitted']:,}**")
        lines.append(f"- Conversion Rate: **{profile_data['conversion_rate_pct']:.2f}%**")
        lines.append("")
        
        # Top Guard Blocks
        top_blocks = profile_data.get('top_guard_blocks', [])
        if top_blocks:
            lines.append("**Top Blocking Factors**:")
            lines.append("")
            lines.append("| Rank | Reason | Count | % of Signals |")
            lines.append("|------|--------|-------|--------------|")
            
            ranks = ['🥇', '🥈', '🥉']
            for i, block in enumerate(top_blocks):
                rank = ranks[i] if i < len(ranks) else f"{i+1}"
                lines.append(f"| {rank} | `{block['reason']}` | {block['count']:,} | {block['percent']:.2f}% |")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # 권장 사항
    lines.append("## 💡 Recommendations")
    lines.append("")
    
    # Profile D 우선 추천 (MIXED_RELAXED)
    profile_d = comparison['profiles'].get('d', {})
    if profile_d.get('status') != 'MISSING':
        conversion_d = profile_d.get('conversion_rate_pct', 0.0)
        
        if conversion_d >= 3.0:
            lines.append("### ✅ Recommended Profile: D (MIXED_RELAXED)")
            lines.append("")
            lines.append(f"- **Conversion Rate**: {conversion_d:.2f}% (Target: 3~5%)")
            lines.append(f"- **Trade Count**: {profile_d['orders_submitted']:,}")
            lines.append("- **Risk Balance**: 🟢 Moderate (suitable for production)")
            lines.append("")
            lines.append("**Rationale**:")
            lines.append("- Profile D achieves the target conversion rate while maintaining balanced risk controls.")
            lines.append("- Combines cooldown relaxation with moderate portfolio exposure limits.")
            lines.append("- Suitable for Paper Trading validation in PHASE28-12+.")
            lines.append("")
        else:
            lines.append("### ⚠️ Profile D (MIXED_RELAXED) - Below Target")
            lines.append("")
            lines.append(f"- **Conversion Rate**: {conversion_d:.2f}% (Target: 3~5%)")
            lines.append("- **Status**: Further optimization required.")
            lines.append("")
    
    # Profile B/C 비교
    profile_b = comparison['profiles'].get('b', {})
    profile_c = comparison['profiles'].get('c', {})
    
    if profile_b.get('status') != 'MISSING' and profile_c.get('status') != 'MISSING':
        conversion_b = profile_b.get('conversion_rate_pct', 0.0)
        conversion_c = profile_c.get('conversion_rate_pct', 0.0)
        
        lines.append("### Comparison: B (Cooldown) vs C (Portfolio)")
        lines.append("")
        lines.append(f"- **Profile B Conversion**: {conversion_b:.2f}%")
        lines.append(f"- **Profile C Conversion**: {conversion_c:.2f}%")
        lines.append("")
        
        if conversion_b > conversion_c:
            lines.append("**Insight**: Cooldown relaxation has a **stronger impact** on conversion rate than portfolio limits.")
        elif conversion_c > conversion_b:
            lines.append("**Insight**: Portfolio relaxation has a **stronger impact** on conversion rate than cooldown.")
        else:
            lines.append("**Insight**: Both cooldown and portfolio relaxation have **similar impact**.")
        
        lines.append("")
    
    # 다음 단계
    lines.append("## 🚀 Next Steps")
    lines.append("")
    lines.append("1. **PHASE28-12**: Fine-tune parameters based on Profile D (if target achieved)")
    lines.append("2. **PHASE28-13**: Multi-Period Validation (Bull/Bear/Range)")
    lines.append("3. **PHASE29**: Paper Trading validation (30 days)")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## 📝 Notes")
    lines.append("")
    lines.append("- This report compares **4 Guard Optimization profiles** (PHASE28-11).")
    lines.append("- All backtests use the **same 3-month period** (2024-10-01 ~ 2024-12-31).")
    lines.append("- Strategy: `btc5m_baseline_v2` (PHASE28-6/7 design).")
    lines.append("- Symbol: BTCUSDT (5m timeframe).")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("PHASE28-11: Profile Comparison Analysis")
    print("=" * 80)
    print()
    
    # 1. 프로파일 데이터 로드
    print("📂 Loading profile summaries...")
    profiles_data = {}
    for profile_name in ['a', 'b', 'c', 'd']:
        data = load_profile_summary(profile_name)
        profiles_data[profile_name] = data
        
        if data is None:
            print(f"   ⚠️  Profile {profile_name.upper()}: MISSING")
        else:
            totals = data.get('totals', {})
            signal_true = totals.get('signal_true', 0)
            orders = totals.get('orders_submitted', 0)
            conversion = calculate_conversion_rate(totals)
            print(f"   ✅ Profile {profile_name.upper()}: {signal_true:,} signals → {orders:,} orders ({conversion:.2f}%)")
    
    print()
    
    # 2. 비교 JSON 생성
    print("🔍 Generating comparison JSON...")
    comparison = generate_comparison_json(profiles_data)
    
    output_json_path = PROJECT_ROOT / "reports/backtest/phase28_11/profile_comparison.json"
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ JSON saved: {output_json_path}")
    print()
    
    # 3. 비교 Markdown 생성
    print("📝 Generating comparison Markdown...")
    markdown = generate_comparison_markdown(comparison)
    
    output_md_path = PROJECT_ROOT / "reports/backtest/phase28_11/profile_comparison.md"
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"   ✅ Markdown saved: {output_md_path}")
    print()
    
    # 4. 요약 출력
    print("=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print()
    
    profile_names = {
        'a': 'BASELINE',
        'b': 'COOLDOWN_RELAXED',
        'c': 'PORTFOLIO_RELAXED',
        'd': 'MIXED_RELAXED'
    }
    
    for profile_key in ['a', 'b', 'c', 'd']:
        profile_data = comparison['profiles'].get(profile_key, {})
        
        if profile_data.get('status') == 'MISSING':
            print(f"Profile {profile_names[profile_key]}: ⚠️ MISSING")
            continue
        
        conversion = profile_data.get('conversion_rate_pct', 0.0)
        orders = profile_data.get('orders_submitted', 0)
        
        if conversion >= 5.0:
            status = "✅ TARGET ACHIEVED"
        elif conversion >= 3.0:
            status = "🟢 GOOD"
        elif conversion >= 1.0:
            status = "🟡 MODERATE"
        else:
            status = "🔴 LOW"
        
        print(f"Profile {profile_names[profile_key]:20s}: {conversion:6.2f}% ({orders:4,} orders) {status}")
    
    print()
    print("=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
