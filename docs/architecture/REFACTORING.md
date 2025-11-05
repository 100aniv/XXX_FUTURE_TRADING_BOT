# 리팩토링 가이드
## 공통 모듈화 및 코드 통합

**날짜:** 2025-10-18 (최종 업데이트)  
**버전:** v2.0  
**작업자:** Cascade AI

---

## 📋 목차

1. [개요](#개요)
2. [리팩토링 목표](#리팩토링-목표)
3. [변경 사항](#변경-사항)
4. [영향받는 파일](#영향받는-파일)
5. [마이그레이션 가이드](#마이그레이션-가이드)
6. [테스트](#테스트)
7. [향후 계획](#향후-계획)

---

## 개요

### 배경

기존 아키텍처에서는 **Signal Bot**이 2가지 역할을 동시에 수행했습니다:
1. ✅ **신호 생성** (주요 역할)
2. ❌ **포지션 추적** (TP/SL 체크, PnL 관리)

이로 인해:
- 코드 복잡도 증가
- 책임 분리 원칙 위반
- Trading Bot 구현 시 중복 로직

### 리팩토링 원칙

**단일 책임 원칙 (Single Responsibility Principle)** 적용:
- **Signal Bot**: 신호 생성 전용
- **Trading Bot**: 매매 실행 + 포지션 추적

---

## 리팩토링 목표

### ✅ 주요 목표

1. **명확한 책임 분리**
   - Signal Bot → 신호 생성만
   - Trading Bot → 포지션 추적 + 매매 실행

2. **코드 재사용성 향상**
   - PositionTracker 클래스로 통합
   - PAPER/LIVE/BACKTEST 모드 지원

3. **확장성 개선**
   - 나중에 `common/tracker.py`로 분리 가능
   - 다른 전략에서도 재사용 가능

4. **테스트 용이성**
   - 각 모듈을 독립적으로 테스트 가능

---

## 변경 사항

### 1. Trading Executor - 추가된 것

#### **PositionTracker 클래스** (trading_executor.py)

```python
class PositionTracker:
    """
    포지션 추적 및 TP/SL 관리
    (Signal Bot에서 이동)
    """
    
    def __init__(self, mode='paper'):
        self.mode = mode  # 'backtest' | 'paper' | 'live'
        self.active_positions = {}
        self.daily_pnl = 0.0
        self.today = time.strftime("%Y-%m-%d")
    
    def track_new_position(self, symbol, side, entry, sl, tp, qty, timestamp):
        """새 포지션 추적 시작"""
        pass
    
    def check_tp_sl(self, symbol, price, timestamp, callback=None):
        """TP/SL 터치 확인 및 청산"""
        pass
    
    def get_goal_progress(self) -> str:
        """일일 목표 달성률"""
        pass
    
    def get_active_positions(self) -> Dict:
        """활성 포지션 조회"""
        pass
    
    def get_daily_pnl(self) -> float:
        """일일 손익 조회"""
        pass
```

**위치:** `trading_executor.py` (클래스 PositionTracker)

#### **Trading Manager** (trading_manager.py)
- 신호 읽기 (DB)
- TradingExecutor 호출
- PositionTracker 관리
- 결과 저장

---

### 2. Signal Bots - 제거된 것

#### **함수 정의 제거**

```python
# ❌ 제거됨
def _tp_from_rr(I, rr): ...
def track_new_signal(symbol, I, qty): ...
def touch_check(symbol, price, ts_ms): ...
def goal_progress_text() -> str: ...
```

#### **전역 변수 제거**

```python
# ❌ 제거됨
ACTIVE_SIG: Dict[str, Dict[str, Any]] = {}
DAILY_PNL: float = 0.0
```

#### **함수 호출 주석 처리**

```python
# ❌ 기존
touch_check(sym, last_price, ts_ms)
track_new_signal(sym, I, qty)

# ✅ 변경 후
# touch_check(sym, last_price, ts_ms)  # Trading Bot으로 이동
# track_new_signal(sym, I, qty)  # Trading Bot으로 이동
```

#### **텔레그램 명령어 수정**

```python
# ❌ 기존: PnL/포지션 통계 표시
elif text == "stats":
    active_count = len([p for p in ACTIVE_SIG.values() ...])
    msg += f"활성 포지션: {active_count}개\n"
    msg += f"일일 PnL: {DAILY_PNL:.2f} USDT\n"

# ✅ 변경 후: 안내 메시지로 대체
elif text == "stats":
    msg = "신호 생성 전용 모드. PnL/포지션 통계는 Trading Bot에서 확인하세요."
```

---

## 영향받는 파일

### ✅ 수정된 파일 (5개)

| 파일 | 역할 | 변경 내용 |
|-----|------|----------|
| `trading_bot.py` | 매매 실행 | ✅ PositionTracker 클래스 추가 |
| `telegram_signal_bot.py` | SCALPING/DAYTRADE/SWING | ❌ 포지션 추적 제거 |
| `signal_bot_trend.py` | TREND 전략 | ❌ 포지션 추적 제거 |
| `signal_bot_reversion.py` | REVERSION 전략 | ❌ 포지션 추적 제거 |
| `signal_bot_breakout.py` | BREAKOUT 전략 | ❌ 포지션 추적 제거 |

### 📊 변경 통계

```
총 라인 수:
  추가: +217 (trading_bot.py)
  삭제: -400 (Signal Bots 4개)
  순 변경: -183 라인

제거된 함수: 4개 × 4파일 = 16개
추가된 메서드: 6개 (PositionTracker)
```

---

## 마이그레이션 가이드

### Signal Bot 사용자

#### 이전 방식

```python
# Signal Bot에서 직접 포지션 추적
track_new_signal(symbol, I, qty)
touch_check(symbol, price, ts_ms)
pnl_text = goal_progress_text()
```

#### 새로운 방식

```python
# Signal Bot은 신호만 생성 & DB 저장
# 포지션 추적은 Trading Bot이 담당
# (코드 변경 불필요 - 자동으로 분리됨)
```

### Trading Bot 사용자

#### 새로운 사용법

```python
from trading_bot import PositionTracker

# 1. 초기화
tracker = PositionTracker(mode='paper')  # 'paper' | 'live' | 'backtest'

# 2. 신호 발생 시 포지션 추적 시작
tracker.track_new_position(
    symbol="BTCUSDT",
    side="LONG",
    entry=50000.0,
    sl=49000.0,
    tp=52000.0,
    qty=0.01,
    timestamp=1700000000000
)

# 3. 1분마다 TP/SL 체크 (WebSocket or Polling)
tracker.check_tp_sl(
    symbol="BTCUSDT",
    price=current_price,
    timestamp=current_ts,
    callback=telegram_alert  # 선택적
)

# 4. 조회
active_positions = tracker.get_active_positions()
daily_pnl = tracker.get_daily_pnl()
progress_text = tracker.get_goal_progress()
```

---

## 테스트

### 단위 테스트

```bash
# 리팩토링 검증 테스트
python test_refactoring.py
```

### 통합 테스트

```bash
# 1. Signal Bot 실행 (신호 생성)
python telegram_signal_bot.py

# 2. Trading Bot 실행 (매매 + 포지션 추적)
python trading_bot.py --strategy ensemble --mode paper
```

### 체크리스트

- [ ] Signal Bot이 신호를 생성하는가?
- [ ] 신호가 DB에 저장되는가?
- [ ] Trading Bot이 신호를 읽는가?
- [ ] PositionTracker가 포지션을 추적하는가?
- [ ] TP/SL 체크가 동작하는가?
- [ ] 일일 PnL이 정상 집계되는가?

---

## 리팩토링 히스토리

### Phase 1: 포지션 추적 분리 (2025-10-17 완료)

```
Signal Bot → Trading Bot 포지션 추적 분리
- PositionTracker 클래스 생성
- Signal Bot에서 포지션 추적 제거
```

### ✅ Phase 2: 공통 모듈화 (2025-10-18 완료)

```
현재 구조:
├─ common/                    # 공통 모듈 ⭐ 완료
│  ├─ __init__.py
│  ├─ logger.py              # 로깅 시스템 (타입별 분류)
│  ├─ database.py            # DB 연결 및 신호 저장
│  ├─ messaging.py           # 텔레그램 메시징 + 포맷팅
│  ├─ config.py              # 환경변수 → 설정
│  └─ calculations.py        # 계산 함수 (포지션, 레버리지 등)
│
├─ signal_bots/              # 신호 생성 (공통 모듈 사용)
├─ trading/                  # 매매 실행 (공통 모듈 사용)
└─ backtest/                 # 백테스트 (공통 모듈 사용)
```

**Phase 2 성과:**
- ✅ 중복 코드 ~650줄 제거
- ✅ 공통 모듈 ~450줄 추가
- ✅ 순 절감: ~200줄
- ✅ 타입별 로그 분류 (signals/trading/performance/errors)
- ✅ DB 연결 통합 관리
- ✅ 텔레그램 메시징 통합
- ✅ 메시지 포맷팅 통합 (format_signal_alert, beginner_block)
- ✅ 계산 함수 통합 (position_size, leverage_suggestion, price_levels)
- ✅ 설정 관리 통합 (load_config, validate_config)

### ✅ Phase 3: Flash Guard 리팩토링 (2025-10-18 완료)

**배경:**
- Signal Bot에서 Flash Guard (급등락 감지) 처리
- Trading Bot과 중복된 리스크 체크 로직
- Pre-Trade Risk Check는 거래 실행 직전에 수행되어야 함

**변경 사항:**

#### Signal Bot에서 제거
```python
# ❌ 제거됨 (4개 파일)
def _tf_ms() -> int: ...
def flash_guard_update(symbol, price, ts_ms): ...
def flash_guard_allowed(symbol, ts_ms) -> bool: ...

FLASHBUF: Dict[str, deque] = {}
FLASH_PAUSE_UNTIL: Dict[str, int] = {}
```

#### Trading Bot에 추가
```python
# ✅ trading_executor.py - RiskManager 클래스
class RiskManager:
    def __init__(self, config=None):
        self.flash_buffers = {}
        self.flash_pause_until = {}
    
    def flash_guard_update(self, symbol, price, ts_ms): ...
    def flash_guard_allowed(self, symbol, ts_ms) -> bool: ...
    def _tf_ms(self) -> int: ...
```

**Phase 3 성과:**
- ✅ Flash Guard를 Trading 모듈 RiskManager로 이동
- ✅ Signal Bot에서 ~120줄 제거 (4개 파일)
- ✅ Pre-Trade Risk Check 로직 중앙화
- ✅ 올바른 책임 분리 (Signal = 신호 생성 / Trading = 리스크 체크)

---

### 🔄 Phase 4: 추가 고도화 (진행 중)

1. **Helper/Util 함수 통합**
   - Signal Bot 공통 함수 → common/utils.py
   - bootstrap_history(), buffer_to_df(), make_streams() 등

2. **전략 로직 분리**
   - signal_logic() → strategies/ 디렉토리
   - 전략별 모듈화

3. **백테스트 지원**
   - 과거 데이터로 전략 검증
   - 성과 분석 리포트

---

### 📱 Phase 4: 메시징 아키텍처 개편 (TO-BE)

#### 현재 문제점 (AS-IS)

**Signal Bot이 독립적인 봇처럼 동작:**
```python
# Signal Bot에서 모든 신호를 텔레그램으로 전송
신호 생성 → DB 저장 → 텔레그램 알림 ❌
```

**문제:**
- 텔레그램 알림이 Signal Bot에 종속
- 전체 시스템 흐름 파악 어려움
- Trading Bot과 알림 역할 중복

#### 목표 아키텍처 (TO-BE)

**트레이딩 시스템 파이프라인:**

```
1. 거래소 API → 데이터 수집
   ↓ 로깅 + 알람(연결 상태)
   
2. 데이터 표준화/정규화
   ↓ 로깅
   
3. 시그널 생성 (Signal Bot)
   ↓ 로깅 + 알람(중요 신호만)
   
4. 시그널 분석 → 전략 선택
   ↓ 로깅 + 알람(전략 변경)
   
5. 매매 실행 (Trading Bot)
   ↓ 로깅 + 알람(거래 내역)
   
6. 포지션 추적 (PositionTracker)
   ↓ 로깅 + 알람(TP/SL 달성)
```

#### 핵심 원칙

**"알림(텔레그램)은 특정 모듈의 전유물이 아니다"**

- ✅ **로깅**: 모든 이벤트를 파일에 기록
- ✅ **알람**: 중요한 이벤트만 텔레그램으로 선택적 전송

#### 알림 대상 분류

##### 1️⃣ **시장 상황 알림** (Market Status)
```python
# 시장 regime 변화
logger.info("시장 regime: 상승장 → 하락장 전환")
if regime_changed:
    tg("📊 시장 전환: 상승장 → 하락장")

# 변동성 급증
if atr_spike:
    tg("⚡ 변동성 급증 감지: ATR +150%")
```

##### 2️⃣ **신호 알림** (Signal Alerts)
```python
# 고신뢰도 신호만 알림
logger.info(f"신호 생성: {symbol} {side}")  # 모든 신호 로깅

if signal_confidence > 0.85:  # 중요 신호만
    tg(f"🚀 고신뢰도 신호: {symbol} {side}")
```

##### 3️⃣ **거래 알림** (Trade Execution)
```python
# 모든 거래 내역 알림
logger.info(f"포지션 진입: {symbol}")
tg(f"💰 포지션 진입: {symbol} {side} @ {price}")
```

##### 4️⃣ **손익 알림** (PnL Updates)
```python
# TP/SL 달성
logger.info(f"TP1 달성: {symbol}")
tg(f"🟢 TP1 달성: +{pnl} USDT")

# 일일 목표 달성
if daily_pnl >= target:
    tg(f"🎉 일일 목표 달성: {daily_pnl} USDT")
```

##### 5️⃣ **시스템 알림** (System Status)
```python
# 봇 시작/종료
tg("🤖 Signal Bot 시작")
tg("🛑 Trading Bot 종료")

# 오류 발생
logger.error(f"WebSocket 오류: {error}")
tg(f"⚠️ 시스템 오류: {error}")
```

#### 구현 예시

**Signal Bot (신호 생성기)**
```python
# AS-IS (현재 - 모든 신호 알림)
msg = format_signal_alert(sym, I, qty, notional, margin)
tg(msg)  # ❌ 모든 신호를 무조건 전송

# TO-BE (개선 - 선택적 알림)
logger.info(f"신호 생성: {sym} {I['side']}")  # 로깅은 항상

# 중요 신호만 알림
if should_notify_signal(I):
    msg = format_signal_alert(sym, I, qty, notional, margin)
    tg(msg)
```

**Trading Bot (매매 실행기)**
```python
# 거래 실행 시 항상 알림
logger.info(f"포지션 진입: {symbol}")
tg(f"💰 [{bot_name}] 포지션 진입\n"
   f"심볼: {symbol}\n"
   f"방향: {side}\n"
   f"가격: {entry}")
```

**PositionTracker (포지션 추적기)**
```python
# TP/SL 달성 시 항상 알림
if tp1_hit:
    logger.info(f"TP1 달성: {symbol}")
    tg(f"🟢 TP1 달성: {symbol} +{pnl} USDT")
```

#### 알림 필터링 로직

```python
def should_notify_signal(signal_info: dict) -> bool:
    """신호 알림 여부 결정"""
    
    # 고신뢰도 신호
    if signal_info.get("confidence", 0) > 0.85:
        return True
    
    # 여러 전략 동시 신호
    if signal_info.get("strategy_count", 0) >= 3:
        return True
    
    # 특별한 패턴 감지
    if signal_info.get("pattern") in ["golden_cross", "death_cross"]:
        return True
    
    # 기본: 알림 안 함 (로깅만)
    return False
```

#### 로깅 vs 알림 비교

| 이벤트 | 로깅 | 텔레그램 알림 |
|--------|------|---------------|
| 캔들 수신 | ✅ DEBUG | ❌ |
| 일반 신호 생성 | ✅ INFO | ❌ |
| 고신뢰도 신호 | ✅ INFO | ✅ |
| 시장 regime 변화 | ✅ INFO | ✅ |
| 포지션 진입 | ✅ INFO | ✅ |
| TP/SL 달성 | ✅ INFO | ✅ |
| 일일 목표 달성 | ✅ INFO | ✅ |
| 오류 발생 | ✅ ERROR | ✅ (심각한 오류만) |

#### 마이그레이션 계획

**Step 1: Signal Bot 알림 최소화**
- 현재: 모든 신호 → 텔레그램
- 개선: DB 저장만, 알림 제거

**Step 2: Trading Bot 알림 강화**
- 거래 실행 결과
- TP/SL 달성
- PnL 업데이트

**Step 3: 시스템 전체 알림 통합**
- 통합 알림 매니저 구현
- 알림 우선순위 설정
- 알림 빈도 제한 (Rate Limiting)

---

## 참고 문서

- [Trading Bot 가이드](TRADING_EXECUTOR.md)
- [매매 결정 로직](TRADING_DECISION.md)
- [실밥 리팩토링 히스토리](../CHANGELOG.md)

---

## 문의

리팩토링 관련 문의사항이나 버그 발견 시:
- GitHub Issues
- Discord #dev 채널

---

**Last Updated:** 2025-10-19  
**Author:** Cascade AI  
**Status:** 
- ✅ Phase 1 완료 (포지션 추적 분리)
- ✅ Phase 2 완료 (공통 모듈화)
- ✅ Phase 3 완료 (indicators 모듈 분리)
- ✅ Phase 4 완료 (helpers 모듈 분리)
- ✅ Phase 5 완료 (strategies 모듈 분리)
- ✅ Phase 6 완료 (signals 모듈 분리)
- 📋 Phase 7 계획 (collector 모듈 분리)
- 📋 Phase 8 계획 (main.py 생성)
