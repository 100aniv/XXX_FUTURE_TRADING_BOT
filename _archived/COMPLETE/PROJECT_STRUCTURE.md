# 📁 프로젝트 구조

**Last Updated**: 2025-10-19

---

## 🌳 **디렉토리 구조**

```
future_alarm_bot/
├── 📁 strategies/                  # 전략 로직 모듈 ⭐ NEW
│   ├── __init__.py
│   ├── scalping.py                 # 스캘핑 (1분/3분)
│   ├── daytrade.py                 # 단타 (5분)
│   ├── swing.py                    # 스윙 (15분)
│   ├── trend.py                    # 추세 (1시간)
│   ├── reversion.py                # 반전 (5분)
│   └── breakout.py                 # 돌파 (15분)
│
├── 📁 common/                      # 공통 모듈 ⭐
│   ├── __init__.py
│   ├── logger.py                   # 로깅 시스템 (타입별 분류)
│   ├── database.py                 # DB 연결 및 신호 저장
│   ├── messaging.py                # 텔레그램 메시징 + 포맷팅
│   ├── config.py                   # 환경변수 → 설정
│   ├── calculations.py             # 계산 함수 (포지션, 레버리지)
│   └── utils.py                    # 유틸리티 함수 (공통 헬퍼)
│
├── 📁 indicators/                  # 기술적 지표 모듈 ⭐
│   ├── __init__.py
│   └── core_indicators.py          # 모든 지표 통합
│
├── 📁 signals/                     # 신호 생성 모듈 ⭐
│   ├── __init__.py
│   ├── signal_generator.py         # 신호 생성 로직
│   └── signal_storage.py           # DB 저장
│
├── 📁 collector/                   # 데이터 수집 모듈 ⭐
│   ├── __init__.py
│   ├── websocket_collector.py      # WebSocket 실시간 수집
│   └── rest_collector.py           # REST API 수집
│
├── 📁 execution/                   # 매매 실행 모듈 ⭐ UPDATED (2025-10-19)
│   ├── __init__.py
│   ├── engine.py                   # ⭐ TradingEngine (통합 엔진)
│   ├── data_sources/               # 데이터 소스 플러그인
│   │   ├── backtest.py             # CSV/Parquet 재생
│   │   └── live.py                 # 실시간 시세
│   ├── executors/                  # 주문 실행 플러그인
│   │   ├── simulation.py           # 백테스트 체결
│   │   ├── paper.py                # 가상 체결
│   │   └── live.py                 # 실제 체결
│   ├── position_sizer.py           # PositionSizer 클래스
│   ├── risk_manager.py             # RiskManager 클래스
│   ├── executor_wrapper.py         # 하위 호환성 래퍼
│   └── manager.py                  # 하위 호환성 stub
│
├── 📁 backtest/                    # 백테스트 모듈
│   ├── data_downloader.py          # 히스토리컬 데이터 다운로드
│   ├── backtest_engine.py          # 백테스트 엔진
│   └── backtest_reporter.py        # 리포트 생성
│
├── 📁 docs/                        # 문서 (카테고리별 분류)
│   ├── 📁 setup/                   # 설정 가이드
│   ├── 📁 strategy/                # 전략 문서
│   ├── 📁 backtest/                # 백테스트 가이드
│   ├── 📁 implementation/          # 구현 계획
│   ├── 📁 architecture/            # 시스템 구조
│   ├── 📁 deployment/              # 배포 전략
│   ├── 📁 reference/               # 참고 자료
│   └── README.md                   # 문서 인덱스
│
├── 📁 tests/                       # 테스트 파일
│   ├── test_*.py                   # 각종 테스트
│   ├── check_*.py                  # 확인 스크립트
│   └── show_*.py                   # 조회 스크립트
│
├── 📁 cleanup/                     # 정리된 파일
│   └── *.bat                       # 불필요한 배치 파일
│
├── 📁 logs/                        # 로그 파일
│
├── 📁 data/                        # 데이터 저장소
│   └── historical/                 # 히스토리컬 데이터
│
├── 📁 results/                     # 백테스트 결과
│
├── 📁 reports/                     # 리포트 파일
│
├── 📄 **핵심 실행 파일**
│   ├── main.py                      # 메인 시그널 봇 (통합) ⭐
│   ├── telegram_signal_bot.py      # 시그널 봇 (레거시)
│   ├── signal_bot_trend.py         # TREND 전략 (레거시)
│   ├── signal_bot_reversion.py     # REVERSION 전략 (레거시)
│   ├── signal_bot_breakout.py      # BREAKOUT 전략 (레거시)
│   ├── ensemble_bot.py             # 앙상블 통합 봇
│   ├── run_trading.py              # 매매 실행 스크립트 ⭐ NEW
│   ├── trading_manager.py          # ⚠️ Deprecated (→ execution/manager.py)
│   └── trading_executor.py         # ⚠️ Deprecated (→ execution/)
│
├── 📄 **설정 파일**
│   ├── .env                        # 환경 변수 (gitignore)
│   ├── env.example                 # 환경 변수 예시
│   ├── config_*.txt                # 전략별 설정 (6개)
│   ├── docker-compose.yml          # Docker Compose 설정
│   ├── Dockerfile*                 # Docker 이미지 설정
│   └── requirements.txt            # Python 패키지
│
└── 📄 **문서**
    ├── README.md                   # 프로젝트 개요
    └── PROJECT_STRUCTURE.md        # 이 파일
```

---

## 📋 **주요 파일 설명**

### **1. 시그널 봇 (6개)**
| 파일 | 전략 | 타임프레임 | 설정 파일 |
|------|------|-----------|----------|
| `telegram_signal_bot.py` | SCALPING | 1분 | `config_scalp.txt` |
| *(동일 파일)* | DAYTRADE | 5분 | `config_intraday.txt` |
| *(동일 파일)* | SWING | 15분 | `config_swing.txt` |
| `signal_bot_trend.py` | TREND | 1시간 | `config_trend.txt` |
| `signal_bot_reversion.py` | REVERSION | 5분 | `config_reversion.txt` |
| `signal_bot_breakout.py` | BREAKOUT | 15분 | `config_breakout.txt` |

### **2. 매매 실행 모듈 (execution/)** ⭐ NEW
- **`executor.py`**: 주문 실행 엔진 (BACKTEST/PAPER/LIVE)
- **`position_sizer.py`**: 포지션 크기 동적 계산
- **`risk_manager.py`**: 리스크 관리 (Flash Guard 포함)
- **`position_tracker.py`**: 포지션 추적 및 TP/SL 관리
- **`manager.py`**: 매매 오케스트레이션 (순수 함수)
- **`run_trading.py`**: 매매 실행 스크립트 (while 루프)

**특징:**
- ✅ 단일 책임 원칙 (SRP)
- ✅ 순수 함수형 설계
- ✅ 테스트 용이성
- ✅ 상용급 아키텍처

### **3. 신호 생성 모듈 (signals/)**
- **`signal_generator.py`**: 신호 생성 및 검증
- **`signal_storage.py`**: DB 저장 로직

### **4. 데이터 수집 모듈 (collector/)**
- **`websocket_collector.py`**: WebSocket 실시간 데이터
- **`rest_collector.py`**: REST API 히스토리컬 데이터

### **5. 앙상블 봇**
- **`ensemble_bot.py`**: 6개 전략 신호 통합 → 최종 결정

### **6. 공통 모듈 (common/)**
- **`logger.py`**: 타입별 로깅 (signals/trading/performance/errors)
- **`database.py`**: DB 연결 관리 + 신호 저장
- **`messaging.py`**: 텔레그램 메시징 + 메시지 포맷팅
- **`config.py`**: 환경변수 설정 관리 + 검증
- **`calculations.py`**: 포지션/레버리지 계산 함수
- **`utils.py`**: 공통 유틸리티 함수 (진행 예정)

### **7. 백테스트 모듈**
- **`backtest/data_downloader.py`**: Binance 데이터 다운로드
- **`backtest/backtest_engine.py`**: 백테스트 실행 엔진
- **`backtest/backtest_reporter.py`**: HTML/PDF 리포트 생성

### **8. 설정 파일**
- **`.env`**: 환경 변수 (DATABASE_URL, API 키 등)
- **`config_*.txt`**: 전략별 파라미터 (ATR, RR, 레버리지 등)
- **`docker-compose.yml`**: 전체 시스템 컨테이너 설정

---

## 📚 **문서 구조**

자세한 내용은 [`docs/README.md`](docs/README.md) 참고

### **카테고리**
1. **Setup** - 초기 설정 및 배포
2. **Strategy** - 트레이딩 전략
3. **Backtest** - 백테스트 가이드
4. **Implementation** - 구현 계획
5. **Architecture** - 시스템 구조
6. **Deployment** - 배포 전략
7. **Reference** - 참고 자료

---

## 🚀 **빠른 시작**

### **1. 환경 설정**
```bash
# .env 파일 생성
copy env.example .env
notepad .env  # DATABASE_URL, STRATEGY_SELECTOR 등 설정

# PostgreSQL 시작
docker-compose up -d postgres
```

### **2. 시그널 봇 실행 (Docker)**
```bash
# 전체 봇 시작
docker-compose up -d

# 특정 봇만 시작
docker-compose up -d postgres scalp-bot trend-bot ensemble-bot
```

### **3. 매매 실행 (로컬)**
```bash
# execution 모듈 사용 (권장) ⭐
python run_trading.py

# .env 설정
STRATEGY_SELECTOR=ensemble  # or trend, reversion, etc.
TRADING_MODE=paper          # or backtest, live
```

### **4. 백테스트 실행**
```bash
# 데이터 다운로드
python backtest/data_downloader.py --start 2024-07-01 --end 2024-10-17

# 백테스트 실행
python backtest/backtest_engine.py --strategy scalping

# 리포트 생성
python backtest/backtest_reporter.py --input results/*.json
```

---

## 🔧 **개발 워크플로우**

### **1. 신규 전략 추가**
1. `signal_bot_[전략명].py` 생성
2. `config_[전략명].txt` 생성
3. `docker-compose.yml`에 컨테이너 추가
4. `ensemble_bot.py`에 가중치 추가

### **2. 백테스트 파라미터 튜닝**
1. `config_*.txt` 수정
2. `python backtest/backtest_engine.py` 실행
3. 결과 분석 후 최적 파라미터 선정

### **3. 코드 수정**
1. `trading_executor.py` 또는 `trading_manager.py` 수정
2. `tests/` 폴더에 테스트 추가
3. 백테스트로 검증
4. Paper Trading으로 실시간 검증
5. Live Trading 배포

---

## 📊 **데이터 흐름**

```
시그널 봇 (6개)
    ↓
monitoring.signals (DB)
    ↓
ensemble_bot.py
    ↓
trading.decisions (DB)
    ↓
run_trading.py ⭐
    ↓
execution/manager.py
    ├─ fetch_signals()
    ├─ convert_to_order()
    └─ process_trades()
    ↓
execution/executor.py
    ├─ position_sizer.calculate()
    ├─ risk_manager.check_order()
    └─ execute_order()
    ↓
trading.trades (DB)
```

---

## ⚙️ **환경 변수**

주요 환경 변수 (`.env` 파일):

```ini
# 전략 선택
STRATEGY_SELECTOR=daytrade  # scalping, daytrade, swing, trend, reversion, breakout, ensemble

# 매매 모드
TRADING_MODE=backtest  # backtest, paper, live

# DB
DATABASE_URL=postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db

# Binance API (Live 모드 시 필수)
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# 리스크 관리
EQUITY_USDT=10000
RISK_PER_TRADE=0.01
MAX_POSITIONS=5
```

---

## 🧪 **테스트**

테스트 파일은 `tests/` 폴더에 정리되어 있습니다:

- `test_*.py` - 기능 테스트
- `check_*.py` - 상태 확인
- `show_*.py` - 데이터 조회

---

## 📝 **업데이트 이력**

- **2025-10-19 (v4.1.0)**: 통합 엔진 아키텍처 완성 ⭐⭐
  - execution.engine.TradingEngine 구현
  - 단일 엔진 + 모드별 플러그인 교체 구조
  - data_sources/ + executors/ 분리
  - 백테스트 완전 통합 (strategies 연동)
  - main.py 리팩토링 (백테스트/실시간 분리)

- **2025-10-19 (v4.0.0)**: execution/ 모듈 리팩토링 (Phase 9) ⭐
  - trading_executor.py → 4개 파일 분할
  - trading_manager.py → manager.py 순수 함수화
  - run_trading.py 재작성
  - 단일 책임 원칙 적용
  - 완전 모듈화 완료

- **2025-10-19 (v3.1.0)**: 전략 로직 분리 (Phase 5)
  - strategies/ 모듈 생성 (6개 전략)
  - Signal Bot 얇아짐 (~250줄 제거)
  - 전략 독립 테스트 가능

- **2025-10-18 (v3.0.1)**: Helper 함수 통합 (Phase 4)
  - common/utils.py 생성
  - Signal Bot 중복 제거 (~150줄)
  
- **2025-10-18 (v3.0.0)**: Flash Guard 리팩토링 (Phase 3)
  - Signal Bot → Trading Bot RiskManager로 이동
  - Pre-Trade Risk Check 중앙화
  
- **2025-10-18 (v3.0.0)**: 공통 모듈화 (Phase 2)
  - common/ 폴더 생성 (logger, database, messaging, config, calculations)
  - indicators/ 모듈 분리
  - 중복 코드 대폭 제거

- **2025-10-18**: 프로젝트 구조 정리
  - 문서 카테고리별 분류
  - 테스트 파일 별도 폴더로 이동
  - README 및 문서 링크 업데이트

---

**문의**: 프로젝트 관련 문의는 [docs/README.md](docs/README.md) 참고
