# Phase 6: signals/ 모듈 분리

**날짜:** 2025-10-19  
**상태:** 진행 예정

---

## 📋 목표

Signal Bot에서 **신호 생성/처리 로직**을 `signals/` 모듈로 분리

---

## 🔍 현재 상태 (AS-IS)

### telegram_signal_bot.py (및 signal_bot_xxx.py)

```python
def on_message(ws, message):  # ❌ WebSocket 콜백 + 신호 처리 혼재
    # 1. WebSocket 수신
    # 2. Buffer 관리
    # 3. 지표 계산 (add_indicators)
    # 4. 전략 호출 (signal_logic)  ✅ strategies/로 이동 완료
    # 5. MTF 확인 (mtf_confirm)
    # 6. 쿨다운 체크 (should_alert)
    # 7. 포지션 계산
    # 8. DB 저장 (save_signal_to_db)
    # 9. 텔레그램 알림
```

### 문제점
- ❌ Signal 로직이 Signal Bot 파일에 혼재
- ❌ `on_message()` 함수가 너무 많은 역할 수행
- ❌ 재사용 불가능한 구조

---

## ✅ 목표 구조 (TO-BE)

### signals/ 모듈

```python
signals/
├── __init__.py
├── signal_generator.py      # 신호 생성 메인 로직
│   ├── SignalGenerator 클래스
│   ├── process_candle()     # 캔들 처리 (on_message 로직 이동)
│   ├── generate_signal()    # 신호 생성 (전략 호출)
│   └── validate_signal()    # 신호 검증 (MTF, 쿨다운)
└── signal_storage.py        # DB 저장
    └── save_signal()        # 신호 DB 저장
```

### Signal Bot 파일 (얇아짐)

```python
# telegram_signal_bot.py
from signals import SignalGenerator

signal_gen = SignalGenerator(config, strategies)

def on_message(ws, message):  # ✅ WebSocket 콜백만
    data = parse_websocket_message(message)
    signal_gen.process_candle(data)  # Signal Generator로 전달
```

---

## 🏗️ 함수명 표준화

### 상용 프로그램 표준 함수명

| 역할 | ❌ 현재 | ✅ 변경 후 | 이유 |
|------|---------|-----------|------|
| 캔들 처리 | `on_message()` | `process_candle()` | WebSocket 콜백 아님 |
| 신호 생성 | `signal_logic()` | `generate_signal()` | 명확한 의도 표현 |
| 신호 검증 | (분산됨) | `validate_signal()` | 검증 로직 통합 |
| DB 저장 | `save_signal_to_db()` | `save_signal()` | 간결함 |

### 참고: 상용 프로그램 사례

```python
# Freqtrade (오픈소스 트레이딩 봇)
class IStrategy:
    def populate_indicators(df)  # 지표 계산
    def populate_entry_trend(df) # 진입 신호
    def populate_exit_trend(df)  # 청산 신호

# Intelligent Trading Bot
class SignalGenerator:
    def generate()               # 신호 생성
    def merge_signals()          # 신호 통합
```

---

## 📊 변경 사항

### 1. signals/signal_generator.py 생성

```python
class SignalGenerator:
    def __init__(self, config, strategies):
        self.config = config
        self.strategies = strategies
        self.buffers = {}  # 캔들 버퍼
        self.last_alert_ts = {}  # 쿨다운
        self.last_regime = {}  # 레짐
    
    def process_candle(self, candle_data):
        """캔들 처리 (기존 on_message 로직)"""
        # 1. Buffer 업데이트
        # 2. DataFrame 생성
        # 3. generate_signal() 호출
    
    def generate_signal(self, df):
        """신호 생성 (전략 호출)"""
        # 1. 지표 계산
        # 2. 전략 호출 (strategies/)
        # 3. 신호 반환
    
    def validate_signal(self, signal):
        """신호 검증"""
        # 1. MTF 확인
        # 2. 쿨다운 체크
        # 3. 거래량 필터
```

### 2. signals/signal_storage.py 생성

```python
def save_signal(signal, config):
    """신호 DB 저장"""
    # common.database.save_signal_to_db() 호출
```

### 3. Signal Bot 파일 수정

```python
# telegram_signal_bot.py
from signals import SignalGenerator

# 초기화
signal_gen = SignalGenerator(CFG, strategies)

def on_message(ws, message):
    """WebSocket 콜백"""
    data = json.loads(message)
    signal_gen.process_candle(data)  # Signal Generator로 전달
```

---

## 🎯 성과 예상

- ✅ **재사용성**: Signal Generator를 다른 프로젝트에서 사용 가능
- ✅ **테스트 용이**: Signal 로직 독립 테스트
- ✅ **코드 절감**: Signal Bot 4개 파일에서 ~200줄 제거
- ✅ **명확성**: 함수명이 역할을 명확히 표현

---

## 📝 작업 순서

1. `signals/` 디렉토리 생성
2. `signals/signal_generator.py` 작성
3. `signals/signal_storage.py` 작성
4. Signal Bot 파일들 수정 (import)
5. 테스트
6. 문서 업데이트

---

**다음 단계: collector/ 모듈 분리**
