#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텔레그램 중복 메시지 방지 테스트 스크립트
"""
import os
import time
import yaml
import dotenv
from common.messaging import tg

# .env 파일 로드
dotenv.load_dotenv()

# 설정 파일 로드
def load_config():
    with open('config.yml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def test_duplicate_prevention():
    """중복 메시지 방지 로직 테스트"""
    config = load_config()
    
    # 텔레그램 설정 확인
    print("텔레그램 설정 확인 중...")
    tg_config = config.get("telegram", {})
    token = tg_config.get("token", "")
    chat_id = str(tg_config.get("chat_id", ""))
    enabled = tg_config.get("enabled", False)
    
    print(f"Telegram 활성화: {enabled}")
    print(f"토큰: {token[:5]}...{token[-5:]}")
    print(f"채팅 ID: {chat_id}")
    
    # 동일 메시지 여러번 전송 시도
    message = f"""⚠️ *PR12 중복 메시지 방지 테스트*
    
📋 메시지 ID: TEST_DUPLICATE_{int(time.time())}
⏱️ 시간: {time.strftime("%H:%M:%S")}
    
*테스트 방식*:
- 동일 메시지 5회 연속 전송
- 각 메시지 사이 간격 1초
- 정상 작동 시 첫 번째 메시지만 텔레그램에 표시됨
- 나머지는 중복 감지되어 차단됨

📝 PR12 버그 수정 상태: 검증 중
"""
    
    print("\n중복 메시지 전송 테스트 시작 (5회):")
    
    # 동일 메시지 5회 전송 시도
    success_count = 0
    for i in range(5):
        print(f"  시도 {i+1}...")
        result = tg(message, config)
        if result:
            success_count += 1
        time.sleep(1)  # 1초 대기
    
    print(f"\n결과: 성공 {success_count}/5 (정상 작동 시 1/5)")
    
    # 약간 다른 메시지 전송 (시간 업데이트)
    print("\n약간 다른 메시지 전송 테스트:")
    message_updated = f"""⚠️ *PR12 중복 메시지 방지 테스트*
    
📋 메시지 ID: TEST_DUPLICATE_{int(time.time())}
⏱️ 시간: {time.strftime("%H:%M:%S")}
    
*다른 메시지 테스트*:
- 내용이 약간 다른 메시지는 정상 전송됨
- 이 메시지는 전송되어야 정상임

📝 PR12 버그 수정 상태: 확인 완료
"""
    
    result = tg(message_updated, config)
    print(f"  결과: {'성공' if result else '실패'} (정상 작동 시 성공)")

if __name__ == "__main__":
    test_duplicate_prevention()
