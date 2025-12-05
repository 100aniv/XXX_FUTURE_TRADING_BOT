#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-6: Signal Parity Analyzer (연구/분석용)
================================================
⚠️ 이 스크립트는 엔진이 아니라 통계 분석 도구입니다.
⚠️ 엔진 루프는 execution.engine.run_v2()가 단일 소스입니다.

Offline Scan ↔ Engine Replay 신호 정합성 심층 분석

목표:
- Bar-level 단위 정합성 비교
- Offline-only / Replay-only 신호 식별
- Warmup/NaN 처리 방식 차이 분석
- Regime/LONG/SHORT 분포 비교

Usage:
    python scripts/research/phase27_6_signal_parity_analyzer.py \\
        --offline-summary docs/PHASE27/phase27_4_btc5m_baseline_signal_scan_summary.json \\
        --replay-summary docs/PHASE27/phase27_5_btc5m_engine_replay_summary.json \\
        --output docs/PHASE27/phase27_6_signal_parity_analysis.json
"""
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime
import pandas as pd
import numpy as np

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def log(msg: str):
    """로그 출력"""
    print(f"[PHASE27-6 PARITY ANALYZER] {msg}")


def load_summary(file_path: Path) -> Dict[str, Any]:
    """Summary JSON 로드"""
    log(f"Summary 로드: {file_path}")
    
    if not file_path.exists():
        raise FileNotFoundError(f"Summary 파일 없음: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_offline_signals(offline_summary: Dict[str, Any]) -> pd.DataFrame:
    """
    Offline Scan 결과에서 신호 정보 추출
    
    Returns:
        DataFrame with columns: index, time, has_signal, side, regime
    """
    scan_result = offline_summary.get('scan_result', {})
    signal_details = scan_result.get('signal_details', [])
    
    # 신호가 발생한 bar의 인덱스와 정보
    signal_map = {}
    for detail in signal_details:
        idx = detail['index']
        signal_map[idx] = {
            'has_signal': True,
            'side': detail.get('side'),
            'regime': detail.get('regime', 'UNKNOWN')
        }
    
    # 전체 평가 범위
    total_bars = scan_result.get('total_bars', 0)
    warmup_skipped = scan_result.get('warmup_skipped', 50)
    
    records = []
    for i in range(warmup_skipped, total_bars):
        if i in signal_map:
            records.append({
                'index': i,
                'has_signal': True,
                'side': signal_map[i]['side'],
                'regime': signal_map[i]['regime']
            })
        else:
            records.append({
                'index': i,
                'has_signal': False,
                'side': None,
                'regime': None
            })
    
    df = pd.DataFrame(records)
    log(f"Offline 신호 추출 완료: {len(df)}개 bars, {df['has_signal'].sum()}개 신호")
    
    return df


def extract_replay_signals(replay_summary: Dict[str, Any]) -> pd.DataFrame:
    """
    Engine Replay 결과에서 신호 정보 추출
    
    Note:
        현재 TradeActivityTracker는 per-bar 정보를 저장하지 않으므로,
        이 함수는 총 카운트만 반환합니다.
    
    Returns:
        DataFrame (향후 per-bar 로그 추가 시 사용)
    """
    totals = replay_summary.get('totals', {})
    
    # 현재는 총 카운트만 있음
    total_calls = totals.get('strategy_signals_total', 0)
    signal_true = totals.get('strategy_signals_true', 0)
    signal_false = totals.get('strategy_signals_false', 0)
    
    log(f"Replay 신호 집계: {total_calls}개 calls, {signal_true}개 신호")
    
    # per-bar 데이터 없으므로 빈 DataFrame 반환 (향후 확장 대비)
    return pd.DataFrame({
        'total_calls': [total_calls],
        'signal_true': [signal_true],
        'signal_false': [signal_false]
    })


def analyze_aggregate_parity(
    offline_summary: Dict[str, Any],
    replay_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Aggregate 수준 정합성 분석
    
    Returns:
        분석 결과 딕셔너리
    """
    log("=" * 60)
    log("Aggregate Parity 분석 시작")
    log("=" * 60)
    
    # Offline 통계
    offline_scan = offline_summary.get('scan_result', {})
    offline_total = offline_scan.get('total_bars', 0)
    offline_warmup = offline_scan.get('warmup_skipped', 0)
    offline_evaluated = offline_scan.get('evaluated_bars', 0)
    offline_signals_true = offline_scan.get('signals_true', 0)
    offline_signals_false = offline_scan.get('signals_false', 0)
    offline_long = offline_scan.get('long_signals', 0)
    offline_short = offline_scan.get('short_signals', 0)
    offline_range = offline_scan.get('regime_range_signals', 0)
    offline_trend = offline_scan.get('regime_trend_signals', 0)
    
    # Replay 통계
    replay_totals = replay_summary.get('totals', {})
    replay_calls = replay_totals.get('strategy_signals_total', 0)
    replay_signals_true = replay_totals.get('strategy_signals_true', 0)
    replay_signals_false = replay_totals.get('strategy_signals_false', 0)
    replay_long = replay_totals.get('long_signals', 0)
    replay_short = replay_totals.get('short_signals', 0)
    replay_range = replay_totals.get('regime_range', 0)
    replay_trend = replay_totals.get('regime_trend', 0)
    
    # 차이 계산
    bar_diff = replay_calls - offline_evaluated
    bar_diff_pct = (bar_diff / offline_evaluated * 100) if offline_evaluated > 0 else 0
    
    signal_diff = replay_signals_true - offline_signals_true
    signal_diff_pct = (signal_diff / offline_signals_true * 100) if offline_signals_true > 0 else 0
    
    # 신호 비율
    offline_signal_rate = (offline_signals_true / offline_evaluated * 100) if offline_evaluated > 0 else 0
    replay_signal_rate = (replay_signals_true / replay_calls * 100) if replay_calls > 0 else 0
    rate_diff = replay_signal_rate - offline_signal_rate
    
    analysis = {
        'offline': {
            'total_bars': offline_total,
            'warmup_skipped': offline_warmup,
            'evaluated_bars': offline_evaluated,
            'signals_true': offline_signals_true,
            'signals_false': offline_signals_false,
            'signal_rate': round(offline_signal_rate, 2),
            'long_signals': offline_long,
            'short_signals': offline_short,
            'long_ratio': round((offline_long / offline_signals_true * 100) if offline_signals_true > 0 else 0, 2),
            'regime_range_signals': offline_range,
            'regime_trend_signals': offline_trend
        },
        'replay': {
            'total_calls': replay_calls,
            'signals_true': replay_signals_true,
            'signals_false': replay_signals_false,
            'signal_rate': round(replay_signal_rate, 2),
            'long_signals': replay_long,
            'short_signals': replay_short,
            'long_ratio': round((replay_long / replay_signals_true * 100) if replay_signals_true > 0 else 0, 2),
            'regime_range': replay_range,
            'regime_trend': replay_trend
        },
        'diff': {
            'bar_count_diff': bar_diff,
            'bar_count_diff_pct': round(bar_diff_pct, 2),
            'signal_count_diff': signal_diff,
            'signal_count_diff_pct': round(signal_diff_pct, 2),
            'signal_rate_diff': round(rate_diff, 2)
        },
        'acceptance': {
            'bar_count_within_10pct': abs(bar_diff_pct) <= 10.0,
            'signal_count_within_10pct': abs(signal_diff_pct) <= 10.0,
            'overall_pass': abs(signal_diff_pct) <= 10.0
        }
    }
    
    # 출력
    log("\n📊 Offline Scan:")
    log(f"  - Total bars: {offline_total:,}")
    log(f"  - Warmup skipped: {offline_warmup}")
    log(f"  - Evaluated bars: {offline_evaluated:,}")
    log(f"  - Signals (True): {offline_signals_true:,} ({offline_signal_rate:.1f}%)")
    log(f"  - LONG: {offline_long:,} ({analysis['offline']['long_ratio']:.1f}%)")
    log(f"  - SHORT: {offline_short:,}")
    log(f"  - Regime RANGE: {offline_range:,}")
    log(f"  - Regime TREND: {offline_trend:,}")
    
    log("\n📊 Engine Replay:")
    log(f"  - Total calls: {replay_calls:,}")
    log(f"  - Signals (True): {replay_signals_true:,} ({replay_signal_rate:.1f}%)")
    if replay_long > 0 or replay_short > 0:
        replay_long_ratio = (replay_long / replay_signals_true * 100) if replay_signals_true > 0 else 0
        log(f"  - LONG: {replay_long:,} ({replay_long_ratio:.1f}%)")
        log(f"  - SHORT: {replay_short:,}")
    else:
        log(f"  - LONG/SHORT: N/A")
    if replay_range > 0 or replay_trend > 0:
        log(f"  - Regime RANGE: {replay_range:,}")
        log(f"  - Regime TREND: {replay_trend:,}")
    else:
        log(f"  - Regime: N/A")
    
    log("\n📊 차이:")
    log(f"  - Bar 수: {bar_diff:+,} ({bar_diff_pct:+.2f}%)")
    log(f"  - 신호 수: {signal_diff:+,} ({signal_diff_pct:+.2f}%)")
    log(f"  - Signal Rate: {rate_diff:+.2f}%p")
    
    log("\n판정:")
    if analysis['acceptance']['overall_pass']:
        log("  ✅ PASS - Signal count parity ±10% 이내")
    else:
        log(f"  ❌ FAIL - Signal count parity {abs(signal_diff_pct):.1f}% (허용: 10%)")
    
    return analysis


def analyze_warmup_nan_handling(offline_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Warmup/NaN 처리 방식 분석
    
    Returns:
        분석 결과
    """
    log("=" * 60)
    log("Warmup/NaN 처리 분석")
    log("=" * 60)
    
    scan_result = offline_summary.get('scan_result', {})
    
    total_bars = scan_result.get('total_bars', 0)
    warmup_skipped = scan_result.get('warmup_skipped', 0)
    evaluated_bars = scan_result.get('evaluated_bars', 0)
    
    analysis = {
        'offline': {
            'total_bars': total_bars,
            'warmup_skipped': warmup_skipped,
            'evaluated_bars': evaluated_bars,
            'warmup_method': 'Fixed N bars (N=50)'
        },
        'replay': {
            'warmup_method': 'Engine default (to be verified)',
            'note': 'Engine의 warmup 처리는 add_indicators() + min_bars_for_signal 설정에 의존'
        },
        'potential_issue': {
            'description': 'Offline은 고정 50 bars warmup, Replay는 indicator별 warmup 기간이 다를 수 있음',
            'recommendation': 'add_indicators()의 warmup 처리와 Offline의 min_bars를 일치시킬 것'
        }
    }
    
    log("\n🔍 Warmup 처리:")
    log(f"  - Offline: 고정 {warmup_skipped} bars skip")
    log(f"  - Replay: Engine default (indicator별 차이 가능)")
    log("\n⚠️  잠재적 문제:")
    log(f"  - {analysis['potential_issue']['description']}")
    log(f"  - {analysis['potential_issue']['recommendation']}")
    
    return analysis


def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """
    분석 결과 기반 권장사항 생성
    
    Returns:
        권장사항 리스트
    """
    recommendations = []
    
    diff_pct = abs(analysis['diff']['signal_count_diff_pct'])
    bar_diff_pct = abs(analysis['diff']['bar_count_diff_pct'])
    
    if diff_pct > 10.0:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Signal Count Parity',
            'issue': f'신호 수 차이 {diff_pct:.1f}% (허용: 10%)',
            'action': [
                'Offline Scan과 Engine Replay의 indicator 계산 경로 확인',
                'add_indicators() warmup 처리 통일',
                'signal_logic()와 BaseStrategy.compute_signal() 동등성 검증'
            ]
        })
    
    if bar_diff_pct > 2.0:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Bar Count Parity',
            'issue': f'평가 bar 수 차이 {bar_diff_pct:.1f}%',
            'action': [
                'Offline의 warmup (50 bars)와 Engine의 min_bars_for_signal 일치 확인',
                'CSV 로딩 시 timestamp 변환 일관성 확인',
                'Engine buffer의 데이터 범위 검증'
            ]
        })
    
    # PHASE27-6: TradeActivityTracker 확장 완료 여부 확인
    replay_long = analysis['replay'].get('long_signals', 0)
    replay_regime_range = analysis['replay'].get('regime_range', 0)
    
    if replay_long == 0 and replay_regime_range == 0:
        # 아직 구현되지 않음
        recommendations.append({
            'priority': 'HIGH',
            'category': 'TradeActivityTracker Enhancement',
            'issue': 'LONG/SHORT/Regime 분리 카운트 없음',
            'action': [
                'TradeActivityTracker.record_strategy_signal()에 side, regime 인자 추가',
                'Summary JSON에 long/short/regime 필드 추가',
                'Engine Hook에서 signal dict의 side/metadata 전달'
            ]
        })
    else:
        # 구현 완료, Regime 차이 분석
        offline_regime_range_pct = (analysis['offline']['regime_range_signals'] / analysis['offline']['signals_true'] * 100) if analysis['offline']['signals_true'] > 0 else 0
        replay_regime_range_pct = (replay_regime_range / analysis['replay']['signals_true'] * 100) if analysis['replay']['signals_true'] > 0 else 0
        regime_diff = abs(offline_regime_range_pct - replay_regime_range_pct)
        
        if regime_diff > 10.0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Regime Classification Parity',
                'issue': f'Regime 분류 차이 {regime_diff:.1f}%p (RANGE/TREND 비율)',
                'action': [
                    'Offline vs Replay ADX 계산 결과 비교',
                    'adx_trend_threshold 파라미터 일치 확인',
                    'Signal metadata의 regime 설정 방식 검증'
                ]
            })
    
    return recommendations


def save_analysis(output_path: Path, analysis: Dict[str, Any]):
    """분석 결과 저장"""
    log("=" * 60)
    log(f"분석 결과 저장: {output_path}")
    log("=" * 60)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    log(f"✅ 저장 완료: {output_path}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PHASE27-6: Signal Parity Analyzer")
    parser.add_argument(
        '--offline-summary',
        type=Path,
        default=PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_4_btc5m_baseline_signal_scan_summary.json',
        help='Offline Scan Summary JSON 경로'
    )
    parser.add_argument(
        '--replay-summary',
        type=Path,
        default=PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_5_btc5m_engine_replay_summary.json',
        help='Engine Replay Summary JSON 경로'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=PROJECT_ROOT / 'docs' / 'PHASE27' / 'phase27_6_signal_parity_analysis.json',
        help='분석 결과 출력 경로'
    )
    
    args = parser.parse_args()
    
    log("=" * 80)
    log("🔍 PHASE27-6: Signal Parity Deep Dive Analysis")
    log("=" * 80)
    
    # Summary 로드
    offline_summary = load_summary(args.offline_summary)
    replay_summary = load_summary(args.replay_summary)
    
    # 분석 실행
    aggregate_analysis = analyze_aggregate_parity(offline_summary, replay_summary)
    warmup_analysis = analyze_warmup_nan_handling(offline_summary)
    recommendations = generate_recommendations(aggregate_analysis)
    
    # 최종 결과
    final_analysis = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'offline_summary_file': str(args.offline_summary),
            'replay_summary_file': str(args.replay_summary)
        },
        'aggregate_parity': aggregate_analysis,
        'warmup_nan_analysis': warmup_analysis,
        'recommendations': recommendations,
        'conclusion': {
            'overall_status': 'PASS' if aggregate_analysis['acceptance']['overall_pass'] else 'FAIL',
            'signal_count_diff_pct': aggregate_analysis['diff']['signal_count_diff_pct'],
            'acceptance_threshold': '±10%',
            'next_steps': [
                'TradeActivityTracker에 LONG/SHORT/Regime 카운트 추가',
                'Warmup 처리 통일',
                'Indicator 계산 경로 검증',
                'Per-bar 로깅 추가 (선택적)'
            ]
        }
    }
    
    # 저장
    save_analysis(args.output, final_analysis)
    
    # 최종 요약 출력
    log("\n" + "=" * 80)
    log("📊 최종 요약")
    log("=" * 80)
    log(f"상태: {final_analysis['conclusion']['overall_status']}")
    log(f"신호 수 차이: {final_analysis['conclusion']['signal_count_diff_pct']}% (허용: ±10%)")
    log(f"\n권장사항: {len(recommendations)}개")
    for i, rec in enumerate(recommendations, 1):
        log(f"  {i}. [{rec['priority']}] {rec['category']}: {rec['issue']}")
    
    return 0 if final_analysis['conclusion']['overall_status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
