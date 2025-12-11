# PHASE30-1: btc15m_core_v1 3M Baseline 백테스트 결과

**실행일**: 2025-12-11  
**Trial ID**: `phase30_1_btc15m_core_v1_3m_baseline`  
**상태**: ✅ **BACKTEST COMPLETE** (AC3 분석 진행 중)

---

## 1. 백테스트 설정

### 1.1 기본 정보
- **전략**: btc15m_core_v1 (PHASE30-0 설계 기반)
- **심볼**: BTCUSDT
- **Timeframe**: 15m
- **기간**: 2024-09-01 ~ 2024-12-01 (91일, 3개월)
- **데이터**: BTCUSDT_15m_2024-01-01_2024-12-31.csv (5m 리샘플링)
- **총 캔들**: 8,832개
- **Guard**: ON (cooldown=2, min_rr=1.5, max_dd=0.12)

### 1.2 전략 파라미터
```yaml
regime_detection:
  adx_trend_threshold: 25
  adx_range_threshold: 20
  atr_high_vol_mult: 1.5
  volume_high_vol_mult: 2.0
  min_confidence: 0.3

filters:
  min_atr_pct: 0.002  # 0.2%
  min_volume_ratio: 0.7  # 평균 대비 70%

sl_tp:
  # Trend Mode
  sl_mult_trend: 2.0
  tp1_rr_trend: 1.5
  tp2_rr_trend: 3.0
  # Range Mode
  sl_mult_range: 1.5
  tp1_rr_range: 1.5
  tp2_rr_range: 2.5
```

---

## 2. 백테스트 실행 결과

### 2.1 실행 로그 요약
```
✅ Trading Engine 종료: 총 캔들=8,832개, 진입 거래=15건, 종료 거래=15건, 활성 포지션=0개
🏆 TUNING_VIBLE 총점: 30.4/100
```

### 2.2 거래 발생 확인
- **총 거래 수**: 15건 (로그 기준)
- **진입 완료**: 15건
- **종료 완료**: 15건
- **미청산 포지션**: 0건

### 2.3 주요 관찰 사항

**1) 전략 정상 로드 확인**
- ✅ `btc15m_core_v1` 전략이 strategies 모듈에 정상 등록됨
- ✅ 엔진이 `btc15m_core_v1` 전략을 성공적으로 로드 및 실행함
- ✅ Regime Detection, Core AND, Optional OR 로직 정상 작동

**2) 지표 자동 계산**
- 로그에서 반복적으로 지표 자동 계산 메시지 확인:
  ```
  [btc15m_core_v1] 지표 컬럼 누락 감지: ['rsi_14', 'di_plus_14', ...] → 자동 계산
  [btc15m_core_v1] 지표 자동 계산 완료
  ```
- **원인**: 엔진이 전달하는 DataFrame에 지표가 미리 계산되지 않음
- **영향**: 성능에는 영향 없으나, 매 캔들마다 지표 재계산으로 인한 오버헤드 발생 가능

**3) 연속 손실 쿨다운 발생**
- 로그에서 연속 손실 쿨다운 메시지 확인:
  ```
  reason=risk_check_failed detail="연속 손실 쿨다운 (5회, 26분 남음)"
  ```
- **의미**: Core V1 전략이 연속 5회 손실 후 RiskManager에 의해 일시 중단됨
- **영향**: 거래 기회 일부 차단 (Guard ON 정상 작동)

---

## 3. AC3 성능 분석 (진행 중)

### 3.1 분석 상태
- ⏳ **진행 중**: DB 스키마 확인 및 성능 지표 추출 중
- ⚠️ **이슈**: Summary JSON이 TUNING_VIBLE 포맷으로 생성됨 (performance_metrics 포맷 아님)
- ⚠️ **이슈**: DB trades 테이블 컬럼 스키마 확인 필요 (`pnl_net` vs `pnl_realized`)

### 3.2 임시 지표 (로그 기반)
- **총 거래**: 15건
- **기간**: 91일 (3개월)
- **월평균 거래**: 5건/월
- **TUNING_VIBLE 점수**: 30.4/100

### 3.3 AC3 기준 (예비 판정)
| 항목 | 목표 | 실제 (추정) | 예비 판정 |
|------|------|-------------|-----------|
| **거래 건수** | 60~120건/월 | 5건/월 | ❌ **FAIL** (거래 부족) |
| **Win Rate** | 40~45% | 분석 중 | ⏳ 대기 |
| **Max DD** | ≤ 12% | 분석 중 | ⏳ 대기 |
| **Profit Factor** | > 1.2 | 분석 중 | ⏳ 대기 |

---

## 4. 문제 분석 및 원인

### 4.1 거래 부족 문제 (5건/월)

**근본 원인 분석**:

1. **Core AND 필터가 과도하게 엄격함**
   - Regime Detection의 `min_confidence` = 0.3
   - ATR 필터 `min_atr_pct` = 0.002 (0.2%)
   - Volume 필터 `min_volume_ratio` = 0.7 (평균 대비 70%)
   - 이 모든 조건을 동시 만족해야 하므로, 진입 기회가 크게 제한됨

2. **Optional OR 시나리오의 조건이 까다로움**
   - EMA Pullback, RSI Oversold, BB Lower 등의 조건이 까다로움
   - 특히 15m Timeframe에서는 빠른 반응이 필요한 조건들이 놓칠 가능성 높음

3. **연속 손실 쿨다운 (5회)**
   - 초기 5회 연속 손실 발생 시, 나머지 기간 동안 거래 차단됨
   - 로그에서 "26분 남음" 메시지 → 실제로는 더 긴 차단이 발생했을 가능성

4. **Guard ON 설정**
   - `cooldown_candles` = 2 (30분)
   - `min_rr_required` = 1.5
   - 이 설정들이 추가로 거래 기회를 줄임

### 4.2 Summary JSON 포맷 문제

**발견 사항**:
```json
{
  "trial_id": null,
  "total_score": 30.39,
  "metrics": {
    "total_trades": 6814,  // ← 잘못된 값
    "winrate": 26.56,
    "mdd": -1009.65,
    ...
  }
}
```

**문제점**:
- `trial_id`가 `null`
- `total_trades`가 6814건 (실제는 15건)
- TUNING_VIBLE 포맷으로 생성됨 (성능 분석용 포맷 아님)

**원인**:
- 엔진의 performance_metrics 모듈이 올바르게 호출되지 않았거나
- Summary JSON 생성 로직이 TUNING_VIBLE 전용으로 작동함

---

## 5. 다음 단계 (PHASE30-1b 또는 PHASE30-2)

### 5.1 즉시 조치 (PHASE30-1b: 긴급 수정)

**Option A: Core AND 필터 완화**
```yaml
filters:
  min_atr_pct: 0.0015  # 0.2% → 0.15% (완화)
  min_volume_ratio: 0.5  # 70% → 50% (완화)

regime_detection:
  min_confidence: 0.2  # 0.3 → 0.2 (완화)
```

**Option B: 연속 손실 쿨다운 조정**
```yaml
risk:
  max_consecutive_losses: 10  # 5 → 10 (여유)
  cooldown_minutes: 0  # 30분 → 즉시 복구
```

**Option C: Optional OR 시나리오 추가**
- 현재: Trend-Up 3개, Trend-Down 3개, Range 2개 (총 8개)
- 추가: 단순 RSI 반전, Volume Spike 단독 진입 등

### 5.2 중기 조치 (PHASE30-2: Light Tuning)

**튜닝 대상**:
1. **Regime Detection 파라미터**
   - `adx_trend_threshold`: {23, 25, 27}
   - `min_confidence`: {0.2, 0.25, 0.3}

2. **Core Filters**
   - `min_atr_pct`: {0.0015, 0.002, 0.0025}
   - `min_volume_ratio`: {0.5, 0.6, 0.7}

3. **SL/TP**
   - `sl_mult_trend`: {1.8, 2.0, 2.2}
   - `tp1_rr_trend`: {1.3, 1.5, 1.7}

**튜닝 규모**: 16~32개 조합 (Grid Search)

### 5.3 장기 조치 (PHASE30-3+)

**1. Summary JSON 포맷 수정**
- performance_metrics 모듈 직접 호출하도록 수정
- trial_id 올바르게 설정
- 정확한 Win Rate, Max DD, PF 계산

**2. 지표 자동 계산 최적화**
- 엔진에서 지표를 미리 계산하여 전략에 전달
- 전략 내부에서 매번 재계산하지 않도록 개선

**3. 30m Timeframe 테스트**
- PHASE30-0 설계에서 30m도 지원 timeframe으로 명시됨
- 15m보다 노이즈가 적고, 신호 품질이 더 높을 가능성

---

## 6. 결론 및 권장 사항

### 6.1 현재 상태 요약

✅ **성공 사항**:
- btc15m_core_v1 전략 코드 구현 완료 (650 lines)
- Config, 검증 스크립트, 단위 테스트 작성 완료
- 백테스트 엔진과의 통합 성공 (15건 거래 발생)
- Regime Detection, Core AND, Optional OR 로직 정상 작동 확인

❌ **실패 사항**:
- 거래 건수 부족 (5건/월 vs 목표 60~120건/월)
- AC3 성능 지표 미추출 (Summary JSON 포맷 문제)

⚠️ **보류 사항**:
- Win Rate, Max DD, Profit Factor 분석 (DB 스키마 확인 후 재실행 필요)

### 6.2 AC3 최종 판정

**판정**: ❌ **AC3 FAIL** (거래 건수 부족으로 인한 명백한 실패)

**근거**:
- 거래 건수: 5건/월 (목표 60~120건/월의 8%)
- Core AND 필터가 과도하게 엄격하여, 실전 운영 불가능한 수준
- 나머지 지표(WinRate, MaxDD, PF)를 확인하더라도, 거래 부족으로 인해 통계적 유의성 없음

### 6.3 권장 다음 단계

**즉시 (24H 이내)**:
1. **PHASE30-1b: 긴급 필터 완화**
   - `min_confidence` 0.3 → 0.2
   - `min_atr_pct` 0.002 → 0.0015
   - `min_volume_ratio` 0.7 → 0.5
   - `max_consecutive_losses` 5 → 10
   - 재백테스트 실행 → 거래 건수 30~50건/월 목표

**단기 (1주 이내)**:
2. **PHASE30-2: Light Tuning (16~32 조합)**
   - Core AND 필터 Grid Search
   - Regime Detection 파라미터 Grid Search
   - 목표: 최소 1개 조합이 AC3 PASS

**중기 (2주 이내)**:
3. **PHASE30-3: 30m Timeframe 테스트**
   - 15m보다 신호 품질 높을 가능성
   - 거래 건수는 줄지만, Win Rate/RR 상승 기대

---

**작성자**: Cascade AI  
**검토일**: 2025-12-11  
**상태**: ⏳ AC3 분석 진행 중 (DB 스키마 확인 후 완료 예정)

**다음 문서**: PHASE30-1b 또는 PHASE30-2 설계 문서
