#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""파일 정리 스크립트"""
import os
import shutil
from pathlib import Path

# 정리할 파일 목록
files_to_move = [
    "common/funding_fee.py",
    "common/backtest_utils.py",
    "check_all_mode.py",
    "check_logs.py",
    "check_recent_log.py",
    "main_backup.py",
    "test_config.py",
]

archived_dir = Path("_archived")
archived_dir.mkdir(exist_ok=True)

print("=" * 60)
print("📁 파일 정리 시작")
print("=" * 60)

for file_path in files_to_move:
    src = Path(file_path)
    if src.exists():
        dst = archived_dir / src.name
        try:
            shutil.move(str(src), str(dst))
            print(f"✅ {file_path} → _archived/{src.name}")
        except Exception as e:
            print(f"❌ {file_path} 이동 실패: {e}")
    else:
        print(f"⏭️  {file_path} 없음 (이미 정리됨)")

print("=" * 60)
print("✅ 파일 정리 완료")
print("=" * 60)
