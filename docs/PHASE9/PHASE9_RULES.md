# 🔧 Windsurf Development Rule (PHASE9 Latest)

## 📌 목적
Windsurf가 future_alarm_bot의 구조를 훼손하지 않고  
PHASE9(전략 튜닝 단계)을 정확히 수행하도록 하는 규칙.

---

# 🎯 1. 절대 수정 금지 영역 (PHASE9 전체)
아래 범위는 **절대로 수정하면 안 됨**:

1. **engine core**
   - execution/engine.py 구조
   - 포지션/주문 실행 순서
   - 슬리피지/수수료 계산 방식
   - SimBroker 기초 로직

2. **DB 스키마**
   - trading.trades
   - trading.positions
   - trading.metrics  
   (컬럼 추가/삭제 절대 금지)

3. **collector/historical_collector.py**
   - CSV 로딩 로직
   - 슬라이싱 로직
   - 데이터 품질 체크 로직

4. **PHASE8 인프라 수정 금지**
   - backtest_clean 격리 구조
   - effective_config 스냅샷
   - scorecard 시스템

---

# 🎯 2. 제한적 변경 허용 영역
아래는 "문서화 → 합의 → 코드" 순으로만 변경 가능:

## (A) configs/modes/*.yml
- backtest_raw.yml 생성 및 수정 OK
- backtest_clean.yml 일부 수정 OK (ensemble conflict 등)
- base.yml 변경은 최소화

## (B) strategies/*
- 진입 조건, 필터, TP/SL, 리스크 파라미터 변경은 가능
- 단 **문서가 먼저 존재해야 함**
  - docs/PHASE9/SCALPING_STRATEGY_MAP.md
  - docs/PHASE9/PHASE9-2_TUNING_RESULTS.md

## (C) run_backtest.py
- 새로운 모드(backtest_raw) 추가 OK
- 로그 확장 OK
- 기능 추가는 금지 (엔진 로직 추가 금지)

---

# 📌 3. 모든 작업은 아래 순서를 따라야 한다

### **RULE A — 문서 먼저**
1. 변경 전 분석 문서 생성  
2. 내가(MR WHITE) 승인  
3. 코드 수정  
4. 대응하는 문서 업데이트  
5. artifacts 출력 확인  
6. 커밋

### **RULE B — 실험 순서 고정**
1. backtest_raw baseline  
2. 진입/필터/TP/SL 수정  
3. backtest_raw 재측정  
4. backtest_clean 검증  
5. 최종 결과 문서화

### **RULE C — 모든 실험은 Run ID 필수**
- scorecard.md + effective_config.yml 포함  
- 실험 문서에서 Run ID로 무조건 링크

---

# 📌 4. PHASE9에서 Windsurf가 반드시 지켜야 할 행동 규칙

1. **기존 구조 반드시 읽고 이해 후 작업**
2. **중복 코드 생성 금지**
3. **논리·구조를 훼손하는 "새 파일 생성" 금지**
4. **수정 이유를 코드 주석 + 문서에 명시**
5. **config 충돌 발견 시 바로 기록하고 수정**
6. **결과는 무조건 Markdown 보고서로 제출**
7. **문서 외부/파일 외부의 설명은 의미 없음 → 파일에 기록해라**

---

# 📌 5. 완성된 작업의 보고 포맷

Windsurf는 각 단계 끝날 때 아래 형식으로 보고:

[PHASE9-X 완료 보고서]

✔ 변경 파일:

file1

file2

✔ 변경 이유:

...

✔ 테스트:

Run ID

기간

trades/day, winrate, PF

✔ 산출물:

artifacts/<run_id>/scorecard.md

docs/PHASE9/<doc>.md


# 📌 6. 모델 행동 설정
- 과도한 수정 금지
- 변경 근거 반드시 명시
- 나한테 질문 없이 구조 파괴 금지
- "새롭게 재설계" 절대 금지
- PHASE9 단위 외의 행동 금지

---

# 📌 7. 금지되는 AI 행동
- 임의 리팩토링
- 새 엔진 생성
- DB 모델 변경
- collector 교체
- 전략 새로 만드는 행동
- 테스트 코드 생성
- 기존 코드 재작성

---

# 🎯 최종 요약
Windsurf는 절대 구조를 파괴하지 않고  
**PHASE9: 전략 튜닝 단계**만 수행해야 하며  
모든 변경은 **문서 → 합의 → 코드 → 검증 → 문서** 순서를 따라야 한다.
