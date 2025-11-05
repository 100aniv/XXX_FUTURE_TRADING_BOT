# 🎯 다음 테스트 진행 가이드 (2025-10-23)

## ✅ 완료된 수정 사항

### 1. **치명적 버그 수정 (engine.py)**
- **파일:** `execution/engine.py` 라인 278-297
- **문제:** save_signal_to_db() 호출 시 매개변수 이름/타입 불일치
- **수정:**
  ```python
  # ✅ 수정됨
  save_signal_to_db(
      signal_id=str(uuid4()),
      strategy_id=strategy_id,
      symbol=candle_symbol,
      timeframe=config.get('timeframe', '5m'),  # ✅ 추가
      candle_closed_at=datetime.fromtimestamp(ts/1000),  # ✅ int → datetime
      direction=signal.get('side'),  # ✅ side → direction
      confidence=signal.get('confidence', 0.75),  # ✅ 추가
      entry_price=signal.get('entry'),
      sl_price=signal.get('sl'),
      tp_price=signal.get('tp'),
      atr=signal.get('atr'),  # ✅ 추가
      leverage=signal.get('lev')  # ✅ 추가
  )
  ```

### 2. **리스크 파라미터 완화 (config.yml)**
- **파일:** `config.yml` 라인 126
- **변경:** `portfolio.max_correlated_positions: 2 → 5`
- **효과:** BTC/ETH/BNB 등 메이저 코인 동시 진입 허용

### 3. **문서 업데이트**
- **파일:** `docs/PHASE3/BUG_FIX/BUG_FIX.md`
- **내용:** 실제 코드 검증 결과 + 수정 내역 추가

---

## 📋 테스트 진행 체크리스트

### Phase 1: 테스트 준비 (⚠️ 필수 확인)

- [ ] **TEST_SCENARIO.md 정독**
  - [ ] Freeze → Tune 순서 이해
  - [ ] 단계별 게이트 기준 확인
  - [ ] 조합 축소 전략 이해

- [ ] **BACKTEST_PERIODS.md 준수**
  - [ ] 대표 6~7개 레짐 블록 선택
  - [ ] WFA 블록 설계 (Train 8주 + OOS 3주)
  - [ ] 전략별 최소 테스트 길이 확인

- [ ] **config.yml 검증**
  - [ ] `mode: backtest` 확인
  - [ ] `strategy.use_ensemble: false` (단일 전략 모드)
  - [ ] `strategy.selector: reversion` (또는 테스트할 전략)
  - [ ] `backtest.data_file` 경로 확인
  - [ ] 리스크 파라미터 검증

---

### Phase 2: Cycle 2 재시작 (REVERSION v3)

#### 2-1. 데이터 준비
- [ ] WFA 블록 확인:
  ```bash
  ls data/wfa_blocks/
  ```
- [ ] 지표 추가 확인:
  ```bash
  python scripts/add_indicators_to_wfa.py
  ```

#### 2-2. Baseline 테스트 (3개 대표 블록)
- [ ] **2018_WFA01** (약세)
  ```yaml
  backtest:
    data_file: wfa_blocks/BTCUSDT_15m_2018_WFA01_TRAIN.csv
  ```
- [ ] **bull_WFA01** (강세)
  ```yaml
  backtest:
    data_file: wfa_blocks/BTCUSDT_15m_bull_WFA01_TRAIN.csv
  ```
- [ ] **2022_WFA01** (루나/FTX)
  ```yaml
  backtest:
    data_file: wfa_blocks/BTCUSDT_15m_2022_WFA01_TRAIN.csv
  ```

#### 2-3. 실행 명령어
```bash
python main.py
```

#### 2-4. 게이트 기준 (각 블록마다 확인)
- [ ] **Expectancy ≥ +0.10R**
- [ ] **PF ≥ 1.3**
- [ ] **MDD ≤ -20%**
- [ ] **연속SL ≤ 6**
- [ ] **거래 수 ≥ 10건** (의미 있는 샘플)

---

### Phase 3: TEST_CHECKLIST.md 업데이트

#### 3-1. 실험 결과 기록
```markdown
| EXP-C2-XX | A-2 | reversion | BTC | Baseline | 2018_WFA01 15m, RSI<35, BB근접, MACD확인 | - | - | [ROI%] | [통과/실패] |
```

#### 3-2. 메타데이터 업데이트
```markdown
| 코드 커밋 | Cycle 2 Day 2 - Bug Fix (engine.py, config.yml) |
| 수정 사항 | save_signal_to_db() 수정, portfolio.max_correlated_positions 완화 |
```

#### 3-3. 게이트 체크
```markdown
## ✅ Gate 체크
- [ ] OOS Expectancy ≥ +0.10R
- [ ] PF ≥ 1.3
- [ ] MDD ≤ -20%
- [ ] 연속SL ≤ 6
```

---

## 🔧 현재 전략 설정 (REVERSION v3)

```yaml
strategies:
  reversion:
    enabled: true
    timeframe: 15m
    rsi_threshold: 35  # v3: 완화 (30→35)
    bb_lower_pct: 0.98  # v3: BB 하단 근접
    bb_upper_pct: 1.02  # v3: BB 상단 근접
    volume_mult: 1.2  # v3: 거래량 증가 배수
    cooldown_candles: 10  # v3: 완화 (20→10)
    risk_per_trade: 0.01
    rr: 2.0
    atr_mult_sl: 1.5
```

**전략 로직 (strategies/reversion.py):**
- **1단계:** 과매도/과매수 영역 감지
  - RSI < 35 + BB 하단 근접 (98%)
  - RSI > 65 + BB 상단 근접 (102%)
- **2단계:** 반전 확인 필터
  - MACD 방향 전환 OR 양봉/음봉 OR 거래량 증가

---

## ⚠️ 주의사항

### 1. PowerShell 명령어
- 복잡한 파이프 조합 금지
- 간단한 명령만 사용 (python, ls, cd)

### 2. 테스트 진행
- **한 번에 하나씩** (여러 변경 동시 진행 금지)
- 각 테스트마다 결과 기록
- 실패 시 원인 분석 후 다음 단계

### 3. 문서 동기화
- TEST_CHECKLIST.md 실시간 업데이트
- 실험 번호 순차적으로 증가 (EXP-C2-06, 07, ...)
- 메타데이터 정확히 기록 (날짜, 설정, 결과)

---

## 📊 예상 결과

### 버그 수정 전 (Cycle 2 Day 1)
- **3개 블록 모두 실패**
- 승률 ~25%, ROI -1,700% ~ -1,900%
- 거래 수 72~90건

### 버그 수정 후 (Cycle 2 Day 2 예상)
- **신호 DB 저장 정상화**
- **거래 차단 완화** (3,111건 → 더 많은 체결 예상)
- **성능 개선 가능성:**
  - 과도한 리스크 차단 해제
  - 앙상블 모드에서 신호 통합 정상 동작

---

## 🎯 성공 기준

### Baseline 통과 조건
- **3개 대표 블록 중 최소 2개 통과**
- **통과 기준:**
  - Expectancy ≥ +0.10R
  - PF ≥ 1.3
  - MDD ≤ -20%
  - 연속SL ≤ 6

### 다음 단계
- **통과:** Exits 튜닝 (stop.k, trailing.k, TP 분할)
- **실패:** Entries 완화 (RSI 임계값, BB 터치 비율)

---

## 📝 실행 로그

```bash
# 1. 데이터 확인
ls data/wfa_blocks/

# 2. config.yml 백업
Copy-Item config.yml config_backup_cycle2_day2.yml

# 3. 테스트 실행
python main.py

# 4. 결과 확인
# - logs/application.log
# - data/trading.db (SQLite)
# - reports/backtest/*.html

# 5. TEST_CHECKLIST.md 업데이트
# (수동)
```

---

## 🔍 디버깅 팁

### 신호 저장 확인
```python
# data/trading.db 확인 (백테스트 결과)
import sqlite3
conn = sqlite3.connect('data/trading.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM trades LIMIT 10")
print(cursor.fetchall())
```

### 로그 분석
```bash
# 최근 로그 확인
tail -n 100 logs/application.log

# 거래 체결 확인
grep "✅ \[" logs/application.log

# 리스크 체크 확인
grep "⛔" logs/application.log
```

---

## 📚 참고 문서

1. **TEST_SCENARIO.md**: 전체 테스트 전략 및 순서
2. **BACKTEST_PERIODS.md**: 대표 레짐 블록 및 WFA 설계
3. **TEST_CHECKLIST.md**: 실험 진행 상황 추적
4. **BUG_FIX.md**: 버그 분석 및 수정 내역
5. **WFA_RESULTS_SUMMARY.md**: WFA 테스트 결과 요약

---

## ✅ 최종 체크

- [x] engine.py save_signal_to_db() 수정 완료
- [x] config.yml 리스크 파라미터 완화 완료
- [x] BUG_FIX.md 업데이트 완료
- [ ] cleanup/ 디렉토리 수동 정리 필요 (PowerShell 이슈)
- [ ] 테스트 재실행 대기
- [ ] TEST_CHECKLIST.md 업데이트 대기

**이제 테스트를 진행하세요!**
