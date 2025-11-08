# 앙상블 시스템 심층 분석 및 개선 방향

## 📊 현재 앙상블 시스템 구조

### 1. ensemble_X_signals의 정체

**`ensemble_1_signals`, `ensemble_2_signals`, `ensemble_3_signals`는 전략 ID가 아닙니다!**

이것들은 **동적으로 생성되는 메타 전략 ID**입니다:

```python
# strategies/ensemble.py:781
decision = {
    'strategy_id': f"ensemble_{n}_signals",  # n = 참여한 전략 개수
    ...
}
```

**작동 방식**:
- `ensemble_1_signals` = **1개 전략**만 신호를 보낸 경우
- `ensemble_2_signals` = **2개 전략**이 합의한 경우  
- `ensemble_3_signals` = **3개 전략**이 합의한 경우

### 2. 실제 전략 구조

**기본 전략들** (strategies/ 폴더):
```
- trend.py      (트렌드 추종)
- swing.py      (스윙 트레이딩)
- daytrade.py   (데이 트레이딩)
- scalping.py   (스캘핑)
- breakout.py   (브레이크아웃)
- reversion.py  (평균 회귀)
- ensemble.py   (앙상블 통합 - 메타 전략)
```

**총 6개 기본 전략 + 1개 앙상블 = 7개 전략 파일**

**앙상블 프로세스**:
1. 각 기본 전략이 독립적으로 신호 생성
2. `ensemble.py`가 모든 신호를 수집
3. 성과 기반 가중치 계산
4. 투표 및 통합 점수 계산
5. 최종 결정 생성 (strategy_id = `ensemble_N_signals`)

### 3. 신호 통합 메커니즘

#### 3.1 가중치 계산 (Performance-Based)
```python
# strategies/ensemble.py:305-397
raw_weight = (
    0.4 * 승률(표준화) +
    0.2 * RR비율(표준화) +
    0.2 * 샤프비율(표준화) +
    0.15 * 신뢰도 +
    0.05 * 레짐적합도
) * experience_score
```

**특징**:
- ✅ 최근 30일 실제 거래 성과 기반
- ✅ 데이터 부족 시 페널티 (experience_score)
- ✅ 전략당 최대 가중치 제한 (40%)

#### 3.2 투표 및 점수 계산
```python
# strategies/ensemble.py:404-448
LONG_score = Σ(weight_i) for all LONG signals
SHORT_score = Σ(weight_i) for all SHORT signals
final_score = LONG_score - SHORT_score

if final_score >= 0.15:  → LONG
elif final_score <= -0.15: → SHORT
else: → FLAT (거래 안 함)
```

#### 3.3 Entry/SL/TP 계산
```python
# strategies/ensemble.py:758-761
entry = Σ(entry_i) / n  # 단순 평균
sl = Σ(sl_i) / n
tp = Σ(tp_i) / n
```

---

## ⚠️ 현재 시스템의 문제점

### 1. 전략별 예산 할당의 모순

**문제**: 
```yaml
# config.yml
portfolio:
  budget:
    strategy_allocation:
      ensemble_1_signals: 0.4  # 1개 전략 합의 → 40%
      ensemble_2_signals: 0.4  # 2개 전략 합의 → 40%
      ensemble_3_signals: 0.3  # 3개 전략 합의 → 30%
```

**모순점**:
- ❌ 더 많은 전략이 합의할수록 신뢰도가 높은데, 예산은 오히려 적음
- ❌ 1개 전략만 신호 보낸 경우(ensemble_1_signals)가 40% 예산
- ❌ 3개 전략 합의(ensemble_3_signals)는 30% 예산만

**논리적으로 올바른 방향**:
```yaml
# 제안
portfolio:
  budget:
    strategy_allocation:
      ensemble_1_signals: 0.2  # 1개 전략 → 낮은 신뢰도 → 적은 예산
      ensemble_2_signals: 0.35 # 2개 전략 → 중간 신뢰도 → 중간 예산
      ensemble_3_signals: 0.5  # 3개 전략 → 높은 신뢰도 → 많은 예산
```

### 2. 전략별 포지션 제한의 문제

**현재**:
```yaml
portfolio:
  max_strategy_positions: 5  # 전략당 최대 5개 포지션
```

**문제**:
- ❌ `ensemble_2_signals`가 5개 포지션 도달 → 추가 거래 불가
- ❌ 하지만 `ensemble_2_signals`는 **매번 다른 전략 조합**일 수 있음
  - 예: trend+swing, trend+daytrade, swing+daytrade 모두 `ensemble_2_signals`
- ❌ 실제로는 다양한 조합인데, 하나의 전략으로 취급

### 3. 유동적 예산 배분 부재

**현재**: 고정 비율 (40%, 40%, 30%)
**문제**: 
- ❌ 성과가 좋은 전략 조합에 더 많은 자금 배분 불가
- ❌ 시장 상황 변화에 대응 불가
- ❌ 실시간 성과 반영 안 됨

---

## 🎯 개선 방안

### 방안 1: 신호 개수 기반 예산 (단순)

```yaml
portfolio:
  budget:
    # 신호 개수에 비례한 예산 배분
    strategy_allocation:
      ensemble_1_signals: 0.2   # 1개 전략 → 20%
      ensemble_2_signals: 0.35  # 2개 전략 → 35%
      ensemble_3_signals: 0.5   # 3개 전략 → 50%
      ensemble_4_signals: 0.6   # 4개 전략 → 60%
```

**장점**:
- ✅ 더 많은 합의 = 더 높은 신뢰도 = 더 많은 예산
- ✅ 구현 간단

**단점**:
- ❌ 여전히 고정 비율
- ❌ 실제 성과 반영 안 됨

### 방안 2: 동적 예산 배분 (성과 기반)

```python
# 실시간 성과 기반 예산 계산
def calculate_dynamic_budget(strategy_id, portfolio_manager):
    # 최근 10거래 승률
    recent_winrate = get_recent_winrate(strategy_id, window=10)
    
    # 최근 샤프 비율
    recent_sharpe = get_recent_sharpe(strategy_id, window=30)
    
    # 기본 예산
    base_budget = 0.3
    
    # 성과 보너스
    performance_bonus = (recent_winrate - 0.5) * 0.4  # 승률 50% 기준
    sharpe_bonus = recent_sharpe * 0.1
    
    # 최종 예산 (20% ~ 60% 범위)
    dynamic_budget = base_budget + performance_bonus + sharpe_bonus
    dynamic_budget = max(0.2, min(0.6, dynamic_budget))
    
    return dynamic_budget
```

**장점**:
- ✅ 실제 성과 반영
- ✅ 잘하는 전략에 더 많은 자금
- ✅ 시장 적응력 향상

**단점**:
- ❌ 구현 복잡도 증가
- ❌ 과최적화 위험

### 방안 3: 포지션 제한 제거 + 총 예산 제한만

```yaml
portfolio:
  max_strategy_positions: null  # 전략별 제한 제거
  
  budget:
    # 전략별 예산만 제한
    strategy_allocation:
      ensemble_1_signals: 0.25
      ensemble_2_signals: 0.40
      ensemble_3_signals: 0.55
    
  # 전체 제한
  max_positions: 20  # 전체 포지션 한도
  max_total_exposure: 0.95  # 전체 exposure 한도
```

**장점**:
- ✅ 유연한 포지션 관리
- ✅ 예산만으로 리스크 제어
- ✅ 좋은 기회 놓치지 않음

**단점**:
- ❌ 한 전략에 과도한 집중 가능

---

## 🏆 상용 프로그램과의 비교

### 1. 3Commas (크립토 트레이딩 봇)

**장점**:
- ✅ DCA (Dollar Cost Averaging) 전략
- ✅ 거래소 다중 연동
- ✅ 간단한 UI

**단점**:
- ❌ 단순 기술적 지표 기반
- ❌ 앙상블/성과 기반 가중치 없음
- ❌ 고정 전략

**우리 시스템**:
- ✅ **성과 기반 동적 가중치** (3Commas보다 우수)
- ✅ **다중 전략 앙상블** (3Commas는 단일 전략)
- ❌ UI 부재 (3Commas가 우수)

### 2. QuantConnect (기관급 퀀트 플랫폼)

**장점**:
- ✅ 강력한 백테스팅
- ✅ 다양한 자산 클래스
- ✅ 클라우드 인프라

**단점**:
- ❌ 복잡한 학습 곡선
- ❌ 비용 (프로 플랜 $20~$400/월)

**우리 시스템**:
- ✅ **실시간 성과 기반 가중치** (QuantConnect와 유사)
- ✅ **무료 오픈소스** (QuantConnect는 유료)
- ❌ 백테스팅 기능 제한적
- ❌ 자산 클래스 제한 (선물만)

### 3. TradingView (차트 + 알고리즘)

**장점**:
- ✅ 최고의 차트 UI
- ✅ Pine Script 전략
- ✅ 커뮤니티

**단점**:
- ❌ 자동 거래 제한적
- ❌ 앙상블 기능 없음
- ❌ 성과 기반 가중치 없음

**우리 시스템**:
- ✅ **완전 자동 거래** (TradingView보다 우수)
- ✅ **앙상블 시스템** (TradingView 없음)
- ❌ 차트 UI 없음

### 4. Freqtrade (오픈소스 크립토 봇)

**장점**:
- ✅ 오픈소스
- ✅ 다양한 전략
- ✅ 백테스팅

**단점**:
- ❌ 앙상블 기능 기본 제공 안 함
- ❌ 성과 기반 가중치 없음
- ❌ 포트폴리오 관리 약함

**우리 시스템**:
- ✅ **앙상블 시스템** (Freqtrade보다 우수)
- ✅ **성과 기반 가중치** (Freqtrade 없음)
- ✅ **포트폴리오 관리** (예산/상관관계 가드)
- ≈ 백테스팅 (비슷한 수준)

---

## 📈 우리 시스템의 수준 평가

### 강점 (상용 수준)
1. ✅ **성과 기반 동적 가중치** - 기관급
2. ✅ **다중 전략 앙상블** - 상용 프로그램 이상
3. ✅ **포트폴리오 리스크 관리** - 전문가 수준
4. ✅ **Paper/Live 파리티** - 상용 수준
5. ✅ **실시간 처리** - 상용 수준

### 약점 (개선 필요)
1. ❌ **UI/대시보드** - 기본적 수준
2. ❌ **백테스팅** - 제한적
3. ❌ **문서화** - 개발 중
4. ❌ **예산 배분 로직** - 비직관적 (이번 이슈)
5. ❌ **모니터링/알림** - 기본적

### 종합 평가

**현재 수준**: **중급~고급 개인 트레이더 / 소규모 헤지펀드 수준**

**비교**:
- 3Commas (대중용) < **우리 시스템** < QuantConnect (기관용)
- Freqtrade (오픈소스) ≈ **우리 시스템** (일부 기능 우수)

**상용화 가능성**: ⭐⭐⭐⭐☆ (5점 만점에 4점)
- 핵심 로직은 상용 수준
- UI/UX 개선 필요
- 문서화 및 사용성 개선 필요

---

## 🎯 즉시 개선 권장 사항

### 1. 예산 배분 로직 수정 (우선순위: 높음)

```yaml
# config.yml 수정
portfolio:
  budget:
    strategy_allocation:
      ensemble_1_signals: 0.2   # 1개 전략 → 20%
      ensemble_2_signals: 0.35  # 2개 전략 → 35%
      ensemble_3_signals: 0.5   # 3개 전략 → 50%
      ensemble_4_signals: 0.6   # 4개 전략 → 60% (있다면)
```

### 2. 포지션 제한 완화 (우선순위: 중간)

```yaml
# config.yml 수정
portfolio:
  max_strategy_positions: 10  # 5 → 10으로 증가
  # 또는
  max_strategy_positions: null  # 제한 제거, 예산으로만 제어
```

### 3. 동적 예산 배분 (우선순위: 낮음, PR13)

- 실시간 성과 기반 예산 조정
- 승률/샤프비율 기반 보너스
- 시장 레짐별 전략 선호도

---

## 💡 결론

**현재 시스템은 이미 상당히 정교합니다**:
- ✅ 성과 기반 가중치
- ✅ 다중 전략 앙상블
- ✅ 포트폴리오 리스크 관리

**하지만 예산 배분 로직이 역설적**:
- ❌ 더 많은 합의 = 적은 예산 (현재)
- ✅ 더 많은 합의 = 많은 예산 (논리적)

**즉시 수정 권장**: config.yml의 strategy_allocation 비율 역전
