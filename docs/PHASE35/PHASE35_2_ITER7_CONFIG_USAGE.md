# PHASE35-2 ITER7: Config 실제 사용 키 분석

**분석 방법**: Static analysis (execution/*.py 코드 grep)  
**날짜**: 2024-12-15

---

## 1. 현재 실제 사용되는 Config 키 (Confirmed)

### 기본 설정
- `mode` - risk_manager.py
- `timeframe` - engine.py, risk_manager.py
- `symbol` - engine.py
- `lookback` - engine.py
- `equity` - engine.py

### 자본 관리 (Capital)
- `capital.initial` - risk_manager.py, position_sizer.py, portfolio_manager.py, engine.py

### 리스크 관리 (Risk)
- `risk.per_trade` - engine.py, position_sizer.py
- `risk.max_positions` - risk_manager.py, portfolio_manager.py, position_sizer.py
- `risk.max_exposure_per_symbol` - risk_manager.py, portfolio_manager.py
- `risk.profiles` - risk_manager.py (모드별 프로파일)
- `risk.liq_buffer_multiple_of_SL` - position_sizer.py
- `risk.leverage_cap` - position_sizer.py
- `risk.margin_ratio` - position_sizer.py

### 포지션 사이징 (Position Sizing)
- `position_sizing.min_position_value` - position_sizer.py
- `position_sizing.max_position_value` - position_sizer.py
- `position_sizing.quality_weight_min` - position_sizer.py
- `position_sizing.quality_weight_max` - position_sizer.py
- `position_sizing.min_position_notional` - risk_manager.py
- `position_sizing.exposure_reduction_factor` - risk_manager.py
- `position_sizing.context_scaling` - position_sizer.py

### 포트폴리오 (Portfolio)
- `portfolio.max_total_exposure` - portfolio_manager.py
- `portfolio.max_strategy_positions` - portfolio_manager.py
- `portfolio.use_dynamic_exposure` - portfolio_manager.py
- `portfolio.use_dynamic_budget` - portfolio_manager.py
- `portfolio.enable_strategy_budget_cap` - portfolio_manager.py
- `portfolio.max_budget_per_trade_pct` - (ITER3 SSOT에 존재)

### 레버리지 (Leverage)
- `leverage.max` - position_sizer.py
- `leverage.min` - position_sizer.py
- `leverage.default` - position_sizer.py
- `leverage.mode` - (ITER3 SSOT에 존재)
- `leverage.value` - (ITER3 SSOT에 존재)

### 청산/이탈 (Exits/TP)
- `exits.take_profits` - tp_manager.py
- `exits.volatility_regime_multipliers` - tp_manager.py
- `exit.time_bars` - (ITER3 SSOT에 존재, 전략 파라미터)
- `exit.adverse_move_pct` - (ITER3 SSOT에 존재, 전략 파라미터)
- `enable_trailing_stop` - position_tracker.py

### Flash Guard (급등락 감지)
- `enable_flash_guard` - risk_manager.py
- `flash_guard.enabled` - risk_manager.py
- `flash_guard.window_sec` - risk_manager.py
- `flash_guard.threshold_pct` - risk_manager.py
- `flash_guard.pause_candles` - risk_manager.py
- `flash_guard.log_throttle_sec` - risk_manager.py
- `flash_window_sec` - risk_manager.py (파생)
- `flash_pct` - risk_manager.py (파생)
- `flash_pause_candles` - risk_manager.py (파생)

### 전략 (Strategy)
- `strategy.selector` - engine.py
- `strategies.<name>.params` - engine.py (merge)

---

## 2. 누락된 중요 리스크 가드 키 (❌ 미구현)

### 일일 트레이드 상한
- `risk.max_trades_per_day` - **누락**
- 코드에서 참조 없음
- **구현 필요**: engine.py 또는 risk_manager.py에 일일 카운터 추가

### 킬스위치 (극단 손실 차단)
- `risk.extreme_loss_cutoff_pct` - **누락**
- `risk.max_drawdown_pct` - **누락**
- 코드에서 참조 없음
- **구현 필요**: engine.py 메인 루프에서 equity 기반 체크

### 레버리지 강제 상한
- `leverage.max` - ✅ 존재하지만 실제 강제 여부 불명확
- position_sizer.py에서 `self.max_leverage = min(leverage.get('max', 10), self.leverage_cap)` 사용
- **검증 필요**: 실제로 주문 생성 시 cap이 적용되는지

---

## 3. Config 스키마 모순/중복 (정리 필요)

### Leverage 중복
- `leverage.max` - position_sizer
- `leverage.value` - (ITER3 SSOT에만 존재, 사용처 불명)
- `leverage.mode` - (ITER3 SSOT에만 존재)
- `risk.leverage_cap` - position_sizer (leverage.max와 중복)

**권장**: `leverage.max`를 단일 SSOT로 통일, `risk.leverage_cap` 제거

### Capital 중복
- `capital.initial`
- `equity`
- `initial_capital`

**권장**: `capital.initial`을 SSOT로 통일

### Portfolio Budget
- `portfolio.max_budget_per_trade_pct` - ITER3 SSOT에 존재
- 코드에서 직접 참조는 보이지 않음 (portfolio_manager 내부 로직?)

---

## 4. SSOT 필수 키 목록 (REQUIRED_DOTPATHS 업데이트 대상)

### Tier 1: 엔진 필수
- `mode`
- `timeframe`
- `symbol`
- `lookback`
- `equity` (또는 `capital.initial`)

### Tier 2: 리스크 필수
- `capital.initial`
- `risk.per_trade`
- `risk.max_positions`
- `risk.max_exposure_per_symbol`
- **`risk.max_trades_per_day`** (신규 추가 필요)
- **`risk.max_drawdown_pct`** (신규 추가 필요)
- **`risk.extreme_loss_cutoff_pct`** (신규 추가 필요)

### Tier 3: 포지션/포트폴리오 필수
- `position_sizing.min_position_value`
- `position_sizing.max_position_value`
- `position_sizing.quality_weight_min`
- `position_sizing.quality_weight_max`
- `portfolio.max_total_exposure`
- `portfolio.max_strategy_positions`
- `leverage.max`

### Tier 4: 전략 필수
- `strategy.selector`
- `strategies.<name>.params` (동적)

---

## 5. ITER7 액션 아이템

### STEP 2: Config 스키마 단일화
1. `configs/phase35/phase35_2_iter3_ssot.yaml` 수정:
   - `risk.max_trades_per_day: 10` 추가 (백테스트 안전 기본값)
   - `risk.max_drawdown_pct: 30.0` 추가 (30% DD 시 경고)
   - `risk.extreme_loss_cutoff_pct: 45.0` 추가 (45% 손실 시 킬스위치)
   - `leverage.max: 1` 확인 (이미 존재)
   - 중복 키 정리: `leverage.value`, `leverage.mode` 제거 고려

2. `common/config_required.py` 업데이트:
   - `REQUIRED_DOTPATHS`에 위 3개 신규 키 추가

### STEP 3: 런타임 리스크 가드 구현
1. **일일 트레이드 카운터** (execution/risk_manager.py 또는 engine.py):
   ```python
   # 날짜별 트레이드 카운터
   self.daily_trade_count = {}  # {date_str: count}
   
   def check_daily_trade_limit(self, current_date: str) -> bool:
       max_trades = self.config['risk']['max_trades_per_day']
       current_count = self.daily_trade_count.get(current_date, 0)
       return current_count < max_trades
   ```

2. **킬스위치** (engine.py 메인 루프):
   ```python
   # 매 바마다 equity 체크
   current_equity = portfolio.get_equity()
   loss_pct = (current_equity - initial_equity) / initial_equity * 100
   
   if loss_pct <= -config['risk']['extreme_loss_cutoff_pct']:
       logger.critical(f"🛑 킬스위치 발동: {loss_pct:.2f}% 손실")
       # 모든 포지션 청산 시도
       # 신규 진입 금지 플래그
       break  # 백테스트 중단
   ```

3. **레버리지 캡 검증** (position_sizer.py):
   - 기존 코드 검토 후 실제 cap 적용 확인
   - 미적용 시 주문 생성 시점에 강제 축소 로직 추가

---

**산출물**: 이 문서는 ITER7 작업의 기반 자료로 사용됨
