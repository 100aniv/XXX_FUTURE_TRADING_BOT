#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket Collector
===================
Binance WebSocket을 통한 실시간 데이터 수집

- WebSocketCollector 클래스
- 캔들 데이터 수신
- 콜백 기반 이벤트 처리
"""
import json
import time
import threading
from typing import Callable, List, Optional, Dict
from websocket import WebSocketApp
from datetime import timedelta

from common.logger import setup_logger
from common.utils import make_streams, parse_timeframe_ms
from common.redis_client import RedisClient
from monitoring.performance_monitor import backfill_stats, connection_stats
try:
    from monitoring import get_monitoring
    GUARDIAN_AVAILABLE = True
except ImportError:
    GUARDIAN_AVAILABLE = False

logger = setup_logger('collector', log_type='application')

BINANCE_F_WS = "wss://fstream.binance.com/stream"


class WebSocketCollector:
    """
    Binance WebSocket 실시간 데이터 수집기
    
    **기능:**
    - 실시간 캔들 데이터 수집
    - 중복 캔들 자동 제거 (dedup)
    - 누락 캔들 자동 복구 (backfill via REST API)
    - 멀티 심볼 지원
    
    **사용 예:**
    ```python
    # 단일 심볼
    ws = WebSocketCollector(["BTCUSDT"], "5m")
    
    # 멀티 심볼
    ws = WebSocketCollector(["BTCUSDT", "ETHUSDT"], "5m")
    
    # dedup/backfill 비활성화 (테스트용)
    ws = WebSocketCollector(["BTCUSDT"], "5m", enable_dedup=False, enable_backfill=False)
    ```
    """
    
    def __init__(self, symbols: List[str], timeframe, enable_dedup: bool = True, enable_backfill: bool = True, redis_cfg: Optional[Dict] = None, ws_cfg: Optional[Dict] = None, env: str = 'paper', run_id: str = 'unknown', runtime_ctx=None):
        """
        WebSocketCollector 초기화 (PR7-4: Multi-TF 지원)
        
        Args:
            symbols: 심볼 리스트 (예: ["BTCUSDT", "ETHUSDT"])
            timeframe: 타임프레임 (str 또는 List[str])
                - 단일: "5m"
                - 다중: ["3m", "5m", "15m", "1h", "4h"]
            enable_dedup: 중복 캔들 제거 활성화 (기본 True)
                - True: 동일 캔들 여러 번 수신 시 1번만 처리
                - False: 모든 캔들 처리 (테스트용)
            enable_backfill: 누락 캔들 자동 복구 활성화 (기본 True)
                - True: WebSocket 연결 끊김 시 REST API로 자동 복구
                - False: 누락 감지만 (복구 안 함)
            redis_cfg: Redis 설정 (host, port, ttl_seconds)
            ws_cfg: WebSocket 설정 (heartbeat_interval_sec, reconnect 등)
            env: 실행 모드 (backtest, paper, live) - PHASE18-2
            run_id: 실행 인스턴스 ID - PHASE18-2
        
        **주의:**
        - 프로덕션에서는 enable_dedup=True, enable_backfill=True 권장
        - 테스트 시에만 비활성화
        """
        self.symbols = symbols
        # PR7-4: Multi-TF 지원
        self.timeframes = timeframe if isinstance(timeframe, list) else [timeframe]
        self.timeframe = self.timeframes[0]  # 하위 호환성
        self.ws = None
        self.running = False
        
        # 중복/누락 처리 설정
        self.enable_dedup = enable_dedup
        self.enable_backfill = enable_backfill
        
        # Dedup: Redis 기반 중복 제거 (재시작 시에도 유지, 분산 환경 지원)
        _rcfg = redis_cfg or {}
        # 환경변수 치환 실패 등으로 None/빈문자열이 들어올 수 있으므로 안전 처리
        _rhost = (_rcfg.get('host') or 'localhost')
        try:
            _rport = int(_rcfg.get('port') or 6379)
        except Exception:
            _rport = 6379
        try:
            _rttl = int(_rcfg.get('ttl_seconds') or 3600)
        except Exception:
            _rttl = 3600
        # ⭐ PHASE18-2: env와 run_id 전달
        self.redis_client = RedisClient.get_instance(host=_rhost, port=_rport, ttl_seconds=_rttl, env=env, run_id=run_id)
        
        # ⭐ PHASE18-4: RuntimeContext 참조 (모니터링)
        self.runtime_ctx = runtime_ctx
        
        # WebSocket 연결 모니터링 설정
        _wscfg = ws_cfg or {}
        self.heartbeat_interval = _wscfg.get('heartbeat_interval_sec', 10)
        self.reconnect_backoff_ms = _wscfg.get('reconnect', {}).get('backoff_ms', 500)
        self.max_reconnect_attempts = _wscfg.get('reconnect', {}).get('max_attempts', 20)
        self.connection_timeout = _wscfg.get('connection_timeout_sec', 30)
        
        # ⭐ Gap 감지 설정
        _gapcfg = _wscfg.get('gap_detection', {})
        self.gap_threshold_mult = _gapcfg.get('threshold_multiplier', 1.5)
        self.max_backfill_batch = _gapcfg.get('max_backfill_batch', 50)
        self.large_gap_threshold = _gapcfg.get('large_gap_threshold', 100)
        
        # ⭐ Backfill: 마지막 캔들 시간 추적
        self.last_candle_time = {}  # {(symbol, timeframe): last_closed_at}
        
        # 콜백 함수들
        self.on_candle_callback = None
        self.on_connect_callback = None
        self.on_error_callback = None
        self.on_close_callback = None
        
        # 캔들 버퍼 (stream용) - PR7-4: Multi-TF 대응 큐 크기
        # config.system.candle_queue_size에서 설정값 읽음 (기본 600,000)
        # Multi-TF: 100심볼 × 1000캔들 × 4TF = 400k + 버퍼
        import queue
        queue_size = _wscfg.get('queue_size', 600000)  # ⭐ PR7-4: config 기반 큐 크기
        self.candle_queue = queue.Queue(maxsize=queue_size)
        
        # PR5: 큐 지표 추적
        self.queue_drop_count = 0
        self.queue_retry_count = 0
        self._last_queue_health_report = time.time()
    
    def on_candle(self, callback: Callable):
        """
        캔들 데이터 수신 시 호출할 콜백 등록
        
        Args:
            callback: function(symbol, candle_data, is_closed)
        """
        self.on_candle_callback = callback
        return self
    
    def on_connect(self, callback: Callable):
        """연결 성공 시 호출할 콜백 등록"""
        self.on_connect_callback = callback
        return self
    
    def on_error(self, callback: Callable):
        """에러 발생 시 호출할 콜백 등록"""
        self.on_error_callback = callback
        return self
    
    def on_close_reconnect(self, callback: Callable):
        """연결 끊김 시 호출할 콜백 등록"""
        self.on_close_callback = callback
        return self
    
    def _on_message(self, ws, message):
        """WebSocket 메시지 수신"""
        try:
            # ⭐ 연결 통계: 하트비트 기록 (메시지 수신 = 연결 활성)
            connection_stats.record_heartbeat()
            
            # ⭐ PHASE18-4: 모니터링 Heartbeat 업데이트
            if self.runtime_ctx and self.runtime_ctx.monitor_registry:
                heartbeat = self.runtime_ctx.monitor_registry.get('heartbeat')
                if heartbeat:
                    heartbeat.update('websocket')
            
            data = json.loads(message)
            
            # ⭐ 디버그: 첫 메시지 로깅
            if not hasattr(self, '_first_message_logged'):
                logger.info(f"✅ WebSocket 첫 메시지 수신! (크기: {len(message)} bytes)")
                self._first_message_logged = True
            
            if "stream" not in data:
                return
            
            payload = data["data"]
            k = payload.get("k", {})
            
            if not k:
                return
            
            symbol = payload.get("s")
            timeframe = k.get("i")
            
            # PR7-3: 캔들 시작 시간 변화 감지로 이전 캔들 닫힘 판단
            is_closed_from_ws = k.get("x", False)
            candle_start = int(k["t"])  # 현재 캔들 시작 시간
            
            # 이전 캔들 시작 시간 추적
            if not hasattr(self, '_last_candle_start'):
                self._last_candle_start = {}
            
            key = (symbol, timeframe)
            prev_start = self._last_candle_start.get(key)
            
            # 캔들 시작 시간 추적 (디버그 로그 제거)
            
            # 새로운 캔들 시작 감지
            if prev_start is not None and candle_start != prev_start:
                # 이전 캔들을 닫힌 것으로 처리하여 큐에 추가
                logger.info(f"🕐 {symbol} {timeframe} 캔들 닫힘 감지: {prev_start} → {candle_start}")
                
                # 중복 체크 (dedup 활성화 시)
                should_add = True
                if self.enable_dedup:
                    is_duplicate = self.redis_client.is_seen(symbol, timeframe, prev_start)
                    if is_duplicate:
                        logger.debug(f"⏭️ {symbol} {timeframe} 중복 캔들 무시: {prev_start}")
                        should_add = False
                    else:
                        self.redis_client.mark_seen(symbol, timeframe, prev_start)
                
                if should_add:
                    closed_candle = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "closed_at": prev_start,
                        "time": prev_start,
                        "open": float(k["o"]),  # 정확도 낮지만 근사값
                        "high": float(k["h"]),
                        "low": float(k["l"]),
                        "close": float(k["c"]),
                        "volume": float(k["v"])
                    }
                    import queue as queue_module
                    try:
                        self.candle_queue.put_nowait(closed_candle)
                        logger.info(f"✅ 닫힌 캔들 큐 추가: {symbol} {timeframe} {prev_start}")
                    except queue_module.Full:
                        logger.warning(f"⚠️ 큐 Full! 닫힌 캔들 추가 실패: {symbol}")
            
            # 현재 캔들 시작 시간 저장
            self._last_candle_start[key] = candle_start
            
            # 현재 캔들은 열린 캔들로 처리 (콜백만)
            is_closed = is_closed_from_ws  # WS에서 명시적으로 닫힘 표시한 경우만
            
            # ⭐ 표준 키 형식: (symbol, timeframe, closed_at)
            closed_at = candle_start
            candle = {
                "symbol": symbol,
                "timeframe": timeframe,
                "closed_at": closed_at,
                "time": closed_at,  # 하위 호환성 (추후 제거)
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"])
            }
            
            # PR7-3: 실시간 데이터 수신 확인 로그 (1분에 한 번)
            current_minute = int(time.time()) // 60
            if not hasattr(self, '_last_log_minute'):
                self._last_log_minute = {}
            
            if symbol not in self._last_log_minute or self._last_log_minute[symbol] != current_minute:
                self._last_log_minute[symbol] = current_minute
                logger.info(f"📊 {symbol} {timeframe} 실시간 수신 중... (가격: {candle['close']:.2f}, 닫힘: {is_closed})")
            
            # PR7-4: Multi-TF - 구독한 timeframe만 처리
            if timeframe not in self.timeframes:
                logger.debug(f"⏭️  {symbol} timeframe 불일치 무시: 수신={timeframe}, 구독={self.timeframes}")
                return

            # WS에서 명시적으로 닫힌 캔들 처리 (드문 경우)
            if is_closed:
                logger.info(f"🕐 {symbol} {timeframe} WS 닫힌 캔들 수신: {closed_at}")
                if self.enable_dedup:
                    if self.redis_client.is_seen(symbol, timeframe, closed_at):
                        logger.debug(f"⏭️  {symbol} {timeframe} 중복 캔들 무시 (Redis): {closed_at}")
                        return
                    self.redis_client.mark_seen(symbol, timeframe, closed_at)
                
                import queue as queue_module
                try:
                    self.candle_queue.put_nowait(candle)
                except queue_module.Full:
                    logger.warning(f"⚠️ 큐 Full! WS 닫힌 캔들 추가 실패: {symbol}")
            
            # PR5: 큐 헬스 리포트 (10초마다)
            if time.time() - self._last_queue_health_report > 10:
                self._emit_queue_health()
                self._last_queue_health_report = time.time()
            
            # 콜백 호출
            if self.on_candle_callback:
                self.on_candle_callback(symbol, candle, is_closed, timeframe)
        
        except Exception as e:
            logger.error(f"❌ 메시지 처리 오류: {e}")
            if self.on_error_callback:
                self.on_error_callback(f"메시지 처리 오류: {e}")
    
    def _emit_queue_health(self):
        """PR5: 큐 헬스 메트릭을 FlowGuardian으로 발행"""
        try:
            queue_size = self.candle_queue.qsize()
            queue_maxsize = self.candle_queue.maxsize
            usage_pct = (queue_size / queue_maxsize * 100) if queue_maxsize > 0 else 0
            
            payload = {
                "size": queue_size,
                "maxsize": queue_maxsize,
                "usage_pct": round(usage_pct, 2),
                "drops": self.queue_drop_count,
                "retries": self.queue_retry_count
            }
            
            # FlowGuardian 이벤트 발행
            if GUARDIAN_AVAILABLE:
                guardian = get_monitoring()
                guardian.emit_event({
                    "type": "queue.health",
                    "ts": time.time(),
                    "payload": payload
                })
                # PR5: 큐 헬스 로깅 (정상 작동 확인용) - debug 레벨로 강등 (PHASE22-1)
                logger.debug(f"📊 [PR5 Queue] 사용률: {usage_pct:.1f}% ({queue_size}/{queue_maxsize}) | Drops: {self.queue_drop_count} | Retries: {self.queue_retry_count}")
            
            # 임계치 경고 (80% 이상)
            if usage_pct >= 80:
                logger.warning(f"⚠️ 큐 사용률 높음: {usage_pct:.1f}% ({queue_size}/{queue_maxsize})")
        
        except Exception as e:
            logger.debug(f"큐 헬스 리포트 실패: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket 에러"""
        # ⭐ 연결 통계: 에러 기록
        connection_stats.record_disconnect(f"error: {str(error)[:50]}")
        logger.error(f"💥 WebSocket 오류: {error}")
        if self.on_error_callback:
            self.on_error_callback(error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket 연결 끊김"""
        # ⭐ 연결 통계: 끊김 기록
        reason = f"close_code_{close_status_code}" if close_status_code else "unknown_close"
        connection_stats.record_disconnect(reason)
        
        # FlowGuardian 훅
        if GUARDIAN_AVAILABLE:
            try:
                guardian = get_monitoring()
                guardian.emit_event({"type": "ws.connection", "ts": time.time(), "payload": {"connected": False, "reason": reason}})
            except Exception:
                pass
        
        if self.running:
            logger.warning("🔌 WebSocket 연결 끊김. 재연결 시도...")
            if self.on_close_callback:
                self.on_close_callback()
            
            # ⭐ 재연결 로직 (백오프 적용)
            for attempt in range(self.max_reconnect_attempts):
                if not self.running:
                    break
                
                connection_stats.record_reconnect_attempt()
                backoff_sec = (self.reconnect_backoff_ms / 1000) * (2 ** min(attempt, 5))  # 지수 백오프
                logger.info(f"🔄 재연결 시도 {attempt+1}/{self.max_reconnect_attempts} (대기: {backoff_sec:.1f}초)")
                time.sleep(backoff_sec)
                
                if self.running:
                    try:
                        self.connect()
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ 재연결 실패: {e}")
            else:
                logger.error(f"❌ 최대 재연결 시도 초과 ({self.max_reconnect_attempts}회)")
        else:
            logger.info("🛑 Collector 정상 종료")
    
    def _on_open(self, ws):
        """WebSocket 연결 성공"""
        # ⭐ 연결 통계: 연결 성공 기록
        connection_stats.record_connect()
        logger.info("🔗 WebSocket 연결 성공")
        
        # FlowGuardian 훅
        if GUARDIAN_AVAILABLE:
            try:
                guardian = get_monitoring()
                guardian.emit_event({"type": "ws.connection", "ts": time.time(), "payload": {"connected": True}})
            except Exception:
                pass
        
        if self.on_connect_callback:
            self.on_connect_callback()
    
    def connect(self):
        """WebSocket 연결 (비동기 스레드에서 실행)"""
        streams = make_streams(self.symbols, self.timeframe)
        url = f"{BINANCE_F_WS}?streams={streams}"
        
        self.ws = WebSocketApp(
            url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        logger.info(f"📡 WebSocket 연결 시작: {len(self.symbols)}개 심볼")
        # ⭐ 비동기 실행: run_forever()를 별도 스레드에서 실행
        # 하트비트 간격을 config에서 가져온 값으로 설정
        # websocket-client 요구사항: ping_interval > ping_timeout 이어야 함
        try:
            _ping_timeout = int(self.connection_timeout)
        except Exception:
            _ping_timeout = 30
        try:
            _ping_interval = int(self.heartbeat_interval)
        except Exception:
            _ping_interval = 10
        if _ping_interval <= _ping_timeout:
            _ping_interval = _ping_timeout + 1
        logger.debug(f"WS run_forever with ping_interval={_ping_interval}s, ping_timeout={_ping_timeout}s")
        self.ws.run_forever(ping_interval=_ping_interval, ping_timeout=_ping_timeout)
    
    def start(self):
        """데이터 수집 시작 (비동기)"""
        self.running = True
        # ⭐ 별도 스레드에서 WebSocket 실행 (메인 스레드 블로킹 방지)
        self._ws_thread = threading.Thread(target=self.connect, daemon=True)
        self._ws_thread.start()
        logger.info("✅ WebSocket 스레드 시작 (비동기)")
    
    def stop(self, timeout=5.0):
        """
        데이터 수집 중지 (PHASE18-3: Graceful Shutdown)
        
        Args:
            timeout: Thread join 타임아웃 (기본 5초)
        """
        logger.info("🛑 WebSocketCollector 중지 시작...")
        
        # 1. running 플래그 False (새 수신 중단)
        self.running = False
        
        # 2. WebSocket 종료
        if self.ws:
            try:
                self.ws.close()
                logger.info("  ✅ WebSocket 연결 종료")
            except Exception as e:
                logger.warning(f"  ⚠️ WebSocket 종료 실패: {e}")
        
        # 3. Thread join (타임아웃)
        if hasattr(self, '_ws_thread') and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=timeout)
            if self._ws_thread.is_alive():
                logger.warning(f"  ⚠️ WebSocket thread 타임아웃 ({timeout}s)")
            else:
                logger.info("  ✅ WebSocket thread 종료")
        
        # 4. Redis 연결 종료
        if hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
                logger.info("  ✅ Redis 연결 종료")
            except Exception as e:
                logger.warning(f"  ⚠️ Redis 종료 실패: {e}")
        
        logger.info("✅ WebSocketCollector 중지 완료")
    
    def _cleanup_old_candles(self):
        """
        오래된 캔들 키 제거 (TTL 기반 메모리 관리)
        
        1시간 이상 된 캔들 키를 제거하여 메모리 누수 방지
        """
        now = time.time()
        ttl_seconds = self.ttl_hours * 3600
        
        expired = [k for k, ts in self.seen_candles.items() 
                  if now - ts > ttl_seconds]
        
        for k in expired:
            del self.seen_candles[k]
        
        if expired:
            logger.debug(f"🗑️  {len(expired)}개 오래된 캔들 키 제거 (메모리 최적화)")
        
        self._last_cleanup = now
    
    def _check_and_backfill(self, symbol: str, timeframe: str, closed_at: int):
        """
        누락 캔들 감지 + REST API로 자동 복구
        
        **동작 방식:**
        1. 마지막 캔들 시간과 현재 캔들 시간 비교
        2. Gap이 1.5배 이상이면 누락으로 판단
        3. REST API로 누락 구간 캔들 가져오기
        4. 누락 캔들을 큐에 추가 (seen_candles에 기록)
        
        **예시:**
        - 5분 타임프레임
        - 마지막: 11:00, 현재: 11:15 (Gap: 15분)
        - Gap > 7.5분 (5분 * 1.5) → 누락 감지!
        - REST로 11:05, 11:10 캔들 복구
        
        Args:
            symbol: 심볼 (예: "BTCUSDT")
            timeframe: 타임프레임 (예: "5m")
            closed_at: 현재 캔들 닫힌 시간 (ms)
        
        **참고:**
        - REST API 호출 실패 시 로그만 남기고 계속 진행
        - 완벽한 복구 보장은 아니지만, 대부분 케이스 커버
        """
        key = (symbol, timeframe)
        last_ts = self.last_candle_time.get(key)
        
        if not last_ts:
            # 첫 캔들이면 skip
            return
        
        # ⭐ 타임프레임 동적 파싱 (모든 TF 지원: 1m, 5m, 1h, 4h, 1d, 1w 등)
        tf_ms = parse_timeframe_ms(timeframe)
        
        # Gap 감지 (설정값 배수 이상 차이나면 누락)
        gap = closed_at - last_ts
        if gap > tf_ms * self.gap_threshold_mult:
            # ⭐ 통계: Gap 발견 (전역 통계 사용)
            backfill_stats.record_gap(symbol)
            
            logger.warning(f"⚠️  {symbol} {timeframe} 캔들 누락 감지! Gap: {gap/1000:.0f}초")
            
            # REST API로 누락 캔들 가져오기
            try:
                from collectors.rest_collector import fetch_history
                
                # 누락 개수 계산
                missing_count = int(gap / tf_ms) - 1
                if missing_count > 0:
                    # ⭐ 대형 Gap 경고
                    if missing_count >= self.large_gap_threshold:
                        logger.warning(f"🚨 {symbol} {timeframe} 대형 Gap 감지! 누락 {missing_count}개 (임계값: {self.large_gap_threshold})")
                    
                    logger.info(f"🔄 {symbol} {timeframe} 누락 캔들 {missing_count}개 복구 중...")
                    
                    # ⭐ 최대 백필 배치 크기 적용
                    batch_size = min(missing_count + 10, self.max_backfill_batch)
                    logger.debug(f"📊 {symbol} 백필 배치 크기: {batch_size} (요청: {missing_count + 10}, 최대: {self.max_backfill_batch})")
                    
                    # REST로 히스토리 가져오기
                    candles = fetch_history(symbol, timeframe, limit=batch_size)
                    
                    recovered_count = 0
                    # 누락 구간만 필터링
                    for c in candles:
                        c_ts = c.get("time", 0)
                        if last_ts < c_ts < closed_at:
                            candle_key = (symbol, timeframe, c_ts)
                            if candle_key not in self.seen_candles:
                                # 표준 형식으로 변환
                                backfilled_candle = {
                                    "symbol": symbol,
                                    "timeframe": timeframe,
                                    "closed_at": c_ts,
                                    "time": c_ts,
                                    "open": c["open"],
                                    "high": c["high"],
                                    "low": c["low"],
                                    "close": c["close"],
                                    "volume": c["volume"]
                                }
                                
                                # 큐에 추가 - 재시도 로직
                                import queue as queue_module
                                try:
                                    self.candle_queue.put_nowait(backfilled_candle)
                                    self.seen_candles[candle_key] = time.time()
                                    recovered_count += 1
                                    logger.debug(f"✅ {symbol} 캔들 복구: {c_ts}")
                                except queue_module.Full:
                                    logger.warning(f"⚠️ 백필 큐 Full! 재시도: {symbol}")
                                    time.sleep(0.1)
                                    try:
                                        self.candle_queue.put(backfilled_candle, timeout=1.0)
                                        self.seen_candles[candle_key] = time.time()
                                        recovered_count += 1
                                        logger.debug(f"✅ {symbol} 캔들 복구 (재시도): {c_ts}")
                                    except queue_module.Full:
                                        logger.error(f"❌ 백필 큐 Full로 손실: {symbol} {c_ts}")
                    
                    # ⭐ 통계: 복구 성공 (전역 통계 사용)
                    backfill_stats.record_recovery(symbol, recovered=recovered_count)
                    logger.info(f"✅ {symbol} {timeframe} 누락 복구 완료: {recovered_count}/{missing_count}개")
            
            except Exception as e:
                # ⭐ 통계: 복구 실패 (전역 통계 사용)
                backfill_stats.record_recovery(symbol, recovered=0, failed=1)
                logger.error(f"❌ {symbol} {timeframe} 누락 복구 실패: {e}")
    
    def get_backfill_report(self) -> dict:
        """
        백필 통계 리포트 반환 (전역 통계 조회)
        
        Returns:
            dict: 백필 통계 정보
                - total_gaps: 총 Gap 발견 수
                - total_recovered: 총 복구된 캔들 수
                - total_failed: 총 실패 수
                - recovery_rate: 복구율 (%)
                - by_symbol: 심볼별 통계
        """
        return backfill_stats.get_report()
    
    def get_connection_report(self) -> dict:
        """
        연결 상태 리포트 반환 (전역 통계 조회)
        
        Returns:
            dict: 연결 상태 정보
                - current_connected: 현재 연결 상태
                - total_connects: 총 연결 수
                - total_disconnects: 총 끊김 수
                - avg_connection_duration_sec: 평균 연결 지속 시간
                - last_heartbeat_ago_sec: 마지막 하트비트 경과 시간
                - disconnect_reasons: 끊김 이유별 통계
        """
        return connection_stats.get_report()
    
    def stream(self):
        """
        캔들 스트림 생성 (generator)
        engine.py 호환용
        
        Yields:
            캔들 dict
        """
        while self.running:
            try:
                # 블로킹 방식으로 캔들 대기 (1초 타임아웃)
                candle = self.candle_queue.get(timeout=1.0)
                yield candle
            except:
                # 타임아웃 또는 에러 시 계속
                continue
