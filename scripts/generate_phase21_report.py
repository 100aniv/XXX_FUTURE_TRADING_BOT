#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A Report Generator
============================
JSON 결과를 Markdown 리포트로 변환
"""
import json
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent


def generate_report(results_json_path: Path, output_md_path: Path):
    """Generate Markdown report from JSON results"""
    
    # Load results
    with open(results_json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Start building report
    report = []
    report.append("# PHASE21-1A: Single Strategy Smoke Test Report")
    report.append("")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Test overview
    report.append("## Test Overview")
    report.append("")
    report.append("**Objective**: Validate that each strategy (with Ensemble OFF) can generate trades independently")
    report.append("")
    report.append("**Environment**:")
    report.append("- Mode: Paper")
    report.append("- Symbol: BTCUSDT")
    report.append("- Timeframe: 5m")
    report.append("- Runtime per strategy: 1 hour (wall-clock)")
    report.append("- Warmup: 5 minutes (early exit if 0 trades)")
    report.append("")
    report.append("**Acceptance Criteria**:")
    report.append("- Minimum 1 trade in 1 hour")
    report.append("- No errors/tracebacks")
    report.append("- Guards/Risk/Portfolio functioning normally")
    report.append("")
    report.append("---")
    report.append("")
    
    # Results table
    report.append("## Results Summary")
    report.append("")
    report.append("| Strategy | Status | Trades | Meaningful | Note |")
    report.append("|----------|--------|--------|------------|------|")
    
    meaningful_count = 0
    for result in results:
        strategy = result['strategy'].upper()
        status = result['status']
        delta = result.get('delta', 0)
        meaningful = "YES" if result.get('meaningful', False) else "NO"
        reason = result.get('reason', '-')
        
        report.append(f"| {strategy} | {status} | {delta} | {meaningful} | {reason} |")
        
        if result.get('meaningful', False):
            meaningful_count += 1
    
    report.append("")
    report.append(f"**Meaningful tests**: {meaningful_count}/{len(results)}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Detailed findings
    report.append("## Detailed Findings")
    report.append("")
    
    for result in results:
        strategy = result['strategy'].upper()
        status = result['status']
        delta = result.get('delta', 0)
        
        report.append(f"### {strategy}")
        report.append("")
        report.append(f"- **Status**: {status}")
        report.append(f"- **Trades Generated**: {delta}")
        report.append(f"- **Meaningful**: {'YES' if result.get('meaningful', False) else 'NO'}")
        
        if result.get('reason'):
            report.append(f"- **Note**: {result['reason']}")
        
        if result.get('early_exit'):
            report.append(f"- **Early Exit**: Test terminated after {result.get('warmup_minutes', 5)} minutes due to 0 trades")
        
        if result.get('stats'):
            stats = result['stats']
            report.append(f"- **LONG**: {stats.get('long', 0)}")
            report.append(f"- **SHORT**: {stats.get('short', 0)}")
            report.append(f"- **PnL Total**: ${stats.get('pnl_total', 0):.2f}")
            report.append(f"- **PnL Avg**: ${stats.get('pnl_avg', 0):.2f}")
        
        report.append("")
    
    report.append("---")
    report.append("")
    
    # Conclusions
    report.append("## Conclusions")
    report.append("")
    
    # Categorize strategies
    meaningful_strategies = [r['strategy'] for r in results if r.get('meaningful', False)]
    not_meaningful_strategies = [r['strategy'] for r in results if not r.get('meaningful', False)]
    
    if meaningful_strategies:
        report.append(f"**Meaningful strategies** ({len(meaningful_strategies)}):")
        for s in meaningful_strategies:
            report.append(f"- {s.upper()}")
        report.append("")
    
    if not_meaningful_strategies:
        report.append(f"**Not meaningful strategies** ({len(not_meaningful_strategies)}):")
        for s in not_meaningful_strategies:
            result = next((r for r in results if r['strategy'] == s), None)
            reason = result.get('reason', 'No trades') if result else 'Unknown'
            report.append(f"- {s.upper()}: {reason}")
        report.append("")
    
    report.append("**Next Steps**:")
    report.append("")
    
    if meaningful_strategies:
        report.append(f"1. **PHASE21-1B**: Run 12-hour extended tests for meaningful strategies: {', '.join([s.upper() for s in meaningful_strategies])}")
    
    if not_meaningful_strategies:
        report.append(f"2. **PHASE21-1C**: Investigate why these strategies produced no/few trades: {', '.join([s.upper() for s in not_meaningful_strategies])}")
        report.append("   - Check strategy parameters")
        report.append("   - Verify guard/filter conditions")
        report.append("   - Consider different market conditions")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("**Report End**")
    
    # Write report
    report_content = "\n".join(report)
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"[OK] Report generated: {output_md_path}")
    return output_md_path


if __name__ == "__main__":
    results_file = project_root / "docs" / "PHASE21" / "phase21_1a_results.json"
    report_file = project_root / "docs" / "PHASE21" / "PHASE21-1A_REPORT.md"
    
    if not results_file.exists():
        print(f"[ERROR] Results file not found: {results_file}")
        sys.exit(1)
    
    generate_report(results_file, report_file)
