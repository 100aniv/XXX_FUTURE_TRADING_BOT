#!/usr/bin/env python3
import shutil

# 기존 main.py → _archived/main_old.py
shutil.move("main.py", "_archived/main_old.py")
print("✅ main.py → _archived/main_old.py")

# main_v2.py → main.py
shutil.move("main_v2.py", "main.py")
print("✅ main_v2.py → main.py")

print("\n완료!")
