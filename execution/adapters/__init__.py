#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Adapters
==================
Broker, Clock 어댑터 + Factory 함수

Feed는 collectors 모듈에서 가져옴:
- collectors.HistoricalFeed (백테스트)
- collectors.WebSocketCollector (페이퍼/라이브)
"""
import os
import sys
import time
from typing import Tuple, Any, List
from pathlib import Path

from .brokers import SimBroker, PaperBroker, LiveBroker
from .clocks import SimClock, LiveClock
from collectors import fetch_history
# ⚠️ WebSocketCollector 임포트를 지연시켜 즉시 활성화 방지
# from collectors import WebSocketCollector  # 🚫 즉시 임포트 금지

__all__ = [
    'SimBroker', 'PaperBroker', 'LiveBroker',
    'SimClock', 'LiveClock',
    'create_adapters',
    'preload_symbols',
    'preload_multi_timeframes'  # PR7-4
]


def preload_multi_timeframes(ws: Any, symbols: List[str], strategies_config: dict, lookback: int, logger: Any):
    """
    Multi-Timeframe 프리로드 (PR7-4)
    
    Args:
        ws: WebSocketCollector 인스턴스
        symbols: 심볼 리스트
        strategies_config: 전략 설정 dict
        lookback: lookback 기간
        logger: 로거
    """
    # 전략별 사용 TF 수집
    timeframes = set()
    for strategy_name, cfg in strategies_config.items():
        if cfg.get('enabled', True):
            tf = cfg.get('timeframe', '1m')
            timeframes.add(tf)
    
    timeframes = sorted(timeframes)
    logger.info(f"📥 Multi-TF Preload: {timeframes} ({len(symbols)}개 심볼)")
    
    total_success = 0
    for tf_idx, tf in enumerate(timeframes):
        logger.info(f"📥 [{tf}] 프리로드 시작...")
        success_count = 0
        
        # ⭐ TF 간 대기 (API Rate Limit 대응)
        if tf_idx > 0:
            logger.info(f"⏳ TF 간 대기: 3초")
            time.sleep(3)
        
        for idx, sym in enumerate(symbols, 1):
            try:
                # ⭐ Rate Limit 대응: 20개마다 1초 대기 (상용 수준)
                if idx > 1 and (idx - 1) % 20 == 0:
                    logger.info(f"⏳ Rate Limit 대응: 1초 대기... ({idx-1}/100 완료)")
                    time.sleep(1)
                
                candles = fetch_history(sym, tf, limit=min(lookback, 1000))
                
                if not candles:
                    logger.warning(f"⚠️ [{tf}] [{idx}/{len(symbols)}] {sym} 데이터 없음")
                    continue
                
                # 큐에 추가
                for c in candles:
                    try:
                        closed_at = int(c.get("closed_at", c.get("time", 0)))
                    except Exception:
                        closed_at = int(c.get("time", 0))
                    
                    enriched = {
                        "symbol": sym,
                        "timeframe": tf,  # ⭐ TF 명시
                        "closed_at": closed_at,
                        "time": closed_at,
                        "open": float(c.get("open")),
                        "high": float(c.get("high")),
                        "low": float(c.get("low")),
                        "close": float(c.get("close")),
                        "volume": float(c.get("volume"))
                    }
                    
                    import queue as queue_module
                    try:
                        ws.candle_queue.put_nowait(enriched)
                    except queue_module.Full:
                        logger.warning(f"⚠️ [{tf}] 큐 Full! {sym} 캔들 추가 실패")
                    except AttributeError:
                        if ws.on_candle_callback:
                            ws.on_candle_callback(sym, enriched, is_closed=True)
                
                success_count += 1
                
                # 10심볼마다 로그
                if idx % 10 == 0 or idx == len(symbols):
                    queue_size = ws.candle_queue.qsize() if hasattr(ws, 'candle_queue') else 0
                    logger.info(f"✅ [{tf}] [{idx}/{len(symbols)}] {sym}: {len(candles)}개 | 큐: {queue_size}")
            
            except Exception as e:
                import traceback
                error_msg = str(e)
                
                # ⭐ API Rate Limit 오류 처리
                if "-1003" in error_msg or "too many requests" in error_msg.lower():
                    logger.warning(f"⚠️ [{tf}] API Rate Limit 초과 - 5초 대기 후 재시도")
                    time.sleep(5)
                    try:
                        # 재시도 1회
                        candles = fetch_history(sym, tf, limit=min(lookback, 1000))
                        if candles:
                            for c in candles:
                                try:
                                    closed_at = int(c.get("closed_at", c.get("time", 0)))
                                except Exception:
                                    closed_at = int(c.get("time", 0))
                                enriched = {
                                    "symbol": sym, "timeframe": tf, "closed_at": closed_at,
                                    "time": closed_at, "open": float(c.get("open")),
                                    "high": float(c.get("high")), "low": float(c.get("low")),
                                    "close": float(c.get("close")), "volume": float(c.get("volume"))
                                }
                                import queue as queue_module
                                try:
                                    ws.candle_queue.put_nowait(enriched)
                                except queue_module.Full:
                                    pass
                            success_count += 1
                            logger.info(f"✅ [{tf}] {sym} 재시도 성공")
                    except Exception as retry_e:
                        logger.error(f"❌ [{tf}] {sym} 재시도 실패: {retry_e}")
                else:
                    logger.error(f"❌ [{tf}] [{idx}/{len(symbols)}] {sym} 실패: {e}")
                    logger.error(f"   스택: {traceback.format_exc()}")
        
        success_rate = (success_count / len(symbols) * 100) if symbols else 0
        logger.info(f"✅ [{tf}] 프리로드 완료: {success_count}/{len(symbols)}개 성공 ({success_rate:.1f}%)")
        total_success += success_count
    
    # 최종 큐 상태
    final_queue_size = ws.candle_queue.qsize() if hasattr(ws, 'candle_queue') else 0
    logger.info(f"✅ 전체 Multi-TF 프리로드 완료: {total_success}건 | 최종 큐: {final_queue_size}")


def preload_symbols(ws: Any, symbols: List[str], timeframe: str, lookback: int, logger: Any):
    """
    WebSocket 초기 데이터 프리로드 (paper/live 공통)
    
    Args:
        ws: WebSocketCollector 인스턴스
        symbols: 심볼 리스트
        timeframe: 타임프레임
        lookback: lookback 기간
        logger: 로거
    """
    logger.info(f"📥 초기 데이터 로드 중 ({len(symbols)}개 심볼)...")
    
    success_count = 0
    for idx, sym in enumerate(symbols, 1):
        try:
            # Rate Limit 대응: 50개마다 2초 대기
            if idx > 50 and (idx - 1) % 50 == 0:
                logger.info(f"⏳ Rate Limit 대응: 2초 대기 중... ({idx-1}개 완료)")
                time.sleep(2)
            
            candles = fetch_history(sym, timeframe, limit=min(lookback, 1000))  # ⭐ Binance API 최대값
            
            if not candles:
                logger.warning(f"⚠️ [{idx}/{len(symbols)}] {sym} 히스토리 데이터 없음")
                continue
            
            for c in candles:
                try:
                    closed_at = int(c.get("closed_at", c.get("time", 0)))
                except Exception as e_time:
                    logger.debug(f"시간 파싱 오류: {e_time}, fallback to time")
                    closed_at = int(c.get("time", 0))
                
                enriched = {
                    "symbol": sym,
                    "timeframe": timeframe,
                    "closed_at": closed_at,
                    "time": closed_at,
                    "open": float(c.get("open")),
                    "high": float(c.get("high")),
                    "low": float(c.get("low")),
                    "close": float(c.get("close")),
                    "volume": float(c.get("volume"))
                }
                # 프리로드 시 큐에 직접 추가 (콜백 없이도 작동)
                import queue as queue_module
                try:
                    ws.candle_queue.put_nowait(enriched)
                except queue_module.Full:
                    logger.warning(f"⚠️ 프리로드 큐 Full! {sym} 캔들 추가 실패")
                except AttributeError:
                    # 백테스트 등 큐가 없는 경우 콜백 사용
                    if ws.on_candle_callback:
                        ws.on_candle_callback(sym, enriched, is_closed=True)
            
            success_count += 1
            # 큐 사이즈 모니터링 (10심볼마다)
            if idx % 10 == 0 or idx == len(symbols):
                queue_size = ws.candle_queue.qsize() if hasattr(ws, 'candle_queue') else 0
                logger.info(f"✅ [{idx}/{len(symbols)}] {sym} 프리로드 완료: {len(candles)}개 캔들 | 큐: {queue_size}")
            else:
                logger.info(f"✅ [{idx}/{len(symbols)}] {sym} 프리로드 완료: {len(candles)}개 캔들")
        except Exception as e:
            import traceback
            logger.error(f"❌ [{idx}/{len(symbols)}] {sym} 프리로드 실패:")
            logger.error(f"   에러 타입: {type(e).__name__}")
            logger.error(f"   에러 메시지: {str(e)}")
            logger.error(f"   스택 트레이스:\n{traceback.format_exc()}")
    
    # 최종 큐 상태 모니터링
    final_queue_size = ws.candle_queue.qsize() if hasattr(ws, 'candle_queue') else 0
    logger.info(f"✅ 전체 심볼 프리로드 완료: {success_count}/{len(symbols)}개 성공 | 최종 큐: {final_queue_size}")


def create_adapters(mode: str, symbols: List[str], config: dict, logger: Any) -> Tuple[Any, Any, Any]:
    """
    모드별 Feed, Broker, Clock 생성 (main.py 모듈화)
    
    Args:
        mode: 'backtest', 'paper', 'live'
        symbols: 심볼 리스트
        config: 전체 설정
        logger: 로거
    
    Returns:
        (feed, broker, clock)
    """
    timeframe = config.get('timeframe', '5m')
    base_timeframe = (config.get('feed', {}) or {}).get('base_timeframe', timeframe)
    lookback = config.get('lookback', 400)
    fees_cfg = config.get('fees', {})
    
    if mode == 'backtest':
        backtest_cfg = config.get('backtest', {})
        data_dir = backtest_cfg.get('data_dir', 'data')
        
        # 기간 설정
        period = backtest_cfg.get('period', 'ten_years')
        periods_cfg = backtest_cfg.get('periods', {})
        period_cfg = periods_cfg.get(period, {})
        start_date = period_cfg.get('start_date')
        end_date = period_cfg.get('end_date')
        
        # 단일/멀티 심볼 판단
        single_symbol = backtest_cfg.get('symbol')
        
        if single_symbol:
            # 단일 심볼 백테스트
            from collectors.historical_collector import HistoricalFeed
            
            # CSV 파일명
            data_file = backtest_cfg.get('data_file')
            if data_file:
                csv_path = Path(data_dir) / data_file
                if not csv_path.exists():
                    csv_path = Path(data_file)
                    if not csv_path.exists():
                        raise FileNotFoundError(f"❌ data_file 없음: {data_file}")
            else:
                csv_filename = f"{single_symbol}_{timeframe}_{start_date}_{end_date}.csv"
                csv_path = Path(data_dir) / csv_filename
                
                if not csv_path.exists():
                    csv_pattern = f"{single_symbol}_{timeframe}_*.csv"
                    csv_files = list(Path(data_dir).glob(csv_pattern))
                    if not csv_files:
                        raise FileNotFoundError(f"❌ CSV 없음: {data_dir}/{csv_pattern}")
                    csv_path = sorted(csv_files)[-1]
                    logger.warning(f"⚠️ 정확한 파일 없음, fallback: {csv_path}")
            
            feed = HistoricalFeed(str(csv_path), symbol=single_symbol, timeframe=timeframe)
            logger.info(f"📊 백테스트 모드: 단일 심볼 ({single_symbol})")
            logger.info(f"   파일: {csv_path}")
        else:
            # 멀티 심볼 백테스트
            from collectors import MultiSymbolHistoricalFeed
            
            feed = MultiSymbolHistoricalFeed(
                symbols=symbols,
                data_dir=data_dir,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"📊 백테스트 모드: 멀티 심볼 ({len(symbols)}개)")
            logger.info(f"   기간: {start_date} ~ {end_date}")
        
        broker = SimBroker(
            fee_rate=fees_cfg.get('taker', 0.0004),
            slippage_pct=fees_cfg.get('slippage', 0.0005)
        )
        clock = SimClock()
    
    elif mode == 'paper':
        # ⭐ PR10 Bug #4: OPEN 포지션 심볼을 WebSocket 구독 목록에 추가
        from common.database import get_db_connection
        
        open_position_symbols = set()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT symbol FROM trading.trades WHERE status = 'OPEN'")
                    rows = cur.fetchall()
                    open_position_symbols = {row[0] for row in rows}
                    
                    if open_position_symbols:
                        logger.info(f"🔓 OPEN 포지션 심볼 발견: {len(open_position_symbols)}개")
                        logger.info(f"   심볼: {', '.join(sorted(open_position_symbols))}")
        except Exception as e:
            logger.warning(f"⚠️ OPEN 포지션 조회 실패 (계속 진행): {e}")
        
        # 심볼 목록 병합 (중복 제거)
        combined_symbols = list(set(symbols) | open_position_symbols)
        added_count = len(combined_symbols) - len(symbols)
        
        if added_count > 0:
            logger.info(f"✅ WebSocket 구독 목록 확장: {len(symbols)}개 → {len(combined_symbols)}개 (+{added_count})")
        
        # 모니터링 설정 주입 (config.yml -> monitoring)
        monitoring_cfg = config.get('monitoring') or {}
        redis_cfg = monitoring_cfg.get('redis') or {}
        # PR7-4: Multi-TF 큐 크기 설정 추가
        queue_size = config.get('system', {}).get('candle_queue_size', 600000)
        ws_cfg = {
            'heartbeat_interval_sec': monitoring_cfg.get('websocket', {}).get('heartbeat_interval_sec', 10),
            'reconnect': monitoring_cfg.get('websocket', {}).get('reconnect', {}),
            'connection_timeout_sec': monitoring_cfg.get('websocket', {}).get('connection_timeout_sec', 30),
            'gap_detection': monitoring_cfg.get('gap_detection', {}),
            'queue_size': queue_size  # ⭐ PR7-4: Multi-TF 큐 크기
        }
        # ⚠️ Paper 모드: WebSocket 생성을 engine.run()으로 지연 (히스토리 로드 자동 시작 방지)
        class WebSocketDelayed:
            def __init__(self, symbols, timeframe, redis_cfg, ws_cfg):
                self.symbols = symbols
                self.timeframe = timeframe  
                self.redis_cfg = redis_cfg
                self.ws_cfg = ws_cfg
                self._actual_ws = None
                logger.info("🔗 [PAPER] WebSocket 설정 준비 완료 (생성은 engine.run()에서)")
            
            def create_actual_websocket(self):
                """실제 WebSocket 생성 및 반환"""
                from collectors.websocket_collector import WebSocketCollector
                logger.info("🔗 [PAPER] 실제 WebSocket 생성 중...")
                self._actual_ws = WebSocketCollector(self.symbols, self.timeframe, 
                                                   redis_cfg=self.redis_cfg, ws_cfg=self.ws_cfg)
                return self._actual_ws
            
            def start(self):
                """실제 WebSocket의 start() 호출"""  
                if self._actual_ws:
                    return self._actual_ws.start()
                    
        feed = WebSocketDelayed(combined_symbols, base_timeframe, redis_cfg=redis_cfg, ws_cfg=ws_cfg)
        
        # 프리로드 정보도 업데이트
        symbols = combined_symbols
        
        broker = PaperBroker(
            fee_rate=fees_cfg.get('taker', 0.0004),
            slippage_pct=fees_cfg.get('slippage', 0.0005)
        )
        clock = LiveClock()
        
        # ⚠️ Paper 모드: WebSocket 시작을 engine.run()으로 지연 (main() 진행 보장)
        logger.info("🔗 WebSocket 준비 완료 (시작은 engine.run()에서)")
        # ws.start()  # 🚫 즉시 시작 방지 - engine.run()에서 처리
        # time.sleep(2)
        
        # PR7-4: Multi-TF 프리로드 (콜백 설정 후 수행하도록 feed 객체에 정보 저장)
        feed._preload_info = {
            'symbols': symbols,
            'strategies_config': config.get('strategies', {}),
            'lookback': lookback,
            'use_multi_tf': True  # PR7-4 플래그
        }
        
        logger.info(f"📄 페이퍼 모드: {len(symbols)}개 심볼 구독 중")
        
        # ⚠️ Paper 모드: WebSocket 즉시 시작 방지 (engine.run() 진행 보장)
        feed._ws_ready_to_start = True  # 시작 준비 플래그
    
    elif mode == 'live':
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET')
        
        if not api_key or not api_secret:
            logger.error("❌ 라이브 모드: API 키 필수")
            sys.exit(1)
        
        # ⭐ PR10 Bug #4: OPEN 포지션 심볼을 WebSocket 구독 목록에 추가
        from common.database import get_db_connection
        
        open_position_symbols = set()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT symbol FROM trading.trades WHERE status = 'OPEN'")
                    rows = cur.fetchall()
                    open_position_symbols = {row[0] for row in rows}
                    
                    if open_position_symbols:
                        logger.info(f"🔓 OPEN 포지션 심볼 발견: {len(open_position_symbols)}개")
                        logger.info(f"   심볼: {', '.join(sorted(open_position_symbols))}")
        except Exception as e:
            logger.warning(f"⚠️ OPEN 포지션 조회 실패 (계속 진행): {e}")
        
        # 심볼 목록 병합 (중복 제거)
        combined_symbols = list(set(symbols) | open_position_symbols)
        added_count = len(combined_symbols) - len(symbols)
        
        if added_count > 0:
            logger.info(f"✅ WebSocket 구독 목록 확장: {len(symbols)}개 → {len(combined_symbols)}개 (+{added_count})")
        
        # 모니터링 설정 주입 (config.yml -> monitoring)
        monitoring_cfg = config.get('monitoring') or {}
        redis_cfg = monitoring_cfg.get('redis') or {}
        # PR7-4: Multi-TF 큐 크기 설정 추가
        queue_size = config.get('system', {}).get('candle_queue_size', 600000)
        ws_cfg = {
            'heartbeat_interval_sec': monitoring_cfg.get('websocket', {}).get('heartbeat_interval_sec', 10),
            'reconnect': monitoring_cfg.get('websocket', {}).get('reconnect', {}),
            'connection_timeout_sec': monitoring_cfg.get('websocket', {}).get('connection_timeout_sec', 30),
            'gap_detection': monitoring_cfg.get('gap_detection', {}),
            'queue_size': queue_size  # ⭐ PR7-4: Multi-TF 큐 크기
        }
        # ⚠️ Live 모드: WebSocket 생성을 engine.run()으로 지연 (히스토리 로드 자동 시작 방지)
        class WebSocketDelayed:
            def __init__(self, symbols, timeframe, redis_cfg, ws_cfg):
                self.symbols = symbols
                self.timeframe = timeframe  
                self.redis_cfg = redis_cfg
                self.ws_cfg = ws_cfg
                self._actual_ws = None
                logger.info("🔗 [LIVE] WebSocket 설정 준비 완료 (생성은 engine.run()에서)")
            
            def create_actual_websocket(self):
                """실제 WebSocket 생성 및 반환"""
                from collectors.websocket_collector import WebSocketCollector
                logger.info("🔗 [LIVE] 실제 WebSocket 생성 중...")
                self._actual_ws = WebSocketCollector(self.symbols, self.timeframe, 
                                                   redis_cfg=self.redis_cfg, ws_cfg=self.ws_cfg)
                return self._actual_ws
            
            def start(self):
                """실제 WebSocket의 start() 호출"""  
                if self._actual_ws:
                    return self._actual_ws.start()
                    
        feed = WebSocketDelayed(combined_symbols, base_timeframe, redis_cfg=redis_cfg, ws_cfg=ws_cfg)
        
        # 프리로드 정보도 업데이트
        symbols = combined_symbols
        
        broker = LiveBroker(
            api_key, api_secret,
            fee_rate=fees_cfg.get('taker', 0.0004)
        )
        clock = LiveClock()
        
        # ⚠️ Live 모드: WebSocket 시작을 engine.run()으로 지연 (main() 진행 보장)
        logger.info("🔗 WebSocket 준비 완료 (시작은 engine.run()에서)")
        # ws.start()  # 🚫 즉시 시작 방지 - engine.run()에서 처리
        # time.sleep(2)
        
        # PR7-4: Multi-TF 프리로드 (콜백 설정 후 수행하도록 feed 객체에 정보 저장)
        feed._preload_info = {
            'symbols': symbols,
            'strategies_config': config.get('strategies', {}),
            'lookback': lookback,
            'use_multi_tf': True  # PR7-4 플래그
        }
        
        logger.info(f"🔴 라이브 모드: {len(symbols)}개 심볼 실거래")
    
    else:
        raise ValueError(f"❌ 알 수 없는 모드: {mode}")
    
    return feed, broker, clock
