# PHASE26-2: Top10 Multi-Symbol PAPER Load Test - Design Document

**작성일**: 2025-12-03  
**상태**: 🔄 IN PROGRESS  
**Model**: Claude 4.5 Thinking  
**목적**: Universe Provider + Multi-Symbol Engine v1 검증용 Top10 PAPER Load Test Harness

---

## 0. Executive Summary

### 0.1. PHASE26-2 목표

**Primary Goal**: Universe Provider와 Multi-Symbol Engine v1을 실전 검증할 수 있는 Top10 PAPER Load Test harness 구축

**Key Requirements**:
1. ✅ **Universe 기반 Multi-Symbol PAPER 실행**: StaticUniverseProvider 또는 TopNByVolumeUniverseProvider로 Top10 심볼 선정
2. ✅ **PHASE25-0 하네스 재사용**: 기존 Long-run harness의 오케스트레이션 로직 최대한 활용
3. ✅ **최소 2H 실행 준비**: 장시간 실행 가능한 Config/Runner/Report 구조
4. ✅ **100% 하위 호환**: 단일 심볼 모드에 영향 없음

**Out of Scope (PHASE26-3+)**:
- Coroutine 기반 비동기 처리 (Sequential processing only)
- Universe auto-refresh (프로세스 시작 시 1회만)
- Per-symbol config override (모든 심볼에 동일 전략/리스크)

---

## 1. AS-IS 분석

### 1.1. PHASE25-0 Long-run PAPER Harness

**파일**: `scripts/infra/phase25_0_long_run_paper.py`

**주요 기능**:
```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: 환경 정리                                           │
│   ├─ Python 프로세스 kill (자동 검색 & 종료)               │
│   └─ Docker 상태 확인                                       │
├──────────────────────────────────────────────────────────────│
│ STEP 2: Pre-flight Check                                    │
│   ├─ env_config_validator.py                                │
│   └─ phase24_1_infra_diagnostics.py                         │
├──────────────────────────────────────────────────────────────│
│ STEP 3: Clean State                                         │
│   └─ clean_state_complete.py                                │
├──────────────────────────────────────────────────────────────│
│ STEP 4: Long-run 실행 (새 CMD 창)                          │
│   └─ run_v2.py --mode paper --config <CONFIG>              │
├──────────────────────────────────────────────────────────────│
│ STEP 5: 실시간 모니터링 (30초 간격)                         │
│   ├─ logs/application.log tail                             │
│   ├─ ERROR/CRITICAL 패턴 감지 → 즉시 중단                  │
│   └─ Wall-clock duration 추적                              │
├──────────────────────────────────────────────────────────────│
│ STEP 6: Post-run 분석                                       │
│   ├─ DB 쿼리 (trades, time range 기반)                     │
│   ├─ 로그 파싱 (Ensemble aggregate, ERROR count)           │
│   └─ 메트릭 계산 (trade_count, active_positions)           │
├──────────────────────────────────────────────────────────────│
│ STEP 7: 결과 저장                                          │
│   ├─ MD 리포트: PHASE25-0_LONG_RUN_PAPER_REPORT.md         │
│   └─ JSON 요약: phase25_0_long_run_summary.json            │
└──────────────────────────────────────────────────────────────┘
```

**핵심 강점**:
- ✅ 완전 자동화 (Pre-flight → Run → Monitor → Report)
- ✅ 실시간 ERROR 감지 & 중단
- ✅ DB + 로그 기반 메트릭 수집
- ✅ MD + JSON 리포트 자동 생성

**현재 제한**:
- ❌ **단일 심볼만 지원**: config.symbol 하드코딩
- ❌ **Universe 미통합**: universe 설정 무시
- ❌ **Per-symbol 메트릭 없음**: 전체 trade_count만 집계

### 1.2. PHASE26-0/1 상태

**PHASE26-0** (✅ COMPLETE):
- UniverseProvider 추상화 설계
- StaticUniverseProvider 구현
- TopNByVolumeUniverseProvider 구현
- load_universe_config() 구현

**PHASE26-1** (✅ COMPLETE):
- engine.run_v2()에서 Universe Provider 로딩
- engine.run()에 symbols 인자 추가
- Multi-Symbol Sequential Processing 구현
- 100% 하위 호환성 보장 (universe.enabled=false)

**현재 엔진 능력**:
```python
# execution/engine.py::run_v2()
universe_cfg = load_universe_config(config)
if universe_cfg:
    provider = create_universe_provider(universe_cfg)
    universe = asyncio.run(provider.get_universe())
    symbols = [s.symbol for s in universe]
else:
    symbols = [config.get('symbol', 'BTCUSDT')]

# execution/engine.py::run()
def run(..., symbols: list = None):
    if symbols is None:
        symbols = [config.get('symbol', 'BTCUSDT')]
    
    # Main Loop: per-symbol sequential processing
    for candle in feed.stream():
        candle_symbol = candle.get("symbol")
        buffer_key = (candle_symbol, candle_timeframe)
        # ... per-symbol buffer/position/risk 관리
```

---

## 2. TO-BE 설계

### 2.1. Top10 Multi-Symbol PAPER Config

**파일**: `configs/paper/phase26_2_top10_paper_2h.yml`

**새 섹션 추가**:
```yaml
# ========================================
# PHASE26-2: Universe Provider 설정
# ========================================
universe:
  enabled: true  # ⭐ Universe 모드 활성화
  
  provider:
    type: topn_volume  # 'static' | 'topn_volume'
    top_n: 10           # Top10 심볼 선정
    cache_ttl_sec: 3600  # 1시간 캐시 (프로세스 시작 시 1회만)
    # Static 모드 예시:
    # static_symbols: [BTCUSDT, ETHUSDT, BNBUSDT, ...]
  
  filters:
    quote_assets: [USDT]               # USDT 쌍만
    exclude_symbols: [BTCDOWNUSDT, BTCUPUSDT]  # 레버리지 토큰 제외
    min_24h_volume_usd: 10000000       # 최소 24H 거래량 (10M USDT)
    market_types: [PERPETUAL]          # 선물 마켓만 (or [SPOT])
    contract_status: TRADING           # TRADING 상태만

# ========================================
# 기존 설정 (base.yml 상속)
# ========================================
mode: paper
env: paper
run_id: "PHASE26-2_top10_paper_2h"

# ⭐ symbol 키는 fallback용으로 유지 (universe 실패 시)
symbol: BTCUSDT

timeframe: 5m
lookback: 1000

# Paper Trading 설정
paper:
  duration_mode: "wall_clock"  # 실제 시계 기준
  duration_hours: 2.0           # 2H 실행 (Acceptance 최소 기준)
  clean_start: true

# Portfolio 설정 (보수적)
portfolio:
  max_strategy_positions: 5
  max_total_exposure: 0.5  # ⭐ 50% (Multi-Symbol 안전 마진)

# Risk 설정 (보수적)
risk:
  per_trade: 0.002             # 0.2% RPT (Multi-Symbol용 축소)
  max_positions: 10            # Top10 × 1포지션/심볼 가정
  max_exposure_per_symbol: 0.1  # 심볼당 10% 한도
  max_exposure_pct: 0.5        # 전체 50% 한도

# Strategy 설정
strategy:
  selector: scalping  # 단일 전략 (Multi-Symbol 초기 테스트)
  # 향후 Ensemble 테스트 가능

strategies:
  scalping:
    enabled: true
    timeframe: 5m
    risk_per_trade: 0.002
    # ... 기타 설정 base.yml 상속
```

**설계 원칙**:
1. **Config 단순화**: 기존 base.yml 상속 + universe 섹션만 추가
2. **보수적 리스크**: RPT 축소 (0.3%→0.2%), 최대 노출 50%
3. **단일 전략 시작**: scalping 단독 → 이후 Ensemble 확장

### 2.2. Top10 PAPER Runner (PHASE25-0 재사용)

**방안 A: PHASE25-0 harness 확장** ✅ **채택**

```python
# scripts/infra/phase26_2_run_top10_paper.py

"""
PHASE26-2: Top10 Multi-Symbol PAPER Load Test Runner
======================================================
PHASE25-0 Long-run harness를 재사용하되, Multi-Symbol 메트릭 추가

핵심 변경:
1. Config 검증: universe 섹션 확인
2. Post-run 분석: Per-symbol 메트릭 수집
3. 리포트: Multi-Symbol 요약 추가
"""

import sys
from pathlib import Path

# PHASE25-0 harness 임포트
sys.path.insert(0, str(Path(__file__).parent))
from phase25_0_long_run_paper import (
    cleanup_environment,
    run_preflight_checks,
    run_clean_state,
    start_long_run,
    monitor_logs,
    # analyze_results,  # ← 이 부분만 확장
    # save_report,       # ← 이 부분만 확장
)

def validate_universe_config(config_path: str) -> bool:
    """Universe 설정 검증 (PHASE26-2 추가)"""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'universe' not in config:
        print("  [WARN] universe 섹션 없음 → 단일 심볼 모드로 fallback")
        return True  # Warning이지만 실행은 허용
    
    universe_cfg = config['universe']
    if not universe_cfg.get('enabled', False):
        print("  [WARN] universe.enabled=false → 단일 심볼 모드")
        return True
    
    provider_type = universe_cfg.get('provider', {}).get('type')
    if provider_type not in ['static', 'topn_volume']:
        print(f"  [ERROR] 지원하지 않는 provider type: {provider_type}")
        return False
    
    print(f"  [OK] Universe Provider: {provider_type}")
    return True

def analyze_results_multi_symbol(start_time, end_time, config_path) -> dict:
    """Post-run 메트릭 수집 (PHASE26-2: Per-symbol 추가)"""
    from phase25_0_long_run_paper import analyze_results
    
    # 기존 메트릭 수집
    metrics = analyze_results(start_time, end_time)
    
    # ⭐ Per-symbol 메트릭 추가
    try:
        import psycopg2
        import os
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5433')),
            database=os.getenv('DB_NAME', 'trading_db'),
            user=os.getenv('DB_USER', 'trading_user'),
            password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
        )
        
        with conn.cursor() as cur:
            # Symbol별 trade 카운트
            cur.execute(
                """
                SELECT symbol, COUNT(*) as trade_count
                FROM trading.trades
                WHERE ts_open >= %s AND ts_open <= %s
                GROUP BY symbol
                ORDER BY trade_count DESC;
                """,
                (start_time, end_time)
            )
            per_symbol_trades = {row[0]: row[1] for row in cur.fetchall()}
        
        conn.close()
        
        metrics['multi_symbol'] = {
            'symbol_count': len(per_symbol_trades),
            'per_symbol_trades': per_symbol_trades,
            'symbols': list(per_symbol_trades.keys())
        }
        
        print(f"  [OK] Multi-Symbol 메트릭: {len(per_symbol_trades)}개 심볼")
        for symbol, count in list(per_symbol_trades.items())[:5]:  # Top 5만 출력
            print(f"    - {symbol}: {count} trades")
    
    except Exception as e:
        print(f"  [WARN] Multi-Symbol 메트릭 수집 실패: {e}")
        metrics['multi_symbol'] = {'error': str(e)}
    
    return metrics

def save_report_multi_symbol(metrics, config_path, duration_hours, monitor_result):
    """리포트 저장 (PHASE26-2: Multi-Symbol 섹션 추가)"""
    from phase25_0_long_run_paper import save_report, REPORT_MD, SUMMARY_JSON
    from datetime import datetime
    import json
    
    # 기존 리포트 생성
    save_report(metrics, config_path, duration_hours, monitor_result)
    
    # ⭐ Multi-Symbol 섹션 추가 (기존 리포트 append)
    multi_metrics = metrics.get('multi_symbol', {})
    
    if 'error' not in multi_metrics:
        with open(REPORT_MD, 'a', encoding='utf-8') as f:
            f.write("\n---\n\n")
            f.write("## PHASE26-2: Multi-Symbol 메트릭\n\n")
            f.write(f"- **심볼 수**: {multi_metrics.get('symbol_count', 0)}개\n")
            f.write(f"- **심볼 목록**: {', '.join(multi_metrics.get('symbols', []))}\n\n")
            
            f.write("### Per-Symbol Trade 카운트\n\n")
            f.write("| Symbol | Trade Count |\n")
            f.write("|--------|-------------|\n")
            for symbol, count in multi_metrics.get('per_symbol_trades', {}).items():
                f.write(f"| {symbol} | {count} |\n")
            f.write("\n")
        
        print(f"  [OK] Multi-Symbol 리포트 추가 완료")

def main():
    """Main orchestrator (PHASE25-0 플로우 재사용)"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="PHASE26-2: Top10 Multi-Symbol PAPER Load Test")
    parser.add_argument("--config", required=True, help="Config 파일 경로")
    parser.add_argument("--duration-hours", type=float, default=2.0, help="실행 시간 (hours)")
    parser.add_argument("--tag", default=None, help="Run 태그 (선택)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("PHASE26-2: Top10 Multi-Symbol PAPER Load Test")
    print("=" * 80)
    
    # STEP 0: Universe Config 검증 (PHASE26-2 추가)
    print("\n[STEP 0] Universe Config 검증")
    if not validate_universe_config(args.config):
        print("  [FAIL] Config 검증 실패")
        return 1
    
    # STEP 1: 환경 정리
    if not cleanup_environment():
        return 1
    
    # STEP 2: Pre-flight Check
    if not run_preflight_checks(args.config):
        return 1
    
    # STEP 3: Clean State
    if not run_clean_state():
        return 1
    
    # STEP 4: Long-run 실행
    start_time = datetime.now()
    process = start_long_run(args.config, args.duration_hours, args.tag)
    
    # STEP 5: 실시간 모니터링
    monitor_result = monitor_logs(args.duration_hours * 3600, start_time)
    end_time = datetime.now()
    
    # STEP 6: Post-run 분석 (Multi-Symbol 메트릭 포함)
    metrics = analyze_results_multi_symbol(start_time, end_time, args.config)
    
    # STEP 7: 결과 저장 (Multi-Symbol 섹션 추가)
    save_report_multi_symbol(metrics, args.config, args.duration_hours, monitor_result)
    
    # Exit code
    if monitor_result['status'] == 'PASS':
        print("\n✅ PHASE26-2 Top10 PAPER Test: PASS")
        return 0
    else:
        print("\n❌ PHASE26-2 Top10 PAPER Test: FAIL")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

**설계 포인트**:
1. ✅ **최대 재사용**: PHASE25-0의 7단계 플로우 그대로 유지
2. ✅ **최소 추가**: Universe 검증 + Per-symbol 메트릭만 확장
3. ✅ **하위 호환**: Universe 없어도 단일 심볼 모드로 fallback

---

## 3. Acceptance Criteria

### 3.1. 필수 조건 (MUST PASS)

#### 구현 완료
- [ ] `configs/paper/phase26_2_top10_paper_2h.yml` 생성 (Universe 설정 포함)
- [ ] `scripts/infra/phase26_2_run_top10_paper.py` 구현 (PHASE25-0 재사용)
- [ ] `tests/test_phase26_2_top10_paper_load_test.py` 작성 (5+ 테스트)

#### 테스트 통과
- [ ] Universe Config 로딩 테스트 (Static, TopN)
- [ ] Runner wiring 테스트 (engine.run_v2 호출 경로)
- [ ] Per-symbol 메트릭 수집 테스트
- [ ] PHASE25/PHASE26-0/1 회귀 테스트 100% PASS

#### 실행 준비
- [ ] Top10 PAPER 실행 커맨드 예시 문서화
- [ ] 2H+ 장기 PAPER 실행 가능 (Config/Runner/Report 준비 완료)
- [ ] 리포트 템플릿 준비 (MD + JSON)

### 3.2. 실행 시나리오 (장기 PAPER는 별도)

**스모크 테스트** (pytest, 단기):
```bash
pytest tests/test_phase26_2_top10_paper_load_test.py -v
```

**실제 Top10 PAPER** (사용자 수동 실행, 향후):
```bash
python scripts/infra/phase26_2_run_top10_paper.py \
    --config configs/paper/phase26_2_top10_paper_2h.yml \
    --duration-hours 2.0 \
    --tag "PHASE26-2_ACCEPTANCE"
```

**기대 결과** (2H 실행 기준):
- Duration: ≥ 1.96H (98% 이상)
- CRITICAL 오류: 0건
- Active Positions: 0
- Symbol 수: 10개 (TopN 기준)
- Total Trades: ≥ 20건 (심볼당 평균 2건 이상)
- Per-Symbol Trades: 각 심볼별 0~N건 (불균형 허용)

---

## 4. Known Limitations

### 4.1. PHASE26-2 제한사항

1. **Sequential Processing Only**:
   - 심볼별 Round-Robin 순차 처리
   - 심볼 수 증가 시 latency 증가 가능
   - **해결**: PHASE26-3에서 coroutine 도입

2. **No Universe Auto-Refresh**:
   - 프로세스 시작 시 1회만 Universe 조회
   - 실행 중 심볼 리스트 변경 불가
   - **해결**: PHASE28에서 hot-reload 지원

3. **No Per-Symbol Config**:
   - 모든 심볼에 동일한 전략/리스크 적용
   - 심볼별 파라미터 조정 불가
   - **해결**: 향후 per-symbol override 지원

4. **Limited Metrics**:
   - Per-symbol trade count만 수집
   - 심볼별 PnL/WinRate/DD는 미수집
   - **해결**: PHASE27에서 확장

### 4.2. 알려진 이슈

- ❌ **없음**: 현재 발견된 버그 없음

---

## 5. Testing Strategy

### 5.1. Unit Tests

**파일**: `tests/test_phase26_2_top10_paper_load_test.py`

**테스트 케이스**:
1. `test_universe_config_loading_static()`: Static Provider config 로딩
2. `test_universe_config_loading_topn()`: TopN Provider config 로딩
3. `test_runner_wiring_engine_call()`: Runner가 engine.run_v2를 올바른 인자로 호출하는지
4. `test_per_symbol_metrics_collection()`: Dummy DB로 per-symbol 메트릭 계산 검증
5. `test_report_generation_multi_symbol()`: Multi-Symbol 리포트 생성 검증

### 5.2. Integration Tests

**스모크 테스트** (0.1H duration):
```python
def test_integration_smoke_top10():
    """
    통합 스모크 테스트 (Top10 Config + 6분 실행)
    
    목적: CI/단기 검증용
    주의: Acceptance용 아님 (2H 실행 필수)
    """
    # Static Universe로 2개 심볼 테스트
    # duration_hours=0.1 (6분)
    # Runner 전체 플로우 검증
    # Exit code 0 확인
```

### 5.3. Regression Tests

**PHASE25/26-0/1 회귀 테스트**:
```bash
# PHASE25-0
pytest tests/test_phase25_0_long_run_paper.py -v

# PHASE26-0
pytest tests/test_phase26_0_universe_provider.py -v

# PHASE26-1
pytest tests/test_phase26_1_multi_symbol_engine.py -v
```

---

## 6. Implementation Plan

### 6.1. 작업 순서

1. **Config 생성** (10분):
   - `configs/paper/phase26_2_top10_paper_2h.yml`
   - universe 섹션 추가 + 기존 설정 상속

2. **Runner 구현** (30분):
   - `scripts/infra/phase26_2_run_top10_paper.py`
   - PHASE25-0 harness 임포트 & 확장
   - Universe 검증 + Per-symbol 메트릭 추가

3. **테스트 작성** (30분):
   - `tests/test_phase26_2_top10_paper_load_test.py`
   - 5개 테스트 케이스 구현

4. **회귀 테스트** (10분):
   - PHASE25/26-0/1 테스트 실행 및 검증

5. **문서 작성** (20분):
   - 설계 문서 (본 파일)
   - 실행 리포트 템플릿
   - PHASE_ROADMAP 업데이트

6. **Git Commit** (5분):
   - 의미 있는 커밋 메시지
   - 변경 파일 확인

**총 예상 시간**: ~1.5H (장기 PAPER 실행 제외)

---

## 7. Files to Create/Modify

### 7.1. 신규 파일

```
configs/paper/
├── phase26_2_top10_paper_2h.yml  (신규)

scripts/infra/
├── phase26_2_run_top10_paper.py  (신규)

tests/
├── test_phase26_2_top10_paper_load_test.py  (신규)

docs/PHASE26/
├── PHASE26-2_TOP10_PAPER_TEST_DESIGN.md  (본 파일)
└── PHASE26-2_TOP10_PAPER_TEST_REPORT.md  (실행 후 생성)
```

### 7.2. 수정 파일

```
docs/PHASE26/
└── PHASE26_ROADMAP_UPDATE.md  (26-2 상태 업데이트)
```

### 7.3. 미수정 파일 (DO NOT TOUCH)

```
execution/
├── engine.py  (이미 PHASE26-1에서 완료, 추가 수정 불필요)
├── portfolio_manager.py
├── risk_manager.py
└── position_tracker.py

common/
├── universe_provider.py  (PHASE26-0에서 완료)
└── config_loader.py  (PHASE26-0에서 완료)
```

---

## 8. Risk Mitigation

### 8.1. 리스크 요소

1. **Runner 복잡도 증가 우려**:
   - **대응**: PHASE25-0 함수를 임포트해서 재사용, 최소 코드 추가

2. **Multi-Symbol 메트릭 수집 실패**:
   - **대응**: Try-except로 래핑, 실패 시 경고만 표시하고 계속 진행

3. **Universe Provider 실패**:
   - **대응**: Fallback to config.symbol (단일 심볼 모드)

4. **성능 저하 (Top10)**:
   - **대응**: Sequential processing 유지, PHASE26-3에서 최적화

### 8.2. 회귀 방지

- ✅ **PHASE25-0 테스트 재실행**: 단일 심볼 long-run 회귀 없음 확인
- ✅ **PHASE26-0/1 테스트 재실행**: Universe/Multi-Symbol 회귀 없음 확인
- ✅ **DO-NOT-TOUCH 원칙**: 엔진/코어 레이어 미수정

---

**작성자**: Cascade AI (Claude 4.5 Thinking)  
**작성일**: 2025-12-03  
**검토 대상**: PHASE26-1 완료 후 즉시 착수  
**핵심 원칙**: "PHASE25-0 재사용 + 최소 확장" - 새로운 하네스를 만들지 말고 기존 것을 확장
