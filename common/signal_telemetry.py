#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Telemetry v1 (PHASE36-1 D1)
==================================

신호/주문/차단 카운터를 추적하여 "거래가 왜 적은지" 진단.

Prometheus Best Practice 준수:
- Counter 명명: *_total
- 라벨 카디널리티 제한 (reason은 고정 enum)

Usage:
    from common.signal_telemetry import SignalTelemetry
    
    telemetry = SignalTelemetry()
    telemetry.signal_evaluated()
    telemetry.signal_passed()
    telemetry.signal_blocked(reason="risk_check_failed")
    telemetry.order_submitted()
    telemetry.order_filled()
    
    counters = telemetry.get_counters()
"""
from typing import Dict
from collections import defaultdict
import threading
import time
import json
from pathlib import Path
from datetime import datetime


class SignalTelemetry:
    """
    Signal-level Telemetry Counter
    
    Thread-safe counter for tracking signal/order lifecycle.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {
            "signal_evaluated_total": 0,
            "signal_passed_total": 0,
            "order_submitted_total": 0,
            "order_filled_total": 0,
            # PHASE36-1 S4: DB persist 추적
            "db_persist_called": 0,
            "db_insert_success": 0,
            "db_insert_failed": 0,
        }
        self._block_reasons = defaultdict(int)
        self._start_time = None  # PHASE36-1 S4: duration 추적용
    
    def signal_evaluated(self, count: int = 1):
        """신호 평가 카운트"""
        with self._lock:
            self._counters["signal_evaluated_total"] += count
    
    def signal_passed(self, count: int = 1):
        """신호 통과 카운트"""
        with self._lock:
            self._counters["signal_passed_total"] += count
    
    def signal_blocked(self, reason: str, count: int = 1):
        """신호 차단 카운트 (reason별)"""
        with self._lock:
            self._block_reasons[reason] += count
    
    def order_submitted(self, count: int = 1):
        """주문 제출 카운트"""
        with self._lock:
            self._counters["order_submitted_total"] += count
    
    def order_filled(self, count: int = 1):
        """주문 체결 카운트"""
        with self._lock:
            self._counters["order_filled_total"] += count
    
    def db_persist_attempted(self, count: int = 1):
        """DB persist 시도 카운트 (PHASE36-1 S4)"""
        with self._lock:
            self._counters["db_persist_called"] += count
    
    def db_insert_succeeded(self, count: int = 1):
        """DB insert 성공 카운트 (PHASE36-1 S4)"""
        with self._lock:
            self._counters["db_insert_success"] += count
    
    def db_insert_failed_count(self, count: int = 1):
        """DB insert 실패 카운트 (PHASE36-1 S4)"""
        with self._lock:
            self._counters["db_insert_failed"] += count
    
    def set_start_time(self, timestamp: float = None):
        """실행 시작 시간 설정 (PHASE36-1 S4)"""
        with self._lock:
            if self._start_time is None:
                self._start_time = timestamp if timestamp else time.time()
    
    def get_counters(self) -> Dict[str, int]:
        """모든 카운터 반환"""
        with self._lock:
            result = self._counters.copy()
            result["block_reasons"] = dict(self._block_reasons)
            
            # PHASE36-1 S4: 퍼널 통계 계산
            if self._start_time:
                elapsed_hours = (time.time() - self._start_time) / 3600.0
                if elapsed_hours > 0:
                    trades = result.get("order_filled_total", 0)
                    result["trades_per_hour"] = round(trades / elapsed_hours, 2)
                    result["elapsed_hours"] = round(elapsed_hours, 2)
                else:
                    result["trades_per_hour"] = 0
                    result["elapsed_hours"] = 0
            else:
                result["trades_per_hour"] = 0
                result["elapsed_hours"] = 0
            
            return result
    
    def get_top_block_reasons(self, top_n: int = 10) -> list:
        """상위 N개 차단 사유 반환"""
        with self._lock:
            sorted_reasons = sorted(
                self._block_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_reasons[:top_n]
    
    def save_checkpoint(self, checkpoint_dir: str, label: str = None) -> str:
        """체크포인트 저장 (PHASE36-1 S4)"""
        counters = self.get_counters()
        
        if label is None:
            label = f"t_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"telemetry_{label}.json"
        filepath = checkpoint_path / filename
        
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "counters": counters,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def reset(self):
        """모든 카운터 리셋"""
        with self._lock:
            self._counters = {
                "signal_evaluated_total": 0,
                "signal_passed_total": 0,
                "order_submitted_total": 0,
                "order_filled_total": 0,
                "db_persist_called": 0,
                "db_insert_success": 0,
                "db_insert_failed": 0,
            }
            self._block_reasons.clear()
            self._start_time = None
    
    def __repr__(self):
        counters = self.get_counters()
        return (
            f"SignalTelemetry("
            f"evaluated={counters['signal_evaluated_total']}, "
            f"passed={counters['signal_passed_total']}, "
            f"submitted={counters['order_submitted_total']}, "
            f"filled={counters['order_filled_total']}, "
            f"block_reasons={len(counters['block_reasons'])})"
        )


# Global instance (싱글톤 패턴)
_global_telemetry = None
_telemetry_lock = threading.Lock()


def get_signal_telemetry() -> SignalTelemetry:
    """전역 SignalTelemetry 인스턴스 반환 (싱글톤)"""
    global _global_telemetry
    
    if _global_telemetry is None:
        with _telemetry_lock:
            if _global_telemetry is None:
                _global_telemetry = SignalTelemetry()
    
    return _global_telemetry


def reset_signal_telemetry():
    """전역 telemetry 리셋"""
    global _global_telemetry
    
    with _telemetry_lock:
        if _global_telemetry is not None:
            _global_telemetry.reset()
        else:
            _global_telemetry = SignalTelemetry()
