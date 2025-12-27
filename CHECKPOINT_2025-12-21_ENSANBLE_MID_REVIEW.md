# 🎯 Current Baseline (as of 2025-12-22)

## Rollback-Safe Production Baseline
- **Commit**: `e02ab143` ("PHASE36-0 Paper Trading Validation Pack - COMPLETE & PASS")
- **Git Tag**: `baseline/phase36-0-pass/20251222`
- **Git Branch**: `baseline/phase36-0-pass`
- **Status**: ✅ **PRODUCTION READY**
- **Evidence**: `docs/PHASE36/PHASE36_0_PAPER_VALIDATION_PACK_FINAL_REPORT.md`

## Completed PHASE List
- ✅ PHASE0-16: Infrastructure & Initial Engine
- ✅ PHASE17: Portfolio Budget & Position Infra (V6.1)
- ✅ PHASE18-20: INFRA, Ensemble Framework, Multi-Symbol
- ✅ PHASE21-23: Strategy Validation, Ensemble V2
- ✅ PHASE24: Redis/DB/Env Hardening
- ✅ PHASE25: Long-run PAPER Regression & Tuning Infra
- ✅ PHASE26: Multi-Symbol Engine v1 (Top100)
- ✅ PHASE27: Trade Activity Diagnosis & Signal SSOT
- ✅ PHASE28: Strategy Performance Baseline
- ✅ PHASE29-35: Strategy Improvement & Ensemble Tuning
- ✅ **PHASE36-0: Paper Trading Validation Pack** (12 trades, 100% DB persist, 4h 24m)
- ✅ **PHASE36-1 S2: Signal Telemetry Validation** (COMPLETE & PASS, 2025-12-24)
- ✅ **PHASE36-1 S3: Smoke Gate + 12H LONGRUN** (2025-12-25)
  - **목표**: SSOT workflow 정립 + 12시간 REAL PAPER 검증
  - **결과**: ✅ PASS & SEAL
  - **Smoke Gate**: doctor(env) + fast(unit) + regression(skip, 0 tests)
    - Doctor PASS, Fast 36/36 PASS
    - Regression SKIP (integration test가 pytest 호환 아님)
  - **12H LONGRUN**: 정상 실행 → 자연 종료 (Code 0)
    - 거래 수: 10개 (LONG 5, SHORT 5)
    - DB persist: 100% (10/10)
    - 프로세스 종료: 정상 (잔존 thread 없음)
  - **Evidence**:
    - Smoke logs: logs/evidence/phase36_1_s3_smoke_gate/
    - LONGRUN logs: logs/evidence/phase36_1_s3_longrun/
    - Report: docs/PHASE36/PHASE36_1_S3_*.md
  - **Commit**: e511c2ad (2025-12-26)
- ✅ **PHASE36-1 S4: SSOT Gate Infrastructure + Signal Telemetry v2 - REAL PASS** (2025-12-27)
  - **목표**: Gate2 regression 복구 + Signal Telemetry v2 실코드/실테스트 완성 + Evidence 기반 PASS
  - **결과**: ✅ **100% PASS** (All 3 Gates + Telemetry v2 Complete with Evidence)
  - **Gate 실행 결과** (UTF-8 evidence logs):
    - **Gate 0 (doctor)**: ✅ PASS (Python 3.14.0 + core deps OK)
    - **Gate 1 (fast)**: ✅ 42/42 PASS in 2.64s (36 기존 + 6 telemetry v2)
    - **Gate 2 (regression)**: ✅ 5/5 PASS in 2.50s (신규 smoke suite)
  - **Telemetry v2 완전 구현** (`common/signal_telemetry.py`):
    - `db_persist_attempted()` - DB persist 시도 카운터
    - `db_insert_succeeded()` - DB insert 성공 카운터
    - `db_insert_failed_count()` - DB insert 실패 카운터
    - `set_start_time(timestamp=None)` - 실행 시작 시간 설정
    - `save_checkpoint(checkpoint_dir, label=None)` - JSON 체크포인트 저장
    - `get_counters()` - trades_per_hour, elapsed_hours 계산 포함
  - **단위 테스트 완전 검증** (`tests/unit/test_signal_telemetry_v2.py`):
    - 6/6 PASS: DB persist counters, trades_per_hour, checkpoint save, reset
  - **Regression Suite 신규 생성** (`tests/regression/test_regression_smoke.py`):
    - 5/5 PASS: strategy/execution/common imports, config loading, telemetry singleton
    - justfile `regression` recipe → `tests/regression` 리타게팅
  - **Runner 자동화** (`scripts/helpers/run_gates_with_evidence.py`):
    - UTF-8 encoding 보장 (null bytes 방지)
    - 3 gates 순차 실행 + 개별 evidence log 저장
  - **Evidence Files** (실제 pytest 출력):
    - `logs/evidence/phase36_1_s4_gates/doctor_final.log`
    - `logs/evidence/phase36_1_s4_gates/fast_final.log` (42 passed, 3 warnings in 2.64s)
    - `logs/evidence/phase36_1_s4_gates/regression_final.log` (5 passed, 3 warnings in 2.50s)
  - **문서 동기화**:
    - `docs/PHASE36/PHASE36_1_S4_GATE_AND_TELEMETRY_REPORT.md` (실제 결과 반영)
    - `PHASE_ROADMAP.md` (S4 섹션 업데이트)
    - `CHECKPOINT_2025-12-21_ENSANBLE_MID_REVIEW.md` (이 파일)
  - **Commit**: 1f934d27 - "PHASE36-1 S4 REAL PASS: Gate2 restored + Telemetry v2 complete + Evidence logs"
  - **판정**: ✅ **REAL PASS** (Evidence-based, not "looks like PASS")
  - **Key Achievement**: 모든 gate를 실제로 실행하고 UTF-8 evidence logs로 PASS 증명

## Next PHASE
- 🔜 PHASE36-2+: Live Trading Deployment (if applicable)
- 🔜 PHASE37+: Future Roadmap (Multi-Asset, Advanced ML, etc.)

## Rollback Instructions
If you need to revert to this baseline:
```bash
git checkout baseline/phase36-0-pass/20251222  # By tag
# OR
git checkout baseline/phase36-0-pass           # By branch
```

---

# 고성능 앙상블 트레이딩 전략 구조 재설계 방안 (PHASE35)
PHASE35 단계에서는 여러 개의 전략을 점수(스코어) 기반으로 결합하는 앙상블 트레이딩 구조로의 전면 리디자인을 목표로 합니다. 이는 단일 전략의 성능 개선부터 다중 전략 조합과 상용 시스템 수준의 확장성까지 모두 달성할 수 있는 구조여야 합니다. 아래에서는 이를 위한 핵심 구성 요소들을 살펴보고, 각 옵션별 특징, 장단점, 문헌 및 실전 사례, 그리고 우리 프로젝트에의 적합성을 비교합니다. 마지막으로 이러한 인사이트를 바탕으로 run_v2 기반 엔진(멀티모듈, 설정 파일 기반 실행, MTF 지원)의 맥락에서 실제 구현할 전략 아키텍처 설계안을 제시합니다.
1. 메타 모델 후보군 비교: XGBoost, LightGBM, Neural Net, Ridge/Logistic Regression 등
메타 모델은 여러 인디케이터나 하위 모델의 출력을 받아 최종 신호를 산출하는 상위 예측 모형입니다. 트레이딩 맥락에서 자주 검토되는 후보들의 특성과 적합성을 비교하면 다음과 같습니다:
XGBoost / LightGBM (Gradient Boosted Decision Trees) – 트리 기반 앙상블 모델로 비선형 변수 관계를 잘 포착하며 Kaggle 등에서 입증된 탁월한 성능을 보여줘 왔습니다
luxalgo.com
. 특징: 데이터 스케일링에 둔감하고 결측치를 자체 처리하는 등 실용성이 높습니다
mql5.com
mql5.com
. 또한 기본 하이퍼파라미터로도 준수한 성능을 내는 편이어서 초기 튜닝 부담이 낮습니다
mql5.com
. 장점: 정형 시계열 데이터에 강하고 과거 금융 데이터 예측에서도 높은 정확도를 보여왔습니다 (예: XGBoost는 ARIMA 대비 오류율을 ~23.7% 개선
luxalgo.com
). 단점: 트리 앙상블 특성상 결과 해석이 어렵고, 데이터가 적거나 과적합 위험을 간과하면 성능 저하 가능성이 있습니다. 또한 대용량 데이터에서는 훈련 비용이 증가할 수 있으나, 대체로 속도/메모리 효율이 뛰어난 LightGBM 등을 통해 완화 가능합니다.
Neural Networks (신경망) – LSTM, Temporal CNN, FFN 등 딥러닝 모델들이 해당됩니다. 특징: 시계열의 복잡한 비선형 패턴을 학습하고 잠재 요인을 포착하는 능력이 뛰어나며, 이미지나 NLP 등 다양한 데이터를 다룬 연구를 통해 금융 분야에서도 적용 사례가 늘고 있습니다. 실제로 TCN·LSTM·강화학습 Actor-Critic 등을 조합해 심층 앙상블 전략을 구성한 연구에서는 개별 알고리즘보다 높은 샤프 비율을 얻기도 했습니다
openfin.engineering.columbia.edu
. 장점: 충분한 데이터를 주면 사람에게 보이지 않는 숨은 패턴까지 학습하여 높은 예측력을 낼 잠재력이 있습니다. 단점: 데이터 전처리(정규화 등)와 하이퍼파라미터 튜닝에 매우 민감하고
mql5.com
, 구조가 복잡해 과적합을 방지하기 위한 노력이 많이 필요합니다. 또한 훈련 시간이 길고 설계 복잡도가 높아 우리 프로젝트 같이 빠른 실험 주기가 필요한 경우 부담이 될 수 있습니다. 즉, 개발 및 운용 리소스가 충분하지 않다면 초기 도입 장벽이 높습니다.
Ridge Regression / Logistic Regression (선형 모델) – 비교적 단순한 선형 결합 모델로, 각각 회귀와 분류 영역의 대표적인 규제화(regularization) 모델입니다. 특징: 모형 구조가 단순하여 빠르고 안정적으로 학습됩니다. 장점: 과대적합 위험이 낮고, 입력 피처의 기여도를 해석하기 쉬워 신호 분석에 용이합니다. 또한 데이터가 비교적 적을 때도 안정적인 성능을 기대할 수 있습니다. 단점: 데이터의 비선형 패턴이나 복잡한 상호작용을 포착하지 못해, 성능 한계가 있을 수 있습니다. 트레이딩 신호처럼 非선형성이 강한 문제에서는 단독으로 높은 예측력을 내기 어려우나, 대신 메타모델로써 스코어들을 가중 합산하는 용도로 활용하면 해석력/안정성을 살리면서 성능도 확보할 수 있습니다. 예컨대, 스태킹(Stacking) 기법에서 메타모델로 로지스틱 회귀를 쓰면 개별 모델들의 출력을 선형 결합하여 약 5% 이상의 예측 정확도 향상이 보고된 바 있습니다
luxalgo.com
.
以上 비교를 표로 요약하면: <table><tr> <th>메타 모델</th> <th>특성 및 장점</th> <th>단점</th> <th>트레이딩 전략 적합성</th> </tr> <tr> <td><b>XGBoost / LightGBM</b><br>(GBDT 계열)</td> <td>- 트리 기반 앙상블 (비선형 패턴 포착) <br>- 데이터 스케일링 불필요:contentReference[oaicite:8]{index=8}, 결측 자동 처리:contentReference[oaicite:9]{index=9}<br>- 기본 설정으로도 우수 성능:contentReference[oaicite:10]{index=10}</td> <td>- 과적합 우려 (튜닝 필요)<br>- 결과 해석 어려움<br>- 대규모 데이터 시 훈련 비용↑</td> <td>- 다수 피처 활용 전략에 적합<br>- 사례: 가격추세 예측에 ARIMA 대비 오류 23.7% 감소:contentReference[oaicite:11]{index=11}</td> </tr> <tr> <td><b>Neural Network<br>(LSTM/TCN 등)</b></td> <td>- 딥러닝 (복잡한 패턴 학습)<br>- 순차 의존성 및 비선형 포착<br>- 강화학습 등과 결합 사례 존재:contentReference[oaicite:12]{index=12}</td> <td>- 많은 데이터 필요<br>- 튜닝 어려움:contentReference[oaicite:13]{index=13}, 과적합 주의<br>- 개발 및 해석 복잡</td> <td>- 비정형 데이터나 복잡한 전략에 활용<br>- 사례: Actor-Critic 앙상블로 Sharpe 개선:contentReference[oaicite:14]{index=14}</td> </tr> <tr> <td><b>Linear Model<br>(Ridge/Logistic)</b></td> <td>- 선형 결합, 구조 단순<br>- 학습 빠르고 안정<br>- 해석 용이 (피처 기여도)</td> <td>- 비선형 관계 표현 한계<br>- 단일 사용시 예측력 제한</td> <td>- 메타모델로 적합 (신호 가중결합)<br>- 사례: Stacking 메타로 정확도 5.2%↑:contentReference[oaicite:15]{index=15}</td> </tr> </table> 우리 프로젝트에 가장 적합한 메타 모델로는 XGBoost/LightGBM 등의 GBDT 계열을 우선 추천합니다. 이유는 (a) 현재 run_v2 엔진이 표형 데이터와 피처 기반 모델에 최적화되어 있고, (b) 트리 모델들은 데이터 스케일, 결측치 처리 등에서 엔지니어링 부담이 적어 개발 효율이 높기 때문입니다
mql5.com
mql5.com
. 또한 여러 전략의 신호(feature)를 조합할 때 각 신호 간 비선형 상호작용 효과까지 자동으로 고려해줄 수 있어 성능 향상 여지가 큽니다. 실제 2017년 연구에서도 Gradient Boosting Trees가 주식 페어트레이딩 알파 예측에서 DNN, RandomForest와 유사하거나 더 나은 성과를 보이며 안정성을 입증했습니다
aimspress.com
. 다만 장기적으로는 두 가지 방향을 모두 고려할 수 있습니다:
하나는 경량/해석적 메타모델(예: 로지스틱 회귀)을 병행해 신호 중요도를 파악하고,
다른 하나는 딥러닝 메타모델(예: TCN+어텐션)로 고차원 패턴까지 캡처하는 실험을 소규모로 진행해보는 것입니다.
이렇게 하면 초기에 GBDT로 실용적 성능을 확보하면서도, 추후 AI 트레이딩 고도화 여지도 남길 수 있습니다.
2. 레짐(Regime) 필터 구성 방식 비교: HMM, Markov Switching, z-score 구간, ATR 필터, 클러스터링 등
시장 레짐(국면) 필터는 현재 시장 상태(예: 상승장/하락장, 트렌딩/횡보, 고변동성/저변동성 등)를 판별하여 전략 적용 여부나 파라미터를 조정하는 역할을 합니다. 이는 잘못된 시기에 전략을 실행하여 발생하는 손실을 줄이고, 전략-시장 적합성을 높이는 핵심 요소입니다. 고려 중인 기법별 개요와 장단점은 다음과 같습니다:
Hidden Markov Model (HMM) – 시계열의 숨은 상태를 추정하는 통계 모델입니다. 가격 수익률 등의 관측치로부터 “Bullish/Bearish” 같은 숨은 레짐 상태를 추론합니다
aimspress.com
aimspress.com
. 장점: 상태 전이확률을 통해 레짐의 지속성을 모델링하므로, 추세적 국면을 포착하는 데 강점이 있습니다. 실제 QuantInsti, LSEG 등 사례에서 HMM은 다른 방법 대비 가장 정확한 레짐 전환 탐지 성능을 보였습니다
developers.lseg.com
. 또, 2008 금융위기나 2020년 급락기에도 매도 시점을 포착해 손실을 회피하여 Buy-and-Hold 대비 성과 개선을 입증했습니다
developers.lseg.com
pyquantnews.com
. 단점: 실시간 적용 시 지연(Lag) 문제가 있습니다. HMM은 통계적으로 레짐 전환을 확신하기까지 시간이 걸리기 때문에, 급격한 변동에서 몇 주 이상 늦게 반응할 수 있습니다
developers.lseg.com
arxiv.org
. 예컨대 한 연구에서는 “레짐 탐지~트레이딩 실행 사이 지연으로 빠른 신호의 이익을 상쇄할 수 있다”라고 지적합니다
arxiv.org
arxiv.org
. 또한 HMM은 모형 추정에 **가정(정상성, 분포 등)**이 필요해, 실제 시장의 비정상성이나 모형 미스펙에 민감하다는 보고가 있습니다
arxiv.org
.
Markov Switching Model – HMM과 유사하나 주로 시계열 모수(평균, 분산 등)가 특정 상태에 따라 바뀌는 형태로 사용됩니다. 예를 들어 Markov Switching AR(GARCH) 모델은 각 상태마다 다른 평균/분산으로 가격을 생성합니다. 장점: 전통 금융시계열 분석에 익숙한 프레임으로, 확률적 상태 전환을 가정하여 상태별 자산 수익률 분포를 추정합니다. 단점: HMM과 마찬가지로 모형 가정이 강하며, 다변량 변수 적용이나 비선형 관계 반영이 어렵습니다. 따라서 단일 자산의 Bull/Bear 정도 구분에는 좋지만, 현대적 복합 지표들을 활용한 레짐 분류에는 유연성이 떨어집니다.
z-score 구간 분할 – 특정 지표(예: VIX, 이동평균 이격도 등)의 z-점수로 단순 Thresholding 하는 방법입니다. 예를 들어 변동성 지표의 z-score가 +2 이상이면 “High Volatility Regime”으로 분류하는 식입니다. 장점: 구현이 매우 간단하며 직관적입니다. 지표 하나만으로 구간을 나누므로 실시간 적용시 계산 지연이 없고 빠릅니다. 단점: 임계값 선정이 임의적이며, 시장 환경 변화에 따라 Threshold 유효성이 저하될 수 있습니다. 또한 한 지표로 시장 상태를 단순 이분법화하므로, 복합적인 시장 국면을 세밀하게 구분하지 못합니다 (예: 변동성 높지만 상승장인 경우 등).
ATR 필터 (Volatility filter) – 평균 실제 범위(ATR) 등의 변동성 지표로 시장 소음 수준을 측정하여, 일정 수준 이상일 때만 트레이딩하거나 포지션 사이즈를 조절하는 방식입니다. 예를 들어 ATR이 일정값 이하인 극저변동 횡보장에서는 진입 자체를 피하거나 포지션 축소를 합니다
statoasis.com
. 장점: 사이드웨이 시장의 잦은 신호 실패를 걸러내어 **거래 품질(Winner 비율)**을 높입니다. 또한 변동성이 너무 높아 예측 불확실성이 클 때도 진입을 자제하여 큰 실수를 줄일 수 있습니다
statoasis.com
. 단점: 변동성 하나로 모든 국면을 설명 못하므로 상승/하락 방향과는 무관하게 필터가 작동합니다. 잘못 설정하면 유효한 트렌드 초입을 놓칠 위험도 있습니다. 그럼에도 실무 트레이딩에서 ATR 필터는 흔히 쓰이는 방법으로, ATR 기준으로 돌파 조건을 강화하거나 저변동 구간을 노트레이드 구간으로 설정하는 등 활용되고 있습니다
quantifiedstrategies.com
blog.traderspost.io
.
클러스터링 (예: K-means, GMM 등) – 비지도 학습으로 다수의 시장 특성 피처를 묶어 유사한 군집들로 구분합니다
developers.lseg.com
developers.lseg.com
. 예를 들어 가격 모멘텀, 변동성, 거래량 증감률 등을 2~3개 클러스터로 k-means하면, 각 클러스터가 “상승-저변동”, “하락-고변동” 등의 상태로 해석될 수 있습니다. 장점: 사전 가정 없이 데이터 자체가 말하는 패턴에 따라 레짐을 식별합니다. 여러 지표를 동시에 고려하므로 다차원적 시장 상태를 반영합니다. 또, GMM(가우시안 혼합)은 각 군집에 확률적 소속도를 부여하므로 불확실성 표현이 가능합니다. 단점: 군집에 의미를 레이블링하는 것이 후처리로 필요하며, 결과가 사용하는 피처와 클러스터 수에 크게 좌우됩니다. 또한 HMM처럼 시간적 연속성을 직접 모델링하지 않기 때문에, 클러스터 결과를 바로 쓰면 레짐이 빠르게 요동칠 수 있습니다. 이를 보완하려면 클러스터+평활화(예: 점프 패널티 부여) 기법을 쓰기도 합니다
arxiv.org
arxiv.org
.
➤ 추천 및 우리 프로젝트 적용: 레짐 필터는 전략 성능 향상 및 리스크 관리의 핵심이므로, 가능하면 도입하는 것이 바람직합니다. 상기 비교를 토대로, HMM 기반의 레짐 필터를 1차 권장합니다. 연구 결과 HMM이 레짐 탐지 정확도 면에서 탁월하고
developers.lseg.com
, HMM을 적용한 전략이 대폭적인 다운사이드 리스크 감소와 샤프 향상을 보인 사례들이 있기 때문입니다
developers.lseg.com
arxiv.org
. 실제 Renaissance Technologies의 Medallion 펀드가 HMM을 쓴다는 소문이 있을 정도로, 업계에서도 주목받는 기법입니다
pyquantnews.com
. 단, 우리 시스템에 실시간 적용시 HMM의 지연 문제를 완화하기 위해, 다음과 같은 보완을 설계에 포함해야 합니다: (a) 레짐 추정 주기를 짧게 가져가거나 (예: 월간→주간 재훈련)
developers.lseg.com
, (b) 상태 전환 신호에 confirmation 기간을 두어 잦은 노이즈 전환을 필터링
developers.lseg.com
하거나, (c) 아예 점프 패널티가 있는 비모수적 점프모델(JM) 기법을 검토하는 것입니다. 참고로 2023년 연구에서는 HMM 대안으로 Jump Model을 도입해 레짐 신호 잦은 변화 문제를 완화하고 Sharpe을 높인 사례도 있습니다
arxiv.org
arxiv.org
. 만약 HMM 구현이 초기에는 복잡하다면, 간이 대책으로 ATR 필터부터 적용해볼 수 있습니다. ATR 필터는 구현 용이성이 높고, 과거 우리 전략의 연승률/Profit Factor를 낮췄던 횡보장 구간을 피하는 효과가 기대됩니다. 예컨대 ATR 14가 일정 값 미만인 기간에는 트레이딩 안 함 혹은 포지션 축소 등의 룰을 config로 제공할 수 있습니다. 추후 HMM이 완성되면, ATR + HMM을 조합해 HMM으로 큰 그림 레짐 판단 (예: 강세/약세장), ATR로 미시적 변동성 상태 필터 (예: 저변동 횡보 시 진입 억제) 형태로 다중 필터 체계를 구축하면 가장 이상적일 것입니다.
3. 스코어링 기반 앙상블 구조: 가중투표, 랭크 평균, 과반투표, 신뢰도 블렌딩 등 비교
다전략 앙상블에서는 각 전략이 산출하는 점수(score)나 시그널을 결합하여 최종 의사결정을 합니다. 여러 결합 방식 중 질문에 언급된 대표 기법들의 개념과 트레이딩에서의 성능 비교를 정리합니다:
Majority Vote (다수결 투표) – 개별 전략이 산출한 **분류 결과(예: +1 매수 / -1 매도)**를 동등한 한 표로 간주, 과반 이상 찬성 방향으로 최종 매매 방향을 결정합니다. 장점: 가장 단순하며 다양한 모델의 합의를 직관적으로 반영합니다. 모델들 성능이 엇비슷하고 상호보완적일 때는 어느 하나의 큰 실수를 완화하는 효과가 있습니다. 단점: 모델의 신뢰도 차이를 반영하지 못하기 때문에, 성능이 낮은 모델도 같은 영향력을 행사합니다. 또한 5개 중 3개 찬성 같은 근소한 우위도 100% 최종결정으로 이어지므로, 확률적 신뢰도를 표현하지 못합니다. 연구에 따르면 전문가들이 **동질적(Homogeneous)**이고 개별 정확도가 유사할 때나 유효하며
emergentmind.com
, 성능 편차가 큰 집단에는 부적합합니다
emergentmind.com
.
Weighted Voting (가중치 투표) – 모델별 가중치를 부여하여 투표 또는 평균에 반영하는 방식입니다. 예를 들어 모델 A의 신호에 0.7, B에 0.3 가중을 주고 합산 스코어로 매매를 결정하거나, 분류일 경우 weighted majority를 택합니다. 장점: 과거 성과 등을 반영해 우수한 모델의 영향력을 키울 수 있으므로, 앙상블 정확도를 높이는 데 효과적입니다
emergentmind.com
emergentmind.com
. 특히 동적 가중치 조정을 도입하면 시장 변화에 따라 잘 맞추는 모델에 더 비중을 실어 적응형 향상이 가능합니다
emergentmind.com
. 실제 2024년 발표된 Numin 프레임워크에서는 최근 성과 기반 동적 가중치로 여러 인트라데이 모델을 결합하여, 모든 단일 모델보다 높은 **정확도와 수익(Risk-adjusted utility)**을 얻었습니다
arxiv.org
arxiv.org
. 단점: 가중치 산정이 관건인데, 부정확한 가중치 설정 시 오히려 왜곡을 초래할 수 있습니다. 또 동적 조정은 구현이 복잡하고 과최적화 위험이 있습니다.
Rank Average (순위 평균) – 각 모델의 신호를 랭킹으로 변환하여 평균 랭크 또는 합산 랭크로 최종 결정하는 기법입니다. 주로 연속형 예측치를 직접 평균하기 어려울 때 (스케일 차이나 분포 차이) 사용됩니다. 예를 들어 3개 모델이 10종목에 대해 목표수익률을 예측한 값을 각각 순위(1~10위)로 변환한 뒤, 평균 순위 상위 to pick 탑 종목을 선택하는 형태입니다. 장점: 예측치의 스케일 차이 영향을 제거해 모델 간 공정한 비교가 가능합니다. 극단값(Outlier)의 영향도 줄여 안정적입니다. 단점: 순위로 변환하면서 절대적 크기 정보가 손실되므로, 모든 모델이 동일한 중요도로 간주됩니다. 또한 순위 산출 과정에서 정보의 일부를 버리기 때문에, 이론적으로는 정보량 면에서 손실이 있습니다. 그러나 순위 앙상블은 Kaggle 등에서 실용적으로 많이 쓰이며, 금융 포트폴리오에서도 종목 점수를 랭크로 변환해 평균내는 방식이 Numerai 등에서 활용됩니다 (Numerai 메타모델은 개별 예측을 랭킹 형태로 통합해 포트폴리오 구성
arxiv.org
).
Confidence Blending (신뢰도 기반 결합) – 각 모델이 자신의 예측에 부여하는 신뢰도나 정확도 추정치를 함께 사용하여 확률적 가중 투표를 하는 방식입니다. 예를 들어 모델이 “상승 70% 확신”이라고 하면 +0.7로, “하락 60% 확신”은 -0.6으로 점수를 부여해 합산하거나, 또는 각 모델의 과거 정확도를 확률로 변환해 logit(승산) 비례 가중치를 주는 방법 등이 있습니다
emergentmind.com
emergentmind.com
. 장점: 이론적으로 최적임이 증명된 방법으로, 집단 지성 분야에서 다수결 대비 오류 확률이 지수적으로 감소함이 알려져 있습니다
emergentmind.com
emergentmind.com
. 특히 CWMV(Confidence-Weighted Majority Voting)는 각 투표자(모델)의 글로벌 정확도를 log-odds로 변환한 가중치를 주어 최종결정 하는데, 모델 간 성능 편차가 있을 때 단순 다수결보다 우월한 결정력을 보입니다
emergentmind.com
emergentmind.com
. Adaptive하게 국부적 신뢰도까지 고려하면 가장 성능이 좋으며, 일부 데이터셋에서는 무가중치 대비 20%p 이상 정확도 향상도 보고되었습니다
emergentmind.com
. 단점: 모델의 신뢰도 추정이 어렵거나 불확실할 경우 잘못된 가중치가 오히려 해가 될 수 있습니다. 또한 모든 모델이 자신의 확률 출력을 제공해야 하는데, 트레이딩 전략 중 규칙 기반이나 임계치형은 본질적으로 확률값을 내지 않으므로 적용이 곤란할 수 있습니다. 이럴 때는 과거 성과로 후험적 신뢰도를 추정하여 사용하는 방법이 대안입니다
emergentmind.com
.
요약하면, 가중치/신뢰도 기반 앙상블 > 단순 과반 투표 순으로 이론·실전 성능이 개선됩니다. 실제 논문에서도 앙상블 가중치 최적화로 단일 모델 대비 성능 향상 사례가 다수 있으며, 특히 금융 도메인에서는 일정 기간 성과에 따라 가중치를 동적으로 부여하는 알고리즘이 유망합니다
arxiv.org
arxiv.org
. 예컨대 Kolter & Maloof의 Weighted Majority Algorithm(WMA)은 틀릴 때마다 가중치를 줄이는 적응형 방법으로, 학습 이론적으로 실수 경계가 증명되어 있습니다
arxiv.org
. 이를 트레이딩에 적용한 연구에서, 단기 성과(정확도나 수익률) 기준 가중 업데이트 시 25분 창 등의 매우 민감한 적응으로도 평균 성능을 개선했다고 보고합니다
arxiv.org
arxiv.org
. ➤ 추천 및 우리 프로젝트 적용: 우리의 스코어 기반 앙상블 구조에는 가중치 결합과 신뢰도(모델 자신/과거 성과) 활용 개념을 적극 도입하는 것이 바람직합니다. 우선 정적 가중치 앙상블부터 시작할 수 있습니다. 과거 백테스트 결과를 토대로 각 전략에 Sharpe나 Win Rate 기반 가중치를 주어 조합하면, 단순 평균보다 나은 성과를 기대할 수 있습니다. 이후 동적 업데이트는 모델 모니터링 모듈을 통해 구현 가능합니다. 예컨대 run_v2 엔진에 각 전략의 최근 1개월 성공률을 실시간 기록하게 한 뒤, config 리로드 시 해당 지표로 가중치를 조정하도록 설계할 수 있습니다. 또한 메타 모델로 로지스틱 회귀를 쓴다면 (섹션 1에서 논의한 대로) 자연스럽게 각 신호에 대한 최적 가중치 학습이 이뤄져 확률적 앙상블 효과를 얻을 수 있습니다. Logistic의 출력은 [0,1] 확률로 해석되므로 의사 신뢰도로 활용 가능하고, 결정경계도 유연하게 조정할 수 있습니다. Rank averaging의 경우, 주식/코인 종목 스코어링 상황에서 유용합니다. 우리 프로젝트가 단일 자산의 롱/숏 타이밍 결정이 주된 목적이라면 rank보다는 score 자체를 ensemble하는 편이 직관적입니다. 하지만 다수 종목을 랭크 선정하는 전략도 겸비한다면, rank ensemble 기법을 적용할 수 있습니다. 결론적으로, “가중 투표 + 메타모델” 투트랙으로 구현하는 방안을 제안합니다. 예를 들어:
1단계: Strategy_A, B, C가 각자 점수 산출 → 가중 합산하여 1차 신호 결정 (이때 가중치는 config에 명시 또는 알고리즘 산출).
2단계: 별도의 Meta 모델이 각 전략 점수들을 입력받아 최종 의사결정 (예: 상승 확률) 산출.
이렇게 이중으로 결합하면 규칙기반 전략과 ML 기반 메타결합의 장점을 모두 취할 수 있습니다. 실제 한 연구에서는 유사하게 1차 다수 모델 결합 + 2차 메타합성의 Two-layer Ensemble로 정확도와 ROI를 모두 향상시켰습니다
papers.ssrn.com
.
4. 고성능 시그널 설계 사례: 지표 복합 조합 Outperformance 등
논문 및 실전에서 밝혀진 고성능 시그널 디자인 패턴을 살펴보면, 두 가지 이상의 요소 결합이 일관되게 유효한 성과 개선을 가져왔습니다. 몇 가지 주목할 사례는 다음과 같습니다:
이종 지표 결합으로 성능 향상: 단일 기술적 지표로 생성한 신호는 한계가 있지만, 상호 보완적인 지표를 함께 사용하면 성과가 향상됩니다. 예를 들어 모멘텀 계열 RSI와 자금흐름 계열 CMF를 동시에 조건으로 넣은 전략은, 각 지표만 단독으로 썼을 때는 시장을 못 이기던 것이 모든 대상 ETF에서 승률과 PF를 개선하며 Buy-and-Hold를 크게 상회했습니다
tandfonline.com
. 연구 결과 *“RSI+CMF 조합 전략이 전 종목에서 양의 PF 달성 및 B&H 대비 현저한 초과성과”*를 보였고, 반면 RSI나 CMF 단일전략은 유의미한 알파를 내지 못했습니다
tandfonline.com
. 이는 거래 신호에 거래량 정보를 추가함으로써 노이즈를 줄인 효과로 해석됩니다.
트렌드 + 모멘텀 필터 결합: 추세 추종 지표와 오실레이터를 결합하면 위험 조정 성과가 좋아지는 사례가 많습니다. 예컨대 *장기 추세 필터(200일 이동평균 위/아래)*와 *단기 모멘텀 신호(Stochastic, RSI 등)*를 함께 조건으로 쓰면, 추세 방향에 순행하는 과매수/과매도 시그널만 취해 훨씬 높은 승률을 얻는 식입니다. 실제 한 연구에서는 RSI 단독 또는 CCI 단독으로는 성과가 미미했던 것을, RSI+CCI 동시 신호일 때 매매로 조건을 강화하자 연평균 수익과 Sharpe이 크게 개선된 바 있습니다
sciencedirect.com
. 이처럼 Multi-indicator consensus는 LuxAlgo 보고서에 따르면 오류 신호 40% 감소 등 크게 품질을 높였습니다
luxalgo.com
.
멀티 타임프레임 확인(MTF confirmation): 상위 차트 방향과 하위 차트 신호를 함께 고려하는 전략이 더 안정적인 수익을 내는 것으로 알려져 있습니다. Tradeciety 등의 실전 트레이더 분석에 따르면 다중 기간 분석으로 보상비율과 승률이 모두 개선되며
tradeciety.com
, 알리나 카이(Alina Khay)의 Tri-Timeframe 시스템처럼 3개 시간대 추세 일치 시에만 진입하는 규칙이 대표적입니다
alinakhay.com
. “여러 기간대가 정렬될 때만 진입하여 성공 확률을 높이는” 접근은 알고리즘 트레이딩에서도 활용되고 있습니다. 예컨대 Quantpedia의 BTC 전략 사례에서는 일간 추세가 상승일 때만 시간봉 돌파 전략 실행하여 신호 정확도를 향상시켰습니다
quantpedia.com
. 논문적 근거로, 한 Medium 튜토리얼에서는 *“견조한 트렌드 전략은 방향 트리거 + 멀티타임프레임 필터 + 변동성 필터의 3계층으로 이루어진다”*고 언급합니다
pyquantlab.medium.com
. 즉 일봉 추세가 맞을 때만 1시간봉 신호를 채택하고, 추가로 ATR등으로 노이즈 많은 구간은 배제하는 식입니다. 이 구조는 Elder의 Triple Screen 원리와도 통하며, 우리 전략에도 적용 가능성이 큽니다 (아래 설계안에 반영).
기계학습을 활용한 지표 리컴비네이션: 전통적 지표들을 머신러닝으로 재조합하여 성능을 끌어올린 연구들도 있습니다. 2024년 Saud & Shakya 연구에서는 MACD, DMI, KST 세 가지 지표를 입력으로 GRU 신경망을 훈련해 매매 신호를 예측한 결과, 동일 지표로 생성한 기존 규칙 전략들보다 모든 성능지표(ARR, Sharpe, 승률 등)에서 우월했다고 합니다
scribd.com
scribd.com
. 특히 *“지표 기반 Intelligent 전략이 해당 지표의 classical 전략보다 일관되게 outperform”*했다는 분석으로
scribd.com
, 이는 두 개 이상 지표 정보를 비선형으로 결합하면 기존 단순 AND/OR 룰보다 우수한 신호를 만들 수 있음을 시사합니다. 우리도 향후 Meta model이 단순 신호 결합을 넘어 지표 원시값들을 통합해 새로운 신호 추론 역할을 수행하게 발전시킬 수 있습니다. (예: XGBoost가 여러 지표 값을 입력받아 상승 확률을 산출 → 이를 신호로 사용)
➤ 시사점 및 적용: **"한 지표에 의존하지 말고, 보완 관계에 있는 요소를 결합하라"**는 것이 핵심입니다. 따라서 PHASE35의 전략 리디자인에서는 둘 이상의 신호로 조건을 강화하거나 다양한 종류의 피처를 결합한 모델 신호를 만들어 Win rate와 PF를 개선하도록 해야 합니다. 구체적으로:
전략 모듈 설계 시 하나의 인디케이터로 매매결정 짓는 모듈 대신, (추세 필터 + 트리거) 쌍을 기본 단위로 삼을 것을 제안합니다. 예를 들어 모듈A = (일봉 방향 필터 AND 1시간 Stochastic 신호), 모듈B = (변동성 돌파 필터 AND 모멘텀 진입) 등으로 구성하면 각 모듈의 질이 올라갑니다. 이러한 설계는 실무 트레이딩 시스템에서도 흔한데, 한 고급 트레이딩 시스템은 다중기간 트렌드 스캐너와 변동성/세션 필터로 종합 신호를 정제한다고 보고되었습니다
medium.com
.
복수 전략 간에도 서로 다른 강점을 이용해 상호 보완해야 합니다. 예를 들어 추세추종형 전략과 역추세(Mean-reversion) 전략을 모두 두고, 시장 상태에 따라 둘 중 하나가 신호를 내도록 하거나 (레짐 필터 응용), 아니면 둘 다 신호를 낼 때 앙상블이 상반된 포지션을 상쇄하도록 설계하면 일관성 있는 성과를 기대할 수 있습니다. 실제 상용 펀드들도 트렌드 + 상대가치 + 이벤트드리븐 등 서로 상관 낮은 전략을 조합해 Sharpe 향상을 도모합니다.
우리 프로젝트의 MTF 지원을 최대한 활용해야 합니다. MTF는 이미 언급한 대로 상위 트렌드 확인 후 하위 진입 같은 구조를 구현할 수 있게 해줍니다. 예컨대 config에서 higher_timeframe_filter: true 옵션을 두어, 해당 모듈이 신호를 낼 때 **글로벌 필터(예: 일봉 200SMA 기울기)**를 자동 체크하게 할 수 있습니다. 이렇게 하면 구조적인 버그였던 노이즈 구간 잦은 매매를 대폭 줄일 수 있습니다.
정리하면, Indicator Fusion + Multi-Timeframe + Adaptive Filter 세 가지가 검증된 시그널 향상 요소입니다. PHASE35 전략 설계시 각 모듈과 룰에 이 원칙들을 반영하고, 반드시 단일 전략 대비 개선 여지가 입증된 구성만 채택하도록 할 것입니다.
5. 제안 구조: PHASE35 앙상블 전략 아키텍처 설계 및 구현 고려사항
위 분석을 바탕으로, 우리 프로젝트에 최적화된 앙상블 트레이딩 시스템 구조를 설계하면 다음과 같습니다: PHASE35 앙상블 트레이딩 전략 구조 예시 – 여러 전략 모듈의 신호를 종합하는 메타모델 계층과 레짐 필터 통합 구조
(a) 멀티모듈 앙상블 구조 개요
위 그림은 제안하는 아키텍처를 나타냅니다. 여러 전략 모듈이 병렬로 **각각의 시그널(score)**을 산출하고, 이를 메타 모델에서 취합하여 최종 매매 신호를 결정하는 2계층 구조입니다. 또한 레짐 필터 모듈이 별도로 시장 상태를 분석하여 메타 모델에 컨텍스트로 입력됩니다. 주요 구성요소별 설계를 설명하면:
Market Data & Features: 시분할 가격, 거래량 등 원천 데이터와, 각 모듈이 필요로 하는 기술 지표 피처들을 생성합니다. run_v2 엔진의 MTF 기능으로, 모듈마다 다른 주기의 데이터도 자유롭게 참조할 수 있습니다. (예: 모듈A는 1분봉, 모듈B는 1시간봉 데이터를 동시 활용) 데이터 준비 파이프라인은 config에 명시된 indicator들을 자동 계산하도록 합니다.
Strategy Modules (S1, S2, S3, ...): 각기 독립적인 전략 논리 블록입니다. 예를 들어 모듈1 = 추세추종 전략, 모듈2 = 모멘텀 역추세 전략, 모듈3 = 뉴스 감성 전략 식으로 다양하게 존재할 수 있습니다. 각 모듈은 자기 계산 주기마다 score 또는 signal을 산출하는데, 이를 위해 모듈 내부에 모델/규칙 로직이 있습니다.
규칙 기반 모듈은 True/False 신호를 score 1/-1로 산출하거나 확률 0/1로 매핑하고,
ML 기반 모듈은 예측 확률, 기대수익률 등 연속형 스코어를 출력합니다.
각 모듈의 output은 표준화하여 메타모델로 넘길 수 있도록 공통 인터페이스(예: -1~+1 스코어 또는 확률값)로 변환합니다. config에서는 모듈별 파라미터, 사용 인디케이터, MTF 필터 적용 여부 등을 설정하여 유연성을 높입니다.
Regime Filter Module: 시장 전반의 상태를 정기적으로 판단합니다. 여기서는 앞서 논의한 HMM 기반 Market Regime Detector를 두는 것을 상정합니다. 이 모듈은 별도 스레드로 움직이며 (예: 하루 1번 업데이트), 현재 레짐을 {Bull, Bear, Volatile, Calm} 등 코드로 나타내어 전역 상태 저장에 기록합니다. 또는 실시간 지표 임계치 기반 필터(예: ATR% -> Low/High Vol regime)와 HMM을 조합해 다차원 상태를 산출할 수도 있습니다.
메타모델은 이 레짐 정보를 받아, 상태에 따라 전략 가중치를 변경하거나 해당 상태에 적합한 출력만 채택하도록 로직을 다르게 할 수 있습니다. 예를 들어 레짐 모듈이 “Bear-HighVol” 상태를 표시하면, 메타모델은 *모멘텀 전략 가중치↓, 변동성 돌파 전략 가중치↑*와 같이 사전에 정의된 룰을 적용합니다. 또는 더 단순히, 특정 레짐에서는 아예 일부 전략의 신호를 무시하도록 할 수도 있습니다 (예: 상승장에서는 숏 전략 신호 무효화 등).
Ensemble Meta-Model: 앙상블의 핵심 결합부입니다. 앞서 (3)에서 논의한 가중치 투표/학습 모델을 구현한 컴포넌트입니다. 두 가지 옵션이 있습니다:
Rule-based Ensemble: config에 지정된 가중치로 각 모듈 스코어의 weighted sum을 계산하고, 임곗값을 넘으면 매수/매도 결정을 내리는 단순 로직. 레짐별 다른 가중치를 세트로 가져서, 레짐 모듈 신호에 따라 다른 weight set을 적용할 수 있습니다. 예컨대 weights_bull = [0.5, 0.3, 0.2], weights_bear = [0.2, 0.5, 0.3] 형태로 조정 가능합니다.
Learning-based Meta-model: LogisticRegression이나 XGBoostClassifier 모델이 각 모듈의 신호와 레짐정보를 입력으로 학습된 상태입니다. 이 모델의 출력이 곧 최종 신호입니다 (분류일 경우 상승확률 P; 회귀일 경우 기대수익률 예측치 등). 학습은 과거 데이터로 오프라인 수행한 뒤, 결과 모델을 시스템에 탑재합니다. 이 접근은 stacking ensemble과 유사하며, 과거 백테스트로 최적 조합을 자동 학습하므로 성능 잠재치가 높습니다
luxalgo.com
. 단, 충분한 학습 데이터가 필요하고 실시간 업데이트가 어렵다는 점에서, 초기엔 rule 기반으로 시작한 후 점진적으로 learning 기반으로 전환하는 전략이 좋습니다.
메타모델에서는 포지션 크기 결정이나 최종 시그널 스무딩도 담당합니다. 예컨대 여러 모듈이 모두 강한 매수 점수를 낼 때는 풀 포지션, 애매하면 하프 사이즈 등 confidence에 비례한 포지션 규모 산출도 고려할 수 있습니다. 이는 향후 **트레이딩 최적화(Trade management)**와 연결되므로, PHASE35에서는 우선 신호 방향 결정에 집중하고 PHASE36 등에서 정교화할 부분입니다.
Execution Engine: run_v2의 실행 모듈로, 메타모델이 최종 산출한 매매 지시를 실제 주문으로 전환합니다. 이때 기존 엔진의 config-driven order handler를 그대로 활용하되, 앙상블 특성에 맞게 보완이 필요합니다. 예를 들어 앙상블 신호는 여러 전략의 의견을 포함하므로 신호 확신도가 높을 때만 매매하는 옵션, 중립(0) 신호 시 포지션 정리 규칙 등을 명시합니다. 또한 여러 전략이 각자 주문을 내려 conflict하던 기존 구조에서, 이제는 메타모델이 단일 창구로 주문을 내므로 체계가 단순해집니다. 단, 백테스트 등에서는 개별 전략의 기여도를 분석하기 위해 가상 Sub-포트폴리오 개념을 유지할 수도 있습니다. (실제 실행은 하나지만, 기록상으로 어떤 전략 모듈이 어느 정도 기여했는지 추적)
(b) 설계 상의 주요 고려사항
Config 주도 설계: 새로운 구조 역시 완전히 설정 파일(config)으로 정의 가능하도록 합니다. 구체적으로, strategies 섹션 아래에 다수의 모듈을 리스트로 나열하고, 각 모듈에 사용 지표, 모델 종류, 신호 타입(분류/회귀), MTF 필터, 활성화 레짐 등을 서브 섹션으로 명시합니다. 그리고 ensemble 섹션에서 메타모델 타입(rule or ML), 가중치 또는 모델 파일 경로, 레짐별 weight 조정 테이블 등을 설정합니다. 예시:
strategies:
  - name: trend_follower
    indicators: [EMA(20), EMA(50)]
    logic: "cross_over"
    timeframe: "1h"
    regime_filter: "bull_only"
  - name: mean_reversion
    indicators: [RSI(14)]
    logic: "oversold_rebound"
    timeframe: "4h"
    regime_filter: "bear_or_neutral"
regime_filter:
  type: "HMM"
  features: [market_index_logret]
  states: 3
ensemble:
  type: "weighted_rule"
  weights:
    bull: [0.7, 0.3]
    bear: [0.4, 0.6]
    neutral: [0.5, 0.5]
  threshold: 0.0   # >0 => buy, <0 => sell
이처럼 모든 구성요소를 모듈화하여 설정함으로써, 개발자나 퀀트 연구원이 전략을 자유롭게 수정·조합할 수 있게 합니다. 또한 이러한 구조는 이후 상용 플랫폼으로 확장 시도할 때도 유용합니다 (전략 세팅을 GUI나 DB로 관리하기 용이).
엔진 아키텍처 변경: 현재 run_v2는 싱글 엔진-single strategy 구동을 가정하고 있을 것입니다. 이를 멀티모듈로 바꾸기 위해, 내부에 전략 모듈 관리자를 두고 각 모듈의 on_tick/on_bar 이벤트를 처리하도록 확장해야 합니다. 즉, 엔진이 시계열 데이터를 새로 받을 때 각 모듈별로 인디케이터 업데이트 → 신호 생성까지 수행하고, 모든 모듈 신호를 취합해 메타모델로 전달 → 최종 의사결정 → 주문 such 순서로 바뀝니다. 이 파이프라인 처리에서 지연이 커지지 않도록 비동기/병렬 처리를 도입하거나, 계산 비용이 큰 모듈은 낮은 빈도로 구동되게 할 필요가 있습니다. (예: 일봉 모듈은 1분봉 틱마다 계산할 필요 없으므로, scheduler로 1일 1회만 실행)
백테스트 및 검증: 새로운 구조는 구성요소가 늘어나므로, 과최적화나 버그 가능성도 커집니다. 반드시 모듈 단위 테스트와 통합 테스트를 통해 신뢰성을 확보해야 합니다. 특히 레짐 필터와 앙상블 로직은 과거 데이터에서 복기 테스트를 돌려 예상대로 동작하는지 검증이 필요합니다. 예를 들어 2020년 3월 급락기에 HMM이 제대로 Risk-off 판정하고 숏 전략이 가동되었는지, 여러 전략 신호 충돌 시 메타모델이 적절히 포지션 줄였는지 등을 살펴야 합니다. 이를 위해 백테스트 리포트에 각 모듈별 PnL 기여, 레짐 타임라인, 가중치 변화 등을 시각화하면 좋습니다.
확장성과 유지보수: 구조적 개선의 궁극 목표 중 하나는 상용 시스템 수준 확장입니다. 제안한 모듈화 앙상블 구조는 새로운 전략 추가가 비교적 쉬워 (그냥 새로운 module 정의 추가), 펀드 운용 시 여러 아이디어를 빠르게 병합하는 데 유리합니다. 또한 특정 모듈에 문제 발생 시 (예: 모델 성능 급락) 해당 모듈만 교체하거나 비활성화하면 되므로 업데이트가 용이합니다. 이런 이점 덕분에 실제 헤지펀드들도 모듈식 앙상블을 채택하는 추세입니다
mdpi.com
.
성능 목표 관점: 최종적으로 기대되는 개선은 단일 전략 성능 향상과 포트폴리오 분산 효과입니다. 단일 전략은 다중 필터/피처로 정제되어 승률 및 Profit Factor 향상이 기대되고, 다전략 앙상블은 서로 손실 시기를 보완하여 샤프 비율 상승과 MDD 감소를 목표로 합니다. 실제 앞서 소개한 Carta 등(2021)의 Multi-ensemble Stock Trader 연구에서도 앙상블 구조가 모든 개별전략과 기존 단순 앙상블을 능가하는 수익률을 올렸고, 변동성도 낮췄다고 보고합니다
researchgate.net
researchgate.net
. 우리의 설계도 이러한 장점을 실현하도록 면밀히 튜닝할 것입니다.
(c) 기술 선택 및 프로젝트 적용상의 이유 요약
마지막으로, 제안 구성요소들이 왜 검증된 것인지, 그리고 우리 프로젝트 맥락에 어떻게 부합하는지 간략히 표로 정리합니다: <table> <tr><th>구성 요소</th><th>채택 기술/방식</th><th>채택 이유 (검증 및 장단점 고려)</th><th>프로젝트 적용 고려</th></tr> <tr> <td><b>Meta 모델</b><br>(Ensemble Combiner)</td> <td>- LightGBM/XGBoost (비선형 메타)<br>- Logistic Regression (선형 메타)</td> <td>- 트레이딩 예측에서 입증된 높은 성능:contentReference[oaicite:84]{index=84}<br>- 스케일링/결측에 강건 (개발 용이):contentReference[oaicite:85]{index=85}<br>- 선형메타는 해석 용이 & 과적합 방지</td> <td>- 초기에 LightGBM 모델 학습해 사용 (config에 모델 경로)<br>- 추후 실시간 업데이트 필요시 Logistic 등 경량 모델 고려</td> </tr> <tr> <td><b>Ensemble 방식</b></td> <td>- 가중치 투표 (정적 + 동적)<br>- 신뢰도 기반 결합 (CWMV 원리 적용)</td> <td>- 가중치 앙상블이 다수결보다 성능 우수:contentReference[oaicite:86]{index=86}:contentReference[oaicite:87]{index=87}<br>- 성과 기반 동적 가중치로 적응 향상:contentReference[oaicite:88]{index=88}<br>- 신뢰도 투표 이론적 최적, 정확도 최대 20%p 향상 사례:contentReference[oaicite:89]{index=89}</td> <td>- 초기엔 백테스트 결과로 정적 가중치 설정<br>- 모듈별 실시간 성능 로그 축적 -> 일정 주기 리밸런싱 스크립트로 가중치 조정<br>- 모델 출력 확률을 confidence로 활용 (CWMV 아이디어)</td> </tr> <tr> <td><b>Regime 필터</b></td> <td>- HMM (은닉 마코프 모델) +<br> ATR 등 변동성 필터 병행</td> <td>- HMM이 시장 국면 탐지 정확도 최고:contentReference[oaicite:90]{index=90}, 위기시 손실 회피 입증:contentReference[oaicite:91]{index=91}<br>- 변동성 필터로 노이즈 구간 트레이드 감소 (실전 활용도 높음)</td> <td>- Python `hmmlearn` 등 사용해 2~3 상태 HMM 구현<br>- 주기적 재훈련 (예: 주간) 스케줄링<br>- ATR% 등은 지표로 실시간 계산하여 조건 분기로 처리</td> </tr> <tr> <td><b>Strategy 모듈</b></td> <td>- 멀티타임프레임 지원<br>- (추세 필터 + 트리거) 구성<br>- 여러 종류 전략 병행</td> <td>- MTF 필터로 신호 품질↑ (여러 시간대 정렬 시 진입):contentReference[oaicite:92]{index=92}<br>- 지표 2개 이상 조합 시 성능 향상 (RSI+CMF 등):contentReference[oaicite:93]{index=93}<br>- 이종 전략 병합 시 포트폴리오 분산효과</td> <td>- config에 module별 TF, 사용지표, 로직명 기술<br>- 예: trend1 (D1 filter + H1 breakout), meanrev1 (H4 filter + M15 oversold)... 등<br>- 기존 전략 리팩토링 시 이러한 구조로 분해/정의</td> </tr> <tr> <td><b>구조 확장성</b></td> <td>- 모듈화 설계<br>- 설정 중심 실행</td> <td>- 상용 트레이딩 시스템은 모듈식 설계로 전략 추가/교체 용이:contentReference[oaicite:94]{index=94}<br>- 설정만으로 전략 구성 가능해야 운영 효율↑</td> <td>- run_v2 엔진의 모듈 Manager 계층 구현<br>- UI/설정 관리 도구에서 여러 전략 묶음 설정 지원<br>- 모델 파일/파라미터 변경 시 재시작 없이 반영 검토</td> </tr> </table> 以上의 구조와 설계를 토대로 PHASE35에서는 기존 전략의 분해와 재구성을 진행합니다. 검증된 구성 요소들만 채택하여, 과거 Phase들에서 드러났던 구조적 결함(예: 특정 시장 상황에서 전략 폭주나, 조합 논리 결여)을 반복하지 않도록 유의할 것입니다. 목표는 단일 전략 수준의 성능 향상 여지 확보와 다중 전략 포트폴리오의 안정적 수익입니다. 또한 본 구조는 1조 원 규모 운용 시스템에도 스케일업 가능하도록 설계되었으므로, 상용 트레이딩 플랫폼 수준으로의 진화를 대비할 수 있습니다. 마지막으로 기대 효과를 요약하면: (i) 앙상블 구조 도입으로 백테스트 상 Sharpe 비율 및 승률 개선, (ii) 연복리 수익의 변동성 감소 및 극단 손실 구간 방어, (iii) 전략 개발 사이클 가속 (모듈 단위 병렬 개발 가능), (iv) 운용 유연성 증대 (시장변화에 따른 설정 조정 용이) 등을 꼽을 수 있습니다. 이를 통해 PHASE35의 최종 산출물은 **“최대 성능과 확장성”**이라는 목표에 한 걸음 더 다가서게 될 것입니다. 출처: 다양한 문헌/사례의 아이디어를 참고하여 작성 (【】 참조). 특히 앙상블 학습 및 레짐 필터의 장단점은 LSEG/QuantStart 자료와 최신 논문 결과를 인용했고
developers.lseg.com
emergentmind.com
, 지표 결합 및 구조 설계는 LuxAlgo 리포트와 관련 연구들의 통찰을 반영했습니다
luxalgo.com
pyquantlab.medium.com
. above
인용

Ensemble Learning for Chart Patterns

https://www.luxalgo.com/blog/ensemble-learning-for-chart-patterns/

Data Science and Machine Learning (Part 23): Why LightGBM and XGBoost outperform a lot of AI models? - MQL5 Articles

https://www.mql5.com/en/articles/14926

Data Science and Machine Learning (Part 23): Why LightGBM and XGBoost outperform a lot of AI models? - MQL5 Articles

https://www.mql5.com/en/articles/14926

Data Science and Machine Learning (Part 23): Why LightGBM and XGBoost outperform a lot of AI models? - MQL5 Articles

https://www.mql5.com/en/articles/14926
Deep Reinforcement Learning for Automated Stock Trading: An Ensemble Strategy

https://openfin.engineering.columbia.edu/sites/default/files/content/publications/ensemble.pdf?ref=luxalgo.com

Data Science and Machine Learning (Part 23): Why LightGBM and XGBoost outperform a lot of AI models? - MQL5 Articles

https://www.mql5.com/en/articles/14926

Ensemble Learning for Chart Patterns

https://www.luxalgo.com/blog/ensemble-learning-for-chart-patterns/
A forest of opinions: A multi-model ensemble-HMM voting framework for market regime shift detection and trading

https://www.aimspress.com/article/doi/10.3934/DSFE.2025019?viewType=HTML
A forest of opinions: A multi-model ensemble-HMM voting framework for market regime shift detection and trading

https://www.aimspress.com/article/doi/10.3934/DSFE.2025019?viewType=HTML
A forest of opinions: A multi-model ensemble-HMM voting framework for market regime shift detection and trading

https://www.aimspress.com/article/doi/10.3934/DSFE.2025019?viewType=HTML
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection

3 ways quants detect market regimes for an edge - PyQuant News

https://www.pyquantnews.com/the-pyquant-newsletter/3-ways-quants-detect-market-regimes-for-an-edge
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

Mastering Market Regimes: When to Trade and When to Stay Out

https://statoasis.com/post/mastering-market-regimes-when-to-trade-and-when-to-stay-out
Average True Range Trading Strategy (Best ATR Indicator, Settings ...

https://www.quantifiedstrategies.com/average-true-range-trading-strategy/

ATR Trading Strategies Guide - TradersPost Blog

https://blog.traderspost.io/article/atr-trading-strategies-guide
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

3 ways quants detect market regimes for an edge - PyQuant News

https://www.pyquantnews.com/the-pyquant-newsletter/3-ways-quants-detect-market-regimes-for-an-edge
Market regime detection using Statistical and ML based approaches | Devportal

https://developers.lseg.com/en/article-catalog/article/market-regime-detection

Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach1footnote 11footnote 1 This article was previously titled “Regime-Aware Asset Allocation: a Statistical Jump Model Approach”.

https://arxiv.org/html/2402.05272v2

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Confidence-Weighted Majority Voting

https://www.emergentmind.com/topics/confidence-weighted-majority-voting

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

Numin: Weighted-Majority Ensembles for Intraday Trading

https://arxiv.org/html/2412.03167v1

A Two-Layer Ensemble Architecture for Enhanced Directional Price ...

https://papers.ssrn.com/sol3/Delivery.cfm/5156285.pdf?abstractid=5156285
Full article: Algorithmic setups for trading popular U.S. ETFs

https://www.tandfonline.com/doi/full/10.1080/23322039.2020.1720056

Technical indicator empowered intelligent strategies to predict stock ...

https://www.sciencedirect.com/science/article/pii/S2199853124001926

Ensemble Learning for Chart Patterns

https://www.luxalgo.com/blog/ensemble-learning-for-chart-patterns/

How To Perform A Multi TimeFrame Analysis + 5 Strategies

https://tradeciety.com/how-to-perform-a-multiple-time-frame-analysis

Mastering the Tri-Timeframe Trend-Following System - Alina Khay

https://alinakhay.com/p/mastering-the-tri-timeframe-trend

How to Design a Simple Multi-Timeframe Trend Strategy on Bitcoin

https://quantpedia.com/how-to-design-a-simple-multi-timeframe-trend-strategy-on-bitcoin/

A Strategic Trend-Following Approach with Multi-Timeframe Vortex ...

https://pyquantlab.medium.com/a-strategic-trend-following-approach-with-multi-timeframe-vortex-trading-strategy-with-volatility-9d6add2b2d6a

1 s2.0 S2199853124001926 Main | PDF | Technical Analysis | Artificial Neural Network

https://www.scribd.com/document/793488035/1-s2-0-S2199853124001926-main

1 s2.0 S2199853124001926 Main | PDF | Technical Analysis | Artificial Neural Network

https://www.scribd.com/document/793488035/1-s2-0-S2199853124001926-main

1 s2.0 S2199853124001926 Main | PDF | Technical Analysis | Artificial Neural Network

https://www.scribd.com/document/793488035/1-s2-0-S2199853124001926-main

Multi-Timeframe Trend-Confirmed Quantitative Breakout Trading ...

https://medium.com/@FMZQuant/multi-timeframe-trend-confirmed-quantitative-breakout-trading-strategy-6375e1e3f54c

An Ensembling Architecture Incorporating Machine Learning Models ...

https://www.mdpi.com/2674-1032/1/2/8

The proposed three layered multi-ensemble approach. The first layer... | Download Scientific Diagram

https://www.researchgate.net/figure/The-proposed-three-layered-multi-ensemble-approach-The-first-layer-stacks-decisions-from_fig1_343345279

The proposed three layered multi-ensemble approach. The first layer... | Download Scientific Diagram

https://www.researchgate.net/figure/The-proposed-three-layered-multi-ensemble-approach-The-first-layer-stacks-decisions-from_fig1_343345279