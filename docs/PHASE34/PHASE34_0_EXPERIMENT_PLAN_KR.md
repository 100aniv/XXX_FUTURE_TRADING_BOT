# PHASE34: 파라미터 최적화 실험 플랜

**작성일**: 2024-12-12  
**목적**: btc15m_core_v2 Light 전략의 핵심 파라미터 튜닝  
**상태**: ✅ **PLANNED** (템플릿/축/AC 정의 완료)

---

## 📋 Executive Summary

### 배경

PHASE33에서 V2 Light 전략의 장기 안정성(9개월)을 입증했으나, 차단율이 **97~99%**로 매우 높음.  
주요 차단 사유는 `low_confidence` (67~74%)로, 필터 파라미터 조정을 통한 거래량/품질 균형 최적화가 필요.

### 목표

**3축 파라미터 스윕**을 통해 다음 목표 달성:
1. **차단율 감소**: 97% → **70~80%**
2. **거래량 증가**: 79 trades/day → **100~150 trades/day**
3. **품질 유지**: Win Rate ≥ 30%, Exceptions == 0

---

## 🎯 실험 설계

### 실험 축 (3 Axes)

| 축 | AS-IS (PHASE33) | 후보값 | 이유 |
|----|----------------|--------|------|
| **1. Confidence Threshold** | 0.25 (Trend)<br>0.30 (Range) | 0.20 / **0.25** / 0.30 | low_confidence가 주요 차단 사유 (67~74%) |
| **2. Hysteresis Candles** | 3 | 2 / **3** / 5 | Regime 전환 민감도 조절 |
| **3. MTF Weight** | 0.6 (HTF)<br>0.4 (Local) | **AS-IS** / 완화(0.5/0.5) | Higher TF 의존도 완화 |

**조합 수**: 3 × 3 × 2 = **18개 실험**

### 기준선 (Baseline)

- **Config**: `configs/backtest/phase33_1_v2_Q1_3m.yml` (AS-IS)
- **Period**: 2024-01-01 ~ 2024-04-01 (3개월, 90일)
- **Expected Trades**: 7,113건 (79 trades/day)
- **차단율**: 97.8%

---

## 📊 Acceptance Criteria (상용급)

### AC1: 기술적 안정성 (필수)

| 항목 | 기준 | 판정 |
|------|------|------|
| **예외 발생** | == 0 | ✅/❌ |
| **전략 호출 성공률** | == 100% | ✅/❌ |
| **DecisionTrace 출력** | 정상 | ✅/❌ |
| **종료 체크 3종** | PASS | ✅/❌ |

**기술적 안정성 FAIL 시 → 해당 조합 즉시 폐기**

---

### AC2: 거래량 목표

| 지표 | AS-IS | 목표 | 판정 기준 |
|------|-------|------|----------|
| **총 거래 (3M)** | 7,113건 | **9,000~13,500건** | ±20% 허용 |
| **일평균 거래** | 79건 | **100~150건** | 27~67% 증가 |

---

### AC3: 품질 유지

| 지표 | AS-IS | 최소 기준 |
|------|-------|----------|
| **Win Rate** | 26.7% | ≥ **25%** |
| **Profit Factor** | N/A | ≥ **0.8** |
| **Max DD** | ~10% | ≤ **12%** |

**품질 기준 미달 시 → 차단율만 낮추고 신호 품질 악화된 것으로 간주**

---

### AC4: 차단율 개선

| 지표 | AS-IS | 목표 |
|------|-------|------|
| **Portfolio BLOCK** | 97.8% | **70~80%** |
| **low_confidence 비율** | 67~74% | ≤ **50%** |

---

## 🔬 실험 매트릭스

### 우선순위 1: Confidence 완화 (6개)

| ID | Confidence (Trend/Range) | Hysteresis | MTF Weight | 예상 효과 |
|----|--------------------------|-----------|------------|----------|
| E1-1 | 0.20 / 0.25 | 3 | AS-IS | low_conf ↓ 30% |
| E1-2 | 0.20 / 0.25 | 2 | AS-IS | low_conf ↓ 35% |
| E1-3 | 0.20 / 0.25 | 5 | AS-IS | low_conf ↓ 25% |
| E1-4 | 0.20 / 0.30 | 3 | AS-IS | low_conf ↓ 20% |
| E1-5 | 0.20 / 0.30 | 2 | AS-IS | low_conf ↓ 25% |
| E1-6 | 0.20 / 0.30 | 5 | AS-IS | low_conf ↓ 15% |

**기대**: 거래량 +40~60%, 차단율 70~80%

---

### 우선순위 2: MTF 완화 (6개)

| ID | Confidence | Hysteresis | MTF Weight (HTF/Local) | 예상 효과 |
|----|------------|-----------|----------------------|----------|
| E2-1 | AS-IS (0.25/0.30) | 3 | 0.5 / 0.5 | Local TF 신뢰도 ↑ |
| E2-2 | AS-IS | 2 | 0.5 / 0.5 | 전환 빠름 + Local ↑ |
| E2-3 | AS-IS | 5 | 0.5 / 0.5 | 전환 느림 + Local ↑ |
| E2-4 | 0.20 / 0.25 | 3 | 0.5 / 0.5 | Conf ↓ + Local ↑ |
| E2-5 | 0.20 / 0.25 | 2 | 0.5 / 0.5 | 복합 완화 (최대) |
| E2-6 | 0.20 / 0.25 | 5 | 0.5 / 0.5 | 복합 완화 (보수) |

**기대**: 거래량 +30~50%, 차단율 75~85%

---

### 우선순위 3: 조합 탐색 (6개)

| ID | Confidence | Hysteresis | MTF Weight | 특징 |
|----|------------|-----------|------------|------|
| E3-1 | 0.30 / 0.35 | 3 | AS-IS | 보수적 (품질 우선) |
| E3-2 | 0.30 / 0.35 | 2 | AS-IS | 보수적 + 빠른 전환 |
| E3-3 | 0.30 / 0.35 | 5 | AS-IS | 보수적 + 느린 전환 |
| E3-4 | 0.30 / 0.35 | 3 | 0.5 / 0.5 | 보수적 + MTF 완화 |
| E3-5 | AS-IS | AS-IS | AS-IS | **재현성 검증** |
| E3-6 | 0.25 / 0.30 | 2 | 0.5 / 0.5 | 균형 조합 |

**E3-5는 PHASE33 재현성 검증용 (Control Group)**

---

## 📁 Config 템플릿

**템플릿 경로**: `configs/backtest/phase34_template.yml`

### 가변 파라미터

```yaml
strategies:
  btc15m_core_v2:
    regime_detection:
      # 실험 축 1: Confidence Threshold
      min_confidence_trend: 0.25     # 0.20 / 0.25 / 0.30
      min_confidence_range: 0.30     # 0.25 / 0.30 / 0.35
      
      # 실험 축 2: Hysteresis
      hysteresis_candles: 3          # 2 / 3 / 5
      
      # 실험 축 3: MTF Weight
      higher_tf_weight: 0.6          # 0.6 / 0.5
      local_tf_weight: 0.4           # 0.4 / 0.5
```

### 고정 파라미터

- **기간**: 2024-01-01 ~ 2024-04-01 (3M)
- **심볼**: BTCUSDT 15m
- **전략**: btc15m_core_v2 (V2 Light)
- **Guards**: ON (PHASE33과 동일)
- **기타**: PHASE33 Q1 config와 동일

---

## 📈 출력 포맷 (표준화)

### Summary JSON 필수 키

```json
{
  "run_id": "phase34_e1_1_conf020",
  "config_id": "E1-1",
  "params": {
    "min_confidence_trend": 0.20,
    "min_confidence_range": 0.25,
    "hysteresis_candles": 3,
    "higher_tf_weight": 0.6,
    "local_tf_weight": 0.4
  },
  "trades": {
    "total": 9500,
    "per_day": 105.6
  },
  "block_rate": 0.78,
  "low_confidence_rate": 0.52,
  "winrate": 0.28,
  "profit_factor": 0.95,
  "max_dd": 0.087,
  "exceptions": 0
}
```

### DecisionTrace 비교 포맷

| Reason | AS-IS (E3-5) | E1-1 | E1-2 | ... |
|--------|--------------|------|------|-----|
| low_confidence_0.15 | 492 (74%) | 320 (45%) | 280 (40%) | ... |
| no_scenario_triggered | 116 (17%) | 150 (21%) | 160 (23%) | ... |
| hysteresis_not_met | 8 (1%) | 5 (0.7%) | 12 (1.7%) | ... |

---

## 🚀 실행 절차 (다음 세션)

### STEP 1: Config 생성 (18개)

```powershell
# 템플릿 기반으로 18개 조합 생성
python scripts/phase34_generate_configs.py
```

**출력**: `configs/backtest/phase34_e{1-3}_{1-6}_*.yml`

---

### STEP 2: 배치 실행 (Watchdog 기반)

```powershell
# E1 시리즈 (6개)
foreach ($i in 1..6) {
    python scripts/utils/run_watchdog.py \
        --command "python scripts/run_backtest.py --config configs/backtest/phase34_e1_$i.yml" \
        --timeout 900 \
        --summary-path "reports/backtest/phase34/e1_$i_summary.json" \
        --run-id "phase34_e1_$i" \
        --log-file "logs/phase34_e1_$i.log" \
        --report-file "reports/watchdog/phase34_e1_$i_watchdog.json"
}

# E2, E3도 동일
```

---

### STEP 3: 결과 수집 & 분석

```powershell
python scripts/phase34_analyze_results.py \
    --input-dir reports/backtest/phase34 \
    --output reports/analysis/phase34_comparison.{md,json}
```

**분석 내용**:
1. AC1~AC4 체크
2. 파라미터별 상관관계
3. Pareto Frontier (거래량 vs 품질)
4. 최종 권장 조합 (Top 3)

---

### STEP 4: 문서화 & 판정

- `docs/PHASE34/PHASE34_1_RESULTS_KR.md` 생성
- 최종 권장 파라미터 확정
- PHASE_ROADMAP.md 업데이트
- Git commit

---

## ⚙️ 기술적 세부사항

### Watchdog 사용 (필수)

- 모든 실행은 `run_watchdog.py`로 감싸서 실행
- Timeout: 900초 (15분, 3M 백테스트 기준)
- 종료 체크 3종 자동 검증
- 실패 시 즉시 중단 + 로그 덤프

### 병렬 실행 (선택)

- 18개 실험을 순차 실행 시 **약 4.5시간** 소요
- 병렬 실행 시 **1~1.5시간** (4~6 worker)
- Windows에서는 PowerShell jobs 사용 권장

---

## 📋 Acceptance Criteria (PHASE34-0 본 문서)

| AC | 항목 | 판정 |
|----|------|------|
| **AC1** | 실험 축 정의 (3축, 18조합) | ✅ **PASS** |
| **AC2** | Config 템플릿 생성 | ✅ **PASS** |
| **AC3** | 출력 포맷 표준화 | ✅ **PASS** |
| **AC4** | 실행 절차 문서화 | ✅ **PASS** |
| **AC5** | Watchdog 통합 | ✅ **PASS** |

**PHASE34-0 판정**: ✅ **COMPLETE** - 다음 세션 sweep 준비 완료

---

## 📚 관련 문서

- `PHASE33_LONG_RUN_VALIDATION_KR.md` - AS-IS 기준선
- `PHASE33_PROCESS_EXIT_CHECKLIST.md` - Watchdog 사용법
- `PHASE32_2_1M_SMOKE_TEST_REPORT_KR.md` - V2 Light 1M 검증
- `configs/backtest/phase34_template.yml` - 실험 템플릿

---

## 🎯 다음 세션 목표

**PHASE34-1: Parameter Sweep Execution**

1. 18개 config 자동 생성
2. 배치 실행 (Watchdog 기반)
3. 결과 수집 & 비교 분석
4. 최종 권장 파라미터 확정
5. 판정 및 문서화

**예상 소요 시간**: 2~3 세션 (Config 생성 30분 + 실행 4.5H + 분석 1H)
