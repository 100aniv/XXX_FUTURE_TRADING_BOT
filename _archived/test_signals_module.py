#!/usr/bin/env python3
"""signals 모듈 테스트"""

try:
    from signals import SignalGenerator
    print("✅ signals.SignalGenerator import 성공")
except Exception as e:
    print(f"❌ signals import 실패: {e}")

try:
    from signals.signal_storage import save_signal
    print("✅ signals.signal_storage import 성공")
except Exception as e:
    print(f"❌ signal_storage import 실패: {e}")

try:
    from common.config import load_config
    cfg = load_config()
    gen = SignalGenerator(cfg)
    print("✅ SignalGenerator 초기화 성공")
except Exception as e:
    print(f"❌ SignalGenerator 초기화 실패: {e}")

print("\n🎉 signals/ 모듈 리팩토링 완료!")
