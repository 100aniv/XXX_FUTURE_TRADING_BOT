#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16 Real-time Monitoring Dashboard
=======================================

Paper Trading 실시간 모니터링 대시보드

사용법:
    python scripts/monitor_phase16.py
"""
from __future__ import annotations
import os
import sys
import json
import time
import curses
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import redis


# =====================================================================
# Configuration
# =====================================================================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
NAMESPACE = "paper:phase16"
REFRESH_INTERVAL = 10  # seconds


# =====================================================================
# Monitoring Dashboard
# =====================================================================

class MonitoringDashboard:
    """실시간 모니터링 대시보드"""
    
    def __init__(self):
        try:
            self.r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            self.r.ping()
        except Exception as e:
            print(f"❌ Redis 연결 실패: {e}")
            sys.exit(1)
        
        self.start_time = datetime.now()
    
    def get_state(self) -> Dict:
        """엔진 상태"""
        key = f"{NAMESPACE}:state"
        data = self.r.get(key)
        return json.loads(data) if data else {}
    
    def get_positions(self, limit: int = 5) -> list:
        """포지션"""
        key = f"{NAMESPACE}:positions"
        positions = self.r.lrange(key, 0, limit - 1)
        return [json.loads(p) for p in positions]
    
    def get_metrics(self, limit: int = 10) -> list:
        """메트릭"""
        key = f"{NAMESPACE}:metrics"
        metrics = self.r.lrange(key, 0, limit - 1)
        return [json.loads(m) for m in metrics]
    
    def get_errors(self, limit: int = 5) -> list:
        """에러"""
        key = f"{NAMESPACE}:errors"
        errors = self.r.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in errors]
    
    def format_time(self, seconds: float) -> str:
        """시간 포맷"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def run_curses(self, stdscr):
        """Curses 기반 대시보드"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        
        try:
            while True:
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                
                # Title
                title = "🟢 PHASE16 Paper Trading Monitor"
                stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
                
                # Runtime
                elapsed = (datetime.now() - self.start_time).total_seconds()
                runtime_str = self.format_time(elapsed)
                stdscr.addstr(2, 2, f"⏱️  Runtime: {runtime_str} / 12:00:00", curses.color_pair(4))
                
                # State
                state = self.get_state()
                state_str = state.get('state', 'UNKNOWN')
                state_color = curses.color_pair(1) if state_str == 'RUNNING' else curses.color_pair(3)
                stdscr.addstr(3, 2, f"📊 State: {state_str}", state_color)
                
                # Positions
                stdscr.addstr(5, 2, "💼 Active Positions:", curses.color_pair(4) | curses.A_BOLD)
                positions = self.get_positions(3)
                if positions:
                    for i, pos in enumerate(positions, 1):
                        line = f"   [{i}] {pos.get('symbol')} {pos.get('side')} @ {pos.get('entry')}"
                        stdscr.addstr(5 + i, 2, line)
                else:
                    stdscr.addstr(6, 2, "   (No active positions)")
                
                # Metrics
                stdscr.addstr(9, 2, "📈 Recent Metrics:", curses.color_pair(4) | curses.A_BOLD)
                metrics = self.get_metrics(3)
                if metrics:
                    for i, metric in enumerate(metrics, 1):
                        line = f"   {metric.get('name')}: {metric.get('value')}"
                        stdscr.addstr(9 + i, 2, line)
                else:
                    stdscr.addstr(10, 2, "   (No metrics)")
                
                # Errors
                stdscr.addstr(13, 2, "⚠️  Errors:", curses.color_pair(2) | curses.A_BOLD)
                errors = self.get_errors(2)
                if errors:
                    for i, error in enumerate(errors, 1):
                        line = f"   {error.get('message')[:50]}"
                        stdscr.addstr(13 + i, 2, line, curses.color_pair(2))
                else:
                    stdscr.addstr(14, 2, "   (No errors)")
                
                # Footer
                stdscr.addstr(height - 2, 2, "Press 'q' to quit, 'r' to refresh", curses.color_pair(3))
                
                stdscr.refresh()
                
                # Input handling
                try:
                    ch = stdscr.getch()
                    if ch == ord('q'):
                        break
                except:
                    pass
                
                time.sleep(REFRESH_INTERVAL)
        
        except KeyboardInterrupt:
            pass
    
    def run_simple(self):
        """간단한 텍스트 기반 모니터링"""
        print("\n" + "=" * 70)
        print("🟢 PHASE16 Paper Trading Monitor")
        print("=" * 70)
        print("(Curses 지원 안 함, 간단한 모드로 실행)")
        print("=" * 70 + "\n")
        
        try:
            while True:
                # Clear screen (Windows 호환)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print("=" * 70)
                print("🟢 PHASE16 Paper Trading Monitor")
                print("=" * 70)
                
                # Runtime
                elapsed = (datetime.now() - self.start_time).total_seconds()
                runtime_str = self.format_time(elapsed)
                print(f"\n⏱️  Runtime: {runtime_str} / 12:00:00")
                
                # State
                state = self.get_state()
                state_str = state.get('state', 'UNKNOWN')
                print(f"📊 State: {state_str}")
                
                # Positions
                print("\n💼 Active Positions:")
                positions = self.get_positions(3)
                if positions:
                    for i, pos in enumerate(positions, 1):
                        print(f"   [{i}] {pos.get('symbol')} {pos.get('side')} @ {pos.get('entry')}")
                else:
                    print("   (No active positions)")
                
                # Metrics
                print("\n📈 Recent Metrics:")
                metrics = self.get_metrics(3)
                if metrics:
                    for i, metric in enumerate(metrics, 1):
                        print(f"   {metric.get('name')}: {metric.get('value')}")
                else:
                    print("   (No metrics)")
                
                # Errors
                print("\n⚠️  Errors:")
                errors = self.get_errors(2)
                if errors:
                    for i, error in enumerate(errors, 1):
                        print(f"   {error.get('message')[:60]}")
                else:
                    print("   (No errors)")
                
                print("\n" + "=" * 70)
                print("Press Ctrl+C to stop")
                print("=" * 70 + "\n")
                
                time.sleep(REFRESH_INTERVAL)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  모니터링 중단")


# =====================================================================
# Main
# =====================================================================

def main():
    """메인 함수"""
    dashboard = MonitoringDashboard()
    
    # Try curses, fall back to simple mode
    try:
        curses.wrapper(dashboard.run_curses)
    except:
        dashboard.run_simple()


if __name__ == "__main__":
    main()
