#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCALPING Strategy
=================
스캘핑 전략 (BB 터치 + EMA 정렬)

전략 개요:
- 타임프레임: 1분/3분
- 핵심: BB 밴드 터치 + 빠른 EMA 정렬
- 조건 완화 (레짐 무시, 빠른 진입)
"""
from typing import Dict, Any
import pandas as pd

from common.calculations import price_levels, leverage_suggestion
from indicators import regime, detect_volatility_regime


def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """
    SCALPING 전략: BB 터치 + EMA 정렬 (조건 완화)
    
    Args:
        df: OHLCV + 지표가 포함된 DataFrame
        config: 전략 설정 (CFG)
    
    Returns:
        dict: 신호 정보
    
    전략 로직:
    - 스캘핑 (1분/3분): BB 터치 + EMA 정렬로 빠른 진입
    - 레짐 무시 (빠른 대응)
    - LONG: BB 하단 근접 + EMA fast > mid + MACD 상승
    - SHORT: BB 상단 근접 + EMA fast < mid + MACD 하락
    """
    # 데이터 충분성 검사
    if len(df) < 2:
        return {"direction": None, "reason": "데이터 부족"}
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 기본 정보
    reg = regime(last)
    price = float(last["close"])
    atr = float(last["atr"])
    atr_pct = atr / price
    
    # MACD 방향 (완화)
    macd_up = last["macd"] > last["macd_signal"]  # 단순화
    macd_down = last["macd"] < last["macd_signal"]
    
    # ⭐ PHASE9-3.1: 조건 완화 파라미터 로드
    relax = config.get('condition_relax', {})
    bb_tolerance = relax.get('bb_bounce_tolerance', 0.002)
    ema_required = relax.get('ema_alignment_required', 3)
    macd_tolerance = relax.get('macd_tolerance', 0.0)
    rsi_tolerance = relax.get('rsi_tolerance', 0.0)
    
    # 파라미터 (기본값은 기존 상수와 동일)
    bb_touch_upper_pct = config.get('bb_touch_upper_pct', 0.995)
    bb_touch_lower_pct = config.get('bb_touch_lower_pct', 1.005)
    rsi_min = config.get('rsi_min', 30)
    rsi_max = config.get('rsi_max', 70)
    volume_mult = config.get('volume_mult', 1.5)
    volume_filter_required = (config.get('filters', {}) or {}).get('volume_spike', config.get('volume_spike', True))
    # BB 반등 임계값 (파라미터화)
    bb_bounce_lower_now_mult = config.get('bb_bounce_lower_now_mult', 1.003)
    bb_bounce_lower_prev_mult = config.get('bb_bounce_lower_prev_mult', 1.008)
    bb_bounce_upper_now_mult = config.get('bb_bounce_upper_now_mult', 0.997)
    bb_bounce_upper_prev_mult = config.get('bb_bounce_upper_prev_mult', 0.992)
    
    # ⭐ PHASE9-3.1: 조건 완화 로그 (1회만)
    import logging
    logger_debug = logging.getLogger(__name__)
    if len(df) == config.get('min_bars_for_signal', 60):  # 첫 신호 가능 시점
        logger_debug.info(f"✅ [CONDITION_RELAX] 조건 완화 파라미터 적용됨:")
        logger_debug.info(f"  - bb_bounce_tolerance: {bb_tolerance:.4f} (BB 범위 확대)")
        logger_debug.info(f"  - ema_alignment_required: {ema_required} (3=전체, 2=fast>mid만, 1=없음)")
        logger_debug.info(f"  - macd_tolerance: {macd_tolerance:.4f} (MACD 완화)")
        logger_debug.info(f"  - rsi_tolerance: {rsi_tolerance:.1f} (RSI 범위 확대)")

    # BB 터치 (근접) - ⭐ 조건 강화
    bb_touch_upper = last["close"] >= last["bb_upper"] * bb_touch_upper_pct  # BB 상단 근접
    bb_touch_lower = last["close"] <= last["bb_lower"] * bb_touch_lower_pct  # BB 하단 근접
    
    # ⭐ PHASE9-3.1: EMA 추세 확인 (조건 완화 적용)
    if ema_required == 3:
        # 3선 정렬 (기본값)
        ema_trend_long = (last["ema_fast"] > last["ema_mid"] and 
                          last["ema_mid"] > last["ema_slow"])
        ema_trend_short = (last["ema_fast"] < last["ema_mid"] and 
                           last["ema_mid"] < last["ema_slow"])
    elif ema_required == 2:
        # 2선 정렬 (fast > mid만)
        ema_trend_long = last["ema_fast"] > last["ema_mid"]
        ema_trend_short = last["ema_fast"] < last["ema_mid"]
    else:
        # EMA 조건 없음
        ema_trend_long = True
        ema_trend_short = True
    
    # ⭐ PHASE9-3.1: RSI 범위 (조건 완화 적용)
    rsi_ok_long = (rsi_min - rsi_tolerance) < last["rsi"] < (rsi_max + rsi_tolerance)
    rsi_ok_short = (rsi_min - rsi_tolerance) < last["rsi"] < (rsi_max + rsi_tolerance)
    
    # ⭐ 거래량 (평균 배수)
    vol_ok = (last["volume"] > last["vol_ma"] * volume_mult) if volume_filter_required else True
    
    # ⭐ MACD 강화 (크로스 확인)
    macd_cross_up = (last["macd"] > last["macd_signal"] and 
                     prev["macd"] <= prev["macd_signal"])  # 상향 크로스
    macd_cross_down = (last["macd"] < last["macd_signal"] and 
                       prev["macd"] >= prev["macd_signal"])  # 하향 크로스
    
    # ⭐ PHASE9-3.1: BB 밴드 반등 확인 (조건 완화 적용)
    # LONG: 이전에 하단 터치 → 현재 반등 중
    bb_bounce_long = (
        last["close"] > last["bb_lower"] * (bb_bounce_lower_now_mult - bb_tolerance) and  # 현재 하단 위 (완화)
        prev["close"] <= prev["bb_lower"] * (bb_bounce_lower_prev_mult + bb_tolerance) and  # 이전 하단 근처 (완화)
        last["close"] > prev["close"]  # 상승 캔들
    )
    
    # SHORT: 이전에 상단 터치 → 현재 조정 중
    bb_bounce_short = (
        last["close"] < last["bb_upper"] * (bb_bounce_upper_now_mult + bb_tolerance) and  # 현재 상단 아래 (완화)
        prev["close"] >= prev["bb_upper"] * (bb_bounce_upper_prev_mult - bb_tolerance) and  # 이전 상단 근처 (완화)
        last["close"] < prev["close"]  # 하락 캔들
    )
    
    # ⭐ PHASE9 DEBUG: 로깅 추가
    import logging
    logger_debug = logging.getLogger(__name__)
    
    # ⭐ PHASE9-3.4: 신호 조건 (AND 구조 복원)
    # LONG/SHORT: BB 반등 + MACD + EMA 정렬 + RSI + 거래량 (모두 만족 필수)
    # - condition_relax 파라미터는 각 조건 내부에서 적용됨
    # - entry_mode는 향후 OR/Hybrid 실험용 훅 (현재는 strict만 사용)
    entry_mode = relax.get('entry_mode', 'strict')
    
    # MACD 조건
    macd_ok_long = (macd_cross_up or macd_up)
    macd_ok_short = (macd_cross_down or macd_down)
    
    # ⭐ AND 구조: 모든 조건 만족 필수
    pullback_long = (bb_bounce_long and macd_ok_long and 
                     ema_trend_long and rsi_ok_long and vol_ok)
    
    pullback_short = (bb_bounce_short and macd_ok_short and 
                      ema_trend_short and rsi_ok_short and vol_ok)
    
    # ⭐ PHASE9-3.4: 조건별 상태 로그 (샘플링: 100캔들마다) - AND 구조
    if len(df) % 100 == 0:
        logger_debug.info(f"🔍 [SCALPING DEBUG] 신호 조건 체크 (캔들 #{len(df)}):")
        logger_debug.info(f"  - bb_bounce_long: {bb_bounce_long} | bb_bounce_short: {bb_bounce_short} (tolerance={bb_tolerance:.4f})")
        logger_debug.info(f"  - macd_ok: long={macd_ok_long}, short={macd_ok_short} (up={macd_up}, down={macd_down})")
        logger_debug.info(f"  - ema_trend: long={ema_trend_long}, short={ema_trend_short} (required={ema_required})")
        logger_debug.info(f"  - rsi: {last['rsi']:.1f} (long_ok={rsi_ok_long}, short_ok={rsi_ok_short}, tolerance={rsi_tolerance:.1f})")
        logger_debug.info(f"  - vol: {last['volume']:.0f} vs ma={last['vol_ma']:.0f} (ok={vol_ok}, mult={volume_mult})")
        logger_debug.info(f"  ⭐ [AND 구조] pullback_long={pullback_long} (entry_mode={entry_mode})")
        logger_debug.info(f"  ⭐ [AND 구조] pullback_short={pullback_short} (entry_mode={entry_mode})")
    
    # 돌파 전략 제거 (스캘핑에서는 위험)
    
    # 옵션: 숏 허용 여부 (기본 True)
    allow_short = (config.get('filters', {}) or {}).get('allow_short', config.get('allow_short', True))

    # 신호 판단
    side = None
    action = None
    reason = []
    
    if pullback_long:
        side = "LONG"
        action = "진입"
        reason.append("BB 하단 반등")
        reason.append("EMA 정렬 + 강한 MACD")
        reason.append("거래량 급증")
        # ⭐ PHASE9 DEBUG: 신호 생성 로그
        logger_debug.info(f"✅ [SCALPING SIGNAL] LONG 신호 생성! (캔들 #{len(df)})")
        logger_debug.info(f"  - Price: {price:.2f} | RSI: {last['rsi']:.1f} | MACD: {last['macd']:.4f}")
    
    elif allow_short and pullback_short:
        side = "SHORT"
        action = "진입"
        reason.append("BB 상단 조정")
        reason.append("EMA 역정렬 + 강한 MACD")
        reason.append("거래량 급증")
        # ⭐ PHASE9 DEBUG: 신호 생성 로그
        logger_debug.info(f"✅ [SCALPING SIGNAL] SHORT 신호 생성! (캔들 #{len(df)})")
        logger_debug.info(f"  - Price: {price:.2f} | RSI: {last['rsi']:.1f} | MACD: {last['macd']:.4f}")
    
    # 가격 레벨 계산
    entry, sl, tp = (None, None, None)
    if side:
        # ⭐ PHASE9-3: 변동성 레짐 감지 (Config 제어)
        vol_regime = detect_volatility_regime(df)
        vol_mults = config.get('exits', {}).get('volatility_regime_multipliers', {
            'high_vol': 1.2,
            'neutral': 1.0,
            'low_vol': 0.9
        })
        vol_mult = vol_mults.get(vol_regime, vol_mults.get('neutral', 1.0))
        atr_mult_adjusted = config["atr_mult_sl"] * vol_mult
        
        entry, sl, tp = price_levels(
            side, price, atr,
            config["rr"],
            atr_mult_adjusted
        )
    
    # 레버리지 제안
    import logging
    logger = logging.getLogger(__name__)
    
    # 디버그: leverage 설정 확인
    if 'leverage' not in config:
        logger.warning(f"⚠️ Config에 leverage 없음! config keys: {list(config.keys())}")
        lev = 1  # 기본값
    else:
        lev = leverage_suggestion(
            atr_pct,
            config['leverage']['min'],
            config['leverage']['max']
        )
        logger.info(f"✅ Leverage 계산: atr_pct={atr_pct:.4f}, lev={lev}")
    
    return {
        "regime": reg,
        "price": price,
        "atr": atr,
        "atr_pct": atr_pct,
        "rsi": float(last["rsi"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "bb_upper": float(last["bb_upper"]),
        "bb_lower": float(last["bb_lower"]),
        "ema_fast": float(last["ema_fast"]),
        "ema_mid": float(last["ema_mid"]),
        "ema_slow": float(last["ema_slow"]),
        "side": side,
        "action": action,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "lev": lev,
        "ts": int(last["time"].timestamp()) if hasattr(last["time"], 'timestamp') else int(last["time"]),
        "reason": reason,
        "volume": float(last["volume"]),
        "vol_ma": float(last["vol_ma"]),
    }
