# PHASE27-2: 전략 로직 재설계 - 설계 문서

**작성일**: 2025-12-04  
**상태**: 🔄 IN PROGRESS  
**목표**: 시장 레짐 기반 전략 재설계로 Signal Dropout 문제 근본 해결

---

## 1. 개요

### 1.1 배경

**PHASE27-0/27-1에서 확인된 사실**:
- V0/V1/V2 파라미터 튜닝 전부 실패 (100% Strategy Signal Dropout)
- Feed/Indicator/Engine/Guard는 정상 작동
- **문제 지점**: 전략 신호 생성 레이어 (Strategy Signal Layer)

**근본 원인**:
- 전략 알고리즘이 **고변동성 추세장** 전용으로 설계됨
- 현재 시장(2025-12-04)은 **저변동성 횡보장**
- 극단적 threshold(RSI 20/80, ADX 15 등)로도 신호 발생 불가능

### 1.2 목표

**Primary Goal**: 
- 현재 시장 레짐에서 **실제로 신호를 내는** 전략 레이어 구축
- Signal Dropout 해소 (Strategy Signals True > 0)

**Secondary Goal**:
- 데이터 기반 접근: 최근 시장 통계로 현실적 threshold 설정
- 레짐 적응형 구조: 시장 상황에 따라 조건 자동 조정

**Non-Goal** (이번 PHASE 범위 밖):
- 수익률 최적화 (추후 튜닝 PHASE에서)
- 멀티심볼 확장 (PHASE27-3+에서)
- 앙상블/가드 재설계 (현재 구조 유지)

---

## 2. 제약사항

### 2.1 DO-NOT-TOUCH 레이어

**절대 변경 금지**:
- `execution/engine.py` (엔진 코어)
- `execution/portfolio_manager.py`
- `execution/risk_manager.py`
- `common/ensemble/aggregator_v2.py` (앙상블 코어)
- `common/ensemble/score_engine_v2.py`
- `tuning/` (튜닝 클러스터 인프라)

### 2.2 변경 허용 범위

**이번 PHASE에서 수정 가능**:
- `strategies/` 디렉토리 내 전략 모듈
- 전략 관련 헬퍼 함수/유틸리티
- 전략 Config 파일 (`configs/paper/*.yml`)

---

## 3. AS-IS 분석

### 3.1 기존 전략 구조

**5개 V2 전략** (PHASE22-1 구현):
1. `scalping_v3.py`: EMA Fresh Trend + RSI + Volume
2. `mean_reversion_v2.py`: BB + RSI 극단값
3. `trend_follow_v2.py`: EMA Cross + ADX
4. `volatility_breakout_v2.py`: BB Breakout + Volume
5. `volume_based_v2.py`: Volume Spike + OBV

**공통 문제점**:

| 전략 | 핵심 조건 | 왜 실패했는가 |
|------|-----------|--------------|
| scalping_v3 | RSI < 30 OR > 70 + Volume Spike | RSI가 45-55 범위 내 유지, Volume도 안정적 |
| mean_reversion_v2 | Price < BB Lower (1.8 std) + RSI < 25 | ±0.4% 변동으로는 BB(1.8 std) 도달 불가 |
| trend_follow_v2 | EMA(8/21) Cross + ADX > 15 | 횡보장에서 ADX < 15, 명확한 Cross 없음 |
| volatility_breakout_v2 | BB(2.0 std) Breakout + Volume > 1.5x | 저변동성으로 BB 돌파 없음 |
| volume_based_v2 | Volume Spike > 1.2x + OBV 확인 | Volume 패턴이 0.8~1.1x 범위 내 안정 |

**데이터 증거** (2025-12-04, BTCUSDT 5m, 30분):
- Price Range: 92,800 - 93,200 (±0.4% / ±$400)
- RSI Range: 45 - 55 (중립 구간)
- ADX: < 15 (추세 없음)
- Volume: 0.8x - 1.1x MA (스파이크 없음)

### 3.2 전략 vs 시장 불일치

**전략이 요구하는 시장**:
- 고변동성 (일중 ±2% 이상)
- 강한 추세 (ADX > 25)
- RSI 극단값 도달 빈도 (< 30 or > 70, 시간당 수회)
- Volume 스파이크 (> 1.5x MA, 빈번)

**실제 시장 상황** (2025-12-04):
- 저변동성 횡보 (±0.4%)
- 추세 부재 (ADX < 15)
- RSI 중립 유지 (45-55)
- Volume 안정 (0.8~1.1x MA)

**결론**: 전략과 시장이 근본적으로 미스매치

---

## 4. TO-BE 설계

### 4.1 데이터 기반 접근

**Phase 1: 시장 프로파일링**
- 최근 30-90일 BTCUSDT 5m 데이터 수집
- 지표 분포 계산:
  - RSI: min/max/mean/median/p05/p25/p50/p75/p95
  - BB Width: std별 (1.0, 1.5, 2.0) 가격 도달 빈도
  - ADX: 분포 및 트렌드 강도 구간별 비율
  - Volume: MA 대비 실제 분포, 스파이크 빈도
  - ATR: 변동성 레벨별 빈도

**Phase 2: 현실적 Threshold 도출**
- 절대값(RSI 30/70) 대신 **퍼센타일 기반** threshold
- 예: RSI p25 = 42, p75 = 58 → "42 이하면 과매도, 58 이상이면 과매수"
- BB 접촉 빈도 기반 std 조정 (2.0 → 1.0 std로 완화)

### 4.2 베이스라인 전략 설계

**새 전략: `btc5m_baseline_v1.py`**

**설계 철학**:
- **단순함**: 조건 2-3개 이하 (AND 최소화)
- **현실성**: 현재 레짐에서 실제 발생하는 패턴
- **빈도**: 30분에 최소 수회 신호 발생
- **안정성**: False Positive 감수, Dropout 방지 우선

**신호 조건 (초안)**:

```python
# LONG 신호
def check_long_signal(df, config):
    last = df.iloc[-1]
    
    # 데이터 프로파일링 결과 기반 threshold
    rsi_threshold = config.get('rsi_long_threshold', 45)  # p25 근처
    bb_lower_mult = config.get('bb_lower_mult', 0.998)  # BB Lower - 0.2%
    
    # 조건 1: RSI 하단
    cond_rsi = last['rsi'] < rsi_threshold
    
    # 조건 2: 가격이 BB Lower 근처
    cond_bb = last['close'] < last['bb_lower'] * (1 + bb_lower_mult)
    
    # 조건 3 (Optional): 최근 모멘텀 하락
    momentum = (last['close'] - df.iloc[-5]['close']) / df.iloc[-5]['close']
    cond_momentum = momentum < 0.001  # -0.1% 이하
    
    # OR 로직 (둘 중 하나만 만족해도 신호)
    if cond_rsi OR (cond_bb AND cond_momentum):
        return True
    
    return False

# SHORT 신호 (대칭)
def check_short_signal(df, config):
    last = df.iloc[-1]
    
    rsi_threshold = config.get('rsi_short_threshold', 55)  # p75 근처
    bb_upper_mult = config.get('bb_upper_mult', 1.002)
    
    cond_rsi = last['rsi'] > rsi_threshold
    cond_bb = last['close'] > last['bb_upper'] * (1 - bb_upper_mult)
    
    momentum = (last['close'] - df.iloc[-5]['close']) / df.iloc[-5]['close']
    cond_momentum = momentum > -0.001
    
    if cond_rsi OR (cond_bb AND cond_momentum):
        return True
    
    return False
```

**핵심 차이점**:
- AND 대신 **OR 로직** 사용 (신호 빈도 증가)
- 절대값 대신 **퍼센타일 기반** threshold
- BB std 완화 (2.0 → 1.0, config 설정)
- RSI threshold 완화 (30/70 → 45/55)

### 4.3 레짐 헬퍼 모듈 (선택)

**파일**: `strategies/common/regime_utils.py`

**기능**:
```python
def compute_percentile_thresholds(df: pd.DataFrame, 
                                   lookback: int = 100) -> dict:
    """
    최근 N개 캔들 기반 지표 퍼센타일 계산
    
    Returns:
        {
            'rsi_p25': float,
            'rsi_p75': float,
            'bb_width_median': float,
            'adx_median': float,
            ...
        }
    """
    recent = df.iloc[-lookback:]
    
    return {
        'rsi_p25': recent['rsi'].quantile(0.25),
        'rsi_p75': recent['rsi'].quantile(0.75),
        'bb_width_median': ((recent['bb_upper'] - recent['bb_lower']) / recent['close']).median(),
        'adx_median': recent['adx'].median(),
        'volume_median': recent['volume'].median(),
    }

def detect_volatility_level(df: pd.DataFrame, lookback: int = 50) -> str:
    """
    변동성 레벨 판정
    
    Returns:
        'low' | 'medium' | 'high'
    """
    recent_atr_pct = (df.iloc[-lookback:]['atr'] / df.iloc[-lookback:]['close']).mean()
    
    if recent_atr_pct < 0.005:  # 0.5% 이하
        return 'low'
    elif recent_atr_pct < 0.015:  # 1.5% 이하
        return 'medium'
    else:
        return 'high'

def detect_trend_strength(df: pd.DataFrame) -> str:
    """
    추세 강도 판정
    
    Returns:
        'weak' | 'moderate' | 'strong'
    """
    last = df.iloc[-1]
    adx = last.get('adx', 15)
    
    if adx < 20:
        return 'weak'
    elif adx < 30:
        return 'moderate'
    else:
        return 'strong'
```

**활용 방안**:
- 전략에서 고정 threshold 대신 `compute_percentile_thresholds()` 결과 사용
- 레짐별 전략 활성화/비활성화 제어
- 향후 멀티레짐 전략 전환 기반

### 4.4 기존 V2 전략 재포지셔닝

**방침**:
- 이번 PHASE에서는 기존 V2 전략을 **삭제하지 않고 유지**
- Config에서 **비활성화** 또는 **보조 역할**로 전환
- 향후 PHASE에서 레짐별 전략 스위칭 구현 시 재활용

**변경 사항**:
1. `scalping_v3`, `mean_reversion_v2`, `trend_follow_v2` 등은 그대로 유지
2. PHASE27-2 Config에서는 **새 베이스라인 전략만 활성화**
3. 문서에 각 전략의 "적합한 레짐" 명시
   - scalping_v3: 고변동성 + 명확한 추세
   - mean_reversion_v2: 고변동성 + 레인지
   - trend_follow_v2: 중/고변동성 + 강한 추세

---

## 5. 데이터 프로파일링 계획

### 5.1 스크립트 구현

**파일**: `scripts/research/phase27_2_btc5m_data_profile.py`

**기능**:
1. 최근 30일 BTCUSDT 5m 데이터 로드
   - 기존 `collectors/historical.py` 재사용
   - Binance API 또는 로컬 DB 활용
2. 지표 계산
   - RSI, BB (std 1.0/1.5/2.0), ADX, Volume, ATR
   - 기존 `indicators/` 모듈 재사용
3. 통계 계산
   - min/max/mean/median/std
   - percentile: p05/p10/p25/p50/p75/p90/p95
4. 결과 저장
   - JSON: `docs/PHASE27/phase27_2_btc5m_data_profile.json`
   - 요약 MD: 설계 문서에 반영

### 5.2 실행 계획

```bash
# 1. 환경 준비
- Docker Postgres/Redis 확인
- trading_bot_env 활성화

# 2. 스크립트 실행
python scripts/research/phase27_2_btc5m_data_profile.py --days 30 --symbol BTCUSDT --timeframe 5m

# 3. 결과 검증
- JSON 파일 생성 확인
- 핵심 지표 (RSI p25/p75, BB width, ADX median) 추출
- 설계 문서에 반영
```

---

## 6. 구현 계획

### 6.1 파일 구조

```
strategies/
├── research/
│   ├── btc5m_baseline_v1.py  (신규)
│   ├── mean_reversion_v2.py  (유지)
│   ├── trend_follow_v2.py    (유지)
│   └── ...
├── common/
│   └── regime_utils.py       (신규, 선택)
└── core/
    └── scalping_v3.py         (유지)

scripts/
└── research/
    └── phase27_2_btc5m_data_profile.py  (신규)

configs/
└── paper/
    └── phase27_2_single_symbol_30m_baseline.yml  (신규)

tests/
└── test_phase27_2_btc5m_baseline_strategy.py  (신규)

docs/
└── PHASE27/
    ├── PHASE27-2_STRATEGY_REDESIGN_DESIGN.md     (이 문서)
    ├── PHASE27-2_STRATEGY_REDESIGN_REPORT.md     (실행 후)
    └── phase27_2_btc5m_data_profile.json         (프로파일링 결과)
```

### 6.2 구현 순서

**Step 1**: 데이터 프로파일링 스크립트
- `phase27_2_btc5m_data_profile.py` 구현
- 실행 및 결과 검증
- 핵심 수치 추출

**Step 2**: 레짐 헬퍼 모듈 (선택)
- `regime_utils.py` 구현
- 단위 테스트 작성

**Step 3**: 베이스라인 전략 구현
- `btc5m_baseline_v1.py` 구현
- BaseStrategy 인터페이스 준수
- 데이터 프로파일링 결과 활용

**Step 4**: Config 생성
- `phase27_2_single_symbol_30m_baseline.yml`
- 베이스라인 전략만 활성화
- ActivityTracker 활성화

**Step 5**: 테스트 작성
- `test_phase27_2_btc5m_baseline_strategy.py`
- 신호 생성 검증
- False Positive 허용 범위 확인

**Step 6**: 30분 실행
- 기존 `phase27_0_run_diagnosis.py` 재사용
- 실시간 모니터링
- Signal/Ensemble/Order 카운트 추적

---

## 7. Acceptance Criteria

### 7.1 데이터 프로파일링

**필수**:
- ✅ 최근 30일 BTCUSDT 5m 데이터 성공적 로드
- ✅ RSI/BB/ADX/Volume/ATR 통계 계산 완료
- ✅ JSON 파일 생성 및 핵심 수치 추출

### 7.2 전략 구현

**필수**:
- ✅ `btc5m_baseline_v1.py` 구현 완료
- ✅ BaseStrategy 인터페이스 준수
- ✅ 단위 테스트 PASS (신호 생성 검증)

### 7.3 30분 실행 검증

**Primary (필수)**:
- ✅ **Strategy Signals (True) > 0** (Dropout 해소)
- ✅ ActivityTracker: Signal → Ensemble 전달 확인
- ✅ 에러/예외 없이 정상 종료

**Secondary (권장)**:
- ✅ Ensemble Tier1 or Tier2 Decision > 0
- ✅ Orders Submitted > 0 (최소 1회 이상)
- ✅ Signal 빈도: 30분에 5-20회 정도 (과다/과소 아님)

**Non-Goal** (이번 PHASE 범위 밖):
- ❌ 수익률 목표 (PnL, Sharpe, MaxDD)
- ❌ Trade 수 목표 (20-50 trades)
- ❌ 멀티심볼 확장

---

## 8. 위험 요소 및 대응

### 8.1 위험 요소

**Risk 1**: 데이터 수집 실패
- **원인**: Binance API 제한, 네트워크 오류
- **대응**: 로컬 DB 우선 사용, API는 백업

**Risk 2**: 신호 과다 발생
- **원인**: Threshold 과도 완화
- **대응**: Config에서 즉시 조정 가능한 구조, 단계적 완화

**Risk 3**: 여전히 신호 0건
- **원인**: 시장이 극단적으로 안정적
- **대응**: OR 로직 확대, Threshold 더 완화, "Always On" 모드 고려

### 8.2 Fallback Plan

**Plan A** (Primary): 퍼센타일 기반 베이스라인 전략
- RSI p25/p75, BB 1.0 std, OR 로직

**Plan B** (Fallback): 단순 모멘텀 전략
- 5분 전 대비 가격 변화 ±0.1% 이상이면 신호
- Threshold를 점진적으로 완화

**Plan C** (Extreme): "Always On" 모드
- 매 캔들마다 무조건 신호 생성 (테스트용)
- 파이프라인 정상 작동 여부만 확인
- 실전 사용 불가, 진단 목적만

---

## 9. 타임라인

**예상 소요 시간**: 4-6시간

| 단계 | 예상 시간 | 산출물 |
|------|-----------|--------|
| 데이터 프로파일링 스크립트 | 1H | `phase27_2_btc5m_data_profile.py`, JSON |
| 프로파일링 실행 & 분석 | 0.5H | 핵심 수치, 문서 반영 |
| 베이스라인 전략 구현 | 1.5H | `btc5m_baseline_v1.py`, Config |
| 테스트 작성 | 0.5H | `test_phase27_2_btc5m_baseline_strategy.py` |
| 30분 실행 & 모니터링 | 0.5H | ActivityTracker 결과 |
| 리포트 작성 | 1H | REPORT.md, ROADMAP 업데이트 |
| 전체 테스트 & 커밋 | 0.5H | pytest, git commit |

---

## 10. 다음 단계 (PHASE27-3+)

**PHASE27-2 성공 후**:
1. **PHASE27-3**: 백테스트 확장 (7일-30일)
   - 베이스라인 전략 장기 검증
   - 신호 빈도/품질 프로파일링
2. **PHASE27-4**: 멀티심볼 재검증 (Top10)
   - 심볼별 신호 분포 확인
3. **PHASE27-5**: 파라미터 튜닝 (Optuna)
   - 베이스라인 전략 최적화
   - 수익률 목표 설정

**레짐 적응형 전략 (장기)**:
- 멀티레짐 전략 스위칭 구현
- 실시간 레짐 감지 + 전략 자동 전환
- V2 전략들 재활용

---

## 11. 참고 문서

- `docs/PHASE27/PHASE27-0_TRADE_ACTIVITY_DIAGNOSIS_REPORT.md`
- `docs/PHASE27/PHASE27-1_PARAM_TUNING_REPORT.md`
- `docs/PHASE23/PHASE23-0_ARCHITECTURE_TOBE_V2.md`
- `common/registry/base_strategy.py` (전략 인터페이스)

---

**설계 문서 작성자**: Windsurf Cascade  
**버전**: 1.0 (초안)  
**최종 수정**: 2025-12-04
