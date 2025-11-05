#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Package
================
PostgreSQL 및 Redis 통합 패키지

리팩토링: 2025-11-02
- common/database.py → database/postgres.py
- common/redis_client.py → database/redis.py
"""

from .postgres import (
    get_db_connection,
    save_signal_to_db,
    test_db_connection,
    get_latest_signals,
)

from .redis import RedisClient

__all__ = [
    "get_db_connection",
    "save_signal_to_db",
    "test_db_connection",
    "get_latest_signals",
    "RedisClient",
]
