#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Generator
================
신호 생성 및 검증 모듈

- process_candle(): 캔들 처리 메인 로직
- generate_signal(): 신호 생성 (전략 호출)
- validate_signal(): 신호 검증 (MTF, 쿨다운)
"""
from typing import Dict, Any, Optional
from collections import deque
from binance.client import Client as BinanceClient
import pandas as pd
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from uuid import uuid4

from common.config_loader import load_config
from common.logger import setup_logger
from common.database import save_signal_to_db
from common.messaging import format_signal_alert
from common.calculations import round_tick, price_levels, leverage_suggestion
from common.utils import buffer_to_df, qty_notional_margin, maybe_regime_alert
from indicators import add_indicators, regime
from strategies import scalping, daytrade, swing, swing_bb

logger = setup_logger('signals', log_type='signals')


class SignalGenerator:
    """신호 생성 및 검증"""
    
    def __init__(self, config: dict, strategy_modules: dict = None, activity_tracker=None):
        """
        Args:
            config: 설정 딕셔너리 (CFG)
            strategy_modules: 전략 dict (PHASE23-2: {name: {"instance": ..., "params": ...}} 형태)
            activity_tracker: PHASE28-10 Guard Telemetry
        """
        self.config = config
        self.activity_tracker = activity_tracker
        self.buffers: dict = {}  # 심볼별 캠들 버퍼
        self.last_alert_ts: dict = {}  # 쿨다운
        self.last_regime: dict = {}  # 레짐
        
        # ⭐ MTF 캠시 (API 호출 최소화)
        self.mtf_cache: dict = {}  # {symbol: {'regime': str, 'ts': int}}
        self.mtf_cache_ttl = 300000  # 5분 (ms)
        
        # PHASE23-2: strategy_modules에서 instance 추출
        if strategy_modules:
            # load_strategies()가 반환하는 형태: {name: {"instance": ..., "params": ...}}
            self.strategy_modules = {}
            for name, strategy_info in strategy_modules.items():
                if isinstance(strategy_info, dict) and "instance" in strategy_info:
                    # PHASE23-2 형태
                    self.strategy_modules[name] = strategy_info["instance"]
                else:
                    # Legacy 형태 (모듈 직접 전달)
                    self.strategy_modules[name] = strategy_info
        else:
            # 기본값 (legacy)
            self.strategy_modules = {
                "1m": scalping, "3m": scalping,
                "5m": daytrade,
                "15m": swing
            }
        
        # 지표 파라미터
        self.EMA_FAST = config.get("ema_fast", 8)
        self.EMA_MID = config.get("ema_mid", 21)
        self.EMA_SLOW = config.get("ema_slow", 50)
        self.RSI_LEN = config.get("rsi_len", 14)
        self.MACD_FAST = config.get("macd_fast", 12)
        self.MACD_SLOW = config.get("macd_slow", 26)
        self.MACD_SIGNAL = config.get("macd_signal", 9)
        self.BB_LEN = config.get("bb_len", 20)
        self.BB_STD = config.get("bb_std", 2.0)
        self.ATR_LEN = config.get("atr_len", 14)
    
    def process_candle(self, symbol: str, candle_data: dict, tg_callback=None) -> Optional[dict]:
        """
        캔들 처리 메인 로직 (기존 on_message 로직)
        
        Args:
            symbol: 심볼
            candle_data: 캔들 데이터
            tg_callback: 텔레그램 콜백 함수
        
        Returns:
            신호 딕셔너리 또는 None
        """
        # Buffer 초기화
        if symbol not in self.buffers:
            self.buffers[symbol] = deque(maxlen=self.config["lookback"])
        
        buf = self.buffers[symbol]
        
        # Buffer 업데이트
        if buf and buf[-1]["time"] == candle_data["time"]:
            buf[-1] = candle_data
        else:
            buf.append(candle_data)
        
        # 충분한 데이터 확인
        if len(buf) < 230:
            return None
        
        # DataFrame 생성
        df = buffer_to_df(symbol, {symbol: buf})
        
        # 지표 계산
        df_ind = add_indicators(
            df, self.EMA_FAST, self.EMA_MID, self.EMA_SLOW,
            self.RSI_LEN, self.MACD_FAST, self.MACD_SLOW, self.MACD_SIGNAL,
            self.BB_LEN, self.BB_STD, self.ATR_LEN,
            self.config["vol_ma_len"]
        )
        
        # Intra-candle 레짐 확인
        reg_now = regime(df_ind.iloc[-1])
        if tg_callback:
            maybe_regime_alert(symbol, reg_now, self.last_regime, 
                             self.config["enable_regime_alert"], tg_callback)
        
        # 신호 생성
        signal = self.generate_signal(df_ind)
        
        if not signal or not signal["side"]:
            return None
        
        # 신호 검증
        if not self.validate_signal(symbol, signal, df_ind):
            return None
        
        # 신호 반환
        signal["symbol"] = symbol
        return signal
    
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        신호 생성 (PHASE23-2: BaseStrategy.compute_signal() 호출)
        
        Args:
            df: 지표가 계산된 DataFrame
        
        Returns:
            신호 딕셔너리 (Ensemble Score V2 필드 포함)
        """
        from common.registry.base_strategy import BaseStrategy
        
        # Config 병합
        strategy_config = dict(self.config)
        
        # 단일 전략 모드
        if len(self.strategy_modules) == 1:
            strategy = list(self.strategy_modules.values())[0]
            
            # PHASE23-2: BaseStrategy 인스턴스면 compute_signal() 호출
            if isinstance(strategy, BaseStrategy):
                return strategy.compute_signal(df, config=strategy_config)
            # Legacy: 모듈이면 signal_logic() 호출
            elif hasattr(strategy, 'signal_logic'):
                return strategy.signal_logic(df, strategy_config)
            else:
                logger.error(f"❌ 전략에 compute_signal/signal_logic 메서드 없음: {type(strategy)}")
                return {'side': None, 'reason': 'invalid_strategy'}
        
        # 앙상블 모드: 타임프레임에 따라 전략 선택
        tf = strategy_config.get("timeframe", "5m")
        strategy = self.strategy_modules.get(tf, list(self.strategy_modules.values())[0])
        
        # PHASE23-2: BaseStrategy 인스턴스면 compute_signal() 호출
        if isinstance(strategy, BaseStrategy):
            return strategy.compute_signal(df, config=strategy_config)
        # Legacy: 모듈이면 signal_logic() 호출
        elif hasattr(strategy, 'signal_logic'):
            return strategy.signal_logic(df, strategy_config)
        else:
            logger.error(f"❌ 전략에 compute_signal/signal_logic 메서드 없음: {type(strategy)}")
            return {'side': None, 'reason': 'invalid_strategy'}
    
    def validate_signal(self, symbol: str, signal: dict, df: pd.DataFrame) -> bool:
        """
        신호 검증
        
        Args:
            symbol: 심볼
            signal: 신호 딕셔너리
            df: DataFrame
        
        Returns:
            검증 통과 여부
        """
        # 1. 거래량 필터
        if self.config.get("enable_vol_spike_filter", False):
            last = df.iloc[-1]
            if last["vol_ma"] > 0 and last["volume"] > last["vol_ma"] * self.config["vol_spike_mult"]:
                logger.info(f"⚠️ {symbol} 거래량 급증으로 신호 보류")
                # ⭐ PHASE28-10: Filter Telemetry
                if self.activity_tracker:
                    self.activity_tracker.record_guard_block(symbol, "FILTER_VOLUME_SPIKE")
                return False
        
        # 2. 세션 화이트리스트 확인 (UTC)
        current_ts = signal.get("ts", 0)
        if not self._session_allowed(current_ts):
            curr_min = (current_ts or 0) // 60000
            d = getattr(self, "_last_session_log_minute", {})
            if d.get(symbol) != curr_min:
                logger.info(f"⏸ {symbol} 세션 비허용")
                d[symbol] = curr_min
                self._last_session_log_minute = d
            # ⭐ PHASE28-10: Filter Telemetry
            if self.activity_tracker:
                self.activity_tracker.record_guard_block(symbol, "FILTER_SESSION_NOT_ALLOWED")
            return False

        # 3. 레짐 필터 (동일 TF)
        try:
            if self.config.get("enable_regime_filter") or self.config.get("filters", {}).get("regime_filter"):
                last = df.iloc[-1]
                reg_now = regime(last)
                if signal.get("side") == "LONG":
                    if reg_now not in ("상승장", "횡보장"):
                        logger.info(f"⏸ {symbol} 레짐 비허용: {reg_now}")
                        # ⭐ PHASE28-10: Filter Telemetry
                        if self.activity_tracker:
                            self.activity_tracker.record_guard_block(symbol, "FILTER_REGIME_NOT_ALLOWED")
                        return False
                elif signal.get("side") == "SHORT":
                    if reg_now not in ("하락장", "횡보장"):
                        logger.info(f"⏸ {symbol} 레짐 비허용: {reg_now}")
                        # ⭐ PHASE28-10: Filter Telemetry
                        if self.activity_tracker:
                            self.activity_tracker.record_guard_block(symbol, "FILTER_REGIME_NOT_ALLOWED")
                        return False
        except Exception:
            # 안전 장치: 오류 시 통과
            pass

        # 4. 트렌드 정렬 필터 (EMA 정렬 + 기울기)
        try:
            trend_required = self.config.get("require_trend_align") or self.config.get("filters", {}).get("require_trend_align")
            if trend_required:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                ema_fast_ok_long = last.get("ema_fast", 0) >= last.get("ema_mid", 0) >= last.get("ema_slow", 0)
                ema_fast_ok_short = last.get("ema_fast", 0) <= last.get("ema_mid", 0) <= last.get("ema_slow", 0)
                slope_mid = (last.get("ema_mid", 0) - prev.get("ema_mid", 0))
                if signal.get("side") == "LONG":
                    if not (ema_fast_ok_long and slope_mid > 0):
                        logger.info(f"⏸ {symbol} 트렌드 미정렬(LONG)")
                        # ⭐ PHASE28-10: Filter Telemetry
                        if self.activity_tracker:
                            self.activity_tracker.record_guard_block(symbol, "FILTER_TREND_NOT_ALIGNED")
                        return False
                elif signal.get("side") == "SHORT":
                    if not (ema_fast_ok_short and slope_mid < 0):
                        logger.info(f"⏸ {symbol} 트렌드 미정렬(SHORT)")
                        # ⭐ PHASE28-10: Filter Telemetry
                        if self.activity_tracker:
                            self.activity_tracker.record_guard_block(symbol, "FILTER_TREND_NOT_ALIGNED")
                        return False
        except Exception:
            pass

        # 5. MTF 확인 (⭐ current_ts 전달 - 캐시 활용, 백테스트는 DF 리샘플 기반 오프라인 확인)
        if not self._mtf_confirm(symbol, signal["side"], current_ts, df):
            logger.info(f"⏸ {symbol} 멀티TF 미정렬")
            # ⭐ PHASE28-10: Filter Telemetry
            if self.activity_tracker:
                self.activity_tracker.record_guard_block(symbol, "FILTER_MTF_NOT_CONFIRMED")
            return False
        
        # 6. 쿨다운 체크
        if not self._should_alert(symbol, signal["side"], signal["ts"]):
            # ⭐ PHASE28-10: Filter Telemetry
            if self.activity_tracker:
                self.activity_tracker.record_guard_block(symbol, "FILTER_COOLDOWN_ACTIVE")
            return False
        
        # 7. 최소 손익비(min_rr_required) 검증 (config: entries.min_rr_required 또는 min_rr_required)
        try:
            min_rr = self.config.get('entries', {}).get('min_rr_required', self.config.get('min_rr_required', None))
            if min_rr:
                entry = signal.get('entry')
                sl = signal.get('sl')
                tp = signal.get('tp')
                if entry and sl and tp:
                    if signal.get('side') == 'LONG':
                        risk = max(entry - sl, 1e-9)
                        reward = max(tp - entry, 0.0)
                    else:
                        risk = max(sl - entry, 1e-9)
                        reward = max(entry - tp, 0.0)
                    rr = (reward / risk) if risk > 0 else 0.0
                    if rr < float(min_rr):
                        logger.info(f"⏸ {symbol} RR 미달: {rr:.2f} < {min_rr}")
                        # ⭐ PHASE28-10: Filter Telemetry
                        if self.activity_tracker:
                            self.activity_tracker.record_guard_block(symbol, "FILTER_RR_BELOW_MIN")
                        return False
        except Exception:
            pass

        return True
    
    def _mtf_confirm(self, symbol: str, side: str, current_ts: int = None, df: pd.DataFrame = None) -> bool:
        """
        멀티타임프레임 확인 (캐싱 적용)
        
        ⭐ 개선: 캐시를 사용하여 API 호출 최소화
        - TTL: 5분 (mtf_cache_ttl)
        - 캐시 히트 시 즉시 반환 (빠름!)
        - 캐시 미스 시 API 호출 후 캐싱
        """
        if not self.config.get("enable_mtf_confirm") or not self.config.get("require_htf_aligned"):
            return True
        
        # 백테스트에서는 DF 리샘플 기반 오프라인 확인 사용 (기본값: 사용)
        try:
            mode = self.config.get('mode', 'paper')
        except Exception:
            mode = 'paper'
        use_offline_mtf = bool((self.config.get('backtest', {}) or {}).get('use_offline_mtf', True))
        
        if mode == 'backtest' and use_offline_mtf and df is not None and not df.empty:
            try:
                # 요청 HTF
                htf = str(self.config.get("htf", "1h")).strip().lower()
                # time 컬럼을 datetime 인덱스로 변환
                df_local = df.copy()
                if 'time' in df_local.columns:
                    if not isinstance(df_local['time'].iloc[-1], pd.Timestamp):
                        df_local['time'] = pd.to_datetime(df_local['time'], unit='ms', utc=True)
                    df_idx = df_local.set_index('time')
                elif 'closed_at' in df_local.columns:
                    df_local['closed_at'] = pd.to_datetime(df_local['closed_at'], unit='ms', utc=True)
                    df_idx = df_local.set_index('closed_at')
                else:
                    # 시간 정보 없으면 통과
                    return True
                
                # 베이스 간격 추정 (분)
                diffs = df_idx.index.to_series().diff().dropna()
                base_min = int(diffs.dt.total_seconds().mode().iloc[0] // 60) if not diffs.empty else 0
                
                # HTF 간격(분) 계산
                def _tf_to_minutes(tf: str) -> int:
                    if tf.endswith('m'):
                        return int(tf[:-1])
                    if tf.endswith('h'):
                        return int(tf[:-1]) * 60
                    if tf.endswith('d'):
                        return int(tf[:-1]) * 60 * 24
                    try:
                        return int(tf)
                    except Exception:
                        return 0
                req_min = _tf_to_minutes(htf)
                
                # 리샘플 또는 최근 바 사용
                if base_min > 0 and req_min >= base_min and (req_min % base_min == 0):
                    rule = f"{req_min}T"
                    resampled = df_idx.resample(rule, label='right', closed='right').agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna(subset=['open','high','low','close']).reset_index()
                    # 지표 재계산
                    df_htf = add_indicators(
                        resampled,
                        self.EMA_FAST, self.EMA_MID, self.EMA_SLOW,
                        self.RSI_LEN, self.MACD_FAST, self.MACD_SLOW, self.MACD_SIGNAL,
                        self.BB_LEN, self.BB_STD, self.ATR_LEN, self.config.get("vol_ma_len", 20)
                    )
                    last = df_htf.iloc[-1]
                else:
                    # 다운샘플 불가 또는 간격 추정 실패 시 현재 바로 판정
                    last = df_local.iloc[-1]
                
                reg = regime(last)
                if side == "LONG":
                    return reg in ("상승장", "횡보장")
                else:
                    return reg in ("하락장", "횡보장")
            except Exception as e:
                logger.debug(f"오프라인 MTF 확인 실패, API 경로로 폴백: {e}")
                # 아래 API 경로로 폴백
        
        # ⭐ 캐시 확인
        if symbol in self.mtf_cache:
            cache_entry = self.mtf_cache[symbol]
            if current_ts and (current_ts - cache_entry['ts']) < self.mtf_cache_ttl:
                # 캐시 히트! (5분 이내)
                reg = cache_entry['regime']
                logger.debug(f"⚡ MTF 캐시 히트: {symbol} = {reg}")
                
                if side == "LONG":
                    return reg in ("상승장", "횡보장")
                else:
                    return reg in ("하락장", "횡보장")
        
        # ⭐ 캐시 미스 → API 호출
        try:
            logger.debug(f"🔄 MTF API 호출: {symbol}")
            client = BinanceClient()
            klines = client.futures_klines(symbol=symbol, interval=self.config.get("htf", "1h"), limit=250)
            df = pd.DataFrame(klines, columns=["time","open","high","low","close","volume","close_time","quote_vol","trades","taker_buy_base","taker_buy_quote","ignore"])
            df = df[["time","open","high","low","close","volume"]].astype(float)
            df = add_indicators(df, self.EMA_FAST, self.EMA_MID, self.EMA_SLOW, 
                              self.RSI_LEN, self.MACD_FAST, self.MACD_SLOW, self.MACD_SIGNAL,
                              self.BB_LEN, self.BB_STD, self.ATR_LEN, self.config.get("vol_ma_len", 20))
            last = df.iloc[-1]
            reg = regime(last)
            
            # ⭐ 캐시 저장
            self.mtf_cache[symbol] = {
                'regime': reg,
                'ts': current_ts or int(datetime.now().timestamp() * 1000)
            }
            logger.info(f"✅ MTF 캐시 갱신: {symbol} = {reg}")
            
            if side == "LONG":
                return reg in ("상승장", "횡보장")
            else:
                return reg in ("하락장", "횡보장")
        except Exception as e:
            logger.error(f"❌ MTF 확인 실패: {e}")
            return True  # 실패 시 통과
    
    def _should_alert(self, symbol: str, side: str, ts: int) -> bool:
        """쿨다운 체크"""
        if not side:
            return False
        
        key = f"{symbol}_{side}"
        prev = self.last_alert_ts.get(key)
        
        tf = self.config["timeframe"]
        if tf.endswith("m"):
            ms = int(tf[:-1]) * 60 * 1000
        elif tf.endswith("h"):
            ms = int(tf[:-1]) * 60 * 60 * 1000
        elif tf.endswith("d"):
            ms = int(tf[:-1]) * 24 * 60 * 60 * 1000
        else:
            ms = 5 * 60 * 1000
        
        # PHASE28-1-FIX: cooldown_candles 기본값 0 (FlowGuardian이 쿨다운 관리)
        cooldown = ms * self.config.get("cooldown_candles", 0)
        
        if prev and ts - prev < cooldown:
            return False
        
        self.last_alert_ts[key] = ts
        return True

    def _session_allowed(self, ts: int) -> bool:
        sessions = self.config.get('session_whitelist') or self.config.get('filters', {}).get('session_whitelist')
        if not sessions:
            return True
        windows_local = self.config.get('session_windows_local', {})
        use_windows = None
        dt = None
        if windows_local and ZoneInfo is not None:
            tz_name = ((self.config.get('system') or {}).get('timezone')) or 'UTC'
            try:
                dt = datetime.fromtimestamp(ts / 1000, tz=ZoneInfo(tz_name))
                use_windows = windows_local
            except Exception:
                dt = None
        if dt is None:
            windows_utc = self.config.get('session_windows_utc', {})
            if not windows_utc:
                return True
            try:
                dt = datetime.utcfromtimestamp(ts / 1000)
            except Exception:
                return True
            use_windows = windows_utc
        now_min = dt.hour * 60 + dt.minute
        for name in sessions:
            for w in (use_windows.get(name, []) if isinstance(use_windows.get(name, []), list) else []):
                try:
                    sh, sm = [int(x) for x in str(w.get('start', '00:00')).split(':')]
                    eh, em = [int(x) for x in str(w.get('end', '23:59')).split(':')]
                except Exception:
                    continue
                smin = sh * 60 + sm
                emin = eh * 60 + em
                if smin <= emin:
                    if smin <= now_min <= emin:
                        return True
                else:
                    if now_min >= smin or now_min <= emin:
                        return True
        return False
