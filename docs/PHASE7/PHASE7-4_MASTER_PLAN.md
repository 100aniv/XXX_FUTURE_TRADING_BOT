# PHASE7-4 마스터 플랜: 전략 개선 (승률 50% 달성)

**최종 업데이트**: 2025-11-13  
**현행 코드(b84c03c)**: 전략별 독립 설정/동적 가중치/백테스트 파이프라인 미구현  
**상태**: ⚠️ PHASE7-2/3 선행 필요. 본 문서 내용은 TO-BE(미구현)

## 📌 Executive Summary (TL;DR)

- **역할**: 전략 품질 개선의 마스터 플랜. 백테스트 파이프라인, 전략별 분석, 동적 가중치 강화.
- **현행**: 안정 버전(b84c03c). 7-2/7-3 선행 미충족으로 본 문서 항목은 TO-BE 상태.
- **방침**: 선행 게이트 통과 후 백테스트→전략 필터링→가중치 강화 순으로 단계 적용.
- **스냅샷**: 최근 2h/24h 성과는 아래 Standard Snapshot 및 SMOKE_TEST_MONITOR.md 참조.

## 🔎 Quick Nav

- [배경/의도](#-배경의도-overview)
- [목표](#-목표-goals)
- [범위](#-범위-scope-in)
- [수용 기준/체크리스트](#-수용-기준-게이트)
- [업데이트 로그](#-업데이트-로그)

## 📊 Standard Snapshot (Paper)

- **최근 2시간**: closed=818, win_rate=38.3%, avg_pnl=-0.24%, min=-31.01%, max=+62.25, >8% 손실=29, 무결성 OK(양방향 0, OPEN 11)
- **최근 24시간**: closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, min=-32.47, max=+70.40, >8% 손실=64, 무결성 OK(양방향 0)
- 출처: SMOKE_TEST_MONITOR.md 실측 스냅샷 (2025-11-13)

## ⚠️ 현재 상태 스냅샷 (최근 30/60분 · Paper)

- **60분**: closed=394, win_rate=31.2%, >8% 손실=20건  
  - Exit breakdown: SL 201건(avg -3.83%, min -16.65%), TP1 196건(avg +2.28%, min -4.86%), ONE_WAY_MODE 2건
- **30분**: closed=151, win_rate=26.5%, avg_pnl=-0.84%, min=-12.05%, max=+25.30%  
- **무결성**: 중복 진입 0, 양방향 OPEN 0, OPEN=13

---

## ✅ 수용 기준 (게이트)

- Paper 1주 평균 승률 ≥ 50%
- Sharpe Ratio > 1.0, Profit Factor > 1.1
- 24h 기준 >8% 손실 0건, TP1 손실 0건
- 시간당 거래 ≤ 15건, 포지션 수 ≤ 10개(포트폴리오)

## 📋 체크리스트

- 전략별 독립 설정 설계안 확정(cooldown_minutes, max_trades_per_hour, max_positions)
- 백테스트 파이프라인 가동(2024년 전체, 전략별)
- 성과 기반 동적 가중치(adaptive_weight) 검증 및 클램핑
- Correlation/Exposure 한도 도입 계획 수립
- SQL/리포트 지표 정의 고정(win_rate, PF, Sharpe, >8%)

## 🔗 참조 문서

- PHASE7_ALGORITHM_BEST.md (MASTER)
- PHASE7-3_MASTER_PLAN.md (운영 안정성 선행)
- SMOKE_TEST_MONITOR.md (관측/SQL)

## 📝 업데이트 로그

- 2025-11-13: 2차 표준화(수용 기준/체크리스트/참조 추가)

## 배경/의도 (Overview)

PHASE 7-1~7-3 완료로 기술적 안정성 확보. 이제 **전략 품질** 개선:
- 현재 승률: 45% (7-2 목표) → 목표: 50% 이상
- 전략별 성과 분석 필요
- 낮은 승률 전략 제거 또는 개선
- 백테스트로 검증

상용 수준 (55~60%) 근접을 위한 최종 성과 개선.

## 목표 (Goals)

- **승률 50% 이상** (Paper 1주 평균)
- **백테스트 파이프라인** 구축
- **전략별 성과 분석** 및 필터링
- **신호 품질 개선** (Confidence scoring)
- **리스크 관리 강화** (Correlation, Exposure Limit)

## 범위 (Scope, In)

### 1. 백테스트 파이프라인 (3일)

**구축**:
- 과거 데이터 (2024년 전체)
- 전략별 백테스트 실행
- 성과 메트릭 (승률/Sharpe/MDD)
- 리포트 자동 생성

**영향 파일**:
- `scripts/backtest_runner.py` (신규)
- `analytics/backtest_analyzer.py` (신규)
- `data/historical/*.csv` (과거 데이터)

### 2. 전략별 성과 분석 및 개선 (1주) ⭐ 앙상블 특화

**개선** (PHASE7_ALGORITHM_BEST.md 기반):

#### A. 전략별 개별 백테스트

- **목적**: 6개 전략 중 어떤 것이 좋은지 검증
- **방법**:
  - 각 전략 단독 백테스트 (2024년 전체)
  - 승률, Sharpe, MDD 측정
  - 승률 45% 미만 전략 식별

**예상 결과**:
```
scalping: 승률 42% (조정 필요)
daytrade: 승률 48% (양호)
swing: 승률 52% (우수)
breakout: 승률 38% (문제)
trend: 승률 51% (우수)
reversion: 승률 44% (조정 필요)
```

#### B. 성과 기반 동적 가중치 강화

**현재 문제** (ensemble.py::calculate_experience_score):
- Experience Score 있지만 약함
- 거래 수만 강하게 반영, 승률은 약하게 반영

**개선**:
```python
def calculate_adaptive_weight(strategy_id, perf, config):
    """
    성과 기반 적응형 가중치
    
    승률 기준:
    - 45% 미만: 가중치 50% 감소
    - 45-55%: 가중치 100% (기본)
    - 55% 이상: 가중치 150% 증가
    """
    base_weight = config.get('ensemble', {}).get('weights', {}).get(strategy_id, 1.0)
    
    winrate = perf.get(strategy_id, {}).get('winrate', 0.5)
    total_trades = perf.get(strategy_id, {}).get('total_trades', 0)
    sharpe = perf.get(strategy_id, {}).get('sharpe', 0.0)
    
    # 최소 거래 수 페널티
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

**영향 파일**:
- `strategies/ensemble.py` (calculate_adaptive_weight 추가)
- `scripts/backtest_runner.py` (전략별 백테스트)
- `analytics/strategy_analyzer.py` (전략별 분석)
- `config.yml::strategies.*`

### 3. 리스크 관리 강화 (2일)

**추가**:
- Position Correlation (심볼 간 상관관계)
- 섹터별 Exposure Limit
- 심볼별 최대 포지션 수

**영향 파일**:
- `execution/risk_manager.py`
- `config.yml::risk.*`

## 제외 (Out-of-Scope)

- ML 모델 통합 (복잡도 높음, optional)
- 새로운 전략 추가 (기존 개선 우선)
- Live 전환 (PHASE 7-5)

## 설정 키

```yaml
strategies:
  ensemble:
    min_votes: 2                    # 최소 투표 2개
    confidence_threshold: 0.7       # 0.6 → 0.7
    use_regime_filter: true         # 변동성 regime
  
  filters:
    atr_min_pct: 2.0                # 최소 ATR 2%
    volume_min_ratio: 1.5           # 평균 대비 1.5배

risk:
  position_correlation:
    enabled: true
    max_correlation: 0.7            # 최대 상관관계 0.7
  
  exposure_limits:
    max_per_symbol: 1               # 심볼당 1개
    max_per_sector: 3               # 섹터당 3개
    max_total: 10                   # 전체 10개

backtest:
  data_path: "data/historical"
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  report_output: "analytics/backtest_reports"
```

## 구현 상세

### 백테스트 파이프라인

```python
# scripts/backtest_runner.py
def run_backtest(strategy_name, symbols, start_date, end_date):
    """전략 백테스트 실행"""
    results = {}
    
    for symbol in symbols:
        # 데이터 로드
        df = load_historical_data(symbol, start_date, end_date)
        
        # 전략 실행
        trades = strategy.backtest(df)
        
        # 메트릭 계산
        metrics = calculate_metrics(trades)
        results[symbol] = metrics
    
    # 리포트 생성
    generate_report(strategy_name, results)
    return results

def calculate_metrics(trades):
    """백테스트 메트릭"""
    return {
        'total_trades': len(trades),
        'win_rate': sum(1 for t in trades if t['pnl'] > 0) / len(trades),
        'avg_pnl': np.mean([t['pnl'] for t in trades]),
        'sharpe_ratio': calculate_sharpe(trades),
        'max_drawdown': calculate_mdd(trades)
    }
```

### 신호 품질 개선

```python
# strategies/ensemble.py
def filter_signals(signals, candle, config):
    """신호 필터링"""
    filtered = []
    
    for signal in signals:
        # 1. Confidence 체크
        if signal['confidence'] < config.get('confidence_threshold', 0.7):
            continue
        
        # 2. ATR 필터
        atr_pct = candle['atr'] / candle['close'] * 100
        if atr_pct < config.get('filters', {}).get('atr_min_pct', 2.0):
            continue
        
        # 3. Volume 필터
        volume_ratio = candle['volume'] / candle['avg_volume']
        if volume_ratio < config.get('filters', {}).get('volume_min_ratio', 1.5):
            continue
        
        # 4. Regime 필터
        if config.get('use_regime_filter', True):
            if not is_favorable_regime(candle):
                continue
        
        filtered.append(signal)
    
    return filtered
```

### 리스크 관리 강화

```python
# execution/risk_manager.py
def check_position_correlation(new_symbol, existing_positions, config):
    """포지션 상관관계 체크"""
    if not config.get('risk', {}).get('position_correlation', {}).get('enabled', False):
        return True
    
    max_corr = config.get('risk', {}).get('position_correlation', {}).get('max_correlation', 0.7)
    
    for pos in existing_positions:
        correlation = calculate_correlation(new_symbol, pos['symbol'])
        if correlation > max_corr:
            logger.warning(f"⚠️ 높은 상관관계: {new_symbol} <-> {pos['symbol']} ({correlation:.2f})")
            return False
    
    return True

def check_exposure_limits(new_symbol, existing_positions, config):
    """Exposure Limit 체크"""
    limits = config.get('risk', {}).get('exposure_limits', {})
    
    # 1. 심볼당 제한
    max_per_symbol = limits.get('max_per_symbol', 1)
    symbol_count = sum(1 for p in existing_positions if p['symbol'] == new_symbol)
    if symbol_count >= max_per_symbol:
        logger.warning(f"⚠️ 심볼 제한 초과: {new_symbol} ({symbol_count}개)")
        return False
    
    # 2. 섹터당 제한
    max_per_sector = limits.get('max_per_sector', 3)
    sector = get_sector(new_symbol)
    sector_count = sum(1 for p in existing_positions if get_sector(p['symbol']) == sector)
    if sector_count >= max_per_sector:
        logger.warning(f"⚠️ 섹터 제한 초과: {sector} ({sector_count}개)")
        return False
    
    # 3. 전체 제한
    max_total = limits.get('max_total', 10)
    if len(existing_positions) >= max_total:
        logger.warning(f"⚠️ 전체 포지션 제한 초과: {len(existing_positions)}개")
        return False
    
    return True
```

## 수용 기준

### 필수

- [ ] Paper 1주 평균 승률: **50% 이상**
- [ ] 백테스트 승률: **55% 이상**
- [ ] Sharpe Ratio: **> 1.0**
- [ ] Max Drawdown: **< 20%**
- [ ] 전략별 성과: 모두 승률 45% 이상

### 선택

- [ ] TP2 도달: 10% 이상
- [ ] 손익비: 1.0 이상
- [ ] Position Correlation: < 0.7

## 테스트 플랜

```bash
# 백테스트 실행
python scripts/backtest_runner.py --strategy all --period 2024

# Paper 1주 검증
docker logs trading_bot_paper_ensemble 2>&1 | grep "승률"

# SQL 검증
SELECT 
  COUNT(*) as total,
  ROUND((COUNT(CASE WHEN pnl_pct > 0 THEN 1 END)::float / COUNT(*)) * 100, 1) as win_rate,
  ROUND(AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END), 2) as avg_win,
  ROUND(AVG(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) END), 2) as avg_loss
FROM trading.trades 
WHERE mode='paper' 
  AND ts_open >= NOW() - INTERVAL '7 days';
```

## 체크리스트

- [ ] 백테스트 파이프라인
- [ ] 전략별 성과 분석
- [ ] 신호 필터링 강화
- [ ] Correlation/Exposure 체크
- [ ] Paper 1주 검증
- [ ] 승률 50% 달성

## 연관 문서

- **PHASE7_ALGORITHM_BEST.md**: 상용 프로그램 알고리즘 비교 및 앙상블 개선안
- **GUARD_EXECUTION_ORDER_ANALYSIS.md**: 가드/차단 기능 실행 순서 분석
- **SLIPPAGE_PERFORMANCE_COMPARISON.md**: 슬리피지 성능 비교
- **체크리스트**: [PHASE7-2_MASTER_PLAN.md 항목 4](PHASE7-2_MASTER_PLAN.md) 참조

## 릴리즈 노트

PHASE7-4: 백테스트 + 신호 품질 개선 + 리스크 강화로 승률 50% 달성. 상용 수준 근접.
