# 🎯 앙상블 통합 봇 아키텍처

**작성일**: 2025-10-14  
**버전**: v1.0  
**파일**: `ensemble_bot.py`

---

## 🎯 목표

3개 전략(scalping, daytrade, swing) 신호를 **가중치 기반**으로 통합하여 최종 매매 결정 생성.

### **핵심 원칙**
1. **성과 기반 가중치**: 실전 승률/RR/샤프 비율 반영
2. **레짐 적합도**: 시장 상황별 전략 유불리 고려
3. **멱등성 보장**: 동일 캔들에 대해 결정 1건만
4. **점진적 학습**: 백테스트 → 실전 승률로 자동 전환

---

## 📊 우선순위 산정 공식

### **1. 기본 점수 계산**

```python
raw_weight_s = 
  α * z(winrate_30d_s) +      # 승률 (30일 롤링)
  β * z(rr_mean_30d_s) +       # 평균 RR
  γ * z(sharpe_30d_s) +        # 샤프 비율
  δ * confidence_s +            # 신호 신뢰도
  ε * regime_fit_s              # 레짐 적합도
```

**파라미터 (기본값):**
- **α** = 0.4 (승률 가중치)
- **β** = 0.2 (RR 가중치)
- **γ** = 0.2 (샤프 가중치)
- **δ** = 0.15 (신뢰도 가중치)
- **ε** = 0.05 (레짐 가중치)

**z(x)**: Z-score 표준화 (평균 0, 표준편차 1)

---

### **2. 레짐 적합도 (Regime Fit)**

| 레짐 | 스캘핑 | 단타 | 스윙 |
|------|--------|------|------|
| **상승장** | 0.6 | 0.6 | **0.8** |
| **하락장** | 0.6 | 0.6 | **0.8** |
| **횡보장** | **0.8** | **0.8** | 0.4 |
| **고변동성** | **1.0** | 0.6 | 0.5 |
| **저변동성** | 0.5 | 0.6 | **0.8** |

**계산 로직:**
```python
if strategy == 'scalping':
    regime_fit = volatility_score  # 변동성 높을수록 유리

elif strategy == 'daytrade':
    if regime == '횡보장':
        regime_fit = 0.8
    elif regime in ('상승장', '하락장'):
        regime_fit = 0.6

elif strategy == 'swing':
    if regime in ('상승장', '하락장'):
        regime_fit = 0.8 * (1.0 - volatility_score * 0.5)  # 낮은 변동성 선호
```

---

### **3. 추가 보너스/패널티**

| 조건 | 조정값 | 설명 |
|------|--------|------|
| **합의 보너스** | +0.2 | 2개 이상 전략 동의 |
| **RR 보너스** | +0.2 | RR ≥ 1.6 |
| **HTF 레짐 정렬** | +0.2 | 상위 타임프레임 추세 동의 |
| **연속 손실** | -0.3 | 최근 3연패 |
| **세션 시간대** | ±0.1 | 유럽/미국 장 시간 |

---

## 🔄 통합 프로세스

```
Step 1: 신호 수집
  ├─ monitoring.signals에서 최근 신호 조회
  └─ 동일 캔들(±10초) 내 3개 전략 신호 수집

Step 2: 성과 메트릭 로드
  ├─ trading.trades에서 최근 30일 실적 계산
  ├─ 승률, RR, 샤프, 총 손익 산출
  └─ 초기값: winrate=0.5, rr=1.0 (중립)

Step 3: 가중치 계산
  ├─ 각 전략 점수 = α*승률 + β*RR + γ*샤프 + δ*신뢰도 + ε*레짐
  ├─ 기본 가중치 추가 (scalp=3, intraday=2, swing=1)
  └─ 정규화: w_s = raw_weight_s / Σ raw_weight_s

Step 4: 통합 점수
  ├─ LONG 점수 = Σ (w_s * confidence_s) for direction='LONG'
  ├─ SHORT 점수 = Σ (w_s * confidence_s) for direction='SHORT'
  └─ final_score = LONG_score - SHORT_score

Step 5: 보너스 적용
  ├─ 합의 보너스 (2개 이상 동의)
  ├─ RR 보너스 (RR ≥ 1.6)
  └─ 연속 손실 패널티 등

Step 6: 의사결정
  ├─ score > 0.15 → LONG
  ├─ score < -0.15 → SHORT
  └─ else → FLAT (거래 안함)

Step 7: 저장 (멱등성)
  └─ trading.decisions에 UPSERT
      (UNIQUE: symbol + timeframe + candle_closed_at)
```

---

## 📈 백테스트 → 실전 승률 전환

### **초기 (백테스트)**
```python
# 수동으로 초기 성과 입력
INSERT INTO reporting.strategy_performance (strategy_id, winrate_30d, rr_mean_30d, sharpe_30d)
VALUES 
  ('scalping', 0.50, 1.5, 0.3),   # 백테스트 결과
  ('daytrade', 0.58, 1.6, 0.5),
  ('swing', 0.65, 2.0, 0.7);
```

### **운영 후 (실전)**
```sql
-- 매일 자동 업데이트 (cron)
INSERT INTO reporting.strategy_performance (
  as_of, strategy_id, symbol,
  winrate_30d, rr_mean_30d, sharpe_30d, total_trades, total_pnl
)
SELECT 
  NOW() AS as_of,
  strategy_id,
  symbol,
  AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) AS winrate_30d,
  AVG(profit_factor) AS rr_mean_30d,
  AVG(pnl_pct) / NULLIF(STDDEV(pnl_pct), 0) AS sharpe_30d,
  COUNT(*) AS total_trades,
  SUM(pnl) AS total_pnl
FROM trading.trades
WHERE ts_open >= NOW() - INTERVAL '30 days'
  AND status = 'CLOSED'
GROUP BY strategy_id, symbol
ON CONFLICT (as_of, strategy_id, symbol) DO UPDATE
SET winrate_30d = EXCLUDED.winrate_30d,
    rr_mean_30d = EXCLUDED.rr_mean_30d,
    sharpe_30d = EXCLUDED.sharpe_30d;
```

**결과**: 실전 성과가 쌓이면 가중치가 자동으로 조정됨!

---

## 🎛️ 환경변수 튜닝

```bash
# .env.ensemble

# === 기본 가중치 ===
WEIGHT_SCALP=3.0          # 스캘핑 기본 가중치
WEIGHT_INTRADAY=2.0       # 단타 기본 가중치
WEIGHT_SWING=1.0          # 스윙 기본 가중치

# === 우선순위 파라미터 ===
ALPHA_WINRATE=0.4         # 승률 가중치
BETA_RR=0.2               # RR 가중치
GAMMA_SHARPE=0.2          # 샤프 가중치
DELTA_CONFIDENCE=0.15     # 신뢰도 가중치
EPSILON_REGIME=0.05       # 레짐 가중치

# === 보너스/패널티 ===
CONSENSUS_BONUS=0.2                    # 합의 보너스
RR_BONUS_THRESHOLD=1.6                 # RR 보너스 임계값
RR_BONUS=0.2                           # RR 보너스
CONSECUTIVE_LOSS_PENALTY=-0.3          # 연속 손실 패널티
HTF_REGIME_BONUS=0.2                   # HTF 레짐 보너스

# === 의사결정 임계값 ===
THETA_LONG=0.15           # LONG 진입 임계값
THETA_SHORT=0.15          # SHORT 진입 임계값

# === 탐험 파라미터 ===
EPSILON_EXPLORE=0.05      # 랜덤 탐험 확률 (5%)
EXPLORE_THRESHOLD=0.05    # 상위 점수와 5% 이내 후보 복수

# === 기타 ===
SIGNAL_WINDOW_SEC=10                   # 신호 수집 윈도우 (초)
PERFORMANCE_WINDOW_DAYS=30             # 성과 추적 기간 (일)
POLL_INTERVAL_SEC=5                    # 폴링 간격 (초)
```

---

## 📊 예시 시나리오

### **시나리오 1: 상승 추세 (BTC)**

**입력 신호:**
```
scalping: LONG, confidence=0.7, atr_pct=2.5%
daytrade: LONG, confidence=0.8, atr_pct=2.5%
swing:    FLAT, confidence=0.3
```

**성과 (30일):**
```
scalping: winrate=0.52, rr=1.5, sharpe=0.3
daytrade: winrate=0.60, rr=1.7, sharpe=0.6
swing:    winrate=0.68, rr=2.1, sharpe=0.8
```

**레짐**: 상승장, 변동성 보통

**계산:**
```python
# 1. Z-score 표준화
z_winrates = [-0.87, 0.22, 0.65]  # (0.52-평균)/표준편차
z_rr = [-0.79, 0.14, 0.65]
z_sharpe = [-0.92, -0.15, 1.07]

# 2. 레짐 적합도
regime_fit = [0.6, 0.6, 0.8]  # 상승장 → 스윙 유리

# 3. 가중치 계산
raw_weights = [
  0.4*(-0.87) + 0.2*(-0.79) + 0.2*(-0.92) + 0.15*0.7 + 0.05*0.6 + 0.3*0.1 = -0.13,
  0.4*(0.22) + 0.2*(0.14) + 0.2*(-0.15) + 0.15*0.8 + 0.05*0.6 + 0.2*0.1 = 0.24,
  0.4*(0.65) + 0.2*(0.65) + 0.2*(1.07) + 0.15*0.3 + 0.05*0.8 + 0.1*0.1 = 0.67
]

# 음수 제거
raw_weights = [0, 0.24, 0.67]

# 정규화
weights = [0, 0.26, 0.74]  # 스윙 74%, 단타 26%

# 4. 통합 점수
LONG_score = 0*0 + 0.26*0.8 + 0*0 = 0.21
SHORT_score = 0
final_score = 0.21

# 5. 보너스
consensus_bonus = +0.2  # 2개 LONG
adjusted_score = 0.21 + 0.2 = 0.41

# 6. 결정
chosen_side = 'LONG' (score=0.41 > theta=0.15)
```

**결과**: **LONG 진입** (스윙 전략 주도, 합의 보너스)

---

### **시나리오 2: 횡보장 (ETH)**

**입력:**
```
scalping: SHORT, confidence=0.6
daytrade: LONG, confidence=0.5
swing:    FLAT, confidence=0.4
```

**계산:**
```
weights = [0.5, 0.4, 0.1]  # 횡보장 → 스캘핑/단타 유리
LONG_score = 0*0 + 0.4*0.5 + 0*0 = 0.20
SHORT_score = 0.5*0.6 + 0*0 + 0*0 = 0.30
final_score = 0.20 - 0.30 = -0.10
```

**결과**: **FLAT** (score=-0.10, |score| < 0.15)

---

## 🔧 튜닝 가이드

### **1. 보수적 설정 (안정성 우선)**
```bash
THETA_LONG=0.25           # 진입 문턱 높임
THETA_SHORT=0.25
ALPHA_WINRATE=0.5         # 승률 더 중시
CONSENSUS_BONUS=0.3       # 합의 필수
```

### **2. 공격적 설정 (수익률 우선)**
```bash
THETA_LONG=0.10           # 진입 문턱 낮춤
THETA_SHORT=0.10
WEIGHT_SCALP=5.0          # 스캘핑 강화
EPSILON_EXPLORE=0.10      # 탐험 증가
```

### **3. 균형 설정 (기본)**
- 현재 기본값 사용

---

## 📉 리스크 관리 (D+2에서 구현)

```python
# 일손실 한도
if daily_pnl < equity * (-DAILY_RISK_LIMIT_PCT):
    chosen_side = 'FLAT'  # 신규 진입 차단

# 연속 손실
if consecutive_losses >= 3:
    adjusted_score -= 0.3  # 패널티

# 동시 포지션 제한
if active_positions >= MAX_POSITIONS:
    chosen_side = 'FLAT'
```

---

## 🧪 검증 체크리스트

- [ ] **백테스트**: 과거 3개월 데이터로 샤프 > 1.0
- [ ] **A/B 테스트**: 앙상블 vs 단일 최고전략 (동일 기간)
- [ ] **워크포워드**: 30일 학습 → 7일 검증
- [ ] **슬리피지**: 체결가 ±0.05% 가정
- [ ] **수수료**: 메이커 0.02%, 테이커 0.05%
- [ ] **리스크**: 일손실 -3%, 연속 3패 쿨다운

---

## 🚀 다음 단계

1. ✅ 앙상블 봇 개발 (완료)
2. ⏳ **성과 추적 자동화** (cron/Airflow)
3. ⏳ **트레이딩 봇 개발** (D+2)
4. ⏳ **백테스트 엔진** (선택)
5. ⏳ **웹 대시보드** (D+3)

---

**작성자**: AI Assistant  
**마지막 업데이트**: 2025-10-14
