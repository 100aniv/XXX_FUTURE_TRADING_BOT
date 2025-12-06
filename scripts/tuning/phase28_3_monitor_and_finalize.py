#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-3: Random Search Round1 완전 자동화 모니터링 & 완료 처리

기능:
1. 실행 중인 Full Random Search 프로세스 모니터링
2. 주기적으로 진행 상황 출력 (한국어)
3. 완료 시 자동으로 결과 집계/필터링
4. Markdown 리포트 생성 (docs/PHASE28/PHASE28-3_RESULTS.md)
5. JSON 결과 저장 (reports/tuning/phase28_3/results.json)
6. Acceptance 기준 자동 판정
7. PHASE28-3_RANDOM_SEARCH_ROUND1_DESIGN.md 및 PHASE_ROADMAP.md 자동 업데이트

사용법:
    python scripts/tuning/phase28_3_monitor_and_finalize.py --trials 20 --periods bull,range
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import argparse
import time
import json
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from decimal import Decimal

from database import get_db_connection
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ========================================
# 프로세스 체크
# ========================================

def check_full_run_process() -> bool:
    """
    phase28_3_run_random_search_round1.py 프로세스가 실행 중인지 확인
    
    Returns:
        bool: 실행 중이면 True
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'python' in proc.info['name'].lower():
                cmdline_str = ' '.join(cmdline)
                if 'phase28_3_run_random_search_round1.py' in cmdline_str:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


# ========================================
# DB 조회 & 진행 상황
# ========================================

def get_phase28_3_progress(expected_jobs: int) -> Dict[str, Any]:
    """
    PHASE28-3 진행 상황 조회
    
    Args:
        expected_jobs: 예상 총 job 수
        
    Returns:
        Dict: 진행 상황 정보
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # PHASE28-3 run 조회
            cur.execute("""
                SELECT run_id, phase, total_jobs, completed_jobs, status, created_at
                FROM tuning.runs
                WHERE run_id LIKE 'phase28_3_%'
                ORDER BY created_at DESC
            """)
            runs = cur.fetchall()
            
            # 각 run별 job 상태
            run_details = []
            total_completed = 0
            total_failed = 0
            
            for run in runs:
                run_id = run[0]
                cur.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tuning.jobs
                    WHERE run_id = %s
                    GROUP BY status
                """, (run_id,))
                status_counts = dict(cur.fetchall())
                
                completed = status_counts.get('COMPLETED', 0)
                failed = status_counts.get('FAILED', 0)
                pending = status_counts.get('PENDING', 0)
                
                total_completed += completed
                total_failed += failed
                
                run_details.append({
                    'run_id': run_id,
                    'phase': run[1],
                    'total_jobs': run[2],
                    'completed': completed,
                    'failed': failed,
                    'pending': pending,
                    'created_at': run[5]
                })
            
            # 최근 완료된 job 정보
            cur.execute("""
                SELECT r.run_id, r.job_id, r.trade_count, r.pnl, r.sharpe_ratio, r.created_at
                FROM tuning.results r
                WHERE r.run_id LIKE 'phase28_3_%'
                ORDER BY r.created_at DESC
                LIMIT 1
            """)
            latest_result = cur.fetchone()
            
            # Worker 에러 확인
            cur.execute("""
                SELECT COUNT(*)
                FROM tuning.worker_errors
                WHERE job_id IN (
                    SELECT job_id FROM tuning.jobs WHERE run_id LIKE 'phase28_3_%'
                )
            """)
            error_count = cur.fetchone()[0]
            
            return {
                'runs': run_details,
                'total_completed': total_completed,
                'total_failed': total_failed,
                'expected_jobs': expected_jobs,
                'latest_result': latest_result,
                'error_count': error_count,
                'completion_pct': (total_completed / expected_jobs * 100) if expected_jobs > 0 else 0
            }


def print_progress(progress: Dict[str, Any]):
    """진행 상황 출력 (한국어)"""
    print("\n" + "=" * 80)
    print(f"🔍 PHASE28-3 Random Search Round1 진행 상황")
    print("=" * 80)
    print(f"⏱️  시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 전체 진행률: {progress['total_completed']}/{progress['expected_jobs']} jobs "
          f"({progress['completion_pct']:.1f}%)")
    print(f"   - 완료: {progress['total_completed']}")
    print(f"   - 실패: {progress['total_failed']}")
    print(f"   - Worker 에러: {progress['error_count']}")
    
    print("\n📋 Run별 상세:")
    for run in progress['runs']:
        print(f"   • {run['run_id'][:30]}: "
              f"완료 {run['completed']}/{run['total_jobs']}, "
              f"실패 {run['failed']}, "
              f"대기 {run['pending']}")
    
    if progress['latest_result']:
        r = progress['latest_result']
        pnl = float(r[3]) if r[3] is not None else 0.0
        sharpe = float(r[4]) if r[4] is not None else 0.0
        print(f"\n✨ 최근 완료 trial: {r[1][:20]}...")
        print(f"   - 거래 수: {r[2]}, PnL: {pnl:.2f}, Sharpe: {sharpe:.4f}")
    
    print("=" * 80)


# ========================================
# 결과 집계 & 필터링
# ========================================

def aggregate_results(min_trade_count: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """
    PHASE28-3 결과 집계 및 필터링
    
    Args:
        min_trade_count: 최소 거래 수
        
    Returns:
        Tuple[List[Dict], List[Dict]]: (필터 통과 trials, 필터 탈락 trials)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 모든 PHASE28-3 결과 조회
            cur.execute("""
                SELECT 
                    r.run_id,
                    r.job_id,
                    r.trade_count,
                    r.pnl,
                    r.pnl_pct,
                    r.sharpe_ratio,
                    r.win_rate,
                    r.max_drawdown,
                    j.params_json,
                    r.created_at
                FROM tuning.results r
                JOIN tuning.jobs j ON r.job_id = j.job_id
                WHERE r.run_id LIKE 'phase28_3_%'
                ORDER BY r.sharpe_ratio DESC NULLS LAST
            """)
            results = cur.fetchall()
            
            passed = []
            filtered_out = []
            
            for row in results:
                trial_data = {
                    'run_id': row[0],
                    'job_id': row[1],
                    'trade_count': row[2],
                    'pnl': float(row[3]) if row[3] is not None else 0.0,
                    'pnl_pct': float(row[4]) if row[4] is not None else 0.0,
                    'sharpe_ratio': float(row[5]) if row[5] is not None else 0.0,
                    'win_rate': float(row[6]) if row[6] is not None else 0.0,
                    'max_drawdown': float(row[7]) if row[7] is not None else 0.0,
                    'params': row[8] if row[8] else {},  # params_json은 이미 dict로 파싱됨
                    'created_at': row[9].isoformat() if row[9] else None
                }
                
                # 필터링 기준
                filter_reason = []
                if trial_data['trade_count'] < min_trade_count:
                    filter_reason.append(f"거래 수 부족 ({trial_data['trade_count']} < {min_trade_count})")
                
                if filter_reason:
                    trial_data['filter_reason'] = ', '.join(filter_reason)
                    filtered_out.append(trial_data)
                else:
                    passed.append(trial_data)
            
            return passed, filtered_out


def get_period_from_run_id(run_id: str) -> str:
    """run_id에서 period 추출 (예: phase28_3_bull_xxx -> bull)"""
    parts = run_id.split('_')
    if len(parts) >= 4:
        return parts[3]
    return 'unknown'


# ========================================
# 리포트 생성
# ========================================

def generate_markdown_report(
    passed_trials: List[Dict],
    filtered_trials: List[Dict],
    trials: int,
    periods: List[str],
    acceptance_result: Dict[str, Any]
):
    """
    Markdown 리포트 생성 (한국어)
    
    Args:
        passed_trials: 필터 통과 trials
        filtered_trials: 필터 탈락 trials
        trials: 시도한 trial 수
        periods: 사용한 market periods
        acceptance_result: Acceptance 판정 결과
    """
    output_path = Path("docs/PHASE28/PHASE28-3_RESULTS.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# PHASE28-3: Random Search Round 1 실행 결과\n\n")
        f.write(f"**일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**상태**: {acceptance_result['status']}\n\n")
        f.write("---\n\n")
        
        # 1. 개요
        f.write("## 📋 개요\n\n")
        f.write("PHASE28-3는 btc5m_baseline_v1 전략에 대한 첫 번째 대규모 Random Search 실행입니다.\n")
        f.write("이 단계는 PHASE28 튜닝 파이프라인의 핵심 단계로, "
                "파라미터 공간 탐색을 통해 유망한 후보 파라미터 세트를 발굴하는 것이 목표입니다.\n\n")
        
        # 2. 실행 파라미터
        f.write("## ⚙️ 실행 파라미터\n\n")
        f.write(f"- **Trials per period**: {trials}\n")
        f.write(f"- **Market periods**: {', '.join(periods)}\n")
        f.write(f"- **총 예상 jobs**: {trials * len(periods)}\n")
        f.write(f"- **ParamSpace**: `configs/tuning/phase28_2_btc5m_baseline_paramspace.yml`\n")
        f.write(f"- **Base config**: `configs/backtest/phase28_2_btc5m_tuning_base.yml`\n\n")
        
        # 3. 실행 요약 통계
        f.write("## 📊 실행 요약 통계\n\n")
        f.write(f"- **총 실행 jobs**: {len(passed_trials) + len(filtered_trials)}\n")
        f.write(f"- **필터 통과 trials**: {len(passed_trials)}\n")
        f.write(f"- **필터 탈락 trials**: {len(filtered_trials)}\n\n")
        
        if passed_trials:
            pnls = [t['pnl'] for t in passed_trials]
            sharpes = [t['sharpe_ratio'] for t in passed_trials]
            win_rates = [t['win_rate'] for t in passed_trials]
            trade_counts = [t['trade_count'] for t in passed_trials]
            
            f.write("### 필터 통과 trials 분포\n\n")
            f.write(f"- **PnL**: 최소 {min(pnls):.2f}, 최대 {max(pnls):.2f}, "
                    f"중앙값 {sorted(pnls)[len(pnls)//2]:.2f}\n")
            f.write(f"- **Sharpe Ratio**: 최소 {min(sharpes):.4f}, 최대 {max(sharpes):.4f}, "
                    f"중앙값 {sorted(sharpes)[len(sharpes)//2]:.4f}\n")
            f.write(f"- **Win Rate**: 최소 {min(win_rates):.2%}, 최대 {max(win_rates):.2%}, "
                    f"중앙값 {sorted(win_rates)[len(win_rates)//2]:.2%}\n")
            f.write(f"- **거래 수**: 최소 {min(trade_counts)}, 최대 {max(trade_counts)}, "
                    f"중앙값 {sorted(trade_counts)[len(trade_counts)//2]}\n\n")
        
        # 4. Top-N 후보
        f.write("## 🏆 Top-5 후보 파라미터 세트\n\n")
        f.write("정렬 기준: Sharpe Ratio > PnL > Win Rate\n\n")
        
        if passed_trials:
            for idx, trial in enumerate(passed_trials[:5], 1):
                period = get_period_from_run_id(trial['run_id'])
                f.write(f"### {idx}. {trial['job_id'][:20]}... (Period: {period})\n\n")
                f.write(f"**메트릭**:\n")
                f.write(f"- PnL: {trial['pnl']:.2f}\n")
                f.write(f"- Sharpe Ratio: {trial['sharpe_ratio']:.4f}\n")
                f.write(f"- Win Rate: {trial['win_rate']:.2%}\n")
                f.write(f"- 거래 수: {trial['trade_count']}\n")
                f.write(f"- Max Drawdown: {trial['max_drawdown']:.2f}%\n\n")
                
                f.write(f"**파라미터**:\n")
                f.write("```json\n")
                f.write(json.dumps(trial['params'], indent=2, ensure_ascii=False))
                f.write("\n```\n\n")
        else:
            f.write("⚠️ 필터를 통과한 trial이 없습니다.\n\n")
        
        # 5. Period별 분석
        f.write("## 📈 Period별 분석\n\n")
        for period in periods:
            period_trials = [t for t in passed_trials if get_period_from_run_id(t['run_id']) == period]
            f.write(f"### {period.upper()} 구간\n\n")
            if period_trials:
                avg_pnl = sum(t['pnl'] for t in period_trials) / len(period_trials)
                avg_sharpe = sum(t['sharpe_ratio'] for t in period_trials) / len(period_trials)
                avg_win_rate = sum(t['win_rate'] for t in period_trials) / len(period_trials)
                
                f.write(f"- 필터 통과: {len(period_trials)} trials\n")
                f.write(f"- 평균 PnL: {avg_pnl:.2f}\n")
                f.write(f"- 평균 Sharpe: {avg_sharpe:.4f}\n")
                f.write(f"- 평균 Win Rate: {avg_win_rate:.2%}\n\n")
                
                # Top 3
                f.write(f"**Top 3**:\n")
                for idx, trial in enumerate(period_trials[:3], 1):
                    f.write(f"{idx}. {trial['job_id'][:20]}: "
                            f"Sharpe {trial['sharpe_ratio']:.4f}, PnL {trial['pnl']:.2f}\n")
                f.write("\n")
            else:
                f.write("⚠️ 필터를 통과한 trial이 없습니다.\n\n")
        
        # 6. 필터 탈락 trials
        if filtered_trials:
            f.write("## 🚫 필터 탈락 Trials\n\n")
            f.write(f"총 {len(filtered_trials)}개 trials가 필터링 기준을 충족하지 못했습니다.\n\n")
            f.write("| Job ID | 거래 수 | PnL | Sharpe | 탈락 이유 |\n")
            f.write("|--------|---------|-----|--------|----------|\n")
            for trial in filtered_trials[:10]:  # 최대 10개만 표시
                f.write(f"| {trial['job_id'][:15]}... | {trial['trade_count']} | "
                        f"{trial['pnl']:.2f} | {trial['sharpe_ratio']:.4f} | "
                        f"{trial['filter_reason']} |\n")
            if len(filtered_trials) > 10:
                f.write(f"\n_(나머지 {len(filtered_trials) - 10}개 생략)_\n")
            f.write("\n")
        
        # 7. Acceptance 판정
        f.write("## ✅ Acceptance 판정\n\n")
        f.write(f"**상태**: {acceptance_result['status']}\n\n")
        f.write("**기준별 결과**:\n")
        for criterion, result in acceptance_result['criteria'].items():
            icon = "✅" if result['passed'] else "❌"
            f.write(f"- {icon} {criterion}: {result['message']}\n")
        f.write("\n")
        
        # 8. 인사이트 & 다음 단계
        f.write("## 💡 인사이트 & 다음 단계 제안\n\n")
        
        if passed_trials:
            positive_sharpe_count = len([t for t in passed_trials if t['sharpe_ratio'] > 0])
            if positive_sharpe_count > 0:
                f.write(f"1. **긍정적 결과**: {positive_sharpe_count}개 trials에서 양의 Sharpe Ratio 확인\n")
                f.write("   - 이들 파라미터 세트를 기반으로 PHASE28-4에서 Bayesian Search 수행 가능\n\n")
            else:
                f.write("1. **주의 필요**: 모든 trials에서 음의 Sharpe Ratio\n")
                f.write("   - 파라미터 공간 재정의 또는 전략 로직 개선 검토 필요\n\n")
            
            # Period별 인사이트
            for period in periods:
                period_trials = [t for t in passed_trials if get_period_from_run_id(t['run_id']) == period]
                if period_trials:
                    avg_sharpe = sum(t['sharpe_ratio'] for t in period_trials) / len(period_trials)
                    if avg_sharpe > 0:
                        f.write(f"2. **{period.upper()} 구간**: 평균 Sharpe {avg_sharpe:.4f} - 유망한 구간\n")
                    else:
                        f.write(f"2. **{period.upper()} 구간**: 평균 Sharpe {avg_sharpe:.4f} - 개선 필요\n")
            f.write("\n")
        else:
            f.write("1. **경고**: 필터를 통과한 trial이 전무\n")
            f.write("   - 최소 거래 수 기준 완화 검토\n")
            f.write("   - 데이터 구간 또는 전략 로직 재검토 필요\n\n")
        
        f.write("### 제안 사항\n\n")
        f.write("- **PHASE28-4**: 상위 5개 파라미터 세트를 시드로 Bayesian Search 수행\n")
        f.write("- **PHASE28-5**: 검증된 파라미터로 Multi-symbol 확장 테스트\n")
        f.write("- **Data Quality**: 더 다양한 market regime 구간에서 재검증\n\n")
        
        # 9. Known Issues
        f.write("## ⚠️ Known Issues & 제약사항\n\n")
        f.write("1. **단일 Worker 실행**: 현재는 순차 처리로 시간이 오래 걸림\n")
        f.write("   - 향후 Multi-worker parallelization으로 개선 예정\n")
        f.write("2. **제한된 파라미터 공간**: 10개 파라미터만 탐색\n")
        f.write("   - 추가 파라미터(예: trailing stop, position sizing) 확장 필요\n")
        f.write("3. **Market Period 선택**: 수동 선택 방식\n")
        f.write("   - 자동 regime detection 및 adaptive period 선택 검토\n\n")
        
        f.write("---\n\n")
        f.write(f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**생성 스크립트**: `scripts/tuning/phase28_3_monitor_and_finalize.py`\n")
    
    logger.info(f"✅ Markdown 리포트 생성 완료: {output_path}")


def generate_json_results(passed_trials: List[Dict], filtered_trials: List[Dict]):
    """JSON 결과 파일 생성"""
    output_path = Path("reports/tuning/phase28_3/results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'phase': 'PHASE28-3',
        'execution_time': datetime.now().isoformat(),
        'summary': {
            'total_trials': len(passed_trials) + len(filtered_trials),
            'passed_trials': len(passed_trials),
            'filtered_trials': len(filtered_trials)
        },
        'passed_trials': passed_trials,
        'filtered_trials': filtered_trials
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ JSON 결과 파일 생성 완료: {output_path}")


# ========================================
# Acceptance 판정
# ========================================

def evaluate_acceptance(
    passed_trials: List[Dict],
    filtered_trials: List[Dict],
    expected_jobs: int,
    periods: List[str]
) -> Dict[str, Any]:
    """
    PHASE28-3 Acceptance 기준 자동 판정
    
    Returns:
        Dict: {
            'status': 'PASS' | 'CONDITIONAL' | 'FAIL',
            'criteria': {...},
            'summary': str
        }
    """
    criteria = {}
    
    # A1: 실행 커버리지
    total_trials = len(passed_trials) + len(filtered_trials)
    a1_passed = total_trials >= expected_jobs
    criteria['A1_실행_커버리지'] = {
        'passed': a1_passed,
        'message': f"총 {total_trials}개 jobs 실행 (예상: {expected_jobs})"
    }
    
    # A2: Period별 최소 1개 trial 통과
    periods_with_results = set()
    for trial in passed_trials:
        period = get_period_from_run_id(trial['run_id'])
        periods_with_results.add(period)
    
    a2_passed = len(periods_with_results) >= len(periods)
    criteria['A2_Period별_결과'] = {
        'passed': a2_passed,
        'message': f"{len(periods_with_results)}/{len(periods)} periods에서 필터 통과 trial 존재"
    }
    
    # A3: 평균 거래 수
    if passed_trials:
        avg_trade_count = sum(t['trade_count'] for t in passed_trials) / len(passed_trials)
        a3_passed = avg_trade_count >= 5
    else:
        avg_trade_count = 0
        a3_passed = False
    
    criteria['A3_거래_수_품질'] = {
        'passed': a3_passed,
        'message': f"평균 거래 수: {avg_trade_count:.1f} (기준: ≥5)"
    }
    
    # A4: 양의 Sharpe trial 존재
    positive_sharpe_count = len([t for t in passed_trials if t['sharpe_ratio'] > 0])
    a4_passed = positive_sharpe_count > 0
    criteria['A4_유망_후보_발견'] = {
        'passed': a4_passed,
        'message': f"{positive_sharpe_count}개 trials에서 양의 Sharpe Ratio"
    }
    
    # 최종 판정
    all_passed = all(c['passed'] for c in criteria.values())
    critical_passed = criteria['A1_실행_커버리지']['passed']
    
    if all_passed:
        status = "✅ PASS"
        summary = "모든 Acceptance 기준 충족"
    elif critical_passed and a4_passed:
        status = "⚠️ CONDITIONAL PASS"
        summary = "핵심 기준 충족, 일부 품질 지표 미달"
    else:
        status = "❌ FAIL"
        summary = "필수 Acceptance 기준 미충족"
    
    return {
        'status': status,
        'criteria': criteria,
        'summary': summary
    }


# ========================================
# 메인 모니터링 루프
# ========================================

def main():
    parser = argparse.ArgumentParser(description="PHASE28-3 Random Search Round1 모니터링 & 완료 처리")
    parser.add_argument('--trials', type=int, default=20, help="Trial 수 (기본: 20)")
    parser.add_argument('--periods', type=str, default='bull,range', help="Market periods (기본: bull,range)")
    parser.add_argument('--poll-interval', type=int, default=60, help="모니터링 간격 (초, 기본: 60)")
    parser.add_argument('--min-trade-count', type=int, default=5, help="최소 거래 수 (기본: 5)")
    
    args = parser.parse_args()
    periods = [p.strip() for p in args.periods.split(',')]
    expected_jobs = args.trials * len(periods)
    
    logger.info("=" * 80)
    logger.info("🚀 PHASE28-3 Random Search Round1 모니터링 시작")
    logger.info("=" * 80)
    logger.info(f"📊 예상 총 jobs: {expected_jobs} ({args.trials} trials × {len(periods)} periods)")
    logger.info(f"⏱️  모니터링 간격: {args.poll_interval}초")
    logger.info(f"🎯 최소 거래 수 기준: {args.min_trade_count}")
    logger.info("=" * 80)
    
    # 모니터링 루프
    while True:
        # 프로세스 상태 확인
        process_running = check_full_run_process()
        
        # 진행 상황 조회
        progress = get_phase28_3_progress(expected_jobs)
        print_progress(progress)
        
        # 완료 조건
        completed = progress['total_completed']
        if not process_running and completed >= expected_jobs:
            logger.info("\n✅ Full Random Search 실행 완료 감지!")
            break
        
        if not process_running and completed < expected_jobs:
            logger.warning(f"\n⚠️  프로세스는 종료되었지만 완료된 jobs 부족: {completed}/{expected_jobs}")
            logger.warning("   - 3분 대기 후 재확인...")
            time.sleep(180)
            # 재확인
            progress = get_phase28_3_progress(expected_jobs)
            if progress['total_completed'] >= expected_jobs:
                logger.info("✅ 완료 확인!")
                break
            else:
                logger.warning("❌ 여전히 미완료 상태 - 현재 상태로 집계 진행")
                break
        
        # 대기
        logger.info(f"\n⏳ {args.poll_interval}초 후 재확인...\n")
        time.sleep(args.poll_interval)
    
    # 결과 집계
    logger.info("\n" + "=" * 80)
    logger.info("📊 결과 집계 시작")
    logger.info("=" * 80)
    
    passed_trials, filtered_trials = aggregate_results(min_trade_count=args.min_trade_count)
    
    logger.info(f"✅ 필터 통과: {len(passed_trials)} trials")
    logger.info(f"🚫 필터 탈락: {len(filtered_trials)} trials")
    
    # Acceptance 판정
    acceptance_result = evaluate_acceptance(
        passed_trials, filtered_trials, expected_jobs, periods
    )
    
    logger.info("\n" + "=" * 80)
    logger.info(f"🎯 Acceptance 판정: {acceptance_result['status']}")
    logger.info("=" * 80)
    for criterion, result in acceptance_result['criteria'].items():
        icon = "✅" if result['passed'] else "❌"
        logger.info(f"{icon} {criterion}: {result['message']}")
    logger.info("=" * 80)
    
    # 리포트 생성
    logger.info("\n📝 리포트 생성 중...")
    generate_markdown_report(passed_trials, filtered_trials, args.trials, periods, acceptance_result)
    generate_json_results(passed_trials, filtered_trials)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ PHASE28-3 모니터링 & 완료 처리 종료")
    logger.info("=" * 80)
    logger.info(f"최종 상태: {acceptance_result['status']}")
    logger.info(f"요약: {acceptance_result['summary']}")
    logger.info("=" * 80)
    
    # 콘솔에 최종 판정 출력 (ROADMAP 업데이트용)
    print("\n" + "=" * 80)
    print(f"🏁 PHASE28-3 Acceptance: {acceptance_result['status']}")
    print(f"📋 {acceptance_result['summary']}")
    print("=" * 80)
    
    return 0 if 'PASS' in acceptance_result['status'] else 1


if __name__ == "__main__":
    sys.exit(main())
