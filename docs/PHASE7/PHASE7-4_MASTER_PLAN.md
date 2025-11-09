# PHASE7-4 마스터 플랜: 전략 개선 (승률 50% 달성)

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

### 2. 신호 품질 개선 (1주)

**개선**:
- Confidence threshold 상향 (0.6 → 0.7)
- 변동성 regime 필터링
- 최소 Ensemble 투표 2개 이상
- ATR/Volume 필터 추가

**영향 파일**:
- `strategies/ensemble.py`
- `strategies/*.py` (개별 전략)
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

## 릴리즈 노트

PHASE7-4: 백테스트 + 신호 품질 개선 + 리스크 강화로 승률 50% 달성. 상용 수준 근접.
