#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL Database Module - Shim (Backward Compatibility)
===========================================================

⚠️ DEPRECATED: 이 파일은 하위 호환성을 위한 shim입니다.
⚠️ 새 코드에서는 `database.postgres` 모듈을 직접 사용하세요.

리팩토링 히스토리:
- 2025-10-19: bot_id 제거, 통합 시스템 기준 변경
- 2025-11-02: database/ 패키지로 이관 (PR 2)

마이그레이션 가이드:
    OLD: from common.database import get_db_connection
    NEW: from database.postgres import get_db_connection
    OR:  from database import get_db_connection
"""

# Re-export from new location
from database.postgres import (
    get_db_connection,
    save_signal_to_db,
    test_db_connection,
    get_latest_signals,
)

__all__ = [
    "get_db_connection",
    "save_signal_to_db",
    "test_db_connection",
    "get_latest_signals",
]
