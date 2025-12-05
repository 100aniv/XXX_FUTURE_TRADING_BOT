#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE23-3: Single Engine Entrypoint Tests
==========================================
엔진이 run_v2() 하나로 통일되어 있는지 검증하는 테스트
"""
import ast
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent


def test_run_backtest_calls_run_v2():
    """run_backtest.py가 run_v2를 호출하는지 확인"""
    script_path = PROJECT_ROOT / "scripts" / "run_backtest.py"
    
    assert script_path.exists(), "run_backtest.py가 존재해야 함"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # AST로 파싱하여 run_v2 import 확인
    tree = ast.parse(content)
    
    has_run_v2_import = False
    calls_run_v2 = False
    
    for node in ast.walk(tree):
        # from execution.engine import run_v2
        if isinstance(node, ast.ImportFrom):
            if node.module == 'execution.engine':
                for alias in node.names:
                    if alias.name == 'run_v2':
                        has_run_v2_import = True
        
        # run_v2(...)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'run_v2':
                calls_run_v2 = True
    
    assert has_run_v2_import, "run_backtest.py가 run_v2를 import해야 함"
    assert calls_run_v2, "run_backtest.py가 run_v2()를 호출해야 함"


def test_run_paper_calls_run_v2():
    """run_paper.py가 run_v2를 호출하는지 확인"""
    script_path = PROJECT_ROOT / "scripts" / "run_paper.py"
    
    assert script_path.exists(), "run_paper.py가 존재해야 함"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # AST로 파싱하여 run_v2 import 확인
    tree = ast.parse(content)
    
    has_run_v2_import = False
    calls_run_v2 = False
    
    for node in ast.walk(tree):
        # from execution.engine import run_v2
        if isinstance(node, ast.ImportFrom):
            if node.module == 'execution.engine':
                for alias in node.names:
                    if alias.name == 'run_v2':
                        has_run_v2_import = True
        
        # run_v2(...)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'run_v2':
                calls_run_v2 = True
    
    assert has_run_v2_import, "run_paper.py가 run_v2를 import해야 함"
    assert calls_run_v2, "run_paper.py가 run_v2()를 호출해야 함"


def test_run_v2_is_thin():
    """run_v2.py가 thin wrapper인지 확인 (200줄 이하)"""
    script_path = PROJECT_ROOT / "scripts" / "run_v2.py"
    
    assert script_path.exists(), "run_v2.py가 존재해야 함"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 빈 줄과 주석만 있는 줄 제외한 실제 코드 줄 수
    code_lines = [
        l for l in lines 
        if l.strip() and not l.strip().startswith('#')
    ]
    
    assert len(code_lines) < 200, f"run_v2.py가 너무 큼 ({len(code_lines)} lines, 목표 <200)"


def test_run_backtest_is_thin():
    """run_backtest.py가 thin wrapper인지 확인 (200줄 이하)"""
    script_path = PROJECT_ROOT / "scripts" / "run_backtest.py"
    
    assert script_path.exists(), "run_backtest.py가 존재해야 함"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 빈 줄과 주석만 있는 줄 제외한 실제 코드 줄 수
    code_lines = [
        l for l in lines 
        if l.strip() and not l.strip().startswith('#')
    ]
    
    assert len(code_lines) < 200, f"run_backtest.py가 너무 큼 ({len(code_lines)} lines, 목표 <200)"


def test_run_paper_is_thin():
    """run_paper.py가 thin wrapper인지 확인 (200줄 이하)"""
    script_path = PROJECT_ROOT / "scripts" / "run_paper.py"
    
    assert script_path.exists(), "run_paper.py가 존재해야 함"
    
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 빈 줄과 주석만 있는 줄 제외한 실제 코드 줄 수
    code_lines = [
        l for l in lines 
        if l.strip() and not l.strip().startswith('#')
    ]
    
    assert len(code_lines) < 200, f"run_paper.py가 너무 큼 ({len(code_lines)} lines, 목표 <200)"


def test_legacy_scripts_moved():
    """레거시 스크립트가 scripts/legacy/로 이동했는지 확인"""
    legacy_dir = PROJECT_ROOT / "scripts" / "legacy"
    
    assert legacy_dir.exists(), "scripts/legacy/ 디렉토리가 존재해야 함"
    
    # 이동되어야 할 레거시 스크립트 목록
    expected_legacy = [
        "run_all_wfa.py",
        "run_paper_phase16.py",
        "run_phase20_paper.py",
        "run_phase21_1a.py",
        "run_tuner.py",
    ]
    
    for script_name in expected_legacy:
        legacy_path = legacy_dir / script_name
        scripts_path = PROJECT_ROOT / "scripts" / script_name
        
        assert legacy_path.exists(), f"{script_name}가 scripts/legacy/에 있어야 함"
        assert not scripts_path.exists(), f"{script_name}가 scripts/에 남아있으면 안 됨"


def test_engine_has_run_v2():
    """execution/engine.py에 run_v2 함수가 존재하는지 확인"""
    engine_path = PROJECT_ROOT / "execution" / "engine.py"
    
    assert engine_path.exists(), "execution/engine.py가 존재해야 함"
    
    with open(engine_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # AST로 파싱하여 run_v2 정의 확인
    tree = ast.parse(content)
    
    has_run_v2 = False
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'run_v2':
            has_run_v2 = True
            break
    
    assert has_run_v2, "execution/engine.py에 run_v2() 함수가 정의되어야 함"


def test_no_run_v3_exists():
    """run_v3 같은 새로운 엔진 진입점이 없는지 확인"""
    scripts_dir = PROJECT_ROOT / "scripts"
    
    # run_v3.py, run_v4.py 등이 없어야 함
    for potential_file in scripts_dir.glob("run_v*.py"):
        if potential_file.name not in ["run_v2.py"]:
            pytest.fail(f"새로운 엔진 진입점 발견: {potential_file.name} (run_v2만 허용)")
