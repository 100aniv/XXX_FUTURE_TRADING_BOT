# 🔔 Signals 모듈

**신호 생성 프레임워크** - 전략 실행 및 신호 관리

**경로**: `signals/`

---

## 개요

Signals 모듈은 전략을 실행하고 신호를 생성/검증/저장하는 프레임워크입니다.

### 구조
```
signals/
├── signal_generator.py    # SignalGenerator 클래스
└── signal_storage.py      # DB 저장 함수
```

---

## SignalGenerator

**신호 생성 엔진**

### 초기화
```python
from signals import SignalGenerator
from common.config import load_config

config = load_config()
generator = SignalGenerator(config)
```

### 캔들 처리
```python
signal = generator.process_candle(
    symbol="BTCUSDT",
    candle=candle_data,
    tg_callback=telegram_function
)

# signal = {
#     "side": "LONG",
#     "entry": 34250.0,
#     "sl": 34000.0,
#     "tp": 34750.0,
#     "lev": 5,
#     "atr": 125.5,
#     "confidence": 0.8,
#     "reason": ["EMA 정렬", "MACD 골든크로스"],
#     "strategy_id": "trend",
#     "ts": 1698264600000
# }
```

### 신호 검증
SignalGenerator는 자동으로 다음을 검증합니다:
- ✅ 거래량 스파이크 필터
- ✅ 멀티 타임프레임 확인
- ✅ 쿨다운 체크 (중복 신호 방지)
- ✅ 레짐 확인

---

## signal_storage

**신호 DB 저장**

### save_signal()
```python
from signals.signal_storage import save_signal

success = save_signal(
    symbol="BTCUSDT",
    signal=signal_dict,
    config=config
)
```

**저장 위치**: `monitoring.signals` 테이블

---

## 사용 예시 (main.py)

```python
from signals import SignalGenerator
from signals.signal_storage import save_signal

# 초기화
generator = SignalGenerator(config)

# 캔들 처리
def on_candle_closed(symbol, candle, is_closed, timeframe):
    if is_closed:
        signal = generator.process_candle(symbol, candle)
        if signal:
            save_signal(symbol, signal, config)
            print(f"✅ {signal['side']} 신호 생성!")
```

---

**최종 업데이트**: 2025-10-19
