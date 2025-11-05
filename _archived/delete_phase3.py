import os
file_path = 'Docs/PHASE2/PHASE3_INTEGRATION.md'
if os.path.exists(file_path):
    os.remove(file_path)
    print(f"✅ {file_path} 삭제 완료")
else:
    print(f"⏭️  {file_path} 이미 없음")
