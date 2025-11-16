# PHASE16: REAL Paper Mode 실행 가이드

## 📋 개요

PHASE16은 PHASE15에서 확정된 최적 파라미터를 사용하여 **실제 엔진 기반의 12시간 Paper Trading**을 자동화하는 단계입니다.

### 목표
- ✅ 실제 WebSocket 피드 사용
- ✅ 실제 PaperBroker 실행
- ✅ 실제 Redis dedup/cooldown/signal 처리
- ✅ 12시간 안정적 실행
- ✅ 자동 모니터링 및 리포트 생성

### 핵심 원칙
- ❌ 랜덤 시뮬레이션 금지
- ❌ 가짜 메트릭 금지
- ✅ 기존 엔진 100% 재사용
- ✅ 래퍼 스크립트만 추가

---

## 🏗️ 아키텍처

### 기존 인프라 (PHASE14~15)

```
┌─────────────────────────────────────────────────────────┐
│ PHASE14: Unified Engine                                 │
│ ├─ execution/engine.py (공통 루프)                      │
│ ├─ execution/adapters/brokers.py                        │
│ │  ├─ SimBroker (백테스트)                              │
│ │  ├─ PaperBroker (페이퍼)                              │
│ │  └─ LiveBroker (실거래)                               │
│ ├─ execution/executors/paper.py (가상 주문)            │
│ └─ collectors/websocket_collector.py (실시간 피드)     │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE15: Tuning Pipeline                                │
│ ├─ tuning/tuning_core.py (Optuna 기반)                 │
│ ├─ configs/scalping/active.yml (Best Trial #8)         │
│ │  ├─ RR: 1.254                                        │
│ │  ├─ ATR_SL_MULT: 1.272                               │
│ │  └─ MAX_HOLD_MINUTES: 23                             │
│ └─ analytics/scorecard/generator.py (결과 분석)        │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE16: REAL Paper Mode (NEW)                          │
│ ├─ scripts/run_paper.py (메인 러너)                     │
│ ├─ scripts/check_paper.py (상태 확인)                   │
│ ├─ scripts/monitor_paper.py (실시간 모니터링)          │
│ └─ scripts/generate_report_phase16.py (리포트 생성)    │
└─────────────────────────────────────────────────────────┘
```

### PHASE16 실행 흐름

```
[시작]
  ↓
[1] Config 로드 (PHASE15 Best 파라미터 적용)
  ↓
[2] 어댑터 생성 (PaperBroker + WebSocketCollector + LiveClock)
  ↓
[3] 전략 로드 (scalping)
  ↓
[4] Engine.run() 실행 (12시간)
  │  ├─ WebSocket 실시간 피드 수집
  │  ├─ 신호 생성 및 주문 실행
  │  ├─ Redis dedup/cooldown/signal 처리
  │  └─ 포지션 추적 및 PnL 계산
  ↓
[5] Scorecard 생성 (broker.closed_trades 기반)
  ↓
[6] 리포트 생성 (PHASE15 OOS 비교)
  ↓
[종료]
```

---

## 🔧 필수 인프라

### 1. Redis
Paper Mode는 Redis를 필수로 사용합니다.

**확인 방법**:
```bash
redis-cli ping
# 응답: PONG
```

**설치 (Docker)**:
```bash
docker-compose up -d redis
```

**설치 (로컬)**:
```bash
# macOS
brew install redis
redis-server

# Ubuntu
sudo apt-get install redis-server
redis-server

# Windows
# https://github.com/microsoftarchive/redis/releases
```

### 2. WebSocket 연결
실시간 시장 데이터가 필요합니다.

**확인 방법**:
```bash
python scripts/check_paper.py
# Redis 연결 상태 확인
```

### 3. 가상환경
```bash
# 활성화 (Linux/Mac)
source trading_bot_env/bin/activate

# 활성화 (Windows)
.\trading_bot_env\Scripts\activate
```

---

## 🚀 사용 방법

### [기본] 12시간 Paper Trading 실행

```bash
python scripts/run_paper.py
```

**기본값**:
- Strategy: `scalping`
- Symbol: `BTCUSDT`
- Timeframe: `3m` (PHASE15 Best)
- Duration: `12.0` hours

### [커스텀] 파라미터 지정

```bash
python scripts/run_paper.py \
  --strategy scalping \
  --symbol BTCUSDT \
  --timeframe 3m \
  --duration-hours 12
```

### [테스트] 짧은 실행

```bash
python scripts/run_paper.py --duration-hours 0.5  # 30분
```

---

## 📊 모니터링

### [터미널 1] Paper Trading 실행
```bash
python scripts/run_paper.py
```

### [터미널 2] 실시간 모니터링
```bash
python scripts/monitor_paper.py
```

**출력 예시**:
```
================================================================================
⏰ 2024-11-16 23:15:30 | 갱신 #5
================================================================================

📊 Redis 키 현황:
   Dedup: 450개
   Cooldown: 3개
   Signal: 12개

📁 최신 Run: 20241116_230000_phase16
   Trades: 2
   Winrate: 50.0%
   PF: 1.23

================================================================================
⏳ 10초 후 갱신... (Ctrl+C로 종료)
```

### [터미널 3] 상태 확인 (1회)
```bash
python scripts/check_paper.py
```

---

## 📈 결과 분석

### 12시간 후 리포트 생성

```bash
python scripts/generate_report_phase16.py --latest
```

### 리포트 확인

```bash
cat docs/PHASE16/PHASE16_PAPER_REPORT.md
```

### Scorecard 상세 확인

```bash
# 최신 run의 scorecard 확인
ls -la scorecards/paper_phase16/*/scorecard.*
```

---

## 📁 출력 파일 구조

```
scorecards/paper_phase16/
└── {run_id}/
    ├── effective_config.yml      # 실행 시 사용된 설정
    ├── scorecard.csv             # 성능 지표 (CSV)
    ├── scorecard.md              # 성능 지표 (Markdown)
    └── trades.log                # 거래 로그 (선택)

docs/PHASE16/
└── PHASE16_PAPER_REPORT.md       # 최종 리포트
```

---

## ⚠️ 알려진 제한사항

### 1. 실시간 데이터 필요
- Paper Mode는 실시간 WebSocket 피드 필수
- 짧은 테스트는 의미 없음 (최소 1~2시간 권장)

### 2. 거래 수 변동성
- 시장 상황에 따라 거래 수가 크게 변할 수 있음
- PHASE15 OOS 결과와 다를 수 있음

### 3. 슬리피지 시뮬레이션
- Paper Mode는 현재 가격에서 즉시 체결 가정
- 실제 Live와 다를 수 있음

### 4. 수수료 계산
- Paper Mode 수수료: 0.04% (설정 가능)
- 실제 Binance 수수료와 다를 수 있음

---

## 🔍 트러블슈팅

### Redis 연결 실패
```bash
# 확인
redis-cli ping

# 재시작
docker-compose restart redis
```

### WebSocket 연결 실패
```bash
# 로그 확인
tail -f logs/application.log | grep -i websocket

# 네트워크 확인
ping api.binance.com
```

### Scorecard 생성 실패
```bash
# 거래 내역 확인
python scripts/check_paper.py

# 로그 확인
tail -f logs/application.log | grep -i scorecard
```

---

## 📋 체크리스트

Paper Trading 시작 전 확인:

- [ ] Redis 실행 중 (`redis-cli ping` → PONG)
- [ ] 가상환경 활성화
- [ ] `configs/scalping/active.yml` 확인 (PHASE15 Best 파라미터)
- [ ] `scripts/run_paper.py` 실행 가능 확인
- [ ] 충분한 디스크 공간 (로그, scorecard)
- [ ] 네트워크 안정성 (12시간 연속)

---

## 🎯 다음 단계 (PHASE17)

### Paper Trading 검증 후

**검증 통과 시**:
1. Live Trading 소액 시작 (10% 자본)
2. 1주일 모니터링
3. 점진적 스케일업

**검증 실패 시**:
1. Paper Trading 기간 연장
2. PHASE15 재튜닝
3. 시장 환경 재분석

---

## 📞 지원

문제 발생 시:
1. `scripts/check_paper.py` 실행하여 상태 확인
2. `logs/application.log` 확인
3. Redis 상태 확인
4. 네트워크 연결 확인

---

*마지막 업데이트: 2024-11-16*
