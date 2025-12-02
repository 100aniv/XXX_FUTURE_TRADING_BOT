#!/usr/bin/env python3
"""
PHASE24-2: Env & Config Validator
==================================
환경변수 및 YAML config 파일 검증 도구

주요 기능:
1. 환경변수 검증 (필수 키 누락, 타입 오류 등)
2. YAML config 검증 (파싱, 필수 필드, 전략 이름 등)
3. 상세 에러 리포트 출력

사용법:
  python scripts/infra/env_config_validator.py
  
Exit Code:
  0: 검증 성공
  1: 검증 실패
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any
import yaml

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from common.logger import setup_logger

logger = setup_logger('env_config_validator', log_type='application')

# ============================================
# 필수 환경변수 정의
# ============================================
REQUIRED_ENV_KEYS = [
    'DB_HOST',
    'DB_PORT',
    'DB_NAME',
    'DB_USER',
    'DB_PASSWORD',
    'REDIS_HOST',
    'REDIS_PORT',
    'REDIS_DB',
]

# 정수형이어야 하는 환경변수
INT_ENV_KEYS = [
    'DB_PORT',
    'REDIS_PORT',
    'REDIS_DB',
]

# Boolean 환경변수 (선택)
BOOL_ENV_KEYS = [
    'ENABLE_TELEGRAM',
]

# ============================================
# 전략 Registry (strategies/__init__.py 기준)
# ============================================
# PHASE23-2 기준: V2 전략 registry
VALID_STRATEGIES = [
    'scalping_v3',
    'volatility_breakout_v2',
    'mean_reversion_v2',
    'trend_follow_v2',
    'volume_based_v2',
    # Legacy 전략들 (deprecated, 하지만 여전히 존재)
    'scalping',
    'swing_bb',
    'daytrade',
    'swing',
    'trend',
    'reversion',
    'breakout',
]

# Ensemble mode 값
VALID_ENSEMBLE_MODES = [
    'v2',           # PHASE23-3: Score V2 모드
    'score_v2',     # 동일 (alias)
    'disabled',     # Ensemble 비활성화
    'factor',       # Legacy factor-based (PHASE22 이전)
]

# ============================================
# 환경변수 검증
# ============================================
def validate_env(load_env: bool = True) -> Tuple[bool, List[str]]:
    """
    환경변수 검증
    
    Args:
        load_env: .env 파일 로드 여부 (테스트 시 False)
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # .env 파일 로드 (있다면)
    if load_env:
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
    
    # 1. 필수 키 존재 여부
    for key in REQUIRED_ENV_KEYS:
        value = os.getenv(key)
        if not value:
            errors.append(f"Missing required environment variable: {key}")
    
    # 2. 정수형 타입 검증
    for key in INT_ENV_KEYS:
        value = os.getenv(key)
        if value:
            try:
                int(value)
            except ValueError:
                errors.append(f"Invalid type for {key}: expected int, got '{value}'")
    
    # 3. Boolean 타입 검증 (선택)
    for key in BOOL_ENV_KEYS:
        value = os.getenv(key)
        if value and value.lower() not in ['true', 'false', '0', '1']:
            errors.append(f"Invalid boolean for {key}: expected true/false, got '{value}'")
    
    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================
# Config 검증
# ============================================
def validate_config(config_path: str) -> Tuple[bool, List[str]]:
    """
    YAML config 파일 검증
    
    Args:
        config_path: config 파일 경로
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # 1. 파일 존재 여부
    if not Path(config_path).exists():
        errors.append(f"Config file not found: {config_path}")
        return False, errors
    
    # 2. YAML 파싱
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error in {config_path}: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Failed to read {config_path}: {e}")
        return False, errors
    
    if not isinstance(config, dict):
        errors.append(f"Config must be a dictionary, got {type(config)}")
        return False, errors
    
    # 3. 필수 필드 검증
    required_fields = ['mode', 'symbol', 'timeframe']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: '{field}'")
    
    # 4. Mode 값 검증
    if 'mode' in config:
        valid_modes = ['paper', 'backtest', 'live']
        if config['mode'] not in valid_modes:
            errors.append(f"Invalid mode: '{config['mode']}' (valid: {valid_modes})")
    
    # 5. Ensemble 설정 검증
    if 'ensemble' in config:
        ensemble = config['ensemble']
        
        # Ensemble enabled 여부
        if isinstance(ensemble, dict):
            # 전략 리스트 검증
            if 'strategies' in ensemble:
                strategies = ensemble['strategies']
                if not isinstance(strategies, list):
                    errors.append(f"ensemble.strategies must be a list, got {type(strategies)}")
                elif len(strategies) == 0:
                    errors.append("ensemble.strategies must have at least 1 strategy")
                else:
                    # 각 전략 이름 검증
                    for strategy_name in strategies:
                        if strategy_name not in VALID_STRATEGIES:
                            errors.append(
                                f"Unknown strategy: '{strategy_name}' "
                                f"(valid strategies: {', '.join(VALID_STRATEGIES[:5])}...)"
                            )
            
            # Ensemble mode 검증
            if 'mode' in ensemble:
                ensemble_mode = ensemble['mode']
                if ensemble_mode not in VALID_ENSEMBLE_MODES:
                    errors.append(
                        f"Invalid ensemble.mode: '{ensemble_mode}' "
                        f"(valid: {', '.join(VALID_ENSEMBLE_MODES)})"
                    )
    
    # 6. Paper 모드일 때 duration 검증
    if config.get('mode') == 'paper':
        if 'paper' in config:
            paper_cfg = config['paper']
            if 'duration_hours' in paper_cfg:
                duration = paper_cfg['duration_hours']
                try:
                    duration_float = float(duration)
                    if duration_float <= 0:
                        errors.append(f"paper.duration_hours must be > 0, got {duration}")
                except (ValueError, TypeError):
                    errors.append(f"paper.duration_hours must be a number, got {duration}")
    
    # 7. Portfolio 설정 검증
    if 'portfolio' in config:
        portfolio = config['portfolio']
        if 'max_open_positions' in portfolio:
            max_pos = portfolio['max_open_positions']
            try:
                max_pos_int = int(max_pos)
                if max_pos_int <= 0:
                    errors.append(f"portfolio.max_open_positions must be > 0, got {max_pos}")
            except (ValueError, TypeError):
                errors.append(f"portfolio.max_open_positions must be an integer, got {max_pos}")
    
    # 8. Position sizing leverage 검증
    if 'position_sizing' in config:
        pos_sizing = config['position_sizing']
        if 'leverage' in pos_sizing:
            leverage = pos_sizing['leverage']
            try:
                leverage_float = float(leverage)
                if leverage_float < 1.0:
                    errors.append(f"position_sizing.leverage must be >= 1.0, got {leverage}")
            except (ValueError, TypeError):
                errors.append(f"position_sizing.leverage must be a number, got {leverage}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================
# 전체 검증 실행
# ============================================
def validate_all(config_paths: List[str] = None) -> int:
    """
    전체 검증 실행 (env + configs)
    
    Args:
        config_paths: 검증할 config 파일 경로 리스트 (None이면 기본 경로 사용)
    
    Returns:
        exit_code (0: OK, 1: FAIL)
    """
    print("=" * 80)
    print("PHASE24-2: Env & Config Validation")
    print("=" * 80)
    print()
    
    all_valid = True
    
    # 1. 환경변수 검증
    print("[1/2] Environment Variables Check...")
    env_valid, env_errors = validate_env()
    
    if env_valid:
        print("  Status: [PASS]")
        print()
    else:
        print("  Status: [FAIL]")
        print("  Errors:")
        for error in env_errors:
            print(f"    - {error}")
        print()
        all_valid = False
    
    # 2. Config 파일 검증
    print("[2/2] Config Files Check...")
    
    # 기본 config 경로 (없으면 자동 탐색)
    if config_paths is None:
        config_dir = project_root / 'configs' / 'paper'
        if config_dir.exists():
            config_paths = [str(p) for p in config_dir.glob('*.yml')]
        else:
            config_paths = []
    
    if not config_paths:
        print("  Status: [SKIP] (no config files found)")
        print()
    else:
        print(f"  Files to check: {len(config_paths)}")
        
        config_errors = []
        for config_path in config_paths:
            config_valid, errors = validate_config(config_path)
            if not config_valid:
                config_errors.append((config_path, errors))
        
        if not config_errors:
            print("  Status: [PASS]")
            print()
        else:
            print("  Status: [FAIL]")
            print("  Errors:")
            for config_path, errors in config_errors:
                print(f"    File: {Path(config_path).name}")
                for error in errors:
                    print(f"      - {error}")
            print()
            all_valid = False
    
    # 3. 최종 결과
    print("=" * 80)
    if all_valid:
        print("[PASS] VALIDATION PASSED")
        print("=" * 80)
        print()
        print("[ACTION] Environment and configs are ready for paper/backtest/live")
        return 0
    else:
        print("[FAIL] VALIDATION FAILED")
        print("=" * 80)
        print()
        print("[ACTION] Fix the issues above before running paper/backtest/live")
        return 1


# ============================================
# CLI 진입점
# ============================================
def main() -> int:
    """
    CLI 진입점
    
    Returns:
        exit_code (0: OK, 1: FAIL)
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PHASE24-2: Env & Config Validator'
    )
    parser.add_argument(
        '--config',
        nargs='*',
        help='Config files to validate (default: all paper configs)'
    )
    
    args = parser.parse_args()
    
    return validate_all(config_paths=args.config)


if __name__ == '__main__':
    sys.exit(main())
