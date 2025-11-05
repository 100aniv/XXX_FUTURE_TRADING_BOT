#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Client Module - Shim (Backward Compatibility)
====================================================

⚠️ DEPRECATED: 이 파일은 하위 호환성을 위한 shim입니다.
⚠️ 새 코드에서는 `database.redis` 모듈을 직접 사용하세요.

리팩토링 히스토리:
- 2025-11-02: database/ 패키지로 이관 (PR 2)

마이그레이션 가이드:
    OLD: from common.redis_client import RedisClient
    NEW: from database.redis import RedisClient
    OR:  from database import RedisClient
"""

# Re-export from new location
from database.redis import RedisClient

__all__ = ["RedisClient"]
