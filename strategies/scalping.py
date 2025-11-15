#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCALPING Strategy V2 (PHASE9-6)
=================================
진정한 고빈도 스캘핑 전략 (1분봉 기반)

 PHASE9-6: 신규 고빈도 스캘핑 전략으로 완전 교체
- 기존 BB 기반 로직은 strategies/swing_bb.py로 이동 완료
- 이 버전은 1분봉 기반 고빈도 스캘핑 전략입니다
- 목표: 10~50건/일 (90일 기준 100건 이상)

전략 철학:
- 타임프레임: 1m (1분봉)
- 보유 시간: 짧은 구간 (수분 ~ 30분 이내)
- RR: 작은 RR (1.2~1.5)
- 빈도: 높은 거래 빈도

신호 조건 (LONG):
1. EMA 교차: fast EMA가 slow EMA 위로 골든크로스
2. RSI 극단: RSI < 30 (과매도 구간) 또는 반등 시작
3. 모멘텀: 최근 N개 캔들 중 higher low 패턴
4. 거래량: 평균 대비 증가

신호 조건 (SHORT):
1. EMA 교차: fast EMA가 slow EMA 아래로 데드크로스
2. RSI 극단: RSI > 70 (과매수 구간) 또는 하락 시작
3. 모멘텀: 최근 N개 캔들 중 lower high 패턴
4. 거래량: 평균 대비 증가

위험 관리:
- SL: ATR 기반 동적 손절
- TP: RR 1.2~1.5 (config 설정)
- 최대 보유: 30분 (config 설정)

 주의:
이 버전은 튜닝 전 초기 뼈대(V1)입니다.
향후 베이시안 튜닝 / Optuna / 앙상블 통합으로 이어질 예정입니다.
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
    
    # ⭐ PHASE11 개선: 고빈도 스캘핑을 위한 다중 진입 패턴
    # 기존 (PHASE10): (EMA AND RSI) OR (EMA AND Volume) → 7 trades/7days (너무 적음)
    # 개선 (PHASE11): 
    #   - Pattern A: EMA + RSI (극단값 기반)
    #   - Pattern B: EMA + Volume (거래량 급증)
    #   - Pattern C: RSI + Momentum (대체 진입)
    # 결과: A OR B OR C → 고빈도 진입 기회 증가
    
    # ⭐ PHASE11 공격적 완화: 다중 진입 패턴 (EMA 선택적)
    # LONG 조건:
    # - Pattern A: EMA bullish AND RSI oversold (EMA 기반)
    # - Pattern B: EMA bullish AND Volume spike (EMA 기반)
    # - Pattern C: RSI oversold AND higher_low (EMA 불필요)
    # - Pattern D: Volume spike AND higher_low (EMA/RSI 불필요) [PHASE11 NEW]
    
    ema_long = ema_bullish  # fast > slow (Golden cross 제거)
    pattern_a_long = ema_long and rsi_oversold_signal
    pattern_b_long = ema_long and vol_spike
    pattern_c_long = rsi_oversold_signal and higher_low  # RSI + Momentum
    pattern_d_long = vol_spike and higher_low  # ⭐ PHASE11: Volume + Momentum (EMA 불필요)
    
    # 최종 신호: A OR B OR C OR D (기본: 모든 패턴 허용)
    signal_long = pattern_a_long or pattern_b_long or pattern_c_long or pattern_d_long
    
    # ⭐ PHASE11: 필터 적용 로직 (선택적)
    # momentum_enabled=true: Pattern A/B는 higher_low 필요, Pattern C/D는 이미 포함
    if momentum_enabled:
        pattern_ab_long = (pattern_a_long or pattern_b_long) and higher_low
        signal_long = pattern_ab_long or pattern_c_long or pattern_d_long
    
    # volume_required=true: Pattern A/C는 vol_spike 불필요, Pattern B/D는 이미 포함
    if volume_required:
        pattern_ac_long = (pattern_a_long or pattern_c_long) and vol_spike
        signal_long = pattern_ac_long or pattern_b_long or pattern_d_long
    
    # SHORT 조건:
    # - Pattern A: EMA bearish AND RSI overbought (EMA 기반)
    # - Pattern B: EMA bearish AND Volume spike (EMA 기반)
    # - Pattern C: RSI overbought AND lower_high (EMA 불필요)
    # - Pattern D: Volume spike AND lower_high (EMA/RSI 불필요) [PHASE11 NEW]
    
    ema_short = ema_bearish  # fast < slow (Dead cross 제거)
    pattern_a_short = ema_short and rsi_overbought_signal
    pattern_b_short = ema_short and vol_spike
    pattern_c_short = rsi_overbought_signal and lower_high  # RSI + Momentum
    pattern_d_short = vol_spike and lower_high  # ⭐ PHASE11: Volume + Momentum (EMA 불필요)
    
    # 최종 신호: A OR B OR C OR D (기본: 모든 패턴 허용)
    signal_short = pattern_a_short or pattern_b_short or pattern_c_short or pattern_d_short
    
    # ⭐ PHASE11: 필터 적용 로직 (선택적)
    # momentum_enabled=true: Pattern A/B는 lower_high 필요, Pattern C/D는 이미 포함
    if momentum_enabled:
        pattern_ab_short = (pattern_a_short or pattern_b_short) and lower_high
        signal_short = pattern_ab_short or pattern_c_short or pattern_d_short
    
    # volume_required=true: Pattern A/C는 vol_spike 불필요, Pattern B/D는 이미 포함
    if volume_required:
        pattern_ac_short = (pattern_a_short or pattern_c_short) and vol_spike
        signal_short = pattern_ac_short or pattern_b_short or pattern_d_short
    
    # ========================================
    # 디버그 로그 (500캔들마다) - PHASE10 성능 최적화
    # ========================================
    if len(df) % 500 == 0:
        logger.info(f"🔍 [DEBUG][SCALPING] 신호 조건 체크 (캔들 #{len(df)}):")
        logger.info(f"  📊 Price: {price:.2f}")
        logger.info(f"  📈 EMA: fast={ema_fast:.2f}, slow={ema_slow:.2f} | bullish={ema_bullish}, bearish={ema_bearish}")
        logger.info(f"  🔀 EMA Cross: golden={golden_cross}, dead={dead_cross}")
        logger.info(f"  📉 RSI: {rsi:.1f} | oversold_signal={rsi_oversold_signal}, overbought_signal={rsi_overbought_signal}")
        logger.info(f"  🔄 Momentum: higher_low={higher_low}, lower_high={lower_high} (enabled={momentum_enabled})")
        logger.info(f"  📦 Volume: {volume:.0f} vs ma={vol_ma:.0f} | spike={vol_spike} (required={volume_required})")
        logger.info(f"  🎯 Pattern A LONG: {pattern_a_long} (EMA+RSI)")
        logger.info(f"  🎯 Pattern B LONG: {pattern_b_long} (EMA+Volume)")
        logger.info(f"  🎯 Pattern C LONG: {pattern_c_long} (RSI+Momentum) [PHASE11]")
        logger.info(f"  🎯 Pattern D LONG: {pattern_d_long} (Volume+Momentum) [PHASE11 NEW]")
        logger.info(f"  🎯 Pattern A SHORT: {pattern_a_short} (EMA+RSI)")
        logger.info(f"  🎯 Pattern B SHORT: {pattern_b_short} (EMA+Volume)")
        logger.info(f"  🎯 Pattern C SHORT: {pattern_c_short} (RSI+Momentum) [PHASE11]")
        logger.info(f"  🎯 Pattern D SHORT: {pattern_d_short} (Volume+Momentum) [PHASE11 NEW]")
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
        
        # 패턴 구분
        if pattern_a_long:
            reason.append("Pattern A (EMA+RSI)")
        if pattern_b_long:
            reason.append("Pattern B (EMA+Volume)")
        if pattern_c_long:
            reason.append("Pattern C (RSI+Momentum) [PHASE11]")
        if pattern_d_long:
            reason.append("Pattern D (Volume+Momentum) [PHASE11 NEW]")
        
        if golden_cross:
            reason.append("EMA 골든크로스")
        elif ema_bullish:
            reason.append("EMA bullish 정렬")
        
        if rsi_oversold_signal:
            reason.append(f"RSI 과매도 반등 ({rsi:.1f})")
        if higher_low:
            reason.append("Higher low 패턴")
        if vol_spike:
            reason.append("거래량 급증")
        
        logger.info(f"✅ [DEBUG][SCALPING] LONG 신호 생성! (캔들 #{len(df)})")
        logger.info(f"  📊 Price: {price:.2f} | RSI: {rsi:.1f}")
        logger.info(f"  📈 EMA: fast={ema_fast:.2f}, slow={ema_slow:.2f}")
        logger.info(f"  🎯 Patterns: {', '.join(reason)}")
    
    elif allow_short and signal_short:
        side = "SHORT"
        action = "진입"
        
        # 패턴 구분
        if pattern_a_short:
            reason.append("Pattern A (EMA+RSI)")
        if pattern_b_short:
            reason.append("Pattern B (EMA+Volume)")
        if pattern_c_short:
            reason.append("Pattern C (RSI+Momentum) [PHASE11]")
        if pattern_d_short:
            reason.append("Pattern D (Volume+Momentum) [PHASE11 NEW]")
        
        if dead_cross:
            reason.append("EMA 데드크로스")
        elif ema_bearish:
            reason.append("EMA bearish 정렬")
        
        if rsi_overbought_signal:
            reason.append(f"RSI 과매수 하락 ({rsi:.1f})")
        if lower_high:
            reason.append("Lower high 패턴")
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