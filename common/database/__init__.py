#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Common Database SHIM
====================
PHASE36-1 S2: Backward compatibility layer

⚠️ DEPRECATED PATH: Use `from database.postgres import ...` in new code
This shim allows legacy imports to work: `from common.database import save_signal_to_db`
"""
from database.postgres import (
    get_db_connection,
    save_signal_to_db,
    test_db_connection,
    get_latest_signals,
    get_database_url,
)

__all__ = [
    "get_db_connection",
    "save_signal_to_db",
    "test_db_connection",
    "get_latest_signals",
    "get_database_url",
]
