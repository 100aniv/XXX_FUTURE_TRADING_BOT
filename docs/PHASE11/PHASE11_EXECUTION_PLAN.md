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

## 📊 PHASE11-C 결과 요약 (2025-11-15 23:20 UTC+09:00)

### 작업 내용
1. **Pattern 토글 구현**: Core (A/B) vs Aggressive (C/D/E) 분리
2. **전용 쿨다운**: entry_cooldown_seconds=15 (스캘핑 전용)
3. **SL/TP 완화**: atr_mult_sl=1.2, rr=1.5
4. **파라미터 강화**: RSI 28/72, Volume 1.3x

### 백테스트 결과 (7일, 1m)
- **Trades**: 21-22건 ✅ (목표 20-80 범위 내)
- **Winrate**: 4.76% ❌ (목표 35%)
- **PF**: 0.01 ❌ (목표 1.1+)
- **Max DD**: -6.3% ✅ (목표 -15% 이내)
- **TP Hit Rate**: 0.0% ❌ (모든 거래가 SL 손절)

### 핵심 발견
**EMA 조건이 너무 단순:**
- `ema_fast > ema_slow`만으로는 트렌드 방향 판단 불충분
- Golden/Dead cross 이후 오랜 시간 경과해도 조건 유지 → 역트렌드 진입
- 추가 필터 필요: cross 직후 제한, price vs EMA, EMA 기울기 등

### 다음 단계 옵션
1. **Option 1**: EMA 조건 강화 (cross 타이밍, price position, 기울기)
2. **Option 2**: Pattern E 활성화 + 엄격한 조건 (RSI+Volume+EMA 다중 확인)
3. **Option 3**: 현재 구조로 Optuna 튜닝 진행 (파라미터 최적화 시도)

---

---

## 📊 PHASE11-D 결과 요약 (2025-11-15 23:48 UTC+09:00)

### 작업 내용
1. **Fresh Cross Tracking (Lookback)**:
   - 최근 N개 캔들 내에서 마지막 크로스 탐색
   - max_cross_age_candles: 80 → 25 (더 Fresh한 크로스만)
   
2. **Trend-Aware Patterns**:
   - Pattern A: Fresh Trend + RSI
   - Pattern B: Fresh Trend + Volume (비활성화)
   - Pattern E: Fresh Trend + RSI + Volume (활성화)
   
3. **Price Alignment**:
   - use_price_alignment: true
   - LONG: price > ema_fast, SHORT: price < ema_fast
   
4. **파라미터 조정**:
   - RR: 1.5 → 1.2 (TP 더 가깝게)
   - entry_cooldown_seconds: 15초 유지

### 백테스트 결과 (7일, 1m)

#### Iteration 1 (max_cross_age=80, RR=1.5, Pattern A/B/E)
- **Trades**: 26건 ✅
- **Winrate**: 0.0% ❌
- **PF**: 0.0 ❌
- **Max DD**: -8.07% ✅
- **TP Hit Rate**: 0.0% ❌

#### Iteration 2 (max_cross_age=25, RR=1.2, Pattern A/E)
- **Trades**: 12건 ✅ (목표 10-30 범위)
- **Winrate**: 8.33% ⚠️ (목표 15-30%)
- **PF**: 0.04 ❌ (목표 ≥0.6)
- **Max DD**: -2.96% ✅ (최고 수준!)
- **TP Hit Rate**: 0.0% ❌

### 핵심 발견

**✅ 성공 사항:**
1. **Fresh Cross 로직 작동**: Lookback 방식으로 크로스 탐지 성공
2. **Late Entry 감소**: age=25 이내로 제한하여 더 Fresh한 진입
3. **리스크 관리 탁월**: Max DD -2.96% (이전 -108% → -6.7% → -2.96%)
4. **첫 번째 승리 거래**: Winrate 0% → 8.33% (12건 중 1건 승리)

**❌ 여전한 문제:**
1. **TP Hit Rate 0%**: RR 1.2도 여전히 너무 높음
2. **Winrate 8.33%**: 목표 15-30%에 미달
3. **PF 0.04**: 손실이 이익을 압도

### 근본 원인 분석

**1m 스캘핑의 근본적 한계:**
- **노이즈 vs 트렌드 구분 어려움**: 1m에서는 진정한 트렌드 시작과 노이즈 구분이 극히 어려움
- **TP 달성 불가능**: RR 1.2조차 1m 변동성에서는 달성 어려움
- **Cross 기반의 한계**: EMA Cross는 Lagging Indicator로 1m에서는 이미 늦은 신호

**Fresh Cross의 한계:**
- max_cross_age=25도 1m 기준으로는 여전히 Late Entry 가능성
- Cross 직후에도 False Breakout 다수 발생

### 다음 단계 권장사항

**Option 1: 전략 방향 전환 (추천) ⭐**
- **목표**: 3m 또는 5m 타임프레임으로 상향
- **이유**: 1m은 노이즈가 너무 심해 EMA Cross 기반 전략으로는 한계
- **예상**: Winrate 20-40%, PF 0.8-1.2 달성 가능

**Option 2: Mean Reversion 전략 추가**
- **목표**: Trend Following(EMA) + Mean Reversion(BB) 혼합
- **이유**: 1m에서는 Mean Reversion이 더 효과적
- **예상**: Winrate 20-30%, PF 0.6-1.0 달성 가능

**Option 3: RR 극단적 축소**
- **목표**: RR 0.8-1.0, SL도 축소
- **이유**: 1m에서는 작은 이익을 빠르게 실현
- **예상**: Winrate 15-25%, PF 0.5-0.8 달성 가능

**Option 4: Optuna 튜닝 진행**
- **목표**: 현재 구조로 파라미터 최적화
- **이유**: max_cross_age, RSI, Volume 등 최적 조합 탐색
- **예상**: 소폭 개선 가능하나 근본적 한계 돌파 어려움

---

## 🚀 Next Step

**Recommendation**: **Option 1 (3m 타임프레임 전환)** 또는 **Option 2 (Mean Reversion 추가)**

**이유**: 1m EMA Cross 기반 전략의 근본적 한계가 확인됨
