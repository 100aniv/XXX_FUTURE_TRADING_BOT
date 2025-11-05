# 통합 테스트 발견 사항 (Integration Test Findings)

**작성일**: 2025-10-30  
**목적**: 전체 플로우 테스트를 통한 문제점 발견 및 개선 방안

---

## 🎯 테스트 목표

**데이터 수집 → 신호 생성 → 리스크 체크 → 포지션 사이징 → 포트폴리오 체크**  
전체 플로우를 순차적으로 테스트하여 각 단계별 문제점 발견

---

## ❌ 발견된 문제점

### 문제 #1: 인디케이터 계산 책임 불명확

**증상**:
```python
KeyError: 'ema_fast'
```

**원인**:
- `signal_logic()`가 인디케이터가 계산된 DataFrame을 기대
- 하지만 원시 데이터만 전달됨 (open, high, low, close, volume)

**현재 구조의 문제점**:
```
데이터 수집 (collectors/rest_collector.py)
    ↓
    원시 데이터 [time, open, high, low, close, volume]
    ↓
전략 로직 (strategies/scalping.py)
    ↓
    ❌ 인디케이터 없음! (ema_fast, ema_mid, ema_slow 등)
```

**누가 인디케이터를 계산해야 하나?**
- ❓ Option 1: 전략 내부에서 계산? → 전략마다 중복 코드
- ❓ Option 2: 엔진에서 계산? → 엔진이 전략별 인디케이터를 알아야 함
- ✅ Option 3: 신호 생성기 계층 추가 → 책임 분리

---

## ✅ 제안: 3계층 아키텍처

### 현재 (2계층)
```
[데이터] → [전략]
```

### 개선 (3계층)
```
[데이터] → [신호 생성기] → [전략]
          (인디케이터 계산)  (신호 로직)
```

### 상세 설계

#### 1. SignalGenerator (새로운 계층)
```python
class SignalGenerator:
    """신호 생성기 - 인디케이터 계산 + 전략 로직 호출"""
    
    def __init__(self, strategy_name: str, config: dict):
        self.strategy = load_strategy(strategy_name)
        self.config = config
    
    def generate(self, raw_df: pd.DataFrame) -> dict:
        """원시 데이터 → 인디케이터 계산 → 신호 생성"""
        # 1. 인디케이터 계산
        df = self._calculate_indicators(raw_df)
        
        # 2. 전략 로직 호출
        signal = self.strategy.signal_logic(df, self.config)
        
        return signal
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """전략별 필수 인디케이터 계산"""
        # EMA
        df['ema_fast'] = ema(df['close'], 9)
        df['ema_mid'] = ema(df['close'], 21)
        df['ema_slow'] = ema(df['close'], 50)
        
        # BB
        df['bb_upper'], df['bb_mid'], df['bb_lower'] = bollinger_bands(df['close'])
        
        # ... 기타 인디케이터
        
        return df
```

#### 2. Strategy (기존)
```python
def signal_logic(df: pd.DataFrame, config: dict) -> dict:
    """인디케이터가 계산된 DataFrame을 받아 신호 생성"""
    # df는 이미 ema_fast, ema_mid, bb_upper 등을 포함
    last = df.iloc[-1]
    
    if last['close'] < last['bb_lower']:
        return {
            'direction': 'long',
            'entry': last['close'],
            # ...
        }
```

#### 3. Engine (기존)
```python
class TradingEngine:
    def __init__(self, strategy_name: str):
        self.signal_generator = SignalGenerator(strategy_name, config)
    
    def on_candle(self, candles: list):
        df = pd.DataFrame(candles)
        
        # 신호 생성기가 인디케이터 계산 + 신호 생성
        signal = self.signal_generator.generate(df)
        
        if signal:
            # 리스크 체크, 포지션 사이징 등
            pass
```

---

## 📊 장단점 분석

### 현재 구조 (2계층)
**장점**:
- 간단함

**단점**:
- ❌ 인디케이터 계산 책임이 불명확
- ❌ 전략마다 인디케이터 계산 코드 중복
- ❌ 테스트 어려움 (인디케이터 없이 전략 테스트 불가)

### 제안 구조 (3계층)
**장점**:
- ✅ 책임 분리 (인디케이터 vs 신호 로직)
- ✅ 재사용성 (인디케이터 계산 공통화)
- ✅ 테스트 용이 (각 계층 독립 테스트)
- ✅ 유지보수 (인디케이터 추가/수정 한 곳)

**단점**:
- 계층 추가 (복잡도 약간 증가)

---

## 🎯 다음 단계

### 1단계: SignalGenerator 구현
- [ ] `signals/signal_generator.py` 생성
- [ ] 인디케이터 계산 로직 이동
- [ ] 전략별 필수 인디케이터 정의

### 2단계: 기존 코드 리팩토링
- [ ] `engine.py` 수정 (SignalGenerator 사용)
- [ ] `strategies/*.py` 수정 (인디케이터 계산 제거)
- [ ] 테스트 코드 수정

### 3단계: 검증
- [ ] 통합 테스트 통과 확인
- [ ] 백테스트 정상 동작 확인
- [ ] 페이퍼 모드 정상 동작 확인

---

## 📝 테스트 실행 로그

```
2025-10-30 12:20:49,076 [INFO] 🚀 전체 플로우 통합 테스트 시작
2025-10-30 12:20:49,778 [INFO] ✅ 1단계 완료: 데이터 수집 성공
2025-10-30 12:20:49,786 [ERROR] ❌ 신호 생성 에러: 'ema_fast'
2025-10-30 12:20:49,789 [INFO] 📊 테스트 결과 요약
2025-10-30 12:20:49,789 [INFO] data_collection     : ✅ 성공
2025-10-30 12:20:49,789 [INFO] signal_generation   : ❌ 실패
2025-10-30 12:20:49,789 [INFO] risk_check          : ❌ 실패
2025-10-30 12:20:49,789 [INFO] position_sizing     : ❌ 실패
2025-10-30 12:20:49,789 [INFO] portfolio_check     : ❌ 실패
```

---

## 🔄 업데이트 기록

- **2025-10-30**: 초안 작성, 문제 #1 발견 (인디케이터 계산 책임 불명확)
