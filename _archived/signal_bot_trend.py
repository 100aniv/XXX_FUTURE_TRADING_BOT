#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TREND Strategy Bot (추세 추종 전략)
=====================================
타임프레임: 1h
전략: EMA 크로스오버 + MACD 골든/데드크로스 + 강한 추세 포착
신호/일: 5-15개
승률 목표: 60-70%

완전한 기능:
- 신호 생성 + 실시간 TP/SL 추적 (1분봉)
- Flash-Guard + 목표 추적 + 일일 리스크 가드
- MTF Confirm (HTF=4h) + Vol Spike Filter
- Regime Alert + Beginner Explain
- DB 저장 (멱등성 보장)
"""
import os, time, math, json, traceback, logging, threading, signal, sys, atexit
from collections import deque
from typing import Dict, Any, Tuple, List
from datetime import datetime

import requests
import pandas as pd
import numpy as np
import ccxt
from binance.client import Client as BinanceClient
from websocket import WebSocketApp
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

# ============================================
# 0. LOGGING (로그 설정) - 공통 모듈 사용
# ============================================
from common.logger import setup_logger
logger = setup_logger(__name__, log_type="signals")

# ============================================
# 1. DATABASE/MESSAGING (공통 모듈 사용)
# ============================================
from common.database import get_db_connection, save_signal_to_db, test_db_connection

# DB 연결 테스트
test_db_connection()

# ============================================
# 2. CONFIGURATION (환경변수 → 설정) - 공통 모듈 사용 ✅
# ============================================
from common.config import load_config, validate_config

CFG = load_config()
validate_config(CFG)

EMA_FAST, EMA_MID, EMA_SLOW = 20, 50, 200
RSI_LEN, ATR_LEN = 14, 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
BB_LEN, BB_STD = 20, 2.0

# Buffers and state
BUFFERS: Dict[str, deque] = {sym: deque(maxlen=CFG["lookback"]+5) for sym in CFG["symbols"]}
LAST_ALERT_TS: Dict[str, int] = {}
LAST_REGIME: Dict[str, str] = {}
BINANCE_F_WS = "wss://fstream.binance.com/stream"

# Flash guard buffers (⚠️ Trading 모듈로 이동)

# Bot 상태
BOT_RUNNING: bool = True
BOT_PAUSED: bool = False

# ============================================
# 3. HELPERS (유틸리티 함수들) - 공통 모듈로 이동 완료 ✅
# ============================================
# ✅ common/messaging.py로 이동:
#    - tg(), format_signal_alert()
# ✅ common/calculations.py로 이동:
#    - round_tick(), position_size(), leverage_suggestion(), price_levels()
# ✅ common/utils.py로 이동:
#    - bootstrap_history(), buffer_to_df(), make_streams()
#    - qty_notional_margin(), maybe_regime_alert()
# ============================================
from common.messaging import tg as _tg, format_signal_alert

def tg(text: str):
    """텔레그램 메시지 전송 (CFG 자동 전달)"""
    return _tg(text, CFG)

# 계산 함수 (공통 모듈 사용) ✅
from common.calculations import round_tick, position_size, leverage_suggestion, price_levels, tp_from_rr

# 유틸리티 함수 (공통 모듈 사용) ✅
from common.utils import bootstrap_history, buffer_to_df, make_streams, qty_notional_margin, maybe_regime_alert

# ============================================
# 4. INDICATORS (지표 계산) - indicators 모듈 사용 ✅
# ============================================
from indicators import add_indicators, regime

# ============================================
# 5. SIGNAL LOGIC (신호 생성 로직) - strategies 모듈 사용 ✅
# ============================================
from strategies import scalping, daytrade, swing

# ============================================
# 6. SIGNAL PROCESSING (신호 처리) - signals 모듈 사용 ✅
# ============================================
from signals import SignalGenerator
from signals.signal_storage import save_signal

# Signal Generator 초기화
signal_generator = SignalGenerator(CFG)

# ============================================
# ⚠️ REMOVED: FLASH GUARD (급등락 감지)
# ============================================
# Trading 모듈로 이동 완료 (trading_executor.py - RiskManager)
# - flash_guard_update() → RiskManager.flash_guard_update()
# - flash_guard_allowed() → RiskManager.flash_guard_allowed()
# - FLASHBUF, FLASH_PAUSE_UNTIL → RiskManager 내부
# ============================================

# ============================================
# 11. FORMATTING (메시지 포맷팅) - 공통 모듈로 이동 완료 ✅
# ============================================
# ✅ common/messaging.py로 이동:
# - beginner_block(): 초보자 설명 블록
# - format_signal_alert(): 신호 알림 메시지 포맷 (가독성 강화)
# - round_tick(): 가격 반올림
# ============================================

# ============================================
# 9. WEBSOCKET (실시간 데이터 수신) - collector 모듈 사용 ✅
# ============================================
from collector import WebSocketCollector, bootstrap_history

def on_candle_closed(symbol, candle, is_closed, timeframe):
    """캔들 닫힐 때 호출되는 콜백 (WebSocketCollector에서 호출)"""
    global BOT_PAUSED
    if BOT_PAUSED:
        return
    
    try:
        # 1m stream: Trading 모듈 전용
        if timeframe == "1m":
            return
        
        # 캔들이 닫힐 때만 신호 생성
        if not is_closed:
            return
        
        # Signal Generator로 신호 생성
        signal = signal_generator.process_candle(symbol, candle, tg_callback=tg)
        
        if not signal:
            return
        
        # 포지션 계산
        qty, notional, margin = qty_notional_margin(
            signal["entry"], signal["sl"], signal["lev"],
            CFG["equity_usdt"], CFG["risk_per_trade"]
        )
        
        # DB 저장
        save_signal(symbol, signal, CFG)
        
        # 텔레그램 알림
        msg = format_signal_alert(symbol, signal, qty, notional, margin, CFG)
        tg(msg)

    except Exception as e:
        logger.error(f"⚠️ 신호 처리 오류: {e}")
        tg(f"⚠️ 신호 처리 오류: {e}")
        traceback.print_exc()

# ============================================
# 12. MAIN (메인 실행 + 명령어 핸들러)
# ============================================
# 리팩토링 시: main.py로 분리
# - main(): 봇 초기화 및 실행
# - telegram_command_handler(): 텔레그램 명령어 처리
# - cleanup(): 종료 시 정리
# ============================================
def main():
    logger.info("="*50)
    logger.info("TREND 전략 봇 시작 (추세 추종)")
    logger.info(f"심볼: {CFG['symbols']}")
    logger.info(f"타임프레임: {CFG['timeframe']}")
    logger.info(f"MTF Confirm: HTF={CFG['htf']}")
    logger.info("="*50)
    
    bot_name = CFG.get("bot_name", "BOT").upper()
    symbols_str = ", ".join(CFG["symbols"])
    start_msg = [
        "FUTURE TRADING BOT [START]",
        "━━━━━━━━━━━━━━━━━━━━━",
        "✅ v13.3 시스템 초기화 완료",
        "📊 실시간 신호 분석 시작",
        f"💼 심볼({len(CFG['symbols'])}개): {symbols_str}",
        f"⏱ 타임프레임: {CFG['timeframe']}",
        "━━━━━━━━━━━━━━━━━━━━━"
    ]
    tg("\n".join(start_msg))
    # 초기 히스토리 로드
    for s in CFG["symbols"]:
        try: 
            logger.info(f"{s} 히스토리 로딩 중...")
            bootstrap_history(s, CFG["timeframe"], CFG["lookback"], BUFFERS)
            logger.info(f"{s} 로드 완료: {len(BUFFERS[s])}개 캔들")
        except Exception as e: 
            logger.error(f"{s} 로드 실패: {e}")
            tg(f"⚠️ {s} 초기 히스토리 로드 실패: {e}")
    
    # WebSocket Collector 시작
    logger.info("WebSocket 연결 시작...")
    collector = WebSocketCollector(CFG["symbols"], CFG["timeframe"])
    collector.on_candle(on_candle_closed)
    collector.on_connect(lambda: tg("🔗 WebSocket 연결 성공"))
    collector.on_error(lambda e: tg(f"💥 WebSocket 오류: {e}"))
    collector.on_close_reconnect(lambda: tg("🔌 WebSocket 연결 끊김. 재연결 중..."))
    collector.start()

def telegram_command_handler():
    """텔레그램 명령어 처리 (별도 스레드)"""
    global BOT_RUNNING, BOT_PAUSED
    last_update_id = 0
    token = CFG["telegram_token"]
    
    if "PUT_YOUR" in token:
        logger.warning("텔레그램 명령어 핸들러: TOKEN 미설정")
        return
    
    logger.info("텔레그램 명령어 핸들러 시작")
    logger.info(f"명령어 핸들러 설정: bot_name={CFG['bot_name']}, chat_id={CFG['telegram_chat_id']}")
    
    while BOT_RUNNING:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            resp = requests.get(url, params=params, timeout=35)
            
            if resp.status_code != 200:
                logger.warning(f"getUpdates 실패: {resp.status_code}")
                time.sleep(5)
                continue
            
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"getUpdates 응답 실패: {data}")
                time.sleep(5)
                continue
            
            results = data.get("result", [])
            if results:
                logger.info(f"📨 {len(results)}개의 업데이트 수신")
            
            for update in data.get("result", []):
                last_update_id = update["update_id"]
                
                if "message" not in update:
                    continue
                
                msg = update["message"]
                if "text" not in msg:
                    continue
                
                text = msg["text"].strip().lower()
                chat_id = str(msg["chat"]["id"])
                
                logger.info(f"📩 메시지 수신: '{text}' from chat_id={chat_id}")
                
                # 설정된 CHAT_ID에서만 명령 수락
                if chat_id != CFG["telegram_chat_id"]:
                    logger.warning(f"거부: chat_id 불일치 ({chat_id} != {CFG['telegram_chat_id']})")
                    continue
                
                # 봇 이름 prefix 확인
                bot_prefix = CFG["bot_name"].lower()
                
                # 명령어 처리 - 봇별 명령어
                if text == f"/{bot_prefix}_start" or text == f"/{bot_prefix}start":
                    BOT_PAUSED = False
                    tg(f"✅ [{CFG['bot_name'].upper()}] 봇 재개됨. 신호 모니터링 시작!")
                    logger.info(f"[{CFG['bot_name']}] 봇 재개됨")
                
                elif text == f"/{bot_prefix}_stop" or text == f"/{bot_prefix}stop":
                    BOT_PAUSED = True
                    tg(f"⏸ [{CFG['bot_name'].upper()}] 봇 일시정지. /{bot_prefix}_start로 재개 가능.")
                    logger.info(f"[{CFG['bot_name']}] 봇 일시정지")
                
                elif text == f"/{bot_prefix}_status" or text == f"/{bot_prefix}status":
                    status = "일시정지" if BOT_PAUSED else "실행 중"
                    msg = f"📊 *[{CFG['bot_name'].upper()}] 봇 상태*\n\n"
                    msg += f"상태: *{status}*\n"
                    msg += f"타임프레임: {CFG['timeframe']}\n"
                    msg += f"모니터링 코인: {', '.join(CFG['symbols'])}\n"
                    # PnL 제거됨 - Trading Bot으로 이동
                    msg += f"\n명령어: /{bot_prefix}_start, /{bot_prefix}_stop, /{bot_prefix}_status, /{bot_prefix}_help"
                    tg(msg)
                
                elif text == f"/{bot_prefix}_stats" or text == f"/{bot_prefix}stats":
                    # 통계 기능 제거됨 - Trading Bot으로 이동
                    msg = f"📈 *[{CFG['bot_name'].upper()}] 통계*\n\n"
                    msg += f"신호 생성 전용 모드. PnL/포지션 통계는 Trading Bot에서 확인하세요."
                    tg(msg)
                
                elif text == f"/{bot_prefix}_help" or text == f"/{bot_prefix}help":
                    help_msg = f"🤖 *[{CFG['bot_name'].upper()}] 봇 명령어*\n\n"
                    help_msg += f"/{bot_prefix}_start - 봇 시작/재개\n"
                    help_msg += f"/{bot_prefix}_stop - 봇 일시정지\n"
                    help_msg += f"/{bot_prefix}_status - 봇 상태 확인\n"
                    help_msg += f"/{bot_prefix}_stats - 통계 확인\n"
                    help_msg += f"/{bot_prefix}_help - 도움말\n\n"
                    help_msg += "_봇이 일시정지되면 신호가 전송되지 않습니다._"
                    tg(help_msg)
                
                # 전체 봇 제어 (all)
                elif text == "/all_start":
                    BOT_PAUSED = False
                    tg(f"✅ [{CFG['bot_name'].upper()}] 전체 시작 명령 수신")
                    logger.info(f"[{CFG['bot_name']}] 전체 시작")
                
                elif text == "/all_stop":
                    BOT_PAUSED = True
                    tg(f"⏸ [{CFG['bot_name'].upper()}] 전체 정지 명령 수신")
                    logger.info(f"[{CFG['bot_name']}] 전체 정지")
                
                elif text == "/help":
                    help_msg = "🤖 *전체 봇 명령어*\n\n"
                    help_msg += "*개별 제어:*\n"
                    help_msg += "/scalp_start, /scalp_stop, /scalp_status\n"
                    help_msg += "/intra_start, /intra_stop, /intra_status\n"
                    help_msg += "/swing_start, /swing_stop, /swing_status\n\n"
                    help_msg += "*전체 제어:*\n"
                    help_msg += "/all_start - 모든 봇 시작\n"
                    help_msg += "/all_stop - 모든 봇 정지\n"
                    help_msg += "/help - 이 도움말\n\n"
                    help_msg += f"_현재 봇: {CFG['bot_name'].upper()}_"
                    tg(help_msg)
        
        except Exception as e:
            logger.error(f"명령어 핸들러 오류: {e}")
            time.sleep(5)
    
    logger.info("텔레그램 명령어 핸들러 종료")

def cleanup():
    """종료 시 정리 작업"""
    global BOT_RUNNING
    BOT_RUNNING = False
    tg("🛑 봇이 종료됩니다...")
    logger.info("봇 종료 중...")
    time.sleep(1)

if __name__ == "__main__":
    # 종료 시 cleanup 실행
    atexit.register(cleanup)
    
    def signal_handler(sig, frame):
        global BOT_RUNNING
        BOT_RUNNING = False
        tg("🛑 수동 종료 (Ctrl+C)")
        logger.info("수동 종료 감지")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("프로그램 시작: 명령어 핸들러 스레드 생성 중...")
        # 명령어 핸들러 스레드 시작
        cmd_thread = threading.Thread(target=telegram_command_handler, daemon=True, name="TelegramCmdHandler")
        logger.info(f"스레드 생성 완료: {cmd_thread.name}")
        cmd_thread.start()
        logger.info("✅ 명령어 핸들러 스레드 시작됨!")
        
        # 메인 봇 실행
        logger.info("메인 봇 실행 시작...")
        main()
    except KeyboardInterrupt:
        BOT_RUNNING = False
        tg("🛑 수동 종료")
    except Exception as e:
        BOT_RUNNING = False
        tg(f"💥 치명 오류: {e}")
        logger.error(f"치명 오류: {e}")
        raise
    finally:
        cleanup()
