# Changelog

모든 주요 변경 사항은 이 파일에 기록됩니다.

---

## [v4.2.0] - 2025-10-19 20:51

### 🚀 **통합 엔진 아키텍처 완성 + 성능 튜닝**

#### Added ✅
- **execution.engine.TradingEngine** - 단일 통합 엔진
  - 모든 모드(backtest/paper/live)에서 공통 엔진 사용
  - `run_backtest()` - 완전한 백테스트 실행
  - Cooldown 로직 구현 (거래 빈도 제어)
  - Equity 동적 업데이트 (복리 효과)
  - MDD, Sharpe, Sortino 정확한 계산

- **data_sources/** - 데이터 소스 플러그인
  - `backtest.py` - CSV/Parquet 재생
  - `live.py` - 실시간 WebSocket/REST

- **executors/** - 주문 실행 플러그인
  - `simulation.py` - 백테스트 체결 (수수료+슬리피지)
  - `paper.py` - 가상 체결
  - `live.py` - 실제 체결 (Binance SDK)

- **reports/** - 리포팅 연계
  - 백테스트 완료 후 HTML 리포트 자동 생성
  - 전략 비교 시각화

#### Changed 🔄
- **common.calculations 모듈 활용**
  - `execution/engine.py`에서 `price_levels()` 함수 사용
  - 중복 코드 제거 (TP/SL 계산)

- **main.py 완전 정리**
  - 백테스트 로직 중복 제거
  - 단일 엔진만 사용
  - 실시간 모드 분리

#### Removed ❌
- `execution/executor.py` (deprecated)
- `execution/manager.py` (stub으로 변경)
- `execution/position_tracker.py` (미사용)

#### Performance 📈
- **거래 빈도 90% 감소**: Cooldown 로직으로 SCALPING 14,533 → 1,388건
- **MDD 93% 개선**: 1,550% → 103.6%
- **성능 지표 정확도**: Sharpe, Sortino, MDD 정확한 계산

#### Documentation 📝
- `docs/COMPLETE/modules/execution.md` - 통합 엔진 구조 반영
- `docs/COMPLETE/BACKTEST_STATUS.md` - 완료 상태로 업데이트
- `docs/COMPLETE/PROJECT_STRUCTURE.md` - execution 모듈 업데이트
- `SYSTEM_ARCHITECTURE.md` - 전체 아키텍처 업데이트

---

## [v3.2.0] - 2025-10-19

### 🏗️ **Phase 6 리팩토링: signals/ 모듈 분리**

#### Added ✅
- **signals/ 모듈 생성** (신호 생성 및 처리)
  - `signals/signal_generator.py` (240줄) - SignalGenerator 클래스
    - `process_candle()` - 캔들 처리 메인 로직
    - `generate_signal()` - 신호 생성 (전략 호출)
    - `validate_signal()` - 신호 검증 (MTF, 쿨다운)
    - `_mtf_confirm()` - 멀티타임프레임 확인
    - `_should_alert()` - 쿨다운 체크
  - `signals/signal_storage.py` (70줄) - 신호 DB 저장
    - `save_signal()` - 신호 DB 저장

#### Changed 🔄
- **Signal Bot 파일 (4개) 대폭 간소화**
  - `on_message()` 로직 → SignalGenerator.process_candle()로 이동
  - `mtf_confirm()` → SignalGenerator._mtf_confirm()로 이동
  - `should_alert()` → SignalGenerator._should_alert()로 이동
  - `get_strategy_module()` → SignalGenerator 내부로 이동
  - DB 저장 로직 → save_signal()로 이동

#### Performance 📈
- **코드 절감**: Signal Bot 4개 파일에서 ~200줄 제거
- **재사용성**: SignalGenerator를 다른 프로젝트에서 사용 가능
- **테스트 용이**: Signal 로직 독립 테스트
- **명확성**: 함수명이 역할을 명확히 표현

#### Files Changed
```
Added:
  - signals/__init__.py
  - signals/signal_generator.py (240줄)
  - signals/signal_storage.py (70줄)
  - test_signals_module.py (테스트)
  - test_full_flow.py (전체 플로우 테스트)

Modified:
  - telegram_signal_bot.py (signals 모듈 사용)
  - signal_bot_trend.py (signals 모듈 사용)
  - signal_bot_reversion.py (signals 모듈 사용)
  - signal_bot_breakout.py (signals 모듈 사용)

Updated:
  - docs/architecture/REFACTORING.md (Phase 6 완료)
  - docs/architecture/SIGNALS_REFACTORING.md (신규 문서)
```

---

## [v3.1.0] - 2025-10-19

### 🏗️ **Phase 5 리팩토링: 전략 로직 분리**

#### Added ✅
- **strategies/ 모듈 생성** (순수 전략 로직)
  - `strategies/scalping.py` - 스캘핑 전략 (1분/3분)
  - `strategies/daytrade.py` - 단타 전략 (5분)
  - `strategies/swing.py` - 스윙 전략 (15분)
  - `strategies/trend.py` - 추세 전략 (1시간)
  - `strategies/reversion.py` - 반전 전략 (5분)
  - `strategies/breakout.py` - 돌파 전략 (15분)

#### Changed 🔄
- **Signal Bot 파일 얇아짐**
  - `signal_logic()` 함수 → strategies/ 모듈로 이동
  - Signal Bot = WebSocket + 전략 호출 + DB 저장
  - 전략 선택: 타임프레임 기반 자동 선택

#### Performance 📈
- **코드 절감**: Signal Bot 4개 파일에서 ~250줄 제거
- **유지보수성**: 전략 변경 시 strategies/ 파일만 수정
- **테스트 용이**: 전략 로직 독립 테스트 가능

#### Files Changed
```
Added:
  - strategies/__init__.py
  - strategies/scalping.py (130줄)
  - strategies/daytrade.py (135줄)
  - strategies/swing.py (135줄)
  - strategies/trend.py (130줄)
  - strategies/reversion.py (130줄)
  - strategies/breakout.py (135줄)

Modified:
  - telegram_signal_bot.py (전략 선택 로직 추가)
  - signal_bot_trend.py (import로 변경)
  - signal_bot_reversion.py (import로 변경)
  - signal_bot_breakout.py (import로 변경)
```

---

## [v3.0.1] - 2025-10-18

### 🏗️ **Phase 4 리팩토링: Helper 함수 통합**

#### Added ✅
- **common/utils.py 생성** (공통 헬퍼 함수)
  - `bootstrap_history()` - Binance 초기 히스토리 로드
  - `buffer_to_df()` - deque → DataFrame 변환
  - `make_streams()` - WebSocket stream URL 생성
  - `qty_notional_margin()` - 수량/명목가치/마진 계산
  - `maybe_regime_alert()` - 레짐 전환 알림

#### Changed 🔄
- **Signal Bot 4개 파일에서 중복 제거**
  - ~150줄 제거
  - import로 대체

---

## [v3.0.0] - 2025-10-18

### 🏗️ **Phase 3 리팩토링: Flash Guard 이동**

#### Changed 🔄
- **Flash Guard (급등락 감지) 리팩토링**
  - Signal Bot → Trading Bot RiskManager로 이동
  - Pre-Trade Risk Check는 거래 실행 직전에 수행
  - 올바른 책임 분리 (Signal = 신호 생성 / Trading = 리스크 체크)

#### Removed ❌
- **Signal Bot 4개 파일에서 제거** (~120줄)
  - `def _tf_ms()` - 타임프레임 변환
  - `def flash_guard_update()` - 급등락 감지
  - `def flash_guard_allowed()` - 신호 허용 체크
  - `FLASHBUF`, `FLASH_PAUSE_UNTIL` 전역 변수

#### Added ✅
- **trading_executor.py - RiskManager 클래스**
  - `flash_guard_update()` 메서드
  - `flash_guard_allowed()` 메서드
  - `_tf_ms()` 메서드
  - `flash_buffers`, `flash_pause_until` 속성

#### Performance 📈
- **코드 절감**: Signal Bot 4개 파일에서 ~120줄 제거
- **중앙화**: Pre-Trade Risk Check 로직 통합
- **확장성**: RiskManager에 다른 리스크 체크 추가 용이

#### Files Changed
```
Modified:
  - telegram_signal_bot.py (Flash Guard 제거)
  - signal_bot_trend.py (Flash Guard 제거)
  - signal_bot_reversion.py (Flash Guard 제거)
  - signal_bot_breakout.py (Flash Guard 제거)
  - trading_executor.py (RiskManager에 Flash Guard 추가)

Updated:
  - docs/architecture/REFACTORING.md (Phase 3 완료 표시)
```

---

## [v3.0.0] - 2025-10-18

### 🏗️ **Phase 2 리팩토링: 공통 모듈화**

#### Added ✅
- **common/ 폴더 생성** (공통 모듈 통합)
  - `common/logger.py` (121줄) - 타입별 로깅 시스템
    - signals, trading, performance, errors, application 분류
    - 일자별 로테이션 (YYYY-MM-DD.log)
    - 오래된 로그 자동 정리 (30일)
  - `common/database.py` (190줄) - DB 연결 관리
    - get_db_connection() (컨텍스트 매니저)
    - save_signal_to_db() (멱등성 보장)
    - test_db_connection()
    - get_latest_signals()
  - `common/messaging.py` (360줄) - 텔레그램 메시징 & 포맷팅 ⭐
    - send_telegram() - 기본 전송
    - tg() - 간편 전송
    - send_alert() - 간단한 알림
    - **format_signal_alert()** - 메시지 포맷팅 (가독성 강화 핵심!)
    - beginner_block() - 초보자 설명 블록
    - round_tick() - 가격 반올림
    - _tp_from_rr() - TP 계산
  - `common/config.py` (280줄) - 환경변수 설정 관리 ⭐
    - load_config() - 환경변수에서 설정 로드
    - validate_config() - 설정 검증
    - get_bool/get_float/get_int/get_str/get_list() - 타입 안전 파싱
    - print_config() - 설정 출력
  - `indicators/` (340줄) - 기술적 지표 모듈 ⭐
    - indicators/core_indicators.py - 모든 지표 통합
    - ema(), rsi(), macd(), bb(), atr() - 개별 지표
    - add_indicators() - 모든 지표 일괄 추가
    - regime() - 시장 레짐 판단
    - TO-BE: trend_indicators.py, momentum_indicators.py 등으로 분리 예정

#### Changed 🔄
- **Signal Bot 파일 (4개)**
  - 로깅: `common.logger` 사용
  - DB 연결: `common.database` 사용
  - 텔레그램 & 포맷팅: `common.messaging` 사용
  - 설정 로드: `common.config` 사용
  - 지표 계산: `indicators` 사용 ⭐ NEW!
  - 중복 코드 약 1200줄+ 제거 (지표 포함)
  
- **기타 봇 파일 (6개)**
  - 로깅: `common.logger` 사용
  - DB/메시징: 공통 모듈 사용
  
- **Dockerfiles (3개)**
  - `common/` 폴더 복사 추가
  - Dockerfile, Dockerfile.ensemble, Dockerfile.trading

#### Fixed 🐛
- 오타 수정: "캨들" → "캔들" (4개 파일)

#### Documentation 📚
- 업데이트: `docs/architecture/REFACTORING.md`
  - Phase 2 완료 표시
  - 공통 모듈 구조 추가
  - 성과 지표 추가

#### Performance 📈
- **코드 절감**: 약 1600줄+ → 40줄 + 1291줄 (모듈) = **약 500줄+ 순 절감**
- **유지보수성**: 로깅/DB/메시징/포맷팅/설정/지표 변경 시 1개 파일만 수정
- **일관성**: 모든 봇이 동일한 로깅/DB/메시징/설정/지표 사용
- **가독성**: 메시지 포맷팅 템플릿 통합 관리 (사용자 경험 강화)
- **안전성**: 설정 검증 자동화 (validate_config)
- **확장성**: 지표 추가/수정이 indicators/core.py 한 곳에서 가능

#### Files Changed
```
Modified:
  - telegram_signal_bot.py
  - signal_bot_trend.py
  - signal_bot_reversion.py
  - signal_bot_breakout.py
  - ensemble_bot.py
  - trading_manager.py
  - trading_executor.py
  - backtest/data_downloader.py
  - backtest/backtest_engine.py
  - backtest/backtest_reporter.py

Added:
  - common/__init__.py
  - common/logger.py (121 lines)
  - common/database.py (190 lines)
  - common/messaging.py (360 lines) ⭐ 메시지 포맷팅 포함
  - common/config.py (280 lines) ⭐ 환경변수 설정 관리
  - indicators/__init__.py
  - indicators/core_indicators.py (340 lines) ⭐ 기술적 지표 통합

Updated:
  - Dockerfile
  - Dockerfile.ensemble
  - Dockerfile.trading
  - docs/architecture/REFACTORING.md
```

---

## [v2.0.0] - 2025-10-17

### 🎯 리팩토링: Signal Bot → Trading Bot 포지션 추적 분리

#### Added ✅
- **PositionTracker 클래스** (`trading_executor.py`)
  - 포지션 추적 및 TP/SL 관리
  - 3가지 모드 지원: BACKTEST, PAPER, LIVE
  - TP1/TP2 부분 익절 지원
  - Trail Stop 기능
  - 일일 PnL 및 목표 달성률 계산
- **통합 구조** (상용 표준 적용)
  - `trading_executor.py`: 주문 실행 + 포지션 추적
  - `trading_manager.py`: 매매 오케스트레이터

#### Changed 🔄
- **Signal Bots (4개 파일)**
  - 포지션 추적 로직 제거
  - 신호 생성 전용으로 단순화
  - `track_new_signal()` 호출 주석 처리
  - `touch_check()` 호출 주석 처리
  - `goal_progress_text()` 함수 제거
  - 텔레그램 stats 명령어 안내 메시지로 변경

#### Removed ❌
- Signal Bot 전역 변수
  - `ACTIVE_SIG` 딕셔너리
  - `DAILY_PNL` 변수
- Signal Bot 함수
  - `_tp_from_rr()`
  - `track_new_signal()`
  - `touch_check()`
  - `goal_progress_text()`

#### Documentation 📚
- 추가: `docs/REFACTORING.md` - 리팩토링 가이드
- 업데이트: `README.md` - 아키텍처 섹션
- 업데이트: `docs/TRADING_EXECUTOR.md` - PositionTracker 섹션
- 추가: `test_refactoring.py` - 검증 테스트

#### Migration 🔄
- **Breaking Change**: Signal Bot은 더 이상 포지션 추적 안 함
- Trading Bot의 PositionTracker 사용 필수
- 환경변수 추가: `TP1_RR`, `TP2_RR`, `ENABLE_TP_TRAIL`, `TRAIL_AFTER_TP1`

#### Files Changed
```
Modified:
  - trading_executor.py (+150 lines) ⭐ PositionTracker 추가
  - trading_manager.py (renamed from trading_bot.py)
  - telegram_signal_bot.py (-100 lines)
  - signal_bot_trend.py (-100 lines)
  - signal_bot_reversion.py (-100 lines)
  - signal_bot_breakout.py (-100 lines)
  - README.md
  - docker-compose.yml
  - docs/TRADING_EXECUTOR.md

Added:
  - docs/REFACTORING.md
  - test_refactoring.py
  - CHANGELOG.md

Renamed:
  - trading_bot.py → trading_manager.py
```

---

## [v1.0.0] - 2025-10-16

### 🚀 Trading Manager 초기 구현

#### Added
- **Trading Manager** (`trading_manager.py`)
  - 7개 전략 선택 시스템
  - 3가지 모드: BACKTEST, PAPER, LIVE
  - TradingExecutor 통합
  - 신호 읽기 및 오케스트레이션

- **Trading Executor** (`trading_executor.py`)
  - 바이낸스 주문 실행
  - Paper Trading 시뮬레이션
  - Position Tracker 통합 ⭐
  - DB 저장 (trades 테이블)

#### Documentation
- `docs/TRADING_BOT_SPEC.md`
- `docs/TRADING_EXECUTOR.md`
- `docs/TRADING_DECISION.md`

---

## [v0.13.3] - 2025-10-15

### Signal Bots 완성

#### Added
- 6개 Signal Bot 구현
  - SCALPING (1m)
  - DAYTRADE (5m)
  - SWING (15m)
  - TREND (1h)
  - REVERSION (5m)
  - BREAKOUT (15m)

- Ensemble Bot (앙상블 통합)
  - 6개 신호 가중치 통합
  - decisions 테이블 저장

#### Features
- 초보자 설명 블록
- Flash Guard (급등락 감지)
- 멀티타임프레임 확인
- TP1/TP2 부분 익절
- 일일 목표 추적

---

## [v0.13.0] - 2025-10-01

### 초기 개발

#### Added
- PostgreSQL 연동
- WebSocket 실시간 데이터
- 텔레그램 알림
- 기본 지표 (EMA, RSI, MACD, BB, ATR)

---

## 버전 관리 규칙

- **Major (X.0.0)**: 아키텍처 변경, Breaking Changes
- **Minor (0.X.0)**: 새로운 기능 추가
- **Patch (0.0.X)**: 버그 수정, 문서 업데이트

---

**Last Updated:** 2025-10-19
