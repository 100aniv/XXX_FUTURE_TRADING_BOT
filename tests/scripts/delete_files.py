#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""불필요 파일 삭제"""
import os

files_to_delete = [
    "execution/liquidation_checker.py",
    "indicators/regime_tagger.py"
]

for file_path in files_to_delete:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"✅ 삭제 완료: {file_path}")
    else:
        print(f"⚠️ 파일 없음: {file_path}")

print("\n🎉 파일 정리 완료!")
