# 🚀 최종 개선 계획 (GPT + Cascade 통합)

**날짜:** 2025-10-21  
**상태:** ✅ Phase 1 완료 (설정 중복 제거 + 멀티 심볼)

---

## ✅ **발견된 문제점 → 해결 완료**

### **1. 설정 중복 (하드코딩)** ✅ 해결됨

#### **execution/position_sizer.py (31-40줄)**
```python
# ❌ 6개 설정 중복
self.equity = float(os.getenv('EQUITY_USDT', '10000'))
self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.01'))
self.quality_weight_min = float(os.getenv('QUALITY_WEIGHT_MIN', '0.7'))
self.quality_weight_max = float(os.getenv('QUALITY_WEIGHT_MAX', '1.3'))
self.max_position_value = float(os.getenv('MAX_POSITION_VALUE', '5000'))
self.min_position_value = float(os.getenv('MIN_POSITION_VALUE', '10'))
```

#### **execution/risk_manager.py (36-41줄)**
```python
# ❌ 4개 설정 중복
self.daily_loss_limit_pct = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '0.03'))
self.daily_loss_limit = self.daily_loss_limit_pct * float(os.getenv('EQUITY_USDT', '10000'))
self.max_positions = int(os.getenv('MAX_CONCURRENT_POSITIONS', '5'))
self.max_exposure_per_symbol_pct = float(os.getenv('MAX_EXPOSURE_PER_SYMBOL_PCT', '0.3'))
```

#### **strategies/ensemble.py (28-67줄)**
```python
# ❌ 20+ 설정 중복 (전체 CFG 딕셔너리)
CFG = {
    "weight_trend": float(os.getenv("WEIGHT_TREND", "2.5")),
    "weight_reversion": float(os.getenv("WEIGHT_REVERSION", "2.0")),
    "alpha_winrate": float(os.getenv("ALPHA_WINRATE", "0.4")),
    # ... 20개 이상
}
```

#### **signals/signal_generator.py (57-66줄)**
```python
# ⚠️ config 읽지만 하드코딩된 기본값
self.EMA_FAST = config.get("ema_fast", 8)   # ← 하드코딩 8
self.EMA_MID = config.get("ema_mid", 21)    # ← 하드코딩 21
self.RSI_LEN = config.get("rsi_len", 14)    # ← 하드코딩 14
```

**문제:** config.yml로 통합했는데 코드에서 여전히 env 직접 읽음!
**총 중복:** 30+ 설정값

### **2. 단일 심볼 강제** ❌

```python
# main.py (42번 줄)
symbol = CFG.get('symbols', ['BTCUSDT'])[0]  # ❌ [0]으로 첫 번째만!
```

**문제:** 사용자 요구사항 = 바이낸스 선물 전체 심볼 (100+개) 실시간 거래!

**목표:**
```python
# 현재 (단일)
symbol = 'BTCUSDT'  # ❌ 1개만

# 목표 (멀티 - 전체)
symbols = get_all_binance_futures()  
# → ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', ...] (100+개)

# 모드 선택
if CFG['symbols']['mode'] == 'all':
    symbols = get_all_binance_futures()  # 전체
elif CFG['symbols']['mode'] == 'top50':
    symbols = get_top_n_futures(50)      # 상위 50개
else:
    symbols = CFG['symbols']['list']      # 수동 지정
```

### **3. 포트폴리오 관리 부재** ❌

- 심볼별/전략별 포지션 추적 없음
- 노출/슬롯 제어 없음
- 충돌 방지 없음

---

## 💡 **의견 통합**

### **GPT 의견**
```
✅ 동의:
- 포트폴리오 매니저 "라이트" 필수
- config.yml 통합
- 정책 2가지: ensemble | parallel

❌ 나중에:
- Allocator (복잡해지면)
- Orchestrators (여러 정책)

🎯 우선순위:
- 실거래 안전장치 (일손실컷/익스포저/슬롯)
- 리포트 강화
- 비동기 I/O
```

### **Cascade 의견 (나)**
```
✅ 완전 동의:
- 포트폴리오 매니저 라이트 (MUST)
- 설정 중복 제거 (단일 소스)
- 멀티 심볼 복원

⚠️ 부분 동의:
- 정책 2개 (ensemble/parallel) - OK
- Allocator 나중에 - 필요하면 추가

🚫 반대:
- 과한 추상화는 안 함 (YAGNI)
- 지금 안 쓰는 레이어 만들지 않음
```

### **최종 합의**
```
🔥 즉시 (1-2시간):
1. 설정 중복 제거 (config 전달)
2. 멀티 심볼 복원

🔥 단기 (1-2일):
3. 포트폴리오 매니저 라이트
4. engine.py 통합

⚠️ 선택 (나중에):
5. 정책 스위치 (ensemble/parallel)
6. Allocator (자본배분)
```

---

## 🎯 **최종 개선 방안 (MVP+)**

### **Phase 1: 설정 통합 + 멀티 심볼** 🔥

#### **작업 시간:** 1-2시간

#### **A. 설정 중복 제거**

**Before:**
```python
# execution/position_sizer.py
class PositionSizer:
    def __init__(self):
        self.equity = float(os.getenv('EQUITY_USDT', '10000'))  # ❌
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.01'))  # ❌
```

**After:**
```python
# execution/position_sizer.py
class PositionSizer:
    def __init__(self, config):
        self.equity = config['capital']['initial']  # ✅ config.yml
        self.risk_per_trade = config['risk']['per_trade']  # ✅ config.yml
```

**수정 파일:**
- `execution/position_sizer.py`
- `execution/risk_manager.py`
- `execution/position_tracker.py`
- `execution/engine.py` (초기화 부분)

#### **B. 멀티 심볼 복원**

**Before:**
```python
# main.py
symbol = CFG.get('symbols', ['BTCUSDT'])[0]  # ❌ 단일

config = {
    'symbol': symbol,  # ❌ 단일
    'timeframe': timeframe,
    'lookback': 400
}

engine.run(feed, broker, clock, strategies, ensemble, config)
```

**After:**
```python
# main.py
symbols = CFG['symbols']['list']  # ✅ ['BTCUSDT', 'ETHUSDT']

config = {
    'symbols': symbols,  # ✅ 멀티
    'timeframe': timeframe,
    'lookback': 400,
    'capital': CFG['capital'],
    'risk': CFG['risk'],
    'strategy': CFG['strategy']
}

engine.run(feed, broker, clock, strategies, ensemble, config)
```

**수정 파일:**
- `main.py`
- `execution/engine.py` (심볼 루프 추가)

---

### **Phase 2: 포트폴리오 매니저 라이트** 🔥

#### **작업 시간:** 1-2일

#### **기능 (최소한만)**

```python
# execution/portfolio_manager.py (NEW)
class PortfolioManager:
    """
    멀티 심볼/전략 포지션 관리 (라이트 버전)
    
    핵심 기능:
    1. 일일 손실 컷 (3% 초과 시 당일 거래 중단)
    2. 노출 제어 (심볼별 30%, 전체 80%)
    3. 슬롯 관리 (최대 5개 포지션)
    4. 충돌 방지 (같은 심볼 반대 방향 불가)
    5. PnL 추적 (실현/미실현)
    """
    
    def __init__(self, capital: float, config: dict):
        """
        Args:
            capital: 초기 자본
            config: config.yml의 risk 섹션
        """
        self.capital = capital
        self.config = config
        
        # 포지션 추적
        self.positions = {}  # {(symbol, strategy): position}
        
        # PnL
        self.daily_pnl = 0.0
        self.daily_loss_limit = capital * config['risk']['daily_loss_limit']
        
        # 노출
        self.total_exposure = 0.0
        self.symbol_exposure = {}  # {symbol: value}
        
        # 슬롯
        self.max_slots = config['risk']['max_positions']
        self.used_slots = 0
    
    def allow(self, symbol: str, strategy: str, side: str, value: float) -> Tuple[bool, str]:
        """
        포지션 진입 허용 여부
        
        Returns:
            (허용 여부, 사유)
        """
        # 1) 일손실 초과
        if self.daily_pnl < -self.daily_loss_limit:
            return False, "일일 손실 한도 초과"
        
        # 2) 슬롯 초과
        if self.used_slots >= self.max_slots:
            return False, "포지션 슬롯 초과"
        
        # 3) 심볼 노출 초과
        max_symbol = self.capital * self.config['risk']['max_exposure_per_symbol']
        current = self.symbol_exposure.get(symbol, 0)
        if current + value > max_symbol:
            return False, f"{symbol} 노출 초과"
        
        # 4) 충돌 체크 (같은 심볼 반대 방향)
        for (s, st), pos in self.positions.items():
            if s == symbol and pos['side'] != side:
                return False, f"{symbol} 반대 방향 포지션 존재"
        
        return True, "OK"
    
    def add(self, symbol: str, strategy: str, position: dict):
        """포지션 추가"""
        key = (symbol, strategy)
        self.positions[key] = position
        
        value = position['qty'] * position['entry']
        self.symbol_exposure[symbol] = self.symbol_exposure.get(symbol, 0) + value
        self.total_exposure += value
        self.used_slots += 1
    
    def remove(self, symbol: str, strategy: str, pnl: float):
        """포지션 제거"""
        key = (symbol, strategy)
        if key not in self.positions:
            return
        
        pos = self.positions[key]
        value = pos['qty'] * pos['entry']
        
        # 노출 감소
        self.symbol_exposure[symbol] -= value
        self.total_exposure -= value
        self.used_slots -= 1
        
        # PnL 업데이트
        self.daily_pnl += pnl
        
        del self.positions[key]
    
    def get_status(self) -> dict:
        """현재 상태"""
        return {
            'total_exposure': self.total_exposure,
            'symbol_exposure': self.symbol_exposure,
            'used_slots': self.used_slots,
            'max_slots': self.max_slots,
            'daily_pnl': self.daily_pnl,
            'positions_count': len(self.positions)
        }
```

#### **engine.py 통합**

```python
# execution/engine.py
def run(feed, broker, clock, strategies, ensemble_module, config):
    # ⭐ 포트폴리오 매니저 초기화
    from execution.portfolio_manager import PortfolioManager
    portfolio = PortfolioManager(
        capital=config['capital']['initial'],
        config=config
    )
    
    # 멀티 심볼 루프
    symbols = config.get('symbols', ['BTCUSDT'])
    
    for candle in feed.stream():
        symbol = candle.get('symbol', symbols[0])
        
        # ... (신호 생성)
        
        # ⭐ 포트폴리오 체크
        if ensemble_module:
            decision = ensemble_module.combine_signals(signals, conn)
            if decision:
                strategy = 'ensemble'
                qty, meta = sizer.calculate(decision, config)
                value = qty * decision['entry']
                
                # ⭐ 포트폴리오 허용 체크
                allowed, reason = portfolio.allow(symbol, strategy, decision['side'], value)
                if allowed:
                    fill = broker.execute(decision, qty)
                    if fill['success']:
                        portfolio.add(symbol, strategy, {
                            'side': decision['side'],
                            'entry': decision['entry'],
                            'qty': qty
                        })
                else:
                    logger.warning(f"⛔ 포트폴리오 거부: {reason}")
```

---

### **Phase 3: 정책 스위치** ⚠️ (선택)

#### **작업 시간:** 1일 (나중에 필요하면)

```yaml
# config.yml
strategy:
  policy: ensemble  # ensemble | parallel
  
  ensemble:
    weights:
      scalping: 1.5
      daytrade: 1.2
  
  parallel:
    allow_conflict: false
    max_per_strategy: 2
```

```python
# engine.py (간단 버전)
policy = config['strategy']['policy']

if policy == 'ensemble':
    # 심볼별 1개 결정
    decision = ensemble.combine_signals(signals, conn)
    decisions = [decision] if decision else []

elif policy == 'parallel':
    # 전략별 독립 거래
    decisions = signals  # 모든 신호 독립 실행

# 공통 실행
for decision in decisions:
    strategy = decision.get('strategy_id', 'ensemble')
    allowed, reason = portfolio.allow(symbol, strategy, decision['side'], value)
    if allowed:
        broker.execute(decision, qty)
```

---

## 📋 **최종 구조 (간소화)**

```
project/
├─ collectors/                 # ✅ 유지 (그대로)
│   websocket_collector.py
│   rest_collector.py
│   historical_collector.py
│
├─ strategies/                 # ✅ 유지 (그대로)
│   trend.py reversion.py breakout.py
│   scalping.py daytrade.py swing.py
│   ensemble.py
│
├─ execution/
│   engine.py                  # ✅ 수정 (멀티 심볼 + 포트폴리오)
│   portfolio_manager.py       # ✅ NEW (라이트)
│   position_sizer.py          # ✅ 수정 (config 전달)
│   risk_manager.py            # ✅ 수정 (config 전달)
│   position_tracker.py        # ✅ 유지
│   adapters/
│       brokers.py             # ✅ 유지
│       clocks.py              # ✅ 유지
│
├─ common/
│   config.py                  # ✅ 유지
│
├─ config.yml                  # ✅ 단일 설정 소스
└─ .env                        # ✅ 비밀만
```

**제거/미룸:**
- ❌ allocator.py (나중에)
- ❌ orchestrators/ (나중에)
- ❌ 복잡한 추상화

---

## ✅ **작업 체크리스트**

### **🔥 Phase 1: 설정 중복 제거** (즉시, 1-2시간)

#### **A. execution 모듈 수정**

- [x] **1.1. position_sizer.py 수정** (`execution/position_sizer.py:29-40`) ✅
  - [x] `__init__(self, config)` 시그니처 변경
  - [x] `os.getenv()` 6개 제거
    - [x] EQUITY_USDT → `config['capital']['initial']`
    - [x] RISK_PER_TRADE → `config['risk']['per_trade']`
    - [x] QUALITY_WEIGHT_MIN → `config['position_sizing']['quality_weight_min']`
    - [x] QUALITY_WEIGHT_MAX → `config['position_sizing']['quality_weight_max']`
    - [x] MAX_POSITION_VALUE → `config['position_sizing']['max_position_value']`
    - [x] MIN_POSITION_VALUE → `config['position_sizing']['min_position_value']`

- [x] **1.2. risk_manager.py 수정** (`execution/risk_manager.py:34-41`) ✅
  - [x] `__init__(self, config)` 시그니처 변경
  - [x] `os.getenv()` 4개 제거
    - [x] DAILY_LOSS_LIMIT_PCT → `config['risk']['daily_loss_limit']`
    - [x] EQUITY_USDT → `config['capital']['initial']`
    - [x] MAX_CONCURRENT_POSITIONS → `config['risk']['max_positions']`
    - [x] MAX_EXPOSURE_PER_SYMBOL_PCT → `config['risk']['max_exposure_per_symbol']`

- [x] **1.3. engine.py 초기화 수정** (`execution/engine.py`) ✅
  - [x] `sizer = PositionSizer(config)` 수정
  - [x] `risk = RiskManager(config)` 수정
  - [x] config 전체 전달 확인

#### **B. strategies 모듈 수정**

- [x] **1.4. ensemble.py 수정** (`strategies/ensemble.py:28-67`) ✅
  - [x] CFG 딕셔너리 제거 (40줄 삭제)
  - [x] `combine_signals(signals, conn, config)` 시그니처 추가
  - [x] config에서 읽기
    - [x] 가중치: `config['strategy']['ensemble']['weights']`
    - [x] 파라미터: `config['strategy']['ensemble']`
  - [x] engine.py 호출 수정

#### **C. config.yml 검증**

- [x] **1.5. config.yml 완성도 체크** ✅
  - [x] position_sizing 섹션 존재 확인 ✅
  - [x] ensemble 섹션 완성 ✅ (파라미터 추가)
  - [x] indicators 섹션 존재 확인 ✅
  - [x] 중복 제거 완료 ✅
    - [x] cooldown_candles 통합
    - [x] strategies 섹션 중복 제거
    - [x] tp_sl 섹션 통합 (trailing 포함)
    - [x] strategy.weights 중복 제거

#### **D. 멀티 심볼 준비**

- [x] **1.6. main.py 수정** ✅
  - [x] `symbols` 멀티 심볼 처리
  - [x] 단일 symbol → symbols 리스트
  - [x] config에 symbols_list 전달
  - [x] broker 생성 시 config.fees 전달 (하드코딩 제거)

- [x] **1.7. symbols 모드 구현** ✅
  - [x] `symbols.mode = 'manual'`: manual 리스트 사용
  - [x] `symbols.mode = 'top50'`: SymbolManager.fetch_top_volume_symbols(50)
  - [x] `symbols.mode = 'top100'`: 100개
  - [x] `symbols.mode = 'all'`: 전체 (가드레일 max_streams 적용)

### **🔥 Phase 2: 포트폴리오 매니저** (단기, 1-2일)

#### **A. 포트폴리오 매니저 구현**

- [x] **2.1. portfolio_manager.py 생성** (`execution/portfolio_manager.py`) ✅
  - [x] 클래스 구조
  - [x] 일손실 컷 (daily_pnl < -limit)
  - [x] 노출 제어 (심볼별 30%, 전체 80%)
  - [x] 슬롯 관리 (최대 5개)
  - [x] 충돌 방지 (같은 심볼 반대 방향)
  - [x] PnL 추적

- [x] **2.2. engine.py 통합** ✅
  - [x] `portfolio = PortfolioManager(config)` 초기화
  - [x] 진입 전 `portfolio.can_open_position()` 체크
  - [x] 진입 후 `portfolio.add_position()` 호출
  - [x] 청산 시 `portfolio.remove_position()` 호출

#### **B. 멀티 심볼 지원**

- [x] **2.3. engine.py 멀티 심볼 루프** ✅
  - [x] symbols 루프 추가 (84-93줄, 심볼별 버퍼)
  - [x] 심볼별 버퍼 관리 (buffers dict)
  - [x] 심볼별 신호 처리

- [x] **2.4. collectors 멀티 심볼** ✅
  - [x] WebSocketCollector: 여러 심볼 구독
  - [x] SymbolManager: 전체 심볼 가져오기

#### **C. 테스트**

- [x] **2.5. 백테스트** ✅ (2025-10-21 22:48)
  - [x] 단일 심볼 (BTCUSDT) 
  - [x] 포트폴리오 제한 확인 (코드 검증)
  - [ ] 멀티 심볼 (BTC+ETH) - backtest는 단일 심볼만 지원

- [x] **2.6. Paper Trading** ✅ (2025-10-21 22:54)
  - [x] 실시간 멀티 심볼 (Manual 5개, Top50 50개, Top100 100개, All 120개)
  - [x] 로그 확인
  - [x] 가드레일 동작 확인

### **✅ Phase 3: 추가 기능** (2025-10-22 확인 완료)

- [x] **3.1. 거래 빈도 증가** ✅
  - [x] 전략 필터 확인 (config.yml에 구현됨)
  - [x] MTF 확인 (signal_generator.py에 구현됨)

- [x] **3.2. 리포트 기능 확인** ✅
  - [x] trading_reporter.py 존재 (전략별 성과 포함)
  - [ ] 백테스트 통합 (선택사항)

- [ ] **3.3. 추가 개선** (나중에)
  - [ ] 정책 스위치 (필요시)
  - [ ] Allocator (필요시)

---

## 🎯 **핵심 원칙**

### **✅ 해야 할 것**
1. 설정 중복 제거 (config.yml 단일 소스)
2. 멀티 심볼 복원 (사용자 요청)
3. 포트폴리오 매니저 라이트 (안전장치)

### **❌ 하지 말아야 할 것**
1. 과한 추상화 (YAGNI)
2. 지금 안 쓰는 레이어
3. 복잡한 Orchestrator

### **⚠️ 나중에 할 것**
1. Allocator (자본배분 복잡해지면)
2. 정책 여러 개 (필요하면)
3. 복잡한 기능

---

## 💡 **예상 효과**

### **즉시 효과**
- ✅ 설정 관리 단순화 (한 곳)
- ✅ 멀티 심볼 거래 가능
- ✅ 코드 중복 제거

### **단기 효과 (1-2일)**
- ✅ 실거래 안전장치 (일손실컷)
- ✅ 리스크 통제 (노출/슬롯)
- ✅ 충돌 방지

### **장기 효과**
- ✅ 유지보수 쉬움
- ✅ 확장 가능
- ✅ 테스트 용이

---

## 🚀 **결론**

**GPT + Cascade 합의:**
```
✅ 포트폴리오 매니저 라이트 필수
✅ 설정 통합 + 멀티 심볼 복원
✅ 과한 추상화 제거 (YAGNI)
⚠️ 정책/Allocator는 나중에
```

**다음 단계:**
1. 즉시: 설정 중복 제거 + 멀티 심볼
2. 단기: 포트폴리오 매니저 라이트
3. 실전: 백테스트 → Paper → Live

**시작할까요?** 🔥
