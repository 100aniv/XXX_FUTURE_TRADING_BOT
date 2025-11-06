#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 메시징 모듈
================
텔레그램 알림 및 메시지 포맷팅 + 구조화된 로깅

⚠️ 리팩토링 완료 (2025-10-27)
- 텔레그램: 외부 알림 (signal_bot 양식)
- 로깅: 내부 기록 (logger 양식)
- 역할 분담: 겹치지 않게 분리

주요 기능:
- send_telegram(): 텔레그램 메시지 전송
- tg(): 간편 전송 함수 (prefix 자동 추가)
- log_signal(): 신호 로깅 (구조화)
- log_trade(): 거래 로깅 (구조화)
- log_status(): 상태 로깅 (주기적)
"""
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from .logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def send_telegram(
    text: str,
    token: str,
    chat_id: str,
    parse_mode: str = "Markdown",
    bot_prefix: Optional[str] = None
) -> bool:
    """
    텔레그램 메시지 전송
    
    Args:
        text: 전송할 메시지
        token: 텔레그램 봇 토큰
        chat_id: 채팅방 ID
        parse_mode: 파싱 모드 (Markdown, HTML)
        bot_prefix: 봇 이름 prefix (예: *[SCALP]*)
    
    Returns:
        bool: 전송 성공 여부
    
    Examples:
        >>> send_telegram("테스트 메시지", token, chat_id)
        >>> send_telegram("신호 발생", token, chat_id, bot_prefix="*[SCALP]*")
    """
    # 봇 prefix 추가
    if bot_prefix and not text.startswith("*["):
        text = f"{bot_prefix} {text}"
    
    # 로깅용 단일 라인 변환 (개행 제거)
    log_text = text.replace('\n', ' | ').replace('\r', '')
    logger.info(f"[TELEGRAM] {log_text[:100]}...")
    
    # 토큰 검증
    if "PUT_YOUR" in token or "PUT_YOUR" in chat_id:
        logger.warning("⚠️  TOKEN/CHAT_ID 미설정")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        resp = requests.post(url, data=data, timeout=10)
        
        if resp.status_code != 200:
            logger.error(f"❌ 텔레그램 전송 실패: {resp.status_code}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 텔레그램 오류: {e}")
        return False


def tg(text: str, config: dict) -> bool:
    """
    텔레그램 메시지 간편 전송
    
    config['telegram']에서 토큰/채팅ID 자동 추출
    
    Args:
        text: 전송할 메시지
        config: 설정 딕셔너리 (telegram.token, telegram.chat_id 포함)
    
    Returns:
        bool: 전송 성공 여부
    
    Examples:
        >>> tg("신호 발생: BTCUSDT LONG", config)
    """
    # telegram 설정 추출
    tg_config = config.get("telegram", {})
    token = tg_config.get("token", "")
    chat_id = str(tg_config.get("chat_id", ""))  # int일 수 있으므로 str 변환
    enabled = tg_config.get("enabled", False)
    
    # 비활성화 확인
    if not enabled or "PUT_YOUR" in str(token) or "PUT_YOUR" in str(chat_id):
        logger.warning("⚠️ 텔레그램 비활성화 또는 설정 없음")
        return False
    
    return send_telegram(
        text=text,
        token=token,
        chat_id=chat_id
    )


def send_alert(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    reason: str,
    config: dict
) -> bool:
    """
    간단한 신호 알림 전송
    
    Args:
        symbol: 심볼
        direction: 방향 (LONG/SHORT)
        entry: 진입가
        sl: 손절가
        tp: 익절가
        reason: 신호 근거
        config: 설정 딕셔너리
    
    Returns:
        bool: 전송 성공 여부
    """
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} *{symbol} {direction}*

📍 진입: `{entry}`
🛑 손절: `{sl}`
🎯 익절: `{tp}`

💡 근거: {reason}
"""
    
    return tg(message.strip(), config)


# ============================================
# 메시지 포맷팅 (가독성 강화) ⭐
# ============================================
from .calculations import round_tick, tp_from_rr  # 계산 함수는 calculations 모듈에서 가져옴


def beginner_block(symbol: str, I: Dict[str, Any], entry, sl, tp1, tp2, qty, lev, config: dict) -> List[str]:
    """
    초보자 설명 블록 생성
    
    Args:
        symbol: 심볼
        I: 신호 정보
        entry: 진입가
        sl: 손절가
        tp1: 익절가 1
        tp2: 익절가 2
        qty: 수량
        lev: 레버리지
        config: 설정 딕셔너리
    
    Returns:
        List[str]: 설명 블록 라인들
    """
    if not config.get("enable_beginner_explain", False):
        return []
    
    atr = I.get("atr", 0)
    atr_pct = I.get("atr_pct", 0) * 100
    rr2 = config.get("tp2_rr", config.get("rr", 2.0))
    tp1_rr = config.get("tp1_rr", 1.5)
    atr_mult_sl = config.get("atr_mult_sl", 1.5)
    rr = config.get("rr", 2.0)
    
    lines = [
        "*초보자 설명 블럭*",
        f"- *ATR* = 최근 변동성 크기. 지금은 `{atr:.4f}` (가격의 약 `{atr_pct:.2f}%`).",
        f"- *RR* = 보상/위험 비율. TP1는 `{tp1_rr if config.get('enable_tp_trail') else '-'}x`, TP2는 `{rr2}x` 기준.",
        f"- *손절가(SL)* = 시장이 흔들려도 버틸 만큼의 거리로, `ATR × {atr_mult_sl}`를 더해 계산.",
        f"- *수량* = 한 번 틀려도 계좌가 크게 안 흔들리게, `자산×리스크% / |진입-손절|`로 산출.",
        f"- *레버리지* = 변동성 낮을수록 조금 높게, 높을수록 낮게. 제안값은 *x{lev}* (참고용).",
        f"- *이번 신호 근거* = " + ("; ".join(I.get("reason", [])) if I.get("reason") else "지표 조합에 따른 진입 조건 충족"),
        "",
        f"`예시 해석:` 진입 `{entry}` 에서 손절 `{sl}` 까지 거리가 손실 1이라면, TP2 `{tp2}` 에서 이익은 대략 `{rr} 배`.",
        "목표가(특히 TP1) 먼저 닿으면 일부 익절로 리스크 축소, 손절가는 진입가로 승격(무손실 가정)."
    ]
    return lines


def format_signal_alert(
    symbol: str,
    I: Dict[str, Any],
    qty: float,
    notional: float,
    margin: float,
    config: dict,
    total_equity: float = 0.0,
    active_positions: int = 0,
    max_positions: int = None,  # ⭐ None이면 config에서 읽기
    position_number: int = 1,
    cash_before: float = 0.0,
    cash_after: float = 0.0,
) -> str:
    """
    진입 알람 메시지 포맷팅 (P2 최종 확정 포맷)
    
    [PAPER][SCALPING] BTCUSDT | LONG X5 | P1🔵📈
    
    Args:
        symbol: 심볼 (BTCUSDT)
        I: 신호 정보 딕셔너리
        qty: 수량
        notional: 명목가치 (투입금액)
        margin: 증거금
        config: 설정 딕셔너리
        total_equity: 총 자산
        active_positions: 활성 포지션 수
        max_positions: 최대 포지션 수
        position_number: 포지션 번호 (P1, P2, ...)
    
    Returns:
        str: 포맷된 메시지
    """
    # config에서 이모지 추출
    tg_cfg = config.get("telegram", {})
    emoji_cfg = tg_cfg.get("emoji", {})
    
    # 방향 및 이모지
    side = I.get("side", "LONG")
    if side == "LONG":
        emoji_circle = emoji_cfg.get("long_circle", "🔵")
        emoji_arrow = emoji_cfg.get("long_arrow", "📈")
        side_text = "LONG"
    else:
        emoji_circle = emoji_cfg.get("short_circle", "🔴")
        emoji_arrow = emoji_cfg.get("short_arrow", "📉")
        side_text = "SHORT"
    
    # 전략명 (하드코딩 제거)
    strategy_name = (config.get("strategy", {}).get("selector") or "ENSEMBLE").upper()
    
    # ⭐ max_positions config에서 읽기
    if max_positions is None:
        max_positions = config.get('risk', {}).get('max_positions', 5)
    
    # 레버리지
    lev = I.get("lev", 1)
    
    # 가격 포맷
    entry = round_tick(symbol, I.get("entry", 0)) if I.get("entry") else 0
    sl = round_tick(symbol, I.get("sl", 0)) if I.get("sl") else 0
    tp2 = round_tick(symbol, I.get("tp", 0)) if I.get("tp") else 0
    
    # TP1 계산 (TP 분할 활성화 시)
    tp_sl_cfg = config.get("tp_sl", {})
    if tp_sl_cfg.get("enabled", False):
        tp1_rr = tp_sl_cfg.get("tp1_rr", 1.0)
        tp1 = round_tick(symbol, tp_from_rr(I, tp1_rr))
    else:
        tp1 = tp2
    
    # SL/TP 퍼센티지 계산
    sl_pct = ((sl - entry) / entry) * 100 if entry > 0 else 0
    tp1_pct = ((tp1 - entry) / entry) * 100 if entry > 0 else 0
    tp2_pct = ((tp2 - entry) / entry) * 100 if entry > 0 else 0
    
    # 현재 시간 (한국 시간, Asia/Seoul)
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    
    # 근거 생성
    reasons = I.get("reason", [])
    if isinstance(reasons, list):
        reason_text = "\n- ".join(reasons) if reasons else "신호 감지"
        if reasons:
            reason_text = "- " + reason_text
    else:
        reason_text = str(reasons)
    
    # 포지션 비중 계산 (노출 기준)
    position_ratio = (notional / total_equity) * 100 if total_equity > 0 else 0
    
    # 투입금액(증거금) 자산 대비 퍼센티지
    investment_pct = (margin / total_equity) * 100 if total_equity > 0 else 0
    
    # 메시지 구성 (사용자 최종 요구사항 반영)
    lines = [
        f"*[{strategy_name}] {symbol} | {side_text} X{lev}{emoji_circle}{emoji_arrow}*",
        "━━━━━━━━━━━━━━━━━",
        f"💰 진입가: {entry:,.2f} USDT",
        f"📦 수량: {qty:.4f} 계약",
        f"💵 투입금액: {margin:,.2f} USDT ({investment_pct:.1f}%)",
        "",
        f"🛡️ 스탑로스(SL): {sl:,.2f} ({sl_pct:+.2f}%)",
        f"🎯 목표가(TP1/TP2): {tp1:,.2f} ({tp1_pct:+.2f}%) / {tp2:,.2f} ({tp2_pct:+.2f}%)",
        "",
        "📌 시황 요약",
        reason_text,
        "",
        "📌 포트폴리오 현황",
        f"- 계좌: ${cash_before:,.0f} → ${cash_after:,.0f} (${margin:,.0f} 진입)",
        f"- 활성 포지션: {active_positions}/{max_positions}개",
        f"- 현재 포지션: P{position_number}",
        "",
        f"📆 시간: {now}",
        "━━━━━━━━━━━━━━━",
    ]
    
    return "\n".join(lines)


# ============================================
# 구조화된 로깅 함수 (내부 기록용)
# ============================================

def format_exit_alert(
    symbol: str,
    side: str,
    entry: float,
    exit_price: float,
    pnl: float,
    pnl_pct: float,
    reason: str,
    qty: float,
    slippage: float = 0.0,
    fee: float = 0.0,
    active_positions: int = 0,
    max_positions: int = None,  # ⭐ None이면 config에서 읽기
    total_equity: float = 0.0,
    equity_before: float = 0.0,
    daily_pnl: float = 0.0,
    position_number: int = 1,
    lev: float = 1.0,
    config: dict = None
) -> str:
    """
    청산 알람 메시지 포맷팅 (P2 최종 확정 포맷)
    
    [PAPER][SCALPING] BTCUSDT | STOP LOSS | P1⛔🛑
    
    Args:
        symbol: 심볼 (BTCUSDT)
        side: 방향 (LONG/SHORT)
        entry: 진입가
        exit_price: 청산가
        pnl: PnL (USDT)
        pnl_pct: PnL (%)
        reason: 청산 사유 (TP, SL, TP1, TP2, TRAILING_SL)
        qty: 수량
        slippage: 슬리피지 (USDT)
        fee: 수수료 (USDT)
        active_positions: 활성 포지션 수
        max_positions: 최대 포지션 수
        total_equity: 총 자산 (청산 후)
        equity_before: 총 자산 (청산 전)
        daily_pnl: 일일 누적 PnL
        position_number: 포지션 번호 (P1, P2, ...)
        config: 설정 딕셔너리
    
    Returns:
        str: 포맷된 메시지
    """
    if config is None:
        config = {}
    
    # config에서 이모지 추출
    tg_cfg = config.get("telegram", {})
    emoji_cfg = tg_cfg.get("emoji", {})
    
    # 이모지 및 제목 선택
    if reason in ["TP", "TP2"]:
        emoji = emoji_cfg.get("take_profit", "✅🏆")
        title_reason = "TAKE PROFIT"
    elif reason in ["SL", "STOP_LOSS", "TRAILING_SL"]:
        emoji = emoji_cfg.get("stop_loss", "⛔🛑")
        title_reason = "STOP LOSS"
    elif reason == "TP1":
        emoji = emoji_cfg.get("tp1_partial", "🟡🎯")
        title_reason = "PARTIAL TP1"
    else:
        emoji = emoji_cfg.get("default", "⚪")
        title_reason = reason.upper()
    
    # 전략명 (하드코딩 제거)
    strategy_name = (config.get("strategy", {}).get("selector") or "ENSEMBLE").upper()
    
    # ⭐ max_positions config에서 읽기
    if max_positions is None:
        max_positions = config.get('risk', {}).get('max_positions', 5)
    
    # 손익 계산 (비용 포함)
    net_pnl = pnl - slippage - fee
    net_pnl_pct = (net_pnl / (entry * qty)) * 100 if qty > 0 else 0
    
    # 슬리피지/수수료 퍼센티지
    slippage_pct = (slippage / (entry * qty)) * 100 if qty > 0 else 0
    fee_pct = (fee / (entry * qty)) * 100 if qty > 0 else 0
    
    # 포지션 비중
    position_ratio = (active_positions / max_positions) * 100 if max_positions > 0 else 0
    
    # 총 자산 변동 퍼센티지
    equity_change_pct = ((total_equity - equity_before) / equity_before) * 100 if equity_before > 0 else 0
    
    # 일일 누적 손익 퍼센티지 (초기 자산 대비)
    initial_equity = config.get("capital", {}).get("initial", 50000)
    daily_pnl_pct = (daily_pnl / initial_equity) * 100 if initial_equity > 0 else 0
    
    # 현재 시간 (한국 시간, Asia/Seoul)
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    
    # 방향 텍스트
    side_text = (side or "").upper()

    # 메시지 구성 (사용자 최종 요구사항 반영)
    lines = [
        f"*[{strategy_name}] {symbol} | {side_text} X{lev}{emoji}*",
        "━━━━━━━━━━━━━━━━━",
        f"💰 평균 진입가: {entry:,.2f}",
        f"📊 청산가: {exit_price:,.2f}",
        f"💸 손익(PnL): {pnl:+.2f} USDT ({pnl_pct:+.2f}%)",
        "",
        "💸 거래 비용",
        f"- 슬리피지: {slippage:+.2f} USDT ({slippage_pct:+.2f}%)",
        f"- 수수료: {fee:+.2f} USDT ({fee_pct:+.2f}%)",
        f"✅ 순손익: {net_pnl:+.2f} USDT ({net_pnl_pct:+.2f}%)",
        "",
        "📌 포트폴리오 현황",
        f"- 총 자산: ${equity_before:,.0f} → ${total_equity:,.0f} ({equity_change_pct:+.2f}%)",
        f"- 활성 포지션: {active_positions}/{max_positions}개 (비중 {position_ratio:.1f}%)",
        f"- 현재 포지션: P{position_number} 청산",
        "",
        f"📈 일일 누적 손익: {daily_pnl:+.2f} USDT ({daily_pnl_pct:+.2f}%)",
        f"📆 시간: {now}",
        "━━━━━━━━━━━━━━━"
    ]
    
    return "\n".join(lines)


def log_signal(strategy: str, symbol: str, side: str, entry: float, sl: float, tp: float, confidence: float = 0.0):
    """
    신호 로깅 (구조화)
    
    Args:
        strategy: 전략명
        symbol: 심볼
        side: 방향 (LONG/SHORT)
        entry: 진입가
        sl: 손절가
        tp: 익절가
        confidence: 신뢰도 (0~1)
    """
    emoji = "🟢" if side == "LONG" else "🔴"
    logger.info(f"{emoji} [{strategy.upper()}] {symbol} {side} | Entry: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f} | Conf: {confidence:.1%}")


def log_trade(strategy: str, symbol: str, side: str, entry: float, exit_price: float, qty: float, pnl: float, reason: str = ""):
    """
    거래 로깅 (구조화)
    
    Args:
        strategy: 전략명
        symbol: 심볼
        side: 방향 (LONG/SHORT)
        entry: 진입가
        exit_price: 청산가
        qty: 수량
        pnl: PnL
        reason: 청산 사유
    """
    emoji = "🟢" if pnl >= 0 else "🔴"
    pnl_pct = (pnl / (entry * qty)) * 100 if qty > 0 else 0
    logger.info(f"{emoji} [{strategy.upper()}] {symbol} {side} | Entry: {entry:.2f} → Exit: {exit_price:.2f} | PnL: {pnl:+,.2f} ({pnl_pct:+.2f}%) | {reason}")


def log_status(strategy: str, candle_count: int, active_positions: int, total_trades: int, equity: float):
    """
    상태 로깅 (주기적, 10분마다)
    
    Args:
        strategy: 전략명
        candle_count: 수신한 캔들 수
        active_positions: 활성 포지션 수
        total_trades: 총 거래 수
        equity: 현재 자산
    """
    strategy_name = strategy.upper() if strategy else "ENSEMBLE"
    logger.info(f"💓 [{strategy_name}] 상태: 캔들 {candle_count:,}개 | 활성 포지션: {active_positions}개 | 총 거래: {total_trades}건 | Equity: ${equity:,.0f}")


def log_performance(strategy: str, send_telegram: bool = False, config: dict = None):
    """
    성능 로깅 + 텔레그램 (점수 포함)
    
    Args:
        strategy: 전략명
        send_telegram: 텔레그램 전송 여부
        config: 설정 딕셔너리
    """
    from monitoring.performance_monitor import get_performance_report
    
    # 성능 리포트 생성
    report = get_performance_report(strategy)
    
    # 로그 출력
    logger.info(report)
    
    # 텔레그램 전송 (선택적)
    if send_telegram and config:
        tg(report, config)


def log_daily_report(strategy: str, total_trades: int, win_trades: int, loss_trades: int, 
                     total_pnl: float, win_rate: float, avg_pnl: float, max_dd: float, config: dict):
    """
    일일 리포트 로깅 + 텔레그램 알림
    
    Args:
        strategy: 전략명
        total_trades: 총 거래 수
        win_trades: 승리 거래 수
        loss_trades: 손실 거래 수
        total_pnl: 총 PnL
        win_rate: 승률 (%)
        avg_pnl: 평균 PnL
        max_dd: 최대 낙폭 (%)
        config: 설정 딕셔너리
    """
    # 로그 기록
    logger.info(f"📊 [{strategy.upper()}] 일일 리포트: 거래 {total_trades}건 | 승률 {win_rate:.1f}% | PnL {total_pnl:+,.2f} | MDD {max_dd:.2f}%")
    
    # 텔레그램 알림
    msg = f"""📊 *[{strategy.upper()}] 일일 리포트*
━━━━━━━━━━━━━━━
📈 거래 수: {total_trades}건
✅ 승리: {win_trades}건
❌ 손실: {loss_trades}건
📊 승률: {win_rate:.1f}%
💰 총 PnL: {total_pnl:+,.2f} USDT
💵 평균 PnL: {avg_pnl:+,.2f} USDT
📉 최대 낙폭: {max_dd:.2f}%
━━━━━━━━━━━━━━━"""
    
    tg(msg, config)


# ============================================
# 시스템 상태 알람 (상용 필수)
# ============================================

def system_start_alert(strategy: str, mode: str, symbols: list, equity: float, config: dict):
    """
    시스템 시작 알람
    
    Args:
        strategy: 전략명
        mode: 모드 (backtest/paper/live)
        symbols: 거래 심볼 리스트
        equity: 초기 자산
        config: 설정 딕셔너리
    """
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    
    msg = f"""🚀 *시스템 시작*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📌 모드: {mode.upper()}
📌 심볼: {len(symbols)}개
💰 자산: ${equity:,.0f}
🕐 시간: {now}
━━━━━━━━━━━━━━━"""
    
    logger.info(f"🚀 [{strategy.upper()}] 시스템 시작 | Mode: {mode} | Equity: ${equity:,.0f}")
    tg(msg, config)


def system_stop_alert(strategy: str, reason: str, config: dict):
    """
    시스템 종료 알람
    
    Args:
        strategy: 전략명
        reason: 종료 사유
        config: 설정 딕셔너리
    """
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime("%Y-%m-%d %H:%M")
    
    msg = f"""🛑 *시스템 종료*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📌 사유: {reason}
🕐 시간: {now}
━━━━━━━━━━━━━━━"""
    
    logger.info(f"🛑 [{strategy.upper()}] 시스템 종료 | Reason: {reason}")
    tg(msg, config)


def system_error_alert(strategy: str, error: str, config: dict):
    """
    시스템 에러 알람
    
    Args:
        strategy: 전략명
        error: 에러 메시지
        config: 설정 딕셔너리
    """
    msg = f"""❌ *시스템 에러*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
❌ 에러: {error}
━━━━━━━━━━━━━━━"""
    
    logger.error(f"❌ [{strategy.upper()}] 시스템 에러: {error}")
    tg(msg, config)


def heartbeat_alert(strategy: str, uptime_hours: float, candle_count: int, active_positions: int, config: dict):
    """
    하트비트 알람 (주기적 생존 확인)
    
    Args:
        strategy: 전략명
        uptime_hours: 가동 시간 (시간)
        candle_count: 수신한 캔들 수
        active_positions: 활성 포지션 수
        config: 설정 딕셔너리
    """
    msg = f"""💓 *하트비트*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
⏰ 가동: {uptime_hours:.1f}h
📊 캔들: {candle_count:,}개
📈 포지션: {active_positions}개
━━━━━━━━━━━━━━━"""
    
    logger.info(f"💓 [{strategy.upper()}] Heartbeat | Uptime: {uptime_hours:.1f}h | Candles: {candle_count:,}")
    tg(msg, config)


# ============================================
# 리스크 관리 알람 (상용 중요)
# ============================================

def risk_guard_alert(strategy: str, daily_loss: float, daily_limit: float, config: dict):
    """
    리스크 가드 발동 알람 (일일 손실 한도 도달)
    
    Args:
        strategy: 전략명
        daily_loss: 일일 손실
        daily_limit: 일일 손실 한도
        config: 설정 딕셔너리
    """
    loss_pct = (daily_loss / daily_limit) * 100
    
    msg = f"""🚨 *리스크 가드 발동*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📉 일일 손실: ${daily_loss:,.2f}
🛑 손실 한도: ${daily_limit:,.2f}
📊 도달률: {loss_pct:.1f}%
⚠️ 신규 거래 중단
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"🚨 [{strategy.upper()}] 리스크 가드 발동 | Loss: ${daily_loss:,.2f} / ${daily_limit:,.2f}")
    tg(msg, config)


def consecutive_loss_alert(strategy: str, loss_count: int, cooldown_candles: int, config: dict):
    """
    연속 손실 쿨다운 알람
    
    Args:
        strategy: 전략명
        loss_count: 연속 손실 횟수
        cooldown_candles: 쿨다운 캔들 수
        config: 설정 딕셔너리
    """
    msg = f"""⏸️ *연속 손실 쿨다운*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
❌ 연속 손실: {loss_count}회
⏰ 쿨다운: {cooldown_candles}캔들
⚠️ 거래 일시 중지
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"⏸️ [{strategy.upper()}] 연속 손실 쿨다운 | Loss: {loss_count}회 | Cooldown: {cooldown_candles}캔들")
    tg(msg, config)


def flash_guard_alert(strategy: str, symbol: str, price_change_pct: float, config: dict):
    """
    Flash Guard 발동 알람 (급격한 가격 변동)
    
    Args:
        strategy: 전략명
        symbol: 심볼
        price_change_pct: 가격 변동 (%)
        config: 설정 딕셔너리
    """
    msg = f"""⚡ *Flash Guard 발동*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📌 심볼: {symbol}
📊 변동: {price_change_pct:+.2f}%
⚠️ 급격한 가격 변동 감지
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"⚡ [{strategy.upper()}] Flash Guard | {symbol} | {price_change_pct:+.2f}%")
    tg(msg, config)


def exposure_limit_alert(strategy: str, current_exposure: float, max_exposure: float, config: dict):
    """
    노출 한도 초과 알람
    
    Args:
        strategy: 전략명
        current_exposure: 현재 노출 (%)
        max_exposure: 최대 노출 (%)
        config: 설정 딕셔너리
    """
    msg = f"""🚫 *노출 한도 초과*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📊 현재 노출: {current_exposure:.1f}%
🛑 최대 노출: {max_exposure:.1f}%
⚠️ 신규 포지션 불가
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"🚫 [{strategy.upper()}] 노출 한도 초과 | {current_exposure:.1f}% / {max_exposure:.1f}%")
    tg(msg, config)


# ============================================
# 포트폴리오 알람
# ============================================

def max_positions_alert(strategy: str, current_positions: int, max_positions: int, config: dict):
    """
    최대 포지션 도달 알람
    
    Args:
        strategy: 전략명
        current_positions: 현재 포지션 수
        max_positions: 최대 포지션 수
        config: 설정 딕셔너리
    """
    msg = f"""⚠️ *최대 포지션 도달*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📊 포지션: {current_positions}/{max_positions}개
⚠️ 신규 진입 불가
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"⚠️ [{strategy.upper()}] 최대 포지션 도달 | {current_positions}/{max_positions}")
    tg(msg, config)


def weekly_report_alert(strategy: str, total_trades: int, win_rate: float, total_pnl: float, 
                       max_dd: float, sharpe: float, config: dict):
    """
    주간 리포트 알람
    
    Args:
        strategy: 전략명
        total_trades: 총 거래 수
        win_rate: 승률 (%)
        total_pnl: 총 PnL
        max_dd: 최대 낙폭 (%)
        sharpe: 샤프 비율
        config: 설정 딕셔너리
    """
    msg = f"""📊 *주간 리포트*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📈 거래: {total_trades}건
✅ 승률: {win_rate:.1f}%
💰 PnL: {total_pnl:+,.2f} USDT
📉 MDD: {max_dd:.2f}%
📊 Sharpe: {sharpe:.2f}
━━━━━━━━━━━━━━━"""
    
    logger.info(f"📊 [{strategy.upper()}] 주간 리포트 | Trades: {total_trades} | Win Rate: {win_rate:.1f}% | PnL: {total_pnl:+,.2f}")
    tg(msg, config)


# ============================================
# 연결 상태 알람
# ============================================

def connection_lost_alert(strategy: str, connection_type: str, config: dict):
    """
    연결 끊김 알람
    
    Args:
        strategy: 전략명
        connection_type: 연결 유형 (WebSocket, REST API)
        config: 설정 딕셔너리
    """
    msg = f"""🔌 *연결 끊김*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
❌ 유형: {connection_type}
⚠️ 재연결 시도 중...
━━━━━━━━━━━━━━━"""
    
    logger.error(f"🔌 [{strategy.upper()}] 연결 끊김 | Type: {connection_type}")
    tg(msg, config)


def connection_restored_alert(strategy: str, connection_type: str, downtime_sec: int, config: dict):
    """
    연결 복구 알람
    
    Args:
        strategy: 전략명
        connection_type: 연결 유형
        downtime_sec: 끊겼던 시간 (초)
        config: 설정 딕셔너리
    """
    msg = f"""✅ *연결 복구*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
✅ 유형: {connection_type}
⏱️ 다운타임: {downtime_sec}초
━━━━━━━━━━━━━━━"""
    
    logger.info(f"✅ [{strategy.upper()}] 연결 복구 | Type: {connection_type} | Downtime: {downtime_sec}s")
    tg(msg, config)


def data_gap_alert(strategy: str, symbol: str, gap_size: int, config: dict):
    """
    데이터 갭 감지 알람
    
    Args:
        strategy: 전략명
        symbol: 심볼
        gap_size: 갭 크기 (캔들 수)
        config: 설정 딕셔너리
    """
    msg = f"""⚠️ *데이터 갭 감지*
━━━━━━━━━━━━━━━
📌 전략: {strategy.upper()}
📌 심볼: {symbol}
❌ 갭: {gap_size}캔들
⚠️ 데이터 무결성 확인 필요
━━━━━━━━━━━━━━━"""
    
    logger.warning(f"⚠️ [{strategy.upper()}] 데이터 갭 | {symbol} | Gap: {gap_size}캔들")
    tg(msg, config)
