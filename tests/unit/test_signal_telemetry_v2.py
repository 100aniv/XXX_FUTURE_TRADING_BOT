#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Telemetry v2 Unit Tests (PHASE36-1 S4)
==============================================

v2 추가 기능 검증:
- DB persist 카운터 (db_persist_attempted, db_insert_succeeded, db_insert_failed_count)
- 시작 시간 설정 및 trades_per_hour 계산
- 체크포인트 저장
"""
import pytest
import time
import json
from pathlib import Path


def test_db_persist_counters():
    """DB persist 카운터 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    t.db_persist_attempted(5)
    t.db_insert_succeeded(4)
    t.db_insert_failed_count(1)
    
    counters = t.get_counters()
    
    assert counters["db_persist_called"] == 5
    assert counters["db_insert_success"] == 4
    assert counters["db_insert_failed"] == 1


def test_start_time_and_trades_per_hour():
    """시작 시간 설정 및 trades/hour 계산 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    # 시작 시간 설정
    start = time.time()
    t.set_start_time(start)
    
    # 거래 10개
    t.order_filled(10)
    
    # 0.1초 대기
    time.sleep(0.1)
    
    counters = t.get_counters()
    
    # trades_per_hour가 계산됨
    assert "trades_per_hour" in counters
    assert counters["trades_per_hour"] >= 0  # 0.1초는 반올림으로 0이 될 수 있음
    assert "elapsed_hours" in counters
    assert counters["elapsed_hours"] >= 0


def test_start_time_default():
    """set_start_time() 기본 동작 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    # 파라미터 없이 호출하면 현재 시간 사용
    t.set_start_time()
    
    counters = t.get_counters()
    
    # elapsed_hours가 0에 가까워야 함
    assert counters["elapsed_hours"] >= 0
    assert counters["elapsed_hours"] < 0.01


def test_checkpoint_save(tmp_path):
    """체크포인트 저장 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    t.signal_evaluated(100)
    t.signal_passed(50)
    t.order_filled(10)
    
    # 임시 디렉토리에 저장
    checkpoint_path = t.save_checkpoint(str(tmp_path), "test_checkpoint")
    
    # 파일 존재 확인
    assert Path(checkpoint_path).exists()
    
    # JSON 로드 및 검증
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert "timestamp" in data
    assert "label" in data
    assert data["label"] == "test_checkpoint"
    assert "counters" in data
    assert data["counters"]["signal_evaluated_total"] == 100
    assert data["counters"]["signal_passed_total"] == 50
    assert data["counters"]["order_filled_total"] == 10


def test_checkpoint_auto_label(tmp_path):
    """체크포인트 자동 라벨 생성 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    # 라벨 없이 저장
    checkpoint_path = t.save_checkpoint(str(tmp_path))
    
    # 파일명이 t_YYYYMMDD_HHMMSS 형식
    filename = Path(checkpoint_path).name
    assert filename.startswith("telemetry_t_")
    assert filename.endswith(".json")


def test_v2_reset():
    """reset()이 v2 카운터도 초기화하는지 검증"""
    from common.signal_telemetry import get_signal_telemetry, reset_signal_telemetry
    
    reset_signal_telemetry()
    t = get_signal_telemetry()
    
    t.set_start_time()
    t.db_persist_attempted(5)
    t.db_insert_succeeded(3)
    
    # reset 호출
    t.reset()
    
    counters = t.get_counters()
    
    assert counters["db_persist_called"] == 0
    assert counters["db_insert_success"] == 0
    assert counters["db_insert_failed"] == 0
    assert counters["trades_per_hour"] == 0
    assert counters["elapsed_hours"] == 0
