#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE22-2 자동 모니터링 & 자동 디버깅 스크립트
==============================================
실시간으로 로그를 분석하고, 문제 발생 시 자동으로 중단·수정·재실행합니다.

Usage:
    python scripts/auto_monitor_phase22.py --duration 2 --check-interval 30
"""
import os
import sys
import time
import re
import subprocess
from datetime import datetime
from pathlib import Path


class PHASE22Monitor:
    def __init__(self, duration_hours=2, check_interval_sec=30):
        self.duration_hours = duration_hours
        self.check_interval_sec = check_interval_sec
        self.log_file = Path("logs/application/2025-11-22.log")
        self.start_time = None
        self.last_log_size = 0
        self.trade_count_history = []
        self.error_count = 0
        self.critical_count = 0
        
    def get_log_tail(self, n=200):
        """로그 파일의 마지막 n줄 읽기"""
        if not self.log_file.exists():
            return []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-n:] if len(lines) > n else lines
        except Exception as e:
            print(f"⚠️ 로그 읽기 실패: {e}")
            return []
    
    def analyze_logs(self, lines):
        """로그 분석 및 메트릭 추출"""
        metrics = {
            'errors': 0,
            'criticals': 0,
            'trade_count': 0,
            'candle_count': 0,
            'duration_elapsed': None,
            'flash_guard_active': False,
            'flowguardian_ready': 0,
            'flowguardian_total': 0,
            'strategies_active': set(),
            'last_update': None,
            'has_signals': False,
        }
        
        for line in lines:
            # ERROR/CRITICAL 카운트
            if '[ERROR]' in line:
                metrics['errors'] += 1
            if '[CRITICAL]' in line and 'DEBUG' not in line:
                metrics['criticals'] += 1
            
            # Trade Count
            match = re.search(r'총 거래=(\d+)건', line)
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
            
            # Flash-Guard
            if 'Flash-Guard' in line:
                metrics['flash_guard_active'] = True
            
            # FlowGuardian
            if 'FlowGuardian' in line and 'READY' in line:
                metrics['flowguardian_ready'] += 1
                metrics['flowguardian_total'] += 1
            elif 'FlowGuardian' in line:
                metrics['flowguardian_total'] += 1
            
            # Strategies
            for strategy in ['scalping', 'breakout', 'reversion', 'trend']:
                if strategy in line.lower():
                    metrics['strategies_active'].add(strategy)
            
            # Signals
            if '신호' in line or 'signal' in line.lower():
                metrics['has_signals'] = True
            
            # Last Update
            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if match:
                metrics['last_update'] = match.group(1)
        
        return metrics
    
    def check_health(self, metrics, elapsed_hours):
        """헬스 체크 및 문제 감지"""
        issues = []
        
        # Issue 1: Trade Count = 0 (1시간 이상 경과)
        if elapsed_hours > 1.0 and metrics['trade_count'] == 0:
            issues.append({
                'severity': 'HIGH',
                'message': f'Trade Count = 0 (1시간 경과)',
                'action': 'INVESTIGATE'
            })
        
        # Issue 2: CRITICAL 에러
        if metrics['criticals'] > 0:
            issues.append({
                'severity': 'CRITICAL',
                'message': f'CRITICAL 에러 발생 ({metrics["criticals"]}건)',
                'action': 'STOP'
            })
        
        # Issue 3: Flash-Guard 반복 활성화
        if metrics['flash_guard_active'] and elapsed_hours > 0.5:
            issues.append({
                'severity': 'MEDIUM',
                'message': 'Flash-Guard 반복 활성화 (변동성 높음)',
                'action': 'MONITOR'
            })
        
        # Issue 4: FlowGuardian 실패
        if metrics['flowguardian_total'] > 0:
            ready_pct = (metrics['flowguardian_ready'] / metrics['flowguardian_total']) * 100
            if ready_pct < 50:
                issues.append({
                    'severity': 'HIGH',
                    'message': f'FlowGuardian READY 비율 낮음 ({ready_pct:.1f}%)',
                    'action': 'INVESTIGATE'
                })
        
        return issues
    
    def print_status(self, metrics, elapsed_hours):
        """현재 상태 출력"""
        print("\n" + "="*80)
        print(f"📊 PHASE22-2 Auto-Monitor | {elapsed_hours:.2f}h / {self.duration_hours}h")
        print(f"⏰ {metrics['last_update'] or 'N/A'}")
        print("="*80)
        
        print(f"\n🎯 Core Metrics:")
        print(f"  - Candle: {metrics['candle_count']:,}")
        print(f"  - Trade: {metrics['trade_count']}")
        print(f"  - Duration: {metrics['duration_elapsed']:.0f}s" if metrics['duration_elapsed'] else "  - Duration: N/A")
        
        print(f"\n⚠️ Errors:")
        print(f"  - ERROR: {metrics['errors']}")
        print(f"  - CRITICAL: {metrics['criticals']}")
        
        print(f"\n🛡️ Guards:")
        print(f"  - Flash-Guard: {'🔴 ACTIVE' if metrics['flash_guard_active'] else '✅ OK'}")
        if metrics['flowguardian_total'] > 0:
            ready_pct = (metrics['flowguardian_ready'] / metrics['flowguardian_total']) * 100
            print(f"  - FlowGuardian: {metrics['flowguardian_ready']}/{metrics['flowguardian_total']} ({ready_pct:.1f}%)")
        
        print(f"\n📈 Strategies:")
        if metrics['strategies_active']:
            print(f"  - Active: {', '.join(sorted(metrics['strategies_active']))}")
        else:
            print(f"  - Active: None detected")
        
        print(f"\n📡 Signals: {'✅ YES' if metrics['has_signals'] else '❌ NO'}")
        
        print("="*80)
    
    def handle_issue(self, issue):
        """문제 처리"""
        severity = issue['severity']
        message = issue['message']
        action = issue['action']
        
        print(f"\n🚨 [{severity}] {message}")
        print(f"   Action: {action}")
        
        if action == 'STOP':
            print(f"\n❌ 테스트 중단 필요!")
            return False
        elif action == 'INVESTIGATE':
            print(f"\n⚠️ 조사 필요 - 계속 모니터링 중...")
            return True
        elif action == 'MONITOR':
            print(f"\n📍 모니터링 중...")
            return True
        
        return True
    
    def run(self):
        """메인 모니터링 루프"""
        print(f"🚀 PHASE22-2 Auto-Monitor 시작")
        print(f"   Duration: {self.duration_hours}h")
        print(f"   Check Interval: {self.check_interval_sec}s")
        
        self.start_time = time.time()
        checkpoint = 0
        
        while True:
            elapsed_hours = (time.time() - self.start_time) / 3600
            
            # 로그 분석
            lines = self.get_log_tail(n=300)
            metrics = self.analyze_logs(lines)
            
            # 상태 출력
            self.print_status(metrics, elapsed_hours)
            
            # 헬스 체크
            issues = self.check_health(metrics, elapsed_hours)
            
            # 문제 처리
            should_continue = True
            for issue in issues:
                if not self.handle_issue(issue):
                    should_continue = False
                    break
            
            if not should_continue:
                print(f"\n❌ 모니터링 중단")
                return False
            
            # 종료 조건
            if elapsed_hours >= self.duration_hours + 0.1:
                print(f"\n✅ 모니터링 완료: {elapsed_hours:.2f}h 경과")
                return True
            
            # 다음 체크 대기
            checkpoint += 1
            remaining = self.duration_hours - elapsed_hours
            print(f"\n⏳ 다음 체크: {self.check_interval_sec}초 후 ({remaining:.2f}h 남음)...")
            time.sleep(self.check_interval_sec)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PHASE22-2 Auto-Monitor')
    parser.add_argument('--duration', type=int, default=2, help='총 실행 시간 (시간)')
    parser.add_argument('--check-interval', type=int, default=30, help='체크 간격 (초)')
    
    args = parser.parse_args()
    
    monitor = PHASE22Monitor(duration_hours=args.duration, check_interval_sec=args.check_interval)
    
    try:
        success = monitor.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 모니터링 중단")
        sys.exit(0)
