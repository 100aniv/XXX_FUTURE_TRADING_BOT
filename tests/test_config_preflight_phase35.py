#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER5.6: Config Preflight Test
=========================================

목적: phase35_2_iter3_ssot.yaml이 모든 필수 키를 포함하는지 검증
"""
import sys
import yaml
import pytest
from pathlib import Path

# Project root 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from common.config_preflight import assert_required
from common.config_required import REQUIRED_DOTPATHS


def test_phase35_config_has_all_required_keys():
    """phase35_2_iter3_ssot.yaml이 모든 필수 키를 포함하는지 검증"""
    config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
    
    assert config_path.exists(), f"Config not found: {config_path}"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # backtest.output_file은 런타임에 설정되므로 제외
    required_keys = [k for k in REQUIRED_DOTPATHS if k != "backtest.output_file"]
    
    # Preflight 검증 (누락 시 RuntimeError)
    try:
        assert_required(config, required_keys, context="Test Config Preflight")
        print(f"✅ Config Preflight PASS: {len(required_keys)}개 필수 키 확인")
    except RuntimeError as e:
        pytest.fail(f"Config Preflight FAIL: {e}")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
