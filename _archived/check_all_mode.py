import os
log_file = 'logs/application/2025-10-21.log'
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # All 모드 로그만
    for line in lines[-30:]:
        if any(k in line for k in ['All 모드', 'max_streams', '심볼', 'WebSocket']):
            print(line.strip())
else:
    print("No log file")
