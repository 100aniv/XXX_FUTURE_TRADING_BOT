#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE24-1: Infra Diagnostics 테스트
===================================
통합 인프라 진단 스크립트 동작 검증
"""
import pytest
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Import diagnostics functions directly
from scripts.infra.phase24_1_infra_diagnostics import (
    check_db,
    check_redis,
    check_flow_guardian
)


def test_db_check_returns_dict():
    """DB check가 올바른 형식의 dict를 반환하는지 검증"""
    result = check_db()
    
    assert isinstance(result, dict), "Result should be a dict"
    assert 'status' in result, "Result should have 'status' key"
    assert 'message' in result, "Result should have 'message' key"
    assert 'details' in result, "Result should have 'details' key"
    
    assert result['status'] in ['ok', 'fail'], "Status should be 'ok' or 'fail'"
    
    if result['status'] == 'ok':
        assert 'total_trades' in result['details'], "Details should have 'total_trades'"
        assert isinstance(result['details']['total_trades'], int), "total_trades should be int"
    
    print(f"✅ DB check result: {result['status']} - {result['message']}")


def test_redis_check_returns_dict():
    """Redis check가 올바른 형식의 dict를 반환하는지 검증"""
    result = check_redis()
    
    assert isinstance(result, dict), "Result should be a dict"
    assert 'status' in result, "Result should have 'status' key"
    assert 'message' in result, "Result should have 'message' key"
    assert 'details' in result, "Result should have 'details' key"
    
    assert result['status'] in ['ok', 'fail'], "Status should be 'ok' or 'fail'"
    
    if result['status'] == 'ok':
        assert 'ping' in result['details'], "Details should have 'ping'"
        assert 'total_keys' in result['details'], "Details should have 'total_keys'"
        assert result['details']['ping'] is True, "Ping should be True when status is ok"
    
    print(f"✅ Redis check result: {result['status']} - {result['message']}")


def test_flow_guardian_check_returns_dict():
    """FlowGuardian (Engine) check가 올바른 형식의 dict를 반환하는지 검증"""
    result = check_flow_guardian()
    
    assert isinstance(result, dict), "Result should be a dict"
    assert 'status' in result, "Result should have 'status' key"
    assert 'message' in result, "Result should have 'message' key"
    assert 'details' in result, "Result should have 'details' key"
    
    assert result['status'] in ['ok', 'warn', 'fail'], "Status should be 'ok', 'warn', or 'fail'"
    
    if result['status'] == 'ok':
        assert 'engine_module' in result['details'], "Details should have 'engine_module'"
    
    print(f"✅ FlowGuardian check result: {result['status']} - {result['message']}")


def test_all_checks_pass_in_healthy_env():
    """
    정상 환경에서 모든 체크가 PASS하는지 검증
    
    이 테스트는 Docker 컨테이너가 실행 중이고 DB/Redis가 정상일 때만 PASS
    """
    db_result = check_db()
    redis_result = check_redis()
    guardian_result = check_flow_guardian()
    
    # DB와 Redis는 반드시 OK여야 함
    assert db_result['status'] == 'ok', f"DB check should pass: {db_result['message']}"
    assert redis_result['status'] == 'ok', f"Redis check should pass: {redis_result['message']}"
    
    # FlowGuardian (Engine)은 OK 또는 WARN 허용
    assert guardian_result['status'] in ['ok', 'warn'], f"FlowGuardian check should be ok or warn: {guardian_result['message']}"
    
    print("✅ All checks passed in healthy environment")
    print(f"  - DB: {db_result['status']}")
    print(f"  - Redis: {redis_result['status']}")
    print(f"  - FlowGuardian: {guardian_result['status']}")


def test_diagnostics_script_can_be_imported():
    """진단 스크립트가 정상적으로 import되는지 검증"""
    try:
        import scripts.infra.phase24_1_infra_diagnostics as diag
        
        assert hasattr(diag, 'check_db'), "Module should have check_db function"
        assert hasattr(diag, 'check_redis'), "Module should have check_redis function"
        assert hasattr(diag, 'check_flow_guardian'), "Module should have check_flow_guardian function"
        assert hasattr(diag, 'main'), "Module should have main function"
        
        print("✅ Diagnostics module import successful")
    
    except ImportError as e:
        pytest.fail(f"Failed to import diagnostics module: {e}")


if __name__ == "__main__":
    # 개별 실행 시 pytest 없이도 실행 가능
    print("=" * 80)
    print("PHASE24-1: Infra Diagnostics Tests")
    print("=" * 80)
    
    # 간단한 smoke test
    print("\n[1/5] Testing diagnostics module import...")
    test_diagnostics_script_can_be_imported()
    
    print("\n[2/5] Testing DB check...")
    test_db_check_returns_dict()
    
    print("\n[3/5] Testing Redis check...")
    test_redis_check_returns_dict()
    
    print("\n[4/5] Testing FlowGuardian check...")
    test_flow_guardian_check_returns_dict()
    
    print("\n[5/5] Testing all checks in healthy env...")
    test_all_checks_pass_in_healthy_env()
    
    print("\n" + "=" * 80)
    print("✅ All smoke tests passed!")
    print("=" * 80)
    print("\nRun 'pytest tests/test_phase24_1_infra_diagnostics.py' for full test suite")
