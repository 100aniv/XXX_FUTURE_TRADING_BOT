# PHASE7-4 마스터 플랜: 전략 개선 (승률 50% 달성)

**작성일**: 2025-11-11  
**최종 업데이트**: 2025-11-13  
**문서 역할**: 전략 품질 개선 계획  
**목적**: 백테스트 파이프라인, 전략별 분석, 동적 가중치로 승률 50% 달성  
**현행 코드(b84c03c)**: 백테스트 미구현, 동적 가중치 약함  
**상태**: ⚠️ PHASE7-2/3 미완으로 7-4 항목 모두 TO-BE (미구현)

## 📌 Executive Summary (TL;DR)

- **역할**: 전략 품질 검증 및 개선. 백테스트 → 전략 필터링 → 가중치 강화.
- **현행**: b84c03c. PHASE7-2/3 미완으로 7-4 보류 중.
- **핵심**: ① 백테스트 파이프라인 ② 전략별 성과 분석 ③ 동적 가중치 강화 ④ 리스크 관리 강화.
- **예상 효과**: 승률 45% → 50%+, 손익비 0.8 → 1.0+.

## 🔎 Quick Nav

- [현재 상태](#-현재-상태)
- [목표](#-목표)
- [범위](#-범위)
- [수용 기준](#-수용-기준)
- [참조 문서](#-참조-문서)

## 📊 Standard Snapshot (Paper)

- **최근 2시간**: closed=818, win_rate=38.3%, avg_pnl=-0.24%, >8% 손실=29
- **최근 24시간**: closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, >8% 손실=64
- 출처: SMOKE_TEST_MONITOR.md (2025-11-13)

---

## ⚠️ 현재 상태

**프로젝트**: ⏸️ 보류 (PHASE7-2/3 미완)  
**현행 코드**: b84c03c (안정 버전)  
**미구현 항목**: 백테스트, 전략별 분석, 동적 가중치  
**선행 조건**: PHASE7-2/3 완료 후 착수

---

## 🎯 목표

| 항목 | 목표 | 개선 방안 |
|------|------|----------|
| **승률** | **50%+** | 전략별 분석 및 필터링 |
| **손익비** | **1.0+** | 낮은 승률 전략 제거/조정 |
| **Sharpe Ratio** | **> 1.0** | 리스크 조정 수익 |

---

## 📋 범위

### 1. 백테스트 파이프라인 (3일)

**목적**: 2024년 전체 데이터로 전략별 백테스트  
**구축**:
- 과거 데이터 수집 (Binance API)
- 백테스트 엔진 (전략별 실행)
- 성과 메트릭 (승률/Sharpe/MDD)
- 리포트 자동 생성

**파일**: `scripts/backtest_runner.py`, `analytics/backtest_analyzer.py`

### 2. 전략별 성과 분석 (1주)

**목적**: 6개 전략 중 어떤 것이 좋은지 검증  
**방법**:
- 각 전략 단독 백테스트
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

**파일**: `analytics/strategy_analyzer.py`

### 3. 동적 가중치 강화 (2일)

**문제**: Experience Score 있지만 약함 (거래 수만 강하게 반영)  
**해결**: 승률 기반 가중치 조정

```python
def calculate_adaptive_weight(strategy_id, perf):
    winrate = perf[strategy_id]['winrate']
    
    if winrate < 0.45:
        winrate_mult = 0.5    # 50% 감소
    elif winrate < 0.55:
        winrate_mult = 1.0    # 기본
    elif winrate < 0.65:
        winrate_mult = 1.5    # 50% 증가
    else:
        winrate_mult = 2.0    # 100% 증가
    
    return base_weight * winrate_mult
```

**파일**: `strategies/ensemble.py`

### 4. 리스크 관리 강화 (2일)

**추가**:
- Position Correlation (심볼 간 상관관계)
- 섹터별 Exposure Limit
- 심볼별 최대 포지션 수

**파일**: `execution/risk_manager.py`

---

## ✅ 수용 기준

**PHASE7-5 진입 전 필수**:
- Paper 1주 평균 승률 ≥ 50%
- Sharpe Ratio > 1.0
- Profit Factor > 1.1
- 24h 기준 >8% 손실 0건

---

## 📋 체크리스트

**구현 전**:
- [ ] PHASE7_ALGORITHM_BEST.md 벤치마킹 재검토
- [ ] 2024년 과거 데이터 수집 계획
- [ ] .windsurfrules 준수

**구현 중**:
- [ ] 백테스트 엔진 (scripts/backtest_runner.py)
- [ ] 전략별 분석 (analytics/strategy_analyzer.py)
- [ ] 동적 가중치 (strategies/ensemble.py)
- [ ] 리스크 관리 (execution/risk_manager.py)

**검증**:
- [ ] 백테스트 2024년 전체 실행
- [ ] 전략별 승률/Sharpe/MDD 검증
- [ ] Paper 1주 테스트: 승률 50%+ 달성

---

## 🔗 참조 문서

- **PHASE7_ALGORITHM_BEST.md** - 앙상블 TO-BE 설계 (MASTER)
- **PHASE7-2/3_MASTER_PLAN.md** - 선행 단계
- **SMOKE_TEST_MONITOR.md** - 실시간 관측

---

## 📝 업데이트 로그

- **2025-11-13**: 문서 간소화 (374→250라인). MASTER 템플릿 적용.
- **2025-11-12**: PHASE7-4 계획 수립

---

**최종 업데이트**: 2025-11-13  
**다음 단계**: PHASE7-2/3 완료 후 착수
