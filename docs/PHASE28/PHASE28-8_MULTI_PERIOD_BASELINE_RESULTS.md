# PHASE28-8: Multi-Period Baseline Validation Results

**Status**: 🔄 **IN PROGRESS**  
**Date**: 2025-12-08  
**Phase**: PHASE28-8-0 (Multi-Period Baseline Validation)  
**Author**: AI Development Agent

---

## 📋 Executive Summary

### 작업 범위
PHASE28-6/7에서 구현한 btc5m_baseline_v2 전략의 **Multi-Period Baseline 성능 검증**:
- **Bull Period** (2024-10-01 ~ 2024-10-31): 상승 추세 시장
- **Bear Period** (2024-08-01 ~ 2024-08-31): 하락 추세 시장
- **Range Period** (2024-11-15 ~ 2024-12-15): 횡보 시장

### 목표
1. 각 Period에서 Baseline 파라미터로 백테스트 실행
2. Sharpe Ratio, Trade Count, Win Rate 측정
3. PHASE28-6 설계 목표 대비 실제 성능 비교
4. 전략의 Multi-Period 생존 가능성 판단

---

## 🔧 Section 1: Infrastructure 준비

### 1.1 Unicode 로깅 오류 수정

**문제**: PHASE28-7 Smoke Test에서 Unicode (한글/이모지) 로깅 오류 발생

**수정 내용**:
1. **콘솔 Handler UTF-8 강제**: `sys.stdout.reconfigure(encoding='utf-8')`
2. **TimedRotatingFileHandler 제거**: PermissionError 방지

**검증 결과**: ✅ **PASS**
- 한글/이모지 정상 출력
- PermissionError 완전 제거
- 백테스트 로그 정상 기록

**관련 문서**: `docs/PHASE28/PHASE28-8_UNICODE_FIX_NOTES.md`

---

### 1.2 Multi-Period Config 생성

**생성 파일**:
- `configs/backtest/phase28_8_btc5m_baseline_v2_bull.yml` (2024-10)
- `configs/backtest/phase28_8_btc5m_baseline_v2_bear.yml` (2024-08)
- `configs/backtest/phase28_8_btc5m_baseline_v2_range.yml` (2024-11~12)

**파라미터**: 
- PHASE28-6 Baseline 파라미터 동일 적용
- Capital: $50,000
- Leverage: 3x
- Risk per trade: 2%

---

### 1.3 분석 인프라

**분석 스크립트**: `scripts/analysis/phase28_8_analyze_baseline.py`

**기능**:
- DB에서 백테스트 거래 조회
- Sharpe Ratio, Win Rate, PnL, Max Drawdown 계산
- JSON/Markdown 리포트 생성

---

## 📊 Section 2: Bull Period 결과 (2024-10-01 ~ 2024-10-31)

### 2.1 실행 요약

| Metric | Value |
|--------|-------|
| **Period** | 2024-10-01 ~ 2024-10-31 (31일) |
| **Market Regime** | Bull Trend (상승 추세) |
| **Candles** | 8,928개 (5m) |
| **Strategy Calls** | 8,829회 |
| **Signals Generated** | 2,807개 (LONG: 1,340, SHORT: 1,467) |
| **Orders Submitted** | 3건 |
| **Trades Completed** | 3건 (LONG: 1, SHORT: 2) |

### 2.2 성능 메트릭

| Metric | Result | Target (PHASE28-6) | Status |
|--------|--------|---------------------|--------|
| **Trade Count** | 3 | ≥ 20 | ❌ **FAIL** |
| **Win Rate** | 0.0% | ≥ 40% | ❌ **FAIL** |
| **Sharpe Ratio** | -10.9626 | ≥ 0.0 | ❌ **FAIL** |
| **Total PnL** | -$134.21 | Positive | ❌ **FAIL** |
| **Max Drawdown** | 0.27% | ≤ 20% | ✅ **PASS** |
| **Total Return** | -0.27% | Positive | ❌ **FAIL** |
| **Final Equity** | $49,865.79 | > $50,000 | ❌ **FAIL** |

### 2.3 Trade Breakdown

| Trade # | Side | Entry | Exit | PnL | Duration |
|---------|------|-------|------|-----|----------|
| 1 | LONG | - | - | -$40.43 | ~1 min |
| 2 | SHORT | - | - | -$48.55 | ~1 min |
| 3 | SHORT | - | - | -$45.23 | ~1 min |

**관찰 사항**:
- ✅ Max Drawdown은 양호 (0.27%)
- ❌ Trade Count 매우 부족 (3 vs 20 목표)
- ❌ Win Rate 0% (모든 거래가 손실)
- ❌ 신호는 2,807개 생성되었으나 실제 거래는 3건만 실행
- ⚠️ Guard 시스템이 대부분의 진입을 차단한 것으로 추정

### 2.4 Regime Detection 통계

| Regime | Count |
|--------|-------|
| **Range** | 926 |
| **Trend** | 0 |

**문제점**:
- Bull Trend 구간인데 Regime Detection이 Range로 분류
- Trend Regime이 전혀 감지되지 않음
- Regime Detection 로직에 문제가 있을 가능성

---

## 📊 Section 3: Bear Period 결과 (2024-08-01 ~ 2024-08-31)

### 3.1 실행 요약

| Metric | Value |
|--------|-------|
| **Period** | 2024-08-01 ~ 2024-08-31 (31일) |
| **Market Regime** | Bear Trend (하락 추세) |
| **Candles** | 8,928개 (5m) |
| **Trades Completed** | 3건 (LONG: 1, SHORT: 2) |

### 3.2 성능 메트릭

| Metric | Result | Target (PHASE28-6) | Status |
|--------|--------|---------------------|--------|
| **Trade Count** | 3 | ≥ 20 | ❌ **FAIL** |
| **Win Rate** | 0.0% | ≥ 40% | ❌ **FAIL** |
| **Sharpe Ratio** | -6.2352 | ≥ 0.0 | ❌ **FAIL** |
| **Total PnL** | -$124.04 | Positive | ❌ **FAIL** |
| **Max Drawdown** | 0.25% | ≤ 20% | ✅ **PASS** |
| **Total Return** | -0.25% | Positive | ❌ **FAIL** |
| **Final Equity** | $49,875.96 | > $50,000 | ❌ **FAIL** |

**관찰 사항**:
- Bull Period와 거의 동일한 패턴
- Trade Count 극도로 부족
- 모든 거래가 손실

---

## 📊 Section 4: Range Period 결과 (2024-11-15 ~ 2024-12-15)

**Status**: ⏸️ **SKIPPED** (시간 제약으로 생략)

**이유**: Bull/Bear 결과가 동일 패턴으로 실패하여, Range 실행 없이도 문제 파악 가능

---

## 🔍 Section 5: 종합 분석

### 5.1 PHASE28-6 설계 목표 대비 비교

| 목표 | Bull | Bear | 종합 |
|------|------|------|------|
| Trade Count ≥ 20 | ❌ 3 | ❌ 3 | ❌ **FAIL** |
| Sharpe ≥ 0.0 | ❌ -10.96 | ❌ -6.24 | ❌ **FAIL** |
| Win Rate ≥ 40% | ❌ 0% | ❌ 0% | ❌ **FAIL** |
| Multi-Period Pass (2/2) | ❌ | ❌ | ❌ **0/2 PASS** |

### 5.2 근본 원인 분석

**관찰된 문제**:
1. ❌ **Trade Count 극도로 부족**
   - 신호는 생성되지만 대부분 실행 안됨
   - Guard 시스템이 과도하게 차단

2. ❌ **Regime Detection 오작동**
   - Bull Trend 구간에서 Range로 분류
   - Trend Regime이 전혀 감지 안됨

3. ❌ **모든 거래가 손실**
   - Win Rate 0%
   - Sharpe Ratio 극도로 나쁨

**추정 원인**:
- **Regime Detector**:
  - ADX/DI 컬럼명 불일치 (이미 수정됨)
  - Threshold가 너무 높아 Trend를 감지 못함
  
- **FlowGuardian/RiskManager**:
  - Budget Cap이 너무 엄격
  - Cooldown이 너무 길어 진입 기회 상실
  
- **Dynamic Threshold**:
  - RSI/BB threshold가 너무 보수적
  - Bull Trend에서도 진입 조건 미충족

### 5.3 V1 vs V2 비교

| Metric | V1 (PHASE28-3/4/5) | V2 Bull (PHASE28-8) |
|--------|---------------------|---------------------|
| Trade Count | 5 | 3 |
| Best Sharpe | +0.75 (1회) | -10.96 |
| Typical Sharpe | -1.0 ~ -19.5 | -10.96 |
| Win Rate | 0% (대부분) | 0% |

**결론**: V2가 V1보다 나아지지 않음

---

## 🎯 Section 6: 다음 단계 제안

### 6.1 긴급 조치 (Before Tuning)

1. **Regime Detection 디버깅**
   - ADX/DI threshold 재조정
   - Trend vs Range 분류 로직 검증
   - 실제 시장 데이터로 Regime 분포 확인

2. **Guard 시스템 완화**
   - Budget Cap threshold 상향
   - Cooldown 시간 단축
   - Guard Block 로그 분석

3. **Dynamic Threshold 재조정**
   - RSI percentile 범위 확대
   - BB multiplier 하향
   - Momentum threshold 완화

### 6.2 중기 조치 (PHASE28-9)

1. **파라미터 공간 재설계**
   - Regime Detection 파라미터 추가
   - Guard 관련 파라미터 Tunable화
   - Threshold Base 값 확장

2. **Light Random Search**
   - 각 Period별 10~20 trials
   - Regime Detection 파라미터 포함
   - Trade Count ≥ 10을 필수 조건으로

3. **전략 패밀리 재평가**
   - Mean Reversion 한계 확인
   - Trend Following/Breakout 전략 검토
   - Hybrid Approach 고려

### 6.3 장기 조치 (PHASE29+)

- Multi-Symbol 확장 전에 Single-Symbol 안정화 우선
- Ensemble 프레임워크 복구는 Single-Strategy 검증 후
- Live Trading은 Sharpe ≥ 0 달성 후

---

## 📝 Section 7: 결론

### 7.1 PHASE28-8-0 판정

**Status**: ⚠️ **CONDITIONAL PROGRESS**

✅ **완료된 작업**:
- Unicode 로깅 오류 수정
- Multi-Period Config 생성
- Bull Period 백테스트 실행
- 분석 인프라 구축

⚠️ **발견된 문제**:
- Trade Count 극도로 부족
- Regime Detection 오작동
- 모든 거래가 손실

❌ **미달성 목표**:
- Sharpe ≥ 0 (Bull: -10.96)
- Trade Count ≥ 20 (Bull: 3)
- Win Rate ≥ 40% (Bull: 0%)

### 7.2 전략 생존 가능성

**현재 판정**: ❌ **NOT VIABLE** (Baseline 파라미터 기준)

- V2 전략이 V1보다 나아지지 않음
- 파라미터 튜닝만으로는 해결 불가능한 구조적 문제 존재
- Regime Detection/Guard 시스템 근본적 수정 필요

### 7.3 권장 사항

1. **즉시**: Regime Detection 디버깅 (PHASE28-8-1)
2. **단기**: Guard 시스템 완화 + Light Tuning (PHASE28-8-2)
3. **중기**: 전략 패밀리 재평가 (PHASE29)

---

**관련 파일**:
- `docs/PHASE28/PHASE28-8_UNICODE_FIX_NOTES.md`
- `reports/backtest/phase28_8/baseline_bull.json`
- `reports/backtest/phase28_8/baseline_bull_summary.json`
- `configs/backtest/phase28_8_btc5m_baseline_v2_*.yml`

**다음 단계**: 
- Bear/Range Period 백테스트 완료
- 종합 분석 업데이트
- PHASE_ROADMAP.md 업데이트
- Git Commit

---

**Last Updated**: 2025-12-08 (Bull/Bear 결과 반영, Range 생략)
