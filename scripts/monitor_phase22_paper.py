#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-2 Monitoring Script
============================
12~24h PAPER 실행 중 주기적으로 상태를 확인하고 로그를 분석합니다.

Usage:
    python scripts/monitor_phase22_paper.py
"""
import os
import sys
import time
import re
from datetime import datetime
from pathlib import Path


def get_latest_log_file():
    """가장 최근 로그 파일 경로 반환"""
    log_dir = Path("logs/application")
    if not log_dir.exists():
        return None
    
    # 오늘 날짜 로그 파일
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = log_dir / f"{today}.log"
    
    if log_file.exists():
        return log_file
    return None


def tail_file(file_path, n=100):
    """파일의 마지막 n줄을 읽어서 반환"""
    if not file_path or not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) > n else lines
    except Exception as e:
        print(f"⚠️ 로그 파일 읽기 실패: {e}")
        return []


def analyze_logs(lines):
    """로그 라인들을 분석하여 주요 메트릭 추출"""
    metrics = {
        'errors': 0,
        'criticals': 0,
        'trade_count': 0,
        'candle_count': 0,
        'duration_elapsed': None,
        'strategies_signals': {},
        'flowguardian_ready': 0,
        'flowguardian_total': 0,
        'last_update': None,
    }
    
    for line in lines:
        # ERROR/CRITICAL 카운트
        if '[ERROR]' in line:
            metrics['errors'] += 1
        if '[CRITICAL]' in line:
            metrics['criticals'] += 1
        
        # Trade Count
        match = re.search(r'거래: (\d+)건', line)
        if match:
            metrics['trade_count'] = int(match.group(1))
        
        # Candle Count
        match = re.search(r'총 캔들=([0-9,]+)개', line)
        if match:
            candle_str = match.group(1).replace(',', '')
            metrics['candle_count'] = int(candle_str)
        
        # Duration Elapsed
        match = re.search(r'경과: ([\d.]+)초', line)
        if match:
            metrics['duration_elapsed'] = float(match.group(1))
        
        # FlowGuardian READY
        if 'FlowGuardian' in line and 'READY' in line:
            metrics['flowguardian_ready'] += 1
            metrics['flowguardian_total'] += 1
        elif 'FlowGuardian' in line and ('BLOCK' in line or 'COOLDOWN' in line):
            metrics['flowguardian_total'] += 1
        
        # Strategy Signals (간단한 패턴)
        for strategy in ['scalping', 'breakout', 'reversion', 'trend']:
            if strategy in line.lower() and ('신호' in line or 'signal' in line.lower()):
                metrics['strategies_signals'][strategy] = metrics['strategies_signals'].get(strategy, 0) + 1
        
        # Last Update Time
        match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if match:
            metrics['last_update'] = match.group(1)
    
    return metrics


def print_status(metrics, checkpoint_hour):
    """현재 상태를 출력"""
    print("\n" + "="*80)
    print(f"📊 PHASE22-2 Monitoring - Checkpoint {checkpoint_hour}h")
    print(f"⏰ Last Update: {metrics['last_update'] or 'N/A'}")
    print("="*80)
    
    print(f"\n🎯 Core Metrics:")
    print(f"  - Candle Count: {metrics['candle_count']:,}")
    print(f"  - Trade Count: {metrics['trade_count']}")
    if metrics['duration_elapsed']:
        hours = metrics['duration_elapsed'] / 3600
        print(f"  - Duration Elapsed: {hours:.2f}h ({metrics['duration_elapsed']:.0f}s)")
    
    print(f"\n⚠️  Errors:")
    print(f"  - ERROR: {metrics['errors']}")
    print(f"  - CRITICAL: {metrics['criticals']}")
    
    print(f"\n🛡️  FlowGuardian:")
    if metrics['flowguardian_total'] > 0:
        ready_pct = (metrics['flowguardian_ready'] / metrics['flowguardian_total']) * 100
        print(f"  - READY: {metrics['flowguardian_ready']}/{metrics['flowguardian_total']} ({ready_pct:.1f}%)")
    else:
        print(f"  - No FlowGuardian checks yet")
    
    print(f"\n📈 Strategy Signals (estimated):")
    if metrics['strategies_signals']:
        for strategy, count in metrics['strategies_signals'].items():
            print(f"  - {strategy}: {count}")
    else:
        print(f"  - No signals detected in recent logs")
    
    print("="*80)


def monitor_loop(interval_minutes=30, total_hours=12):
    """주기적으로 로그를 확인하고 상태를 출력"""
    print(f"🚀 PHASE22-2 Monitoring Started")
    print(f"   Interval: {interval_minutes} min")
    print(f"   Total Duration: {total_hours}h")
    print(f"   Expected Checkpoints: {int(total_hours * 60 / interval_minutes)}")
    
    start_time = time.time()
    checkpoint = 0
    
    while True:
        elapsed_hours = (time.time() - start_time) / 3600
        
        # 로그 파일 확인
        log_file = get_latest_log_file()
        if not log_file:
            print("⚠️ 로그 파일을 찾을 수 없습니다. 60초 후 재시도...")
            time.sleep(60)
            continue
        
        # 마지막 100줄 분석
        lines = tail_file(log_file, n=200)
        metrics = analyze_logs(lines)
        
        # 상태 출력
        print_status(metrics, elapsed_hours)
        
        # Critical 이슈 체크
        if metrics['criticals'] > 0:
            print(f"\n❌ CRITICAL 에러 발견! ({metrics['criticals']}건)")
            print(f"   로그 확인 필요: {log_file}")
            print(f"   모니터링 중단 권장")
            break
        
        # 12시간 초과 시 종료
        if elapsed_hours >= total_hours + 0.5:  # 30분 오차 허용
            print(f"\n✅ 모니터링 종료: {elapsed_hours:.2f}h 경과")
            break
        
        # 다음 체크포인트까지 대기
        checkpoint += 1
        print(f"\n⏳ Next checkpoint in {interval_minutes} min...")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PHASE22-2 Monitoring')
    parser.add_argument('--interval', type=int, default=30, help='체크 간격 (분, 기본: 30)')
    parser.add_argument('--duration', type=int, default=12, help='총 실행 시간 (시간, 기본: 12)')
    
    args = parser.parse_args()
    
    try:
        monitor_loop(interval_minutes=args.interval, total_hours=args.duration)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 모니터링 중단")
        sys.exit(0)
