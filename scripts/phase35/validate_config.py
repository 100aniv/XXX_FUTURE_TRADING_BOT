#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Config validation script"""
import sys
import yaml
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.config_preflight import assert_required
from common.config_required import REQUIRED_DOTPATHS

config_path = project_root / "configs" / "phase35" / "phase35_2_iter3_ssot.yaml"
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

required = [k for k in REQUIRED_DOTPATHS if k != "backtest.output_file"]

try:
    assert_required(config, required, context="Direct Validation")
    print(f"✅ ALL PASS: {len(required)} keys validated")
except RuntimeError as e:
    print(str(e))
    sys.exit(1)
