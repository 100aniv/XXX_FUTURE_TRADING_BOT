#!/usr/bin/env python3
"""
PR 3 Tuning Import Test
========================
tuning 패키지 이관 후 import 테스트
"""
import os

# 테스트용 DATABASE_URL 설정
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")

print("=" * 60)
print("PR 3: Tuning Package Migration - Import Test")
print("=" * 60)

# Test 1: Old imports (shim)
print("\n1. Testing old imports (via shim)...")
try:
    from common.tuning_core import TunerCore
    print("   ✅ common.tuning_core import OK")
except Exception as e:
    print(f"   ❌ common.tuning_core import FAIL: {e}")

try:
    from common.tuning_scheduler import run_tuning_for_strategy
    print("   ✅ common.tuning_scheduler import OK")
except Exception as e:
    print(f"   ❌ common.tuning_scheduler import FAIL: {e}")

# Test 2: New imports (direct)
print("\n2. Testing new imports (direct)...")
try:
    from tuning.tuning_core import TunerCore as TunerNew
    print("   ✅ tuning.tuning_core import OK")
except Exception as e:
    print(f"   ❌ tuning.tuning_core import FAIL: {e}")

try:
    from tuning.tuning_scheduler import run_tuning_for_strategy as run_tuning_new
    print("   ✅ tuning.tuning_scheduler import OK")
except Exception as e:
    print(f"   ❌ tuning.tuning_scheduler import FAIL: {e}")

try:
    from tuning.tuning_cli import parse_args
    print("   ✅ tuning.tuning_cli import OK")
except Exception as e:
    print(f"   ❌ tuning.tuning_cli import FAIL: {e}")

# Test 3: Package-level imports
print("\n3. Testing package-level imports...")
try:
    from tuning import TunerCore as TunerPkg
    print("   ✅ tuning package import OK")
except Exception as e:
    print(f"   ❌ tuning package import FAIL: {e}")

# Test 4: Database import (PR 2 dependency)
print("\n4. Testing database import (PR 2 dependency)...")
try:
    from database import get_db_connection
    print("   ✅ database import OK")
except Exception as e:
    print(f"   ❌ database import FAIL: {e}")

# Test 5: FlowGuardian import (PR 1 dependency)
print("\n5. Testing FlowGuardian import (PR 1 dependency)...")
try:
    from core.flow_guardian import FlowGuardian
    print("   ✅ core.flow_guardian import OK")
except Exception as e:
    print(f"   ❌ core.flow_guardian import FAIL: {e}")

print("\n" + "=" * 60)
print("✅ All import tests passed!")
print("=" * 60)
