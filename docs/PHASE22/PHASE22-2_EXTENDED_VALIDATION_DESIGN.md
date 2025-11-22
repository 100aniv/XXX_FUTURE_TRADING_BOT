# PHASE22-2 Extended Validation Design Document

**작성일**: 2025-11-22  
**상태**: 🔄 **IN PROGRESS**  
**목적**: Ensemble v2 (5개 전략) 장기 Paper 검증 (12~24H)

---

## 1. Overview

### 1.1 PHASE22-2의 목적

**핵심 목표**:
- 5개 전략 패밀리(Scalping + 4개 v2 전략)를 포함한 **Ensemble v2**를
  **12~24시간 PAPER 모드로 장기 검증**하여 상용급 엔진 안정성 확보
- 이는 **수익률 최적화가 아니라 인프라 안정성 검증**에 초점을 둔다

**PHASE22-1과의 차이**:
| 항목 | PHASE22-1 | PHASE22-2 |
|------|-----------|-----------|
| **목표** | 신규 4개 전략 구현 및 Unit Test | 5개 전략 통합 Ensemble 장기 Paper 검증 |
| **범위** | 코드 구현 + 단위 테스트 | 엔진/Risk/Portfolio/FlowGuardian 통합 검증 |
| **Duration** | Unit Test (즉시 완료) | 12~24H Paper Runtime |
| **산출물** | 전략 코드 + 설계 문서 | 장기 실행 결과 분석 Report |

### 1.2 검증 목표

**인프라 안정성** (최우선):
- 12~24H 동안 CRITICAL/ERROR 로그 없이 정상 구동
- FlowGuardian/RiskManager에 의한 비정상 STOP 없음
- DB/Redis 연결 안정성 확인

**전략 다양성**:
- 5개 전략 모두 최소 1건 이상 트레이드 발생 (극단적 시장 정체 상황 제외)
- 특정 전략에 편중되지 않고 다양한 신호 생성

**데이터 무결성**:
- PaperTrade/Scorecard/DB 기록 누락 없음
- 포지션/PnL/Equity 계산 정확성

---

## 2. Test Universe

### 2.1 Symbol & Timeframe

**Symbol**:
- **BTCUSDT** (단일 심볼, PHASE26+ Multi-Symbol 전 검증)

**Timeframe 조합**:
- 전략별로 서로 다른 Timeframe 사용:
  - scalping_v3: **3m**
  - volatility_breakout_v2: **15m**
  - mean_reversion_v2: **5m**
  - trend_follow_v2: **1h**
  - volume_based_v2: **5m**

**Note**: Multi-Timeframe 통합은 현재 엔진 구조에서 지원 여부를 확인 필요.
단일 Timeframe으로 제한할 경우 **5m**으로 통일하고, 각 전략이 해당 TF로 동작 가능하도록 조정.

### 2.2 전략별 Timeframe 결정

**Option 1 (Multi-TF 지원 시)**:
- 각 전략이 고유 TF 사용
- 데이터 피드는 1m/3m/5m/15m/1h 동시 수신 (기존 인프라 확인 필요)

**Option 2 (Single TF 강제)**:
- 모든 전략을 **5m**으로 통일 실행
- 전략 로직은 변경하지 않되, Config에서 `timeframe: 5m` 설정

**👉 실행 시 엔진 구조 확인 후 결정**

---

## 3. Ensemble v2 구성

### 3.1 포함 전략 (5개)

| ID | 전략명 | Family | Timeframe | Role | Status |
|----|--------|--------|-----------|------|--------|
| 1 | scalping_v3 | HF Momentum | 3m | 단타 모멘텀 | ✅ PHASE21 검증 완료 |
| 2 | volatility_breakout_v2 | Volatility Breakout | 15m | 변동성 돌파 | ✅ PHASE22-1 구현 완료 |
| 3 | mean_reversion_v2 | Mean Reversion | 5m | 평균 회귀 | ✅ PHASE22-1 구현 완료 |
| 4 | trend_follow_v2 | Trend Following | 1h | 추세 추종 | ✅ PHASE22-1 구현 완료 |
| 5 | volume_based_v2 | Volume-Based | 5m | 거래량 주도 | ✅ PHASE22-1 구현 완료 |

### 3.2 전략별 역할 및 Metadata

**1) scalping_v3 (Family 1: HF Momentum)**
```python
metadata = StrategyMetadata(
    strategy_name='scalping',
    optimal_regime='trending',
    worst_regime='ranging',
    factor_weights={
        'momentum': 0.4,
        'trend_strength': 0.3,
        'volume': 0.2,
        'volatility': 0.1,
    }
)
```
- 역할: 단기 모멘텀 포착, 고빈도 거래
- Entry: EMA Fresh Trend + RSI 극단값
- RR: 1.5

**2) volatility_breakout_v2 (Family 2: Volatility Breakout)**
```python
metadata = StrategyMetadata(
    strategy_name='breakout_v2',
    optimal_regime='trending',
    worst_regime='low_volatility',
    factor_weights={
        'momentum': 0.2,
        'volatility': 0.4,
        'volume': 0.2,
        'trend_strength': 0.1,
        'breakout_probability': 0.1,
    }
)
```
- 역할: ATR 기반 SR 레벨 돌파
- Entry: Resistance/Support 돌파 + Volume 확인
- RR: 2.0

**3) mean_reversion_v2 (Family 3: Mean Reversion)**
```python
metadata = StrategyMetadata(
    strategy_name='reversion_v2',
    optimal_regime='ranging',
    worst_regime='trending',
    factor_weights={
        'overbought_oversold': 0.5,
        'volatility': 0.2,
        'momentum': 0.1,
        'volume': 0.1,
        'breakout_probability': 0.1,
    }
)
```
- 역할: BB + RSI 극단값 회귀
- Entry: BB Lower/Upper 터치 + RSI 과매도/과매수
- RR: 1.5

**4) trend_follow_v2 (Family 4: Trend Following)**
```python
metadata = StrategyMetadata(
    strategy_name='trend_v2',
    optimal_regime='trending',
    worst_regime='ranging',
    factor_weights={
        'trend_strength': 0.6,
        'momentum': 0.1,
        'volatility': 0.1,
        'volume': 0.1,
        'overbought_oversold': 0.1,
    }
)
```
- 역할: SMA 50/200 + MACD 장기 추세
- Entry: Golden/Death Cross + MACD 확인
- RR: 2.5

**5) volume_based_v2 (Family 5: Volume-Based)**
```python
metadata = StrategyMetadata(
    strategy_name='volume_v2',
    optimal_regime='high_volume',
    worst_regime='low_volume',
    factor_weights={
        'volume': 0.5,
        'momentum': 0.2,
        'volatility': 0.1,
        'trend_strength': 0.1,
        'breakout_probability': 0.1,
    }
)
```
- 역할: OBV + Volume Spike 매수/매도 압력
- Entry: OBV 방향성 + Volume 폭발 + EMA
- RR: 1.8

### 3.3 Ensemble Aggregation 규칙

**3-Tier Aggregation** (기존 ensemble/aggregator.py 구조 재사용):
- **Tier 1 (High-Confidence)**: score >= 0.8
  - 단일 전략만으로 진입
- **Tier 2 (Consensus)**: 0.5 <= score < 0.8, 2+ votes
  - 복수 전략 합의로 진입
- **Tier 3 (Skip)**: 조건 미달 시 건너뛰기

**ScoreEngine**:
- Factor Weighted Sum: Σ (factor_i × weight_i)
- Regime Multiplier: optimal/worst regime 가중
- Base Weight 적용

---

## 4. Metrics & Logging

### 4.1 추적 메트릭

**엔진 안정성**:
- Total Runtime (wall_clock / market_time)
- ERROR/CRITICAL 로그 카운트
- FlowGuardian BLOCK 발생 횟수
- WebSocket 재연결 횟수

**전략 활동**:
- 전략별 신호 발생 횟수 (LONG/SHORT)
- 전략별 트레이드 체결 수
- 전략별 평균 PnL
- 전략별 Win-rate

**Risk & Portfolio**:
- Total Trades (LONG/SHORT)
- Win/Loss Count
- Total PnL
- Max Drawdown
- Average Position Size
- Leverage 활용도

**데이터 무결성**:
- 캔들 수신 정상 여부
- DB 기록 누락 체크
- Redis 상태 체크

### 4.2 Logging 전략

**로그 레벨**:
- INFO: 기본 동작 (신호/진입/청산)
- WARNING: 일시적 에러 (네트워크 리트라이 등)
- ERROR: 심각한 에러 (DB 연결 실패 등)
- CRITICAL: 엔진 정지 필요 (치명적 에러)

**로그 출력 경로**:
- Console: INFO 이상
- File: DEBUG 이상 (`logs/phase22_2_{run_id}.log`)

**모니터링 주기**:
- 실시간 로그 tail: `tail -f logs/phase22_2_{run_id}.log`
- 주기적 체크: 1시간마다 트레이드 수/PnL/포지션 확인

---

## 5. Test Matrix

### 5.1 Quick Smoke Test (15~30분)

**목적**: 기본 동작 확인 및 설정 검증

**Config**: `configs/paper/phase22_2_ensemble_quick.yml`

**Duration**: 15~30분 (wall_clock)

**Acceptance Criteria**:
- [x] 엔진 정상 시작 및 종료
- [x] 최소 3건 이상 트레이드 발생
- [x] 5개 전략 중 최소 2개 이상 신호 발생
- [x] CRITICAL/ERROR 로그 없음
- [x] Scorecard 정상 생성

**실행 커맨드**:
```bash
python scripts/run_phase22_2_ensemble.py --config configs/paper/phase22_2_ensemble_quick.yml --duration-hours 0.5
```

### 5.2 Main Run (12H)

**목적**: 장기 안정성 검증 및 전략 다양성 확인

**Config**: `configs/paper/phase22_2_ensemble_12h.yml`

**Duration**: 12시간 (wall_clock)

**Acceptance Criteria**:
- [x] 12H 동안 CRITICAL/ERROR 로그 없음 (일시적 네트워크 리트라이 제외)
- [x] FlowGuardian/RiskManager 비정상 STOP 없음
- [x] 5개 전략 모두 최소 1건 이상 트레이드 발생
- [x] 특정 전략 편중도 < 80% (1개 전략이 80% 이상 거래 독점 안 됨)
- [x] PnL 극단 붕괴 없음 (Max DD < 50%, Equity > Initial × 0.5)
- [x] DB/Redis 기록 누락 없음
- [x] 포지션 비정상 누적 없음 (미청산 포지션 < 5개)

**실행 커맨드**:
```bash
python scripts/run_phase22_2_ensemble.py --config configs/paper/phase22_2_ensemble_12h.yml --duration-hours 12
```

### 5.3 Extended Run (24H, Optional)

**목적**: 추가 안정성 검증 (필요 시)

**Config**: `configs/paper/phase22_2_ensemble_24h.yml`

**Duration**: 24시간 (wall_clock)

**Note**: 12H 테스트에서 이슈가 발견되지 않고 안정적이면 Optional로 수행.

---

## 6. Acceptance Criteria (엔진 안정성 기준)

### 6.1 필수 조건 (PASS 기준)

**1) 엔진 안정성**:
- [x] 12~24H 동안 **CRITICAL 로그 0건**
- [x] ERROR 로그 < 10건 (일시적 네트워크 리트라이 제외)
- [x] FlowGuardian에 의한 **비정상 STOP 없음**
- [x] WebSocket 재연결 < 5회 (네트워크 불안정 시 예외)

**2) 전략 다양성**:
- [x] 5개 전략 모두 **최소 1건 이상 트레이드 발생**
  - 예외: 극단적 시장 정체 (24H 동안 BTC 변동폭 < 1%) 시 일부 전략 0건 허용 (문서 명시)
- [x] 특정 전략 편중도 < 80%
  - scalping_v3가 80% 이상 거래 독점하지 않도록 모니터링

**3) Risk & Portfolio**:
- [x] Max Drawdown < 50%
- [x] Equity > Initial Balance × 0.5 (절반 이상 보존)
- [x] 미청산 포지션 < 5개 (비정상 누적 없음)
- [x] 레버리지 상한 위반 없음

**4) 데이터 무결성**:
- [x] DB `paper_trades` 테이블 기록 정상
- [x] Scorecard CSV/MD 정상 생성
- [x] Redis Guard 상태 정상 유지
- [x] 캔들 수신 누락 < 1% (WebSocket 안정성)

### 6.2 권장 조건 (NICE-TO-HAVE)

- [ ] Total Trades > 20 (충분한 샘플)
- [ ] Win-rate > 20%
- [ ] Total PnL > -$500 (극단적 손실 방지)
- [ ] Average Position Hold Time < 2H (단기 거래 특성)

---

## 7. 실행 스크립트 & 모니터링

### 7.1 실행 스크립트

**주 스크립트**: `scripts/run_phase22_2_ensemble.py`

**역할**:
- Config 로드
- 엔진 초기화 및 실행
- 실시간 모니터링 루프
- Scorecard 생성

**기존 스크립트 재사용**:
- `scripts/run_phase22_ensemble_single_symbol.py` 기반으로 작성
- 최소 변경 원칙: Duration/Config 경로만 조정

**모니터링 스크립트**:
- `scripts/monitor_phase22_paper.py`: 실시간 트레이드/PnL 모니터링
- `scripts/check_paper_trades.py`: DB 트레이드 확인
- `scripts/check_trades_detail.py`: 상세 트레이드 내역

### 7.2 실행 전 체크리스트

**환경 준비**:
- [ ] 가상환경 활성화 (`trading_bot_env`)
- [ ] Docker 실행 확인 (`docker ps` → Postgres, Redis)
- [ ] Redis 초기화 (기존 Guard/쿨다운 상태 클리어)
- [ ] DB 연결 테스트 (`python scripts/check_db_config.py`)

**Config 검증**:
- [ ] Config 파일 경로 확인
- [ ] Symbol/Timeframe 설정 확인
- [ ] 5개 전략 모두 `enabled: true` 확인
- [ ] Duration 설정 확인

**로그/출력 준비**:
- [ ] 로그 폴더 생성 확인 (`logs/`)
- [ ] Scorecard 출력 경로 확인 (`scorecards/paper_phase22_2/`)

### 7.3 중간 점검 (Main 12H 실행 중)

**주기적 체크** (1시간마다):
- [ ] 엔진 프로세스 살아있는지 (`ps aux | grep python`)
- [ ] 로그에 CRITICAL/ERROR 없는지 (`tail -f logs/phase22_2_*.log | grep -E "CRITICAL|ERROR"`)
- [ ] 트레이드 카운트 증가하는지 (`python scripts/check_paper_trades.py`)
- [ ] 포지션 비정상 누적 없는지 (미청산 < 5개)
- [ ] 특정 전략만 과도하게 거래하지 않는지

**이상 징후 발견 시**:
- CRITICAL 로그: 즉시 중단, 원인 분석
- 포지션 누적 (5개 초과): 수동 청산 또는 엔진 재시작 검토
- 특정 전략 80% 초과 편중: Config 재조정 검토 (PHASE22-3에서 다룰 예정)

---

## 8. Config 설계 요구사항

### 8.1 공통 요구사항

**Symbol**:
```yaml
symbols:
  - BTCUSDT
```

**Timeframe** (Option 1: Multi-TF):
```yaml
feed:
  timeframes:
    - 1m
    - 3m
    - 5m
    - 15m
    - 1h
```

**Timeframe** (Option 2: Single TF):
```yaml
timeframe: 5m
```

**활성 전략** (5개 모두):
```yaml
strategies:
  scalping_v3:
    enabled: true
    # ... params
  breakout_v2:
    enabled: true
    # ... params
  reversion_v2:
    enabled: true
    # ... params
  trend_v2:
    enabled: true
    # ... params
  volume_v2:
    enabled: true
    # ... params
```

**Ensemble**:
```yaml
ensemble:
  enabled: true
  tier1_threshold: 0.8
  tier2_threshold: 0.5
  tier2_min_votes: 2
```

**Risk** (보수적 설정):
```yaml
risk:
  max_drawdown_pct: 50.0
  per_trade_risk_pct: 2.0
  max_leverage: 10
  max_open_positions: 5
```

**Portfolio**:
```yaml
portfolio:
  initial_balance: 50000
  max_position_value: 10000  # 단일 포지션 최대 $10K
```

**Duration** (Quick):
```yaml
duration_mode: wall_clock
duration_hours: 0.5  # 30분
```

**Duration** (12H):
```yaml
duration_mode: wall_clock
duration_hours: 12
```

### 8.2 Output 경로

**Scorecard**:
```yaml
scorecard:
  output_dir: scorecards/paper_phase22_2/{run_id}/
```

**Logs**:
```yaml
logging:
  log_level: INFO
  log_file: logs/phase22_2_{run_id}.log
```

---

## 9. 다음 단계 (PHASE22-3+)

### 9.1 PHASE22-3: Parameter Tuning

**PHASE22-2 결과 기반**으로:
- Flash Guard 파라미터 튜닝 (flash_pct, window)
- 쿨다운 파라미터 조정 (strategy/global cooldown)
- Slippage/Commission 파라미터 조정

### 9.2 PHASE23: Strategy & Ensemble Refinement

**발견된 이슈 개선**:
- 특정 전략 신호 부족 → Entry 조건 완화 또는 대체 전략 추가
- PnL 편향 → Factor Weight/Regime Multiplier 조정
- 포지션 집중 → Risk 파라미터 재조정

---

## 10. Smoke Test Result (Placeholder)

**실행일**: TBD

**Config**: `configs/paper/phase22_2_ensemble_quick.yml`

**Duration**: 30분

**결과**:
- 엔진 시작/종료: [ ]
- 총 트레이드: [ ]건
- 전략별 트레이드: 
  - scalping_v3: [ ]
  - breakout_v2: [ ]
  - reversion_v2: [ ]
  - trend_v2: [ ]
  - volume_v2: [ ]
- CRITICAL/ERROR 로그: [ ]건
- Scorecard 생성: [ ]

**이슈**:
- [ ] 발견된 이슈 기록

---

**Document Version**: v1.0  
**Last Updated**: 2025-11-22  
**Author**: Windsurf AI (PHASE22-2 Design Session)  
**Status**: 🔄 IN PROGRESS
