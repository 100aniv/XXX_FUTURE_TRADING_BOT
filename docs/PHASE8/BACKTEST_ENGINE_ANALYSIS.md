# 백테스트 엔진 구조 분석 (PHASE8-1)

**분석 일시**: 2025-11-14  
**목적**: 현행 백테스트 엔진의 작동 방식을 Freqtrade 관점에서 비교 분석  
**범위**: 데이터 소스, 실행 모델, 수수료/슬리피지, 결정론, 차이점

---

## 1. 데이터 소스

### 1.1 백테스트 시 데이터 읽기 방식

**CSV 파일 기반**
- **모듈**: `collectors/historical_collector.py`
- **클래스**: `HistoricalFeed` (단일 심볼) / `MultiSymbolHistoricalFeed` (멀티 심볼)
- **경로**: `data/{symbol}_{timeframe}_{start_date}_{end_date}.csv`

**주요 함수**:
```python
# collectors/historical_collector.py
class HistoricalFeed:
    def __init__(self, csv_path: str, symbol: str, timeframe: str):
        self.df = pd.read_csv(csv_path)
        # 시간 컬럼 정규화, 정렬
    
    def stream(self) -> Iterator[Dict]:
        """캔들을 한 줄씩 yield"""
        for i in range(self.total):
            row = self.df.iloc[i]
            candle = {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'closed_at': ts,
                'open': float(row["open"]),
                'high': float(row["high"]),
                'low': float(row["low"]),
                'close': float(row["close"]),
                'volume': float(row["volume"])
            }
            yield candle
```

**어댑터 생성** (`execution/adapters/__init__.py:create_adapters()`):
```python
if mode == 'backtest':
    from collectors.historical_collector import HistoricalFeed
    feed = HistoricalFeed(csv_path, symbol=symbol, timeframe=timeframe)
```

### 1.2 실시간 모드 (Paper/Live)

- **WebSocket**: `collectors.WebSocketCollector` (Binance WebSocket)
- **API**: `collectors.fetch_history()` (REST API로 이력 조회)

### 1.3 Freqtrade와 비교

| 항목 | 현행 시스템 | Freqtrade |
|------|------------|-----------|
| 데이터 소스 | CSV 파일 | JSON/HDF5/Feather/CSV |
| 로딩 방식 | pandas.read_csv → generator | pandas.read_hdf/json |
| 멀티 심볼 | MultiSymbolHistoricalFeed | 각 심볼별 개별 로드 |
| 시간 정규화 | timestamp → time (자동 감지) | 표준 컬럼명 강제 |

**결론**: CSV 기반으로 동일하나, Freqtrade는 HDF5/Feather를 권장 (성능)

---

## 2. 실행 모델 (체결 시뮬레이션)

### 2.1 메인 루프

**위치**: `execution/engine.py:run()`

```python
# execution/engine.py (line 468)
for candle in feed.stream():
    # 1. 시계 업데이트
    clock.update(ts)
    
    # 2. 버퍼 추가
    buffers[buffer_key].append(candle)
    
    # 3. 신호 생성
    signals = signal_generator.generate(...)
    
    # 4. 앙상블/전략 선택
    decision = ensemble.select(...) if use_ensemble else signals[0]
    
    # 5. 체결 실행
    fill = broker.execute(decision, qty)
    
    # 6. 포지션 추가
    portfolio.add_position(entry_price=fill['filled_price'], ...)
```

### 2.2 체결 로직

**위치**: `execution/adapters/brokers.py:SimBroker.execute()`

```python
class SimBroker:
    def __init__(self, fee_rate=0.0004, slippage_pct=0.0005):
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
    
    def execute(self, decision: dict, qty: float) -> dict:
        side = decision.get('side')  # 'LONG' or 'SHORT'
        price = float(decision.get('entry', 0))  # 신호의 entry 가격
        
        # 슬리피지 적용
        if side == 'LONG':
            filled_price = price * (1 + self.slippage_pct)  # 매수: 가격 상승
        else:
            filled_price = price * (1 - self.slippage_pct)  # 매도: 가격 하락
        
        value = filled_price * qty
        fee = value * self.fee_rate
        
        return {
            'success': True,
            'filled_price': filled_price,
            'qty': qty,
            'value': value,
            'fee': fee,
            'timestamp': datetime.now()
        }
```

### 2.3 체결 시점

**⚠️ 중요**: 현재 구현에서는 **신호 생성 시점의 `entry` 가격**을 사용합니다.

```python
# execution/engine.py (line 1082-1085)
decision["entry_price"] = decision.get("entry", 0)  # 신호에서 가져온 entry
```

**신호의 entry 가격은 어디서 결정되는가?**
- 전략 모듈 (`strategies/`) 에서 생성
- 일반적으로 **현재 캔들의 close 가격** 또는 **특정 지표 기반 가격**

**fill_policy 적용 여부**:
- `backtest_clean.yml`에서 `execution.fill_policy: next_open` 설정
- ⚠️ **현재 코드에서 fill_policy를 실제로 반영하는 로직은 확인되지 않음**
- 신호의 `entry` 가격을 그대로 사용 → fill_policy가 무시될 가능성

### 2.4 Freqtrade와 비교

| 항목 | 현행 시스템 | Freqtrade |
|------|------------|-----------|
| 기본 체결 시점 | 신호의 entry 가격 (보통 close) | next candle open |
| fill_policy 구현 | ⚠️ 미구현 (설정만 존재) | 명시적 구현 |
| 슬리피지 적용 | 진입 시 % 적용 | 진입/청산 모두 적용 |
| 수수료 적용 | value * fee_rate | 동일 |

**결론**: fill_policy가 설정은 있지만 실제 적용되지 않음. 개선 필요.

---

## 3. 수수료/슬리피지 적용 방식

### 3.1 backtest_clean 모드 설정

**파일**: `configs/modes/backtest_clean.yml`

```yaml
execution:
  fill_policy: next_open
  fees_bps: 10  # 0.1%
  slippage:
    type: fixed
    bps: 5  # 0.05%
```

### 3.2 실제 적용 코드

**위치**: `execution/adapters/__init__.py:create_adapters()` (line 305-308)

```python
broker = SimBroker(
    fee_rate=fees_cfg.get('taker', 0.0004),  # ⚠️ fees_bps가 아닌 taker 사용
    slippage_pct=fees_cfg.get('slippage', 0.0005)  # ⚠️ slippage.bps가 아닌 slippage 사용
)
```

**⚠️ 문제점**:
- `fees_bps` (10) → 실제로는 `fees.taker` (0.0004) 사용
- `slippage.bps` (5) → 실제로는 `fees.slippage` (0.0005) 사용
- **backtest_clean 설정이 무시됨!**

### 3.3 슬리피지 적용 시점

- **진입 시**: SimBroker.execute()에서 적용 ✅
- **청산 시**: 코드 확인 필요 (exit 로직 분석 필요)

### 3.4 일관성 확인

**모든 트레이드에 일관되게 적용되는가?**
- ✅ SimBroker.execute()가 모든 진입에 호출됨
- ✅ fee_rate, slippage_pct가 고정값
- ✅ 결정적(deterministic)

**하지만**:
- ❌ config에서 읽는 키가 잘못됨
- ❌ backtest_clean 모드의 fees_bps, slippage.bps가 반영 안 됨

### 3.5 Freqtrade와 비교

| 항목 | 현행 시스템 | Freqtrade |
|------|------------|-----------|
| 수수료 모델 | 고정 % (fee_rate) | 고정 % (maker/taker) |
| 슬리피지 모델 | 고정 % (slippage_pct) | 비활성화 or 고정 % |
| 적용 시점 | 진입만 확인됨 | 진입/청산 모두 |
| 설정 반영 | ❌ 키 불일치 | ✅ 정확히 반영 |

**결론**: 구조는 유사하나, config 키 매핑 오류로 설정이 반영 안 됨.

---

## 4. 결정론 (Determinism)

### 4.1 재현성 확인

**동일 config + 동일 기간 = 동일 결과?**

**결정적 요소**:
- ✅ CSV 데이터: 순차 읽기, 변경 없음
- ✅ 슬리피지/수수료: 고정값
- ✅ 시간: SimClock으로 캔들 시간 사용

**비결정적 요소 (잠재적)**:
1. **현재 시간 사용**:
   ```python
   # brokers.py (line 58, 99)
   'timestamp': datetime.now()  # ⚠️ 실행 시간 의존
   ```
   → 체결 timestamp가 실제 시간 사용 → 재현성 손상

2. **랜덤 요소**:
   - uuid4() 사용 (position_id 생성 시)
   - 하지만 거래 로직에는 영향 없음

3. **Redis dedup**:
   ```python
   # engine.py (line 539-549)
   if redis_client.exists(dedup_key):
       continue  # 중복 캔들 스킵
   ```
   → Redis 상태에 따라 결과 달라질 수 있음 (백테스트에서는 비활성화 필요)

### 4.2 개선 필요 사항

1. **datetime.now() 제거**:
   - SimBroker에서 clock.now() 사용
   - 캔들 시간 기준으로 체결 timestamp 설정

2. **Redis dedup 백테스트 비활성화**:
   - backtest 모드에서 redis_client = None 처리

3. **random seed 고정**:
   - 혹시 모를 랜덤 요소 제어

### 4.3 Freqtrade와 비교

| 항목 | 현행 시스템 | Freqtrade |
|------|------------|-----------|
| 시간 결정론 | ⚠️ datetime.now() 사용 | ✅ 캔들 시간만 사용 |
| Redis/외부 의존성 | ⚠️ dedup 활성화 가능 | ✅ 백테스트에서 격리 |
| 랜덤 시드 제어 | ❌ 없음 | ✅ optional seed 지원 |

**결론**: datetime.now()와 Redis dedup로 인한 재현성 문제 가능성.

---

## 5. Freqtrade와의 차이 요약

### 5.1 유사점

- ✅ CSV 기반 백테스트
- ✅ 단일 공통 루프 (backtest = paper = live)
- ✅ 고정 수수료/슬리피지
- ✅ Broker/Feed/Clock 어댑터 패턴

### 5.2 차이점

| 분류 | 현행 시스템 | Freqtrade | 우선순위 |
|------|------------|-----------|---------|
| **fill_policy** | 설정만 존재, 미구현 | next_open 명시적 구현 | 🔴 높음 |
| **config 매핑** | fees_bps → fees.taker (오류) | 정확히 반영 | 🔴 높음 |
| **재현성** | datetime.now() 사용 | 캔들 시간만 | 🟡 중간 |
| **Redis 격리** | 백테스트에서도 활성화 | 완전 격리 | 🟡 중간 |
| **데이터 형식** | CSV only | HDF5/Feather 지원 | 🟢 낮음 |
| **청산 슬리피지** | 확인 필요 | 명시적 적용 | 🟡 중간 |

### 5.3 향후 PHASE8-BT-REFACTOR 제안

**🔴 높은 우선순위 (필수)**:
1. **fill_policy 구현**:
   - `next_open`: 다음 캔들 open 가격으로 체결
   - `current_close`: 현재 캔들 close 가격 (기본값)
   - 신호 생성과 체결 시점 분리

2. **config 키 매핑 수정**:
   ```python
   # 수정 전
   fee_rate=fees_cfg.get('taker', 0.0004)
   
   # 수정 후
   fee_bps = exec_cfg.get('fees_bps', 10) / 10000  # 10 → 0.001
   slippage_bps = exec_cfg.get('slippage', {}).get('bps', 5) / 10000
   broker = SimBroker(fee_rate=fee_bps, slippage_pct=slippage_bps)
   ```

**🟡 중간 우선순위 (권장)**:
3. **재현성 개선**:
   - SimBroker에서 datetime.now() → clock.now() 사용
   - Redis dedup 백테스트 비활성화

4. **청산 슬리피지 명시적 적용**:
   - 현재 exit 로직 확인 후 슬리피지 적용 확인

**🟢 낮은 우선순위 (개선)**:
5. **HDF5/Feather 지원**: 대용량 데이터 성능 개선
6. **Vectorized 백테스트**: 루프 대신 vectorized 연산

---

## 6. 실행 결과 (2025-11-14)

### 6.1 backtest_clean 검증

**Run ID**: `20251114_163902_liqw`

**설정**:
- Mode: backtest_clean
- Strategy: scalping
- Symbol: BTCUSDT
- Timeframe: 5m
- 기간: 2024-12-27 ~ 2024-12-30 (3일, 865 캔들)

**산출물** ✅:
- `effective_config.yml` - 521줄, 병합된 설정
- `scorecard.csv` - 12줄
- `scorecard.md` - 38줄

**성과 (더미 데이터 5건)**:
- Trades: 5
- Winrate: 60.0%
- Profit Factor: 3.75
- Max DD: -1.2%
- Loss>8%: 0

### 6.2 발견된 문제

1. ✅ **ensemble 키 충돌** → 해결 (current.yml 수정)
2. ⚠️ **실제 백테스트 엔진 미연동** → 더미 데이터로만 작동
3. ⚠️ **fill_policy 미구현** → 설정이 반영 안 됨
4. ⚠️ **config 키 매핑 오류** → fees_bps, slippage.bps 무시됨

---

## 7. 다음 단계 (PHASE8-2)

### 7.1 즉시 수정 필요
- [ ] run_backtest.py와 실제 engine.py 연동
- [ ] fill_policy 구현 (next_open)
- [ ] config 키 매핑 수정 (fees_bps, slippage.bps)

### 7.2 검증 필요
- [ ] 청산 시 슬리피지 적용 여부 확인
- [ ] Redis dedup 백테스트 비활성화 확인
- [ ] datetime.now() 사용 부분 확인

### 7.3 문서화
- [x] 백테스트 엔진 구조 분석 완료
- [ ] fill_policy 구현 설계
- [ ] config 키 매핑 수정 가이드

---

**작성**: Windsurf + User  
**검증**: backtest_clean 실행 테스트  
**참고**: Freqtrade 백테스트 모델
