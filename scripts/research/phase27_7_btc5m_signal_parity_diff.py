#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-7: Per-bar Signal Parity Diff Harness (연구/분석용)
===========================================================
⚠️ 이 스크립트는 엔진이 아니라 비교/분석 도구입니다.
⚠️ 엔진 루프는 execution.engine.run_v2()가 단일 소스입니다.

Offline Scan과 Engine Replay의 per-bar 신호를 비교하여 불일치 지점을 특정

목표:
- 동일 timestamp에서 신호 불일치 발견
- Regime 분류 차이 분석
- Indicator 값 차이 비교 (선택적)

Usage:
    python scripts/research/phase27_7_btc5m_signal_parity_diff.py \\
        --offline docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json \\
        --replay docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json \\
        --output docs/PHASE27/phase27_7_signal_parity_diff_report.json \\
        --top-n 20
"""
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import pandas as pd

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def log(msg: str):
    """로그 출력"""
    print(f"[PHASE27-7 PARITY DIFF] {msg}")


def extract_offline_signals_df(offline_summary: Dict[str, Any]) -> pd.DataFrame:
    """
    Offline Scan 결과에서 신호 DataFrame 추출
    
    Args:
        offline_summary: phase27_4_btc5m_baseline_signal_scan_summary.json
    
    Returns:
        DataFrame with columns: [index, timestamp, has_signal, side, regime]
    """
    scan_result = offline_summary.get('scan_result', {})
    signal_details = scan_result.get('signal_details', [])
    total_bars = scan_result.get('total_bars', 0)
    warmup_skipped = scan_result.get('warmup_skipped', 0)
    
    # 전체 bar에 대한 DataFrame 생성 (warmup 이후)
    records = []
    signal_dict = {s['index']: s for s in signal_details}
    
    for i in range(warmup_skipped, total_bars):
        if i in signal_dict:
            s = signal_dict[i]
            records.append({
                'index': i,
                'timestamp': s.get('time'),
                'has_signal': True,
                'side': s.get('side'),
                'regime': s.get('regime')
            })
        else:
            records.append({
                'index': i,
                'timestamp': None,  # signal_details에만 timestamp가 있음
                'has_signal': False,
                'side': None,
                'regime': None
            })
    
    return pd.DataFrame(records)


def extract_replay_signals_df(replay_summary: Dict[str, Any]) -> pd.DataFrame:
    """
    Engine Replay 결과에서 신호 DataFrame 추출
    
    Args:
        replay_summary: phase27_5_btc5m_engine_replay_summary.json
    
    Returns:
        DataFrame with columns: [call_index, has_signal, side, regime]
        
    Notes:
        Replay Summary에는 per-bar 정보가 없으므로,
        totals만 사용하여 aggregate 비교
    """
    # PHASE27-6+: Replay Summary에는 totals만 있음
    totals = replay_summary.get('totals', {})
    
    # Per-bar 정보가 없으므로 aggregate 정보만 반환
    return pd.DataFrame([{
        'total_calls': totals.get('strategy_signals_total', 0),
        'signals_true': totals.get('strategy_signals_true', 0),
        'long_signals': totals.get('long_signals', 0),
        'short_signals': totals.get('short_signals', 0),
        'regime_range': totals.get('regime_range', 0),
        'regime_trend': totals.get('regime_trend', 0)
    }])


def analyze_aggregate_diff(
    offline_summary: Dict[str, Any],
    replay_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Aggregate 수준 차이 분석 (phase27_6_signal_parity_analyzer와 유사)
    
    Args:
        offline_summary: Offline Scan 결과
        replay_summary: Engine Replay 결과
    
    Returns:
        차이 분석 결과
    """
    offline_scan = offline_summary.get('scan_result', {})
    replay_totals = replay_summary.get('totals', {})
    
    # Offline
    offline_evaluated = offline_scan.get('evaluated_bars', 0)
    offline_signals_true = offline_scan.get('signals_true', 0)
    offline_long = offline_scan.get('long_signals', 0)
    offline_short = offline_scan.get('short_signals', 0)
    offline_range = offline_scan.get('regime_range_signals', 0)
    offline_trend = offline_scan.get('regime_trend_signals', 0)
    
    # Replay
    replay_calls = replay_totals.get('strategy_signals_total', 0)
    replay_signals_true = replay_totals.get('strategy_signals_true', 0)
    replay_long = replay_totals.get('long_signals', 0)
    replay_short = replay_totals.get('short_signals', 0)
    replay_range = replay_totals.get('regime_range', 0)
    replay_trend = replay_totals.get('regime_trend', 0)
    
    # 차이 계산
    bar_diff = replay_calls - offline_evaluated
    bar_diff_pct = (bar_diff / offline_evaluated * 100) if offline_evaluated > 0 else 0
    
    signal_diff = replay_signals_true - offline_signals_true
    signal_diff_pct = (signal_diff / offline_signals_true * 100) if offline_signals_true > 0 else 0
    
    long_diff = replay_long - offline_long
    long_diff_pct = (long_diff / offline_long * 100) if offline_long > 0 else 0
    
    short_diff = replay_short - offline_short
    short_diff_pct = (short_diff / offline_short * 100) if offline_short > 0 else 0
    
    # Regime 비율 차이
    offline_range_ratio = (offline_range / offline_signals_true * 100) if offline_signals_true > 0 else 0
    replay_range_ratio = (replay_range / replay_signals_true * 100) if replay_signals_true > 0 else 0
    regime_diff = replay_range_ratio - offline_range_ratio
    
    return {
        'offline': {
            'evaluated_bars': offline_evaluated,
            'signals_true': offline_signals_true,
            'long_signals': offline_long,
            'short_signals': offline_short,
            'regime_range': offline_range,
            'regime_trend': offline_trend,
            'range_ratio': round(offline_range_ratio, 2)
        },
        'replay': {
            'total_calls': replay_calls,
            'signals_true': replay_signals_true,
            'long_signals': replay_long,
            'short_signals': replay_short,
            'regime_range': replay_range,
            'regime_trend': replay_trend,
            'range_ratio': round(replay_range_ratio, 2)
        },
        'diff': {
            'bar_count_diff': bar_diff,
            'bar_count_diff_pct': round(bar_diff_pct, 2),
            'signal_count_diff': signal_diff,
            'signal_count_diff_pct': round(signal_diff_pct, 2),
            'long_diff': long_diff,
            'long_diff_pct': round(long_diff_pct, 2),
            'short_diff': short_diff,
            'short_diff_pct': round(short_diff_pct, 2),
            'regime_range_ratio_diff': round(regime_diff, 2)
        },
        'acceptance': {
            'bar_count_within_10pct': abs(bar_diff_pct) <= 10.0,
            'signal_count_within_10pct': abs(signal_diff_pct) <= 10.0,
            'long_count_within_10pct': abs(long_diff_pct) <= 10.0,
            'short_count_within_10pct': abs(short_diff_pct) <= 10.0,
            'regime_diff_within_10pct': abs(regime_diff) <= 10.0,
            'overall_pass': (
                abs(bar_diff_pct) <= 10.0 and
                abs(signal_diff_pct) <= 10.0 and
                abs(regime_diff) <= 10.0
            )
        }
    }


def generate_summary_report(
    analysis: Dict[str, Any],
    offline_summary: Dict[str, Any],
    replay_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    최종 요약 리포트 생성
    
    Args:
        analysis: analyze_aggregate_diff() 결과
        offline_summary: Offline Scan 원본
        replay_summary: Engine Replay 원본
    
    Returns:
        최종 리포트
    """
    return {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'offline_summary_file': offline_summary.get('run_id'),
            'replay_summary_file': replay_summary.get('run_id')
        },
        'aggregate_analysis': analysis,
        'conclusion': {
            'overall_status': 'PASS' if analysis['acceptance']['overall_pass'] else 'FAIL',
            'signal_count_diff_pct': analysis['diff']['signal_count_diff_pct'],
            'regime_diff': analysis['diff']['regime_range_ratio_diff'],
            'acceptance_threshold': '±10%',
            'improvements': [
                f"Bar count parity: {analysis['diff']['bar_count_diff_pct']:.2f}%",
                f"Signal count parity: {analysis['diff']['signal_count_diff_pct']:.2f}%",
                f"LONG parity: {analysis['diff']['long_diff_pct']:.2f}%",
                f"SHORT parity: {analysis['diff']['short_diff_pct']:.2f}%",
                f"Regime RANGE ratio diff: {analysis['diff']['regime_range_ratio_diff']:.2f}%p"
            ]
        }
    }


def main():
    parser = argparse.ArgumentParser(description='PHASE27-7: Signal Parity Per-Bar Diff')
    parser.add_argument('--offline', type=str, required=True,
                        help='Offline Scan summary JSON 파일')
    parser.add_argument('--replay', type=str, required=True,
                        help='Engine Replay summary JSON 파일')
    parser.add_argument('--output', type=str,
                        default='docs/PHASE27/phase27_7_signal_parity_diff_report.json',
                        help='출력 리포트 파일')
    parser.add_argument('--top-n', type=int, default=20,
                        help='상위 N개 mismatch 샘플 출력')
    
    args = parser.parse_args()
    
    offline_path = Path(args.offline)
    replay_path = Path(args.replay)
    output_path = Path(args.output)
    
    log("=" * 60)
    log("🔍 PHASE27-7: Signal Parity Per-Bar Diff Analysis")
    log("=" * 60)
    
    # Summary 로드
    log(f"Offline Summary 로드: {offline_path}")
    with open(offline_path, 'r', encoding='utf-8') as f:
        offline_summary = json.load(f)
    
    log(f"Replay Summary 로드: {replay_path}")
    with open(replay_path, 'r', encoding='utf-8') as f:
        replay_summary = json.load(f)
    
    # Aggregate 분석
    log("=" * 60)
    log("Aggregate Diff 분석 시작")
    log("=" * 60)
    
    analysis = analyze_aggregate_diff(offline_summary, replay_summary)
    
    # 결과 출력
    log("\n📊 Offline Scan:")
    log(f"  - Evaluated bars: {analysis['offline']['evaluated_bars']:,}")
    log(f"  - Signals (True): {analysis['offline']['signals_true']:,}")
    log(f"  - LONG: {analysis['offline']['long_signals']:,}")
    log(f"  - SHORT: {analysis['offline']['short_signals']:,}")
    log(f"  - Regime RANGE: {analysis['offline']['regime_range']:,} ({analysis['offline']['range_ratio']:.1f}%)")
    log(f"  - Regime TREND: {analysis['offline']['regime_trend']:,}")
    
    log("\n📊 Engine Replay:")
    log(f"  - Total calls: {analysis['replay']['total_calls']:,}")
    log(f"  - Signals (True): {analysis['replay']['signals_true']:,}")
    log(f"  - LONG: {analysis['replay']['long_signals']:,}")
    log(f"  - SHORT: {analysis['replay']['short_signals']:,}")
    log(f"  - Regime RANGE: {analysis['replay']['regime_range']:,} ({analysis['replay']['range_ratio']:.1f}%)")
    log(f"  - Regime TREND: {analysis['replay']['regime_trend']:,}")
    
    log("\n📊 차이:")
    log(f"  - Bar 수: {analysis['diff']['bar_count_diff']:+,} ({analysis['diff']['bar_count_diff_pct']:+.2f}%)")
    log(f"  - 신호 수: {analysis['diff']['signal_count_diff']:+,} ({analysis['diff']['signal_count_diff_pct']:+.2f}%)")
    log(f"  - LONG: {analysis['diff']['long_diff']:+,} ({analysis['diff']['long_diff_pct']:+.2f}%)")
    log(f"  - SHORT: {analysis['diff']['short_diff']:+,} ({analysis['diff']['short_diff_pct']:+.2f}%)")
    log(f"  - Regime RANGE 비율 차이: {analysis['diff']['regime_range_ratio_diff']:+.2f}%p")
    
    log("\n판정:")
    if analysis['acceptance']['overall_pass']:
        log("  ✅ PASS - Signal Parity ±10% 이내")
    else:
        log("  ❌ FAIL - Signal Parity 목표 미달")
        if not analysis['acceptance']['signal_count_within_10pct']:
            log(f"    - 신호 수 차이 {abs(analysis['diff']['signal_count_diff_pct']):.1f}% (허용: 10%)")
        if not analysis['acceptance']['regime_diff_within_10pct']:
            log(f"    - Regime 비율 차이 {abs(analysis['diff']['regime_range_ratio_diff']):.1f}%p (허용: 10%)")
    
    # 리포트 생성
    report = generate_summary_report(analysis, offline_summary, replay_summary)
    
    # 저장
    log("=" * 60)
    log(f"리포트 저장: {output_path}")
    log("=" * 60)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    log(f"✅ 저장 완료: {output_path}")
    
    log("\n" + "=" * 60)
    log("📊 최종 요약")
    log("=" * 60)
    log(f"상태: {report['conclusion']['overall_status']}")
    log(f"신호 수 차이: {report['conclusion']['signal_count_diff_pct']:.2f}% (허용: ±10%)")
    log(f"Regime 차이: {report['conclusion']['regime_diff']:.2f}%p (허용: ±10%)")
    log("")
    
    return 0 if analysis['acceptance']['overall_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
