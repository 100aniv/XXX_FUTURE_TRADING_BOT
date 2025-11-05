#!/usr/bin/env python3
import shutil
import os

print("="*60)
print("Dockerfile 교체")
print("="*60)

# 1. 기존 Dockerfile 백업
if os.path.exists("Dockerfile"):
    shutil.move("Dockerfile", "_archived/Dockerfile_old")
    print("✅ Dockerfile → _archived/Dockerfile_old")
else:
    print("⏭️  기존 Dockerfile 없음")

# 2. Dockerfile.new → Dockerfile
if os.path.exists("Dockerfile.new"):
    shutil.move("Dockerfile.new", "Dockerfile")
    print("✅ Dockerfile.new → Dockerfile")
else:
    print("❌ Dockerfile.new 없음")

print("\n" + "="*60)
print("✅ 완료!")
print("="*60)
