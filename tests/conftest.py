#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest configuration for tests
"""
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_collection_modifyitems(config, items):
    """legacy 폴더의 테스트는 skip"""
    skip_legacy = pytest.mark.skip(reason="legacy test - sys.exit(1) 사용")
    for item in items:
        if "legacy" in str(item.fspath):
            item.add_marker(skip_legacy)
