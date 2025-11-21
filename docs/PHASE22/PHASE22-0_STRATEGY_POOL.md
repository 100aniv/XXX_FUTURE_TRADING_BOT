# PHASE22-0 – Global Strategy Pool & Ensemble v1 Candidate Selection

**작성일**: 2025-11-21  
**상태**: 🟦 PLANNED (템플릿 생성 완료, 실제 수치는 실행 세션에서 채움)  
**목적**: Global Strategy Pool을 SSOT로 정리하고, Ensemble v1 후보 전략군 선정

---

## 1. 목적 (Objective)

- Global Strategy Pool(전역 전략 후보군)을 **단일 진실 소스(SSOT)** 로 정리한다.
- PHASE21에서 이미 수행한 단일 전략 PAPER 테스트 결과를 요약하고,
  이를 기반으로 **Ensemble v1에 포함할 전략 후보 7~8개를 선정**한다.
- 이 문서는 이후 PHASE22-1/22-2/22-3 및 PHASE23~24의 기준점이 된다.

---

## 2. 입력 (Inputs)

**PHASE21 리포트**:
- `docs/PHASE21/PHASE21-1A_REPORT.md` – 타임프레임 최적화 및 초기 검증
- `docs/PHASE21/PHASE21-1B_FEED_FIX_REPORT.md` – Feed collector 버그 수정
- `docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md` – 인프라 레벨 검증 완료

**Scorecards / Paper 결과**:
- `scorecards/paper_phase21/*` (존재할 경우)
- Paper 실행 로그 및 DB 쿼리 결과

**Global Strategy Pool 정의**:
- `PHASE_ROADMAP.md` 내 "📚 Global Strategy Pool" 섹션

---

## 3. 전략별 요약 테이블 (To be filled)

| ID         | Type           | Timeframe | ACTIVE/LOW_FREQ | Implemented | PnL   | Win-rate | Trades | Max DD | Status (KEEP/RESERVE/DROP) |
|-----------|----------------|-----------|-----------------|-------------|-------|----------|--------|--------|-----------------------------|
| scalping  | Momentum/Scalp | 3m        | ACTIVE          | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| breakout  | Volatility     | 15m       | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| reversion | Mean Reversion | 5m        | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| swing_bb  | Mean Reversion | 5m        | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| daytrade  | Intraday Trend | 15m       | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| trend     | Trend Follow   | 1h        | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |
| swing     | Swing Trend    | 1h        | LOW_FREQ        | YES         | T.B.D | T.B.D    | T.B.D  | T.B.D  | T.B.D                       |

⚠️ **실제 수치 채우기는 다음 PHASE22-0 실행 세션에서 수행**

---

## 4. PHASE21 테스트 결과 요약

### 4.1 인프라 검증 완료 전략 (PHASE21-1C 기준)

**✅ Scalping (3m) - ACTIVE**
- Duration: 90초
- Trades: 31 (LONG 9, SHORT 22)
- PnL: -$707.65
- 결론: 고빈도 전략, 인프라 정상

**✅ Reversion (5m) - LOW_FREQ**
- Duration: 15분+
- Trades: 0 (Flash Guard 활성화)
- 결론: 평균 회귀 조건 미충족, 인프라 정상

**✅ Trend (1h) - LOW_FREQ**
- Duration: 5분
- Trades: 0
- 결론: 장기 타임프레임, 짧은 테스트에서는 신호 없음, 인프라 정상

### 4.2 타임프레임 매핑 (PHASE21-1A 확정)

| 전략 | 설계 타임프레임 | Config 수정 | 상태 |
|------|----------------|-------------|------|
| scalping | 3m | ✅ 적용 | FIXED |
| breakout | 15m | ✅ 적용 | FIXED |
| reversion | 5m | ✅ OK | OK |
| trend | 1h | ✅ 적용 | FIXED |
| swing | 1h | ✅ 적용 | FIXED |
| swing_bb | 5m | ✅ OK | OK |
| daytrade | 15m | ✅ 적용 | FIXED |

---

## 5. Ensemble v1 후보 전략군

### 5.1 포함 기준 (Inclusion Criteria)

**IN (확정 포함)**:
- [ ] 인프라 검증 PASS (PHASE21-1C)
- [ ] 타임프레임 정상 작동
- [ ] 전략 로직이 명확하고 구현 완료
- [ ] (선택) PnL/Win-rate가 허용 범위 내

**RESERVE (예비/상황에 따라 포함)**:
- [ ] 인프라는 PASS지만 성능 데이터 부족
- [ ] 타임프레임 특성상 장기 테스트 필요 (1h 전략 등)

**OUT (현재 앙상블 v1에서는 제외)**:
- [ ] 인프라 검증 미완료
- [ ] 전략 로직 불명확
- [ ] 치명적 버그 발견

### 5.2 후보 리스트 (To be decided)

**IN (확정 포함)**
- [ ] scalping – (T.B.D.)
- [ ] reversion – (T.B.D.)
- [ ] ... (실행 세션에서 결정)

**RESERVE (예비/상황에 따라 포함)**
- [ ] trend – (장기 타임프레임, 12H 테스트 필요)
- [ ] swing – (장기 타임프레임, 12H 테스트 필요)
- [ ] ... (실행 세션에서 결정)

**OUT (현재 앙상블 v1에서는 제외)**
- [ ] (실행 세션에서 결정)

---

## 6. 다음 단계 (PHASE22-0 실행 세션)

### 6.1 데이터 수집
1. PHASE21 scorecard 파일 읽기 (`scorecards/paper_phase21/*`)
2. DB 쿼리로 전략별 PnL/Win-rate/Trade Count 추출
3. 전략별 요약 테이블 (섹션 3) 채우기

### 6.2 분석 및 결정
1. 각 전략을 KEEP/RESERVE/DROP으로 분류
2. Ensemble v1 IN/OUT/RESERVE 플래그 확정
3. 최종 7~8개 전략 리스트 도출

### 6.3 산출물
1. 이 문서 업데이트 (수치 및 결정 사항 반영)
2. `PHASE_ROADMAP.md` 링크 확인
3. Git commit: `PHASE22-0: Complete Strategy Pool analysis`

---

## 7. Acceptance Criteria (퇴출 조건)

- [ ] Global Strategy Pool 테이블에 **현재 구현된 모든 전략 7개가 포함**된다.
- [ ] 각 전략에 대해 최소한 "구현 여부 / Timeframe / ACTIVE/LOW_FREQ" 정보가 채워진다.
- [ ] Ensemble v1 후보 IN/RESERVE/OUT 플래그가 명시된다.
- [ ] PHASE22-1~3에서 참조할 수 있도록, 이 문서의 위치와 역할이 PHASE_ROADMAP에 링크로 언급된다.

---

## 8. 참조

- PHASE21 완료 리포트: `docs/PHASE21/PHASE21-1C_ACTUAL_EXECUTION_REPORT.md`
- Global Strategy Pool (SSOT): `PHASE_ROADMAP.md` 섹션 참조
- PHASE22 전체 계획: `PHASE_ROADMAP.md` → PHASE22 블록
