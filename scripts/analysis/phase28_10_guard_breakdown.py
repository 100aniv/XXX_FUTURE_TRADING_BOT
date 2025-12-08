#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-10: Guard & Filter Breakdown Analysis
==============================================
TradeActivityTracker Summary로부터 Guard rejection breakdown을 분석하여
JSON + Markdown 리포트를 생성한다.

Usage:
    python scripts/analysis/phase28_10_guard_breakdown.py \\
        --input reports/backtest/phase28_10/guard_diag_3m_summary.json \\
        --output-json reports/backtest/phase28_10/guard_breakdown.json \\
        --output-md docs/PHASE28/PHASE28_10_GUARD_BREAKDOWN_REPORT.md
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


def load_summary(input_path: str) -> dict:
    """Load TradeActivityTracker summary JSON."""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_guard_blocks(summary: dict) -> dict:
    """Analyze guard rejection breakdown."""
    totals = summary.get('totals', {})
    signal_true = totals.get('strategy_signals_true', 0)
    guard_blocks_total = totals.get('guard_blocks_total', 0)
    orders_submitted = totals.get('orders_submitted', 0)
    
    # Collect guard blocks by reason
    guard_blocks_by_reason = {}
    for symbol, symbol_data in summary.get('symbols', {}).items():
        for reason, count in symbol_data.get('guard_blocks', {}).items():
            guard_blocks_by_reason[reason] = guard_blocks_by_reason.get(reason, 0) + count
    
    # Sort by count descending
    sorted_reasons = sorted(guard_blocks_by_reason.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate percentages and cumulative
    breakdown = []
    cumulative_count = 0
    for reason, count in sorted_reasons:
        pct = (count / signal_true * 100) if signal_true > 0 else 0.0
        cumulative_count += count
        cumulative_pct = (cumulative_count / signal_true * 100) if signal_true > 0 else 0.0
        breakdown.append({
            'reason': reason,
            'count': count,
            'percent_of_signals': round(pct, 2),
            'cumulative_count': cumulative_count,
            'cumulative_percent': round(cumulative_pct, 2),
        })
    
    # Conversion rate
    conversion_rate = (orders_submitted / signal_true * 100) if signal_true > 0 else 0.0
    
    return {
        'summary': {
            'run_id': summary.get('run_id', 'N/A'),
            'timestamp': summary.get('timestamp', 'N/A'),
            'end_timestamp': summary.get('end_timestamp', 'N/A'),
            'signal_true': signal_true,
            'guard_blocks_total': guard_blocks_total,
            'orders_submitted': orders_submitted,
            'conversion_rate_pct': round(conversion_rate, 2),
        },
        'breakdown': breakdown,
    }


def generate_json_report(analysis: dict, output_path: str):
    """Generate JSON report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON report saved: {output_path}")


def generate_markdown_report(analysis: dict, output_path: str):
    """Generate Markdown report."""
    summary = analysis['summary']
    breakdown = analysis['breakdown']
    
    lines = [
        "# PHASE28-10: Guard & Filter Breakdown Report",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 📊 Summary",
        "",
        f"- **Run ID**: `{summary['run_id']}`",
        f"- **Timestamp**: `{summary['timestamp']}` → `{summary['end_timestamp']}`",
        f"- **Signal True**: {summary['signal_true']:,}",
        f"- **Guard Blocks Total**: {summary['guard_blocks_total']:,}",
        f"- **Orders Submitted**: {summary['orders_submitted']:,}",
        f"- **Conversion Rate**: **{summary['conversion_rate_pct']:.2f}%**",
        "",
        "---",
        "",
        "## 🚫 Guard Rejection Breakdown",
        "",
        "| Rank | Reason | Count | % of Signals | Cumulative | Cumulative % |",
        "|------|--------|-------|--------------|------------|--------------|",
    ]
    
    for idx, item in enumerate(breakdown, start=1):
        lines.append(
            f"| {idx} | `{item['reason']}` | {item['count']:,} | {item['percent_of_signals']:.2f}% | {item['cumulative_count']:,} | {item['cumulative_percent']:.2f}% |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 🔍 Top 3 Blocking Factors",
        "",
    ])
    
    for idx, item in enumerate(breakdown[:3], start=1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉"
        lines.extend([
            f"### {emoji} #{idx}: `{item['reason']}`",
            "",
            f"- **Count**: {item['count']:,} ({item['percent_of_signals']:.2f}% of signals)",
            f"- **Description**: {get_reason_description(item['reason'])}",
            "",
        ])
    
    lines.extend([
        "---",
        "",
        "## 💡 Recommendations",
        "",
    ])
    
    # Generate recommendations based on top reasons
    if breakdown:
        top1 = breakdown[0]['reason']
        if 'COOLDOWN' in top1:
            lines.extend([
                "### 1. Cooldown Optimization",
                "",
                "- The cooldown filter is the **#1 blocking factor**.",
                "- **Action**: Review and relax cooldown parameters in `signals/signal_generator.py`.",
                "- **Config Key**: `cooldown_minutes` (currently applied per signal side).",
                "",
            ])
        
        if len(breakdown) > 1:
            top2 = breakdown[1]['reason']
            if 'PORTFOLIO' in top2:
                lines.extend([
                    "### 2. Portfolio Guard Refinement",
                    "",
                    "- `GUARD_PORTFOLIO_CAN_OPEN` is blocking a significant portion of signals.",
                    "- **Action**: Analyze `PortfolioManager.can_open_position()` logic.",
                    "- **Possible causes**: max_positions, exposure limits, budget cap.",
                    "",
                ])
        
        if len(breakdown) > 2:
            top3 = breakdown[2]['reason']
            if 'VOLUME_SPIKE' in top3:
                lines.extend([
                    "### 3. Volume Spike Filter Review",
                    "",
                    "- Volume spike filter is blocking signals during high volatility.",
                    "- **Action**: Consider adjusting `vol_spike_mult` or disabling in trending markets.",
                    "",
                ])
    
    lines.extend([
        "---",
        "",
        "## 📝 Notes",
        "",
        "- This report is purely **diagnostic**. No strategy logic or guard parameters were changed in PHASE28-10.",
        "- Use this analysis as input for PHASE28-11 (Guard Optimization).",
        "",
    ])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Markdown report saved: {output_path}")


def get_reason_description(reason: str) -> str:
    """Get human-readable description for guard reason."""
    descriptions = {
        'FILTER_COOLDOWN_ACTIVE': 'Signal was blocked due to active cooldown period after recent signal.',
        'GUARD_PORTFOLIO_CAN_OPEN': 'Signal was blocked by PortfolioManager (max_positions, exposure, or budget cap).',
        'FILTER_VOLUME_SPIKE': 'Signal was blocked due to abnormal volume spike detection.',
        'FILTER_REGIME_NOT_ALLOWED': 'Signal was blocked due to unfavorable market regime.',
        'FILTER_TREND_NOT_ALIGNED': 'Signal was blocked due to EMA trend misalignment.',
        'FILTER_MTF_NOT_CONFIRMED': 'Signal was blocked due to multi-timeframe confirmation failure.',
        'FILTER_SESSION_NOT_ALLOWED': 'Signal was blocked due to session whitelist check.',
        'FILTER_RR_BELOW_MIN': 'Signal was blocked due to risk-reward ratio below minimum threshold.',
        'GUARD_RISK_ALLOW_ENTRY': 'Signal was blocked by RiskManager.allow_entry().',
        'GUARD_POSITION_SIZE_ZERO': 'Signal was blocked due to position size calculation resulting in zero.',
        'GUARD_SIGNAL_IDEMPOTENCY': 'Signal was blocked due to Redis idempotency check (duplicate signal).',
        'GUARD_RISK_CHECK_ORDER': 'Signal was blocked by RiskManager.check_order().',
        'GUARD_EQUITY_DEPLETED': 'Signal was blocked due to equity depletion.',
        'GUARD_CONSECUTIVE_LOSS_COOLDOWN': 'Signal was blocked due to consecutive loss cooldown.',
        'GUARD_DAILY_LOSS_LIMIT': 'Signal was blocked due to daily loss limit breach.',
        'GUARD_EQUITY_STOP': 'Signal was blocked due to equity stop limit.',
        'GUARD_MAX_POSITIONS': 'Signal was blocked due to maximum positions limit.',
        'GUARD_SYMBOL_EXPOSURE': 'Signal was blocked due to symbol exposure limit.',
        'GUARD_MIN_NOTIONAL': 'Signal was blocked due to minimum notional value check.',
    }
    return descriptions.get(reason, 'Unknown guard reason.')


def main():
    parser = argparse.ArgumentParser(description='PHASE28-10 Guard Breakdown Analysis')
    parser.add_argument('--input', required=True, help='Input TradeActivityTracker summary JSON path')
    parser.add_argument('--output-json', required=True, help='Output JSON report path')
    parser.add_argument('--output-md', required=True, help='Output Markdown report path')
    args = parser.parse_args()
    
    # Validate input
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Load summary
    print(f"📖 Loading summary: {args.input}")
    summary = load_summary(args.input)
    
    # Analyze
    print("🔍 Analyzing guard rejection breakdown...")
    analysis = analyze_guard_blocks(summary)
    
    # Generate reports
    print("📝 Generating reports...")
    generate_json_report(analysis, args.output_json)
    generate_markdown_report(analysis, args.output_md)
    
    print("\n✅ PHASE28-10 Guard Breakdown Analysis Complete!")
    print(f"   - JSON: {args.output_json}")
    print(f"   - Markdown: {args.output_md}")


if __name__ == '__main__':
    main()
