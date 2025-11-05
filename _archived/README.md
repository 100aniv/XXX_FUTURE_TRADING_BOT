# Archived Signal Bot Files

**날짜:** 2025-10-19  
**이유:** main.py로 통합 완료

## 백업된 파일들

이 폴더에는 리팩토링 전의 Signal Bot 파일들이 보관되어 있습니다.

### 파일 목록:
- `telegram_signal_bot.py` - 원본 메인 파일
- `signal_bot_trend.py` - TREND 전략 봇
- `signal_bot_reversion.py` - REVERSION 전략 봇
- `signal_bot_breakout.py` - BREAKOUT 전략 봇

### 왜 백업?
리팩토링 완료 후, 4개 파일이 모두 동일한 구조가 되었습니다.
유일한 차이점은 logger 메시지뿐이었습니다.

### 결과:
- **main.py** 하나로 통합
- Config 파일로 전략 선택
- 코드 중복 제거 완료

### 사용하지 마세요!
이 파일들은 기념용입니다. 실제 운영에는 `main.py`를 사용하세요.
