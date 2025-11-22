#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCALPING Strategy V3 (PHASE12)
=================================
3분봉 기반 스캘핑 전략 (EMA Fresh Trend + Optional MR)

 PHASE12: 3m 타임프레임 전환
- PHASE11-D의 Fresh Cross + Trend-Aware 로직 유지
- Pattern A/B (Trend-Following) 집중
- Optional Mean-Reversion (BB Bounce) 추가 (기본 OFF)
- 목표: 10~40건/7일, Winrate 20%+, PF 0.7+

전략 철학:
- 타임프레임: 3m (3분봉)
- 보유 시간: 짧은 구간 (수분 ~ 30분 이내)
- RR: 1.5 (3m 변동성 대응)
- 빈도: 적정 거래 빈도

신호 조건 (LONG):
1. Pattern A: Fresh Bullish Trend + price > ema_fast + RSI < 30
2. Pattern B: Fresh Bullish Trend + price > ema_fast + Volume Spike
3. Pattern MR (Optional): price <= BB Lower + RSI < 25

신호 조건 (SHORT):
1. Pattern A: Fresh Bearish Trend + price < ema_fast + RSI > 70
2. Pattern B: Fresh Bearish Trend + price < ema_fast + Volume Spike
3. Pattern MR (Optional): price >= BB Upper + RSI > 75

위험 관리:
- SL: ATR 기반 동적 손절 (atr_mult_sl: 1.2)
- TP: RR 1.5 (3m 기준)
- 최대 보유: 30분 (config 설정)
- 전략별 쿨다운: 5초 (3m 빈도 대응)

 주의:
이 버전은 튜닝 전 베이스라인입니다.
향후 Optuna 튜닝으로 파라미터 최적화 예정.
"""
from typing import Dict, Any
import pandas as pd
import logging

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime

logger = logging.getLogger(__name__)

# 전역 플래그: 파라미터 로그는 1회만 출력
_PARAMS_LOGGED = False


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    SCALPING V2 전략: EMA 교차 + RSI 극단 + 모멘텀 (1분봉 고빈도)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정 (CFG)
    
    Returns:
        dict: 신호 정보
    
    전략 로직 (PHASE9-6):
    - 1분봉 기반 고빈도 스캘핑
    - LONG: EMA 골든크로스 + RSI < 30 + higher low
    - SHORT: EMA 데드크로스 + RSI > 70 + lower high
    - RR: 1.2~1.5 (작은 RR, 빠른 청산)
    - 최대 보유: 30분
    
     이 버전은 튜닝 전 초기 뼈대(V1)입니다.
    """
    global _PARAMS_LOGGED
    
    # PHASE22-1: leverage config 검증
    lv = config.get("leverage", {})
    if not all(k in lv for k in ("min", "max", "default")):
        return {"direction": None, "reason": "leverage_config_incomplete"}
    
    # 데이터 충분성 검사 (최소 60개 캔들 필요)
    min_bars = config.get('min_bars_for_signal', 60)
    if len(df) < min_bars:
        return {"direction": None, "reason": "데이터 부족"}
    
    # 현재 캔들
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 기본 정보
    reg = regime(last)
    price = float(last["close"])
    atr = float(last["atr"])
    atr_pct = atr / price
    
    #  PHASE9-6: 파라미터 로드 및 초기화 로그 (1회만)
    rsi_oversold = config.get('rsi_oversold', 30)
    rsi_overbought = config.get('rsi_overbought', 70)
    rsi_neutral_min = config.get('rsi_neutral_min', 40)
    rsi_neutral_max = config.get('rsi_neutral_max', 60)
    
    ema_fast_len = config.get('ema_fast', 8)
    ema_slow_len = config.get('ema_slow', 21)
    
    momentum_lookback = config.get('momentum_lookback', 5)
    volume_mult = config.get('volume_mult', 1.3)
    
    # 🔧 PHASE10.5: Optional 조건 플래그
    momentum_enabled = config.get('momentum_enabled', True)  # 모멘텀 필터 사용 여부
    volume_required = config.get('volume_required', True)    # 거래량 필터 필수 여부
    
    rr = config.get('rr', 1.3)
    max_hold_minutes = config.get('max_hold_minutes', 30)
    atr_mult_sl = config.get('atr_mult_sl', 0.8)
    
    allow_short = (config.get('filters', {}) or {}).get('allow_short', True)
    
    if not _PARAMS_LOGGED:
        logger.info("=" * 60)
        logger.info("[SCALPING V2 INIT] 파라미터 로드 완료 (PHASE9-6)")
        logger.info("=" * 60)
        logger.info(f" 신호 조건:")
        logger.info(f"  - RSI 과매도: < {rsi_oversold}")
        logger.info(f"  - RSI 과매수: > {rsi_overbought}")
        logger.info(f"  - RSI 중립: {rsi_neutral_min}~{rsi_neutral_max}")
        logger.info(f"  - EMA fast: {ema_fast_len}, slow: {ema_slow_len}")
        logger.info(f"  - 모멘텀 lookback: {momentum_lookback}개 캔들")
        logger.info(f"  - 거래량 배수: {volume_mult}x")
        logger.info(f" 위험 관리:")
        logger.info(f"  - RR: {rr}")
        logger.info(f"  - SL 배수: {atr_mult_sl}x ATR")
        logger.info(f"  - 최대 보유: {max_hold_minutes}분")
        logger.info(f"  - 숏 허용: {allow_short}")
        logger.info("=" * 60)
        _PARAMS_LOGGED = True
    
    # ========================================
    # 1. EMA 교차 감지
    # ========================================
    ema_fast = float(last["ema_fast"])
    ema_slow = float(last["ema_slow"])
    ema_fast_prev = float(prev["ema_fast"])
    ema_slow_prev = float(prev["ema_slow"])
    
    # 골든크로스: fast EMA가 slow EMA를 상향 돌파
    golden_cross = (ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev)
    # 데드크로스: fast EMA가 slow EMA를 하향 돌파
    dead_cross = (ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev)
    
    # EMA 상승/하락 추세 (크로스 없어도 정렬)
    ema_bullish = ema_fast > ema_slow
    ema_bearish = ema_fast < ema_slow
    
    # ========================================
    # 2. RSI 극단 구간 감지
    # ========================================
    rsi = float(last["rsi"])
    rsi_prev = float(prev["rsi"])
    
    # 과매도 구간 (< 30) 또는 과매도에서 반등 중
    rsi_oversold_signal = (rsi < rsi_oversold) or (rsi_prev < rsi_oversold and rsi > rsi_prev)
    # 과매수 구간 (> 70) 또는 과매수에서 하락 중
    rsi_overbought_signal = (rsi > rsi_overbought) or (rsi_prev > rsi_overbought and rsi < rsi_prev)
    
    # RSI 중립 구간 (40~60)
    rsi_neutral = (rsi_neutral_min <= rsi <= rsi_neutral_max)
    
    # ========================================
    # 3. 모멘텀 패턴 감지
    # ========================================
    if len(df) >= momentum_lookback + 1:
        recent = df.iloc[-(momentum_lookback+1):].copy()
        
        # Higher low 패턴: 최근 저점들이 상승 추세
        lows = recent["low"].values
        higher_low = all(lows[i] >= lows[i-1] * 0.998 for i in range(1, len(lows)))
        
        # Lower high 패턴: 최근 고점들이 하락 추세
        highs = recent["high"].values
        lower_high = all(highs[i] <= highs[i-1] * 1.002 for i in range(1, len(highs)))
    else:
        higher_low = False
        lower_high = False
    
    # ========================================
    # 4. 거래량 확인
    # ========================================
    volume = float(last["volume"])
    vol_ma = float(last["vol_ma"])
    vol_spike = volume > vol_ma * volume_mult
    
    # ========================================
    # 5. 신호 조건 결합 (PHASE11: 3-Pattern OR 로직)
    # ========================================
    
    # ========================================
    # 5-1. PHASE12: Fresh Cross Tracking (Lookback)
    # ========================================
    # ⭐ Late Entry 방지: 최근 N개 캔들 내 크로스 탐색 (3m 기준)
    
    # Config 파라미터 (PHASE12: 3m 기준으로 조정)
    max_cross_age = config.get('strategies', {}).get('scalping', {}).get('max_cross_age_candles', 12)  # 3m × 12 = 36분
    use_price_align = config.get('strategies', {}).get('scalping', {}).get('use_price_alignment', True)
    
    # Lookback window: 최근 N개 캔들 + 여유 (cross 탐지 보장)
    lookback = min(max_cross_age + 10, len(df))
    recent_df = df.iloc[-lookback:] if lookback > 0 else df
    
    # 최근 구간에서 크로스 탐색
    cross_dir = 0  # 0=unknown, 1=bullish, -1=bearish
    cross_age = 999  # 기본값: 매우 오래됨
    
    if len(recent_df) >= 2:
        # 현재 방향
        curr_dir = 1 if ema_fast > ema_slow else (-1 if ema_fast < ema_slow else 0)
        
        # 역순으로 탐색하며 마지막 크로스 찾기
        for i in range(len(recent_df)-1, 0, -1):
            fast_now = float(recent_df.iloc[i]['ema_fast'])
            slow_now = float(recent_df.iloc[i]['ema_slow'])
            fast_prev = float(recent_df.iloc[i-1]['ema_fast'])
            slow_prev = float(recent_df.iloc[i-1]['ema_slow'])
            
            # Golden Cross: fast가 slow를 상향 돌파
            if fast_now > slow_now and fast_prev <= slow_prev:
                cross_dir = 1
                cross_age = len(recent_df) - 1 - i
                break
            # Death Cross: fast가 slow를 하향 돌파
            elif fast_now < slow_now and fast_prev >= slow_prev:
                cross_dir = -1
                cross_age = len(recent_df) - 1 - i
                break
        
        # Cross를 찾지 못한 경우, 현재 방향 사용 (그러나 age는 999로 유지)
        if cross_age == 999:
            cross_dir = curr_dir
    
    # Fresh Trend 조건
    bullish_trend_fresh = (cross_dir == 1) and (cross_age <= max_cross_age)
    bearish_trend_fresh = (cross_dir == -1) and (cross_age <= max_cross_age)
    
    # Price Alignment (가격이 EMA 방향과 일치)
    price_above_fast = price > ema_fast
    price_below_fast = price < ema_fast
    
    # ========================================
    # 5-2. PHASE12: Trend-Aware Patterns (A/B)
    # ========================================
    # Core Patterns: Fresh Trend + Price Alignment + Filter
    
    # Config에서 Pattern 토글 가져오기
    enable_a = config.get('strategies', {}).get('scalping', {}).get('enable_pattern_a', True)
    enable_b = config.get('strategies', {}).get('scalping', {}).get('enable_pattern_b', True)
    enable_c = config.get('strategies', {}).get('scalping', {}).get('enable_pattern_c', False)  # PHASE12: 미사용
    enable_d = config.get('strategies', {}).get('scalping', {}).get('enable_pattern_d', False)  # PHASE12: 미사용
    enable_e = config.get('strategies', {}).get('scalping', {}).get('enable_pattern_e', False)  # PHASE12: 미사용
    
    # LONG 조건 (Fresh Bullish Trend 기반)
    if use_price_align:
        trend_long_ok = bullish_trend_fresh and price_above_fast
    else:
        trend_long_ok = bullish_trend_fresh
    
    pattern_a_long = enable_a and trend_long_ok and rsi_oversold_signal
    pattern_b_long = enable_b and trend_long_ok and vol_spike
    pattern_c_long = enable_c and rsi_oversold_signal  # PHASE12: 미사용
    pattern_d_long = enable_d and vol_spike  # PHASE12: 미사용
    pattern_e_long = enable_e and trend_long_ok and rsi_oversold_signal and vol_spike  # PHASE12: 미사용
    
    # SHORT 조건 (Fresh Bearish Trend 기반)
    if use_price_align:
        trend_short_ok = bearish_trend_fresh and price_below_fast
    else:
        trend_short_ok = bearish_trend_fresh
    
    pattern_a_short = enable_a and trend_short_ok and rsi_overbought_signal
    pattern_b_short = enable_b and trend_short_ok and vol_spike
    pattern_c_short = enable_c and rsi_overbought_signal  # PHASE12: 미사용
    pattern_d_short = enable_d and vol_spike  # PHASE12: 미사용
    pattern_e_short = enable_e and trend_short_ok and rsi_overbought_signal and vol_spike  # PHASE12: 미사용
    
    # ========================================
    # 5-3. PHASE12: Optional Mean-Reversion (BB + RSI)
    # ========================================
    enable_mr = config.get('strategies', {}).get('scalping', {}).get('enable_mean_reversion', False)
    
    pattern_mr_long = False
    pattern_mr_short = False
    
    if enable_mr:
        # BB 밴드 (indicators에서 이미 계산됨)
        bb_upper = float(last.get('bb_upper', price))
        bb_lower = float(last.get('bb_lower', price))
        
        # MR 전용 RSI 임계값
        rsi_oversold_mr = config.get('strategies', {}).get('scalping', {}).get('rsi_oversold_mr', 25)
        rsi_overbought_mr = config.get('strategies', {}).get('scalping', {}).get('rsi_overbought_mr', 75)
        
        # MR LONG: BB Lower Bounce + RSI Oversold
        pattern_mr_long = (price <= bb_lower * 1.002) and (rsi < rsi_oversold_mr)
        
        # MR SHORT: BB Upper Bounce + RSI Overbought
        pattern_mr_short = (price >= bb_upper * 0.998) and (rsi > rsi_overbought_mr)
    
    # 최종 신호 (Trend-Following + Mean-Reversion)
    signal_long = pattern_a_long or pattern_b_long or pattern_c_long or pattern_d_long or pattern_e_long or pattern_mr_long
    signal_short = pattern_a_short or pattern_b_short or pattern_c_short or pattern_d_short or pattern_e_short or pattern_mr_short
    
    # ========================================
    # 디버그 로그 (500캔들마다) - PHASE10 성능 최적화
    # ========================================
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][SCALPING] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f}")
        logger.info(f"  📈 EMA: fast={ema_fast:.2f}, slow={ema_slow:.2f} | bullish={ema_bullish}, bearish={ema_bearish}")
        logger.info(f"  🔀 EMA Cross: golden={golden_cross}, dead={dead_cross}")
        logger.info(f"  ⭐ PHASE11-D Fresh Trend: dir={cross_dir} age={cross_age}/{max_cross_age} | bullish_fresh={bullish_trend_fresh}, bearish_fresh={bearish_trend_fresh}")
        logger.info(f"  ⭐ Price Alignment: above_fast={price_above_fast}, below_fast={price_below_fast}")
        logger.info(f"  📉 RSI: {rsi:.1f} | oversold_signal={rsi_oversold_signal}, overbought_signal={rsi_overbought_signal}")
        logger.info(f"  📦 Volume: {volume:.0f} vs ma={vol_ma:.0f} | spike={vol_spike}")
        logger.info(f"  🎯 Pattern A LONG: {pattern_a_long} (Fresh+RSI) [{'ON' if enable_a else 'OFF'}]")
        logger.info(f"  🎯 Pattern B LONG: {pattern_b_long} (Fresh+Volume) [{'ON' if enable_b else 'OFF'}]")
        logger.info(f"  🎯 Pattern C LONG: {pattern_c_long} (RSI alone) [{'ON' if enable_c else 'OFF'}]")
        logger.info(f"  🎯 Pattern D LONG: {pattern_d_long} (Volume alone) [{'ON' if enable_d else 'OFF'}]")
        logger.info(f"  🎯 Pattern E LONG: {pattern_e_long} (Fresh+RSI+Volume) [{'ON' if enable_e else 'OFF'}]")
        logger.info(f"  🎯 Pattern MR LONG: {pattern_mr_long} (BB Lower+RSI) [{'ON' if enable_mr else 'OFF'}]")
        logger.info(f"  🎯 Pattern A SHORT: {pattern_a_short} (Fresh+RSI) [{'ON' if enable_a else 'OFF'}]")
        logger.info(f"  🎯 Pattern B SHORT: {pattern_b_short} (Fresh+Volume) [{'ON' if enable_b else 'OFF'}]")
        logger.info(f"  🎯 Pattern C SHORT: {pattern_c_short} (RSI alone) [{'ON' if enable_c else 'OFF'}]")
        logger.info(f"  🎯 Pattern D SHORT: {pattern_d_short} (Volume alone) [{'ON' if enable_d else 'OFF'}]")
        logger.info(f"  🎯 Pattern E SHORT: {pattern_e_short} (Fresh+RSI+Volume) [{'ON' if enable_e else 'OFF'}]")
        logger.info(f"  🎯 Pattern MR SHORT: {pattern_mr_short} (BB Upper+RSI) [{'ON' if enable_mr else 'OFF'}]")
        logger.info(f"  ✅ FINAL: LONG={signal_long}, SHORT={signal_short}")
    
    # ========================================
    # 7. 신호 판단
    # ========================================
    side = None
    action = None
    reason = []
    
    if signal_long:
        side = "LONG"
        action = "진입"
        
        # ⭐ PHASE11-D: Pattern 구분
        if pattern_a_long:
            reason.append("Pattern A (Fresh+RSI)")
        if pattern_b_long:
            reason.append("Pattern B (Fresh+Volume)")
        if pattern_c_long:
            reason.append("Pattern C (RSI alone)")
        if pattern_d_long:
            reason.append("Pattern D (Volume alone)")
        if pattern_e_long:
            reason.append("Pattern E (Fresh+RSI+Volume)")
        
        # ⭐ PHASE11-D: Fresh Trend 정보
        if bullish_trend_fresh:
            reason.append(f"Fresh Bullish (age={cross_age})")
        if price_above_fast:
            reason.append("Price>EMA_fast")
        
        if rsi_oversold_signal:
            reason.append(f"RSI {rsi:.1f}")
        if vol_spike:
            reason.append("거래량 급증")
        
        logger.info(f"✅ [DEBUG][SCALPING] LONG 신호 생성! (캔들 #{len(df)})")
        logger.info(f"  📊 Price: {price:.2f} | RSI: {rsi:.1f}")
        logger.info(f"  📈 EMA: fast={ema_fast:.2f}, slow={ema_slow:.2f}")
        logger.info(f"  🎯 Patterns: {', '.join(reason)}")
    
    elif allow_short and signal_short:
        side = "SHORT"
        action = "진입"
        
        # ⭐ PHASE11-D: Pattern 구분
        if pattern_a_short:
            reason.append("Pattern A (Fresh+RSI)")
        if pattern_b_short:
            reason.append("Pattern B (Fresh+Volume)")
        if pattern_c_short:
            reason.append("Pattern C (RSI alone)")
        if pattern_d_short:
            reason.append("Pattern D (Volume alone)")
        if pattern_e_short:
            reason.append("Pattern E (Fresh+RSI+Volume)")
        
        # ⭐ PHASE11-D: Fresh Trend 정보
        if bearish_trend_fresh:
            reason.append(f"Fresh Bearish (age={cross_age})")
        if price_below_fast:
            reason.append("Price<EMA_fast")
        elif ema_bearish:
            reason.append("EMA bearish 정렬")
        
        if rsi_overbought_signal:
            reason.append(f"RSI 과매수 하락 ({rsi:.1f})")
        # ⭐ PHASE11 Iter2: Momentum 패턴 제거됨
        if vol_spike:
            reason.append("거래량 급증")
        
        logger.info(f"✅ [DEBUG][SCALPING] SHORT 신호 생성! (캔들 #{len(df)})")
        logger.info(f"  📊 Price: {price:.2f} | RSI: {rsi:.1f}")
        logger.info(f"  📉 EMA: fast={ema_fast:.2f}, slow={ema_slow:.2f}")
        logger.info(f"  🎯 Patterns: {', '.join(reason)}")
    
    # ========================================
    # 8. 가격 레벨 계산 (SL/TP)
    # ========================================
    entry, sl, tp = (None, None, None)
    if side:
        #  PHASE9-6: 변동성 레짐 감지 (Config 제어)
        vol_regime = detect_volatility_regime(df)
        vol_mults = config.get('exits', {}).get('volatility_regime_multipliers', {
            'high_vol': 1.2,
            'neutral': 1.0,
            'low_vol': 0.9
        })
        vol_mult = vol_mults.get(vol_regime, vol_mults.get('neutral', 1.0))
        atr_mult_adjusted = atr_mult_sl * vol_mult
        
        entry, sl, tp = price_levels(
            side, price, atr,
            rr,
            atr_mult_adjusted
        )
    
    # ========================================
    # 9. 레버리지 계산
    # ========================================
    if 'leverage' not in config:
        logger.warning(f" Config에 leverage 없음! config keys: {list(config.keys())}")
        lev = 1  # 기본값
    else:
        lev = leverage_suggestion(
            atr_pct,
            config['leverage']['min'],
            config['leverage']['max']
        )
    
    # ========================================
    # 10. 신호 반환
    # ========================================
    return {
        "regime": reg,
        "price": price,
        "atr": atr,
        "atr_pct": atr_pct,
        "rsi": rsi,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "side": side,
        "action": action,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lev": lev,
        "ts": int(last["time"].timestamp()) if hasattr(last["time"], 'timestamp') else int(last["time"]),
        "reason": reason,
        "volume": volume,
        "vol_ma": vol_ma,
        #  PHASE9-6: 추가 정보
        "golden_cross": golden_cross,
        "dead_cross": dead_cross,
        "higher_low": higher_low,
        "lower_high": lower_high,
        "vol_spike": vol_spike,
    }


# ============================================================================
# PHASE19-1: BaseStrategy 래퍼
# ============================================================================
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata


class ScalpingStrategy(BaseStrategy):
    """
    Scalping 전략 (PHASE12, 3m 고빈도)
    
    **전략 특징**:
    - 타임프레임: 1m, 3m, 5m
    - EMA Fresh Trend + Optional MR
    - RR: 1.5
    - 보유 시간: 짧음 (수분 ~ 30분)
    
    **PHASE19-1 래퍼**:
    - 기존 signal_logic() 함수 호출
    - BaseStrategy 인터페이스 구현
    - Registry 자동 로드 지원
    """
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='scalping',
            strategy_type='scalping',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],  # 주요 심볼 (빈 리스트 = 모든 심볼)
            supported_timeframes=['1m', '3m', '5m'],
            version='v3.0',
            description='3분봉 기반 EMA Fresh Trend + Optional Mean Reversion',
            # PHASE19-2: Ensemble Score System
            optimal_regime='trending',
            worst_regime='ranging',
            base_weight=1.0,
            factor_weights={
                'momentum': 0.4,
                'trend_strength': 0.3,
                'volume': 0.2,
                'volatility': 0.1,
            }
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        신호 계산 (기존 signal_logic 호출)
        
        Args:
            df: OHLCV + 지표 DataFrame
        
        Returns:
            dict: 신호 정보
        """
        return signal_logic(df, self.config)