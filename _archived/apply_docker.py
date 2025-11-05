#!/usr/bin/env python3
import shutil
import os

print("="*60)
print("Docker Compose 파일 교체")
print("="*60)

# 1. 기존 파일 백업
if os.path.exists("docker-compose.yml"):
    shutil.move("docker-compose.yml", "_archived/docker-compose_old.yml")
    print("✅ docker-compose.yml → _archived/docker-compose_old.yml")

# 2. 새 파일 적용
if os.path.exists("docker-compose.yml.final"):
    shutil.move("docker-compose.yml.final", "docker-compose.yml")
    print("✅ docker-compose.yml.final → docker-compose.yml")

print("\n" + "="*60)
print("✅ 완료!")
print("="*60)
print("\n다음 명령어로 실행:")
print("  docker-compose up -d")
