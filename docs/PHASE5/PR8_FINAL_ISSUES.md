# PR8 최종 문제점 및 해결 방안

**작성**: 2025-11-05 21:36 UTC+09:00  
**상태**: 긴급 수정 필요

---

## 🚨 발견된 문제점

### 1. 레버리지 중복 (심각)
**위치**:
- `common/calculations.py` - `leverage_suggestion()` (다차원, ATR 기반)
- `execution/position_sizer.py` - `suggest_max_leverage()` (청산가 기반)

**문제**:
- 두 메서드가 다른 방식으로 레버리지 계산
- calculations는 변동성 기반
- position_sizer는 청산가 안전성 기반

**해결**:
→ position_sizer.suggest_max_leverage()를 수정하여 calculations.leverage_suggestion() 호출
→ 청산가 검증은 별도 메서드 유지

### 2. 레버리지 항상 x2 문제
**현상**:
```
2025-11-05 21:31:47 ✅ Leverage 계산: atr_pct=0.0077, lev=2
2025-11-05 21:31:47 ✅ Leverage 계산: atr_pct=0.0083, lev=2
```

**원인 분석 필요**:
- ATR이 높아서 항상 min(2)로 계산?
- 전략 성과 데이터 없어서 기본값?
- ensemble weight 미전달?

### 3. config.yml 고정값 문제
**발견**:
```yaml
capital:
  initial: 50000  # ❌ 고정값 (라이브 모드에서도 고정?)

portfolio:
  max_strategy_positions: 5  # ❌ 고정값 (성과 기반 동적 조정 필요)
  max_correlated_positions: 5  # ❌ 사용 안 함
```

**문제**:
- 라이브 모드에서 실제 자산 자동 로드 안 됨
- 포트폴리오 설정이 모두 고정값
- 성과 기반 동적 조정 없음

### 4. 라이브 모드 자산 로드 확인
**확인 필요**:
- `execution/adapters/live.py` - 바이낸스 API에서 자산 조회하는지?
- 라이브 모드 시작 시 자동으로 capital 업데이트?

---

## ✅ 해결 방안

### A. 레버리지 통합 (즉시)
```python
# position_sizer.py
def suggest_max_leverage(self, entry, stop, side, 
                        atr_pct=None, strategy_metrics=None,
                        signal_confidence=None, current_dd=0.0):
    """
    적정 레버리지 제안 (통합)
    
    1. calculations.leverage_suggestion() 호출 (다차원)
    2. 청산가 안전성 검증
    3. 둘 중 작은 값 반환
    """
    from common.calculations import leverage_suggestion
    
    # 1. 다차원 레버리지
    suggested_lev = leverage_suggestion(
        atr_pct=atr_pct,
        min_leverage=self.config['leverage']['min'],
        max_leverage=self.config['leverage']['max'],
        strategy_metrics=strategy_metrics,
        signal_confidence=signal_confidence,
        current_dd=current_dd
    )
    
    # 2. 청산가 안전성 검증
    safe_lev = self._verify_liq_safety(entry, stop, side, suggested_lev)
    
    # 3. 안전한 값 반환
    return min(suggested_lev, safe_lev)
```

### B. 라이브 모드 자산 자동 로드 (즉시)
```python
# execution/adapters/live.py
def load_live_equity(self):
    """바이낸스 API에서 실제 자산 조회"""
    balance = self.exchange.fetch_balance()
    total_usdt = balance['total']['USDT']
    return total_usdt

# main.py or engine.py
if mode == 'live':
    live_equity = adapter.load_live_equity()
    config['capital']['initial'] = live_equity
    config['equity'] = live_equity
    logger.info(f"💰 라이브 자산 로드: ${live_equity:,.2f}")
```

### C. 포트폴리오 동적 설정 (PR8 추가)
```python
# portfolio_manager.py
def calculate_dynamic_exposure(self, symbol, volatility):
    """변동성 기반 동적 exposure"""
    base_exposure = 0.3
    
    if volatility > 0.03:  # 고변동성
        return base_exposure * 0.7  # 20%
    elif volatility < 0.01:  # 저변동성
        return base_exposure * 1.3  # 40%
    else:
        return base_exposure

def calculate_strategy_budget(self, strategy, performance):
    """성과 기반 전략별 budget"""
    base_positions = 3
    
    if performance['sharpe'] > 1.5:
        return int(base_positions * 1.5)  # 5개
    elif performance['sharpe'] < 0.5:
        return int(base_positions * 0.5)  # 1개
    else:
        return base_positions
```

---

## 📋 작업 우선순위

### 🔴 즉시 (Critical)
1. ✅ 레버리지 중복 제거 (통합)
2. ✅ 레버리지 x2 문제 원인 파악
3. ✅ 라이브 모드 자산 자동 로드 구현

### 🟡 중요 (High)
4. ✅ 포트폴리오 동적 exposure
5. ✅ 전략별 동적 budget
6. ✅ config.yml 정리 (사용 안 하는 설정 제거)

### 🟢 보통 (Medium)
7. 문서 전체 정리
8. 24시간 테스트

---

## 다음 단계

1. position_sizer.py 레버리지 메서드 통합
2. 라이브 모드 자산 로드 구현
3. portfolio_manager.py 동적 설정 추가
4. config.yml 정리
5. 재빌드 & 즉시 검증
6. 문서 업데이트

**목표**: .windsurfrules 100% 준수, 중복 제거, 동적 최적화
