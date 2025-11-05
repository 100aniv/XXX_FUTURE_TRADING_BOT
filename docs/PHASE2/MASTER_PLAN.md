# 🚀 PHASE 2 마스터 플랜

**작성일:** 2025-10-21  
**최종 업데이트:** 2025-10-22 14:15 KST  
**상태:** Phase 2 완료 ✅  
**목적:** 설정 중복 제거 + 멀티 심볼 지원 + 성능 최적화

---

## ✅ **빠른 체크리스트**

### **Phase 1 완료 항목 (2025-10-21)**

- [x] 설정 중복 제거 (30+개)
  - [x] position_sizer.py (6개)
  - [x] risk_manager.py (4개)
  - [x] ensemble.py (20+개)
  
- [x] config.yml 중심 설계
  - [x] load_yaml_config() 추가
  - [x] YAML 우선, 환경변수 fallback
  - [x] 모든 모듈 config 전달
  
- [x] 멀티 심볼 완전 지원
  - [x] symbols.mode (manual/top50/top100/all)
  - [x] SymbolManager 활용
  - [x] 가드레일 (max_streams)
  - [x] paper/live 멀티 심볼 구독
  - [x] engine.py 멀티 심볼 버퍼

### **Phase 2 다음 단계**

- [x] 테스트 (2025-10-21 22:54 완료) ✅✅✅
  - [x] Config 로드 ✅
  - [x] Backtest (단일 심볼) ✅
  - [x] Paper - Manual (5개) ✅
  - [x] Paper - Top50 (50개) ✅
  - [x] Paper - Top100 (100개) ✅
  - [x] Paper - All (120개, 가드레일) ✅
  - [ ] Live 모드 (맨 마지막, 선택)
  
- [x] 포트폴리오 매니저 (2025-10-21 23:45 완료) ✅✅✅
  - [x] portfolio_manager.py 생성 ✅
  - [x] 심볼별 exposure 제한 ✅
  - [x] 전략별 포지션 수 제한 ✅
  - [x] 상관성 관리 ✅
  - [x] config.yml 섹션 추가 ✅
  - [x] engine.py import 추가 ✅
  - [x] engine.py 신호 처리 통합 ✅
    - [x] portfolio.can_open_position() 체크 (235-247줄)
    - [x] portfolio.add_position() 호출 (285-299줄)
    - [x] portfolio.remove_position() 호출 (131-135줄)
  
- [x] 거래 빈도 증가 (2025-10-22 00:20 완료) ✅
  - [x] 전략 필터 완화 (scalping/daytrade/reversion: false)
  - [x] 멀티 타임프레임 (signal_generator.py MTF 캐싱 구현)

- [x] config.yml 우선순위 수정 (2025-10-22 14:00 완료) ✅
  - [x] main.py: mode = CFG.get('mode', ...) 우선
  - [x] 환경변수는 fallback으로만
  - [x] docker-compose.yml: config.yml volumes 마운트
  
- [x] 단일 전략 테스트 (2025-10-22 14:15 완료) ✅
  - [x] daytrade 단독 실행 확인
  - [x] 로컬 백테스트 성공 (Docker 이슈 우회)
  - [x] 포트폴리오 매니저 동작 확인

- [x] 전략별 백테스트 및 튜닝 (2025-10-22 16:45 완료) ✅
  - [x] 6개 전략 개별 테스트
  - [x] 성과 비교 분석
  - [x] Reversion RR 조정 (1.8 → 1.3)
  - [x] Trend 필터 완화
  - [x] Scalping/Breakout 문제 진단
  - [x] 최종 리포트 작성 (BACKTEST_REPORT.md)
  - [x] 문서 정리 및 통합 (14개 → 4개)

### **Phase 2 완료 요약**
**14일 백테스트 결과:**
- ✅ Daytrade만 수익 (+$5,212)
- ⚠️ Reversion 승률 40.85%지만 RR 문제로 손실
- ❌ Scalping/Breakout 재설계 필요

**3개월 백테스트 결과 (2025-10-22 17:30 완료):**
- ✅ 9개 심볼, 25,921 캔들/심볼
- ✅ Daytrade 안정성 확인 (+$5,212 유지)
- ⚠️ Trend 거래 5배 증가 (92→506건), 손실 확대
- 📝 결론: 기간/심볼 늘려도 동일한 패턴

**포지션 사이즈 버그 수정 후 (2025-10-22 19:54 완료):**
- ✅ 1,047건 거래 (이전 3건 → 349배 증가)
- ✅ position_value 재계산 오류 수정
- ✅ symbol 키 누락 수정
- ✅ config.yml 기반 백테스트 완성 (하드코딩 제거)
- ✅ 멀티 심볼 백테스트 지원 추가

**멀티 심볼 백테스트 (2025-10-23 00:46 완료):**
- ✅ 3,621건 거래 (5개 심볼, 3개월)
- ✅ 버그 3개 수정:
  1. database.py 통합 (backtest_db.py 삭제)
  2. risk.add_position candle_symbol 사용
  3. 포지션 체크 심볼 확인 추가
- ❌ ROI: -33.49% (전략 재조정 필요)
- 📊 결과:
  - scalping: 722건, 승률 31.7%, PnL -$55.80
  - daytrade: 1,545건, 승률 27.8%, PnL -$1,444.73
  - reversion: 1,348건, 승률 47.2%, PnL -$1,780.65
  - trend: 6건, 승률 16.7%, PnL -$68.16

**TUNING_VIBLE 기준 적용 (2025-10-23):**
- ✅ 자동 검증 시스템 추가 (analyze_backtest_results)
- ✅ TUNING_BENCHMARK.md 문서화
- 🎯 백테스트 합격 기준:
  - 승률 × RR ≥ 2.0
  - 승률 ≥ 50%
  - RR ≥ 1.5
  - MDD ≥ -20%
  - 연속 손실 ≤ 6
  - Profit Factor ≥ 1.3
  - ROI ≥ 10%

**다음 단계:**
- TUNING_VIBLE 기준 달성까지 반복 튜닝
- 합격 시 → 페이퍼 트레이딩 (4~6주)
- 페이퍼 합격 시 → 소액 라이브 (리스크 1/3)

---

## 📊 **Phase 1 현황 (완료)**

### **✅ 완료된 작업**

#### **A. execution 모듈 리팩토링** ✅
1. **position_sizer.py** 
   - os.getenv() 6개 제거
   - `__init__(self, config)` 시그니처로 변경
   - config['capital'], config['risk'], config['position_sizing']에서 읽기

2. **risk_manager.py**
   - os.getenv() 4개 제거
   - `__init__(self, config)` 시그니처로 변경
   - config['risk'], config['capital']에서 읽기

3. **engine.py**
   - `PositionSizer(config)`, `RiskManager(config)` 호출 수정
   - config 전달 방식 적용

#### **B. strategies 모듈 리팩토링** ✅
4. **ensemble.py**
   - CFG 딕셔너리 제거 (40줄 삭제)
   - 15+ CFG 참조 → config['strategy']['ensemble'] 참조로 변경
   - 모든 함수에 config 파라미터 추가:
     - `load_strategy_performance(conn, window_days)`
     - `collect_signals(conn, symbol, timeframe, candle_closed_at, window_sec)`
     - `calculate_weights(signals, perf, config)`
     - `calculate_ensemble_score(signals, weights, config)`
     - `apply_bonuses(signals, score, chosen_side, config)`
     - `combine_signals(signals, conn, config)`
   - engine.py 호출부 수정

#### **C. config.yml 완성** ✅
5. **ensemble 섹션 추가**
   ```yaml
   strategy:
     ensemble:
       weights:          # 전략별 가중치 (6개)
       alpha_winrate: 0.4    # 우선순위 계산 (5개)
       theta_long: 0.15      # 임계값 (2개)
       consensus_bonus: 0.2  # 보너스 (3개)
       window_sec: 10        # 윈도우 (2개)
   ```

6. **position_sizing 섹션 확인**
   ```yaml
   position_sizing:
     quality_weight_min: 0.7
     quality_weight_max: 1.3
     max_position_value: 5000
     min_position_value: 10
   ```

### **📊 설정 중복 제거 결과**

**Before:** 30+ 설정값 중복 (os.getenv()로 분산)  
**After:** 0개 중복 (config.yml 단일 소스)

**제거 항목:**
- position_sizer: 6개
- risk_manager: 4개
- ensemble: 20+개
- **총 30+개 중복 제거** ✅

---

## ✅ **Phase 1 완료** (2025-10-21)

### **멀티 심볼 준비 - 100% 완료**

- [x] **1.6. config.yml 완성** ✅
  - [x] symbols.mode (manual/top50/top100/all)
  - [x] symbols.manual (수동 리스트)
  - [x] symbols.core (항상 포함)
  - [x] symbols.topN (N, min_volume, refresh_interval)
  - [x] symbols.max_streams (가드레일)

- [x] **1.7. common/config.py 수정** ✅
  - [x] load_yaml_config() 추가
  - [x] load_config() 수정 (config.yml 우선, 환경변수 fallback)
  - [x] 하위 호환성 유지

- [x] **1.8. main.py 멀티 심볼 지원** ✅
  - [x] SymbolManager 임포트
  - [x] mode별 심볼 로드 (manual/top50/top100/all)
  - [x] core 심볼 병합
  - [x] 가드레일 적용 (max_streams 제한)
  - [x] collectors에 심볼 리스트 전달
  - [x] 백테스트: 단일/멀티 심볼 모두 지원 (config.yml 기반)
  - [x] paper/live: 멀티 심볼 완전 지원

- [x] **1.9. engine.py 멀티 심볼 루프** ✅ (이미 구현됨)
  - [x] 심볼별 버퍼 관리 (buffers = {symbol: deque})
  - [x] 심볼별 신호 처리
  - [x] 멀티 심볼 아키텍처 완성

### **완성된 아키텍처**

```
config.yml
  ↓
common/config.py (load_yaml_config)
  ↓
main.py
  ├─ SymbolManager (common/symbol_manager.py)
  │   ├─ mode='manual' → symbols.manual
  │   ├─ mode='top50' → fetch_top_volume_symbols(50) + core
  │   ├─ mode='top100' → fetch_top_volume_symbols(100) + core
  │   └─ mode='all' → fetch_all_usdt_symbols() + core
  │
  ├─ 가드레일: max_streams 제한
  │
  ├─ backtest:  # config.yml 기반
  │   ├─ 단일 심볼: HistoricalFeed (config.backtest.symbol)
  │   └─ 멀티 심볼: MultiSymbolHistoricalFeed (symbols 전체)
  ├─ paper: WebSocketCollector(symbols)    # 멀티 심볼
  └─ live: WebSocketCollector(symbols)     # 멀티 심볼
      ↓
engine.py
  ├─ buffers = {symbol: deque(maxlen=lookback)}  # 심볼별 독립 버퍼
  ├─ PositionSizer(config)
  ├─ RiskManager(config)
  └─ SignalGenerator(config, strategies)
      ↓
strategies/ensemble.py
  └─ combine_signals(signals, conn, config)
```

### **사용법**

#### **1. Manual 모드 (기본)**
```yaml
# config.yml
symbols:
  mode: manual
  manual:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
```

#### **2. Top50 모드**
```yaml
symbols:
  mode: top50
  core:
    - BTCUSDT
    - ETHUSDT
  topN:
    n: 50
    min_volume_24h: 30000000
```

#### **3. All 모드**
```yaml
symbols:
  mode: all
  max_streams: 120  # 가드레일
```

#### **4. 실행**
```bash
# Paper Trading (멀티 심볼)
TRADING_MODE=paper python main.py

# Live Trading (멀티 심볼)
TRADING_MODE=live python main.py

# Backtest (단일 심볼)
TRADING_MODE=backtest python main.py
```

---

## 📋 **이전 완료 사항 (Phase 0)**

### **아키텍처 체크리스트: 6/6 (100%)**

| 항목 | 상태 |
|-----|------|
| 1. 엔진 모드 분기 금지 | ✅ 100% |
| 2. Collector 표준화 | ✅ 100% |
| 3. Broker 일관성 | ✅ 100% |
| 4. Clock 통일 | ✅ 100% |
| 5. 리스크/사이징 외부 | ✅ 100% |
| 6. 단위 테스트 | ✅ 80% |

### **구현 완료 항목**

1. **main.py 단순화** (244줄 → 51줄)
   - 백테스트: `TradingEngine.run_all_backtests()`
   - 페이퍼/라이브: `TradingEngine.run_realtime_mode(mode)`

2. **전략 파라미터 수정** (RR 비율 상향)
   - Scalping: 1.5 → 2.5 (익절 0.5%)
   - Daytrade: 2.0 → 3.0 (익절 0.6%)

3. **DB 스키마 수정**
   - trading.trades: leverage 컬럼
   - trading.decisions: leverage, executed, executed_at 컬럼

4. **Executor None 값 처리**
   - simulation.py ✅
   - paper.py ✅
   - live.py ✅

5. **백테스트 유틸리티**
   - common/backtest_utils.py

---

## 🎯 **Phase 2 계획 (다음 단계)**

### **우선순위 1: 포트폴리오 매니저** ⏳

#### **목표**
- 멀티 심볼 환경에서 포트폴리오 수준 리스크 관리
- 심볼별/전략별 exposure 제한
- 동시 포지션 수 제어

#### **작업 항목**
1. **execution/portfolio_manager.py 생성**
   ```python
   class PortfolioManager:
       def __init__(self, config):
           self.equity = config['capital']['initial']
           self.max_positions = config['risk']['max_positions']
           self.max_exposure_per_symbol = config['risk']['max_exposure_per_symbol']
           self.active_positions = {}  # {symbol: position}
       
       def allow(self, symbol: str, strategy: str, position_value: float) -> bool:
           """새 포지션 허용 여부"""
           # 1. 최대 포지션 수
           if len(self.active_positions) >= self.max_positions:
               return False
           
           # 2. 심볼 중복
           if symbol in self.active_positions:
               return False
           
           # 3. 심볼별 exposure 한도
           if position_value > self.equity * self.max_exposure_per_symbol:
               return False
           
           # 4. 전체 exposure 한도 (80%)
           total_exposure = sum(p['value'] for p in self.active_positions.values())
           if total_exposure + position_value > self.equity * 0.8:
               return False
           
           return True
   ```

2. **engine.py 통합**
   ```python
   portfolio = PortfolioManager(config)
   
   # 신호 처리 루프에서
   if portfolio.allow(symbol, strategy, position_value):
       execute(decision)
   ```

3. **config.yml 설정 추가**
   ```yaml
   risk:
     max_positions: 10  # 최대 동시 포지션
     max_exposure_per_symbol: 0.2  # 심볼당 20%
     max_total_exposure: 0.8  # 전체 80%
   ```

### **우선순위 2: 거래 빈도 증가**

#### **목표**
- 하루 30-50건 (현재 1건/일)
- 스캘핑 중심 (성공 패턴 적용)

#### **방법**
1. **전략 필터 완화**
   - RSI 범위 확대
   - BB 밴드 조건 완화
   - 거래량 임계값 낮춤

2. **멀티 타임프레임 활용**
   - 5m: 스캘핑
   - 15m: 데이트레이드
   - 1h: 스윙

3. **멀티 전략 병렬 실행**
   - 전략별 독립 거래
   - 심볼별 분산 투자

### **우선순위 3: 성능 최적화**

#### **Context Scaling**
```python
# 레짐별 포지션 크기 조정
if regime == 'trending':
    position *= 1.2  # 확대
elif regime == 'choppy':
    position *= 0.7  # 축소
```

#### **Portfolio Caps**
```python
# 심볼별 한도
max_per_symbol = equity * 0.2  # 20%

# 전략별 예산
strategy_budgets = {
    'scalping': equity * 0.3,
    'daytrade': equity * 0.4,
    'swing': equity * 0.3,
}
```

#### **Safety Brakes**
```python
# DD cutoff
if daily_loss > equity * 0.05:  # 5%
    stop_trading()

# Slippage 체크
if actual_price > expected_price * 1.002:  # 0.2%
    reject_trade()
```

---

## 📈 **성공 패턴 (백테스트 검증)**

### **REVERSION (100% 승률)**
- RSI < 30 + BB 하단 + EMA 역배열
- 3가지 조건 모두 충족
- 12건 거래

### **SCALPING (95.2% 승률)**
- BB 밴드 근접 + MACD 방향 + EMA 추세 + RSI 적정 + 거래량
- 5가지 조건 모두 충족
- 21건 거래

### **핵심 원칙**
1. 다층 필터 (3-5개 조건)
2. BB 밴드 + MACD/RSI 조합
3. 거래량 확인
4. 적절한 거래 빈도 (10-50건)

---

## 🔧 **다음 작업 흐름**

### **즉시 (오늘)**
1. ✅ 설정 중복 제거 (완료)
2. 🔄 멀티 심볼 준비 (진행 중)
   - config.yml symbols 섹션
   - main.py 멀티 심볼 루프
   - collectors 수정

### **단기 (1-2일)**
3. 멀티 심볼 테스트
   - 백테스트: BTC + ETH
   - Paper Trading: 실시간 5개 심볼
4. 포트폴리오 매니저 구현
5. 성과 모니터링

### **중기 (1주)**
6. 전략 필터 완화 (거래 빈도 증가)
7. Context Scaling 추가
8. Safety Brakes 구현
9. HTML 리포트 강화

---

## 📝 **업데이트 정책**

- ✅ 이 파일만 업데이트 (Docs/PHASE2/MASTER_PLAN.md)
- ✅ 완료 항목: 체크박스 변경
- ✅ 새 섹션: 마지막에 추가
- ❌ 새 MD 파일 생성 금지 (전혀 다른 항목 제외)

---

## 📊 **모듈 아키텍처 (중복 없음 확인)**

### **execution/ 모듈 구조**
```
execution/
├── position_sizer.py      # 포지션 크기 계산 (RPT, Kelly)
├── risk_manager.py        # 거래 수준 리스크 (일일 손실, Flash Guard)
├── portfolio_manager.py   # 포트폴리오 수준 리스크 (전략 배분, 상관성)
└── position_tracker.py    # 포지션 생명주기 (트레일링, TP/SL)
```

**역할 구분:**
- **RiskManager**: 개별 거래 리스크 (일일 손실, 급등락)
- **PortfolioManager**: 포트폴리오 밸런싱 (멀티 심볼 환경)
- **→ 둘 다 필요! 계층이 다름!** ✅

**중복 체크 완료:**
- execution/ 모듈: 4개, 모두 독립 ✅
- common/ 모듈: 9개, 모두 독립 ✅

---

## 🎉 **추가 완료 사항 (2025-10-21 22:54)**

### **전략 설정 완전 통합** ✅
1. **strategy_config.py 삭제**
   - _archived/strategy_config.py.bak로 백업
   - 더 이상 중간 레이어 불필요

2. **config.yml에 strategies 섹션 추가**
   ```yaml
   strategies:
     scalping:
       rr: 2.5
       risk_per_trade: 0.01
       cooldown_candles: 3
     # ... (6개 전략 모두)
   ```

3. **execution/engine.py 수정**
   - `from common.strategy_config import load_strategy_params` 제거
   - `cfg = config.get('strategies', {}).get(strategy_id, {})` 직접 사용

**결과:** 
- ✅ strategy_params.yaml 경고 완전 제거
- ✅ config.yml 단일 소스 완성
- ✅ 설정 중복 0개!

---

## 🎉 **Phase 1 최종 요약**

### **완료된 작업 (2025-10-21)**

#### **1. 설정 중복 제거** ✅
- position_sizer.py: os.getenv() 6개 → config 전달
- risk_manager.py: os.getenv() 4개 → config 전달
- ensemble.py: CFG 딕셔너리 40줄 삭제, 15+ 참조 변경
- **총 30+개 설정값 통합**

#### **2. config.yml 중심 설계** ✅
- common/config.py: load_yaml_config() 추가
- config.yml 우선, 환경변수 fallback
- 모든 모듈이 config 전달 방식

#### **3. 멀티 심볼 완전 지원** ✅
- symbols.mode: manual/top50/top100/all
- SymbolManager 활용
- 가드레일: max_streams 제한
- paper/live: 멀티 심볼 구독
- backtest: 단일 심볼 (HistoricalFeed 한계)

### **아키텍처 개선**

**Before (중복):**
```
position_sizer.py → os.getenv('EQUITY_USDT')
risk_manager.py → os.getenv('EQUITY_USDT')
ensemble.py → CFG['weight_trend']
main.py → symbol = 'BTCUSDT'  # 하드코딩
```

**After (통합):**
```
config.yml (단일 소스)
  ↓
common/config.py (load_yaml_config)
  ↓
all modules (config 전달)
  ↓
main.py → SymbolManager → symbols (동적)
```

### **파일 변경 이력**

| 파일 | 변경 내용 | 상태 |
|-----|----------|------|
| config.yml | symbols 섹션 완성 | ✅ |
| common/config.py | load_yaml_config() 추가 | ✅ |
| main.py | 멀티 심볼 지원 | ✅ |
| execution/position_sizer.py | config 전달 방식 | ✅ |
| execution/risk_manager.py | config 전달 방식 | ✅ |
| execution/engine.py | config 전달 확인 | ✅ |
| strategies/ensemble.py | CFG 제거, config 사용 | ✅ |

### **다음 단계**

1. **테스트** (즉시)
   - Paper Trading: 5개 심볼
   - config.yml mode 전환 확인

2. **포트폴리오 매니저** (1-2일)
   - execution/portfolio_manager.py
   - 심볼별/전략별 exposure 제한

3. **거래 빈도 증가** (1주)
   - 전략 필터 완화
   - 멀티 타임프레임 활용

---

## 🔧 **기술 노트**

### **중요 설계 결정**

#### **1. config.yml 우선 전략**
- 환경변수보다 YAML 우선
- 하위 호환성 유지 (fallback)
- 설정 변경 = 파일 수정만

#### **2. SymbolManager 활용**
- 별도 파일 (common/symbol_manager.py)
- main.py에서만 호출
- collectors에 리스트 전달

#### **3. 가드레일 필수**
- max_streams: 최대 구독 수
- 메모리 보호 (buffers)
- API 제한 준수

#### **4. 백테스트 단일 심볼**
- HistoricalFeed 구조적 한계
- 멀티 심볼 = paper/live
- 향후 개선 가능 (우선순위 낮음)

### **모듈 의존성**

```
config.yml
  ↓
common/config.py
  ├─ load_yaml_config()
  └─ load_config() → yaml 우선
      ↓
main.py
  ├─ common/symbol_manager.py
  ├─ collectors/websocket_collector.py (멀티 심볼)
  └─ execution/engine.py
      ├─ execution/position_sizer.py (config)
      ├─ execution/risk_manager.py (config)
      └─ strategies/ensemble.py (config)
```

### **설정 계층**

```
config.yml (최우선)
  ↓
환경변수 (fallback)
  ↓
하드코딩 기본값 (최후)
```

---

**업데이트:** 2025-10-22 00:39 KST  
**작성자:** Cascade AI  
**버전:** Phase 2 Complete - 리포트 최소화 + 다음 단계 준비 ✅
