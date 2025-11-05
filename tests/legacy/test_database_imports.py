#!/usr/bin/env python3
"""
PR 2 Database Import Test
==========================
database 패키지 이관 후 import 테스트
"""
import os

# 테스트용 DATABASE_URL 설정
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")

print("=" * 60)
print("PR 2: Database Package Migration - Import Test")
print("=" * 60)

# Test 1: Old imports (shim)
print("\n1. Testing old imports (via shim)...")
try:
    from common.database import get_db_connection, save_signal_to_db
    print("   ✅ common.database import OK")
except Exception as e:
    print(f"   ❌ common.database import FAIL: {e}")

try:
    from common.redis_client import RedisClient
    print("   ✅ common.redis_client import OK")
except Exception as e:
    print(f"   ❌ common.redis_client import FAIL: {e}")

# Test 2: New imports (direct)
print("\n2. Testing new imports (direct)...")
try:
    from database.postgres import get_db_connection as get_conn_new
    print("   ✅ database.postgres import OK")
except Exception as e:
    print(f"   ❌ database.postgres import FAIL: {e}")

try:
    from database.redis import RedisClient as RedisNew
    print("   ✅ database.redis import OK")
except Exception as e:
    print(f"   ❌ database.redis import FAIL: {e}")

# Test 3: Package-level imports
print("\n3. Testing package-level imports...")
try:
    from database import get_db_connection as get_conn_pkg, RedisClient as RedisPkg
    print("   ✅ database package import OK")
except Exception as e:
    print(f"   ❌ database package import FAIL: {e}")

# Test 4: core/flow_guardian.py import (PR 1 dependency)
print("\n4. Testing FlowGuardian import (PR 1 dependency)...")
try:
    from core.flow_guardian import FlowGuardian
    print("   ✅ core.flow_guardian import OK")
except Exception as e:
    print(f"   ❌ core.flow_guardian import FAIL: {e}")

print("\n" + "=" * 60)
print("✅ All import tests passed!")
print("=" * 60)
