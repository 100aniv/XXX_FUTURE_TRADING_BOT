# PHASE7-3 마스터 플랜: 운영 안정성 강화 (Live 모드 준비)

## 배경/의도 (Overview)

PHASE 7-1/7-2 완료 후 성과 개선 완료. 하지만 **운영 안정성** 부족:
- 컨테이너 재시작 시 포지션 유실 위험
- Live 모드: Binance SL 주문 유실
- 헬스체크 부실 (튜너 Unhealthy 방치)
- 모니터링 없음 (Dashboard, Alert)

Live 운영을 위한 **필수 안전장치** 구축.

## 목표 (Goals)

- **Graceful Shutdown**: 종료 전 모든 포지션 정리
- **State Recovery**: 재시작 시 포지션/주문 동기화
- **Docker Healthcheck**: DB/Redis/API 연결 검증
- **Monitoring Dashboard**: Grafana 기본 대시보드
- **컨테이너 재시작 안전**: 포지션 유실 0건

## 범위 (Scope, In)

### 1. Graceful Shutdown (1일)

**문제**:
- Daily Loss Limit 도달 → `sys.exit(1)` → 강제 종료
- OPEN 포지션 방치
- Live: Binance SL/TP 주문 남음

**구현**:
- 종료 신호 핸들러 (SIGTERM, SIGINT)
- 포지션 정리 순서:
  1. 신규 진입 중단
  2. OPEN 포지션 시장가 청산
  3. Binance SL/TP 주문 취소 (Live)
  4. 상태 저장 (DB + Redis)
  5. 정상 종료

**영향 파일**:
- `main.py` (신호 핸들러)
- `execution/engine.py` (shutdown 메서드)
- `execution/adapters/brokers.py` (LiveBroker 주문 취소)

### 2. State Recovery (1일)

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

### 3. Docker Healthcheck (반나절)

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

### 4. Monitoring Dashboard (2일)

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

- [ ] **Graceful Shutdown**
  - [ ] 신호 핸들러 (SIGTERM/SIGINT)
  - [ ] 포지션 청산 로직
  - [ ] Binance 주문 취소 (Live)
  - [ ] Redis 상태 저장

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

## 릴리즈 노트

PHASE7-3: Graceful Shutdown + State Recovery + Healthcheck + Dashboard로 Live 운영 안정성 확보. 컨테이너 재시작 안전, 포지션 유실 0건.
