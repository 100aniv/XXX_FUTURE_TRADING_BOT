# PHASE29-4: BTC 5m Baseline V4 - 1개월 성능 검증 & 경량 튜닝

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-4 |
| **작성일** | 2025-12-10 |
| **전략명** | btc5m_baseline_v4 |
| **목적** | 1개월 성능 검증 + 경량 파라미터 튜닝 |
| **상태** | 🚧 **IN PROGRESS** |

---

## 🎯 PHASE 목적

### 핵심 목표

**V4를 "BTCUSDT 5m 단일 전략 후보"로 1개월 성능 검증**

1. **성능 검증**: 1개월 백테스트로 Win Rate/Max DD/Sharpe 등 핵심 메트릭 확보
2. **경량 튜닝**: 최소 수준의 파라미터 조합(3~5개 변수) 비교로 "쓸 수 있는 전략인지" 판단
3. **Guard 최적화**: min_rr_required, cooldown_candles 실전 수준 조정

**NOT in scope**:
- ❌ 새로운 V5 전략 설계
- ❌ 멀티 심볼/앙상블
- ❌ 풀스케일 튜닝 클러스터 (PHASE25)

---

## 📖 이전 PHASE 요약

### V2/V3 실패 요약

| 전략 | 진입 로직 | 결과 | 실패 원인 |
|------|-----------|------|-----------|
| **V2** | OR (RSI OR BB OR Volume) | 신호 과다, Win Rate < 45% | OR 과잉 |
| **V3** | AND (RSI AND BB AND EMA/ADX) | 1개월 17건 ❌ | AND 과잉 결합 |

### V4 Gate PASS 요약 (PHASE29-3.4)

**1주일 백테스트** (2024-11-24 ~ 2024-12-01):
- ✅ **신호 생성**: 96건 (LONG 35, SHORT 61)
- ✅ **체결**: 35건 (Gate 목표 20-60건 범위 내)
- ✅ **근본 원인 발견**: Guard 설정(base.yml)이 100% 차단
- ✅ **해결**: Gate Config로 Guard 완화 (min_rr_required=null, cooldown_candles=0)

**V4 전략 컨셉**:
- **OR + Score 기반**: AND/OR 과잉의 중간 지점
- **Regime-Aware**: Trend Pullback + Range Mean Reversion
- **Multi-TP**: TP1 60%, TP2 40% (V3 재사용)

---

## ✅ Acceptance Criteria (AC)

### AC1: 1개월 백테스트 성공적 완료
- **조건**: 에러 없이 1개월 구간 백테스트 완료
- **기간**: 2024-11-01 ~ 2024-12-01 (V3와 동일 구간)
- **검증**: Summary JSON 생성 확인

### AC2: Gate_1M 통과 (거래 건수)
- **조건**: 1개월 거래 건수 80~240건 범위
- **근거**: 1주일 20건 × 4배 = 80~240건
- **측정**: orders_submitted (실제 체결 기준)

### AC3: 핵심 성능 메트릭 달성
- **Win Rate ≥ 45%**: PASS, 미달 시 FAIL로 솔직히 기록
- **Max Drawdown ≤ 15%**: PASS, 미달 시 FAIL로 솔직히 기록
- **Profit Factor ≥ 1.0**: 참고 지표 (PASS 필수 아님)

### AC4: 경량 튜닝 결과 리포트
- **조합 수**: 최소 3~5개 파라미터 조합
- **변수**: range_min_score, trend_min_score, min_rr_required, cooldown_candles
- **산출물**: JSON/Markdown 리포트 (상위 3개 조합 요약)

### AC5: 문서/코드/테스트 동기화
- **pytest**: 모든 V4 관련 테스트 PASS
- **PHASE_ROADMAP.md**: PHASE29-4 상태 업데이트
- **Git**: 의미 있는 커밋 메시지로 모든 변경 커밋

---

## 🛠️ 작업 계획

### STEP 0: 컨텍스트 스캔 ✅
- [x] PHASE_ROADMAP.md
- [x] V3 1개월 백테스트 레퍼런스 (PHASE29_2C)
- [x] V4 설계/백테스트/Gate 문서 (PHASE29-3.1~3.4)
- [x] V4 전략 코드 (strategies/btc5m_baseline_v4.py)
- [x] Gate Config (phase29_3_4_btc5m_baseline_v4_week_gate.yml)

### STEP 1: 계획 문서 작성 ✅
- [x] 현재 V4 상태 요약 (10줄)
- [x] PHASE29-4 목표 및 AC 정의
- [x] docs/PHASE29/PHASE29_4_BTC5M_BASELINE_V4_PLAN_KR.md

### STEP 2: 1개월 Backtest Config 설계 & 생성
- [ ] Config 생성: `phase29_4_0_btc5m_baseline_v4_month_baseline.yml`
  - 기간: 2024-11-01 ~ 2024-12-01 (V3와 동일)
  - Guard: 실전 수준 (min_rr_required=1.2, cooldown_candles=1)
  - Score: range_min_score=3, trend_min_score=3
- [ ] 검증 스크립트: `phase29_4_check_v4_month_config.py`

### STEP 3: 1개월 Backtest 실행 & 결과 분석
- [ ] Backtest 실행: `run_backtest.py`
- [ ] Summary JSON 확인
- [ ] 분석 스크립트: `phase29_4_analyze_v4_month_performance.py`
- [ ] 결과 문서: `docs/PHASE29/PHASE29_4_1_V4_MONTH_BASELINE_RESULT_KR.md`

### STEP 4: Light Parameter Tuning (경량 튜닝)
- [ ] 파라미터 Grid 정의:
  - range_min_score: {2, 3, 4}
  - trend_min_score: {2, 3}
  - min_rr_required: {1.0, 1.2}
  - cooldown_candles: {0, 1}
  - 총 24 조합 (필요시 축소)
- [ ] 튜닝 스크립트: `phase29_4_run_light_tuning.py`
- [ ] 분석 스크립트: `phase29_4_analyze_light_tuning.py`
- [ ] 결과 문서: `docs/PHASE29/PHASE29_4_2_V4_LIGHT_TUNING_RESULT_KR.md`

### STEP 5: 테스트, ROADMAP, Git 정리
- [ ] pytest 실행 (V4 관련 테스트 전체)
- [ ] PHASE_ROADMAP.md 업데이트
- [ ] Git commit (의미 있는 메시지)

---

## 📊 예상 산출물 (Artifacts)

### Configs
- `configs/backtest/phase29_4_0_btc5m_baseline_v4_month_baseline.yml`
- `tuning_results/phase29_4_v4_light_tuning.json` (24개 조합 결과)

### Scripts
- `scripts/phase29_4_check_v4_month_config.py`
- `scripts/phase29_4_analyze_v4_month_performance.py`
- `scripts/phase29_4_run_light_tuning.py`
- `scripts/phase29_4_analyze_light_tuning.py`

### Reports
- `reports/backtest/phase29_4_0/btc5m_baseline_v4_month_baseline_summary.json`
- `reports/analysis/PHASE29/phase29_4_1_v4_month_performance.json`
- `reports/analysis/PHASE29/phase29_4_2_v4_light_tuning.json`

### Documentation
- `docs/PHASE29/PHASE29_4_BTC5M_BASELINE_V4_PLAN_KR.md` (this)
- `docs/PHASE29/PHASE29_4_1_V4_MONTH_BASELINE_RESULT_KR.md`
- `docs/PHASE29/PHASE29_4_2_V4_LIGHT_TUNING_RESULT_KR.md`

---

## 🎯 판정 기준

### PASS 조건
1. ✅ AC1: 1개월 백테스트 에러 없이 완료
2. ✅ AC2: 거래 건수 80~240건
3. ✅ AC3: Win Rate ≥ 45% AND Max DD ≤ 15%
4. ✅ AC4: 경량 튜닝 결과 리포트 (상위 3개 조합)
5. ✅ AC5: 문서/코드/테스트 동기화

### FAIL 조건
- ❌ AC3 미달성: Win Rate < 45% OR Max DD > 15%
  - 이 경우, 결과를 솔직히 FAIL로 기록
  - 다음 PHASE에서 "전략 로직 재설계" vs "Guard 구제" 결정

### CONDITIONAL GO
- ⚠️ AC2 미달성 (거래 건수 80 미만): 신호 부족 문제
- ⚠️ AC3 부분 달성 (Win Rate만 PASS OR Max DD만 PASS)

---

## 📝 비고

### V3 대비 차이점
- **V3**: AND 로직 과잉 → 1개월 17건 (FAIL)
- **V4**: OR + Score → 1주일 35건 (PASS)
- **기대**: V4가 V3보다 신호 빈도/Win Rate 모두 개선

### 경량 튜닝 이유
- PHASE29-4는 "V4가 쓸 수 있는 전략인지" 빠른 판단
- 풀스케일 튜닝은 V4 PASS 후 별도 PHASE에서 진행
- 파일 기반 경량 튜닝으로 DB 의존성 제거

---

**작성자**: Future Trading Bot Team  
**최종 업데이트**: 2025-12-10
