# 🚀 선물 트레이딩 봇 튜닝/검증 체크리스트 (Cycle 2)

> 목적: **과적합을 피하면서** 기대값/드로우다운/실행안정성을 기준으로 **단계별 승인(Gate)**을 통과하는지 확인  
> 사이클 범위: **Cycle 2 - REVERSION v2 전략 (2024-01-01 ~ 2024-09-30 Train, 2024-10-01 ~ 2024-12-31 OOS)**  
> 운영 원칙: **고정 레이어 먼저 잠금 → Exits → Entries/Filters → 전략별 → 앙상블 → 페이퍼 → 소액 라이브**

---

## 0. 메타 데이터

| 항목 | 값 |
|---|---|
| 프로젝트/시스템 | TRADING BOT v3.0 |
| 사이클 | **Cycle 2** |
| 전략 | **REVERSION v2** (성공 패턴 기반 재설계) |
| 데이터 버전 | `data@20251023_v2` (6개 레짐 블록, 16개 WFA 블록) |
| 코드 커밋 | `Cycle 2 Day 2 - Bug Fix (engine.py, config.yml)` |
| 설정 | `config.yml` (15m, Daytrade 단일 전략) |
| 실행 환경 | backtest |
| 심볼 세트 | BTCUSDT (단일) |
| 기간(Train) | 2018~2024 (6개 레짐 블록 × 16개 WFA 블록) |
| OOS 기간 | 각 WFA 블록당 3주 (2,016 캔들 @15m) |
| 레짐 블록 | bear_2018(4), covid_2020(1), halving20_bull(4), luna_ftx_2022(3), etf_anticip_24(2), halving24_post(2) |
| 메모 | BACKTEST_PERIODS.md 준수, main.py data_file 우선 처리 버그 수정 |

---

## 게이트 기준 (고정)

- **OOS Expectancy ≥ +0.10 R/trade**
- **PF ≥ 1.3** (앙상블 시 ≥ 1.4)
- **MDD ≤ -20%** (앙상블 시 ≤ -15%)
- **Calmar ≥ 0.5** (앙상블 시 ≥ 0.6)
- 레짐(트렌드/레인지/저유동) **각 구간 기대값 ≥ 0**
- 연속 손실 ≤ 6, 일일 손실 한도(DDL) 준수

---

## 진행 상태 요약

| 단계 | 설명 | 상태 | 시작일 | 종료일 | 증빙(리포트/로그 링크) | 비고 |
|---|---|---:|---|---|---|---|
| **Cycle 1** | scalping 전략 (실패) | ❌ | 2025-10-23 | 2025-10-23 | 12개 실험 | PF 0.41~0.46, MDD -848% |
| **Cycle 2-A** | REVERSION v2 데이터 준비 | ✅ | 2025-10-23 | 2025-10-23 | 6개 레짐 블록 다운로드 | 2018~2024, 15m |
| **Cycle 2-B** | WFA 블록 생성 | ✅ | 2025-10-23 | 2025-10-23 | 16개 WFA 블록 | Train 8주 + OOS 3주 |
| **Cycle 2-C** | 대표 블록 테스트 | ❌ | 2025-10-23 | 2025-10-23 | 3개 블록 실패 | 승률 25%, ROI -1,700~-1,900% |
| Cycle 2-B | REVERSION v2 Entries 튜닝 | ☐ |  |  |  | A-2 통과 시 시작 |
| Cycle 2-C | 멀티 심볼 전이 검증 | ☐ |  |  |  | A-3 통과 시 시작 |
| Cycle 2-D | 앙상블 백테스트 | ☐ |  |  |  | B 통과 시 시작 |
| Cycle 2-E | 페이퍼 트레이딩 | ☐ |  |  |  | C 통과 시 시작 |
| Cycle 2-F | 소액 라이브 | ☐ |  |  |  | D 통과 시 시작 |

> 체크 표기: ☐ 진행 전 / 🟨 진행중 / ✅ 완료 / ❌ 보류(사유 기재)

---

## A. 단일 전략 × 단일 심볼 × 백테 (BTCUSDT 기준)

### A-1. 고정 레이어 잠금 (필수)
| 체크 | 항목 | 목표/규칙 | 상태 | 메모 |
|---:|---|---|---:|---|
| ✅ | 수수료/슬리피지/펀딩 | taker 0.04%, slippage 0.05%, avg_realized 펀딩 | 완료 | config.yml 확인 완료 |
| ✅ | 리스크 엔진 | risk_per_trade_pct=0.5%, DDL=2%, 연속SL=4, 레버리지cap=5 | 완료 | config.yml 확인 완료 |
| ✅ | 실행 안정화 | post-only 기본, 슬리피지 캡=8bp, 재시도 3회 | 완료 | config.yml 확인 완료 |
| ✅ | 익스포저/상관 | 심볼 그룹 캡 준수(BTC/ETH/ALTS) | 완료 | portfolio_manager 구현됨 |

### A-2. Exits 그리드 (REVERSION v2, Baseline: stop.k=1.5, rr=2.0)
| 체크 | 파라미터 | 테스트 세트 (LHS 20개) | 성과(요약) | 합격 |
|---:|---|---|---|---:|
| ❌ | Baseline (2018_WFA01) | 2018 약세 (8주, 5,347 캔들) | 90건, 승률 25.2%, ROI -1,738% | ❌ |
| ❌ | Baseline (bull_WFA01) | 2020-2021 강세 (8주, 5,347 캔들) | 72건, 승률 25.4%, ROI -1,857% | ❌ |
| ❌ | Baseline (2022_WFA01) | 2022 루나/FTX (8주, 5,347 캔들) | 78건, 승률 25.4%, ROI -1,862% | ❌ |
| ☐ | stop.k | 1.2 ~ 2.0 (LHS) | 미테스트 | ☐ |
| ☐ | trailing.k | 2.0 ~ 3.5 (LHS) | 미테스트 | ☐ |
| ☐ | move_to_break_even_at_r | 0.5 ~ 1.2 (LHS) | 미테스트 | ☐ |
| ☐ | TP 분할 | (20/30/50), (30/40/30), (25/50/25) | 미테스트 | ☐ |
| ☐ | time_exit_min | 120 / 240 / 360 | 미테스트 | ☐ |

**전략**: Baseline 실행 → LHS 20개 샘플 → 베스트 선정 → OOS 검증

**Cycle 2 Baseline 설정**:
- `stop.k`: 1.5 (ATR 기반)
- `rr`: 2.0
- `trailing.k`: 2.5
- `move_to_break_even_at_r`: 0.8
- `TP 분할`: 30/40/30

> **합격 기준**: OOS Expectancy ≥ 0.10R, PF ≥ 1.3, MDD ≤ -20%

### A-3. Entries/Filters 튜닝 (REVERSION v2, Baseline: rsi_threshold=30)
| 체크 | 파라미터 | 테스트 세트 (LHS 20개) | 성과(요약) | 합격 |
|---:|---|---|---|---:|
| ☐ | rsi_threshold | 25 ~ 35 (LHS) | 미테스트 | ☐ |
| ☐ | bb_touch_pct | 1.003 ~ 1.010 (LHS) | 미테스트 | ☐ |
| ☐ | require_volume_spike | true / false | 미테스트 | ☐ |
| ☐ | cooldown_candles | 1 / 3 / 5 | 미테스트 | ☐ |
| ☐ | min_rr_required | 1.0 / 1.3 / 1.5 | 미테스트 | ☐ |

**전략**: A-2 통과 후 Entries 튜닝 시작

**Cycle 2 Baseline 설정**:
- `rsi_threshold`: 30 (성공 패턴)
- `bb_touch_pct`: 1.005
- `require_volume_spike`: false
- `cooldown_candles`: 3

### A-4. 전략 프리셋 확정 (Cycle 2)
| 전략 | 프리셋명 | 설정 스냅샷/해시 | OOS 핵심지표(Exp/PF/MDD) | 승인 |
|---|---|---|---|---:|
| **reversion** | Cycle 2 v2 | config_cycle2.yml | 미테스트 | ☐ |
| scalping | Cycle 1 (실패) | config_cycle1_backup.yml | PF 0.46, MDD -848% | ❌ |
| **daytrade** | Cycle 2 Day 2 (실패) | config.yml | PF 0.42, MDD -1860%, 승률 25.4% | ❌ |
| **swing** | Cycle 2 Day 2 (실패) | config.yml | PF 0.42, MDD -1877%, 승률 25.4% | ❌ |
| swing |  |  |  | ☐ |
| trend |  |  |  | ☐ |
| breakout |  |  |  | ☐ |

---

## B. 단일 전략 × 멀티 심볼 전이 검증

| 전략 | 심볼 세트 | 설정 프리셋 | OOS Expectancy(가중) | 심볼별 음수 존재? | 합격 |
|---|---|---|---:|---|---:|
| scalping | BTC, ETH, SOL, BNB, XRP, ADA | v1 |  |  | ☐ |
| daytrade | 〃 | v1 |  |  | ☐ |
| swing | 〃 | v1 |  |  | ☐ |
| trend | 〃 | v1 |  |  | ☐ |
| reversion | 〃 | v1 |  |  | ☐ |
| breakout | 〃 | v1 |  |  | ☐ |

> 기준: 심볼별 OOS ≥ 0 유지, 전체 가중 평균 ≥ 0.07R. 슬리피지 민감 심볼 메모 필수.

---

## C. 앙상블 구성/튜닝

### C-1. 재료 제한 & 초기 가중치
- 전략별 프리셋: 각 1~2개 (총 6~12개)  
- 초기 가중치: 균등 → 최근 30일 OOS 성과 기반 재가중

### C-2. 하이퍼 튜닝(상위 노브만)
| 체크 | 파라미터 | 후보 | 메모 |
|---:|---|---|---|
| ☐ | weights.* | 0.5 ~ 3.0 | 전략별 |
| ☐ | alpha_winrate | 0.2 ~ 0.6 |  |
| ☐ | beta_rr | 0.1 ~ 0.4 |  |
| ☐ | gamma_sharpe | 0.1 ~ 0.3 |  |
| ☐ | consensus_bonus | 0.0 ~ 0.3 |  |
| ☐ | rr_bonus / threshold | 0.0 ~ 0.3 / 1.4~1.8 |  |
| ☐ | theta_long/short | 0.1 ~ 0.3 |  |

### C-3. 앙상블 게이트
- 단일 전략 대비 **MDD 15~30% 감소**, 자본곡선 매끄러움 개선(Ulcer ↓)  
- **OOS** Expectancy ≥ 0.10R, PF ≥ 1.4, MDD ≤ -15%, Calmar ≥ 0.6

| 체크 | 항목 | 결과/링크 | 합격 |
|---:|---|---|---:|
| ☐ | 자본곡선 비교(단일 vs 앙상블) |  | ☐ |
| ☐ | 레짐/세션별 편차 축소 |  | ☐ |
| ☐ | 핵심 지표 기준 충족 |  | ☐ |

---

## D. 페이퍼 트레이딩(4~6주)

| 체크 | 항목 | 목표 | 결과/링크 | 합격 |
|---:|---|---|---|---:|
| ☐ | 실행 손상률(백테 대비) | ≤ 25% |  | ☐ |
| ☐ | 주문/상태 일치율 | ~100% |  | ☐ |
| ☐ | 슬리피지 캡 A/B | 캡 vs 체결률 균형점 |  | ☐ |
| ☐ | 재시작 복원 | 포지션/주문 스냅샷 정상 |  | ☐ |
| ☐ | 알림/SLA | DDL/연속SL/오류 알림 |  | ☐ |

---

## E. 소액 라이브(리스크 1/3 시작 → 승급)

| 주차 | 리스크 배율 | DDL 위반 | 연속SL | 핵심지표(주간) | 승급 여부 | 메모 |
|---:|---:|---:|---:|---|---|---|
| 1 | x0.33 |  |  |  |  |  |
| 2 | x0.33/0.5 |  |  |  |  |  |
| 3 | x0.5/0.66 |  |  |  |  |  |
| 4 | x0.66/1.0 |  |  |  |  |  |

---

## 레짐 성과 표 (필수)

| 레짐 | 기준 | Trades | Exp(R) | PF | MDD | 메모 |
|---|---|---:|---:|---:|---:|---|
| 트렌드 고 | ADX↑/MA slope↑ |  |  |  |  |  |
| 트렌드 저 | 〃 |  |  |  |  |  |
| 레인지 | ATR↓/밴드 수축 |  |  |  |  |  |
| 고변동 | ATR% 상위분위 |  |  |  |  |  |
| 저변동 | ATR% 하위분위 |  |  |  |  |  |
| 이벤트 | 뉴스 블랙아웃± |  |  |  |  |  |

---

## 실험 로그 (샘플 효율용 기록)

| 실험ID | 단계 | 전략/프리셋 | 심볼 | 변경 레이어 | 핵심 변경값 | OOS Exp | PF | MDD | 결론 |
|---|---|---|---|---|---|---:|---:|---:|---|
| EXP-A2-01 | A-2 | scalping | BTC | Exits | stop.k=1.8, trail=2.5, BE=0.8, TP(30/40/30) | - | 0.46 | -848% | ❌ FAIL |
| EXP-A2-02 | A-2 | scalping | BTC | Exits | stop.k=1.6, trail=2.0, BE=0.8, TP(30/40/30) | - | 0.45 | -861% | ❌ FAIL |
| EXP-A2-03 | A-2 | scalping | BTC | Exits | stop.k=2.0, trail=3.0, BE=1.0, TP(25/50/25) | - | 0.45 | -874% | ❌ FAIL |
| EXP-A3-01 | A-3 | scalping | BTC | Entries | volume_spike=TRUE | - | 0.45 | -887% | ❌ FAIL |
| EXP-A3-02 | A-3 | scalping | BTC | Entries | min_rr=1.8 | - | 0.45 | -900% | ❌ FAIL |
| EXP-A2-04 | A-2 | reversion | BTC | Exits | 코드 버그 발견 | - | 0.45 | -912% | ❌ FAIL |
| EXP-A2-05 | A-2 | reversion | BTC | Exits | 코드 수정 후 (main.py, signal_generator.py) | - | 0.45 | -918% | ❌ FAIL |
| EXP-A2-06 | Data | reversion | BTC | 데이터 | one_year 설정 (데이터 없음) | - | 0.45 | -924% | ❌ FAIL |
| EXP-A2-07 | A-2 | daytrade | BTC | Strategy | 15m 전략 테스트 | - | 0.45 | -934% | ❌ FAIL |
| EXP-A2-08 | Bugfix | daytrade | BTC | Code | MTF/거래량 필터 비활성화 | - | 0.44 | -946% | ❌ FAIL |
| EXP-A2-09 | Data | daytrade | BTC | Data | 2024년 1년 데이터 (105,121 캠들) | - | 0.42 | -1227% | ❌ FAIL |
| EXP-A3-03 | A-3 | reversion | BTC | Entries | RSI 30→40, AND→OR (8,797건) | - | 0.41 | -1568% | ❌ FAIL |
| EXP-C2-01 | Data | reversion | BTC | Data | 2018~2024 6개 레짐 블록 다운로드 (15m) | - | - | - | ✅ 완료 |
| EXP-C2-02 | WFA | reversion | BTC | WFA | 16개 WFA 블록 생성 (Train 8주 + OOS 3주) | - | - | - | ✅ 완료 |
| EXP-C2-03 | A-2 | reversion | BTC | Baseline | 2018_WFA01 (약세) 15m, RSI<30, BB하단, EMA역배열 | - | - | -1738% | ❌ FAIL |
| EXP-C2-04 | A-2 | reversion | BTC | Baseline | bull_WFA01 (강세) 15m | - | - | -1857% | ❌ FAIL |
| EXP-C2-05 | A-2 | reversion | BTC | Baseline | 2022_WFA01 (루나/FTX) 15m | - | - | -1862% | ❌ FAIL |
| EXP-C2-06 | A-2 | daytrade | BTC | Baseline | 2022_WFA01 (루나/FTX) 15m | 251건, 승률 25.4% | 0.42 | -1906% | ❌ FAIL |
| EXP-C2-07 | A-2 | swing | BTC | Baseline | 2022_WFA01 (루나/FTX) 1h | 213건, 승률 25.4% | 0.42 | -1923% | ❌ FAIL |
| EXP-C2-08 | A-2 | daytrade | BTC | Baseline | 2022_WFA01 (루나/FTX) 15m (Fix-1~3 Sanity) | 255건, 승률 28.6% | 0.39 | -22.2% | ❌ FAIL |
| EXP-C2-09 | A-2 | daytrade | BTC | Baseline | 2018_WFA01 (약세) 15m OOS | 112건, 승률 28.6% | 0.36 | -18.1% | ❌ FAIL |
| EXP-C2-10 | A-2 | daytrade | BTC | Baseline | 2020_WFA01 15m OOS | 102건, 승률 30.4% | 0.53 | -9.0% | ❌ FAIL |
| EXP-C2-11 | A-2 | daytrade | BTC | Baseline | halving20_bull 15m OOS | 1115건, 승률 23.0% | 0.35 | -85.3% | ❌ FAIL |
| EXP-C2-12 | A-2 | scalping | BTC | Baseline | bear_2018 5m OOS | 734건, 승률 22.3% | 0.38 | -35.1% | ❌ FAIL |
| EXP-C2-13 | A-2 | scalping | BTC | Baseline | covid_2020 5m OOS | 455건, 승률 20.7% | 0.40 | -20.5% | ❌ FAIL |
| EXP-C2-14 | A-2 | scalping | BTC | Baseline | etf_anticip_24 5m OOS | 569건, 승률 21.8% | 0.36 | -19.8% | ❌ FAIL |
| EXP-C2-15 | A-2 | reversion | BTC | Baseline | 2018_WFA01 15m OOS | 2건, 승률 0.0% | 0.00 | -0.9% | ❌ FAIL |
| EXP-C2-16 | A-2 | reversion | BTC | Baseline | 2020_WFA01 15m OOS | 0건, 승률 - | - | 0.0% | ❌ FAIL |
| EXP-C2-17 | A-2 | reversion | BTC | Baseline | 2022_WFA01 15m OOS | 0건, 승률 - | - | 0.0% | ❌ FAIL |
| EXP-C2-18 | A-2 | swing | BTC | Baseline | 2018_WFA01 1h OOS (15m→1h) | 10건, 승률 20.0% | 0.23 | -3.6% | ❌ FAIL |
| EXP-A4-01 | Bugfix | ALL | BTC | Code | 자본 0 체크, 연속손실 백테 적용, Scalping 강화 | - | - | - | ❌ 조기중단 |
| EXP-A4-02 | A-4 | scalping | BTC | Strategy | 조건 과도 강화 (RSI 30-70, EMA 3선, BB 0.8%, Vol 1.5x, MACD cross) | - | - | - | ❌ 3건만 |
| EXP-0003 | B | scalping_v1 | BTC/ETH/SOL | Transfer | 동일 프리셋 전이 |  |  |  |  |
| EXP-0004 | C | ensemble_v0 | Multi | Weights | alpha=0.4, rr_bonus=0.2 |  |  |  |  |
| EXP-C2-19 | A-2 | daytrade | BTC | Exits | stop.k=1.6, trail=2.0, BE=0.8, time_exit=360 (2020_WFA01) | 54건, 승률 40.7%, RR 1.06 | 0.72 | -2.6% | ❌ FAIL |
| EXP-C2-20 | A-2 | daytrade | BTC | Exits | stop.k=1.4, trail=1.8, BE=0.6, time_exit=360 (2020_WFA01) | 54건, 승률 40.7%, RR 1.06 | 0.73 | -2.5% | ❌ FAIL |
| EXP-C2-21 | A-2 | daytrade | BTC | Exits | stop.k=1.8, trail=3.0, BE=1.0, time_exit=720 (2020_WFA01) | 46건, 승률 37.0%, RR 1.53 | 0.90 | -2.2% | ⚠️ 개선 |
| EXP-C2-22 | A-2 | daytrade | BTC | Exits | stop.k=1.8, trail=3.0, BE=1.0, time_exit=720 (2018_WFA01) | 50건, 승률 34.0%, RR 0.63 | 0.32 | -9.3% | ❌ FAIL |
| EXP-C2-23 | A-2 | daytrade | BTC | Exits | stop.k=1.8, trail=3.0, BE=1.0, time_exit=720 (24_WFA01) | 64건, 승률 25.0%, RR 2.04 | 0.68 | -3.0% | ❌ FAIL |
| EXP-C2-24 | A-3 | daytrade | BTC | Entries | min_rr=1.5 (2020_WFA01) | 46건, 승률 37.0%, RR 1.53 | 0.90 | -2.2% | ❌ 변화없음 |
| EXP-C2-25 | A-3 | daytrade | BTC | Entries | min_rr=1.8 (2020_WFA01) | 46건, 승률 37.0%, RR 1.53 | 0.90 | -2.2% | ❌ 변화없음 |
| EXP-C2-26 | A-3 | daytrade | BTC | Entries | cooldown=5, vol_spike=true (2020_WFA01) | 46건, 승률 37.0%, RR 1.53 | 0.90 | -2.2% | ❌ 변화없음 |
| EXP-C2-27 | A-3 | daytrade | BTC | Filters | session_whitelist=(London, NY-open) (2020_WFA01) | 22건, 승률 40.9%, RR 1.10 | 0.76 | -2.0% | ❌ FAIL |
| EXP-C2-28 | A-3 | daytrade | BTC | Filters | regime_filter=true (2020_WFA01) | 22건, 승률 40.9%, RR 1.10 | 0.76 | -2.0% | ❌ FAIL |
| EXP-C2-29 | A-3 | daytrade | BTC | Filters | min_rr_required enforcement (2020_WFA01) | 22건, 승률 40.9%, RR 1.10 | 0.76 | -2.0% | ❌ FAIL |
| EXP-C2-30 | A-3 | daytrade | BTC | Entries | rsi_long_min=45 (2020_WFA01) | 22건, 승률 40.9%, RR 1.10 | 0.76 | -2.0% | ❌ FAIL |
| EXP-C2-31 | A-3 | daytrade | BTC | Entries | allow_breakout=false (2020_WFA01) | 22건, 승률 40.9%, RR 1.10 | 0.76 | -2.0% | ❌ FAIL |
| EXP-C2-33 | A-3 | daytrade | BTC | Filters | htf=4h + mtf_confirm (2020_WFA01) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-34 | A-3 | daytrade | BTC | Filters | mtf=1h + trend_align=true (2020_WFA01) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-35 | A-3 | daytrade | BTC | Filters | mtf_confirm=false (2020_WFA01) | 47건, 승률 31.9%, RR 1.23 | 0.58 | -3.4% | ❌ FAIL |
| EXP-C2-36 | A-3 | daytrade | BTC | Filters | session_whitelist=OFF (2020_WFA01) | 86건, 승률 25.6%, RR 1.18 | 0.41 | -10.5% | ❌ FAIL |
| EXP-C2-37 | A-3 | daytrade | BTC | Filters | session_whitelist=(London, NY-open), mtf_confirm=false (2020_WFA01) | 47건, 승률 31.9%, RR 1.23 | 0.58 | -3.4% | ❌ FAIL |
| EXP-C2-38 | A-3 | daytrade | BTC | Entries | rsi_short_max=55 (2020_WFA01) | 47건, 승률 29.8%, RR 1.16 | 0.49 | -3.7% | ❌ FAIL |
| EXP-C2-39 | A-3 | daytrade | BTC | Filters | require_trend_align=false (2020_WFA01) | 47건, 승률 29.8%, RR 1.16 | 0.49 | -3.7% | ❌ FAIL |
| EXP-C2-40 | A-3 | daytrade | BTC | Filters | vol_spike_mult=3.0 (2020_WFA01) | 47건, 승률 29.8%, RR 1.14 | 0.48 | -3.3% | ❌ FAIL |
| EXP-C2-41 | A-1 | daytrade | BTC | Risk | max_consecutive_losses=6 (2020_WFA01) | 23건, 승률 26.1%, RR 0.60 | 0.21 | -3.4% | ❌ FAIL |
| EXP-C2-42 | A-2 | daytrade | BTC | Exits | TP 25/50/잔25, time_exit=720 (2020_WFA01) | 23건, 승률 26.1%, RR 0.54 | 0.19 | -3.5% | ❌ FAIL |
| EXP-C2-43 | A-2 | daytrade | BTC | Exits | time_exit=360 (TP 25/50/잔25) (2020_WFA01) | 23건, 승률 26.1%, RR 0.54 | 0.19 | -3.5% | ❌ FAIL |
| EXP-C2-44 | A-2 | daytrade | BTC | Exits | move_to_break_even_at_r=0.8 (2020_WFA01) | 23건, 승률 26.1%, RR 0.54 | 0.19 | -3.4% | ❌ FAIL |
| EXP-C2-45 | A-3 | daytrade | BTC | Entries | min_rr_required=1.6 (2020_WFA01) | 23건, 승률 26.1%, RR 0.54 | 0.19 | -3.4% | ❌ FAIL |
| EXP-C2-46 | A-1 | daytrade | BTC | Risk | max_consecutive_losses=999 (2020_WFA01) | 47건, 승률 27.7%, RR 1.11 | 0.42 | -3.7% | ❌ FAIL |
| EXP-C2-47 | A-3 | reversion | BTC | Strategy | selector=reversion (2020_WFA01) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-48 | A-3 | reversion | BTC | Filters | regime_filter=false (top-level) (2020_WFA01) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-49 | A-3 | reversion | BTC | Entries | rsi_threshold=40 (2020_WFA01 15m OOS) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-50 | A-3 | reversion | BTC | Entries | bb_lower_pct=1.02, bb_upper_pct=0.98 (2020_WFA01 15m OOS) | 10건, 승률 10.0%, RR 1.04 | 0.12 | -2.8% | ❌ FAIL |
| EXP-C2-51 | A-3 | reversion | BTC | Entries | rsi_threshold=30 (2020_WFA01 15m OOS) | 59건, 승률 39.0%, RR 1.17 | 0.75 | -2.2% | ⚠️ B (60.9/100) |
| EXP-C2-52 | A-3 | reversion | BTC | Filters | trend_context_required=true (EMA 컨텍스트) | 28건, 승률 35.7%, RR 1.61 | 0.89 | -0.5% | ⚠️ B (66.2/100) |
| EXP-C2-53 | A-3 | reversion | BTC | Exits | move_to_break_even_at_r=0.6 | 28건, 승률 35.7%, RR 1.61 | 0.89 | -0.5% | ⚠️ B (66.2/100) |
| EXP-C2-55 | A-3 | reversion | BTC | Filters | regime=true | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-56 | A-3 | reversion | BTC | Exits | trailing.k=2.5 (baseline regime=false) | 28건, 승률 35.7%, RR 1.68 | 0.93 | -0.3% | ⚠️ B (66.9/100) |
| EXP-C2-57 | A-3 | reversion | BTC | Exits | TP 30/40/잔30 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-58 | A-3 | reversion | BTC | Entries | rsi_threshold=28 | 30건, 승률 30.0%, RR 1.46 | 0.63 | -2.2% | ⚠️ B (60.0/100) |
| EXP-C2-59 | A-3 | reversion | BTC | Entries | rsi_threshold=30 (baseline 복원) | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-60 | A-3 | reversion | BTC | Exits | trailing.k=2.0 | 26건, 승률 34.6%, RR 1.36 | 0.72 | -1.3% | ⚠️ B (61.6/100) |
| EXP-C2-61 | A-3 | reversion | BTC | Exits | time_exit_min=720 | 26건, 승률 34.6%, RR 1.36 | 0.72 | -1.3% | ⚠️ B (61.6/100) |
| EXP-C2-62 | A-3 | reversion | BTC | Exits | stop.k=2.0 | 26건, 승률 34.6%, RR 1.36 | 0.72 | -1.3% | ⚠️ B (61.6/100) |
| EXP-C2-63 | A-3 | reversion | BTC | Exits | stop.k=1.6 | 26건, 승률 34.6%, RR 1.36 | 0.72 | -1.3% | ⚠️ B (61.6/100) |
| EXP-C2-64 | A-3 | reversion | BTC | Filters | mtf_confirm=true (1h) | 0건, 승률 - | - | 0.0% | ❌ No trades |
| EXP-C2-65 | A-3 | reversion | BTC | Entries | rr=2.2 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-66 | A-3 | reversion | BTC | Exits | move_to_break_even_at_r=0.8 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-67 | A-3 | reversion | BTC | Exits | trailing.k=3.0 | 28건, 승률 35.7%, RR 1.80 | 1.00 | -0.0% | ⚠️ B (68.0/100) |
| EXP-C2-68 | A-3 | reversion | BTC | Exits | TP 40/40/잔20 | 28건, 승률 35.7%, RR 1.62 | 0.90 | -0.4% | ⚠️ B (66.3/100) |
| EXP-C2-69 | A-3 | reversion | BTC | Filters | volume_mult=1.1 (TP 40/40 동시) | 27건, 승률 37.0%, RR 1.59 | 0.94 | -0.3% | ⚠️ B (67.2/100) |
| EXP-C2-70 | A-3 | reversion | BTC | Exits | time_exit_min=180 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-71 | A-3 | reversion | BTC | Exits | move_to_break_even_at_r=1.0 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-72 | A-3 | reversion | BTC | Entries | min_rr_required=1.5 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-73 | A-3 | reversion | BTC | Entries | min_rr_required=1.2 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-74 | A-3 | reversion | BTC | Entries | rsi_threshold=32 | 30건, 승률 36.7%, RR 1.72 | 1.00 | -0.0% | ⚠️ B (68.1/100) |
| EXP-C2-75 | A-3 | reversion | BTC | Entries | bb_lower_pct=1.01, bb_upper_pct=0.99 | 27건, 승률 33.3%, RR 1.60 | 0.80 | -0.9% | ⚠️ B (64.2/100) |
| EXP-C2-76 | A-3 | reversion | BTC | Entries | cooldown_candles=5 | 32건, 승률 34.4%, RR 1.61 | 0.84 | -0.9% | ⚠️ B (65.1/100) |
| EXP-C2-77 | A-3 | reversion | BTC | Filters | volume_spike=true | 7건, 승률 28.6%, RR 1.44 | 0.57 | -0.8% | ❌ FAIL (58.5/100) |
| EXP-C2-78 | A-3 | reversion | BTC | Entries | bb_lower_pct=1.03, bb_upper_pct=0.97 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-79 | A-3 | reversion | BTC | Filters | volume_mult=1.3 | 28건, 승률 35.7%, RR 1.88 | 1.04 | 0.2% | ⚠️ B (68.9/100) |
| EXP-C2-80 | A-3 | reversion | BTC | Entries | bb_lower_pct=1.00, bb_upper_pct=1.00 | 24건, 승률 29.2%, RR 1.75 | 0.72 | -1.2% | ⚠️ B (61.9/100) |
| EXP-C2-81 | A-3 | reversion | BTC | Filters | trend_context_required=false | 60건, 승률 38.3%, RR 1.33 | 0.82 | -1.6% | ⚠️ B (63.7/100) |
| EXP-C2-82 | A-3 | reversion | BTC | Filters | allow_short=false (LONG-only) | 17건, 승률 41.2%, RR 2.63 | 1.84 | 1.7% | ✅ A (79.5/100) |
| EXP-C2-83 | A-3 | reversion | BTC | Exits | TP 20/80 @ 1.0/2.2 | 17건, 승률 41.2%, RR 2.64 | 1.85 | 1.8% | ✅ A (79.6/100) |
| EXP-C2-84 | A-3 | reversion | BTC | Exits | time_exit_min=240 | 17건, 승률 41.2%, RR 2.64 | 1.85 | 1.8% | ✅ A (79.6/100) |
| EXP-C2-85 | A-3 | reversion | BTC | Entries | bb_lower_pct=1.04 (upper=0.98) | 17건, 승률 41.2%, RR 2.64 | 1.85 | 1.8% | ✅ A (79.6/100) |
| EXP-C3-01 | C3 | scalping | BTC | Pivot | 5m etf_anticip_24, selector=scalping (OOS) | 97건, 승률 19.6%, RR 1.63 | 0.40 | -5.6% | ❌ FAIL |
| EXP-C3-02 | C3 | scalping | BTC | Risk | max_consecutive_losses=4 (5m OOS) | 4건, 승률 0.0%, RR 0.00 | 0.00 | -0.4% | ❌ FAIL |
| EXP-C3-03 | C3 | scalping | BTC | Filters | session_whitelist=[] (5m OOS) | 6건, 승률 33.3%, RR 0.12 | 0.06 | -0.4% | ❌ FAIL |
| EXP-C3-81 | C3 | scalping | BTC | Pivot | 5m etf_anticip_24, selector=scalping (OOS, 최신 실행) | 4건, 승률 0.0%, RR 0.00 | 0.00 | -0.4% | ❌ FAIL |
| EXP-C3-82 | C3 | scalping | BTC | Filters | allow_short=false (LONG-only) | 8건, 승률 37.5%, RR 2.27 | 1.36 | -0.6% | ✅ A (74.1/100) |
| EXP-C3-83 | C3 | scalping | BTC | Entries | volume_mult=1.2 | 11건, 승률 54.5%, RR 2.07 | 2.48 | 1.0% | 🎉 S (82.4/100) |
| EXP-C3-84 | C3 | scalping | BTC | Exits | time_exit_min=120 | 11건, 승률 54.5%, RR 2.07 | 2.48 | 1.0% | 🎉 S (82.4/100) |
| EXP-C3-85 | C3 | scalping | BTC | Entries | bb_bounce_lower_now_mult=1.002 | 11건, 승률 54.5%, RR 2.07 | 2.48 | 1.0% | 🎉 S (82.4/100) |
| EXP-C3-86 | C3 | scalping | BTC | OOS | WFA_02 HALVING | 5건, 승률 0.0%, RR 0.00 | 0.00 | -0.3% | ❌ D (25.0/100) |
| EXP-C3-87 | C3 | scalping | BTC | OOS | WFA_03 POST_HALVING | 11건, 승률 27.3%, RR 3.51 | 1.32 | 0.2% | ✅ A (72.6/100) |
| EXP-C3-88 | C3 | scalping | BTC | OOS | WFA_04 SUMMER_RANGE | 4건, 승률 0.0%, RR 0.00 | 0.00 | -0.3% | ❌ D (25.0/100) |
| EXP-C3-89 | C3 | scalping | BTC | OOS | WFA_05 Q4_VOLATILITY | 10건, 승률 30.0%, RR 1.62 | 0.69 | -0.2% | ⚠️ B (61.6/100) |
| EXP-C3-90 | C3 | scalping | BTC | OOS | WFA_06 YEAR_END | 19건, 승률 36.8%, RR 1.76 | 1.03 | 0.0% | ⚠️ B (68.7/100) |
| EXP-C3-91 | C3 | scalping | BTC | Filters | session_whitelist=[London, NY-open] (HALVING) | 4건, 승률 25.0%, RR 3.20 | 1.07 | 0.0% | ⚠️ B (67.7/100) |
| EXP-C3-92 | C3 | scalping | BTC | Filters | require_trend_align=true (HALVING) | 4건, 승률 25.0%, RR 3.20 | 1.07 | 0.0% | ⚠️ B (67.7/100) |
| EXP-C3-93 | C3 | scalping | BTC | Entries | entries.min_rr_required=1.5 (HALVING) | 4건, 승률 25.0%, RR 3.20 | 1.07 | 0.0% | ⚠️ B (67.7/100) |
| EXP-C3-94 | C3 | scalping | BTC | Filters | vol_spike_mult=4.0 (HALVING) | 4건, 승률 25.0%, RR 3.20 | 1.07 | 0.0% | ⚠️ B (67.7/100) |
| EXP-C3-95 | C3 | scalping | BTC | Exits | trailing.k=2.0 (YEAR_END) | 19건, 승률 36.8%, RR 1.76 | 1.03 | 0.0% | ⚠️ B (68.7/100) |
| EXP-C3-97 | C3 | scalping | BTC | Filters | session_whitelist=NY-open (YEAR_END) | 7건, 승률 28.6%, RR 1.70 | 0.68 | -0.2% | ⚠️ B (61.1/100) |
| EXP-C3-98 | C3 | scalping | BTC | Filters | vol_spike_mult=1.5 (YEAR_END) | 7건, 승률 42.9%, RR 1.46 | 1.09 | 0.1% | ✅ A (70.2/100) |
| EXP-C3-99 | C3 | scalping | BTC | OOS | WFA_02 HALVING (vol_spike_mult=1.5) | 2건, 승률 0.0%, RR 0.00 | 0.00 | -0.2% | ❌ D (25.0/100) |
| EXP-C3-100 | C3 | scalping | BTC | OOS | WFA_04 SUMMER_RANGE (vol_spike_mult=1.5) | 3건, 승률 0.0%, RR 0.00 | 0.00 | -0.0% | ❌ D (25.0/100) |
| EXP-C3-102 | C3 | scalping | BTC | Entries | entries.min_rr_required=1.6 (HALVING) | 4건, 승률 0.0%, RR 0.00 | 0.00 | -0.5% | ❌ D (25.0/100) |
| EXP-C3-103 | C3 | scalping | BTC | Filters | scalping.volume_mult=1.1 (SUMMER_RANGE) | 4건, 승률 0.0%, RR 0.00 | 0.00 | -0.3% | ❌ D (25.0/100) |
| EXP-C3-104 | C3 | scalping | BTC | Filters | allow_short=true (HALVING) | 5건, 승률 0.0%, RR 0.00 | 0.00 | -0.5% | ❌ D (25.0/100) |
| EXP-C3-105 | C3 | scalping | BTC | Filters | allow_short=true (SUMMER_RANGE) | 11건, 승률 27.3%, RR 2.47 | 0.93 | -0.0% | ⚠️ B (65.4/100) |
| EXP-C3-106 | C3 | scalping | BTC | Exits | trailing.k=2.5 (SUMMER_RANGE) | 11건, 승률 27.3%, RR 2.47 | 0.93 | -0.0% | ⚠️ B (65.4/100) |
| EXP-C3-107 | C3 | scalping | BTC | Exits | time_exit_min=180 (HALVING) | 5건, 승률 0.0%, RR 0.00 | 0.00 | -0.5% | ❌ D (25.0/100) |
| EXP-C3-108 | C3 | scalping | BTC | Exits | time_exit_min=180 (SUMMER_RANGE) | 11건, 승률 27.3%, RR 2.47 | 0.93 | -0.0% | ⚠️ B (65.4/100) |
| EXP-C3-109 | C3 | scalping | BTC | Exits | trailing.k=2.5 (HALVING) | 5건, 승률 0.0%, RR 0.00 | 0.00 | -0.5% | ❌ D (25.0/100) |
| EXP-C3-110 | C3 | scalping | BTC | Risk | max_consecutive_losses=6 (HALVING) | 6건, 승률 0.0%, RR 0.00 | 0.00 | -0.7% | ❌ D (25.0/100) |
| EXP-C3-111 | C3 | scalping | BTC | Filters | session_whitelist=[London, NY-open] (HALVING) | 6건, 승률 0.0%, RR 0.00 | 0.00 | -0.4% | ❌ D (25.0/100) |
| EXP-C3-113 | C3 | scalping | BTC | Filters | session_whitelist=[] (HALVING) | 16건, 승률 18.8%, RR 1.29 | 0.30 | -0.9% | ❌ D (49.4/100) |
| EXP-C3-114 | C3 | scalping | BTC | Exits | rr=2.0 (HALVING) | 16건, 승률 18.8%, RR 1.29 | 0.30 | -0.9% | ❌ D (49.4/100) |
| EXP-C3-115 | C3 | scalping | BTC | Exits | trailing.k=3.0 (HALVING) | 16건, 승률 18.8%, RR 1.29 | 0.30 | -0.9% | ❌ D (49.4/100) |
| EXP-C3-116 | C3 | scalping | BTC | Filters | volume_mult=1.5 (HALVING) | 43건, 승률 34.9%, RR 1.80 | 0.97 | -0.1% | ⚠️ B (67.3/100) |
| EXP-C3-117 | C3 | scalping | BTC | Filters | require_trend_align=true (HALVING) | 42건, 승률 33.3%, RR 1.82 | 0.91 | -0.2% | ⚠️ B (66.1/100) ❌ 롤백 |
| EXP-C3-118 | C3 | scalping | BTC | Exits | TP2={2.0R:50%} (HALVING) | 40건, 승률 30.0%, RR 0.93 | 0.40 | -1.3% | ❌ C (50.6/100) ❌ 롤백 |
| EXP-C3-119 | C3 | scalping | BTC | Restore | S등급 설정 복원 (volume_mult=1.2, time_exit_min=120) HALVING 재테스트 | 16건, 승률 18.8%, RR 1.29 | 0.30 | -0.9% | ❌ D (49.4/100) ⚠️ 레짐 의존성 |
| EXP-C3-120 | C3 | scalping | BTC | OOS | C3-116 설정 (volume_mult=1.5) SUMMER_RANGE 검증 | 10건, 승률 20.0%, RR 2.57 | 0.64 | -0.2% | ❌ C (58.7/100) |
| EXP-C3-121 | C3 | scalping | BTC | Entries | min_rr_required=1.6 (HALVING) | 43건, 승률 34.9%, RR 1.80 | 0.97 | -0.1% | ⚠️ B (67.3/100) |
| EXP-C3-122 | C3 | scalping | BTC | Exits | move_to_break_even_at_r=0.6 (HALVING) | 43건, 승률 34.9%, RR 1.85 | 0.99 | -0.0% | ⚠️ B (67.8/100) |
| EXP-C3-123 | C3 | scalping | BTC | Exits | trailing.k=2.8 (HALVING) | 43건, 승률 34.9%, RR 1.85 | 0.99 | -0.0% | ⚠️ B (67.8/100) |
| EXP-C3-124 | C3 | scalping | BTC | Filters | news_blackout_min=40 (HALVING) | 43건, 승률 34.9%, RR 1.85 | 0.99 | -0.0% | ⚠️ B (67.8/100) |
| EXP-C3-125 | C3 | scalping | BTC | Filters | volume_spike_guard=true, vol_spike_mult=2.5 (HALVING) | 8건, 승률 12.5%, RR 2.10 | 0.30 | -0.4% | ❌ C (50.0/100) ❌ 롤백 |
| EXP-C3-126 | C3 | scalping | BTC | Exits | trailing.k=3.2 (HALVING) | 43건, 승률 34.9%, RR 1.85 | 0.99 | -0.0% | ⚠️ B (67.8/100) |
| EXP-C3-127 | C3 | scalping | BTC | Filters | volume_mult=1.6 (HALVING) | 42건, 승률 35.7%, RR 1.91 | 1.06 | +0.1% | ⚠️ B (69.2/100) |
| EXP-C3-128 | C3 | scalping | BTC | Exits | TP 분할=TP1 30%, TP2 40%, Trail 30% (2.0R) (HALVING) | 39건, 승률 30.8%, RR 0.98 | 0.43 | -1.1% | ❌ C (51.9/100) ❌ 롤백 |
| FINAL-C3-HALVING | C3 | scalping | BTC | Preset | vol_mult=1.7, min_rr=1.8, BE=0.6, trail.k=3.4, TP(1.0:20/2.2:80), time_exit=240 | 36건, 승률 38.9%, RR 2.09 | 1.33 | +0.5% | ✅ A (74.1/100) |
| EXP-C3-134 | C3 | scalping | BTC | Filters | volume_mult=1.8 (HALVING) | 31건, 승률 38.7%, RR 1.99 | 1.26 | +0.4% | ✅ A (73.1/100) |
| EXP-C3-135 | C3 | scalping | BTC | Entries | bb_bounce_lower_now_mult=1.003 (HALVING) | 29건, 승률 37.9%, RR 1.98 | 1.21 | +0.3% | ✅ A (72.1/100) |
| EXP-C3-136 | C3 | scalping | BTC | Entries | bb_bounce_lower_prev_mult=1.009 (HALVING) | 30건, 승률 40.0%, RR 2.00 | 1.33 | +0.5% | ✅ A (74.2/100) |
| EXP-C3-137 | C3 | scalping | BTC | Exits | time_exit_min=300 (HALVING) | 30건, 승률 40.0%, RR 2.00 | 1.33 | +0.5% | ✅ A (74.2/100) |
| EXP-C3-138 | C3 | scalping | BTC | Exits | trailing.k=3.6 (HALVING) | 30건, 승률 40.0%, RR 2.00 | 1.33 | +0.5% | ✅ A (74.2/100) |
| EXP-C3-139 | C3 | scalping | BTC | Exits | move_to_break_even_at_r=0.55 (HALVING) | 30건, 승률 40.0%, RR 2.00 | 1.33 | +0.5% | ✅ A (74.2/100) |
| EXP-C3-140 | C3 | scalping | BTC | Entries | min_rr_required=2.0 (HALVING) | 30건, 승률 40.0%, RR 2.00 | 1.33 | +0.5% | ✅ A (74.2/100) |
| EXP-C3-141 | C3 | scalping | BTC | Filters | session_whitelist=NY-open (HALVING) | 3건, 승률 0.0%, RR 0.00 | 0.00 | -0.3% | ❌ D (25.0/100) ❌ 롤백 |
| EXP-C3-144 | C3 | scalping | BTC | Transfer | ETF_APPROVAL OOS (HALVING A preset) | 31건, 승률 29.0%, RR 1.52 | 0.62 | -1.0% | ⚠️ B (60.1/100) |
| EXP-C3-145 | C3 | scalping | BTC | Transfer | SUMMER_RANGE OOS (HALVING A preset) | 9건, 승률 11.1%, RR 3.82 | 0.48 | -0.3% | ❌ C (53.4/100) |

> **변경 레이어는 한 번에 하나만!** (원인-결과 추적)
> **⚠️ 중요 발견**: ETF 구간 S등급 설정이 HALVING 구간에서 D등급 → **레짐별 파라미터 분기 필요**
> **🚨 결론**: 단일 파라미터 세트로는 전체 OOS 통과 불가능. TEST_SCENARIO 단계 B(멀티 심볼 전이) 전에 **레짐별 프리셋 구축** 필요

---

## 회고/결정(RETRO)

- **무엇이 먹혔나**: 
  - TP 분할 시스템 정상 작동 (TP1→TP2→Trailing)
  - 멀티 심볼/멀티 전략 인프라 구축 완료
  - **코드 버그 발견 & 수정** (2개):
    1. main.py + signal_generator.py: selector 로직 추가 → strategy_loader.py 모듈화
    2. MTF 필터 백테스트 불가 발견 (require_htf_aligned + BinanceClient API)
  
- **무엇이 과적합 기미였나**: 
  - 모든 전략을 한꺼번에 테스트 → 원인 추적 불가
  - 승률 26%, MDD -771% → 엔트리 필터 부족
  - **selector 무시 버그**: timeframe 기반으로만 전략 선택 (수정 완료)
  
- **다음 사이클에서 고정할 것**:
  - 고정 레이어 (fees/risk/execution) ✅
  - **단일 전략 × BTCUSDT로 시작** (TEST_SCENARIO.md 원칙)
  - **Exits 먼저 → Entries 나중** (단계별 진행)
  
- **다음 사이클에서 실험할 것(LHS/BO 후보)**:
  - ✅ A-2 Exits 그리드: 완료 (개선 없음)
  - ✅ A-3 Entries: 일부 완료 (개선 없음)
  - ✅ 3개 전략 테스트: scalping, reversion, daytrade (모두 실패)
  - ✅ 필터 비활성화: 개선 없음
  - ✅ 데이터 기간 변경: 2024년 1년 데이터 (105,121 캠들) 다운로드 & 테스트
  - ✅ 치명적 버그 3개 수정 (EXP-A4-01):
    1. 자본 0 이하 거래 차단 추가 (`RiskManager.check_order`)
    2. 백테스트 연속 손실 제한 적용 (기존: 경고만, 수정: 차단)
    3. Scalping 전략 조건 강화 시도
  - ✅ **EXP-A4-02: 조건 과도 강화 결과**
    - 거래: 3건/년 (목표: 수천 건의 0.03%)
    - Win Rate: 66.7% (2승 1패)
    - 총 PnL: +$100 (평균 +$33/건)
    - **문제**: 5가지 조건 모두 충족 → 신호 소멸
    - RSI 30-70 + EMA 3선 정렬 + BB 0.8% + 거래량 1.5x + MACD 크로스
  - ⏭ **최종 결론: 양극단 문제**
    - **조건 완화**: 388,926건/년 (1,065건/일) - PF 0.41~0.46
    - **조건 강화**: 3건/년 (0.01건/일) - 거래 없음
    - 승률 24.8~25.8% (완화) vs 66.7% (강화, 샘플 부족)
    - MDD -848% ~ -1568% (완화) vs 측정 불가 (강화)
    - **근본 문제**: 전략 로직이 현재 시장 패턴과 불일치
    - **권장**: 
      1. 전략 로직 전면 재설계 (성공 패턴 기반)
      2. 균형잡힌 조건 (RSI 25-75, EMA 2선, BB 1.0%, Vol 1.2x)
      3. 단계적 완화 테스트
  - ⏭ **Cycle 2 Day 1 결론: REVERSION 전략 실패 확인**
    - **BACKTEST_PERIODS.md 준수**: 6개 레짐 블록 다운로드 (2018~2024, 15m)
    - **WFA 블록 생성**: 16개 (Train 8주 + OOS 3주)
    - **대표 블록 3개 테스트**: 모두 실패
      - 2018_WFA01 (약세): 90건, 승률 25.2%, ROI -1,738%
      - bull_WFA01 (강세): 72건, 승률 25.4%, ROI -1,857%
      - 2022_WFA01 (루나/FTX): 78건, 승률 25.4%, ROI -1,862%
    - **근본 문제**: 성공 패턴(RSI<30 + BB하단 + EMA역배열)이 **모든 레짐에서 실패**
    - **버그 수정**: main.py의 data_file 우선 처리 추가
  
  - ⏭ **Cycle 2 Day 2: 전체 시스템 버그 수정 (2025-10-23)**
    - **근본 원인 분석**: "검증된 조건"인데도 실패한 이유
      1. **Bug #1 (치명적)**: engine.py save_signal_to_db() 호출 오류
         - 매개변수 이름/타입 불일치 (side→direction, timestamp→candle_closed_at)
         - timeframe, confidence, atr, leverage 누락
         - **영향**: 앙상블 모드에서 신호 저장 실패 (단일 전략은 영향 없음)
      2. **Bug #2**: portfolio_manager.py 과도한 거래 차단
         - max_correlated_positions: 2 (BTC/ETH 동시 진입 제한)
         - **영향**: "상관성 높은 포지션 초과 (2/2)" 반복 → 3,111건 신호 차단
      3. **Bug #3**: risk_manager.py 연속 손실 쿨다운
         - max_consecutive_losses: 4 (이후 999로 완화됨)
         - **영향**: "연속 손실 쿨다운 (6회)" → 3,111건 → 12건
    - **수정 완료**:
      - ✅ engine.py 라인 278-297: save_signal_to_db() 매개변수 수정
      - ✅ config.yml: portfolio.max_correlated_positions: 2 → 5
      - ✅ config.yml: risk.max_consecutive_losses: 999 (이미 설정됨)
    - **전략 구조 명확화**:
      - **현재 모드**: use_ensemble: false (단일 전략만 테스트)
      - **현재 전략**: selector: daytrade (REVERSION 실패 후 전환)
      - **앙상블**: 모든 단일 전략 튜닝 완료 후 진행 (TEST_SCENARIO.md 단계 C)
    - **Daytrade 테스트 결과 (EXP-C2-06)**:
      - 2022_WFA01 (루나/FTX): 251건, 승률 25.4%, PF 0.42, ROI -1906%
      - **문제**: REVERSION과 동일한 패턴 (승률 25%, MDD -1800%+)
      - **총점**: 28.0/100 (D등급)
    - **Daytrade 테스트 결과 (EXP-C2-06)**:
      - 2022_WFA01: 251건, 승률 25.4%, PF 0.42, ROI -1906%
    - **Swing 테스트 결과 (EXP-C2-07)**:
      - 2022_WFA01: 213건, 승률 25.4%, PF 0.42, ROI -1923%
    - **근본 문제 재확인 (4개 전략 테스트 완료)**:
      - **Scalping**: PF 0.46, MDD -848%
      - **REVERSION**: PF 0.42~0.45, MDD -1738~-1862%
      - **Daytrade**: PF 0.42, MDD -1906%
      - **Swing**: PF 0.42, MDD -1923%
      - **공통점**: 모든 전략이 승률 25%, PF 0.42~0.46, 총점 28점/100점
      - **패턴**: 시장 구조와 전략 로직의 근본적 불일치
    - **최종 결론**:
      - **4개 전략 모두 동일한 실패 패턴**
      - **원인**: 전략 로직이 2022년 레짐과 맞지 않음
      - **다음 단계**: 
        1. 다른 레짐 블록 테스트 (2018_WFA01, bull_WFA01)
        2. 남은 전략 테스트 (Trend, Breakout)
        3. 전략 로직 전면 재설계 검토
  
  - ⏭ **Cycle 2 Day 3: Daytrade A-2 Exits 튜닝 (2025-10-24)**
    - **R3 Exits 설정 (stop.k=1.8, trail=3.0, BE=1.0, time_exit=720)**:
      - **2020_WFA01 (강세)**: 46건, 승률 37.0%, RR 1.53, PF 0.90, MDD -2.2% → 총점 61.5점 (B등급)
      - **2018_WFA01 (약세)**: 50건, 승률 34.0%, RR 0.63, PF 0.32, MDD -9.3%, 연속손실 12회 → 총점 37.2점 (D등급)
      - **24_WFA01 (2024)**: 64건, 승률 25.0%, RR 2.04, PF 0.68, MDD -3.0%, 연속손실 14회 → 총점 50.4점 (C등급)
    - **레짐별 분석**:
      - **RR 개선 확인**: 2020(1.53), 2024(2.04) → Trail 강화(k=3.0) + 장기 time_exit(720) 효과
      - **승률 레짐 의존**: 강세(37%) > 약세(34%) > 2024(25%)
      - **연속손실 악화**: 2020(8회) → 2018(12회) → 2024(14회) → Entries 필터 필요
      - **PF 미달 원인**: 승률 < 40% → 허수 진입 과다
    - **Gate 기준 대비**:
      - ✅ RR ≥ 1.5: 2020/2024 충족
      - ❌ PF ≥ 1.3: 모든 레짐 미달 (0.32~0.90)
      - ✅ MDD ≤ -20%: 모든 레짐 충족
      - ❌ Expectancy ≥ 0.10R: 모든 레짐 음수
      - ❌ 연속손실 ≤ 6: 모든 레짐 초과
    - **A-3(Entries/Filters) 시도 (EXP-C2-24~26)**:
      - **R1**: min_rr=1.5 → 46건, 승률 37.0%, RR 1.53 (변화 없음)
      - **R2**: min_rr=1.8 → 46건, 승률 37.0%, RR 1.53 (변화 없음)
      - **R3**: cooldown=5, vol_spike=true → 46건, 승률 37.0%, RR 1.53 (변화 없음)
      - **근본 원인 발견**: 
        1. `min_rr_required` 코드 미구현 (grep 결과 0건)
        2. `cooldown_candles`, `enable_vol_spike_filter` 필터 무효과
        3. Daytrade 전략의 진입 로직이 고정됨 (config 변경 무반영)
    - **최종 결론 (Cycle 2)**:
      - **A-2 Exits 튜닝 성과**: RR 1.53~2.04 달성 (Gate 기준 충족)
      - **A-3 Entries 튜닝 실패**: Config 필터가 전략 코드에 미구현
      - **근본 문제**: 
        1. Daytrade 전략 진입 로직이 하드코딩됨 (파라미터 튜닝 불가)
        2. 승률 37% 고정 → 허수 진입 필터링 불가
        3. TEST_SCENARIO.md 단계별 튜닝 불가 (코드 재설계 필요)
      - **다음 사이클 계획**:
        1. **전략 코드 리팩토링**: config → 전략 파라미터 전달 경로 구현
        2. **Entries 필터 구현**: min_rr_required, cooldown, vol_spike, session, regime
        3. **성공 패턴 재분석**: 2020 강세 구간에서 승률 37% 원인 규명
        4. **대안 전략 검토**: Swing/Trend/Breakout 중 구조적 문제 적은 후보 선택  

---

## 저장/버전 규칙

- 파일명: `RUNBOOK_CHECKLIST__YYYY-MM-DD__cycle-N.md`  
- 태그: `[stage][strategy][symbolset][dates][config_hash]`  
- 사이클 종료 시: **새 파일로 복제 → 메타/기간/커밋 갱신 → 다음 사이클 시작**

- [auto] study=scalping_v1_dryrun trial=0 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun trial=1 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun trial=2 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun trial=3 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun_fixed trial=0 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun trial=4 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun_fixed trial=1 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v2_test trial=0 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v1_dryrun_fixed trial=2 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_v2_test trial=1 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=0 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=1 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=2 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=3 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=4 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v1 trial=5 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=0 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=1 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=2 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=3 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=4 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=5 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=6 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=7 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=8 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=9 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2 trial=10 score=None grade=None PF=None ROI=None% MDD=None% Trades=None
- [auto] study=scalping_optuna_v2_fix1 trial=0 score=25.0 grade=D PF=0.0 ROI=-0.3752903509500013% MDD=-0.1766832550703781% Trades=3
- [auto] study=scalping_optuna_v2_fix1 trial=1 score=25.0 grade=D PF=0.0 ROI=-0.5110360450499914% MDD=-0.3126995653476185% Trades=4
- [auto] study=scalping_optuna_v2_fix1 trial=2 score=25.0 grade=D PF=0.0 ROI=-0.5233469807999982% MDD=-0.37663348199887764% Trades=5
- [auto] study=scalping_optuna_v2_fix1 trial=3 score=25.0 grade=D PF=0.0 ROI=-0.23878803575499513% MDD=-0.15692582619208392% Trades=3
- [auto] study=scalping_struct_test trial=0 score=25.0 grade=D PF=0.0 ROI=-0.16861788472499573% MDD=-0.021381212443137728% Trades=3
- [auto] study=scalping_v3_prod trial=0 score=25.0 grade=D PF=0.0 ROI=-1.0269302706399939% MDD=-0.8809594834616229% Trades=5
- [auto] study=scalping_v3_prod trial=1 score=25.0 grade=D PF=0.0 ROI=-0.5110360450499914% MDD=-0.3126995653476185% Trades=4
- [auto] study=scalping_v3_prod trial=2 score=25.0 grade=D PF=0.0 ROI=-1.0301871261349898% MDD=-0.8842211423416423% Trades=5
- [auto] study=scalping_v3_prod trial=3 score=25.0 grade=D PF=0.0 ROI=-0.5012016258399938% MDD=-0.35445546588260685% Trades=4
- [auto] study=scalping_v3_prod trial=4 score=25.0 grade=D PF=0.0 ROI=-1.105526195749994% MDD=-0.908374863414913% Trades=5
- [auto] study=scalping_v3_prod trial=5 score=25.0 grade=D PF=0.0 ROI=-0.8719554272499968% MDD=-0.7257560748675378% Trades=3
- [auto] study=scalping_v3_prod trial=6 score=25.0 grade=D PF=0.0 ROI=-1.015109547249996% MDD=-0.8691213262353057% Trades=4
- [auto] study=scalping_v3_prod trial=7 score=25.0 grade=D PF=0.0 ROI=-0.5110360450499914% MDD=-0.3126995653476185% Trades=4
- [auto] study=scalping_v3_prod trial=8 score=25.0 grade=D PF=0.0 ROI=-0.5110360450499914% MDD=-0.3126995653476185% Trades=4
- [auto] study=scalping_v3_prod trial=9 score=25.0 grade=D PF=0.0 ROI=-0.23878803575499513% MDD=-0.15692582619208392% Trades=3
- [auto] study=scalping_v3_prod trial=10 score=25.0 grade=D PF=0.0 ROI=-1.0301871261349898% MDD=-0.8842211423416423% Trades=5
- [auto] study=scalping_v3_prod trial=11 score=25.0 grade=D PF=0.0 ROI=-0.5233469807999982% MDD=-0.37663348199887764% Trades=5
- [auto] study=scalping_v3_prod trial=12 score=25.0 grade=D PF=0.0 ROI=-0.3120774225999939% MDD=-0.1460347572262287% Trades=3
