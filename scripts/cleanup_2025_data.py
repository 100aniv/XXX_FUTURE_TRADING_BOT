#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2025년 미래 데이터 삭제 스크립트
"""
import os
from pathlib import Path

# 데이터 디렉토리
data_dir = Path(__file__).parent.parent / 'data'

# 2025년 데이터 파일 찾기
files_to_delete = list(data_dir.glob('*2025*.csv'))

if not files_to_delete:
    print("✅ 삭제할 2025년 데이터 없음")
else:
    print(f"🗑️  {len(files_to_delete)}개 파일 삭제 예정:")
    for file in files_to_delete:
        print(f"   - {file.name}")
    
    # 삭제 진행
    for file in files_to_delete:
        try:
            file.unlink()
            print(f"✅ 삭제: {file.name}")
        except Exception as e:
            print(f"❌ 삭제 실패: {file.name} - {e}")
    
    print(f"\n✅ 총 {len(files_to_delete)}개 파일 삭제 완료")

# 남은 파일 확인
remaining = list(data_dir.glob('*.csv'))
print(f"\n📂 남은 CSV 파일: {len(remaining)}개")
for file in remaining:
    size_mb = file.stat().st_size / 1024 / 1024
    print(f"   - {file.name} ({size_mb:.2f} MB)")
