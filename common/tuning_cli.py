#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tuning CLI Module - Shim (Backward Compatibility)
==================================================

⚠️ DEPRECATED: 이 파일은 하위 호환성을 위한 shim입니다.
⚠️ 새 코드에서는 `tuning.tuning_cli` 모듈을 직접 사용하세요.

리팩토링 히스토리:
- 2025-11-02: tuning/ 패키지로 이관 (PR 3)

마이그레이션 가이드:
    OLD: python -u common/tuning_cli.py ...
    NEW: python -u -m tuning.tuning_cli ...
"""

# Re-export from new location
from tuning.tuning_cli import *

# CLI entry point
if __name__ == "__main__":
    from tuning import tuning_cli
    tuning_cli.main()
