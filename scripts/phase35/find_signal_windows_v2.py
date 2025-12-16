#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-3 ITER13: Signal Window Finder (Simplified)
====================================================

목표:
1. 기존 runner 재사용하여 빠른 스캔
2. 2024년 샘플 기간 테스트 (5~10개 후보)
3. DecisionTrace 분석으로 trades=0 원인 정량화
4. trades>0 window 확보 또는 Light Profile 권고

출력:
- artifacts/phase35/iter13/window_scan.json

Usage:
    python scripts/phase35/find_signal_windows_v2.py
"""
import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from collections import defaultdict

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("find_signal_windows")


def generate_candidate_windows() -> List[Dict[str, str]]:
    """
    2024년 샘플 기간 후보 생성 (수동 선택 - 빠른 실행)
    
    전략:
    - 2024년을 대표하는 5~10개 1M 구간 선정
    - 계절성/시장 상황 고려
    """
    candidates = [
        # Q1 2024
        {'label': '2024_Q1_Jan', 'start': '2024-01-01', 'end': '2024-01-31', 'note': 'New Year Rally'},
        {'label': '2024_Q1_Feb', 'start': '2024-02-01', 'end': '2024-02-29', 'note': 'Pre-Halving'},
        {'label': '2024_Q1_Mar', 'start': '2024-03-01', 'end': '2024-03-31', 'note': 'Q1 Close'},
        
        # Q2 2024
        {'label': '2024_Q2_Apr', 'start': '2024-04-01', 'end': '2024-04-30', 'note': 'Halving Month'},
        {'label': '2024_Q2_May', 'start': '2024-05-01', 'end': '2024-05-31', 'note': 'Post-Halving'},
        
        # Q3 2024
        {'label': '2024_Q3_Jul', 'start': '2024-07-01', 'end': '2024-07-31', 'note': 'Summer Lull'},
        {'label': '2024_Q3_Aug', 'start': '2024-08-01', 'end': '2024-08-31', 'note': 'Late Summer'},
        
        # Q4 2024
        {'label': '2024_Q4_Oct', 'start': '2024-10-01', 'end': '2024-10-31', 'note': 'Pre-Election'},
        {'label': '2024_Q4_Nov', 'start': '2024-11-01', 'end': '2024-11-30', 'note': 'Election Month'},
    ]
    
    logger.info(f"Generated {len(candidates)} candidate windows")
    return candidates


def run_backtest_scan(window: Dict[str, str], config_base_path: Path, run_id: int) -> Dict[str, Any]:
    """
    특정 window에 대해 백테스트 실행 (기존 runner 사용)
    
    Args:
        window: {'label', 'start', 'end', 'note'}
        config_base_path: Base config 경로
        run_id: Run ID
    
    Returns:
        {
            'window': {...},
            'trades': int,
            'win_rate': float,
            'pnl': float,
            'runtime_sec': float,
            'summary_path': str,
            'error': str | None
        }
    """
    import time
    
    logger.info(f"[Scan] {window['label']}: {window['start']} → {window['end']}")
    
    # Temp config 생성
    temp_config = config_base_path.parent / f"temp_scan_{window['label']}.yaml"
    
    try:
        with open(config_base_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 날짜 범위 설정
        if 'backtest' not in config:
            config['backtest'] = {}
        config['backtest']['start_date'] = window['start']
        config['backtest']['end_date'] = window['end']
        
        # DecisionTrace 활성화
        if 'decision_trace' not in config:
            config['decision_trace'] = {}
        config['decision_trace']['enabled'] = True
        
        # Output 경로 고정
        iter13_dir = project_root / "artifacts" / "phase35" / "iter13" / "scans" / window['label']
        iter13_dir.mkdir(parents=True, exist_ok=True)
        
        config['backtest']['output_file'] = str(iter13_dir / "summary.json")
        
        with open(temp_config, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        
        # 백테스트 실행
        start_time = time.time()
        
        # run_iter5_isolated_v2.py 대신 직접 engine 호출 (더 빠름)
        cmd = [
            sys.executable,
            str(project_root / "scripts" / "phase35" / "run_iter5_isolated_v2.py"),
            str(run_id),
            "--config", str(temp_config)
        ]
        
        logger.info(f"  Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=180  # 3분 제한
        )
        
        runtime_sec = time.time() - start_time
        
        # summary.json 파싱
        summary_path = iter13_dir / "summary.json"
        
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            
            return {
                'window': window,
                'trades': summary.get('trades', 0),
                'win_rate': summary.get('win_rate', 0.0),
                'pnl': summary.get('pnl', 0.0),
                'runtime_sec': runtime_sec,
                'summary_path': str(summary_path),
                'error': None
            }
        else:
            # Summary 없으면 stdout에서 추출 시도
            trades = 0
            for line in result.stdout.splitlines():
                if "Trades:" in line or "trades:" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            trades = int(parts[1].strip().split()[0])
                        except:
                            pass
            
            return {
                'window': window,
                'trades': trades,
                'win_rate': 0.0,
                'pnl': 0.0,
                'runtime_sec': runtime_sec,
                'summary_path': None,
                'error': 'No summary.json generated'
            }
    
    except subprocess.TimeoutExpired:
        logger.warning(f"  TIMEOUT: {window['label']}")
        return {
            'window': window,
            'trades': 0,
            'win_rate': 0.0,
            'pnl': 0.0,
            'runtime_sec': 180.0,
            'summary_path': None,
            'error': 'TIMEOUT (180s)'
        }
    
    except Exception as e:
        logger.error(f"  ERROR: {window['label']}: {e}")
        return {
            'window': window,
            'trades': 0,
            'win_rate': 0.0,
            'pnl': 0.0,
            'runtime_sec': 0.0,
            'summary_path': None,
            'error': str(e)
        }
    
    finally:
        # Temp config 삭제
        if temp_config.exists():
            temp_config.unlink()


def analyze_decision_traces(scan_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    DecisionTrace 파일들을 수집하여 차단 reason 분석
    
    Returns:
        {
            'total_decisions': int,
            'total_blocks': int,
            'blocked_reasons_topN': [{'reason': str, 'count': int, 'pct': float}, ...],
            'per_window_summary': [...]
        }
    """
    from common.decision_trace import DecisionTraceAnalyzer
    
    all_traces = []
    per_window_summary = []
    
    for result in scan_results:
        window_label = result['window']['label']
        trace_dir = project_root / "reports" / "backtest" / "phase35" / "traces"
        trace_file = trace_dir / f"decision_trace_{window_label}.json"
        
        # DecisionTrace 파일 탐색 (표준 경로)
        if not trace_file.exists():
            # 대체 경로 시도
            trace_file = trace_dir / "decision_trace.json"
        
        if trace_file.exists():
            logger.info(f"  Analyzing DecisionTrace: {trace_file}")
            analyzer = DecisionTraceAnalyzer(str(trace_file))
            analysis = analyzer.analyze()
            
            summary = analysis.get('summary', {})
            block_reasons = analysis.get('block_reason_analysis', {})
            
            per_window_summary.append({
                'window': window_label,
                'total_decisions': summary.get('total_decisions', 0),
                'entry_count': summary.get('entry_count', 0),
                'block_count': summary.get('block_count', 0),
                'top_blockers': block_reasons.get('top_reasons', [])[:3]
            })
            
            # 전체 traces 누적
            if hasattr(analyzer, 'traces'):
                all_traces.extend(analyzer.traces)
        else:
            logger.warning(f"  No DecisionTrace found for {window_label}")
    
    # 전체 통계
    total_decisions = sum(s['total_decisions'] for s in per_window_summary)
    total_blocks = sum(s['block_count'] for s in per_window_summary)
    
    # Blocked reasons 집계
    reason_counts = defaultdict(int)
    
    for trace in all_traces:
        if trace.get('final_action') == 'BLOCK' and trace.get('block_reason'):
            reason_counts[trace['block_reason']] += 1
    
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    
    blocked_reasons_topN = [
        {
            'reason': reason,
            'count': count,
            'pct': count / total_blocks if total_blocks > 0 else 0.0
        }
        for reason, count in sorted_reasons[:10]
    ]
    
    return {
        'total_decisions': total_decisions,
        'total_blocks': total_blocks,
        'blocked_reasons_topN': blocked_reasons_topN,
        'per_window_summary': per_window_summary
    }


def recommend_light_profile(decision_trace_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    DecisionTrace 분석 기반 Light Profile 권고
    
    Returns:
        {
            'recommended_stage': int (1~4),
            'reason': str,
            'changes': [...]
        }
    """
    top_blockers = decision_trace_analysis.get('blocked_reasons_topN', [])
    
    if not top_blockers:
        return {
            'recommended_stage': 0,
            'reason': 'No blocked reasons found',
            'changes': []
        }
    
    # Top reason 분석
    top_reason = top_blockers[0]['reason']
    top_pct = top_blockers[0]['pct']
    
    if 'confidence' in top_reason.lower() or 'threshold' in top_reason.lower():
        if top_pct > 0.5:
            stage = 2
            reason = f"Top blocker: {top_reason} ({top_pct*100:.1f}%) - confidence threshold too strict"
        else:
            stage = 1
            reason = f"Top blocker: {top_reason} ({top_pct*100:.1f}%) - mild confidence relaxation"
        
        changes = [
            f"Stage {stage}: confidence_threshold 0.70 → {0.70 - stage*0.05:.2f}"
        ]
    
    elif 'consensus' in top_reason.lower() or 'votes' in top_reason.lower():
        stage = 4
        reason = f"Top blocker: {top_reason} ({top_pct*100:.1f}%) - voting too strict"
        changes = [
            "Stage 4: min_votes 2 → 1 (최후 수단)"
        ]
    
    else:
        stage = 1
        reason = f"Top blocker: {top_reason} ({top_pct*100:.1f}%) - try mild relaxation"
        changes = [
            "Stage 1: confidence_threshold 0.70 → 0.65"
        ]
    
    return {
        'recommended_stage': stage,
        'reason': reason,
        'changes': changes
    }


def main():
    logger.info("=" * 80)
    logger.info("PHASE35-3 ITER13: Signal Window Finder (Simplified)")
    logger.info("=" * 80)
    
    # Output 디렉토리 생성
    output_dir = project_root / "artifacts" / "phase35" / "iter13"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Base config
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    if not config_path.exists():
        logger.error(f"❌ Config not found: {config_path}")
        return 1
    
    # 1. Window 후보 생성
    logger.info("=" * 80)
    logger.info("📋 Step 1: Generate Window Candidates")
    logger.info("=" * 80)
    
    windows = generate_candidate_windows()
    for i, w in enumerate(windows, 1):
        logger.info(f"  {i}. {w['label']}: {w['start']} → {w['end']} ({w['note']})")
    
    # 2. 빠른 스캔 실행
    logger.info("=" * 80)
    logger.info("🔄 Step 2: Quick Scan")
    logger.info("=" * 80)
    
    scan_results = []
    for i, window in enumerate(windows, 1):
        logger.info(f"[{i}/{len(windows)}] {window['label']}")
        result = run_backtest_scan(window, config_path, run_id=13000 + i)
        scan_results.append(result)
        logger.info(f"  → Trades: {result['trades']}, WinRate: {result['win_rate']:.2%}, PnL: ${result['pnl']:.2f}, Runtime: {result['runtime_sec']:.1f}s")
    
    # 3. DecisionTrace 분석
    logger.info("=" * 80)
    logger.info("📊 Step 3: DecisionTrace Analysis")
    logger.info("=" * 80)
    
    dt_analysis = analyze_decision_traces(scan_results)
    
    logger.info(f"Total Decisions: {dt_analysis['total_decisions']}")
    logger.info(f"Total Blocks: {dt_analysis['total_blocks']}")
    logger.info("")
    logger.info("Top Blocked Reasons:")
    for i, reason_info in enumerate(dt_analysis['blocked_reasons_topN'][:5], 1):
        logger.info(f"  {i}. {reason_info['reason']}: {reason_info['count']} ({reason_info['pct']*100:.1f}%)")
    
    # 4. Best Window 선정
    logger.info("=" * 80)
    logger.info("🎯 Step 4: Select Best Window")
    logger.info("=" * 80)
    
    valid_windows = [r for r in scan_results if r['trades'] > 0]
    
    if valid_windows:
        best = max(valid_windows, key=lambda x: (x['trades'], x['pnl']))
        logger.info(f"✅ Best Window: {best['window']['label']}")
        logger.info(f"   Date Range: {best['window']['start']} → {best['window']['end']}")
        logger.info(f"   Trades: {best['trades']}")
        logger.info(f"   Win Rate: {best['win_rate']:.2%}")
        logger.info(f"   PnL: ${best['pnl']:.2f}")
    else:
        best = None
        logger.warning("⚠️  No trades>0 window found")
    
    # 5. Light Profile 권고
    logger.info("=" * 80)
    logger.info("💡 Step 5: Light Profile Recommendation")
    logger.info("=" * 80)
    
    recommendation = recommend_light_profile(dt_analysis)
    
    if recommendation['recommended_stage'] > 0:
        logger.info(f"Recommended Stage: {recommendation['recommended_stage']}")
        logger.info(f"Reason: {recommendation['reason']}")
        logger.info("Changes:")
        for change in recommendation['changes']:
            logger.info(f"  - {change}")
    else:
        logger.info("No specific recommendation")
    
    # 6. 결과 저장
    output = {
        'scan_metadata': {
            'scan_timestamp': datetime.now().isoformat(),
            'total_windows_scanned': len(windows),
            'config_used': str(config_path)
        },
        'scan_results': scan_results,
        'decision_trace_analysis': dt_analysis,
        'best_window': best,
        'light_profile_recommendation': recommendation,
        'recommendation_summary': {
            'selected_start_date': best['window']['start'] if best else None,
            'selected_end_date': best['window']['end'] if best else None,
            'expected_trades': best['trades'] if best else 0,
            'needs_light_profile': best is None or best['trades'] < 10
        }
    }
    
    output_file = output_dir / "window_scan.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info("=" * 80)
    logger.info(f"✅ Output saved: {output_file}")
    logger.info("=" * 80)
    
    if best and best['trades'] > 0:
        logger.info("✅ SUCCESS: trades>0 window 확보")
        return 0
    else:
        logger.warning("⚠️  WARNING: trades>0 window 없음, Light Profile 적용 필요")
        return 2  # Warning (not full failure)


if __name__ == "__main__":
    sys.exit(main())
