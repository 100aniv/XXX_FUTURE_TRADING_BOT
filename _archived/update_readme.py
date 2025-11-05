#!/usr/bin/env python3
import shutil

# 기존 README 백업
shutil.move("README.md", "_archived/README_old.md")
print("✅ README.md → _archived/README_old.md")
