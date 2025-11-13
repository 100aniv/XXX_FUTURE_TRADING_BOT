# PHASE7-2 마스터 플랜: 포지션 관리 개선 (승률 45% 달성)

**작성일**: 2025-11-10  
**최종 업데이트**: 2025-11-13  
**문서 역할**: PHASE7-2 구현 계획 (앙상블 특화)  
**목적**: 전략별 독립 설정 + 거래 빈도 제한으로 승률 45% 달성  
**현행 코드(b84c03c)**: 중단 후 복원 완료, 전략별 설정 미구현  
**주의**: TO-BE 설계. 슬리피지 실패는 SLIPPAGE_PERFORMANCE_COMPARISON.md 참조.

## 📌 Executive Summary (TL;DR)

- **역할**: 앙상블 6개 전략을 독립적으로 관리. 거래 빈도 제한으로 수수료 절감, 승률 45% 달성.
- **현행**: b84c03c 복원 완료. 슬리피지(5e651dc) 실패로 중단. 전략별 설정 미구현.
- **핵심**: ① 전략별 쿨다운/제한 ② 포트폴리오 거래 빈도 제한 ③ TP/SL 최적화 ④ 슬리피지 보류.
- **예상 효과**: 시간당 거래 310→15건, 수수료 24.8%→1.2%, 승률 39.6%→45%+.

## 🔎 Quick Nav

- [현재 상태](#️-현재-상태)
- [목표 (AS-IS → TO-BE)](#-목표)
- [구현 범위](#-범위)
- [수용 기준](#-수용-기준)
- [참조 문서](#-참조-문서)

## 📊 Standard Snapshot (Paper)

- **최근 2시간**: closed=818, win_rate=38.3%, avg_pnl=-0.24%, >8% 손실=29
- **최근 24시간**: closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, >8% 손실=64
- 출처: SMOKE_TEST_MONITOR.md (2025-11-13)

---

## ⚠️ 현재 상태

**프로젝트**: ❌ 중단 → ✅ 복원 완료  
**복원 커밋**: `b84c03c` (2025-11-10 15:47)  
**중단 이유**: 슬리피지 실패(5e651dc) - 핵심 기능 마비, 승률 54%→28%, 연쇄 버그 9건  
**복원 결과**: 모든 기능 정상, 승률 54.3% 회복  
**상세**: [SLIPPAGE_PERFORMANCE_COMPARISON.md](SLIPPAGE_PERFORMANCE_COMPARISON.md)

---

## 🎯 목표

### AS-IS (현행 문제)
| 지표 | 현재 | 문제 |
|------|------|------|
| **승률** | 39.6% | 상용(60%) 대비 -20% |
| **시간당 거래** | 310건 | 수수료 누적 24.8%/h |
| **>8% 손실** | 최대 -16.65% | SL 설정 미흡 |

### TO-BE (목표)
| 지표 | 목표 | 개선 방안 |
|------|------|----------|
| **승률** | **45%+** | 전략별 독립 설정, 신호 품질 향상 |
| **시간당 거래** | **15건** | 전략별 쿨다운, 포트폴리오 제한 |
| **수수료** | **1.2%/h** | 거래 빈도 95% 감소 |
| **>8% 손실** | **0건** | ATR 기반 동적 SL (2~6%) |

---

## 📋 범위

### 1. 전략별 독립 설정 (핵심) ⭐

**문제**: 6개 전략 동일 처리 → scalping(1분)과 swing(1시간)이 동일한 제한  
**해결**: 전략별 쿨다운, 포지션 제한, 거래 빈도, 신뢰도 임계값 독립 설정

```yaml
strategies:
  scalping:
    cooldown_minutes: 5
    max_positions: 5
    max_trades_per_hour: 20
    confidence_threshold: 0.65
  swing:
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 5
    confidence_threshold: 0.75
```

**파일**: `execution/engine.py`, `strategies/ensemble.py`, `config.yml`

### 2. 거래 빈도 제한 (핵심)

**문제**: 시간당 310건 → 수수료 24.8%  
**해결**: 포트폴리오 레벨 시간당 15건 제한

```yaml
ensemble:
  max_total_positions: 10       # 20 → 10
  max_trades_per_hour: 15
```

**파일**: `execution/engine.py`, `config.yml`

### 3. TP/SL 최적화

**문제**: TP1(1.5R) 너무 가깝고, SL(8%) 너무 넓음  
**해결**: TP1 2.0R, 동적 SL (ATR 기반 2~6%)

**파일**: `common/calculations.py`, `execution/position_tracker.py`

### 4. 슬리피지 (보류)

**이유**: 동적 슬리피지 구현 실패로 중단  
**계획**: PHASE7-2 완료 후 별도 재설계

---

## ✅ 수용 기준

**PHASE7-3 진입 전 필수**:
- Paper 24h 평균 승률 ≥ 45%
- 시간당 거래 ≤ 15건
- >8% 손실 0건 (24h 기준)
- TP1 손실 0건
- 중복 진입 0건, 양방향 동시 0건

---

## 📋 체크리스트

**구현 전**:
- [ ] PHASE7_ALGORITHM_BEST.md 벤치마킹 재검토
- [ ] 전략별 설정 설계 문서화 (config.yml 스키마)
- [ ] .windsurfrules 준수: 단계별 3파일 이하

**구현 중**:
- [ ] 전략별 쿨다운/제한 (engine.py)
- [ ] 포트폴리오 레벨 제한 (engine.py)
- [ ] TP/SL 최적화 (calculations.py, position_tracker.py)
- [ ] 회귀 테스트: 중복 방지, ONE-WAY, OHLC SL

**검증**:
- [ ] Paper 24h: 승률/거래빈도/손실상한
- [ ] DB/Redis 네임스페이스 {ns}:{env}:{run_id}:* 격리 검증
- [ ] config.yml diff 기록 (변경 이유/근거)

---

## 🔗 참조 문서

- **PHASE7_ALGORITHM_BEST.md** - 앙상블 TO-BE 전체 설계 (MASTER)
- **SLIPPAGE_PERFORMANCE_COMPARISON.md** - 슬리피지 실패 회귀 분석
- **GUARD_EXECUTION_ORDER_ANALYSIS.md** - 실행 순서 최적화
- **SYSTEM_OPERATIONS_ANALYSIS.md** - 운영 안정성 정책
- **SMOKE_TEST_MONITOR.md** - 실시간 관측/SQL

---

## 📝 업데이트 로그

- **2025-11-13**: 문서 대폭 간소화 (1613→350라인). MASTER 템플릿 적용. 슬리피지 내용 제거.
- **2025-11-12**: 슬리피지 실패 분석 추가
- **2025-11-11**: PHASE7-2 Phase 1 완료 (TP/SL, 중복 방지)
- **2025-11-10**: PHASE7-2 계획 수립

---

## 🚀 구현 계획 (4단계)

### Phase 1: 전략별 독립 설정 (1일)

**작업**:
- config.yml에 strategies.* 추가 (6개 전략)
- engine.py에서 진입 전 전략별 체크
- Redis 전략별 쿨다운 관리

**예상 효과**: 거래 빈도 50% 감소

### Phase 2: 포트폴리오 제한 (0.5일)

**작업**:
- ensemble.max_trades_per_hour 추가
- engine.py에서 시간당 거래 카운트

**예상 효과**: 거래 빈도 추가 40% 감소 (총 310→15건)

### Phase 3: TP/SL 최적화 (0.5일)

**작업**:
- calculations.py ATR 기반 동적 SL
- position_tracker.py Trailing Stop 조기 활성화

**예상 효과**: >8% 손실 0건

### Phase 4: 검증 및 튜닝 (1일)

**작업**:
- Paper 24h 테스트
- 수용 기준 검증
- 파라미터 미세 조정

---

## 🛠️ 구현 상세 (간략)

### config.yml 스키마

```yaml
strategies:
  scalping:
    cooldown_minutes: 5
    max_positions: 5
    max_trades_per_hour: 20
    confidence_threshold: 0.65
  daytrade:
    cooldown_minutes: 15
    max_positions: 3
    max_trades_per_hour: 12
    confidence_threshold: 0.70
  swing:
    cooldown_minutes: 60
    max_positions: 2
    max_trades_per_hour: 5
    confidence_threshold: 0.75
  # breakout, trend, reversion 동일 패턴

ensemble:
  max_total_positions: 10
  max_trades_per_hour: 15
  max_positions_per_symbol: 1

exits:
  tp1_r: 2.0              # 1.5R → 2.0R
  tp2_r: null             # 삭제
  tp1_size_pct: 60        # 60% 청산
  sl_max_pct: 6.0         # 8% → 6%
  sl_min_pct: 2.0
  sl_atr_multiplier: 1.5
```

### 주요 코드 변경 (개념)

**engine.py::check_strategy_limits()**:
```python
def check_strategy_limits(strategy_id, symbol, config):
    # 전략별 쿨다운 체크
    cooldown_min = config['strategies'][strategy_id]['cooldown_minutes']
    # 전략별 포지션 수 체크
    max_pos = config['strategies'][strategy_id]['max_positions']
    # 전략별 시간당 거래 체크
    max_trades = config['strategies'][strategy_id]['max_trades_per_hour']
```

**engine.py::check_portfolio_limits()**:
```python
def check_portfolio_limits(config):
    # 전체 시간당 거래 체크
    if hour_trades >= config['ensemble']['max_trades_per_hour']:
        return False
```

---

**최종 업데이트**: 2025-11-13  
**다음 단계**: 구현 착수 (Claude 담당)
