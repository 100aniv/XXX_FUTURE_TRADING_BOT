import os
log_file = 'logs/application/2025-10-21.log'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print("=" * 80)
    print("최근 50줄 로그")
    print("=" * 80)
    for line in lines[-50:]:
        print(line.rstrip())
else:
    print("No log")
