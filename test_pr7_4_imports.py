#!/usr/bin/env python3
"""PR7-4 Import 테스트"""
import os
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_NAME', 'test')
os.environ.setdefault('DB_USER', 'test')
os.environ.setdefault('DB_PASSWORD', 'test')

print("테스트 시작...")

# 1. adapters import
try:
    from execution.adapters import preload_multi_timeframes, create_adapters
    print("✅ execution.adapters import 성공")
except Exception as e:
    print(f"❌ execution.adapters import 실패: {e}")
    exit(1)

# 2. WebSocketCollector import
try:
    from collectors import WebSocketCollector
    print("✅ collectors.WebSocketCollector import 성공")
except Exception as e:
    print(f"❌ collectors.WebSocketCollector import 실패: {e}")
    exit(1)

# 3. common.utils import
try:
    from common.utils import make_streams
    print("✅ common.utils.make_streams import 성공")
except Exception as e:
    print(f"❌ common.utils.make_streams import 실패: {e}")
    exit(1)

# 4. config 로드
try:
    from common.config_loader import load_config
    config = load_config()
    print(f"✅ config 로드 성공")
    
    # flow_guardian 섹션 확인
    if 'flow_guardian' in config:
        print(f"✅ flow_guardian 섹션 존재: {config['flow_guardian']}")
    else:
        print(f"❌ flow_guardian 섹션 없음")
        
    # strategies min_bars_for_signal 확인
    strategies = config.get('strategies', {})
    for name, cfg in strategies.items():
        min_bars = cfg.get('min_bars_for_signal', 'N/A')
        print(f"   {name}: min_bars_for_signal={min_bars}")
        
except Exception as e:
    print(f"❌ config 로드 실패: {e}")
    exit(1)

print("\n✅ 모든 import 테스트 통과!")
