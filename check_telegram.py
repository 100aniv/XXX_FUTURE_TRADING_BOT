#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텔레그램 봇 상태 확인 스크립트
"""
import os
import requests
from datetime import datetime
import dotenv

# .env 파일 로드
dotenv.load_dotenv()

# 토큰 및 채팅 ID 가져오기
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

def check_bot():
    """봇 상태 확인"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print(f"✅ 봇 정보: @{bot_info.get('username')} ({bot_info.get('first_name')})")
                print(f"✅ 봇 ID: {bot_info.get('id')}")
                print(f"✅ 상태: 정상 (API 응답 OK)")
                return True
            else:
                print(f"❌ 봇 상태 불량: {data}")
                return False
        else:
            print(f"❌ API 응답 오류: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 연결 오류: {e}")
        return False

def send_test_message():
    """테스트 메시지 전송"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"""⚠️ *PR12 테스트 메시지*
    
🔄 이 메시지는 PR12 텔레그램 연결 테스트입니다.
⏱️ 시간: {now}
📌 새 거래는 없습니다. 이전 거래가 표시될 수 있습니다.

*중요*: 
- 모든 Docker 컨테이너가 종료되었습니다.
- 새로운 거래가 있다면 다른 프로세스에서 실행 중인 것입니다.
- 화면 캡처 해주시면 확인하겠습니다.
    """
    
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            print(f"✅ 테스트 메시지 전송 성공")
            return True
        else:
            print(f"❌ 메시지 전송 실패: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("===== 텔레그램 봇 상태 확인 =====")
    bot_ok = check_bot()
    
    if bot_ok:
        print("\n===== 테스트 메시지 전송 =====")
        send_test_message()
    
    print("\n===== 환경 정보 =====")
    print(f"💬 채팅 ID: {chat_id}")
    print(f"🤖 토큰 길이: {len(token) if token else 0}자")

if __name__ == "__main__":
    main()
