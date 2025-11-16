#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16 Paper Trading Status Checker
=====================================

현재 Paper Trading 상태를 조회합니다.

사용법:
    python scripts/check_paper_phase16.py
"""
from __future__ import annotations
import os
import sys
import json
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


# =====================================================================
# Status Checker
# =====================================================================

class PaperTradingChecker:
    """Paper Trading 상태 확인"""
    
    def __init__(self):
        try:
            self.r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.r.ping()
        except Exception as e:
            print(f"❌ Redis 연결 실패: {e}")
            sys.exit(1)
    
    def check_state(self) -> Dict:
        """엔진 상태 확인"""
        key = f"{NAMESPACE}:state"
        data = self.r.get(key)
        
        if not data:
            return {"state": "NOT_RUNNING", "message": "Paper Trading이 실행 중이 아닙니다"}
        
        return json.loads(data)
    
    def check_positions(self, limit: int = 5) -> list:
        """활성 포지션 확인"""
        key = f"{NAMESPACE}:positions"
        positions = self.r.lrange(key, 0, limit - 1)
        return [json.loads(p) for p in positions]
    
    def check_metrics(self, limit: int = 10) -> list:
        """성능 지표 확인"""
        key = f"{NAMESPACE}:metrics"
        metrics = self.r.lrange(key, 0, limit - 1)
        return [json.loads(m) for m in metrics]
    
    def check_errors(self, limit: int = 10) -> list:
        """에러 로그 확인"""
        key = f"{NAMESPACE}:errors"
        errors = self.r.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in errors]
    
    def print_status(self):
        """상태 출력"""
        print("\n" + "=" * 70)
        print("🔍 PHASE16 Paper Trading Status")
        print("=" * 70)
        
        # Engine state
        print("\n📊 Engine State:")
        state = self.check_state()
        print(f"   State: {state.get('state', 'UNKNOWN')}")
        print(f"   Timestamp: {state.get('timestamp', 'N/A')}")
        if state.get('details'):
            for key, value in state['details'].items():
                print(f"   {key}: {value}")
        
        # Positions
        print("\n💼 Active Positions:")
        positions = self.check_positions()
        if positions:
            for i, pos in enumerate(positions, 1):
                print(f"   [{i}] {pos.get('symbol')} {pos.get('side')}")
                print(f"       Entry: {pos.get('entry')}, TP: {pos.get('tp')}, SL: {pos.get('sl')}")
                print(f"       Time: {pos.get('timestamp')}")
        else:
            print("   (No active positions)")
        
        # Metrics
        print("\n📈 Recent Metrics:")
        metrics = self.check_metrics()
        if metrics:
            for i, metric in enumerate(metrics[:5], 1):
                print(f"   [{i}] {metric.get('name')}: {metric.get('value')}")
                print(f"       Time: {metric.get('timestamp')}")
        else:
            print("   (No metrics recorded)")
        
        # Errors
        print("\n⚠️  Errors:")
        errors = self.check_errors()
        if errors:
            for i, error in enumerate(errors[:5], 1):
                print(f"   [{i}] {error.get('message')}")
                print(f"       Time: {error.get('timestamp')}")
        else:
            print("   (No errors)")
        
        print("\n" + "=" * 70 + "\n")


# =====================================================================
# Main
# =====================================================================

def main():
    """메인 함수"""
    checker = PaperTradingChecker()
    checker.print_status()


if __name__ == "__main__":
    main()
