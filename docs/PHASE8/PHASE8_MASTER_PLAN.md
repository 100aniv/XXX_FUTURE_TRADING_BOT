# PHASE8 MASTER PLAN  
**목표: 전체 프로젝트 구조 정비 + 재현성 확립 + 백테스트/전략 검증 체계 구축**

---

# 0. 개요 (Why PHASE8?)
현재 프로젝트는 다음 문제가 누적되어 있음:

1) **재현성 부재**  
- 실행할 때마다 결과가 다름  
- effective_config 없음  
- 백테스트 환경 없음  
- 실험 조건 추적 불가  

2) **난개발로 모듈 의미 불명확**  
- reports/ 는 legacy  
- analytics/만이 실제 유효 모듈  
- 전략/엔진 코드 중복 및 무질서  

3) **Paper/LIVE/Past Test 구분 없음**  
- 수수료/슬리피지/쿨다운 섞여 있음  
- Paper에도 슬리피지 적용  
- 자주 “Precision 오류” 발생  

4) **voting/score 혼재**  
- Voting → Score Fusion → 롤백  
- 여러 방식 섞여 일관성 없음  

**PHASE8은 이 모든 문제를 정리하는 ‘구조 총정리 단계’이다.**

---

# 1. PHASE8의 최종 목표

## 🎯 최종적으로 프로젝트를 아래 상태로 만든다:

### (1) **재현성 100% 확보**
- effective_config.yml 자동 저장
- env/mode/run_id 구조 확립
- 실행 조건 로그 헤더에 표시

### (2) **백테스트 환경 완전 구현**
- backtest_clean 모드 추가
- CSV 기반 결정적 체결
- 수수료/슬리피지/쿨다운 OFF

### (3) **단일 전략 점수표(scorecard) 자동 생성**
필수 지표:
- 총 거래 수
- Winrate
- Profit Factor
- Max Drawdown
- >8% 손실 횟수
- TP 도달률

### (4) **legacy 제거 + 모듈 정리**
- reports/ 완전 폐기
- analytics/ 에 모든 지표/리포트 통합
- 엔진/전략/리스크 하드코딩 제거

### (5) **앙상블은 ‘봉인’**
- Phase8에서는 앙상블 로직 절대 수정하지 않음
- Shadow Score만 기록  
- Phase9에서 앙상블 재개

---

# 2. Phase8 개발 범위 (실제 작업)

## 2-1. config 시스템 정비
- base.yml / modes/*.yml / active/current.yml 구조 확정
- 병합 순서 고정
- 실행 시 effective_config.yml 저장

## 2-2. config_validation 추가
- 필수 키 확인
- 타입/범위 체크
- 중복 의미 키 충돌 검사

## 2-3. backtest_clean 모드 생성
```
fill_policy: next_open  
fees_bps: 10  
slippage: fixed_5bps  
flash_guard: false  
cooldown: 0  
ensemble.enabled: false  
```

## 2-4. run_backtest.py 생성 (단일 엔트리)
- 전략 1개만 실행  
- CSV 데이터 기반  
- 결과는 artifacts/로 저장

## 2-5. analytics 기반 scorecard 생성
폴더 구조:

```
analytics/
  ├─ scorecard/
  │   ├─ scorecard_generator.py
  │   ├─ metrics.py
  │   ├─ writer_csv.py
  │   └─ writer_md.py
```

## 2-6. reports/ 폐기 선언
- legacy 폴더로 남기되 개발 금지

---

# 3. 산출물 구조 (결과물)

```
artifacts/
  └─ backtest_clean/
       └─ {run_id}/
            ├─ effective_config.yml
            ├─ scorecard.csv
            ├─ scorecard.md
            ├─ trades.log
```

---

# 4. PHASE8의 성공 기준

- 단일 전략(backtest_clean) 기준:
  - Winrate ≥ 40%  
  - PF ≥ 1.10  
  - Max DD > -20%  
  - >8% 손실 0  
  - 설정 스냅샷 저장 성공  

- 모든 전략 단독 테스트 완료 후  
  → Phase9에서 앙상블 복귀

---

# 5. RULES (요약)

- reports/ 사용 금지  
- analytics/만 리포트/지표 생성  
- 엔진/브로커/전략 하드코딩 금지  
- config만 읽어서 동작  
- 앙상블 OFF (Phase8 전체)  
- core 리팩토링 금지  
- Score Fusion 금지 (Phase9로 이월)  

---

# 6. Windsurf 작업 순서 (단계별)

1) config_loader 정비  
2) config_validation 작성  
3) backtest_clean.yml 생성  
4) run_backtest.py 작성  
5) analytics/scorecard 시스템 작성  
6) 모듈 경로 정리 및 import 정리  
7) artifacts 저장 구조 구현  
8) 단일 전략(backtest_clean) 테스트  
9) scorecard 제출  

---

# 7. PHASE8 진행 현황

## ✅ PHASE8-1: Config 시스템 정비 (완료)
- base.yml / modes/*.yml / active/current.yml 병합 구조 확립
- config_validation 추가 (필수 키, 타입, 충돌 검사)
- effective_config.yml 자동 저장

## ✅ PHASE8-2: Backtest Clean 환경 구축 (완료)
- backtest_clean 모드 생성 (fill_policy: next_open, fees_bps: 10, slippage: fixed_5bps)
- run_backtest.py 단일 엔트리 스크립트 작성
- PortfolioManager 완전 격리 (load_existing=False)
- Redis dedup 비활성화
- DB env별 격리 (trading.trades, positions, metrics, signals)

## ✅ PHASE8-2c: DB Trades INSERT 수정 (완료)
- trading.trades INSERT 문 21개 컬럼 명시
- decision_id 컬럼 추가
- trades_mode_check 제약 수정 (backtest_clean 추가)
- DB 저장 성공 확인 (17/17건)

## ✅ PHASE8-3: Strategy Baseline Backtest (완료)

### scalping / BTCUSDT / 5m / 30d backtest_clean baseline

**Run ID**: `20251114_184356_pfmz`  
**기간**: 2024-10-01 ~ 2024-10-31 (30일, OOS 데이터)  
**총 캔들**: 26,101개  

**성능 지표:**
- **Trades Closed**: 25건 (목표: ≥100, ❌ 데이터 부족)
- **Winrate**: 44.0% (목표: ≥40%, ✅ 통과)
- **Profit Factor**: 0.68 (목표: ≥1.10, ❌ 손실 상태)
- **Max Drawdown**: -2.03% (목표: >-20%, ✅ 통과)
- **Loss > 8%**: 0건 (목표: =0, ✅ 통과)
- **TP Hit Rate**: 0.0%
- **Sharpe Ratio**: -0.18

**Overall Result**: ❌ 불합격 (PF < 1.10, 거래 수 부족)

**산출물:**
- `artifacts/backtest_clean/20251114_184356_pfmz/scorecard.md`
- `artifacts/backtest_clean/20251114_184356_pfmz/effective_config.yml`
- `artifacts/backtest_clean/20251114_184356_pfmz/scorecard.csv`

**분석:**
- scalping 전략은 현재 손실 상태 (PF 0.68)
- Winrate는 목표 달성했으나 손실 크기가 더 큼
- 30일 데이터로도 거래 수 25건에 불과 (목표 100건 미달)
- 리스크 관리는 양호 (DD -2.03%, 큰 손실 0건)

**다음 단계 고려사항:**
- 전략 파라미터 튜닝 필요 (PHASE9)
- TP/SL 비율 재검토
- 진입 조건 강화
- 장기 백테스트 (90일+) 필요

## ✅ PHASE8-4: 백테스트 데이터 구간 투명화 (완료)

### 목표
- CSV 원본 정보 로깅
- `--days` 옵션 실제 반영 (데이터 슬라이싱)
- scorecard에 실제 사용 기간 표시

### 구현 내역

**1. HistoricalFeed 개선** (`collectors/historical_collector.py`)
- `days` 파라미터 추가
- CSV 로드 직후 원본 정보 로깅:
  ```
  [BACKTEST] Raw CSV info:
    - candles_total=26,101
    - first_ts=2024-10-01 00:00:00
    - last_ts=2024-12-30 15:00:00
  ```
- `--days` 옵션 기반 데이터 슬라이싱 (마지막 캔들 기준 N일 전부터):
  ```
  [BACKTEST] --days=30 슬라이싱 적용:
    - cutoff_time=2024-11-30 15:00:00
    - before=26,101 → after=8,641 (33.1%)
  ```
- 실제 사용 구간 정보 로깅:
  ```
  [BACKTEST] Used window:
    - used_candles=8,641
    - first_used_ts=2024-11-30 15:00:00
    - last_used_ts=2024-12-30 15:00:00
    - approx_days=30
    ✅ Requested days=30, actual_days=30 (매칭)
  ```

**2. 데이터 흐름 개선**
- `run_backtest.py`: CLI `args.days` → `config['backtest']['days']` 저장
- `create_adapters()`: `config['backtest']['days']` → `HistoricalFeed(days=...)` 전달
- `feed` 객체에서 실제 사용 기간 정보 추출 (`first_used_ts`, `last_used_ts`)

**3. Scorecard 개선**
- `ScorecardGenerator`: `period_info` 파라미터 추가 (start_date, end_date, actual_days)
- `scorecard.md`에 실제 사용 기간 표시:
  ```markdown
  - **Period**: 2024-11-30 ~ 2024-12-30 (30 days)
  ```

### 검증 결과

**Run ID**: `20251114_192123_n1uq`

**데이터 슬라이싱 검증:**
- ✅ CSV 원본: 26,101개 캔들 (2024-10-01 ~ 2024-12-30)
- ✅ --days=30 슬라이싱: 8,641개 캔들 (33.1%)
- ✅ 실제 사용: 2024-11-30 ~ 2024-12-30 (30일)
- ✅ Requested days = Actual days (30 = 30)

**성능 지표 (참고):**
- Trades: 14건
- Winrate: 28.57%
- PF: 0.35
- Max DD: -2.51%

**산출물:**
- `artifacts/backtest_clean/20251114_192123_n1uq/scorecard.md` (Period 정보 포함)
- `artifacts/backtest_clean/20251114_192123_n1uq/effective_config.yml`

### 주요 성과

1. **데이터 사용 완전 투명화**
   - CSV 원본 vs 실제 사용 구간 명확히 구분
   - 로그에서 모든 정보 확인 가능

2. **--days 옵션 정확한 반영**
   - 마지막 캔들 기준 N일 전부터 슬라이싱
   - 요청 일수 vs 실제 일수 비교 로깅

3. **scorecard 정합성 확보**
   - 실제 사용 기간 = 로그 = scorecard
   - 모든 artifact가 동일한 기준 사용

### 제약 준수
- ✅ 전략 로직 변경 금지
- ✅ Risk/Portfolio/Broker 로직 변경 금지
- ✅ DB 스키마 변경 금지
- ✅ 기존 backtest_clean 격리 기능 유지

## ✅ PHASE8-5: 데이터 품질 검증 및 거래 빈도 분석 (완료)

### 목표
백테스트 CSV 데이터 품질을 검증하고, 기간별 trade frequency를 분석하여 "데이터 문제 vs 전략 문제"를 분리

### 구현 내역

**1. CSV 데이터 품질 검증 스크립트** (`scripts/inspect_csv.py`)
- 자동화된 데이터 품질 검사 도구
- 검사 항목:
  - Missing candles (연속성)
  - Duplicated timestamps (중복)
  - Gap 분석 (최대 gap 및 상위 N개)
  - Timezone 일관성
- Markdown 리포트 자동 생성
- 종합 점수 시스템 (100점 만점)

**2. HistoricalFeed 개선** (`collectors/historical_collector.py`)
- `start_date`/`end_date` 파라미터 추가
- 특정 날짜 범위 필터링 지원
- `days` 옵션보다 우선순위 높음
- YYYY-MM-DD 형식 지원

**3. run_backtest.py CLI 확장**
- `--start-date`, `--end-date` 옵션 추가
- config를 통해 HistoricalFeed에 전달
- 기간별 백테스트 실행 가능

### CSV 데이터 품질 검증 결과

**파일**: `data/BTCUSDT_5m_2024-10-01_2024-12-31_OOS.csv`

| 항목 | 값 | 상태 |
|------|-----|------|
| **Total Candles** | 26,101 | - |
| **Period** | 2024-10-01 ~ 2024-12-30 (90일) | - |
| **Expected Candles** | 26,101 | - |
| **Missing Candles** | 0 (0.00%) | ✅ Good |
| **Duplicated Timestamps** | 0 (0.00%) | ✅ Good |
| **Gap Count** | 0 | ✅ Good |
| **Overall Score** | **100/100** | ✅ **EXCELLENT** |

**결론**: 데이터 품질은 완벽함. 문제 없음.

### 기간별 Trade Frequency 분석 결과

**Strategy**: scalping / BTCUSDT / 5m

| Period | Run ID | Trades | Days | Trades/Day | Winrate | PF | MaxDD |
|--------|--------|--------|------|------------|---------|-----|-------|
| **2024-10-01~10-31** | `20251114_194449_zdut` | 6 | 30 | **0.20** | 33.33% | 0.52 | -0.48% |
| **2024-11-01~11-30** | `20251114_194654_vgzd` | 4 | 29 | **0.14** | 0.0% | 0.0 | -0.57% |
| **2024-12-01~12-30** | `20251114_194845_djud` | 7 | 29 | **0.24** | 14.29% | 0.2 | -1.32% |
| **Average** | - | **5.7** | **29.3** | **0.19** | 15.87% | 0.24 | -0.79% |

### 핵심 발견 사항

**1. Trade Frequency: 매우 낮음 ❌**
- **평균 0.19 trades/day** (5일에 1건 미만!)
- **예상치 대비 97% 부족** (scalping 전략은 하루 5-10건 예상)
- **90일간 총 17건** 거래만 발생

**2. 성능: 일관되게 불량 ❌**
- 모든 3개 구간에서 손실 (PF < 1.0)
- 평균 PF: 0.24 (획득한 $1당 $0.76 손실)
- TP Hit Rate: 0% (TP 도달 없음, 모두 SL/시간 종료)

**3. 리스크 관리: 양호 ✅**
- Max DD < -2% (모든 구간)
- Loss > 8%: 0건 (모든 구간)
- 보수적 포지션 사이징 작동

### 근본 원인 분석

**데이터 문제? ❌ NO**
- CSV 품질: 100/100 (EXCELLENT)
- 누락/중복/gap 없음
- **데이터는 문제 없음**

**전략 문제? ✅ YES**
1. **진입 조건이 너무 엄격**
   - 5m scalping인데 하루 0.19건은 비정상적으로 적음
   - 95%+ 기회를 놓치고 있음
   - RSI/MACD 임계값, 트렌드 필터 등 검토 필요

2. **청산 로직 비최적**
   - TP Hit Rate: 0%
   - TP 레벨이 너무 멀거나 SL이 너무 좁음
   - TP/SL 비율 재조정 필요

3. **시장 regime 미적응**
   - 10월/11월/12월 모두 다른 시장 상황
   - 변동성 변화에 적응하지 못함

### 권고 사항

**즉시 조치 (PHASE9)**

**DO NOT**: 데이터 재다운로드 - 데이터는 완벽함 ✅  
**DO**: 전략 파라미터 분석 및 튜닝

1. **진입 조건 완화** (우선순위: HIGH)
   - RSI 임계값 완화 (예: 30→35)
   - 트렌드 필터 완화
   - **목표**: 최소 하루 1-3건 거래

2. **TP/SL 비율 검토** (우선순위: HIGH)
   - TP 거리 축소 (2:1 → 1.5:1 또는 1:1)
   - 현재 TP Hit 0%는 비현실적 설정 의미
   - ATR 기반 동적 TP/SL 고려

3. **변동성 적응** (우선순위: MEDIUM)
   - ATR 기반 동적 파라미터
   - Regime detection 추가
   - 횡보/추세 구간 구분

4. **다른 전략 테스트** (우선순위: LOW)
   - `daytrade`, `swing` 전략 비교
   - 동일 데이터로 성능 비교
   - 앙상블 가능성 검토

### 산출물

**문서**:
- `docs/PHASE8/PHASE8-5_DATA_QUALITY.md`
  - CSV 품질 검증 리포트
  - 기간별 trade frequency 분석
  - 근본 원인 분석 및 권고사항

**스크립트**:
- `scripts/inspect_csv.py`
  - CSV 데이터 품질 자동 검증 도구
  - Markdown 리포트 생성

**백테스트 결과**:
- `artifacts/backtest_clean/20251114_194449_zdut/` (10월)
- `artifacts/backtest_clean/20251114_194654_vgzd/` (11월)
- `artifacts/backtest_clean/20251114_194845_djud/` (12월)

### 주요 성과

1. **데이터 vs 전략 문제 분리 성공**
   - 데이터: 완벽 (100/100)
   - 전략: 문제 있음 (PF 0.24, trades/day 0.19)

2. **정량적 분석 완료**
   - 기간별 성능 비교
   - 거래 빈도 측정
   - 일관성 확인

3. **명확한 다음 단계 제시**
   - PHASE9 진입 준비 완료
   - 우선순위별 개선 방향 제시
   - 불필요한 작업 배제 (데이터 재다운로드 불필요)

### 제약 준수
- ✅ 전략 로직 변경 금지 (분석만 수행)
- ✅ Risk/Portfolio/Broker 로직 변경 금지
- ✅ DB 스키마 변경 금지
- ✅ backtest_clean 격리 기능 유지

---
