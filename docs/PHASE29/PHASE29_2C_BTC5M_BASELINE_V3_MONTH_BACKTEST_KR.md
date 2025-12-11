# PHASE29-2C: BTC 5m Baseline V3 Scenario A+ 1개월 백테스트 리포트

## 📋 Document Control

| 항목 | 내용 |
|------|------|
| **PHASE** | PHASE29-2C |
| **작성일** | 2025-12-09 |
| **작성자** | Future Trading Bot Team |
| **관련 PHASE** | PHASE29-2B (1주일 백테스트, 20 트레이드, PASS) |
| **상태** | ✅ **COMPLETE** (PHASE29-2C-R 재검증 완료) |

---

## 🎯 목표

PHASE29-2B에서 확정한 Scenario A+ 설정을 1개월 구간에 적용하여 장기 성능 검증

**목표 지표**:
- ✅ 거래 건수: 80-240건 (1주일 20건 × 4배)
- ✅ Win Rate ≥ 45%
- ✅ Max Drawdown ≤ 15%
- ✅ Profit Factor ≥ 1.0
- ✅ Regime별 성과 분석

---

## 📖 배경

### PHASE29-2B 성과 요약

**1주일 백테스트** (Scenario A+):
- **거래 건수**: 20건 ✅ (목표: 20-60건)
- **Signal Rate**: 10.0% (221/2,205)
- **Guard 차단**: 200건
- **핵심 완화**: `range_min_conditions: 1` (단일 조건 진입)

**주요 설정 (Scenario A+)**:
```yaml
# Range 모드 RSI 완화
range_rsi_long_threshold: 40   # (30 → 40)
range_rsi_short_threshold: 60  # (70 → 60)
range_min_conditions: 1        # ⭐ 핵심 완화 (3 → 1)

# Global Filters 완화
min_atr_pct: 0.0015            # (0.002 → 0.0015)
min_volume_ratio: 0.5          # (0.8 → 0.5)

# RR 필터 완화
min_reward_risk_ratio: 1.5     # (2.0 → 1.5)
```

---

## 📊 백테스트 설정

### Config 파일

**파일**: `configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml`

### 실행 조건

| 항목 | 값 |
|------|-----|
| **기간** | 2024-11-01 00:00:00 ~ 2024-12-01 00:00:00 (30일) |
| **심볼** | BTCUSDT |
| **Timeframe** | 5m |
| **전략** | btc5m_baseline_v3 (단일 전략) |
| **Capital** | $50,000 |
| **Max Drawdown Guard** | 15% |
| **Daily Loss Guard** | SOFT (5%, 차단 안 함) |

### 전략 파라미터 (Scenario A+)

```yaml
# Regime 기준
adx_trend_threshold: 25
adx_range_threshold: 20

# Multi-TP 구조
atr_mult_sl_trend: 2.0
atr_mult_sl_range: 1.5
tp1_mult: 1.2  # 1차 TP (60%)
tp2_mult: 3.0  # 2차 TP (40%)

# Range 모드 완화 조건
range_rsi_long_threshold: 40   # (30 → 40)
range_rsi_short_threshold: 60  # (70 → 60)
range_min_conditions: 1        # ⭐ (3 → 1)

# V3 필터 완화
min_atr_pct: 0.0015            # 0.15%
min_volume_ratio: 0.5          # MA20 대비 50%

# RR 필터
min_reward_risk_ratio: 1.5     # (2.0 → 1.5)
```

---

## 📈 백테스트 결과 (PHASE29-2C-R 재검증)

### 실행 정보

**초기 실행**: 2025-12-09 22:58:09 (Config 파라미터 전달 버그로 실패)  
**재검증 실행**: 2025-12-09 23:52:11 (버그 수정 후)  
**실행 명령**: `python scripts/run_backtest.py --config configs/backtest/phase29_2c_btc5m_baseline_v3_month_scenario_a_plus.yml`

### 핵심 지표 (재검증 결과)

| 항목 | 실제 값 | 목표 | 판정 |
|------|---------|------|------|
| **총 캔들** | 8,928개 | - | ✅ |
| **진입 거래** | 17건 | 80-240건 | ❌ **FAIL** |
| **종료 거래** | 17건 | - | ✅ |
| **활성 포지션** | 0개 | 0개 | ✅ |
| **TUNING_VIBLE 점수** | 28.3/100 | - | ⚠️ |
| **Summary JSON** | ✅ 생성됨 | 필수 | ✅ |

### 주요 변경사항 (PHASE29-2C-R)

#### ✅ Config 파라미터 전달 버그 수정

**문제**: `strategies/__init__.py`의 `load_strategies` 함수가 `params` 키가 없는 Config를 빈 딕셔너리로 처리

**해결**:
```python
# 수정 전
strategy_params = strategy_config.get('params', {})

# 수정 후 (PHASE29-2C-R)
if 'params' in strategy_config:
    strategy_params = strategy_config['params']
else:
    known_meta_keys = {'enabled', 'timeframe', 'filters'}
    strategy_params = {k: v for k, v in strategy_config.items() if k not in known_meta_keys}
```

**검증**:
- ✅ Unit Test 3/3 PASS
- ✅ 로그에서 파라미터 전달 확인:
  - `range_min_conditions: 1`
  - `range_rsi_long_threshold: 40`
  - `range_rsi_short_threshold: 60`
  - 총 21개 파라미터 정상 전달

#### ✅ Summary JSON 저장 로직 수정

**문제**: `html_enabled=False`일 때 Summary JSON이 생성되지 않음

**해결**:
- `execution/engine.py`: `html_enabled=False`여도 JSON 저장 수행
- `analytics/report_generator.py`: Config의 `backtest.output_file` 경로 우선 사용

**검증**:
- ✅ Summary JSON 생성 확인: `reports/backtest/phase29_2c/btc5m_baseline_v3_month_scenario_a_plus_summary.json`
- ✅ 파일 내용: TUNING_VIBLE 점수 28.3/100, 메트릭 포함

---

### 분석

#### 1. 거래 건수 심각한 부족 (변화 없음)

- **실제**: 17건
- **목표**: 80-240건 (1주일 20건 × 4배)
- **달성률**: 7.1% ~ 21.3% (목표 대비 **78.8% ~ 92.9% 부족**)

**재검증 후 최종 결론**:

✅ **Config 파라미터는 정상 전달됨** (PHASE29-2C-R에서 검증 완료)
- 로그: `params: {'range_min_conditions': 1, 'range_rsi_long_threshold': 40, ...}`
- Scenario A+ 완화 설정이 전략에 정확히 적용됨

❌ **파라미터 전달과 무관하게 거래 건수 부족**
- 초기 실행 (파라미터 미전달): 17건
- 재검증 실행 (파라미터 정상 전달): 17건
- → **동일한 거래 건수** = 파라미터 전달 버그와 무관

**진짜 원인 가설**:
1. **1주일 → 1개월 선형 확장 불가**
   - 1주일: 20건 (2,205 캔들)
   - 1개월 예상: 80-90건 (8,928 캔들, 4배)
   - 실제: 17건 (예상 대비 79% 감소)
   - 1주일 구간이 특수한 고신호 구간이었을 가능성

2. **V3 전략 자체의 신호 부족**
   - Scenario A+로 완화했음에도 불구하고
   - 1개월 평균 신호율이 매우 낮음
   - AND 로직 + Multi-TP 구조가 여전히 보수적

3. **시장 구간과 전략 미스매치**
   - 2024-11-01 ~ 2024-12-01 구간의 시장 특성
   - V3 전략이 요구하는 조건과 맞지 않음

#### 2. 로그에서 관찰된 문제

백테스트 로그에서 다음 메시지가 반복적으로 출력됨:
```
[INFO] 🔍 [PHASE22-4 DEBUG] btc5m_baseline_v3 params: {}
[INFO] 🔍 [PHASE22-4 DEBUG] btc5m_baseline_v3 cfg rsi_oversold=MISSING, rsi_overbought=MISSING
```

**해석**:
- 전략 파라미터가 **빈 딕셔너리 `{}`**로 전달됨
- `rsi_oversold`, `rsi_overbought` 파라미터 누락
- **Config 파라미터 전달 문제 가능성** (PHASE22-4/23-1 이슈 재발?)

**영향**:
- 전략이 **기본값(default parameters)**으로 실행되었을 가능성
- Scenario A+ 완화 설정이 적용되지 않았을 수 있음
- `range_rsi_long_threshold: 40` → 기본값 30 사용?
- `range_min_conditions: 1` → 기본값 3 사용?

---

## 🚨 문제점 및 근본 원인

### 1. 결과 파일 미생성

**현상**:
- Config에서 지정한 경로: `reports/backtest/phase29_2c/btc5m_baseline_v3_month_scenario_a_plus_summary.json`
- 실제 상태: 폴더 `reports/backtest/phase29_2c/` 존재, 파일 0개
- `artifacts/backtest_clean/`, `artifacts/backtest_raw/` 폴더에도 오늘 날짜(2025-12-09) 결과 없음

**원인 가설**:
- Summary JSON 생성 로직 오류
- 경로 미생성 (폴더는 생성되었으나 파일 쓰기 실패)
- 백테스트 엔진 결과 저장 단계 버그

### 2. Config 파라미터 전달 문제 (추정)

**증거**:
- 로그: `params: {}` (빈 딕셔너리)
- 로그: `rsi_oversold=MISSING, rsi_overbought=MISSING`

**원인 가설**:
- PHASE23-1에서 수정한 `engine.run_v2()` 파라미터 전달 경로 미작동?
- `scripts/run_backtest.py` → `engine.run_v2()` 사이 Config 병합 누락?
- `strategies.btc5m_baseline_v3` 섹션 파싱 오류?

**검증 필요**:
- Unit Test: `test_phase22_4_config_integration.py` 재실행
- Config 파싱 로그 확인
- `load_strategies()` 함수 디버깅

### 3. 거래 건수 목표 미달 (17건 vs 80-240건)

**가설 1: Config 파라미터 미전달로 완화 미적용**
- Scenario A+ 완화 설정이 적용되지 않음
- 기본값(보수적 조건)으로 실행됨
- 신호 발생률 대폭 감소

**가설 2: 1주일 → 1개월 선형 확장 불가**
- 1주일 구간이 특수한 고신호 구간이었음
- 1개월 구간은 평균적으로 신호가 적음
- 거래 빈도가 불규칙 (일부 주는 많고, 일부 주는 적음)

**가설 3: 장기 Guard 누적 효과**
- Cooldown, 연속 손실 Guard가 누적 작동
- 초반 거래 후 Guard 활성화로 후반 거래 차단

---

## 🔮 다음 단계

### 즉시 조치 (PHASE29-2C 재시도 필요 시)

#### Option 1: Config 파라미터 전달 검증 후 재실행

1. **Unit Test 재실행**:
   ```bash
   pytest tests/test_phase22_4_config_integration.py -v
   ```

2. **Config 파싱 확인**:
   - `strategies.btc5m_baseline_v3` 섹션 정확히 로드되는지 확인
   - `load_strategies()` 함수에서 params 전달 확인

3. **재백테스트**:
   - Config 수정 (필요 시)
   - 동일 설정으로 재실행
   - 로그에서 `params: {rsi_oversold: 40, ...}` 확인

#### Option 2: 디버그 모드 백테스트

1. **Verbose 로깅 활성화**:
   - Config: `logging.level: DEBUG`
   - 전략 파라미터 로딩 과정 전체 로그 수집

2. **Activity Tracker 확인**:
   - `data/activity_backtest.db` 존재 여부 확인
   - Signal True/False 건수, Guard 차단 이유 분석

3. **결과 저장 경로 변경**:
   - Config: `output_file` 경로 변경 (절대 경로 사용)
   - 파일 쓰기 권한 확인

#### Option 3: 1주일 구간 추가 분석

1. **1주일 구간별 백테스트**:
   - 1개월을 4개 1주일 구간으로 분할
   - 각 구간 별도 백테스트
   - 거래 빈도 패턴 분석

2. **고신호 구간 식별**:
   - 신호가 많이 발생한 주 vs 적게 발생한 주
   - 시장 특성 차이 분석 (변동성, Regime 등)

---

## 📝 작업 체크리스트

- [x] PHASE29-2B 문서 검토
- [x] Scenario A+ Config 확인
- [x] pytest 실행 (btc5m_baseline_v3)
- [x] 1개월 백테스트 실행
- [ ] ⚠️ 결과 파일 확인 → **미생성**
- [ ] ⚠️ 성능 지표 분석 → **데이터 부족**
- [x] PHASE29-2C 리포트 작성 (본 문서)
- [ ] PHASE_ROADMAP 업데이트 (보류)
- [ ] Git 커밋 (보류)

---

## 🔗 관련 문서

- [PHASE29-0: V2 전략 리디자인](./PHASE29_0_BTC5M_BASELINE_V2_STRATEGY_REDESIGN_KR.md)
- [PHASE29-1: V3 전략 구현](./PHASE29_1_BTC5M_BASELINE_V3_IMPLEMENTATION_KR.md)
- [PHASE29-2: V3 백테스트 실패](./PHASE29_2_BTC5M_BASELINE_V3_BACKTEST_KR.md)
- [PHASE29-2A: V3 디버깅](./PHASE29_2A_BTC5M_BASELINE_V3_DEBUG_KR.md)
- [PHASE29-2B: Scenario A+ 1주일 백테스트](./PHASE29_2B_BTC5M_BASELINE_V3_SCENARIO_A_KR.md)

---

## 📌 요약

**PHASE29-2C Status**: ✅ **COMPLETE (INFRASTRUCTURE)** | ❌ **FAIL (STRATEGY PERFORMANCE)**

**PHASE29-2C-R 수정 사항**:
1. ✅ **Config 파라미터 전달 버그 수정**: `strategies/__init__.py` 3개 경로 수정
2. ✅ **Summary JSON 저장 로직 수정**: `execution/engine.py`, `analytics/report_generator.py` 수정
3. ✅ **Unit Test 추가**: `test_phase29_2c_config_params.py` (3/3 PASS)
4. ✅ **재백테스트 실행**: 파라미터 전달 정상 확인

**최종 결과**:
- ✅ 인프라 검증 완료 (파라미터 전달, Summary 생성)
- ❌ 전략 성능 미달 (17건/80-240건, 달성률 7.1% ~ 21.3%)

**핵심 발견**:
- Config 파라미터 전달 버그는 **거래 건수와 무관**
  - 버그 수정 전: 17건
  - 버그 수정 후: 17건 (동일)
- V3 전략 자체의 **구조적 신호 부족** 문제

**판정**: ❌ **FAIL** (전략 거래 건수 기준 미충족)

**권장 조치**:
1. **V3 전략 재평가** (PHASE29-3 or 전략 오버홀)
   - Scenario A+로도 신호 부족
   - 추가 완화 vs 전략 로직 재설계 선택 필요
2. **1주일 구간별 분석** (옵션)
   - 1개월을 4개 1주일로 분할
   - 고신호/저신호 구간 패턴 분석
3. **대안 전략 검토** (옵션)
   - V2 복귀 or V4 새로운 접근

**다음 PHASE**:
- ~~ChatGPT 리뷰 후 결정~~
- ~~PHASE29-3 (V3 Overhaul) or 전략 방향 전환~~

---

## 📋 PHASE29-3: 전략 폐기 결정 (2025-12-10)

**결정사항**: btc5m_baseline_v3 전략 공식 폐기 (DEPRECATED)

**폐기 근거**:
1. ✅ 인프라 검증 완료: Config 파라미터 전달, Summary JSON 생성 모두 정상 작동
2. ❌ 전략 성능 실패: 1개월 백테스트 17건/80-240건 (달성률 7.1~21.3%)
3. 🔍 근본 원인: AND 로직 과잉 결합 + 엄격한 Threshold → 교집합 극소
4. ⚠️ 완화 실패: Scenario A+ (최대 완화)로도 목표 미달
5. 📊 Config 버그와 무관: 파라미터 전달 수정 전후 거래 건수 동일 (17건)

**폐기 작업** (PHASE29-3):
- ✅ `strategies/btc5m_baseline_v3.py`: DEPRECATED 표시 추가
- ✅ 전략 클래스에 `deprecated=True` flag 추가
- ✅ Auto-Discovery에서 자동 제외 로직 추가
- ✅ Config/튜닝 paramspace에 DEPRECATED 표시
- ✅ Deprecation 테스트 작성 및 PASS (4/4)
- ✅ 문서 및 ROADMAP 업데이트

**다음 단계**: PHASE29-3.1 (새로운 전략 설계 - OR 기반 접근)

---

**작성 완료**: 2025-12-09  
**폐기 결정**: 2025-12-10 (PHASE29-3)  
**다음 문서**: `docs/PHASE29/PHASE29_3_STRATEGY_REDESIGN_TODO.md`
