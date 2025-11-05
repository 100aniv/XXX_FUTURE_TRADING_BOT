#!/usr/bin/env python3
"""
Import 테스트 - 모든 Signal Bot 파일
"""
import sys

print("="*60)
print("🧪 Import 테스트 시작")
print("="*60)

files_to_test = [
    "telegram_signal_bot",
    "signal_bot_trend",
    "signal_bot_reversion",
    "signal_bot_breakout"
]

success_count = 0
fail_count = 0

for file_name in files_to_test:
    try:
        print(f"\n[{file_name}]", end=" ")
        __import__(file_name)
        print("✅ SUCCESS")
        success_count += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
        fail_count += 1

print("\n" + "="*60)
print(f"📊 결과: ✅ {success_count} / ❌ {fail_count}")
print("="*60)

if fail_count == 0:
    print("\n🎉 모든 파일 Import 성공!")
else:
    print(f"\n⚠️  {fail_count}개 파일에 문제가 있습니다.")
    sys.exit(1)
