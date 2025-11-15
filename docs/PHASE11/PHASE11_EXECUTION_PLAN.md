# 🍀 PHASE11 TRUE SCALPING & TUNING FULL-AUTOMATION
## Execution Plan & Progress Tracker

**Status**: 🚀 In Progress  
**Last Updated**: 2025-11-15 21:57 UTC+09:00  
**Target Completion**: PHASE11 완료 (모든 기준 충족)

---

## 📊 작업 분해 (Work Breakdown Structure)

### Phase 11A: Scalping 전략 재설계 (HIGH PRIORITY)
- [ ] **11A-1**: 현재 scalping.py 분석 및 문제점 파악
  - 현재 조건: 너무 엄격 (7일 7건)
  - 목표: 7일 20~60건
  - 작업: 조건 완화 전략 수립
  
- [ ] **11A-2**: Scalping 신호 조건 재설계
  - EMA 교차 조건 완화
  - RSI 극단값 범위 조정
  - Volume/Momentum 필터 선택적 적용
  - Pattern A/B/C 다중 진입 로직
  
- [ ] **11A-3**: configs/base.yml 업데이트
  - scalping 섹션 파라미터 조정
  - 튜닝 가능 범위 설정
  
- [ ] **11A-4**: 7일 Sanity Backtest
  - 목표: Trades 20~60, 실행시간 2~5분
  - 검증: Scorecard/Trades 일치

### Phase 11B: 90일 기준선 Backtest
- [ ] **11B-1**: 90일 데이터 확인
  - 파일: data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
  
- [ ] **11B-2**: 90일 Backtest 실행
  - 목표: Trades 200~600, DD -20% 이내
  - 성능 기준선 수립

### Phase 11C: Optuna 튜닝 (3단계)
- [ ] **11C-1**: Smoke Test (3 Trial)
  - 목표: 파이프라인 동작 확인
  - PostgreSQL storage 검증
  
- [ ] **11C-2**: 샘플 튜닝 (30 Trial)
  - 목표: 최적 파라미터 탐색 시작
  - Best trial 성능 확인
  
- [ ] **11C-3**: 프로덕션 튜닝 (100 Trial)
  - 목표: 최고 성능 파라미터 도출
  - Before/After 비교

### Phase 11D: 앙상블 통합
- [ ] **11D-1**: scalping을 ensemble에 편입
  - strategies/ensemble.py 수정
  - configs/base.yml ensemble 섹션 업데이트
  
- [ ] **11D-2**: 앙상블 Backtest
  - 목표: 다중 전략 조화 검증

### Phase 11E: 문서화
- [ ] **11E-1**: PHASE11_SCALPING_REDESIGN.md
  - 설계 철학, 조건별 역할, 파라미터 범위
  
- [ ] **11E-2**: PHASE11_SCALPING_TUNING_SUMMARY.md
  - 튜닝 설정, Best trial, Before/After 비교

---

## 🎯 Success Criteria

### Scalping Strategy
- ✅ 7일 Sanity: Trades 20~60, 실행시간 2~5분
- ✅ 90일 기준선: Trades 200~600, DD -20% 이내
- ✅ Scorecard/Trades 동기화 (경고 로그 0)

### Tuning Pipeline
- ✅ 3 Trial smoke: PostgreSQL storage, Trades 계산 정상
- ✅ 30 Trial 샘플: Best trial 도출
- ✅ 100 Trial 프로덕션: 최고 성능 파라미터

### Ensemble Integration
- ✅ scalping이 고빈도 레그로 정상 반영
- ✅ 다중 전략 Backtest 성공

### Documentation
- ✅ PHASE11_SCALPING_REDESIGN.md (충실한 내용)
- ✅ PHASE11_SCALPING_TUNING_SUMMARY.md (충실한 내용)

---

## 📅 Timeline

| Phase | Task | Est. Time | Status |
|-------|------|-----------|--------|
| 11A | Scalping 재설계 | 1-2h | ⏳ Pending |
| 11B | 90일 기준선 | 0.5h | ⏳ Pending |
| 11C-1 | Smoke 튜닝 | 0.5h | ⏳ Pending |
| 11C-2 | 30 Trial | 2-3h | ⏳ Pending |
| 11C-3 | 100 Trial | 5-8h | ⏳ Pending |
| 11D | 앙상블 통합 | 1h | ⏳ Pending |
| 11E | 문서화 | 1h | ⏳ Pending |
| **Total** | | **11-16h** | |

---

## 🔍 Key Decisions

### 1. Scalping 조건 완화 전략
- **문제**: 현재 조건이 너무 엄격 (AND 지옥)
- **해결**: 
  - Pattern A: EMA + RSI (필수)
  - Pattern B: EMA + Volume (필수)
  - Pattern C: RSI + Momentum (선택)
  - 진입: A OR B (기본), C는 보조

### 2. 파라미터 범위 설정
- EMA: fast 5-20, slow 15-60
- RSI: oversold 20-40, overbought 60-80
- Volume: 0.8-2.0x
- RR: 1.1-1.5
- SL: 0.4-1.2x ATR

### 3. 튜닝 전략
- Train/Val 분할: 70/30 (기존 유지)
- Objective: Maximize (PF + 0.1*Winrate - DD_penalty)
- Min trades: TRAIN 10, VAL 5 (Trades=0 → score=-100)

---

## 📝 Notes

- 모든 수정은 diff 기반 patch로 수행
- DB/Storage 정책 엄격히 유지 (PostgreSQL only)
- 기존 swing_bb/ensemble 구조 보존
- 문서는 PHASE11 폴더에만 생성 (PHASE9/10 건드리지 않음)

---

## 🚀 Next Step

**Immediate Action**: 11A-1 시작 (Scalping 분석)
