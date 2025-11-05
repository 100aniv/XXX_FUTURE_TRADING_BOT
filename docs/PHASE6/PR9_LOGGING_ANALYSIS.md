# PR9 로깅 분석 및 개선 제안

**작성**: 2025-11-06 01:47 UTC+09:00

---

## 현재 상태

### 1. TP/SL 이모지 (config.yml)

**현재 설정:**
```yaml
telegram:
  emoji:
    take_profit: ✅🏆      # 익절
    stop_loss: ⛔🛑        # 손절
    tp1_partial: 🟡🎯     # 부분 익절 (TP1)
```

**결론: ✅ 정상**
- TP와 SL 이모지가 명확히 구분됨
- TP: ✅🏆 (초록 체크 + 트로피)
- SL: ⛔🛑 (빨강 금지 + 정지)
- TP1: 🟡🎯 (노랑 원 + 다트)

**텔레그램 출력 예시:**
```
✅🏆 [1] TP: LONG XPLUSDT @ 0.32 (Entry: 0.30) | PnL: $200 (+6.67%)
⛔🛑 [2] SL: SHORT BTCUSDT @ 45000 (Entry: 46000) | PnL: -$100 (-2.17%)
🟡🎯 [3] TP1: LONG ETHUSDT @ 2500 (Entry: 2400) | PnL: $150 (+4.17%)
```

---

### 2. 진입 로깅 (execution/engine.py)

**현재 구조 (3줄):**
```python
# Line 921: 간단 요약
logger.info(f"✅ [{trade_count}] {decision.get('side')} @ {fill.get('filled_price'):.2f}")

# Line 968: 상세 정보
logger.info(f"{emoji_circle} [{mode_tag}|{strategy_tag}] {candle_symbol} BUY @ {fill.get('filled_price'):,.2f} | SL: {decision.get('sl'):,.2f} | TP: {decision.get('tp'):,.2f} | Qty: {qty:.2f} | Notional: ${position_value:,.0f} | x{signal_info['lev']}")

# Line 974: 포트폴리오 상태
logger.info(f"📊 [PORTFOLIO] Positions {total_positions}/{max_positions} | Total Notional: ${total_exposure:,.0f} ({exposure_pct:.1f}%) | Equity: ${current_equity:,.0f}")
```

**실제 출력 예시:**
```
✅ [1] LONG @ 0.30
🔵 [PAPER|ENSEMBLE] XPLUSDT BUY @ 0.30 | SL: 0.29 | TP: 0.31 | Qty: 100.00 | Notional: $30 | x2
📊 [PORTFOLIO] Positions 1/5 | Total Notional: $30 (0.3%) | Equity: $10000
```

---

## 개선 제안

### Option A: 1줄 통합 (텔레그램 스타일)

**장점:**
- 간결하고 통일성 있음
- 텔레그램과 동일한 포맷
- 로그 가독성 향상

**단점:**
- 포트폴리오 상태 정보 누락 가능

**제안 포맷:**
```python
logger.info(f"{emoji_circle} [{trade_count}] {mode_tag}|{strategy_tag} {candle_symbol} {decision.get('side')} @ {fill.get('filled_price'):,.2f} | SL: {decision.get('sl'):,.2f} | TP: {decision.get('tp'):,.2f} | Qty: {qty:.2f} | ${position_value:,.0f} | x{signal_info['lev']} | Pos: {total_positions}/{max_positions}")
```

**출력 예시:**
```
🔵 [1] PAPER|ENSEMBLE XPLUSDT LONG @ 0.30 | SL: 0.29 | TP: 0.31 | Qty: 100.00 | $30 | x2 | Pos: 1/5
```

---

### Option B: 2줄 (진입 + 포트폴리오)

**장점:**
- 진입 정보와 포트폴리오 상태 분리
- 가독성 유지

**단점:**
- 여전히 2줄

**제안 포맷:**
```python
# Line 1: 진입 정보
logger.info(f"{emoji_circle} [{trade_count}] {mode_tag}|{strategy_tag} {candle_symbol} {decision.get('side')} @ {fill.get('filled_price'):,.2f} | SL: {decision.get('sl'):,.2f} | TP: {decision.get('tp'):,.2f} | Qty: {qty:.2f} | ${position_value:,.0f} | x{signal_info['lev']}")

# Line 2: 포트폴리오 상태
logger.info(f"📊 [PORTFOLIO] Pos: {total_positions}/{max_positions} | Notional: ${total_exposure:,.0f} ({exposure_pct:.1f}%) | Equity: ${current_equity:,.0f}")
```

**출력 예시:**
```
🔵 [1] PAPER|ENSEMBLE XPLUSDT LONG @ 0.30 | SL: 0.29 | TP: 0.31 | Qty: 100.00 | $30 | x2
📊 [PORTFOLIO] Pos: 1/5 | Notional: $30 (0.3%) | Equity: $10000
```

---

### Option C: 현재 유지 (3줄)

**장점:**
- 정보 손실 없음
- 디버깅 용이

**단점:**
- 로그가 길어짐
- 통일성 부족

---

## 청산 로깅 (비교)

**현재 청산 로깅 (1줄):**
```python
logger.info(f"{exit_emoji} [{closed_count}] {reason}: {position['side']} {position['symbol']} @ {current_price:,.2f} (Entry: {position['entry']:,.2f}) | PnL: ${pnl:,.2f} ({pnl_pct_calc:+.2f}%)")
```

**출력 예시:**
```
✅🏆 [1] TP: LONG XPLUSDT @ 0.32 (Entry: 0.30) | PnL: $200 (+6.67%)
⛔🛑 [2] SL: SHORT BTCUSDT @ 45000 (Entry: 46000) | PnL: -$100 (-2.17%)
```

**통일성 관점:**
- 청산은 1줄
- 진입은 3줄 → **불균형**

---

## 권장 사항

### 🎯 Option A 추천 (1줄 통합)

**이유:**
1. 청산 로깅과 통일성 유지
2. 텔레그램 포맷과 일치
3. 로그 가독성 향상
4. 필수 정보 모두 포함 가능

**구현:**
```python
# Line 921 제거 (중복)
# Line 968 수정 (1줄 통합)
logger.info(f"{emoji_circle} [{trade_count}] {mode_tag}|{strategy_tag} {candle_symbol} {decision.get('side')} @ {fill.get('filled_price'):,.2f} | SL: {decision.get('sl'):,.2f} | TP: {decision.get('tp'):,.2f} | Qty: {qty:.2f} | ${position_value:,.0f} | x{signal_info['lev']} | Pos: {total_positions}/{max_positions} ({exposure_pct:.1f}%)")
# Line 974 제거 (통합됨)
```

**최종 출력:**
```
🔵 [1] PAPER|ENSEMBLE XPLUSDT LONG @ 0.30 | SL: 0.29 | TP: 0.31 | Qty: 100.00 | $30 | x2 | Pos: 1/5 (0.3%)
```

---

## 한글 로그 깨짐 해결

**문제:**
Docker 로그에서 한글이 `???`로 표시됨

**원인:**
UTF-8 인코딩 환경변수 미설정

**해결:**
Dockerfile에 환경변수 추가
```dockerfile
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8
```

**적용 후:**
```
✅ Redis 연결 성공: redis:6379
🔒 ensemble_1_signals XPLUSDT 쿨다운 중 (Redis TTL: 30초)
```

---

## 다음 단계

1. **즉시 적용:**
   - [x] Dockerfile UTF-8 환경변수 추가
   - [ ] Docker 재빌드 및 테스트

2. **검토 후 적용:**
   - [ ] 진입 로깅 1줄 통합 (Option A)
   - [ ] 사용자 확인 후 구현

3. **PR9 Fix Log 업데이트:**
   - [ ] 한글 로그 깨짐 해결 기록
   - [ ] 로깅 개선 기록 (적용 시)

---

**작성**: 2025-11-06 01:47 UTC+09:00  
**상태**: 분석 완료, 적용 대기 ✅
