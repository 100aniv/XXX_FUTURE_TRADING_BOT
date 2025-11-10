#  앙상블 시스템 알고리즘 종합 개선안

**작성일**: 2025-11-10  
**목적**: 6개 전략 앙상블 시스템 특화 개선 (상용 프로그램 벤치마킹)  
**중요**:  **단일 전략 로직을 그대로 적용하면 안 됨!** 각 전략은 서로 다른 특성을 가짐

---

##  목차

1. [현재 시스템 구조 완전 이해](#현재-시스템-구조)
2. [상용 앙상블 프로그램 벤치마킹](#상용-프로그램-벤치마킹)
3. [핵심 문제 분석](#핵심-문제)
4. [앙상블 특화 개선안](#개선안)
5. [PHASE별 적용 계획](#phase별-적용)

---

##  현재 시스템 구조 완전 이해 {#현재-시스템-구조}

### 시스템 아키텍처

```

                      ENSEMBLE MANAGER                            
   - 6개 전략 신호 수집                                           
   - 성과 기반 가중치 계산 (winrate, sharpe, experience)          
   - 투표 및 최종 결정 (LONG/SHORT/FLAT)                          

                      신호 수집
       
                                                               
                  
   scalp      daytrade    swing       breakout     trend     
   1m/3m      15m         1h          15m          1h        
   빈번        중간         느림         중간          느림       
                  
                                                              
                                                              reversion 
                                                              ?m        
                                                              중간       
                                                              
```

### 전략별 특성 (실제 코드 분석 결과)

| 전략 | 타임프레임 | 신호 조건 | 적정 빈도 | 특징 |
|------|-----------|----------|----------|------|
| **scalping** | 1분/3분 | BB 터치 + EMA 3선 정렬 + MACD 크로스 + 거래량 (5개) | **높음** (시간당 10-20회) | 초단타, 빠른 진입/청산 |
| **daytrade** | 15분 | EMA 정렬 + RSI + MACD (3개) | **중간** (시간당 5-10회) | 일중 매매 |
| **swing** | 1시간 | EMA 정렬 + MACD + Donchian (3개) | **낮음** (시간당 2-5회) | 스윙, 큰 움직임 포착 |
| **breakout** | 15분 | Donchian 돌파 + ATR 급등 (2개) | **중간** (시간당 3-8회) | 돌파 전략 |
| **trend** | 1시간 | EMA 크로스 + MACD (2개) | **낮음** (시간당 1-3회) | 추세 추종 |
| **reversion** | ? | RSI 과매도/과매수 + BB 근접 (2단계) | **중간** (시간당 5-10회) | 평균 회귀 |

### 현재 문제 (CRITICAL_SYSTEM_ANALYSIS 기반)

| 문제 | 현황 | 근본 원인 | 심각도 |
|------|------|----------|-------|
| **승률 39.6%** | 상용 60% 대비 -20% |  전략별 성과 검증 없음 |  심각 |
| **빈번한 거래** | 시간당 310건 (6시간 1,859건) |  쿨다운 없음, 모든 신호 수용 |  심각 |
| **수수료 누적** | 0.08%  310건 = **24.8% 손실** |  거래 빈도 제한 없음 |  심각 |
| **TP1 손실** | 11건 (TP1인데 손실) |  PHASE7-1 수정 완료 |  해결됨 |
| **8% 초과 손실** | 4건 |  PHASE7-1 수정 완료 |  해결됨 |
| **TP2 도달** | 0건 |  TP2 너무 멀음 (3.0R) |  심각 |

---

##  상용 앙상블 프로그램 벤치마킹 {#상용-프로그램-벤치마킹}

### 1. QuantConnect (Multi-Strategy Framework)

#### 아키텍처 철학

```python
class MultiStrategyAlgorithm:
    def __init__(self):
        #  핵심: 각 전략은 독립적으로 실행
        self.strategies = {
            'momentum': MomentumStrategy(
                cooldown=timedelta(hours=2),      # 전략별 쿨다운
                max_positions=3,                   # 전략별 제한
                confidence_threshold=0.75
            ),
            'mean_reversion': MeanReversionStrategy(
                cooldown=timedelta(minutes=15),    # 짧은 쿨다운 (회귀)
                max_positions=5,
                confidence_threshold=0.65
            ),
            'breakout': BreakoutStrategy(
                cooldown=timedelta(hours=1),
                max_positions=2,
                confidence_threshold=0.80          # 높은 임계값
            )
        }
        
        #  포트폴리오 레벨 제한만
        self.max_total_positions = 10
        self.max_exposure = 0.5  # 50%
        self.max_capital_per_symbol = 0.1  # 10%
```

#### 핵심 원칙

1. **전략별 독립 설정**: 쿨다운, 신뢰도, 최대 포지션 모두 다름
2. **포트폴리오 레벨만 제한**: 전체 합산 제한
3. **성과 기반 동적 가중치**: 승률 낮은 전략 자동 축소
4. **타임프레임 존중**: 1분 전략과 1시간 전략을 동일하게 제한하지 않음

### 2. Freqtrade (Multi-Strategy)

#### 설정 예시

```json
{
  \"max_open_trades\": 10,  // 전체 제한
  
  \"strategies\": {
    \"ScalpingStrategy\": {
      \"minimal_roi\": {\"0\": 0.01},      // 1% 수익 목표
      \"stoploss\": -0.02,                // -2% SL
      \"timeframe\": \"1m\",
      \"max_open_trades\": 5,             // 스캘핑: 5개
      \"cooldown_minutes\": 5              // 5분 쿨다운
    },
    \"SwingStrategy\": {
      \"minimal_roi\": {\"0\": 0.05},      // 5% 수익 목표
      \"stoploss\": -0.05,                // -5% SL
      \"timeframe\": \"1h\",
      \"max_open_trades\": 2,             // 스윙: 2개
      \"cooldown_minutes\": 120            // 2시간 쿨다운
    },
    \"DayTradeStrategy\": {
      \"minimal_roi\": {\"0\": 0.03},
      \"stoploss\": -0.03,
      \"timeframe\": \"15m\",
      \"max_open_trades\": 3,
      \"cooldown_minutes\": 30
    }
  }
}
```

#### 핵심 원칙

1. **전략별 ROI/SL**: 스캘핑 1%, 스윙 5% (타임프레임에 맞게)
2. **전략별 거래 제한**: 스캘핑 5개, 스윙 2개
3. **전략별 쿨다운**: 5분 ~ 2시간 (특성에 맞게)

### 3. 상용 vs 우리 시스템 비교

| 항목 | QuantConnect | Freqtrade | 우리 시스템 현재 | 필요한 개선 |
|------|--------------|-----------|-----------------|------------|
| **전략별 쿨다운** |  각각 다름 |  5분~2시간 |  없음 |  필수 |
| **전략별 거래 제한** |  전략마다 다름 |  2~5개 |  무제한 |  필수 |
| **포트폴리오 제한** |  10개, 50% |  10개 |  20개 (너무 많음) |  10개로 감소 |
| **신뢰도 임계값** |  0.65~0.80 |  전략별 |  전체 동일 |  전략별 설정 |
| **성과 기반 조정** |  동적 가중치 |  백테스트 기반 |  Experience Score (약함) |  강화 |
| **타임프레임 존중** |  각각 설정 |  각각 설정 |  무시됨 |  필수 |

---

##  핵심 문제 분석 {#핵심-문제}

### 문제 #1: 빈번한 거래로 인한 수수료 누적 

**현상**:
- 6시간 동안 1,859건 거래 = **시간당 310건**
- 수수료 0.08%  310건 = **시간당 24.8% 손실**
- 같은 종목에 초 단위로 신호 발생

**근본 원인**:
1. **전략별 쿨다운 없음**: scalping(1분)과 swing(1시간) 모두 동일하게 처리
2. **Ensemble 투표 쿨다운만 존재**: 전략 자체는 무제한 신호 생성
3. **모든 신호 수용**: Confidence 낮아도 진입

**상용 프로그램 해결 방식**:
```python
# Freqtrade 방식
strategies = {
    'scalping': {
        'cooldown_minutes': 5,        # 5분
        'max_trades_per_hour': 20
    },
    'daytrade': {
        'cooldown_minutes': 30,       # 30분
        'max_trades_per_hour': 10
    },
    'swing': {
        'cooldown_minutes': 120,      # 2시간
        'max_trades_per_hour': 3
    }
}
```

### 문제 #2: 승률 39.6% (상용 대비 -20%) 

**현상**:
- 현재: 39.6%
- 상용: 55-60%
- 차이: **-20%**

**근본 원인**:
1. **전략별 성과 검증 없음**: 6개 전략 중 어떤 것이 좋은지 모름
2. **낮은 승률 전략도 동일 가중치**: Experience Score 있지만 약함
3. **신호 필터링 부족**: Confidence 낮아도 진입

**상용 프로그램 해결 방식**:
```python
# QuantConnect 방식
def adjust_strategy_weight(strategy_id, performance):
    \"\"\"성과 기반 가중치 조정\"\"\"
    if performance.win_rate < 0.45:
        # 승률 45% 미만이면 가중치 50% 감소
        return 0.5
    elif performance.win_rate > 0.60:
        # 승률 60% 이상이면 가중치 50% 증가
        return 1.5
    return 1.0
```

### 문제 #3: TP2 도달 0건 

**현상**:
- TP2 설정: 3.0R
- 6시간 동안 0건 도달

**근본 원인**:
1. **TP2 너무 멀음**: 3.0R (예: Entry , SL   TP2 )
2. **도달 전 반대 신호**: 다른 전략이 역방향 신호  청산
3. **타임프레임 불일치**: swing 전략 TP2를 scalping이 청산

---

##  앙상블 특화 개선안 {#개선안}

### 개선안 #1: 전략별 독립 설정 (PHASE7-2)

#### 설정 구조

````yaml
strategies:
  scalping:
    enabled: true
    cooldown_minutes: 5              # 5분 쿨다운
    max_positions: 5                 # 최대 5개
    max_trades_per_hour: 20          # 시간당 20개
    confidence_threshold: 0.65       # 낮은 임계값 (빈번)
    atr_range:
      min_pct: 0.003                 # 0.3% (낮은 변동성도 OK)
      max_pct: 0.030                 # 3.0%
  
  daytrade:
    enabled: true
    cooldown_minutes: 15             # 15분 쿨다운
    max_positions: 3                 # 최대 3개
    max_trades_per_hour: 12          # 시간당 12개
    confidence_threshold: 0.70       # 중간 임계값
    atr_range:
      min_pct: 0.005                 # 0.5%
      max_pct: 0.025                 # 2.5%
  
  swing:
    enabled: true
    cooldown_minutes: 60             # 1시간 쿨다운
    max_positions: 2                 # 최대 2개
    max_trades_per_hour: 5           # 시간당 5개
    confidence_threshold: 0.75       # 높은 임계값
    atr_range:
      min_pct: 0.008                 # 0.8%
      max_pct: 0.030                 # 3.0%
  
  breakout:
    enabled: true
    cooldown_minutes: 30
    max_positions: 3
    max_trades_per_hour: 8
    confidence_threshold: 0.78       # 높은 임계값 (확실할 때만)
  
  trend:
    enabled: true
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 3
    confidence_threshold: 0.70
  
  reversion:
    enabled: true
    cooldown_minutes: 20
    max_positions: 3
    max_trades_per_hour: 10
    confidence_threshold: 0.68

# 포트폴리오 레벨 제한
ensemble:
  max_total_positions: 10            # 전체 최대 10개
  max_exposure_pct: 50               # 총 노출 50%
  max_positions_per_symbol: 1        # 심볼당 1개 (중복 방지)
  max_trades_per_hour: 15            # 전체 시간당 15개
```

#### 구현 위치

- execution/engine.py: 진입 전 전략별 제한 체크
- strategies/ensemble.py: 가중치 계산 시 전략별 성과 반영
- config.yml: 전략별 설정 추가

### 개선안 #2: 성과 기반 동적 가중치 강화 (PHASE7-2/4)

#### 현재 Experience Score 문제

```python
# strategies/ensemble.py::calculate_experience_score()
# 문제: 거래 수만 고려, 승률은 약하게 반영
exp_score = (
    data_sufficiency * 0.4 +      # 거래 수
    recent_performance * 0.4 +    # 승률/PF
    stability * 0.2               # Sharpe
)
```

#### 개선안

```python
def calculate_adaptive_weight(strategy_id, perf, config):
    \"\"\"
    성과 기반 적응형 가중치
    
    승률 기준:
    - 45% 미만: 가중치 50% 감소
    - 45-55%: 가중치 100% (기본)
    - 55% 이상: 가중치 150% 증가
    \"\"\"
    base_weight = config.get('ensemble', {}).get('weights', {}).get(strategy_id, 1.0)
    
    # 성과 메트릭
    winrate = perf.get(strategy_id, {}).get('winrate', 0.5)
    total_trades = perf.get(strategy_id, {}).get('total_trades', 0)
    sharpe = perf.get(strategy_id, {}).get('sharpe', 0.0)
    
    # 최소 거래 수 미달 시 페널티
    if total_trades < 20:
        data_penalty = total_trades / 20
    else:
        data_penalty = 1.0
    
    # 승률 기반 배수
    if winrate < 0.45:
        winrate_mult = 0.5    # 50% 감소
    elif winrate < 0.55:
        winrate_mult = 1.0    # 기본
    elif winrate < 0.65:
        winrate_mult = 1.5    # 50% 증가
    else:
        winrate_mult = 2.0    # 100% 증가
    
    # Sharpe 보너스
    if sharpe > 1.0:
        sharpe_bonus = 1.2
    elif sharpe > 0.5:
        sharpe_bonus = 1.1
    else:
        sharpe_bonus = 1.0
    
    # 최종 가중치
    final_weight = base_weight * data_penalty * winrate_mult * sharpe_bonus
    
    # 클램핑 (0.1 ~ 2.0)
    return max(0.1, min(2.0, final_weight))
```

### 개선안 #3: TP/SL 재조정 (PHASE7-2)

#### 문제

- 현재: TP1 1.5R, TP2 3.0R
- TP2 도달 0건 (너무 멀음)

#### 개선안

````yaml
exits:
  # TP 재조정
  tp1_r: 2.0              # 1.5R  2.0R (보수적)
  tp2_r: null             # 삭제 (또는 4.5R)
  tp1_size_pct: 60        # 60% 청산
  
  # SL 동적 조정
  sl_max_pct: 6.0         # 8%  6% (더 보수적)
  sl_min_pct: 2.0
  sl_atr_multiplier: 1.5
  
  # Trailing Stop 조기 활성화
  trailing_activate_at: \"TP1\"  # TP1 도달 후 즉시
  trailing_distance_pct: 2.0
```

---

##  PHASE별 적용 계획 {#phase별-적용}

### PHASE7-2: 포지션 관리 개선 (승률 45% 달성)

**적용 항목**:
1.  TP/SL 재조정 (기존 계획 유지)
2.  **전략별 독립 설정 추가**:
   - cooldown_minutes
   - max_positions
   - confidence_threshold
3.  **거래 빈도 제한**:
   - 전략별 시간당 제한
   - 포트폴리오 시간당 15건

**예상 효과**:
- 시간당 거래: 310건  **15건** (95% 감소)
- 수수료 누적: 24.8%  **1.2%** (95% 감소)
- 승률: 39.6%  **45%+** (신호 품질 향상)

### PHASE7-3: 운영 안정성 (기존 계획 유지)

- Graceful Shutdown
- State Recovery
- Healthcheck
- Dashboard

### PHASE7-4: 전략 개선 (승률 50% 달성)

**적용 항목**:
1.  백테스트 파이프라인 (기존 계획 유지)
2.  **전략별 성과 분석**:
   - 각 전략 개별 백테스트
   - 승률 45% 미만 전략 제거 또는 파라미터 조정
3.  **성과 기반 동적 가중치 강화**:
   - adaptive_weight 함수 적용
   - 낮은 승률 전략 자동 축소

**예상 효과**:
- 승률: 45%  **50%+**
- 손익비: 0.45  **0.8+**

### PHASE7-5: Live 전환 (기존 계획 유지)

- Paper/Live 파리티 100%
- 소액 테스트
- 단계적 확장

---

##  최종 목표 vs 현재

| 지표 | 현재 (PHASE7-1) | PHASE7-2 목표 | PHASE7-4 목표 | Live 목표 |
|------|----------------|--------------|--------------|----------|
| **승률** | 39.6% | **45%+** | **50%+** | 55%+ |
| **시간당 거래** | 310건  | **15건** | 15건 | 10건 |
| **수수료 누적** | 24.8%  | **1.2%** | 1.2% | 0.8% |
| **손익비** | 0.45 | **0.8+** | **1.0+** | 1.2+ |
| **8% 초과 손실** | 0건  | 0건 | 0건 | 0건 |
| **TP2 도달** | 0% | 삭제 | - | - |

---

**작성자**: Cascade AI (종합 분석 완료)  
**다음 단계**: PHASE7-2~5 마스터 플랜 업데이트

---

##  config.yml 설계안 (이식/확장 가능)

아래 스키마는 현재 구조와 .windsurfrules를 모두 준수하며, 상용 파리티(전략별·포트폴리오 레벨 분리), Redis 네임스페이스, DB env/run_id 정책을 반영합니다.

```yaml
# config.yml v7 (Ensemble + Ops)
runtime:
  env: "paper"                 # paper | live
  ns: "fg"                     # Redis/DB 네임스페이스 접두사
  run_id: ""            # 실행 시 자동 생성 (DB/Redis 키에 사용)

redis:
  host: "localhost"
  port: 6379
  namespace_template: "{ns}:{env}:{run_id}:{domain}"

database:
  url: "postgresql://user:pass@host:5432/trading_db"
  schema: "trading"
  enforce_env_run_id: true       # INSERT 시 env/run_id 강제

fees:
  taker: 0.0004                  # 0.04%
  maker: 0.0002
  funding_rate_check: true
  slippage_model: "dynamic"      # fixed | dynamic
  slippage_fixed: 0.0005         # 0.05%
  slippage_atr_multiplier: 0.5   # ATR * 0.5%
  slippage_max: 0.02             # 2% 상한

ensemble:
  min_votes: 2
  confidence_threshold: 0.7      # 포트폴리오 레벨 임계
  max_total_positions: 10
  max_trades_per_hour: 15
  max_positions_per_symbol: 1
  max_exposure_pct: 50
  max_weight_per_strategy: 0.35
  experience:
    enabled: true
  theta_long: 0.6
  theta_short: 0.6
  consensus_bonus: 0.1
  rr_bonus_threshold: 1.2
  rr_bonus: 0.05
  weights:
    scalping: 1.0
    daytrade: 1.0
    swing: 1.0
    breakout: 1.0
    trend: 1.0
    reversion: 1.0

strategies:
  scalping:
    enabled: true
    timeframe: "1m"
    cooldown_minutes: 5
    max_positions: 5
    max_trades_per_hour: 20
    confidence_threshold: 0.65
    atr_range: { min_pct: 0.3, max_pct: 3.0 }
  daytrade:
    enabled: true
    timeframe: "15m"
    cooldown_minutes: 15
    max_positions: 3
    max_trades_per_hour: 12
    confidence_threshold: 0.70
    atr_range: { min_pct: 0.5, max_pct: 2.5 }
  swing:
    enabled: true
    timeframe: "1h"
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 5
    confidence_threshold: 0.75
    atr_range: { min_pct: 0.8, max_pct: 3.0 }
  breakout:
    enabled: true
    timeframe: "15m"
    cooldown_minutes: 30
    max_positions: 3
    max_trades_per_hour: 8
    confidence_threshold: 0.78
  trend:
    enabled: true
    timeframe: "1h"
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 3
    confidence_threshold: 0.70
  reversion:
    enabled: true
    timeframe: "5m"
    cooldown_minutes: 20
    max_positions: 3
    max_trades_per_hour: 10
    confidence_threshold: 0.68

exits:
  tp1_r: 2.0
  tp2_r: null
  tp1_size_pct: 60
  sl_max_pct: 6.0
  sl_min_pct: 2.0
  sl_atr_multiplier: 1.5
  trailing_activate_at: "TP1"
  trailing_distance_pct: 2.0

risk:
  extreme_loss_threshold_pct: -20
  daily_loss_limit_pct: -5
  guards:
    slippage_cap_pct: 3.0
    daily_loss_halt: true

operations:
  graceful_shutdown_enabled: true
  state_recovery_enabled: true
  healthcheck_interval: 30
  prometheus_enabled: true

logging:
  trial_file: "logs/trial_0000.json"
```

### 적용/연계 매핑
- **engine.py**: 전략별 제한(enforce), 포트폴리오 합산 제한(enforce)
- **strategies/ensemble.py**: ensemble.* 임계, weights/experience, adaptive_weight(7-4)
- **risk_manager.py**: daily loss, slippage cap, exposure/correlation(7-4)
- **adapters/PaperBroker**: fees/slippage 모델
- **common/redis_client.py**: namespace_template 적용, 쿨다운 키 TTL
- **database layer**: env/run_id 필수 컬럼 채움 (INSERT 경로)

---

##  모듈/오버 리팩토링 로드맵 (문서 합의 단계)
- **중복 제거**: 레짐/ATR 보정 유틸  common/calculations 단일화 (전략 내 중복 제거)
- **소유권 준수**: PnL/Equity 단일 소스 PortfolioManager 유지. Engine은 인터페이스만 호출
- **레이어링**: core=계약, metrics=구현 격리. from metrics.compute import MetricsEngine 유지
- **튜닝(PR13)**: common/tuning_*.py deprecated  tuning/ 단일 소스 유지
- **네임스페이스**: 모든 키/채널 {ns}:{env}:{run_id}:<domain> 강제
- **데이터 분리**: Postgres 핵심 테이블 env/run_id/created_at 필드 필수 + (env, created_at) 인덱스 권장

---

