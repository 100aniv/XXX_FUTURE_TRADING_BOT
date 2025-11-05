#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Storage
==============
신호 DB 저장 모듈
"""
from datetime import datetime
from uuid import uuid4

from common.logger import setup_logger
from common.database import save_signal_to_db

logger = setup_logger('signals', log_type='signals')


def save_signal(symbol: str, signal: dict, config: dict) -> bool:
    """
    신호 DB 저장
    
    Args:
        symbol: 심볼
        signal: 신호 딕셔너리 (strategy_id 포함)
        config: 설정 딕셔너리
    
    Returns:
        저장 성공 여부
    
    Note:
        signal dict에 strategy_id 필드 필수
    """
    try:
        signal_id = str(uuid4())
        strategy_id = signal.get("strategy_id", "unknown")  # signal에서 직접 읽기
        candle_closed_at = datetime.fromtimestamp(signal["ts"] / 1000)
        
        features = {
            "rsi": signal.get("rsi"),
            "macd": signal.get("macd"),
            "macd_signal": signal.get("macd_signal"),
            "regime": signal.get("regime"),
            "atr_pct": signal.get("atr_pct"),
            "volume": signal.get("volume"),
            "reason": " / ".join(signal.get("reason", []))
        }
        
        save_signal_to_db(
            signal_id=signal_id,
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=config["timeframe"],
            candle_closed_at=candle_closed_at,
            direction=signal["side"],
            confidence=signal.get("confidence", 0.75),  # signal에서 읽거나 기본값
            entry_price=signal["entry"],
            sl_price=signal["sl"],
            tp_price=signal["tp"],
            atr=signal["atr"],
            leverage=signal["lev"],
            features=features
        )
        
        logger.info(f"✅ 신호 DB 저장 성공: {symbol} {signal['side']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 신호 DB 저장 실패: {e}")
        return False
