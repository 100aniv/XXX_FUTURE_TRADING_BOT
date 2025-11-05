좋다, 이 정도 구조면 “막 돌리기”가 아니라 **체계적 실험 설계**로 가야 한다.
핵심은 **(1) 층별 고정–튜닝 순서**, **(2) 조합 수 축소(샘플 효율)**, **(3) 재현성 있는 게이트 기준**이다. 아래 **플레이북** 그대로 따라가면 된다.

---

# 0) 원칙: “고정 레이어 → 변동 레이어” (Freeze → Tune)

**고정(공통) 레이어**

* 수수료/슬리피지/펀딩 모델(fees/accounting)
* 리스크 엔진(risk, leverage, exposure, DDL/연속SL)
* 실행(engine/execution) 재시도·슬리피지 캡·부분체결 처리
* 공통 필터 정책(예: 세션, 뉴스 블랙아웃)

**변동(튜닝) 레이어**

* exits(Stop/TP/Trailing/Time) → **손익비 먼저 안정화**
* entries(신호/필터 강도/쿨다운) → 허수 진입 제거
* strategies/* (각 전략 전용 파라미터)
* ensemble(가중치, 보너스, 윈도우)

> 순서 요약: **리스크·실행 고정 → Exits 튜닝 → Entries/Filters 튜닝 → 전략별 튜닝 → 앙상블 튜닝**
> 승률 집착 금지, **기대값(R/trade), PF, MDD** 기준으로만 승급.

---

# 1) 모드·심볼·전략별 “단계적 확장” 로드맵
 
> 현재 메인 튜닝 경로는 **D. 페이퍼 트레이딩**이며, **A~C는 보조(백테스트 검증)** 단계로 사용한다.

## 단계 A. **단일 전략 × 단일 심볼 × 백테스트**

* 심볼: **BTCUSDT**(유동성·체결 안정), 필요 시 ETHUSDT 보조
* 기간: **3년 WFA(roll)** + 최근 3~6개월 OOS 별도
* 목표: **Exits로 RR 확보 → Entries로 허수 제거**
* 게이트:

  * OOS **Expectancy ≥ +0.10R**, PF ≥ 1.3, MDD ≤ -20%, 연속SL ≤ 6
  * 레짐(트렌드/레인지/저유동) **모두 + 기대값**

> 이 단계에서 **전략별 “대표 파라미터 프리셋”** 1~2개만 뽑아둔다. (예: scalping_v1, scalping_v2)

## 단계 B. **단일 전략 × 멀티 심볼 × 백테스트**

* 심볼 확장: BTC, ETH → **ALTS 3~5개** (SOL/BNB/XRP/ADA 등)
* 방법: **고정 파라미터 그대로** 적용 → **심볼 전이 성능** 확인
* 게이트:

  * 심볼별 OOS Expectancy ≥ 0, 전체 가중 평균 ≥ 0.07R
  * 슬리피지 민감도(ALT)는 **슬리피지 캡 vs 체결률** 트레이드오프 기록

> 이 단계 통과 시 **전략의 “범용성” 확인**. 특정 심볼에만 맞는 전략은 앙상블에서 가중치 낮춤.

## 단계 C. **여러 전략(6개) 독립 튜닝 완료 후 → 앙상블 백테스트**

* 입력: 각 전략 **프리셋 1~2개씩** (너무 많으면 과적합)
* 앙상블: `weights`, `alpha~epsilon`, `consensus_bonus`, `rr_bonus` 등 **상위 6~12개 노브만** 튜닝
* 앙상블 평가:

  * 단일 전략 대비 **자본곡선 매끄러움 개선(드로우다운 감소)**가 최우선
  * OOS Expectancy ≥ 0.10R, PF ≥ 1.4, MDD ≤ -15%, Calmar ≥ 0.6

## 단계 D. **페이퍼 트레이딩(멀티 심볼·멀티 전략·앙상블)**

* 4~6주, **실행/체결/슬리피지** 격차 검증 (백테 대비 손상률 기록)
* 알림·재시작 복원·주문 일치율 100% 근접 확인
* **슬리피지 캡·주문유형(post-only/IOC/market) A/B**로 체결률↔가격개선 균형점 찾기

## 단계 E. **소액 라이브(리스크 1/3) → 점진 승급**

* DDL/연속SL 조건 위반 없으면 주차별 25~33%씩 리스크 상향
* 레짐 변화(고변동/저변동) 발생 시 프리셋 자동 전환 동작 확인

---

# 2) 조합 폭 줄이는 “샘플 효율” 전략

1. **Optuna TPE 베이지안 최적화(페이퍼)**

   * 각 전략별 핵심 노브 6~10개 → Optuna TPE가 탐색
   * 목적함수: 7일 롤링 `Sharpe × min(1, Trades/T_min) × (1 - MDD_penalty)`

2. **단일 변경 원칙(ABL: A/B/Layers)**

   * “Exits만” 묶음 A/B → 베스트 Exits 고정
   * 그다음 “Entries/Filters”만 A/B
   * 마지막 “전략 파라미터”만 A/B
     → 한 번에 한 레이어만 바꿔서 **원인-결과** 선명화

3. **Stop-early 기준**

   * WFA fold 1~2개에서 **명백히 열세**면 즉시 중단(계산 자원 절약)

4. **대표 구간 샘플링**

   * 트렌드 강/약 2구간, 레인지 1구간, 급락장 1구간, 저유동 1구간 = **대표 5구간** 먼저 평가
   * 합격 후보만 전체 기간 확장

---

# 3) 전략별 튜닝 지침 (당신 YAML 기준)

### Exits(공통; **최우선**)

* `exits.stop.k` (ATR) 1.5~2.2 스윕
* `take_profits`: TP1/TP2 비율(예: 30/40/잔30) vs (25/50/잔25) 비교
* `trailing.k` 2.0~3.0, `move_to_break_even_at_r` 0.6~1.0
* `time_exit_min` 180/360/720 A/B → **MFE/MAE 대비 잔량 회수 최적**

### Entries/Filters

* `entries.type` 고정(전략 특성 유지) + `min_rr_required` 1.2~1.8
* `filters.require_trend_align`(true/false), `atr_window`(10/14/20), `session_whitelist` on/off
* `volume_spike`(true/false), `vol_spike_mult`(2.0/2.5/3.0)

### 전략군별 팁

<!-- P4: 3m TF 전환 (2025-10-27) -->
<!-- 기존 5m 설정 (참고용 보존)
* **scalping(5m)**: 승률↑ 중심. `atr_mult_sl` 낮추고 `trailing` 빠르게. 세션 필수, `news_blackout` 강화.
-->
<!-- 새로운 3m 설정 -->
* **scalping(3m)**: 거래 빈도 증가(2배). 승률↑ 중심. `atr_mult_sl` 낮추고 `trailing` 빠르게. 세션 필수, `news_blackout` 강화. `min_bars_for_signal` 상향(30→50).
* **daytrade(15m)**: 엔트리 필터 강하게(HTF 1h), `rr` 2.5~3.0 노림.
* **reversion(15m)**: 과매수/과매도 조건을 **시간 제한 + mean-revert 증거**(볼린저 터치 후 회귀)로 묶기.
* **swing(1h)**: `time_exit_min` 크게, `trailing` 느리게. **펀딩 비용 영향** 체크.
* **trend(4h)**: 허수 신호 적음 → `rr` 2.5 노리되 거래수 적어 분산용.
* **breakout(1h)**: 가짜 돌파 방지(OB/AVWAP/상위 타임프레임 방향 필터).

---

# 4) 앙상블 튜닝 절차

1. **재료 제한**: 각 전략 **프리셋 1~2개**로 제한(총 6~12개 후보)
2. **가중치 초기화**: 균등 → 성과 기반(최근 30일 OOS 기준)
3. 하이퍼:

   * `weights.*` (0.5~3.0 범위), `alpha_winrate`(0.2~0.6), `beta_rr`(0.1~0.4), `gamma_sharpe`(0.1~0.3)
   * `consensus_bonus`(0~0.3), `rr_bonus`(0~0.3), `rr_bonus_threshold`(1.4~1.8)
   * `theta_long/short`(0.1~0.3)
4. **목표 함수**: **자본곡선 매끄러움**(MDD↓, Ulcer↓)을 핵심으로 Calmar/Sharpe 동시 개선
5. **심볼 가중 구조**: BTC/ETH 60~70%, ALTS 30~40%로 시작 → 알트 과대비중 금지
6. **검증**:

   * WFA + OOS에서 **단일 전략 대비 드로우다운 15~30% 감소** 확인
   * 레짐별(+세션별) 성과 **편차 축소**가 발생해야 합격

---

# 5) 실험 관리(필수): 로그/리포트/이름짓기

**실험 이름 규칙**
`{stage}-{strategy|ens}-{symbolset}-{dates}-{tag}`
예: `A-scalping-btc-eth-2022_2025-exits_grid_v3`

**기록 필드(최소)**

* git_commit, config_hash, seed, data_version
* train_periods, oos_periods, regime_tags
* metrics: Trades, Win%, AvgWinR, AvgLossR, **Expectancy**, PF, MDD, Calmar, Sharpe, Ulcer, MaxDDLen, MaxLosingStreak
* slippage_realized_vs_model(%), fee_realized
* notes: 체결 실패/재시작 이벤트/알림

**승급 게이트(권장 고정값)**

* 단일 전략 OOS: **Expectancy ≥ 0.10R**, PF ≥ 1.3, MDD ≤ -20%
* 앙상블 OOS: **Expectancy ≥ 0.10R**, PF ≥ 1.4, MDD ≤ -15%, Calmar ≥ 0.6
* 페이퍼→라이브: 백테 대비 **실행 손상률 ≤ 25%**, 주문/상태 일치율 ~100%

---

# 6) 심볼 세트 운용

* **Anchor**: BTCUSDT, ETHUSDT(상시)
* **ALTS 풀**: 유동성 필터(topN.min_volume_24h) 충족심볼 중 3~6개 롤링 선택
* **상관 캡**: exposure.symbol_groups 준수(BTC/ETH vs ALTS 분리)
* **리밸런싱**: `topN.refresh_interval`(1h)로 감시하되, 실거래는 **일 단위** 변경(시그널 교란 방지)

---

# 7) 권장 “튜닝 실행 순서” 체크리스트

1. **(공통 고정) fees/accounting/risk/execution/exposure 잠금**
2. **Exits 튜닝(각 전략 × BTC)** → RR 목표 달성
3. **Entries/Filters 튜닝(각 전략 × BTC)** → 허수 제거
4. **전이 검증(각 전략 × 멀티 심볼)** → 범용성 확인
5. **프리셋 확정(전략당 1~2개)**
6. **앙상블 튜닝(가중치·보너스·쓰레숄드)**
7. **대표 5구간 샘플 OOS→전체 OOS 확장**
8. **페이퍼 4~6주(실행·슬리피지 캡/주문유형 A/B)**
9. **소액 라이브(리스크 1/3)→승급**

---

# 8) 당신 설정(YAML)에서 바로 손댈 “스몰 스타트” 제안

* `risk.risk_per_trade_pct` **0.5% 유지**, `max_daily_loss_pct=2.0`, `max_consecutive_losses=4` 잠금
* **Exits 그리드**(전략 공통 후보):

  * `stop.k`: 1.6/1.8/2.0, `trailing.k`: 2.0/2.5/3.0, `move_to_break_even_at_r`: 0.6/0.8/1.0
  * TP 분할: `(30,40,잔30)`, `(25,50,잔25)`, `(40,40,잔20)`
* **Entries/Filters 후보**:

  * `min_rr_required`: 1.2/1.5/1.8
  * `require_trend_align`: true/false, `session_whitelist`: on/off
  * `volume_spike`: true/false, `vol_spike_mult`: 2.0/2.5/3.0
* **전략별 프리셋 1차**: scalping_v1/daytrade_v1/reversion_v1/swing_v1/trend_v1/breakout_v1
* **앙상블 1차**: weights 균등 → 30일 OOS 성과 기반으로 선형 스코어링 후 재가중

---

# 9) “한 번에 vs 개별” 질문에 대한 결론

* **개별 전략을 먼저**: 각 전략의 **Exits→Entries** 튜닝을 **단일 심볼(BTC)**에서 끝낸 뒤 멀티 심볼 전이 검증.
* 그 다음에 **앙상블**: 완성된 전략 프리셋만 재료로 사용(조합 폭 급감).
* 멀티 전략을 처음부터 한꺼번에 튜닝하면 **원인 추적 불가 + 과적합 위험**이 급증.

---

# 10) 필요하면 만들어 줄 수 있는 것

* Walk-Forward + LHS/BO 기반 **실험 파이프라인 스크립트**(결과 CSV/PNG, config 해시 자동)
* **레짐 태거**(트렌드/레인지/변동성/세션 라벨러) 템플릿
* **포지션 사이징 & 청산가 여유 검사** 모듈(당신 YAML 키와 1:1 매핑)
* **앙상블 가중치 메타러닝**(최근 30일 OOS로 주간 업데이트)

원하는 순서대로 뽑아줄게.
첫 파일은 **“Exits 그리드 테스트 러너”**로 갈까, 아니면 **Walk-Forward 자동화**부터 갈까?

---

## 부록) 페이퍼 모드 베이지안 튜너 (Tuner CLI)

- 목적: 페이퍼 트레이딩에서 7일 롤링 메트릭 기반으로 실시간 베이지안 최적화 수행.
- 구현: `common/tuning_core.py` + `common/tuner_cli.py` (Optuna TPE, MedianPruner). 엔진/전략 코드는 수정하지 않으며, `CONFIG_PATH`로 단일 전략 YAML(active.yml)만 발행.
- 입력: PostgreSQL `trading.trades` (최근 7일, CLOSED 거래). 필요시 `TUNE_WINDOW_DAYS`로 조정.
- 출력: `configs/<strategy>/active.yml` (현재 활성 프리셋), `logs/tuning/<study>/study.db` (Optuna), `logs/tuning/trial_<study>_<n>.json` 권장.
- 게이트 준수: `Trades ≥ T_min`, `MDD ≤ cap` 위반 시 Prune/패널티. 점수=Sharpe×min(1,Trades/T_min)×(1−MDD_penalty).
- 제한: 페이퍼/라이브 실행 중 데이터가 쌓여야 동작. 백테스트 파일 이름 기반 레짐 프리셋은 사용하지 않음.
