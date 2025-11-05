# WFA 블록 테스트 결과 요약
**생성일**: 2025-10-23  
**전략**: REVERSION v2  
**타임프레임**: 15m  
**데이터 버전**: data@20251023_v2

---

## 데이터 준비 (완료 ✅)

### 6개 대표 레짐 블록 (BACKTEST_PERIODS.md 준수)

| 레짐 | 기간 | 캔들 수 (15m) | 파일 |
|------|------|---------------|------|
| 2018 약세장 | 2018-01-01 ~ 2018-12-31 | 34,683 | BTCUSDT_15m_bear_2018.csv |
| 2020 코로나 | 2020-02-01 ~ 2020-06-30 | 14,342 | BTCUSDT_15m_covid_2020.csv |
| 2020-2021 반감기 강세 | 2020-05-01 ~ 2021-04-30 | 34,868 | BTCUSDT_15m_halving20_bull.csv |
| 2022 루나/FTX | 2022-04-01 ~ 2022-12-31 | 26,305 | BTCUSDT_15m_luna_ftx_2022.csv |
| 2023-2024 ETF | 2023-10-01 ~ 2024-03-31 | 17,473 | BTCUSDT_15m_etf_anticip_24.csv |
| 2024 반감기 직후 | 2024-04-01 ~ 2024-09-30 | 17,473 | BTCUSDT_15m_halving24_post.csv |

### 16개 WFA 블록 생성 (완료 ✅)

**구조**: Train 8주 (5,376 캔들) + OOS 3주 (2,016 캔들)

| 레짐 | WFA 블록 수 | Train 파일 예시 |
|------|-------------|----------------|
| 2018 약세 | 4개 | BTCUSDT_15m_2018_WFA01~04_TRAIN.csv |
| 2020 코로나 | 1개 | BTCUSDT_15m_2020_WFA01_TRAIN.csv |
| 반감기 강세 | 4개 | BTCUSDT_15m_bull_WFA01~04_TRAIN.csv |
| 루나/FTX | 3개 | BTCUSDT_15m_2022_WFA01~03_TRAIN.csv |
| ETF | 2개 | BTCUSDT_15m_24_WFA01~02_TRAIN.csv |
| 반감기 직후 | 2개 | BTCUSDT_15m_post_WFA01~02_TRAIN.csv |

---

## 백테스트 결과 (3개 대표 블록)

### Baseline 설정

**전략**: REVERSION v2 (성공 패턴 기반)
- **엔트리 조건**:
  - LONG: RSI < 30 + BB 하단 터치 + EMA 역배열
  - SHORT: RSI > 70 + BB 상단 터치 + EMA 순배열
- **익절/손절**:
  - Stop: 1.5 ATR
  - RR: 2.0
  - Trailing: 2.5 ATR
  - TP 분할: 30/40/30
- **리스크**:
  - 거래당: 0.5%
  - 연속 손실: 999 (백테스트용)

### 테스트 결과

| 블록 | 레짐 | 캔들 수 | 거래 | 승률 | ROI | 상태 |
|------|------|---------|------|------|-----|------|
| 2018_WFA01 | 약세장 | 5,347 | 90건 | 25.2% | -1,738% | ❌ 실패 |
| bull_WFA01 | 강세장 | 5,347 | 72건 | 25.4% | -1,857% | ❌ 실패 |
| 2022_WFA01 | 루나/FTX | 5,347 | 78건 | 25.4% | -1,862% | ❌ 실패 |

### 공통 문제점

1. **승률**: 25% (매우 낮음, 목표: 50%+)
2. **ROI**: -1,700% ~ -1,900% (치명적)
3. **레짐 무관**: 약세/강세/스트레스 모두 실패
4. **근본 원인**: "성공 패턴"이 현재 데이터에서 작동하지 않음

---

## 게이트 기준 비교 (TEST_SCENARIO.md)

| 지표 | 목표 | 2018_WFA01 | bull_WFA01 | 2022_WFA01 | 상태 |
|------|------|------------|------------|------------|------|
| OOS Expectancy | ≥ 0.10R | - | - | - | ⏸️ 미테스트 |
| PF | ≥ 1.3 | ~0.42 | ~0.42 | ~0.42 | ❌ 실패 |
| MDD | ≤ -20% | -1,738% | -1,857% | -1,862% | ❌ 실패 |
| 승률 | ≥ 50% | 25.2% | 25.4% | 25.4% | ❌ 실패 |
| 연속 손실 | ≤ 6 | 99 | 99 | 99 | ❌ 실패 |

**결론**: **모든 게이트 기준 불통과** ❌

---

## 버그 수정 내역

### 1. main.py - data_file 우선 처리 추가

**문제**: config.yml의 `data_file` 설정을 무시하고 패턴 매칭으로 fallback  
**해결**: data_file 설정 우선 확인 로직 추가 (Line 141-162)

```python
# ⭐ data_file 설정 우선 확인
data_file = backtest_cfg.get('data_file')
if data_file:
    csv_path = Path(data_dir) / data_file
    if not csv_path.exists():
        # 절대 경로 시도
        csv_path = Path(data_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"❌ data_file 없음: {data_file}")
else:
    # 기간 기반 선택 (기존 로직)
    ...
```

---

## 다음 단계 (TEST_SCENARIO.md 준수)

### 우선순위 1: Exits 튜닝 (손익비 확보)

**현재**: stop.k=1.5, trailing.k=2.5, TP(30/40/30)  
**테스트 후보**:
- `stop.k`: 1.2 / 1.6 / 1.8 / 2.0 (LHS 샘플링)
- `trailing.k`: 2.0 / 2.5 / 3.0 / 3.5
- `move_to_break_even_at_r`: 0.6 / 0.8 / 1.0
- `TP 분할`: (20/30/50), (25/50/25), (40/40/20)

### 우선순위 2: Entries 완화 (거래 빈도 증가)

**현재**: RSI 30/70 (극단적)  
**테스트 후보**:
- `rsi_threshold`: 25 / 28 / 32 / 35
- `bb_touch_pct`: 1.003 / 1.005 / 1.008 / 1.010
- `volume_spike`: true / false
- `cooldown_candles`: 10 / 15 / 20

### 우선순위 3: 레짐별 파라미터 분기

**가설**: 약세/강세/레인지 각각 다른 파라미터 필요  
**방법**: 레짐 인식 → 파라미터 세트 자동 전환

---

## 시사점

1. **"성공 패턴" 재검증 필요**
   - 소규모 샘플(12건)에서 100% 승률 ≠ 일반화 성능
   - 과적합 가능성 높음

2. **TEST_SCENARIO.md 원칙 준수**
   - ✅ 고정 레이어 잠금 (fees/risk/execution)
   - ✅ 단일 전략 × 단일 심볼 (BTCUSDT)
   - ⏭️ Exits 먼저 튜닝 → Entries 나중

3. **BACKTEST_PERIODS.md 완전 준수**
   - ✅ 6개 대표 레짐 블록
   - ✅ 15m 타임프레임
   - ✅ WFA 구조 (Train 8주 + OOS 3주)

4. **현실적 기대치 설정**
   - 첫 사이클에서 게이트 통과는 드묾
   - 반복적 튜닝 및 학습 필요
   - 전략 전면 재설계 고려

---

## 파일 구조

```
data/
├── backtest_periods/          # 원본 레짐 블록
│   ├── BTCUSDT_15m_bear_2018.csv
│   ├── BTCUSDT_15m_covid_2020.csv
│   ├── BTCUSDT_15m_halving20_bull.csv
│   ├── BTCUSDT_15m_luna_ftx_2022.csv
│   ├── BTCUSDT_15m_etf_anticip_24.csv
│   └── BTCUSDT_15m_halving24_post.csv
├── wfa_blocks/                # WFA Train/OOS 블록
│   ├── BTCUSDT_15m_2018_WFA01_TRAIN.csv
│   ├── BTCUSDT_15m_2018_WFA01_OOS.csv
│   ├── ... (32개 파일)
│   └── wfa_blocks_summary.csv
└── download_summary.csv

scripts/
├── download_backtest_periods.py   # 레짐 블록 다운로드
├── create_wfa_from_periods.py     # WFA 블록 생성
├── add_indicators_to_wfa.py       # 지표 계산
└── run_wfa_blocks_sequential.py   # 순차 실행 (개선 필요)
```

---

**생성**: Cycle 2 Day 1 (2025-10-23 22:50)  
**상태**: 데이터 준비 완료, Baseline 실패, Exits 튜닝 대기
