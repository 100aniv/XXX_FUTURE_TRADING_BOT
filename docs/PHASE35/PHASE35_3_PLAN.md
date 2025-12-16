# PHASE35-3 계획서 (Production-Ready Backtest)

**작성일**: 2024-12-16  
**전제조건**: PHASE35-2 ITER10 완료 (AC0+AC1 PASS, AC2 critical finding)  
**목표**: Production-ready 백테스트 인프라 + max_trades_per_day 구현

---

## Executive Summary

PHASE35-3는 **"Production-ready 백테스트 시스템 완성"**을 목표로 합니다.

### 핵심 목표
1. **Safety Critical**: `max_trades_per_day` RiskGuard 구현 (ITER10 발견사항 해결)
2. **1M Baseline**: 2024년 1개월 백테스트로 성능 기준선 확립
3. **KPI SSOT**: 10종 KPI 단일 출처 계산 + 일관성 검증
4. **운영 기준**: 드로우다운/손실 한도/킬스위치 조건 명시

### 전제조건 (PHASE35-2 완료 상태)
- ✅ 1D 백테스트 속도: 5초 (목표 < 3분 달성)
- ✅ 날짜 필터 정규화: backtest 섹션 동기화
- ✅ KPI SSOT 연결: metrics_kpi.py 사용
- ✅ repro.json SSOT: Git commit 재현성 메타데이터
- ⚠️  max_trades_per_day: **미구현 발견** (Critical)

---

## PHASE35-3 구조

### ITER11: max_trades_per_day 구현 (Safety Critical)
**우선순위**: P0 (Production Blocker)  
**목표**: 일일 거래 상한 차단 기능 구현 + 검증  
**Exit Criteria**:
- RiskManager에 daily trade counting 로직 추가
- check_order() 함수에 상한 검증
- 단위 테스트 5개 이상 (cap enforcement, reset, telemetry 등)
- 7D 백테스트에서 실제 차단 확인

### ITER12: 1M Baseline 실행 + OOS Validation
**우선순위**: P1  
**목표**: Production 성능 기준선 확립  
**Exit Criteria**:
- 2024년 1개월 (예: 2024-11-01 ~ 2024-11-30) 백테스트 완료
- KPI 10종 산출 (Sharpe, Sortino, Calmar, Win Rate 등)
- Walk-forward validation (IS: 3주, OOS: 1주)
- 오버피팅 방지 검증

### ITER13: 운영 기준 확립 + 킬스위치
**우선순위**: P1  
**목표**: Live 운영 시 리스크 관리 기준 명시  
**Exit Criteria**:
- 드로우다운 한도 (soft/hard)
- 일일/주간/월간 손실 한도
- 킬스위치 조건 (자동 정지)
- 알림 임계값 정의

---

## ITER11 상세 계획: max_trades_per_day 구현

### 배경 (ITER10 발견사항)
**문제**:
- `configs/phase35/phase35_2_iter3_ssot.yaml`에 `risk.max_trades_per_day: 10` 존재
- `execution/risk_manager.py` 전체 검색 결과: **해당 로직 없음**
- `check_order()` 함수에 daily loss/consecutive loss만 존재

**영향**:
- Backtest: 문제 없음 (시뮬레이션)
- Paper/Live: **폭주(runaway) 방지 불가** → Production Blocker

### 구현 설계

#### 1) RiskManager 필드 추가

```python
class RiskManager:
    def __init__(self, config, mode='backtest', portfolio=None, activity_tracker=None):
        # 기존 초기화...
        
        # PHASE35-3 ITER11: Daily trade counting
        self.max_trades_per_day = config.get('risk', {}).get('max_trades_per_day')
        self._daily_trades: Dict[str, Set[str]] = defaultdict(set)  # {date: {trade_ids}}
        self._daily_trade_blocks = 0  # 차단 카운터 (telemetry)
        
        if self.max_trades_per_day:
            logger.info(f"✅ Daily Trade Cap: {self.max_trades_per_day} trades/day")
        else:
            logger.info("⚠️  Daily Trade Cap: OFF (unlimited trades)")
```

#### 2) check_order() 함수에 검증 추가

```python
def check_order(self, signal: Dict, qty: float, position_value: float = None) -> Tuple[bool, str]:
    """
    주문 실행 전 리스크 체크
    """
    symbol = signal.get('symbol', 'UNKNOWN')
    
    # 기존 체크들 (0-2)...
    
    # PHASE35-3 ITER11: Daily trade cap
    if self.max_trades_per_day:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 날짜 변경 시 이전 날짜 데이터 정리 (메모리 절약)
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        for old_date in list(self._daily_trades.keys()):
            if old_date < cutoff_date:
                del self._daily_trades[old_date]
        
        # 오늘 거래 수 확인
        today_count = len(self._daily_trades[today])
        
        if today_count >= self.max_trades_per_day:
            self._daily_trade_blocks += 1
            reason = f"일일 거래 상한 도달 ({today_count}/{self.max_trades_per_day})"
            self._notify_guard(reason)
            
            # Guard Telemetry
            if self.activity_tracker:
                self.activity_tracker.record_guard_block(symbol, "GUARD_DAILY_TRADE_CAP")
            
            return False, reason
    
    # 나머지 기존 체크들...
    
    return True, "OK"
```

#### 3) 거래 기록 함수 추가

```python
def record_trade(self, trade_id: str, date: str = None):
    """
    거래 기록 (엔진에서 체결 후 호출)
    
    Args:
        trade_id: 고유 거래 ID
        date: 거래 날짜 (YYYY-MM-DD), None이면 오늘
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    self._daily_trades[date].add(trade_id)
    
    if self.max_trades_per_day:
        today_count = len(self._daily_trades[date])
        logger.debug(f"[Daily Trade] {date}: {today_count}/{self.max_trades_per_day}")
```

#### 4) 메트릭 조회 함수 추가

```python
def get_daily_trade_stats(self) -> Dict[str, Any]:
    """
    일일 거래 통계 조회 (summary.json 연동)
    
    Returns:
        {
            'per_day_trades': {date: count},
            'total_blocks': int,
            'max_trades_per_day': int
        }
    """
    per_day = {date: len(trades) for date, trades in self._daily_trades.items()}
    
    return {
        'per_day_trades': per_day,
        'total_blocks': self._daily_trade_blocks,
        'max_trades_per_day': self.max_trades_per_day
    }
```

### 통합 지점

#### Engine 통합 (`execution/engine.py`)

```python
# 주문 생성 전 (기존 check_order 호출 위치)
approved, reason = risk_manager.check_order(signal, qty, position_value)
if not approved:
    logger.warning(f"❌ Risk check failed: {reason}")
    continue

# 주문 체결 후 (trade 생성 후)
trade_id = f"{symbol}_{timestamp}_{side}"
risk_manager.record_trade(trade_id)
```

#### Summary 통합 (`scripts/phase35/run_iter5_isolated_v2.py`)

```python
# ITER11: RiskGuard stats 추가
if hasattr(rm, 'get_daily_trade_stats'):
    riskguard_stats = rm.get_daily_trade_stats()
    summary['riskguard'] = riskguard_stats
    
    logger.info(f"📊 RiskGuard Stats:")
    logger.info(f"   Daily trades: {riskguard_stats['per_day_trades']}")
    logger.info(f"   Blocks: {riskguard_stats['total_blocks']}")
```

### 테스트 계획

#### 단위 테스트 (`tests/test_phase35_iter11_daily_cap.py`)

1. **test_daily_cap_enforcement**: 10개 거래 후 11번째 차단
2. **test_daily_cap_reset**: 날짜 변경 시 카운터 리셋
3. **test_daily_cap_telemetry**: 차단 카운터 증가 확인
4. **test_daily_cap_off**: max_trades_per_day=None 시 무제한
5. **test_daily_cap_memory_cleanup**: 7일 이상 오래된 데이터 삭제

#### 통합 테스트 (7D 백테스트)

```bash
# 보수적 cap (5 trades/day)
python scripts/phase35/run_iter5_isolated_v2.py 1101 --range 7d --daily-cap 5

# 검증:
# - summary.json의 riskguard.total_blocks > 0
# - 각 날짜별 trades <= 5
# - 7일 총 trades <= 35
```

### Exit Criteria (ITER11)

**EC1**: 단위 테스트 5/5 PASS  
**EC2**: 7D 백테스트에서 실제 차단 확인 (blocks > 0)  
**EC3**: summary.json에 riskguard stats 포함  
**EC4**: 문서화 + Git 커밋/푸시

---

## ITER12 상세 계획: 1M Baseline + OOS Validation

### 목표
**Production 성능 기준선 확립**:
- 2024년 1개월 (30일) 백테스트
- KPI 10종 산출
- Walk-forward validation (오버피팅 방지)

### 기간 선택 방식

#### Option A: 최근 1개월 (권장)
- **기간**: 2024-11-01 ~ 2024-11-30 (30일)
- **장점**: 최신 시장 환경 반영
- **단점**: 특정 시장 국면 편향 가능성

#### Option B: 대표성 있는 1개월
- **기간**: 2024년 중 변동성 중간 수준 월
- **방법**: 월별 ATR/변동률 계산 후 중간값 선택
- **장점**: 극단 구간 회피
- **단점**: 최신성 부족

#### Option C: 복합 (권장)
- **IS (In-Sample)**: 2024-11-01 ~ 2024-11-21 (3주)
- **OOS (Out-of-Sample)**: 2024-11-22 ~ 2024-11-30 (1주)
- **장점**: 오버피팅 검증 가능
- **단점**: OOS 기간 짧음

**결정**: **Option C (IS/OOS 분리)**

### KPI 10종 SSOT 정의

#### 1) 수익률 KPI (4종)
- **Total Return (%)**: `(final_equity - initial_equity) / initial_equity * 100`
- **CAGR (%)**: `((final_equity / initial_equity) ^ (365 / days)) - 1) * 100`
- **Max Drawdown (%)**: `max((peak - valley) / peak)` (최대 낙폭)
- **Calmar Ratio**: `CAGR / abs(Max Drawdown)` (위험 대비 수익)

#### 2) 위험 KPI (3종)
- **Sharpe Ratio**: `(avg_return - risk_free_rate) / std_return`
- **Sortino Ratio**: `(avg_return - risk_free_rate) / downside_std`
- **Max Consecutive Losses**: 최대 연속 손실 횟수

#### 3) 거래 KPI (3종)
- **Win Rate (%)**: `wins / total_trades * 100`
- **Profit Factor**: `gross_profit / abs(gross_loss)`
- **Avg Trade Duration (hours)**: `sum(durations) / total_trades`

**구현 위치**: `common/metrics_kpi.py`에 `compute_comprehensive_kpis()` 함수 추가

### Walk-Forward Validation

#### IS (In-Sample) Phase
- **기간**: 2024-11-01 ~ 2024-11-21 (21일)
- **목적**: 파라미터 검증
- **실행**: `python scripts/phase35/run_iter5_isolated_v2.py 1201 --start-date 2024-11-01 --end-date 2024-11-22`

#### OOS (Out-of-Sample) Phase
- **기간**: 2024-11-22 ~ 2024-11-30 (9일)
- **목적**: 오버피팅 검증
- **실행**: `python scripts/phase35/run_iter5_isolated_v2.py 1202 --start-date 2024-11-22 --end-date 2024-12-01`

#### 검증 기준
- **IS/OOS Sharpe 차이**: < 30% (예: IS=1.5, OOS=1.05 → OK)
- **IS/OOS Win Rate 차이**: < 10% (예: IS=55%, OOS=50% → OK)
- **OOS Max Drawdown**: < IS의 150%

### 실행 계획

```bash
# ITER12 Step 1: IS 백테스트
python scripts/phase35/run_iter5_isolated_v2.py 1201 \
  --start-date 2024-11-01 \
  --end-date 2024-11-22 \
  --daily-cap 10

# ITER12 Step 2: OOS 백테스트
python scripts/phase35/run_iter5_isolated_v2.py 1202 \
  --start-date 2024-11-22 \
  --end-date 2024-12-01 \
  --daily-cap 10

# ITER12 Step 3: KPI 비교 리포트 생성
python scripts/phase35/compare_is_oos.py \
  artifacts/phase35/iter5/phase35_2_iter9_run1201_*/summary.json \
  artifacts/phase35/iter5/phase35_2_iter9_run1202_*/summary.json
```

### Exit Criteria (ITER12)

**EC1**: IS 백테스트 완료 (21일, summary.json 생성)  
**EC2**: OOS 백테스트 완료 (9일, summary.json 생성)  
**EC3**: KPI 10종 산출 (IS/OOS 모두)  
**EC4**: IS/OOS 비교 리포트 (`PHASE35_3_ITER12_IS_OOS_REPORT.md`)  
**EC5**: 오버피팅 검증 (Sharpe/Win Rate 차이 < 임계값)

---

## ITER13 상세 계획: 운영 기준 + 킬스위치

### 목표
**Live 운영 시 리스크 관리 기준 명시**

### 드로우다운 한도

#### Soft Limit (경고)
- **일일**: -5% (equity 기준)
- **주간**: -10%
- **월간**: -15%
- **조치**: 신규 진입 차단 + 텔레그램 알림

#### Hard Limit (강제 정지)
- **일일**: -10%
- **주간**: -20%
- **월간**: -30%
- **조치**: 모든 포지션 정리 + 봇 자동 정지

### 손실 한도

#### Daily Loss Limit
- **Soft**: $500 (equity의 5%)
- **Hard**: $1,000 (equity의 10%)
- **구현**: RiskManager의 기존 daily_loss guard 사용

#### Consecutive Losses
- **한도**: 5회 연속 손실
- **쿨다운**: 60분 (4캔들, 15분봉 기준)
- **구현**: RiskManager의 기존 consecutive loss guard 사용

### 킬스위치 조건

#### 자동 정지 트리거
1. **Daily Loss Hard Limit** 도달
2. **Max Drawdown Hard Limit** 도달
3. **Equity < 초기 자본의 70%**
4. **FlashGuard 3회 연속 발동** (급등락 시장)
5. **연속 슬리피지 초과 5회** (유동성 문제)

#### 킬스위치 로직 (Pseudo-code)

```python
def check_killswitch(portfolio, risk_manager, config):
    """
    킬스위치 조건 검사
    
    Returns:
        (should_stop: bool, reason: str)
    """
    initial_capital = config['initial_capital']
    current_equity = portfolio.equity
    
    # 1. Daily Loss Hard Limit
    if risk_manager.daily_loss_mode == 'hard':
        daily_loss = portfolio.get_daily_pnl()
        if abs(daily_loss) >= risk_manager.daily_loss_hard_limit:
            return True, f"Daily loss hard limit: ${abs(daily_loss):.2f}"
    
    # 2. Max Drawdown Hard Limit
    max_dd_pct = risk_manager.max_drawdown_pct
    current_dd = (portfolio.peak_equity - current_equity) / portfolio.peak_equity
    if current_dd >= max_dd_pct:
        return True, f"Max drawdown limit: {current_dd*100:.1f}%"
    
    # 3. Equity < 70%
    if current_equity < initial_capital * 0.7:
        return True, f"Equity depletion: ${current_equity:.2f} < 70% of ${initial_capital}"
    
    # 4. FlashGuard 연속 발동
    if hasattr(risk_manager, '_flash_consecutive_blocks'):
        if risk_manager._flash_consecutive_blocks >= 3:
            return True, "FlashGuard 3회 연속 발동 (급등락)"
    
    # 5. 연속 슬리피지 초과
    if hasattr(risk_manager, '_slippage_consecutive_blocks'):
        if risk_manager._slippage_consecutive_blocks >= 5:
            return True, "연속 슬리피지 초과 5회 (유동성 문제)"
    
    return False, ""
```

### 알림 임계값

#### 텔레그램 알림 우선순위

**P0 (즉시 알림, 무제한)**:
- 킬스위치 발동
- Daily Loss Hard Limit
- Max Drawdown Hard Limit

**P1 (즉시 알림, throttle=5분)**:
- Daily Loss Soft Limit
- Max Drawdown Soft Limit
- Consecutive Losses 도달

**P2 (배치 알림, throttle=1시간)**:
- Daily Trade Cap 차단
- FlashGuard 발동
- RiskGuard 일반 차단

### 구현 위치

#### 1) 킬스위치 함수 추가
- **파일**: `execution/risk_manager.py`
- **함수**: `check_killswitch() -> Tuple[bool, str]`

#### 2) Engine 통합
- **파일**: `execution/engine.py`
- **위치**: 메인 루프 시작 부분
- **동작**: 킬스위치 발동 시 `break` + 로그 + 알림

#### 3) Config 섹션
- **파일**: `configs/phase35/phase35_2_iter3_ssot.yaml`
- **섹션**: `killswitch` 추가

```yaml
killswitch:
  enabled: true
  daily_loss_hard_pct: 10.0
  max_drawdown_hard_pct: 20.0
  equity_depletion_pct: 70.0
  flash_consecutive_limit: 3
  slippage_consecutive_limit: 5
```

### Exit Criteria (ITER13)

**EC1**: killswitch 함수 구현 + 단위 테스트  
**EC2**: Config에 killswitch 섹션 추가  
**EC3**: 운영 기준 문서화 (`PHASE35_3_OPERATIONAL_GUIDELINES.md`)  
**EC4**: 알림 우선순위 구현 + 테스트

---

## 전체 타임라인

### ITER11: max_trades_per_day 구현
- **소요**: 2-3시간
- **병목**: 단위 테스트 작성

### ITER12: 1M Baseline + OOS
- **소요**: 4-6시간
- **병목**: 백테스트 실행 시간 (IS 21일 + OOS 9일)

### ITER13: 운영 기준 + 킬스위치
- **소요**: 2-3시간
- **병목**: Config 설계 + 문서화

**총 예상 시간**: 8-12시간

---

## 다음 프롬프트 (ITER11 시작)

```
PHASE35-3 ITER11: max_trades_per_day RiskGuard 구현 (한 턴 끝장)

## 원칙
- 설계 → 구현 → 단위 테스트 → 통합 테스트 → 문서화 → Git
- PASS 기준: 단위 테스트 5/5 + 7D 백테스트 실제 차단 (blocks > 0)
- 실행/검증은 AI가 끝까지 수행

## STEP 0) 루트 스캔
- execution/risk_manager.py 구조 파악
- check_order() 함수 위치 확인
- 기존 Guard 패턴 분석

## STEP 1) RiskManager 구현
- _daily_trades 필드 추가
- check_order()에 daily cap 검증
- record_trade() 함수
- get_daily_trade_stats() 함수

## STEP 2) Engine 통합
- execution/engine.py에서 record_trade() 호출
- 체결 후 거래 기록

## STEP 3) Summary 통합
- scripts/phase35/run_iter5_isolated_v2.py
- summary.json에 riskguard stats 추가

## STEP 4) 단위 테스트 (5개)
- test_daily_cap_enforcement
- test_daily_cap_reset
- test_daily_cap_telemetry
- test_daily_cap_off
- test_daily_cap_memory_cleanup

## STEP 5) 통합 테스트 (7D)
- --daily-cap 5로 보수적 실행
- summary.json 검증 (blocks > 0)

## STEP 6) 문서화 + Git
- PHASE35_3_ITER11_REPORT.md
- git add/commit/push

AC:
- AC1: 단위 테스트 5/5 PASS
- AC2: 7D 백테스트 blocks > 0
- AC3: summary.json에 riskguard 섹션 존재
```

---

## 결론

**PHASE35-3 구성**:
- ITER11: max_trades_per_day 구현 (Safety Critical) ← **최우선**
- ITER12: 1M Baseline + OOS Validation
- ITER13: 운영 기준 + 킬스위치

**판정**: ✅ **계획 문서 작성 완료** (조건부 자동 진행 준비)

**다음 액션**: ITER11 프롬프트 실행 (max_trades_per_day 구현)

---

**PHASE35-3 PLAN 종료**
