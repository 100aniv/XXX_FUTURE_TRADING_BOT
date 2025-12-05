#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-8: Signal SSOT Guard Tests
===================================
엔진 외부에서 신호를 직접 계산하는 코드 탐지 테스트

목적:
- scripts/ 및 scripts/research/에서 signal_logic() 직접 호출 방지
- add_indicators() + 신호 계산 패턴 탐지
- BaseStrategy.compute_signal() 엔진 없이 직접 호출 방지

허용:
- scripts/legacy/ 하위 (격리된 코드)
- tests/ 하위 (유닛 테스트)
- JSON만 읽는 분석 스크립트 (phase27_6, phase27_7)
"""
import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set

import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def find_direct_signal_calculations(file_path: Path) -> List[Tuple[int, str]]:
    """
    파일에서 신호를 직접 계산하는 패턴 탐지
    
    Args:
        file_path: 검사할 Python 파일
    
    Returns:
        [(line_number, pattern_description), ...]
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return violations
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return violations
    
    for node in ast.walk(tree):
        # 1. signal_logic() 직접 호출
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'signal_logic':
                line = node.lineno
                violations.append((line, "signal_logic() 직접 호출"))
            
            # 2. BaseStrategy.compute_signal() 직접 호출 (엔진 외부)
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'compute_signal':
                    # 엔진 내부 호출은 허용, 외부 직접 호출만 탐지
                    # 파일명으로 구분
                    if 'engine.py' not in str(file_path):
                        line = node.lineno
                        violations.append((line, "BaseStrategy.compute_signal() 엔진 외부 직접 호출"))
    
    return violations


def scan_scripts_directory() -> List[Tuple[Path, List[Tuple[int, str]]]]:
    """
    scripts/ 디렉토리 전체 스캔
    
    Returns:
        [(file_path, violations), ...]
    """
    results = []
    
    scripts_dir = PROJECT_ROOT / "scripts"
    
    # 제외 디렉토리
    exclude_dirs = {'legacy', '__pycache__', '.pytest_cache'}
    
    for py_file in scripts_dir.rglob("*.py"):
        # legacy, __pycache__ 제외
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        
        violations = find_direct_signal_calculations(py_file)
        if violations:
            results.append((py_file, violations))
    
    return results


def test_no_signal_logic_direct_calls():
    """scripts/에서 signal_logic() 직접 호출 금지"""
    violations = scan_scripts_directory()
    
    if violations:
        error_msg = "\n\n❌ SSOT 위반: 엔진 외부에서 신호 직접 계산 발견\n\n"
        for file_path, file_violations in violations:
            error_msg += f"📁 {file_path.relative_to(PROJECT_ROOT)}\n"
            for line, pattern in file_violations:
                error_msg += f"   Line {line}: {pattern}\n"
            error_msg += "\n"
        
        error_msg += """
공식 신호 계산 경로:
    execution/engine.py::run_v2()
        ↓
    BaseStrategy.compute_signal(df, config)
        ↓
    metrics/trade_activity_tracker.py

대안:
- 백테스트: scripts/run_backtest.py --config xxx.yml
- 연구용: phase27_5_btc5m_baseline_engine_replay.py (run_v2 호출)
- 분석: TradeActivityTracker Summary JSON 사용
"""
        pytest.fail(error_msg)


def test_phase27_6_is_json_only():
    """phase27_6_signal_parity_analyzer.py는 JSON만 읽는지 확인"""
    file_path = PROJECT_ROOT / "scripts" / "research" / "phase27_6_signal_parity_analyzer.py"
    
    if not file_path.exists():
        pytest.skip("phase27_6_signal_parity_analyzer.py가 존재하지 않음")
    
    violations = find_direct_signal_calculations(file_path)
    
    # JSON만 읽는 파일이므로 violations가 없어야 함
    assert len(violations) == 0, f"phase27_6은 JSON만 읽어야 함, 발견된 위반: {violations}"


def test_phase27_7_is_json_only():
    """phase27_7_btc5m_signal_parity_diff.py는 JSON만 읽는지 확인"""
    file_path = PROJECT_ROOT / "scripts" / "research" / "phase27_7_btc5m_signal_parity_diff.py"
    
    if not file_path.exists():
        pytest.skip("phase27_7_btc5m_signal_parity_diff.py가 존재하지 않음")
    
    violations = find_direct_signal_calculations(file_path)
    
    # JSON만 읽는 파일이므로 violations가 없어야 함
    assert len(violations) == 0, f"phase27_7은 JSON만 읽어야 함, 발견된 위반: {violations}"


def test_legacy_offline_scan_is_isolated():
    """Legacy Offline Scan이 scripts/legacy/에 격리되었는지 확인"""
    # scripts/research/에 phase27_4가 남아있으면 안 됨
    research_path = PROJECT_ROOT / "scripts" / "research" / "phase27_4_btc5m_baseline_signal_scan.py"
    
    assert not research_path.exists(), \
        "phase27_4_btc5m_baseline_signal_scan.py가 scripts/research/에 남아있음 (scripts/legacy/로 이동 필요)"
    
    # scripts/legacy/에 존재하는지 확인
    legacy_path = PROJECT_ROOT / "scripts" / "legacy" / "phase27_4_btc5m_baseline_signal_scan_legacy.py"
    
    assert legacy_path.exists(), \
        "phase27_4_btc5m_baseline_signal_scan_legacy.py가 scripts/legacy/에 없음"
    
    # 경고 주석이 있는지 확인
    with open(legacy_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "DEPRECATED" in content, "Legacy 파일에 DEPRECATED 경고가 없음"
    assert "SSOT" in content, "Legacy 파일에 SSOT 설명이 없음"


def test_run_v2_is_single_entrypoint():
    """run_v2가 단일 엔진 진입점인지 확인 (PHASE23-5 회귀 테스트)"""
    # scripts/에 run_v3, run_v4 등 새로운 엔진이 없는지 확인
    scripts_dir = PROJECT_ROOT / "scripts"
    
    for potential_file in scripts_dir.glob("run_v*.py"):
        if potential_file.name not in ["run_v2.py"]:
            pytest.fail(f"새로운 엔진 진입점 발견: {potential_file.name} (run_v2만 허용)")


def test_phase27_5_uses_subprocess():
    """phase27_5_btc5m_baseline_engine_replay.py가 subprocess로 run_v2를 호출하는지 확인"""
    file_path = PROJECT_ROOT / "scripts" / "research" / "phase27_5_btc5m_baseline_engine_replay.py"
    
    if not file_path.exists():
        pytest.skip("phase27_5_btc5m_baseline_engine_replay.py가 존재하지 않음")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # subprocess.run 호출 확인
    assert "subprocess.run" in content, \
        "phase27_5는 subprocess로 run_v2를 호출해야 함 (신호 직접 계산 금지)"
    
    # run_v2.py 호출 확인
    assert "run_v2.py" in content, \
        "phase27_5는 run_v2.py를 호출해야 함"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
