# PHASE8 MASTER PLAN  
**목표: 전체 프로젝트 구조 정비 + 재현성 확립 + 백테스트/전략 검증 체계 구축**

---

# 0. 개요 (Why PHASE8?)
현재 프로젝트는 다음 문제가 누적되어 있음:

1) **재현성 부재**  
- 실행할 때마다 결과가 다름  
- effective_config 없음  
- 백테스트 환경 없음  
- 실험 조건 추적 불가  

2) **난개발로 모듈 의미 불명확**  
- reports/ 는 legacy  
- analytics/만이 실제 유효 모듈  
- 전략/엔진 코드 중복 및 무질서  

3) **Paper/LIVE/Past Test 구분 없음**  
- 수수료/슬리피지/쿨다운 섞여 있음  
- Paper에도 슬리피지 적용  
- 자주 “Precision 오류” 발생  

4) **voting/score 혼재**  
- Voting → Score Fusion → 롤백  
- 여러 방식 섞여 일관성 없음  

**PHASE8은 이 모든 문제를 정리하는 ‘구조 총정리 단계’이다.**

---

# 1. PHASE8의 최종 목표

## 🎯 최종적으로 프로젝트를 아래 상태로 만든다:

### (1) **재현성 100% 확보**
- effective_config.yml 자동 저장
- env/mode/run_id 구조 확립
- 실행 조건 로그 헤더에 표시

### (2) **백테스트 환경 완전 구현**
- backtest_clean 모드 추가
- CSV 기반 결정적 체결
- 수수료/슬리피지/쿨다운 OFF

### (3) **단일 전략 점수표(scorecard) 자동 생성**
필수 지표:
- 총 거래 수
- Winrate
- Profit Factor
- Max Drawdown
- >8% 손실 횟수
- TP 도달률

### (4) **legacy 제거 + 모듈 정리**
- reports/ 완전 폐기
- analytics/ 에 모든 지표/리포트 통합
- 엔진/전략/리스크 하드코딩 제거

### (5) **앙상블은 ‘봉인’**
- Phase8에서는 앙상블 로직 절대 수정하지 않음
- Shadow Score만 기록  
- Phase9에서 앙상블 재개

---

# 2. Phase8 개발 범위 (실제 작업)

## 2-1. config 시스템 정비
- base.yml / modes/*.yml / active/current.yml 구조 확정
- 병합 순서 고정
- 실행 시 effective_config.yml 저장

## 2-2. config_validation 추가
- 필수 키 확인
- 타입/범위 체크
- 중복 의미 키 충돌 검사

## 2-3. backtest_clean 모드 생성
```
fill_policy: next_open  
fees_bps: 10  
slippage: fixed_5bps  
flash_guard: false  
cooldown: 0  
ensemble.enabled: false  
```

## 2-4. run_backtest.py 생성 (단일 엔트리)
- 전략 1개만 실행  
- CSV 데이터 기반  
- 결과는 artifacts/로 저장

## 2-5. analytics 기반 scorecard 생성
폴더 구조:

```
analytics/
  ├─ scorecard/
  │   ├─ scorecard_generator.py
  │   ├─ metrics.py
  │   ├─ writer_csv.py
  │   └─ writer_md.py
```

## 2-6. reports/ 폐기 선언
- legacy 폴더로 남기되 개발 금지

---

# 3. 산출물 구조 (결과물)

```
artifacts/
  └─ backtest_clean/
       └─ {run_id}/
            ├─ effective_config.yml
            ├─ scorecard.csv
            ├─ scorecard.md
            ├─ trades.log
```

---

# 4. PHASE8의 성공 기준

- 단일 전략(backtest_clean) 기준:
  - Winrate ≥ 40%  
  - PF ≥ 1.10  
  - Max DD > -20%  
  - >8% 손실 0  
  - 설정 스냅샷 저장 성공  

- 모든 전략 단독 테스트 완료 후  
  → Phase9에서 앙상블 복귀

---

# 5. RULES (요약)

- reports/ 사용 금지  
- analytics/만 리포트/지표 생성  
- 엔진/브로커/전략 하드코딩 금지  
- config만 읽어서 동작  
- 앙상블 OFF (Phase8 전체)  
- core 리팩토링 금지  
- Score Fusion 금지 (Phase9로 이월)  

---

# 6. Windsurf 작업 순서 (단계별)

1) config_loader 정비  
2) config_validation 작성  
3) backtest_clean.yml 생성  
4) run_backtest.py 작성  
5) analytics/scorecard 시스템 작성  
6) 모듈 경로 정리 및 import 정리  
7) artifacts 저장 구조 구현  
8) 단일 전략(backtest_clean) 테스트  
9) scorecard 제출  

---

# 7. PHASE8 진행 현황

## ✅ PHASE8-1: Config 시스템 정비 (완료)
- base.yml / modes/*.yml / active/current.yml 병합 구조 확립
- config_validation 추가 (필수 키, 타입, 충돌 검사)
- effective_config.yml 자동 저장

## ✅ PHASE8-2: Backtest Clean 환경 구축 (완료)
- backtest_clean 모드 생성 (fill_policy: next_open, fees_bps: 10, slippage: fixed_5bps)
- run_backtest.py 단일 엔트리 스크립트 작성
- PortfolioManager 완전 격리 (load_existing=False)
- Redis dedup 비활성화
- DB env별 격리 (trading.trades, positions, metrics, signals)

## ✅ PHASE8-2c: DB Trades INSERT 수정 (완료)
- trading.trades INSERT 문 21개 컬럼 명시
- decision_id 컬럼 추가
- trades_mode_check 제약 수정 (backtest_clean 추가)
- DB 저장 성공 확인 (17/17건)

## ✅ PHASE8-3: Strategy Baseline Backtest (완료)

### scalping / BTCUSDT / 5m / 30d backtest_clean baseline

**Run ID**: `20251114_184356_pfmz`  
**기간**: 2024-10-01 ~ 2024-10-31 (30일, OOS 데이터)  
**총 캔들**: 26,101개  

**성능 지표:**
- **Trades Closed**: 25건 (목표: ≥100, ❌ 데이터 부족)
- **Winrate**: 44.0% (목표: ≥40%, ✅ 통과)
- **Profit Factor**: 0.68 (목표: ≥1.10, ❌ 손실 상태)
- **Max Drawdown**: -2.03% (목표: >-20%, ✅ 통과)
- **Loss > 8%**: 0건 (목표: =0, ✅ 통과)
- **TP Hit Rate**: 0.0%
- **Sharpe Ratio**: -0.18

**Overall Result**: ❌ 불합격 (PF < 1.10, 거래 수 부족)

**산출물:**
- `artifacts/backtest_clean/20251114_184356_pfmz/scorecard.md`
- `artifacts/backtest_clean/20251114_184356_pfmz/effective_config.yml`
- `artifacts/backtest_clean/20251114_184356_pfmz/scorecard.csv`

**분석:**
- scalping 전략은 현재 손실 상태 (PF 0.68)
- Winrate는 목표 달성했으나 손실 크기가 더 큼
- 30일 데이터로도 거래 수 25건에 불과 (목표 100건 미달)
- 리스크 관리는 양호 (DD -2.03%, 큰 손실 0건)

**다음 단계 고려사항:**
- 전략 파라미터 튜닝 필요 (PHASE9)
- TP/SL 비율 재검토
- 진입 조건 강화
- 장기 백테스트 (90일+) 필요

---
