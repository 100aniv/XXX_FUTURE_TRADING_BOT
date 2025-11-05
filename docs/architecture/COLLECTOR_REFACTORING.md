# Phase 7: collector/ 모듈 분리

**날짜:** 2025-10-19  
**상태:** 진행 중

---

## 📋 목표

Signal Bot에서 **데이터 수집 로직**을 collector/ 모듈로 분리

---

## 🔍 현재 상태 (AS-IS)

### Signal Bot 파일 (4개)

```python
telegram_signal_bot.py
signal_bot_trend.py
signal_bot_reversion.py
signal_bot_breakout.py

# 각 파일에 포함된 것:
├── WebSocket 연결 (on_open, on_error, on_close, on_message)
├── 초기 히스토리 로드 (bootstrap_history)
├── Stream URL 생성 (make_streams)
└── 신호 생성 (SignalGenerator 사용)
```

### 문제점
- ❌ WebSocket 로직이 4개 파일에 중복
- ❌ Collector와 Signal 로직 혼재
- ❌ 재사용 불가능한 구조

---

## ✅ 목표 구조 (TO-BE)

### collector/ 모듈

```python
collector/
├── __init__.py
├── websocket_collector.py    # WebSocket 수집
│   ├── WebSocketCollector 클래스
│   ├── connect()
│   ├── on_message()
│   ├── on_error()
│   └── on_close()
└── rest_collector.py          # REST API 수집
    └── fetch_history()
```

### Signal Bot 파일 (얇아짐)

```python
# telegram_signal_bot.py (예시)
from collector import WebSocketCollector
from signals import SignalGenerator

# 초기화
collector = WebSocketCollector(symbols, timeframe)
signal_gen = SignalGenerator(config)

# 콜백 연결
collector.on_candle_closed(signal_gen.process_candle)

# 실행
collector.start()
```

---

## 📊 분리 대상

### 1. WebSocket 로직
```python
# 이동: signal_bot → collector/websocket_collector.py
- def on_open(ws)
- def on_error(ws, error)
- def on_close(ws, a, b)
- def on_message(ws, message)  # 일부만
- def start_ws()
- WebSocketApp 생성
```

### 2. 초기 히스토리
```python
# 이미 common/utils.py에 있음
- bootstrap_history()  # ✅ 완료
- make_streams()       # ✅ 완료
```

### 3. 신호 생성 로직
```python
# 이미 signals/에 있음
- SignalGenerator.process_candle()  # ✅ 완료
```

---

## 🏗️ WebSocketCollector 설계

### 클래스 구조

```python
class WebSocketCollector:
    """WebSocket 데이터 수집"""
    
    def __init__(self, symbols, timeframe, callback=None):
        self.symbols = symbols
        self.timeframe = timeframe
        self.callback = callback  # 캔들 닫힐 때 호출
        self.ws = None
    
    def connect(self):
        """WebSocket 연결"""
        streams = make_streams(self.symbols, self.timeframe)
        self.ws = WebSocketApp(
            streams,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
    
    def start(self):
        """수집 시작"""
        self.connect()
        self.ws.run_forever()
    
    def on_candle_closed(self, callback):
        """캔들 닫힐 때 호출할 콜백 등록"""
        self.callback = callback
    
    def _on_message(self, ws, message):
        """WebSocket 메시지 수신"""
        data = json.loads(message)
        # 캔들 파싱
        candle = self._parse_candle(data)
        
        if candle['is_closed'] and self.callback:
            # 콜백 호출 (Signal Generator로 전달)
            self.callback(candle['symbol'], candle)
```

---

## 🎯 성과 예상

- ✅ **코드 절감**: Signal Bot 4개 파일에서 ~150줄 제거
- ✅ **재사용성**: Collector를 다른 프로젝트에서 사용 가능
- ✅ **테스트 용이**: Collector 독립 테스트
- ✅ **명확성**: 책임 분리 (Collector = 수집 / Signal = 생성)

---

## 📝 작업 순서

1. collector/ 디렉토리 생성
2. websocket_collector.py 작성
3. rest_collector.py 작성
4. Signal Bot 파일 수정 (import)
5. 테스트
6. 문서 업데이트

---

**다음 단계: Phase 8 - main.py 생성**
