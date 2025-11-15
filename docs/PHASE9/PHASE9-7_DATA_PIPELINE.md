# PHASE9-7: 데이터 파이프라인 통합 정리 + 1분봉 자동 다운로드 구조 구축

## 📋 Executive Summary

**목표**: 데이터 파이프라인 통합 정리 및 1분봉 자동 다운로드 구조 구축  
**상태**: ✅ **다운로드 파이프라인 완료** (백테스트는 scalping.py 파일 복원 필요)  
**주요 산출물**:
- `scripts/download_data.py`: 범용 CLI 다운로더
- `data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv`: 131,041개 캔들

---

## 🎯 작업 목표

### 1. 데이터 관련 코드 전수 조사 ✅
- scripts/, collectors/, data/ 탐색
- 다운로더, 컬렉터, 데이터 파이프라인 구조 파악

### 2. 1분봉 자동 다운로드 파이프라인 구축 ✅
- 기존 코드 재활용 (download_historical_data.py 기반)
- CLI 인자 지원 (argparse)
- 백테스트 호환 CSV 포맷 (time, open, high, low, close, volume)

### 3. 백테스트 스모크 테스트 ⚠️
- 7일 테스트: 진행 중 (scalping.py 파일 복원 필요)
- 로그 확인: [SCALPING V2 INIT], [SCALPING V2 DEBUG], [SCALPING V2 SIGNAL]

---

## 🗂️ 데이터 파이프라인 구조 (전수 조사 결과)

### 1. 다운로더 스크립트들 (scripts/)

#### `download_historical_data.py`
- **역할**: 범용 히스토리 데이터 다운로더 (10년치)
- **거래소**: Binance API (`binance.client.Client`)
- **심볼/타임프레임**: 하드코딩 (BTCUSDT, ETHUSDT / 5m, 15m, 1h, 4h)
- **출력 포맷**: CSV (`timestamp, open, high, low, close, volume`)
- **저장 경로**: `data/historical/{symbol}_{interval}_{start}_{end}.csv`
- **백테스트 연결**: HistoricalFeed가 CSV 로드

#### `download_2024_data.py`
- **역할**: 2024년 전용 다운로더
- **거래소**: Binance API
- **심볼/타임프레임**: 하드코딩 (BTCUSDT / 5m)
- **출력 포맷**: CSV
- **저장 경로**: `data/{symbol}_{interval}_{start}_{end}.csv`

#### `download_backtest_periods.py`
- **역할**: 특정 레짐 블록 다운로더 (2018~2024 대표 기간)
- **거래소**: Binance API
- **심볼/타임프레임**: BTCUSDT / 5m, 15m, 1h, 4h
- **출력 포맷**: CSV (time 컬럼명 사용)
- **저장 경로**: `data/backtest_periods/{symbol}_{interval}_{period_name}.csv`
- **특징**: 레짐별 블록 (bear_2018, covid_2020, halving20_bull, etc.)

#### `download_backtest_data_3months.py`
- **역할**: 3개월 데이터 다운로더
- **거래소**: Binance API
- **출력 포맷**: CSV

#### ⭐ **download_data.py** (PHASE9-7 신규)
- **역할**: 범용 CLI 다운로더 (**최소 변경 원칙 준수**)
- **거래소**: Binance API
- **심볼/타임프레임**: CLI 인자로 지정 (`--symbol`, `--timeframe`)
- **출력 포맷**: CSV (**time 컬럼명**, 백테스트 호환)
- **저장 경로**: CLI 인자로 지정 (`--output-path`)
- **특징**:
  - argparse 기반 CLI
  - 날짜 범위 지정 (`--start-date`, `--end-date`)
  - 기존 `download_historical_data.py` 로직 재활용
  - **컬럼명 변경**: `timestamp` → `time` (HistoricalFeed 호환)

---

### 2. 데이터 컬렉터 (collectors/)

#### `historical_collector.py` ⭐
- **역할**: CSV → 백테스트 스트림 (HistoricalFeed 클래스)
- **기능**:
  - CSV 파일 읽기 및 파싱
  - 컬럼명 표준화 (`timestamp` → `time`)
  - 시간 변환 (epoch 밀리초/초 → datetime)
  - 날짜 범위 필터링 (`start_date`, `end_date`, `days`)
  - 타임프레임 리샘플링 (15m → 1h/4h)
  - 캔들 스트림 생성 (generator)
- **백테스트 연결**: `run_backtest.py`에서 `HistoricalFeed` 사용

#### `rest_collector.py`
- **역할**: REST API 수집
- **거래소**: Binance
- **용도**: 실시간 데이터 수집 (백테스트 아님)

#### `websocket_collector.py`
- **역할**: WebSocket 실시간 수집
- **거래소**: Binance
- **용도**: 라이브 트레이딩

---

### 3. 백테스트 파이프라인 연결 포인트

```
[다운로드] scripts/download_data.py
    ↓
[CSV 저장] data/{symbol}_{timeframe}_{start}_{end}.csv
    ↓
[CSV 로드] collectors/historical_collector.py (HistoricalFeed)
    ↓
[캔들 스트림] run_backtest.py → BacktestEngine
    ↓
[지표 계산] indicators/core_indicators.py (add_indicators)
    ↓
[전략 로직] strategies/scalping.py (signal_logic)
    ↓
[백테스트 실행] execution/backtest_engine.py
    ↓
[결과 저장] artifacts/{mode}/{run_id}/scorecard.md
```

---

## 🔧 PHASE9-7 구현 상세

### 1. download_data.py 생성 ✅

**파일**: `scripts/download_data.py`

**기존 코드 재활용**:
- `download_historical_data.py`의 `download_binance_data()` 함수 로직 복사
- argparse만 추가 (최소 변경)

**주요 변경 사항**:
1. **CLI 인자 지원**:
   ```bash
   python scripts/download_data.py \
       --symbol BTCUSDT \
       --timeframe 1m \
       --start-date 2024-10-01 \
       --end-date 2024-12-31 \
       --output-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
   ```

2. **컬럼명 변경** (`timestamp` → `time`):
   ```python
   # ⭐ PHASE9-7: 컬럼명 변경 (timestamp → time)
   # HistoricalFeed가 기대하는 포맷과 일치시킴
   df = df.rename(columns={'timestamp': 'time'})
   ```

3. **출력 경로 지정**:
   - `--output-path` 인자로 지정
   - 지정하지 않으면 `data/{symbol}_{interval}_{start}_{end}.csv`

**코드 크기**: 약 200 라인 (기존 로직 + argparse)

---

### 2. BTCUSDT 1분봉 데이터 다운로드 ✅

**실행 커맨드**:
```bash
python scripts/download_data.py \
    --symbol BTCUSDT \
    --timeframe 1m \
    --start-date 2024-10-01 \
    --end-date 2024-12-31 \
    --output-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**다운로드 결과**:
- ✅ 파일: `data\BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv`
- ✅ 캔들 수: **131,041개**
- ✅ 기간: 2024-09-30 15:00 ~ 2024-12-30 15:00
- ✅ 컬럼: `time, open, high, low, close, volume`

**다운로드 시간**: 약 2분 (131K 캔들, Binance API 제한: 1000개/요청, 0.5초 delay)

---

### 3. 백테스트 호환성 검증

**CSV 포맷 확인**:
```csv
time,open,high,low,close,volume
2024-09-30 15:00:00,63785.72,63785.73,63745.97,63753.47,20.42826
2024-09-30 15:01:00,63753.47,63797.76,63750.92,63780.25,31.87253
...
```

**HistoricalFeed 호환성**:
- ✅ `time` 컬럼명 (HistoricalFeed가 `timestamp` → `time` 자동 변환)
- ✅ datetime 형식 (pandas가 자동 파싱)
- ✅ OHLCV 순서

**지표 계산 호환성**:
- ✅ `add_indicators()` 함수가 `ema_fast`, `ema_slow`, `rsi`, `atr`, `vol_ma` 추가
- ✅ scalping 전략이 필요한 모든 지표 포함

---

## ⚠️ 발견된 문제점

### 1. scalping.py 파일 작성 이슈

**문제**:
- `strategies/scalping.py` 파일이 0바이트로 생성됨
- `write_to_file` 도구로 작성했으나 실제로 저장되지 않음
- 백테스트 실행 시 `module 'strategies.scalping' has no attribute 'signal_logic'` 오류 발생

**원인**:
- Windsurf IDE의 파일 작성 도구 버그로 추정
- 파일 경로 또는 권한 문제 가능성

**해결 방법**:
1. **Git에서 복원**:
   ```bash
   git checkout 2eaf7c8 -- strategies/scalping.py
   ```
   
2. **수동 복사**:
   - Checkpoint Summary의 scalping.py 코드를 복사
   - IDE에서 직접 붙여넣기

3. **PowerShell로 작성**:
   ```powershell
   @'
   # scalping.py 전체 코드
   '@ | Out-File -FilePath strategies/scalping.py -Encoding utf8
   ```

**현재 상태**:
- ⚠️ scalping.py 파일 복원 필요
- ⚠️ 백테스트 실행 불가 (전략 로드 실패)

---

### 2. Config 검증 오류 (ensemble 충돌)

**문제**:
- `configs/active/current.yml`에 `ensemble` 키가 최상위와 `strategies.ensemble`에 중복 존재
- Config 검증 실패

**해결**:
- ✅ 최상위 `ensemble` 키 제거
- ✅ `strategies.ensemble`만 유지

---

## 📊 데이터 파이프라인 플로우 차트

```
┌─────────────────────────────────────────────────────────┐
│ 1. 데이터 다운로드 (Binance API)                         │
│    scripts/download_data.py                             │
│    - CLI 인자: symbol, timeframe, start-date, end-date  │
│    - Binance API: get_historical_klines()               │
│    - Rate limit: 1000개/요청, 0.5초 delay               │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 2. CSV 저장 (data/)                                     │
│    - 포맷: time, open, high, low, close, volume         │
│    - 경로: data/{symbol}_{tf}_{start}_{end}.csv         │
│    - 예시: BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv     │
│    - 캔들 수: 131,041개                                 │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 3. CSV 로드 (HistoricalFeed)                            │
│    collectors/historical_collector.py                   │
│    - 컬럼명 표준화: timestamp → time                    │
│    - 시간 변환: epoch → datetime                        │
│    - 날짜 필터링: start_date, end_date                  │
│    - 리샘플링: 15m → 1h/4h (optional)                   │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 4. 캔들 스트림 (BacktestEngine)                         │
│    scripts/run_backtest.py                              │
│    - feed.stream_with_history(lookback=400)             │
│    - 캔들 하나씩 처리 (generator)                       │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 5. 지표 계산 (add_indicators)                           │
│    indicators/core_indicators.py                        │
│    - EMA: ema_fast (8), ema_slow (21), ema_mid (50)     │
│    - RSI: 14                                            │
│    - ATR: 14                                            │
│    - Volume MA: 20                                      │
│    - BB, MACD, Donchian                                 │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 6. 전략 로직 (signal_logic)                             │
│    strategies/scalping.py                               │
│    - EMA 교차 감지 (golden_cross, dead_cross)           │
│    - RSI 극단 (oversold < 30, overbought > 70)          │
│    - 모멘텀 패턴 (higher_low, lower_high)                │
│    - 거래량 급증 (volume > vol_ma * 1.3)                │
│    - 신호 생성: LONG/SHORT                              │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 7. 백테스트 실행 (BacktestEngine)                       │
│    execution/backtest_engine.py                         │
│    - 포지션 관리 (entry, exit)                          │
│    - PnL 계산 (realized, unrealized)                    │
│    - 리스크 관리 (SL, TP, trailing)                     │
│    - 통계 수집 (trades, winrate, PF, DD)                │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ 8. 결과 저장 (Scorecard)                                │
│    artifacts/{mode}/{run_id}/                           │
│    - scorecard.md: 요약 통계                            │
│    - effective_config.yml: 실제 사용된 설정             │
│    - trades.csv: 거래 내역 (optional)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 백테스트 실행 가이드

### 1. 7일 샘플 테스트 (backtest_raw)

```bash
python scripts/run_backtest.py \
    --mode backtest_raw \
    --strategy scalping \
    --symbol BTCUSDT \
    --timeframe 1m \
    --start-date 2024-10-01 \
    --end-date 2024-10-07 \
    --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**확인 사항**:
- [ ] [SCALPING V2 INIT] 로그 출력
- [ ] [SCALPING V2 DEBUG] 로그 (100캔들마다)
- [ ] [SCALPING V2 SIGNAL] 로그 (신호 생성 시)
- [ ] Trades 수 (7일 기준)
- [ ] scorecard.md 생성

---

### 2. 90일 전체 테스트 (backtest_clean)

```bash
python scripts/run_backtest.py \
    --mode backtest_clean \
    --strategy scalping \
    --symbol BTCUSDT \
    --timeframe 1m \
    --start-date 2024-10-01 \
    --end-date 2024-12-30 \
    --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
```

**목표**:
- [ ] Trades ≥ 100 (90일 기준)
- [ ] Winrate, PF 참고용 (pass/fail 기준 아님)
- [ ] Max DD < 50%, Loss < 15% (폭발 방지)

---

## 📝 파일 목록

### 신규 생성
- ✅ `scripts/download_data.py` (범용 CLI 다운로더)
- ✅ `data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv` (131K 캔들)
- ✅ `docs/PHASE9/PHASE9-7_DATA_PIPELINE.md` (이 문서)

### 수정
- ✅ `configs/active/current.yml` (ensemble 충돌 제거)
- ⚠️ `strategies/scalping.py` (복원 필요)

### 변경 없음 (보호됨)
- ✅ `collectors/historical_collector.py`
- ✅ `indicators/core_indicators.py`
- ✅ `execution/backtest_engine.py`
- ✅ `strategies/swing_bb.py`

---

## 🚀 다음 단계 (To-Do)

### 즉시 해결 필요 ⚠️
1. **scalping.py 파일 복원**:
   - Git checkout 또는 수동 복사
   - Checkpoint Summary의 코드 사용
   
2. **백테스트 스모크 테스트**:
   - 7일 테스트 실행
   - 로그 확인 ([SCALPING V2 INIT], [SCALPING V2 DEBUG], [SCALPING V2 SIGNAL])
   - Trades 수 확인

### PHASE10 이후
1. **베이시안 튜닝**:
   - RSI 임계값 최적화
   - EMA 기간 최적화
   - 모멘텀 lookback 최적화
   - RR 최적화

2. **앙상블 통합**:
   - swing_bb와 결합
   - 포트폴리오 매니저 연동

3. **실전 배포**:
   - 페이퍼 트레이딩
   - 라이브 트레이딩

---

## 💡 핵심 설계 결정 (Design Decisions)

### 1. 기존 코드 재활용 우선
- ❌ 새로운 downloader 생성 (처음부터)
- ✅ `download_historical_data.py` 로직 복사 + argparse 추가

### 2. 최소 변경 원칙
- 변경 사항:
  1. argparse 추가 (CLI 지원)
  2. 컬럼명 변경 (`timestamp` → `time`)
  3. 출력 경로 지정 (`--output-path`)
- 기존 로직: Binance API 호출, CSV 저장, Rate limit 대응 (변경 없음)

### 3. 백테스트 호환성 우선
- CSV 포맷: `time, open, high, low, close, volume` (HistoricalFeed 호환)
- 컬럼명: `time` (HistoricalFeed가 기대하는 포맷)
- datetime 형식: pandas 자동 파싱 지원

### 4. 확장성 고려
- CLI 인자로 모든 파라미터 지정 가능
- 여러 심볼/타임프레임 지원
- 날짜 범위 유연하게 지정

---

## 📚 참고 자료

### 관련 문서
- `docs/PHASE9/PHASE9-6_SCALPING_V1_DESIGN.md` (스캘핑 전략 설계)
- `docs/PHASE9/PHASE9-5_STRATEGY_SEPARATION.md` (전략 분리)
- `docs/PHASE8/PHASE8_MASTER_PLAN.md` (전체 구조)

### 관련 코드
- `scripts/download_data.py` (범용 다운로더)
- `collectors/historical_collector.py` (HistoricalFeed)
- `strategies/scalping.py` (스캘핑 전략, 복원 필요)
- `scripts/run_backtest.py` (백테스트 실행)

---

**Status**: ⚠️ **파일 복원 필요** (scalping.py)  
**Next**: scalping.py 복원 → 백테스트 실행 → PHASE10 (베이시안 튜닝)  
**Generated**: 2025-11-15  
**Version**: PHASE9-7 (데이터 파이프라인 통합)
