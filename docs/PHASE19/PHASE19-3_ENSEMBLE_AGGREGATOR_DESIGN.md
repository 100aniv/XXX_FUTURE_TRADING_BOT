# PHASE19-3+: Ensemble Signal Aggregator 설계 문서 (Full Integration)
**작성일**: 2025-11-20  
**목적**: 여러 전략의 신호 + Score를 통합하여 최종 Ensemble 의사결정 생성

---

## 1. 개요

Ensemble Signal Aggregator는 다음을 수행:
1. **여러 전략 평가**: StrategyRegistry + ScoreEngine + FactorCalculator로 각 전략의 신호 + 점수 계산
2. **3-Tier Aggregation**: High-Confidence → Consensus → Skip 규칙으로 최종 의사결정
3. **엔진 연결**: execution/engine.py에서 선택적으로 사용 (config.ensemble.enabled)

---

## 2. 데이터 구조

### 2.1 StrategyDecision (개별 전략 결정)

```python
@dataclass
class StrategyDecision:
    """개별 전략의 신호 + 점수"""
    name: str                    # 전략 이름 (예: 'scalping')
    side: Optional[str]          # 'LONG' | 'SHORT' | None
    score: float                 # 0~1 (ScoreEngine 계산 결과)
    confidence: float            # 0~1 (score와 동일하거나 추가 조정)
    raw_signal: Any              # 기존 signal_logic 결과 (dict)
    metadata: StrategyMetadata   # 전략 메타데이터
```

**사용 목적**:
- 각 전략이 현재 캔들에서 어떤 신호를 냈는지 기록
- Aggregator가 여러 StrategyDecision을 입력받아 최종 결정

### 2.2 EnsembleDecision (최종 Ensemble 결정)

```python
@dataclass
class EnsembleDecision:
    """Ensemble 최종 의사결정"""
    side: Optional[str]                      # 최종 방향 ('LONG' | 'SHORT' | None)
    confidence: float                        # 0~1 (최종 신뢰도)
    chosen_strategy: Optional[str]           # 선택된 전략 (Tier1 경우)
    contributing_strategies: List[str]       # 기여한 전략 목록
    tier: str                                # 'tier1' | 'tier2' | 'skip'
    decisions: List[StrategyDecision]        # 모든 전략 결정 (디버깅용)
    regime: Optional[str]                    # 현재 Regime (참고용)
    reason: str                              # 결정 이유 (로그용)
```

**사용 목적**:
- 엔진이 이 객체를 받아서 진입/청산 의사결정
- side=None이면 이번 캔들 건너뛰기
- side가 있으면 포지션 오픈/청산 진행

---

## 3. EnsembleAggregator 클래스

### 3.1 인터페이스

```python
class EnsembleAggregator:
    """
    Ensemble Signal Aggregator
    
    **역할**:
    - 여러 전략의 신호를 평가하고 점수화
    - 3-Tier 규칙으로 최종 Ensemble 의사결정 생성
    
    **의존성**:
    - StrategyRegistry: 전략 인스턴스 생성
    - ScoreEngine: 전략 점수 계산
    - FactorCalculator: 시장 Factor 계산 (compute_all_factors)
    """
    
    def __init__(
        self,
        registry: StrategyRegistry,
        score_engine: ScoreEngine
    ):
        """
        초기화
        
        Args:
            registry: StrategyRegistry 인스턴스
            score_engine: ScoreEngine 인스턴스
        """
        self.registry = registry
        self.score_engine = score_engine
    
    def evaluate_strategies(
        self,
        strategy_names: List[str],
        df: pd.DataFrame,
        regime: Optional[str] = None,
    ) -> List[StrategyDecision]:
        """
        여러 전략을 평가하여 StrategyDecision 리스트 생성
        
        **처리 흐름**:
        1. 각 전략에 대해 compute_signal(df) 호출
        2. 신호가 있으면 Factor 계산 (compute_all_factors)
        3. Score 계산 (score_engine.compute_strategy_score)
        4. StrategyDecision 생성
        
        Args:
            strategy_names: 평가할 전략 이름 리스트
            df: OHLCV + 지표 포함 DataFrame
            regime: 현재 시장 Regime (None이면 unknown)
        
        Returns:
            List[StrategyDecision]: 신호가 있는 전략들의 결정 리스트
        """
        pass
    
    def aggregate(
        self,
        decisions: List[StrategyDecision],
        regime: Optional[str] = None,
    ) -> EnsembleDecision:
        """
        여러 StrategyDecision을 3-Tier 규칙으로 통합
        
        **3-Tier 규칙**:
        - Tier 1: High-Confidence (score >= 0.8)
        - Tier 2: Consensus (0.5 <= score < 0.8, 2+ votes)
        - Tier 3: Skip (조건 미달)
        
        Args:
            decisions: StrategyDecision 리스트
            regime: 현재 Regime (참고용)
        
        Returns:
            EnsembleDecision: 최종 의사결정
        """
        pass
    
    def decide(
        self,
        strategy_names: List[str],
        df: pd.DataFrame,
        regime: Optional[str] = None,
    ) -> EnsembleDecision:
        """
        evaluate_strategies + aggregate를 한 번에 수행
        
        **편의 메서드**:
        엔진에서 이 메서드 하나만 호출하면 됨
        
        Args:
            strategy_names: 평가할 전략 이름 리스트
            df: OHLCV + 지표 DataFrame
            regime: 현재 Regime
        
        Returns:
            EnsembleDecision: 최종 의사결정
        """
        decisions = self.evaluate_strategies(strategy_names, df, regime)
        return self.aggregate(decisions, regime)
```

---

## 4. 3-Tier Aggregation 규칙

### 4.1 Tier 1: High-Confidence Pick

**조건**: score >= 0.8인 전략이 1개 이상

**처리 로직**:
```python
tier1_decisions = [d for d in decisions if d.score >= 0.8]

if len(tier1_decisions) == 0:
    # Tier 2로 넘어감
    pass
elif len(tier1_decisions) == 1:
    # 단일 High-Confidence → 즉시 선택
    return EnsembleDecision(
        side=tier1_decisions[0].side,
        confidence=tier1_decisions[0].score,
        chosen_strategy=tier1_decisions[0].name,
        tier='tier1',
        ...
    )
else:
    # 여러 High-Confidence → 충돌 검사
    long_count = sum(1 for d in tier1_decisions if d.side == 'LONG')
    short_count = sum(1 for d in tier1_decisions if d.side == 'SHORT')
    
    if long_count > 0 and short_count > 0:
        # 충돌 발생 → 점수 차이 검사
        long_max = max((d.score for d in tier1_decisions if d.side == 'LONG'), default=0)
        short_max = max((d.score for d in tier1_decisions if d.side == 'SHORT'), default=0)
        
        diff = abs(long_max - short_max)
        
        if diff >= 0.15:
            # 차이가 충분히 큼 → 높은 쪽 선택
            if long_max > short_max:
                chosen = max((d for d in tier1_decisions if d.side == 'LONG'), key=lambda x: x.score)
            else:
                chosen = max((d for d in tier1_decisions if d.side == 'SHORT'), key=lambda x: x.score)
            
            return EnsembleDecision(
                side=chosen.side,
                confidence=chosen.score,
                chosen_strategy=chosen.name,
                tier='tier1',
                reason=f"High-confidence pick (diff={diff:.2f})",
                ...
            )
        else:
            # 차이가 작음 → Conflict, NO TRADE
            return EnsembleDecision(
                side=None,
                confidence=0.0,
                tier='skip',
                reason=f"Tier1 conflict (diff={diff:.2f} < 0.15)",
                ...
            )
    else:
        # 같은 방향만 존재 → 최고 점수 선택
        chosen = max(tier1_decisions, key=lambda x: x.score)
        return EnsembleDecision(
            side=chosen.side,
            confidence=chosen.score,
            chosen_strategy=chosen.name,
            tier='tier1',
            reason="High-confidence unanimous",
            ...
        )
```

### 4.2 Tier 2: Consensus Vote

**조건**: 0.5 <= score < 0.8인 전략들이 2개 이상

**처리 로직**:
```python
tier2_decisions = [d for d in decisions if 0.5 <= d.score < 0.8]

if len(tier2_decisions) < 2:
    # Tier 3 (Skip)
    return EnsembleDecision(side=None, confidence=0.0, tier='skip', reason="Insufficient votes", ...)

long_votes = [d for d in tier2_decisions if d.side == 'LONG']
short_votes = [d for d in tier2_decisions if d.side == 'SHORT']

# 한 쪽이 최소 2개 이상 & 다른 쪽보다 명확히 많음
if len(long_votes) >= 2 and len(long_votes) > len(short_votes):
    avg_confidence = sum(d.score for d in long_votes) / len(long_votes)
    return EnsembleDecision(
        side='LONG',
        confidence=avg_confidence,
        contributing_strategies=[d.name for d in long_votes],
        tier='tier2',
        reason=f"Consensus vote (LONG: {len(long_votes)} vs SHORT: {len(short_votes)})",
        ...
    )
elif len(short_votes) >= 2 and len(short_votes) > len(long_votes):
    avg_confidence = sum(d.score for d in short_votes) / len(short_votes)
    return EnsembleDecision(
        side='SHORT',
        confidence=avg_confidence,
        contributing_strategies=[d.name for d in short_votes],
        tier='tier2',
        reason=f"Consensus vote (SHORT: {len(short_votes)} vs LONG: {len(long_votes)})",
        ...
    )
else:
    # 동률 or 조건 미달
    return EnsembleDecision(
        side=None,
        confidence=0.0,
        tier='skip',
        reason=f"Consensus tie (LONG: {len(long_votes)} vs SHORT: {len(short_votes)})",
        ...
    )
```

### 4.3 Tier 3: Skip

**조건**: Tier 1/2 모두 조건 미달

**처리**:
```python
return EnsembleDecision(
    side=None,
    confidence=0.0,
    tier='skip',
    reason="No confident signals",
    decisions=decisions,
    regime=regime,
    ...
)
```

---

## 5. Signal 충돌 & 무효 처리

### 5.1 신호 없는 전략

**처리**:
- `compute_signal(df)` 결과에서 `side=None` 또는 `signal=0`인 경우
- 해당 전략은 이번 캔들에서 제외 (StrategyDecision 생성 안 함)

### 5.2 LONG/SHORT 충돌

**Tier 1**: 점수 차이 >= 0.15면 높은 쪽 선택, 아니면 NO TRADE  
**Tier 2**: 한 쪽이 명확히 많으면 선택, 아니면 NO TRADE

### 5.3 Ensemble가 None 반환

**엔진 동작**:
- `EnsembleDecision.side = None`이면 이번 캔들에서 진입하지 않음
- 기존 포지션이 있으면 유지 (청산 신호는 별도)

---

## 6. 엔진 통합 (Minimal Hook)

### 6.1 Config 구조

**파일**: `configs/*.yaml` 또는 `CFG` dict

```yaml
# 기존 필드...
symbol: BTCUSDT
timeframe: 1m
strategy: scalping  # 단일 전략 (ensemble.enabled=false일 때 사용)

# PHASE19-3: Ensemble 옵션
ensemble:
  enabled: false  # 기본값 false (기존 단일 전략 모드)
  strategies:     # Ensemble 모드에서 사용할 전략 목록
    - scalping
    - trend
    - breakout
  min_tier1_score: 0.8    # Tier 1 임계값
  min_tier2_score: 0.5    # Tier 2 임계값
  tier1_conflict_diff: 0.15  # Tier 1 충돌 최소 차이
  min_tier2_votes: 2      # Tier 2 최소 투표 수
```

**기본값** (config에 없을 경우):
```python
DEFAULT_ENSEMBLE_CONFIG = {
    "enabled": False,
    "strategies": ["scalping"],
    "min_tier1_score": 0.8,
    "min_tier2_score": 0.5,
    "tier1_conflict_diff": 0.15,
    "min_tier2_votes": 2,
}
```

### 6.2 Engine Hook 위치

**파일**: `execution/engine.py`

**기존 구조** (추정):
```python
# execution/engine.py

class TradingEngine:
    def run(self, ...):
        for candle in candles:
            df = self._prepare_dataframe(candle)
            
            # 기존: 단일 전략 신호 생성
            signal = self.strategy.compute_signal(df)
            
            if signal and signal['side']:
                # 포지션 오픈/청산 로직
                self._process_signal(signal)
```

**PHASE19-3 수정** (Minimal Hook):
```python
# execution/engine.py

class TradingEngine:
    def __init__(self, config, ...):
        self.config = config
        
        # Ensemble 옵션 확인
        self.ensemble_enabled = config.get('ensemble', {}).get('enabled', False)
        
        if self.ensemble_enabled:
            # Ensemble 모드
            from common.ensemble import EnsembleAggregator, ScoreEngine
            from common.registry import StrategyRegistry
            
            self.registry = StrategyRegistry()
            self.registry.scan()
            self.score_engine = ScoreEngine()
            self.aggregator = EnsembleAggregator(self.registry, self.score_engine)
            self.ensemble_strategies = config.get('ensemble', {}).get('strategies', ['scalping'])
        else:
            # 기존 단일 전략 모드
            self.strategy = self._load_strategy(config['strategy'])
    
    def run(self, ...):
        for candle in candles:
            df = self._prepare_dataframe(candle)
            
            if self.ensemble_enabled:
                # Ensemble 모드: Aggregator 사용
                ensemble_decision = self.aggregator.decide(
                    strategy_names=self.ensemble_strategies,
                    df=df,
                    regime=None  # PHASE19-4에서 Regime Classifier 연결 예정
                )
                
                if ensemble_decision.side:
                    # Ensemble이 진입 신호를 냈음
                    signal = self._convert_ensemble_to_signal(ensemble_decision)
                    self._process_signal(signal)
                else:
                    # NO TRADE (skip)
                    logger.info(f"[ENSEMBLE] Skip: {ensemble_decision.reason}")
            else:
                # 기존 단일 전략 모드 (변경 없음)
                signal = self.strategy.compute_signal(df)
                
                if signal and signal.get('side'):
                    self._process_signal(signal)
    
    def _convert_ensemble_to_signal(self, ensemble_decision: EnsembleDecision) -> dict:
        """
        EnsembleDecision을 기존 엔진이 사용하는 signal dict로 변환
        
        Args:
            ensemble_decision: Ensemble 의사결정
        
        Returns:
            dict: 기존 signal_logic 형식 (side, entry, sl, tp, ...)
        """
        # Tier1: chosen_strategy 사용
        # Tier2: contributing_strategies 중 하나 사용 (또는 평균)
        # 여기서는 간단히 첫 번째 전략의 raw_signal 사용
        
        if ensemble_decision.tier == 'tier1' and ensemble_decision.chosen_strategy:
            # Tier1: chosen_strategy의 raw_signal 사용
            chosen = next(
                (d for d in ensemble_decision.decisions if d.name == ensemble_decision.chosen_strategy),
                None
            )
            if chosen and chosen.raw_signal:
                return chosen.raw_signal
        elif ensemble_decision.tier == 'tier2' and ensemble_decision.contributing_strategies:
            # Tier2: contributing 중 첫 번째 전략 사용 (또는 평균 계산)
            first_contrib = ensemble_decision.contributing_strategies[0]
            chosen = next(
                (d for d in ensemble_decision.decisions if d.name == first_contrib),
                None
            )
            if chosen and chosen.raw_signal:
                return chosen.raw_signal
        
        # Fallback: 빈 신호
        return {'side': None}
```

**주의사항**:
- **DO-NOT-TOUCH 영역**: portfolio_manager, risk_manager, position_sizer, position_tracker는 절대 수정 금지
- **최소 변경 원칙**: engine.py에서 신호 생성 부분만 Hook, 나머지 로직은 그대로 유지
- **Config 기반 분기**: ensemble.enabled=false일 때는 기존 코드 경로 100% 유지

---

## 6-A. Full Engine Integration (PHASE19-3+)

### 6-A.1 통합 전략

**기존 문제점**:
- PHASE19-3 Prototype에서는 Aggregator가 구현되었지만 실제 엔진 루프에 연결 안 됨
- ensemble.enabled=true로 설정해도 실제로는 단일 전략 모드로 동작

**Full Integration 목표**:
1. Engine 초기화 시 StrategyRegistry, ScoreEngine, Aggregator 생성
2. 메인 루프에서 Ensemble 모드일 때 여러 전략의 신호 + 점수 수집
3. Aggregator.decide() 호출하여 최종 의사결정
4. EnsembleDecision → signal dict 변환하여 기존 파이프라인에 전달

### 6-A.2 구현 위치

**execution/engine.py 수정 지점**:

1. **초기화 섹션** (line 180-210 근처):
```python
# PHASE19-3+: Ensemble 컴포넌트 초기화
ensemble_registry = None
ensemble_score_engine = None
ensemble_aggregator = None

if use_ensemble:
    from common.registry import StrategyRegistry
    from common.ensemble import ScoreEngine, EnsembleAggregator
    
    ensemble_registry = StrategyRegistry()
    ensemble_registry.scan()  # 모든 전략 스캔
    
    ensemble_score_engine = ScoreEngine()
    ensemble_aggregator = EnsembleAggregator(ensemble_registry, ensemble_score_engine)
    
    logger.info(f"✅ [ENSEMBLE] Aggregator 초기화 완료")
```

2. **메인 루프 신호 생성 섹션** (line 896-1118 근처):

**기존 로직**:
```python
# line 896-1118: 각 전략별로 순회하며 signal_logic 호출
for strategy_id, strategy_module in selected_strategies.items():
    signal = strategy_module.signal_logic(df_tf, cfg)
    if signal and signal.get("side"):
        signals.append(signal)
```

**Ensemble 통합 후**:
```python
if use_ensemble:
    # PHASE19-3+: Ensemble 모드
    ensemble_strategies = config.get("ensemble", {}).get("strategies", ["scalping"])
    
    # 지표 계산된 DataFrame 준비 (기존 로직 재사용)
    df_with_indicators = df_tf  # 이미 add_indicators() 완료
    
    # Aggregator 호출
    ensemble_decision = ensemble_aggregator.decide(
        strategy_names=ensemble_strategies,
        df=df_with_indicators,
        regime=None  # PHASE19-4에서 구현 예정
    )
    
    # EnsembleDecision → signal dict 변환
    if ensemble_decision.side:
        signal = _convert_ensemble_decision_to_signal(ensemble_decision)
        signals.append(signal)
    else:
        logger.debug(f"⏸ [ENSEMBLE] NO TRADE: {ensemble_decision.reason}")
else:
    # 기존 단일 전략 모드 (변경 없음)
    for strategy_id, strategy_module in selected_strategies.items():
        signal = strategy_module.signal_logic(df_tf, cfg)
        if signal and signal.get("side"):
            signals.append(signal)
```

3. **EnsembleDecision → signal dict 변환 헬퍼**:
```python
def _convert_ensemble_decision_to_signal(ensemble_decision: EnsembleDecision) -> dict:
    """
    EnsembleDecision을 기존 엔진이 사용하는 signal dict로 변환
    """
    if ensemble_decision.tier == 'tier1' and ensemble_decision.chosen_strategy:
        # Tier1: chosen_strategy의 raw_signal 사용
        chosen = next(
            (d for d in ensemble_decision.decisions if d.name == ensemble_decision.chosen_strategy),
            None
        )
        if chosen and chosen.raw_signal:
            signal = chosen.raw_signal.copy()
            signal['ensemble_tier'] = 'tier1'
            signal['ensemble_confidence'] = ensemble_decision.confidence
            signal['ensemble_reason'] = ensemble_decision.reason
            return signal
    
    elif ensemble_decision.tier == 'tier2':
        # Tier2: contributing 전략들의 평균 또는 첫 번째 사용
        if ensemble_decision.contributing_strategies:
            first_contrib = ensemble_decision.contributing_strategies[0]
            chosen = next(
                (d for d in ensemble_decision.decisions if d.name == first_contrib),
                None
            )
            if chosen and chosen.raw_signal:
                signal = chosen.raw_signal.copy()
                signal['ensemble_tier'] = 'tier2'
                signal['ensemble_confidence'] = ensemble_decision.confidence
                signal['ensemble_reason'] = ensemble_decision.reason
                signal['ensemble_contributors'] = ensemble_decision.contributing_strategies
                return signal
    
    # Fallback
    return {'side': None}
```

### 6-A.3 회귀 방지

**Ensemble OFF (ensemble.enabled=false) 일 때**:
- 기존 코드 경로 100% 유지
- StrategyRegistry, ScoreEngine, Aggregator 초기화 안 함
- 메인 루프에서 `if not use_ensemble:` 블록만 실행

**검증 방법**:
1. ensemble.enabled=false로 설정
2. REAL PAPER Smoke Test 실행
3. 기존 테스트 결과와 100% 동일해야 함

---

## 7. Regime 전달 방식

### 7.1 현재 PHASE (19-3)

**상태**: RegimeClassifier 미구현  
**처리**: `regime=None` 또는 간단한 placeholder (예: 'trending')

```python
# 현재는 regime을 None으로 전달
ensemble_decision = self.aggregator.decide(
    strategy_names=self.ensemble_strategies,
    df=df,
    regime=None  # PHASE19-4에서 구현 예정
)
```

### 7.2 미래 PHASE (19-4+)

**상태**: RegimeClassifier 구현 완료  
**처리**: 실시간 Regime 분류 결과를 전달

```python
# PHASE19-4 이후
from common.ensemble.regime import RegimeClassifier

regime_classifier = RegimeClassifier()
current_regime = regime_classifier.classify(df)  # 'trending' | 'breakout' | 'ranging'

ensemble_decision = self.aggregator.decide(
    strategy_names=self.ensemble_strategies,
    df=df,
    regime=current_regime
)
```

---

## 8. 확장 포인트

### 8.1 Performance Feedback (PHASE19-8+)

**현재**: Base Weight / Factor Weight는 고정값  
**미래**: Win Rate, PF 기반 동적 조정

```python
# PHASE19-8+
class PerformanceTracker:
    def update_weights(self, strategy_name, outcome):
        recent_winrate = self.calculate_winrate(strategy_name, window=20)
        
        if recent_winrate < 0.4:
            metadata.base_weight *= 0.9  # 10% 감소
        elif recent_winrate > 0.6:
            metadata.base_weight *= 1.05  # 5% 증가
```

### 8.2 Multi-Symbol (PHASE20)

**현재**: 단일 심볼 전제 (BTCUSDT)  
**미래**: 여러 심볼에 대해 Ensemble 실행

```python
# PHASE20
for symbol in symbols:
    df = self._prepare_dataframe(symbol, candle)
    ensemble_decision = self.aggregator.decide(
        strategy_names=self.ensemble_strategies,
        df=df,
        regime=regime_classifier.classify(df),
        symbol=symbol  # 심볼별 metadata/config
    )
```

### 8.3 Advanced Aggregation

**현재**: 3-Tier (High-Confidence / Consensus / Skip)  
**미래**: ML 기반 Meta-Model

```python
# 미래
class MLAggregator(EnsembleAggregator):
    def aggregate(self, decisions, regime):
        # Random Forest / XGBoost로 decisions → final_decision
        features = self._extract_features(decisions, regime)
        prediction = self.ml_model.predict(features)
        return prediction
```

---

## 9. 테스트 전략

### 9.1 단위 테스트

**파일**: `tests/test_phase19_3_aggregator.py`

**항목**:
1. Tier 1 단일 High-Confidence 선택
2. Tier 1 충돌 (차이 큼) → 높은 쪽 선택
3. Tier 1 충돌 (차이 작음) → NO TRADE
4. Tier 2 Consensus (LONG 2 vs SHORT 1) → LONG 선택
5. Tier 2 동률 → NO TRADE
6. evaluate_strategies + aggregate End-to-End (mock)

### 9.2 통합 테스트

**Smoke Test**:
1. **Ensemble OFF**: 기존 단일 전략 모드 (REAL PAPER 3분)
2. **Ensemble ON**: Aggregator 사용 (REAL PAPER 3분)

**검증**:
- ERROR/CRITICAL 로그 없음
- 기존 기능 회귀 없음
- Ensemble 모드에서 최소 1회 이상 진입 시도

---

## 10. 예상 문제 & 해결 방안

### 10.1 Factor 계산 실패

**문제**: df에 필요한 지표(ATR, EMA, RSI 등)가 없을 경우  
**해결**: `compute_all_factors(df)`는 지표 없으면 중립값(0.5) 반환 (PHASE19-2에서 구현됨)

### 10.2 모든 전략이 신호 없음

**문제**: `evaluate_strategies()`가 빈 리스트 반환  
**해결**: `aggregate([])`는 Tier 3 (Skip) 반환 → 엔진은 이번 캔들 건너뛰기

### 10.3 Ensemble vs 단일 전략 성과 비교

**문제**: Ensemble이 항상 더 나은지 불명확  
**해결**: PHASE19-3에서는 구현만, 성과 비교는 Backtest로 검증 (별도 작업)

---

## 11. Acceptance Criteria

- [x] EnsembleAggregator 클래스 구현
- [x] StrategyDecision, EnsembleDecision dataclass 정의
- [x] 3-Tier Aggregation 로직 구현
- [x] Config에 ensemble.enabled, ensemble.strategies 추가
- [x] Engine Hook (ensemble ON/OFF 분기)
- [x] 단위 테스트 PASS (6/6)
- [x] Smoke Test (Ensemble ON/OFF 모두)
- [x] DO-NOT-TOUCH 영역 보존
- [x] 설계 문서 작성 (이 문서)
- [x] COMPLETE_REPORT 작성
- [x] Git Commit

---

**문서 작성**: 2025-11-20  
**다음 작업**: PHASE19-4 (Regime Classifier 구현)

**END OF DESIGN DOC**
