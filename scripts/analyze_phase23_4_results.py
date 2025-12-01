#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE23-4: Ensemble V2 3H Paper Validation Analysis
====================================================
로그 파일을 분석하여 Ensemble V2의 동작을 정량화합니다.
"""
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def parse_ensemble_logs(log_file_path):
    """
    Ensemble V2 로그 파일을 파싱하여 메트릭 추출
    
    Returns:
        dict: 분석 결과 딕셔너리
    """
    metrics = {
        # 전략 평가
        'evaluation_count': 0,
        'strategy_signals': defaultdict(int),  # 전략별 신호 생성 횟수
        'strategy_signal_types': defaultdict(lambda: {'LONG': 0, 'SHORT': 0, 'None': 0}),
        
        # Aggregate 결과
        'aggregate_count': 0,
        'tier_distribution': Counter(),  # tier1, tier2, skip
        'side_distribution': Counter(),  # LONG, SHORT, None
        'skip_reasons': Counter(),
        
        # Score V2 통계
        's_net_values': [],
        's_risk_values': [],
        's_quality_values': [],
        
        # 전략 기여도
        'strategies_count': [],  # 각 aggregate에 참여한 전략 수
        'chosen_strategies': Counter(),  # Tier1/2에서 선택된 전략
    }
    
    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # 전략 평가 시작
            if '전략 평가 시작' in line:
                metrics['evaluation_count'] += 1
            
            # 개별 전략 신호
            # 예: 📊 [ENSEMBLE V2] scalping_v3: side=LONG, S_NET=1.000, S_DIR=LONG, S_RISK=0.287, S_QUALITY=0.900
            strategy_signal_match = re.search(
                r'\[ENSEMBLE V2\] (\w+): side=(\w+), S_NET=([-\d.]+), S_DIR=(\w+), S_RISK=([\d.]+), S_QUALITY=([\d.]+)',
                line
            )
            if strategy_signal_match:
                strategy_name = strategy_signal_match.group(1)
                side = strategy_signal_match.group(2)
                s_net = float(strategy_signal_match.group(3))
                s_risk = float(strategy_signal_match.group(5))
                s_quality = float(strategy_signal_match.group(6))
                
                metrics['strategy_signals'][strategy_name] += 1
                metrics['strategy_signal_types'][strategy_name][side] += 1
                metrics['s_net_values'].append(s_net)
                metrics['s_risk_values'].append(s_risk)
                metrics['s_quality_values'].append(s_quality)
            
            # 신호 없음
            # 예: ⏸ [ENSEMBLE V2] scalping_v3: 신호 없음 (side=None)
            no_signal_match = re.search(r'\[ENSEMBLE V2\] (\w+): 신호 없음', line)
            if no_signal_match:
                strategy_name = no_signal_match.group(1)
                metrics['strategy_signal_types'][strategy_name]['None'] += 1
            
            # Aggregate 결과
            # 예: 🎯 [ENSEMBLE V2] Aggregate 결과: tier=tier1, side=LONG, reason=['tier1_high_confidence', 'chosen_strategy=mean_reversion_v2', 'S_NET=1.000'], strategies=1
            aggregate_match = re.search(
                r"Aggregate 결과: tier=(\w+), side=(\w+), reason=\[(.*?)\], strategies=(\d+)",
                line
            )
            if aggregate_match:
                metrics['aggregate_count'] += 1
                tier = aggregate_match.group(1)
                side = aggregate_match.group(2)
                reason_str = aggregate_match.group(3)
                strategies_count = int(aggregate_match.group(4))
                
                metrics['tier_distribution'][tier] += 1
                metrics['side_distribution'][side] += 1
                metrics['strategies_count'].append(strategies_count)
                
                # Skip 이유 추출
                if tier == 'skip':
                    skip_reason_match = re.search(r"'skip: ([^']+)'", reason_str)
                    if skip_reason_match:
                        skip_reason = skip_reason_match.group(1)
                        metrics['skip_reasons'][skip_reason] += 1
                
                # 선택된 전략 추출 (Tier1/2)
                if tier in ['tier1', 'tier2']:
                    chosen_strategy_match = re.search(r"chosen_strategy=(\w+)", reason_str)
                    if chosen_strategy_match:
                        chosen_strategy = chosen_strategy_match.group(1)
                        metrics['chosen_strategies'][chosen_strategy] += 1
    
    return metrics


def compute_statistics(metrics):
    """메트릭에서 통계 계산"""
    stats = {}
    
    # 전략 평가
    stats['총_평가_횟수'] = metrics['evaluation_count']
    stats['전략별_신호_생성'] = dict(metrics['strategy_signals'])
    
    # Aggregate
    stats['총_Aggregate_횟수'] = metrics['aggregate_count']
    stats['Tier_분포'] = dict(metrics['tier_distribution'])
    stats['Side_분포'] = dict(metrics['side_distribution'])
    stats['Skip_이유'] = dict(metrics['skip_reasons'])
    
    # Tier 비율
    if metrics['aggregate_count'] > 0:
        for tier, count in metrics['tier_distribution'].items():
            pct = (count / metrics['aggregate_count']) * 100
            stats[f'{tier}_비율'] = f"{pct:.1f}%"
    
    # 전략 기여도
    if metrics['strategies_count']:
        avg_strategies = sum(metrics['strategies_count']) / len(metrics['strategies_count'])
        max_strategies = max(metrics['strategies_count'])
        stats['평균_참여_전략_수'] = f"{avg_strategies:.2f}"
        stats['최대_참여_전략_수'] = max_strategies
    
    stats['선택된_전략'] = dict(metrics['chosen_strategies'])
    
    # Score V2 통계
    if metrics['s_net_values']:
        stats['S_NET_평균'] = f"{sum(metrics['s_net_values']) / len(metrics['s_net_values']):.3f}"
        stats['S_NET_최소'] = f"{min(metrics['s_net_values']):.3f}"
        stats['S_NET_최대'] = f"{max(metrics['s_net_values']):.3f}"
    
    if metrics['s_risk_values']:
        stats['S_RISK_평균'] = f"{sum(metrics['s_risk_values']) / len(metrics['s_risk_values']):.3f}"
        stats['S_RISK_최소'] = f"{min(metrics['s_risk_values']):.3f}"
        stats['S_RISK_최대'] = f"{max(metrics['s_risk_values']):.3f}"
    
    if metrics['s_quality_values']:
        stats['S_QUALITY_평균'] = f"{sum(metrics['s_quality_values']) / len(metrics['s_quality_values']):.3f}"
        stats['S_QUALITY_최소'] = f"{min(metrics['s_quality_values']):.3f}"
        stats['S_QUALITY_최대'] = f"{max(metrics['s_quality_values']):.3f}"
    
    return stats


def print_report(stats):
    """분석 결과 출력"""
    print("=" * 80)
    print("PHASE23-4: Ensemble V2 3H Paper Validation - Analysis Report")
    print("=" * 80)
    print()
    
    print("## 1. 전략 평가")
    print(f"   총 평가 횟수: {stats.get('총_평가_횟수', 0):,}")
    print()
    print("   전략별 신호 생성:")
    for strategy, count in sorted(stats.get('전략별_신호_생성', {}).items(), key=lambda x: x[1], reverse=True):
        print(f"     - {strategy}: {count:,}회")
    print()
    
    print("## 2. Aggregate 결과")
    print(f"   총 Aggregate 횟수: {stats.get('총_Aggregate_횟수', 0):,}")
    print()
    print("   Tier 분포:")
    for tier, count in sorted(stats.get('Tier_분포', {}).items(), key=lambda x: x[1], reverse=True):
        pct = stats.get(f'{tier}_비율', 'N/A')
        print(f"     - {tier}: {count:,}회 ({pct})")
    print()
    print("   Side 분포:")
    for side, count in sorted(stats.get('Side_분포', {}).items(), key=lambda x: x[1], reverse=True):
        print(f"     - {side}: {count:,}회")
    print()
    
    if stats.get('Skip_이유'):
        print("   Skip 이유:")
        for reason, count in sorted(stats.get('Skip_이유', {}).items(), key=lambda x: x[1], reverse=True):
            print(f"     - {reason}: {count:,}회")
        print()
    
    print("## 3. 전략 기여도")
    print(f"   평균 참여 전략 수: {stats.get('평균_참여_전략_수', 'N/A')}")
    print(f"   최대 참여 전략 수: {stats.get('최대_참여_전략_수', 'N/A')}")
    print()
    if stats.get('선택된_전략'):
        print("   선택된 전략 (Tier1/2):")
        for strategy, count in sorted(stats.get('선택된_전략', {}).items(), key=lambda x: x[1], reverse=True):
            print(f"     - {strategy}: {count:,}회")
        print()
    
    print("## 4. Score V2 통계")
    print(f"   S_NET: 평균={stats.get('S_NET_평균', 'N/A')}, 범위=[{stats.get('S_NET_최소', 'N/A')}, {stats.get('S_NET_최대', 'N/A')}]")
    print(f"   S_RISK: 평균={stats.get('S_RISK_평균', 'N/A')}, 범위=[{stats.get('S_RISK_최소', 'N/A')}, {stats.get('S_RISK_최대', 'N/A')}]")
    print(f"   S_QUALITY: 평균={stats.get('S_QUALITY_평균', 'N/A')}, 범위=[{stats.get('S_QUALITY_최소', 'N/A')}, {stats.get('S_QUALITY_최대', 'N/A')}]")
    print()
    
    print("=" * 80)


def main():
    """메인 실행"""
    log_file = project_root / 'logs' / 'phase23_4_ensemble_v2_3h.log'
    
    if not log_file.exists():
        print(f"ERROR: Log file not found: {log_file}")
        return 1
    
    print(f"로그 파일 분석 중: {log_file}")
    print()
    
    # 로그 파싱
    metrics = parse_ensemble_logs(log_file)
    
    # 통계 계산
    stats = compute_statistics(metrics)
    
    # 리포트 출력
    print_report(stats)
    
    # 결과를 파일로 저장
    output_file = project_root / 'logs' / 'phase23_4_analysis_results.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        import sys
        old_stdout = sys.stdout
        sys.stdout = f
        print_report(stats)
        sys.stdout = old_stdout
    
    print(f"\n분석 결과 저장됨: {output_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
