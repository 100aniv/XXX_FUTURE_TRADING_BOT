# PHASE7-3 마스터 플랜: 운영 안정성 강화 (Live 모드 준비)

**최종 업데이트**: 2025-11-13  
**현행 코드(b84c03c)**: 슬리피지 미구현, Manager 상태 DB 미구현, SL 거래소 등록만 사용  
**상태**: ⚠️ 7-2 중단으로 7-3 항목은 모두 TO-BE (미구현)

## 📌 Executive Summary (TL;DR)

- **역할**: Live 전환 전 운영 안정성 표준 수립 문서(종료/복원/헬스/모니터링).
- **현행**: 안정 버전(b84c03c). 상태 DB/TP 거래소 등록 미구현 → 계획 보류, 운영 표준만 확정.
- **방침**: Paper/Live 동형 운영, 종료/재시작 시 상태 복원 100%, 헬스체크·알림 체계 강화.
- **스냅샷**: 최근 2h/24h 지표는 아래 Standard Snapshot 및 SMOKE_TEST_MONITOR.md 참조.

## 🔎 Quick Nav

- [배경/의도(원래 계획)](#-배경의도-overview--원래-계획-참고용)
- [목표](#-목표-goals)
- [범위](#-범위-scope-in)
- [수용 기준/체크리스트](#-수용-기준-게이트)
- [업데이트 로그](#-업데이트-로그)

## 📊 Standard Snapshot (Paper)

- **최근 2시간**: closed=818, win_rate=38.3%, avg_pnl=-0.24%, min=-31.01%, max=+62.25, >8% 손실=29, 무결성 OK(양방향 0, OPEN 11)
- **최근 24시간**: closed=1,550, win_rate=35.8%, avg_pnl=-0.38%, min=-32.47, max=+70.40, >8% 손실=64, 무결성 OK(양방향 0)
- 출처: SMOKE_TEST_MONITOR.md 실측 스냅샷 (2025-11-13)

## ⚠️ 현재 상태 스냅샷 (최근 30/60분 · Paper)

- **60분**: closed=394, win_rate=31.2%, >8% 손실=20건  
  - Exit breakdown: SL 201건(avg -3.83%, min -16.65%), TP1 196건(avg +2.28%, min -4.86%), ONE_WAY_MODE 2건
- **30분**: closed=151, win_rate=26.5%, avg_pnl=-0.84%, min=-12.05%, max=+25.30%  
- **무결성**: 중복 진입 0, 양방향 OPEN 0, OPEN=13

---

## ✅ 수용 기준 (게이트)

- Graceful 종료: 작업 중단 시 누락 이벤트/오더 0건, 종료 로그/텔레그램 알림 필수
- 재기동 복원: 재시작 직후 포지션/주문 상태 일치율 100%, 유령 포지션 0
- 헬스체크: unhealthy 자동 복구(재기동 또는 격리) 성공률 100%
- 모니터링: 대시보드/알림이 5분 내 이상 감지, 경고→크리티컬 단계화
- 무결성: 중복 진입 0, 양방향 동시 0, 미결 주문 유실 0

## 📋 체크리스트

- 종료 훅 구현(try/finally)과 큐 drain → 오더 cancel/replace 정책 적용
- 상태 복원 순서 정의: Symbols → Positions → Orders → Engine clocks
- Docker healthcheck + restart policy + backoff 설정 확인
- 텔레그램/로그 레벨 및 샘플링 정책 확정(과다/누락 방지)
- Redis/DB 네임스페이스: `{ns}:{env}:{run_id}:*` 준수

## 🔗 참조 문서

- SYSTEM_OPERATIONS_ANALYSIS.md
- PHASE7_ALGORITHM_BEST.md (MASTER)
- SMOKE_TEST_MONITOR.md

## 📝 업데이트 로그

- 2025-11-13: 2차 표준화(수용 기준/체크리스트/참조 추가)

---

## 배경/의도 (Overview) — 원래 계획 (참고용)

PHASE 7-1/7-2 완료 후 성과 개선 완료. 하지만 **운영 안정성** 부족:
- 컨테이너 재시작 시 포지션 유실 위험
- Live 모드: Binance SL 주문 유실
- 🚨 **TP 거래소 미등록**: 프로그램 종료 시 TP 미작동 (수익 기회 손실)
- 헬스체크 부실 (튜너 Unhealthy 방치)
- 모니터링 없음 (Dashboard, Alert)
- 초기화 옵션 없음 (테스트 목적 재시작 불편)

Live 운영을 위한 **필수 안전장치** 구축.

**PHASE7-2 연기 항목 통합:**
- 항목 7 (--reset 옵션): Graceful Shutdown 로직과 통합
- TP 거래소 등록: Live 모드 안전장치

**참고**: [PHASE7_ALGORITHM_BEST.md](PHASE7_ALGORITHM_BEST.md) - 앙상블 시스템 알고리즘 종합 개선안

## 목표 (Goals)

- **Graceful Shutdown**: 종료 전 모든 포지션 정리
- **--reset 옵션**: 테스트 초기화 지원 (PHASE7-2 항목 7 통합)
- **TP 거래소 등록**: 프로그램 종료해도 TP 작동 보장 (Live 안전)
- **State Recovery**: 재시작 시 포지션/주문 동기화
- **Docker Healthcheck**: DB/Redis/API 연결 검증
- **Monitoring Dashboard**: Grafana 기본 대시보드
- **컨테이너 재시작 안전**: 포지션 유실 0건

## 범위 (Scope, In)

### 1. Graceful Shutdown + --reset 옵션 (1.5일) ⭐ PHASE7-2 항목 7 통합

**문제**:
- Daily Loss Limit 도달 → `sys.exit(1)` → 강제 종료
- OPEN 포지션 방치
- Live: Binance SL/TP 주문 남음
- **테스트 초기화**: 기존 포지션 남아있어 깨끗한 시작 불가

**구현**:
#### A. Graceful Shutdown (기본)
- 종료 신호 핸들러 (SIGTERM, SIGINT)
- 포지션 정리 순서:
  1. 신규 진입 중단
  2. OPEN 포지션 시장가 청산
  3. Binance SL/TP 주문 취소 (Live)
  4. 상태 저장 (DB + Redis)
  5. 정상 종료

#### B. --reset 옵션 (초기화 모드) ⭐ PHASE7-2 항목 7
- **용도**: 테스트 목적 초기화 (깨끗한 시작)
- **Paper 모드**:
  1. DB OPEN 포지션 강제 청산 (status='CLOSED', exit_reason='RESET')
  2. equity → config.initial_capital
  3. 새 run_id 생성
  4. Redis 상태 초기화
- **Live 모드**: --reset 금지 (에러 발생)
  - 이유: 거래소에 실제 포지션 존재
  - 절차: 수동 청산 후 시작

**사용 예시**:
```bash
# Paper 재시작 (기본, 포지션 복원)
docker-compose restart trading_bot_paper_ensemble

# Paper 초기화 (테스트 목적)
docker-compose run --rm -e RESET_MODE=true trading_bot_paper_ensemble

# Live는 --reset 금지
python main.py --mode live --reset  # ERROR: Live 모드는 수동 청산 필요
```

**영향 파일**:
- `main.py` (신호 핸들러 + argparse --reset)
- `execution/engine.py` (shutdown 메서드 + reset_mode 처리)
- `execution/adapters/brokers.py` (LiveBroker 주문 취소)
- `docker-compose.yml` (RESET_MODE 환경변수 지원)

**로직 공유**:
- Graceful Shutdown과 --reset은 동일한 "포지션 청산" 로직 재사용
- 차이점: --reset은 DB 강제 청산 + equity 초기화 추가

### 2. TP 거래소 등록 (1일) 🚨 높은 우선순위

**문제 (2025-11-11 SYSTEM_OPERATIONS_ANALYSIS.md)**:
- 현재: SL만 거래소 등록 ✅, TP는 프로그램 메모리 ❌
- 위험: 프로그램 종료 시 TP 미작동 → 수익 기회 손실
- 시나리오:
  ```
  1. BTCUSDT LONG @ $50,000
  2. SL $49,500 (거래소) ✅
  3. TP1 $51,000 (메모리) ❌
  4. 프로그램 크래시
  5. 가격 $51,500 도달 → TP 미작동
  6. 가격 반전 → SL $49,500 터짐
  7. 손실: $1,500 (이익 기회 + 손실)
  ```

**구현 (Option C: 하이브리드)**:
```python
# execution/adapters/brokers.py (LiveBroker)
def create_tp_order(self, position: dict, tp_price: float, qty_pct: float = 100) -> dict:
    """
    TP 주문 등록 (Binance TAKE_PROFIT_MARKET)
    
    Args:
        position: 포지션 정보 {'id': int, 'symbol': str, 'side': str, 'qty': float}
        tp_price: TP 가격
        qty_pct: 청산 비율 (50 = 50% 청산)
    
    Returns:
        {'success': bool, 'order_id': int}
    """
    try:
        symbol = position['symbol']
        side = position['side']
        qty = position['qty'] * (qty_pct / 100)
        
        close_side = 'SELL' if side == 'LONG' else 'BUY'
        
        tp_order = self.client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type='TAKE_PROFIT_MARKET',
            stopPrice=tp_price,
            quantity=qty,
            positionSide='BOTH',
            reduceOnly=True  # 포지션 감소만
        )
        
        if not hasattr(self, 'tp_orders'):
            self.tp_orders = {}
        self.tp_orders[position['id']] = tp_order['orderId']
        
        logger.info(f"✅ [LIVE] TP 주문 등록: {symbol} @ ${tp_price:.2f} ({qty_pct}%)")
        return {'success': True, 'order_id': tp_order['orderId']}
        
    except BinanceAPIException as e:
        logger.error(f"❌ [LIVE] TP 주문 등록 실패: {e}")
        return {'success': False, 'error': str(e)}

# execution/engine.py (진입 시 호출)
if mode == "live":
    # SL 등록 (기존)
    broker.create_sl_order(...)
    
    # TP1 등록 (신규, 50%)
    if tp_levels.get('TP1'):
        broker.create_tp_order(
            position={'id': position_id, 'symbol': symbol, 'side': side, 'qty': qty},
            tp_price=tp_levels['TP1'],
            qty_pct=50
        )
    
    # TP2는 프로그램 관리 (유연성 유지)
```

**장점**:
- SL + TP1 거래소 보호 → 최소 수익 보장
- TP2, Trailing은 프로그램 관리 → 유연성 유지
- 프로그램 종료해도 TP1 50% 작동

**단점**:
- 비정상 종료 시 TP2 손실 (허용 가능)

**영향 파일**:
- `execution/adapters/brokers.py` (LiveBroker.create_tp_order 추가)
- `execution/engine.py` (진입 시 TP1 거래소 등록)
- `config.yml` (tp_exchange_registration 설정)

**수용 기준**:
- Live 모드 진입 시 TP1 주문 ID 로그 확인
- 프로그램 재시작 후 TP1 주문 유지 확인
- Binance 주문 목록에서 TAKE_PROFIT_MARKET 확인

### 3. State Recovery (1일)

**문제**:
- 재시작 시 DB OPEN 포지션 복구 시도
- Binance 주문 ID 없음 → 동기화 실패
- 중복 SL 주문 등록 오류

**구현**:
- 시작 시 상태 복구:
  1. DB OPEN 포지션 로드
  2. Binance API 현재 포지션 조회 (Live)
  3. 주문 ID 매칭/동기화
  4. 불일치 시 알림 + 수동 확인
- Redis 상태 저장:
  - 포지션 상태 (entry/sl/tp)
  - 주문 ID (order_id/sl_order_id)
  - 마지막 업데이트 시간

**영향 파일**:
- `execution/engine.py` (recovery 메서드)
- `execution/adapters/brokers.py` (LiveBroker 동기화)
- `common/redis_client.py` (상태 저장/로드)

### 4. Docker Healthcheck (반나절)

**문제**:
- 현재: Python 프로세스만 체크
- DB/Redis 연결 끊김 감지 못함
- 튜너 Unhealthy 방치

**구현**:
- 헬스체크 스크립트 (`scripts/healthcheck.py`):
  1. DB 연결 테스트
  2. Redis ping
  3. Binance API 연결 (Live)
  4. 마지막 캔들 수신 시간 (< 5분)
- docker-compose.yml 업데이트
- Unhealthy 시 자동 재시작

**영향 파일**:
- `scripts/healthcheck.py` (신규)
- `docker-compose.yml`
- `Dockerfile` (HEALTHCHECK 추가)

### 5. Monitoring Dashboard (2일)

**문제**:
- 텔레그램 로그만 존재
- 실시간 성과 확인 불가
- 이상 징후 감지 늦음

**구현**:
- Grafana + Prometheus (간단 설정):
  - Equity 차트 (시간별)
  - 포지션 현황 (OPEN/CLOSED)
  - 승률/손익비 (실시간)
  - 시스템 메트릭 (CPU/Memory)
  - 알림 규칙 (손실 한도, 연결 끊김)
- 메트릭 export:
  - `monitoring/prometheus_exporter.py` (신규)
  - `/metrics` 엔드포인트

**영향 파일**:
- `monitoring/prometheus_exporter.py` (신규)
- `docker-compose.yml` (Grafana/Prometheus 추가)
- `monitoring/dashboards/trading_dashboard.json` (신규)

## 제외 (Out-of-Scope)

- 전략/리스크 로직 (Strategy, Risk Manager)
- Manager 상태 복원 (PHASE7-2 항목 8에서 구현)
- 백테스트 파이프라인 (PHASE 7-4)
- 신호 품질 개선 (PHASE 7-4)
- Live 전환 (PHASE 7-5)

## 영향 파일

**필수**:
- `main.py`
- `execution/engine.py`
- `execution/adapters/brokers.py`
- `scripts/healthcheck.py` (신규)
- `monitoring/prometheus_exporter.py` (신규)
- `docker-compose.yml`
- `Dockerfile`

**선택**:
- `common/redis_client.py`
- `monitoring/dashboards/*.json` (신규)

**테스트**:
- `tests/execution/test_shutdown.py` (신규)
- `tests/execution/test_recovery.py` (신규)

**문서**:
- `docs/PHASE7/PHASE7-3_IMPLEMENTATION_LOG.md`
- `docs/OPERATIONS_GUIDE.md` (신규)

## 설정 키

```yaml
operations:
  # Graceful Shutdown
  graceful_shutdown_enabled: true
  graceful_shutdown_timeout: 60     # 최대 60초
  close_positions_on_shutdown: true # 포지션 정리
  cancel_orders_on_shutdown: true   # 주문 취소 (Live)
  
  # Reset 옵션
  allow_reset_paper: true           # Paper --reset 허용
  allow_reset_live: false           # Live --reset 금지 (안전)
  
  # TP 거래소 등록 (Live)
  tp_exchange_registration: true    # TP1 거래소 등록
  tp_exchange_percentage: 50        # TP1 청산 비율 (50%)
  
  # State Recovery
  state_recovery_enabled: true
  state_recovery_db: true           # DB 복구
  state_recovery_redis: true        # Redis 복구
  state_recovery_binance: true      # Binance 동기화 (Live)
  state_mismatch_action: "ALERT"    # "ALERT" or "AUTO_FIX"
  
  # Healthcheck
  healthcheck_interval: 30          # 30초마다
  healthcheck_db_timeout: 5         # DB 연결 5초 타임아웃
  healthcheck_redis_timeout: 3      # Redis 3초
  healthcheck_api_timeout: 10       # Binance API 10초
  healthcheck_candle_max_age: 300   # 캔들 5분 이상 없으면 Unhealthy

monitoring:
  prometheus_enabled: true
  prometheus_port: 9090
  metrics_export_interval: 10       # 10초마다
  
  grafana_enabled: true
  grafana_port: 3000
  
  alerts:
    daily_loss_limit_alert: true
    connection_lost_alert: true
    extreme_loss_alert: true
```

## 구현 상세

### 1. Graceful Shutdown

**신호 핸들러**:
```python
# main.py
import signal
import sys

shutdown_requested = False

def signal_handler(signum, frame):
    """종료 신호 핸들러"""
    global shutdown_requested
    logger.warning(f"⚠️ 종료 신호 수신: {signal.Signals(signum).name}")
    shutdown_requested = True

# 신호 등록
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def main():
    # ...
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.warning("⚠️ Ctrl+C 감지")
        shutdown_requested = True
    finally:
        if config.get('operations', {}).get('graceful_shutdown_enabled', True):
            engine.graceful_shutdown()
```

**Engine Shutdown**:
```python
# execution/engine.py
def graceful_shutdown(self):
    """안전한 종료 처리"""
    logger.info("🛑 Graceful Shutdown 시작...")
    timeout = self.config.get('operations', {}).get('graceful_shutdown_timeout', 60)
    start_time = time.time()
    
    # 1. 신규 진입 중단
    self.accept_new_entries = False
    logger.info("✅ 신규 진입 중단")
    
    # 2. OPEN 포지션 청산
    if self.config.get('operations', {}).get('close_positions_on_shutdown', True):
        open_positions = [p for p in self.active_positions if p['status'] == 'OPEN']
        logger.info(f"📊 OPEN 포지션 {len(open_positions)}개 청산 시작...")
        
        for position in open_positions:
            if time.time() - start_time > timeout:
                logger.error(f"⏰ Timeout 초과! 남은 포지션: {len(open_positions)}")
                break
            
            try:
                current_price = self.get_current_price(position['symbol'])
                pnl = calculate_pnl(position, current_price, self.fee_rate)
                
                # 시장가 청산
                self.broker.place_order(
                    symbol=position['symbol'],
                    side='SELL' if position['side'] == 'LONG' else 'BUY',
                    qty=position['qty'],
                    order_type='MARKET'
                )
                
                close_trade_in_db(position['id'], current_price, pnl, 'SHUTDOWN', mode=self.mode)
                logger.info(f"✅ 청산 완료: {position['symbol']} @ ${current_price:.6f}")
                
            except Exception as e:
                logger.error(f"❌ 청산 실패: {position['symbol']} - {e}")
    
    # 3. Binance 주문 취소 (Live)
    if self.mode == 'live' and self.config.get('operations', {}).get('cancel_orders_on_shutdown', True):
        logger.info("📋 Binance SL/TP 주문 취소 중...")
        try:
            self.broker.cancel_all_orders()
            logger.info("✅ 모든 주문 취소 완료")
        except Exception as e:
            logger.error(f"❌ 주문 취소 실패: {e}")
    
    # 4. 상태 저장
    self.save_state_to_redis()
    logger.info("✅ 상태 Redis 저장 완료")
    
    # 5. 종료
    elapsed = time.time() - start_time
    logger.info(f"🛑 Graceful Shutdown 완료 ({elapsed:.1f}초)")
```

### 2. State Recovery

**시작 시 복구**:
```python
# execution/engine.py
def recover_state_on_startup(self):
    """재시작 시 상태 복구"""
    logger.info("🔄 State Recovery 시작...")
    
    if not self.config.get('operations', {}).get('state_recovery_enabled', True):
        logger.warning("⚠️ State Recovery 비활성화")
        return
    
    # 1. DB OPEN 포지션 로드
    db_positions = self.load_open_positions_from_db()
    logger.info(f"📊 DB OPEN 포지션: {len(db_positions)}개")
    
    # 2. Redis 상태 로드 (optional)
    redis_states = {}
    if self.config.get('operations', {}).get('state_recovery_redis', True):
        redis_states = self.load_states_from_redis()
        logger.info(f"📊 Redis 상태: {len(redis_states)}개")
    
    # 3. Binance 동기화 (Live only)
    binance_positions = {}
    if self.mode == 'live' and self.config.get('operations', {}).get('state_recovery_binance', True):
        binance_positions = self.broker.get_open_positions()
        logger.info(f"📊 Binance 포지션: {len(binance_positions)}개")
        
        # 불일치 체크
        for db_pos in db_positions:
            symbol = db_pos['symbol']
            if symbol not in binance_positions:
                logger.error(
                    f"⚠️ [STATE MISMATCH] DB에는 있지만 Binance에 없음: {symbol} | "
                    f"Entry: ${db_pos['entry']:.6f}, Qty: {db_pos['qty']}"
                )
                self.handle_state_mismatch(db_pos, None)
            elif abs(binance_positions[symbol]['qty'] - db_pos['qty']) > 0.001:
                logger.error(
                    f"⚠️ [STATE MISMATCH] 수량 불일치: {symbol} | "
                    f"DB: {db_pos['qty']}, Binance: {binance_positions[symbol]['qty']}"
                )
                self.handle_state_mismatch(db_pos, binance_positions[symbol])
    
    # 4. active_positions 복구
    self.active_positions = db_positions
    
    # 5. Redis에서 order_id 복구
    for pos in self.active_positions:
        symbol = pos['symbol']
        if symbol in redis_states:
            pos['sl_order_id'] = redis_states[symbol].get('sl_order_id')
            pos['tp_order_ids'] = redis_states[symbol].get('tp_order_ids', [])
    
    logger.info(f"✅ State Recovery 완료: {len(self.active_positions)}개 포지션")

def handle_state_mismatch(self, db_pos, binance_pos):
    """상태 불일치 처리"""
    action = self.config.get('operations', {}).get('state_mismatch_action', 'ALERT')
    
    if action == 'ALERT':
        # 텔레그램 알림
        self.telegram.send_message(
            f"🚨 [STATE MISMATCH]\n"
            f"Symbol: {db_pos['symbol']}\n"
            f"DB: {db_pos}\n"
            f"Binance: {binance_pos}\n"
            f"수동 확인 필요!"
        )
    elif action == 'AUTO_FIX':
        # 자동 수정 (신중)
        logger.warning("⚠️ AUTO_FIX는 구현되지 않음 (수동 확인 권장)")
```

**상태 저장/로드**:
```python
# common/redis_client.py
def save_position_state(redis_client, mode, run_id, position):
    """포지션 상태 Redis 저장"""
    key = f"state:{mode}:{run_id}:position:{position['symbol']}"
    state = {
        'entry': position['entry'],
        'qty': position['qty'],
        'side': position['side'],
        'sl_order_id': position.get('sl_order_id'),
        'tp_order_ids': position.get('tp_order_ids', []),
        'updated_at': datetime.now().isoformat()
    }
    redis_client.setex(key, 86400, json.dumps(state))  # 24시간 TTL

def load_position_states(redis_client, mode, run_id):
    """포지션 상태 Redis 로드"""
    pattern = f"state:{mode}:{run_id}:position:*"
    keys = redis_client.keys(pattern)
    
    states = {}
    for key in keys:
        symbol = key.split(':')[-1]
        data = redis_client.get(key)
        if data:
            states[symbol] = json.loads(data)
    
    return states
```

### 3. Docker Healthcheck

**헬스체크 스크립트**:
```python
# scripts/healthcheck.py
#!/usr/bin/env python3
import sys
import time
import psycopg2
import redis
from binance.client import Client

def check_db(timeout=5):
    """DB 연결 체크"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            connect_timeout=timeout
        )
        conn.close()
        return True
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}", file=sys.stderr)
        return False

def check_redis(timeout=3):
    """Redis 연결 체크"""
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            socket_connect_timeout=timeout
        )
        r.ping()
        return True
    except Exception as e:
        print(f"❌ Redis 연결 실패: {e}", file=sys.stderr)
        return False

def check_api(timeout=10):
    """Binance API 체크"""
    mode = os.getenv('MODE', 'paper')
    if mode == 'paper':
        return True  # Paper 모드는 API 불필요
    
    try:
        client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET'),
            requests_params={'timeout': timeout}
        )
        client.ping()
        return True
    except Exception as e:
        print(f"❌ Binance API 연결 실패: {e}", file=sys.stderr)
        return False

def check_candle_age(max_age=300):
    """마지막 캔들 수신 시간 체크"""
    try:
        r = redis.Redis(host=os.getenv('REDIS_HOST'))
        key = f"candle:{os.getenv('MODE')}:*:last_update"
        keys = r.keys(key)
        
        if not keys:
            print("⚠️ 캔들 키 없음", file=sys.stderr)
            return False
        
        # 가장 최근 업데이트
        latest = 0
        for k in keys:
            timestamp = float(r.get(k) or 0)
            latest = max(latest, timestamp)
        
        age = time.time() - latest
        if age > max_age:
            print(f"❌ 캔들 수신 지연: {age:.0f}초", file=sys.stderr)
            return False
        
        return True
    except Exception as e:
        print(f"❌ 캔들 체크 실패: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    checks = [
        ('DB', check_db),
        ('Redis', check_redis),
        ('API', check_api),
        ('Candle', check_candle_age)
    ]
    
    failed = []
    for name, check_fn in checks:
        if not check_fn():
            failed.append(name)
    
    if failed:
        print(f"❌ Healthcheck 실패: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)
    
    print("✅ Healthcheck 통과")
    sys.exit(0)
```

**docker-compose.yml**:
```yaml
services:
  trading_bot_paper_ensemble:
    # ...
    healthcheck:
      test: ["CMD", "python", "/app/scripts/healthcheck.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

### 4. Monitoring Dashboard

**Prometheus Exporter**:
```python
# monitoring/prometheus_exporter.py
from prometheus_client import start_http_server, Gauge, Counter

# 메트릭 정의
equity_gauge = Gauge('trading_equity', 'Current Equity')
pnl_daily_gauge = Gauge('trading_pnl_daily', 'Daily PnL')
open_positions_gauge = Gauge('trading_open_positions', 'Open Positions Count')
win_rate_gauge = Gauge('trading_win_rate', 'Win Rate (%)')
trades_total = Counter('trading_trades_total', 'Total Trades', ['exit_reason'])

def update_metrics(engine):
    """메트릭 업데이트"""
    # Equity
    equity = engine.portfolio.get_equity()
    equity_gauge.set(equity)
    
    # Daily PnL
    daily_pnl = engine.portfolio.get_daily_pnl()
    pnl_daily_gauge.set(daily_pnl)
    
    # Open 포지션
    open_count = len([p for p in engine.active_positions if p['status'] == 'OPEN'])
    open_positions_gauge.set(open_count)
    
    # 승률 (최근 100건)
    win_rate = calculate_recent_win_rate(engine.mode, limit=100)
    win_rate_gauge.set(win_rate)

def start_exporter(port=9090):
    """Prometheus Exporter 시작"""
    start_http_server(port)
    logger.info(f"📊 Prometheus Exporter 시작: http://0.0.0.0:{port}/metrics")
```

## 수용 기준

### 필수

- [ ] 컨테이너 재시작: 포지션 유실 **0건**
- [ ] Graceful Shutdown: 모든 OPEN 포지션 청산
- [ ] --reset 옵션: Paper 초기화 동작 확인
- [ ] TP 거래소 등록: Live 모드 TP1 주문 ID 확인
- [ ] State Recovery: DB-Binance 불일치 알림
- [ ] Healthcheck: Unhealthy 3회 연속 → 자동 재시작
- [ ] Dashboard: Equity/PnL/승률 실시간 표시

### 선택

- [ ] Shutdown 시간: < 60초
- [ ] Recovery 시간: < 30초
- [ ] Healthcheck 간격: 30초
- [ ] 메트릭 지연: < 10초

## 테스트 플랜

### 단위 테스트

```python
# tests/execution/test_shutdown.py
def test_graceful_shutdown_closes_positions():
    """Graceful Shutdown 포지션 청산"""
    engine = MockEngine()
    engine.active_positions = [
        {'id': 1, 'symbol': 'BTCUSDT', 'side': 'LONG', 'qty': 1.0, 'status': 'OPEN'}
    ]
    
    engine.graceful_shutdown()
    
    assert len(engine.active_positions) == 0
    assert engine.broker.cancel_all_orders_called == True

# tests/execution/test_recovery.py
def test_state_recovery_from_db():
    """DB에서 상태 복구"""
    # DB에 OPEN 포지션 삽입
    insert_open_position('BTCUSDT', 'LONG', 1.0)
    
    engine = Engine(mode='paper')
    engine.recover_state_on_startup()
    
    assert len(engine.active_positions) == 1
    assert engine.active_positions[0]['symbol'] == 'BTCUSDT'
```

### 통합 테스트

```bash
# 1. 컨테이너 강제 종료 후 재시작
docker kill trading_bot_paper_ensemble
docker-compose up -d trading_bot_paper_ensemble

# 로그 확인
docker logs trading_bot_paper_ensemble 2>&1 | grep "State Recovery"

# 2. Healthcheck 테스트
docker exec trading_bot_paper_ensemble python /app/scripts/healthcheck.py
# 출력: ✅ Healthcheck 통과

# 3. DB 연결 끊기
docker pause trading_db_postgres
sleep 60  # 30초 * 2회 체크
docker ps  # Unhealthy 확인
docker unpause trading_db_postgres
```

## 체크리스트

### 구현

- [ ] **Graceful Shutdown + --reset**
  - [ ] 신호 핸들러 (SIGTERM/SIGINT)
  - [ ] 포지션 청산 로직 (공통)
  - [ ] Binance 주문 취소 (Live)
  - [ ] Redis 상태 저장
  - [ ] --reset 옵션: argparse + 환경변수
  - [ ] Paper 초기화 로직
  - [ ] Live --reset 금지 (에러 처리)

- [ ] **TP 거래소 등록**
  - [ ] LiveBroker.create_tp_order() 메서드
  - [ ] engine.py: 진입 시 TP1 50% 등록
  - [ ] 주문 ID 저장/복원
  - [ ] State Recovery 연동

- [ ] **State Recovery**
  - [ ] DB OPEN 포지션 로드
  - [ ] Binance 동기화 (Live)
  - [ ] 불일치 알림
  - [ ] Redis 상태 로드

- [ ] **Healthcheck**
  - [ ] `healthcheck.py` 스크립트
  - [ ] DB/Redis/API 체크
  - [ ] 캔들 수신 시간 체크
  - [ ] docker-compose.yml 설정

- [ ] **Dashboard**
  - [ ] Prometheus Exporter
  - [ ] Grafana 설정
  - [ ] 기본 대시보드
  - [ ] 알림 규칙

### 테스트

- [ ] 단위 테스트
- [ ] 재시작 시나리오 테스트
- [ ] Healthcheck 검증
- [ ] Dashboard 정상 표시

### 문서

- [ ] IMPLEMENTATION_LOG.md
- [ ] OPERATIONS_GUIDE.md (운영 매뉴얼)

## 배포/롤백

- PHASE 7-2 완료 → 7-3 적용
- Paper 1주 안정성 검증
- 재시작 3회 테스트 → 포지션 유실 0건
- Live 소액 테스트 전 필수

## 리스크/완화

- Shutdown 타임아웃? → 60초 → 120초 증가
- Binance 동기화 실패? → 수동 확인 알림
- Healthcheck 오탐? → 재시도 3회
- Dashboard 리소스? → Sampling rate 조정

## 연관 문서

- **PHASE7-2_MASTER_PLAN.md**: 항목 7(--reset) 원본 설계
- **SYSTEM_OPERATIONS_ANALYSIS.md**: TP 위험 분석 및 TO-BE 방안
- **CRITICAL_SYSTEM_ANALYSIS_2025-11-10.md**: 포지션 관리 분석
- **GUARD_EXECUTION_ORDER_ANALYSIS.md**: 가드/차단 기능 실행 순서 분석
- **SLIPPAGE_PERFORMANCE_COMPARISON.md**: 슬리피지 성능 비교
- **체크리스트**: [PHASE7-2_MASTER_PLAN.md 항목 4](PHASE7-2_MASTER_PLAN.md) 참조

## 릴리즈 노트

PHASE7-3: Graceful Shutdown + --reset 옵션 + TP 거래소 등록 + State Recovery + Healthcheck + Dashboard로 Live 운영 안정성 확보. 컨테이너 재시작 안전, 포지션 유실 0건, TP 안전 보장.
