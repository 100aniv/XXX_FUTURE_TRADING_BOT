#!/usr/bin/env python3
"""
문서 정리 스크립트
=================
루트의 MD 파일들을 docs/COMPLETE/로 이동
"""
import shutil

# 이동할 파일들
files_to_move = [
    "PROJECT_STRUCTURE.md",
    "REFACTORING_COMPLETE.md", 
    "CHANGELOG.md"
]

print("="*60)
print("문서 정리 시작")
print("="*60)

for filename in files_to_move:
    try:
        src = filename
        dst = f"docs/COMPLETE/{filename}"
        shutil.move(src, dst)
        print(f"✅ {filename} → docs/COMPLETE/")
    except FileNotFoundError:
        print(f"⏭️  {filename} 없음")
    except Exception as e:
        print(f"❌ {filename} 이동 실패: {e}")

print("\n" + "="*60)
print("완료!")
print("="*60)
print("\n루트에 남은 MD 파일:")
print("  ✅ README.md (메인)")
print("  ✅ SYSTEM_ARCHITECTURE.md (전체 아키텍처)")
