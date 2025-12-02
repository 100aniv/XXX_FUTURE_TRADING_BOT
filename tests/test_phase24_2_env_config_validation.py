"""
PHASE24-2: Env & Config Validation Tests
=========================================
환경변수 및 YAML config 검증 테스트

테스트 케이스:
1. 환경변수 검증 (필수 키 누락, 타입 오류 등)
2. Config 파일 검증 (파싱, 필수 필드, 전략 이름 등)
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.infra.env_config_validator import (
    validate_env,
    validate_config,
    validate_all,
)


# ============================================
# 환경변수 검증 테스트
# ============================================

def test_env_missing_required_key():
    """필수 환경변수 누락 시 FAIL"""
    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        # DB_NAME 누락
        'DB_USER': 'user',
        'DB_PASSWORD': 'pass',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
    }, clear=True):
        is_valid, errors = validate_env(load_env=False)
        assert not is_valid, "필수 키 누락 시 검증 실패해야 함"
        assert any('DB_NAME' in err for err in errors), "DB_NAME 누락 에러가 있어야 함"


def test_env_invalid_type():
    """잘못된 타입(포트가 문자열) 시 FAIL"""
    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': 'not_a_number',  # 잘못된 타입
        'DB_NAME': 'trading',
        'DB_USER': 'user',
        'DB_PASSWORD': 'pass',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
    }, clear=True):
        is_valid, errors = validate_env(load_env=False)
        assert not is_valid, "타입 오류 시 검증 실패해야 함"
        assert any('DB_PORT' in err and 'int' in err for err in errors), \
            "DB_PORT 타입 에러가 있어야 함"


def test_env_valid():
    """정상 환경변수 시 PASS"""
    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'trading',
        'DB_USER': 'user',
        'DB_PASSWORD': 'pass',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
    }, clear=True):
        is_valid, errors = validate_env(load_env=False)
        assert is_valid, f"정상 환경변수는 검증 통과해야 함 (errors: {errors})"
        assert len(errors) == 0, "에러가 없어야 함"


# ============================================
# Config 파일 검증 테스트
# ============================================

def test_config_missing_field():
    """필수 필드 누락 시 FAIL"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
        # mode 필드 누락
        f.write("""
symbol: BTCUSDT
timeframe: 5m
ensemble:
  enabled: true
  strategies:
    - scalping_v3
""")
        f.flush()
        config_path = f.name
    
    try:
        is_valid, errors = validate_config(config_path)
        assert not is_valid, "필수 필드 누락 시 검증 실패해야 함"
        assert any('mode' in err for err in errors), "mode 누락 에러가 있어야 함"
    finally:
        os.unlink(config_path)


def test_config_invalid_strategy():
    """미존재 전략 이름 시 FAIL"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
        f.write("""
mode: paper
symbol: BTCUSDT
timeframe: 5m
ensemble:
  enabled: true
  strategies:
    - scalping_v3
    - non_existent_strategy
""")
        f.flush()
        config_path = f.name
    
    try:
        is_valid, errors = validate_config(config_path)
        assert not is_valid, "미존재 전략 이름 시 검증 실패해야 함"
        assert any('non_existent_strategy' in err for err in errors), \
            "미존재 전략 에러가 있어야 함"
    finally:
        os.unlink(config_path)


def test_config_invalid_type():
    """잘못된 타입/범위 시 FAIL"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
        f.write("""
mode: paper
symbol: BTCUSDT
timeframe: 5m
paper:
  duration_hours: -1
ensemble:
  enabled: true
  strategies:
    - scalping_v3
""")
        f.flush()
        config_path = f.name
    
    try:
        is_valid, errors = validate_config(config_path)
        assert not is_valid, "잘못된 타입/범위 시 검증 실패해야 함"
        assert any('duration_hours' in err and '> 0' in err for err in errors), \
            "duration_hours 범위 에러가 있어야 함"
    finally:
        os.unlink(config_path)


def test_config_invalid_ensemble_mode():
    """잘못된 ensemble mode 시 FAIL"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
        f.write("""
mode: paper
symbol: BTCUSDT
timeframe: 5m
ensemble:
  enabled: true
  mode: invalid_mode
  strategies:
    - scalping_v3
""")
        f.flush()
        config_path = f.name
    
    try:
        is_valid, errors = validate_config(config_path)
        assert not is_valid, "잘못된 ensemble mode 시 검증 실패해야 함"
        assert any('invalid_mode' in err for err in errors), \
            "ensemble mode 에러가 있어야 함"
    finally:
        os.unlink(config_path)


def test_config_valid():
    """정상 config 시 PASS"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
        f.write("""
mode: paper
symbol: BTCUSDT
timeframe: 5m
paper:
  duration_hours: 1.0
  clean_start: true
ensemble:
  enabled: true
  mode: v2
  strategies:
    - scalping_v3
    - mean_reversion_v2
portfolio:
  initial_balance: 50000.0
  max_open_positions: 3
position_sizing:
  leverage: 3.0
""")
        f.flush()
        config_path = f.name
    
    try:
        is_valid, errors = validate_config(config_path)
        assert is_valid, f"정상 config는 검증 통과해야 함 (errors: {errors})"
        assert len(errors) == 0, "에러가 없어야 함"
    finally:
        os.unlink(config_path)


def test_config_file_not_found():
    """존재하지 않는 파일 시 FAIL"""
    is_valid, errors = validate_config('/non/existent/path.yml')
    assert not is_valid, "존재하지 않는 파일은 검증 실패해야 함"
    assert any('not found' in err.lower() for err in errors), \
        "파일 not found 에러가 있어야 함"


# ============================================
# 통합 테스트
# ============================================

def test_validate_all_with_valid_setup():
    """정상 env + config 시 exit code 0"""
    # 정상 환경변수 설정
    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'trading',
        'DB_USER': 'user',
        'DB_PASSWORD': 'pass',
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_DB': '0',
    }, clear=True):
        # 정상 config 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
            f.write("""
mode: paper
symbol: BTCUSDT
timeframe: 5m
ensemble:
  enabled: true
  strategies:
    - scalping_v3
""")
            f.flush()
            config_path = f.name
        
        try:
            exit_code = validate_all(config_paths=[config_path])
            assert exit_code == 0, "정상 setup은 exit code 0이어야 함"
        finally:
            os.unlink(config_path)


def test_validate_all_with_invalid_env():
    """비정상 env 시 exit code 1"""
    # 필수 키 누락
    with patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        # DB_PORT 누락
    }, clear=True):
        # validate_all()은 내부에서 validate_env()를 호출하므로 mock 필요
        with patch('scripts.infra.env_config_validator.validate_env') as mock_validate:
            mock_validate.return_value = (False, ['Missing required environment variable: DB_PORT'])
            exit_code = validate_all(config_paths=[])
            assert exit_code == 1, "비정상 env는 exit code 1이어야 함"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
