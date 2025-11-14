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
