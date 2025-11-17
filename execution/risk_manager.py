#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Manager - 리스크 관리 및 한도 체크
======================================
Pre-Trade Risk Check 및 포지션 관리

원본: trading_executor.py 라인 387-533
실밥 리팩토링 주석: 라인 381

기능:
- 일일 손실 한도
- 동시 포지션 수 제한
- 심볼별/전략별 한도
- 순노출 한도
- Flash Guard (급등락 감지 - Circuit Breaker)

⭐ PHASE17 추가 기능:
- Per-symbol Exposure Guard 3단계 의사결정 (ALLOW/ALLOW_REDUCED/BLOCK)
- 사이즈 축소 후 진입 허용 (가드레일 철학)

참고: docs/implementation/EXECUTION_MODULE_REFACTORING.md
"""
import os
import time
from typing import Dict, Tuple, NamedTuple
from dataclasses import dataclass

from common.logger import setup_logger
from common.messaging import tg

logger = setup_logger(__name__, log_type="trading")


# ⭐ PHASE17: Exposure Guard 3단계 의사결정 결과
@dataclass
class ExposureDecision:
    """
    Per-symbol Exposure Guard 의사결정 결과
    
    Attributes:
        decision: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
        adjusted_notional: 조정된 포지션 금액 (USDT)
        reason: 결정 사유
        original_notional: 원래 요청 금액
        current_exposure: 현재 심볼 노출도
        max_exposure: 최대 허용 노출도
    """
    decision: str  # "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
    adjusted_notional: float
    reason: str
    original_notional: float = 0.0
    current_exposure: float = 0.0
    max_exposure: float = 0.0


class RiskManager:
    """
    리스크 관리 및 한도 체크
    (업계 표준: Daily loss limit + Position limits + Flash Guard)
    
    ⭐ PR12: PortfolioManager로 PnL 관리 통합, 가드 로직만 유지
    """
    
    def __init__(self, config: dict, portfolio=None):
        """
        Args:
            config: config.yml 전체 설정
        """
        # 모드 확인
        self.mode = config.get('mode', 'paper')
        
        # 자본 (config.yml에서)
        self.equity = config['capital']['initial']
        self.initial_equity = self.equity
        
        # ⭐⭐⭐ 모드별 프로파일 자동 로드
        _risk = config.get('risk', {})
        _profiles = _risk.get('profiles', {})
        
        # 현재 모드에 맞는 프로파일 선택
        if self.mode == 'live' and 'live' in _profiles:
            _profile = _profiles['live']
            logger.info("🔴 [LIVE MODE] 가드 엄격 (보수적 운영)")
        elif self.mode == 'paper' and 'paper' in _profiles:
            _profile = _profiles['paper']
            logger.info("🟡 [PAPER MODE] 가드 완화 (운영 흐름 검증)")
        else:
            _profile = {}
            logger.info(f"⚠️  [{self.mode.upper()} MODE] 기본 리스크 설정 사용")
        
        # 프로파일 설정 병합 (프로파일 우선, 없으면 기본값)
        def get_value(key, default):
            # 1순위: 프로파일의 값
            if key in _profile:
                return _profile[key]
            # 2순위: risk 섭션의 기본값
            if key in _risk:
                return _risk[key]
            # 3순위: 하드코딩 기본값
            return default
        
        # 일일 손실 한도
        _ddl_pct = get_value('max_daily_loss_pct', 2.0)
        if _ddl_pct is None:
            # 일일 손실 한도 비활성화
            self.daily_loss_limit_pct = None
            self.daily_loss_limit = None
            logger.info("✅ 일일 손실 한도: OFF")
        else:
            _ddl_frac = float(_ddl_pct) / 100.0 if _ddl_pct > 1 else float(_ddl_pct)
            self.daily_loss_limit_pct = max(0.0, min(1.0, _ddl_frac))
            self.daily_loss_limit = self.daily_loss_limit_pct * self.equity
            logger.info(f"✅ 일일 손실 한도: {self.daily_loss_limit_pct*100:.1f}% (${self.daily_loss_limit:,.0f})")
        
        # 포지션 한도
        self.max_positions = config['risk']['max_positions']
        self.max_exposure_per_symbol_pct = config['risk']['max_exposure_per_symbol']
        
        # ⭐ PR11: 추가 리스크 가드 (DD cutoff, Slippage Guard)
        # DD cutoff (최대 낙폭 강제 차단)
        self.max_drawdown_pct = get_value('max_drawdown_pct', 10.0) / 100.0  # 10% 기본값
        self.max_drawdown_limit = self.max_drawdown_pct * self.equity
        logger.info(f"✅ 최대 낙폭 한도: {self.max_drawdown_pct*100:.1f}% (${self.max_drawdown_limit:,.0f})")
        
        # Slippage Guard (예상 슬리피지 차단)
        self.max_slippage_pct = get_value('max_slippage_pct', 0.5) / 100.0  # 0.5% 기본값
        logger.info(f"✅ 슬리피지 가드: {self.max_slippage_pct*100:.2f}%")
        
        # 극단 손실 cutoff (PR10 연계, 중복 방지)
        # PR10 position_tracker.py L198-207에서 -50% cutoff 이미 구현됨
        # 여기서는 더 보수적인 임계값 설정 (예: -30%)
        self.extreme_loss_cutoff_pct = get_value('extreme_loss_cutoff_pct', -30.0) / 100.0  # -30% 기본값
        logger.info(f"✅ 극단 손실 가드: {self.extreme_loss_cutoff_pct*100:.1f}% (PR10 -50% cutoff와 연계)")
        
        # ⭐ PR12: 포트폴리오 참조 추가
        self.portfolio = portfolio
        
        # 현재 상태 (나중에 DB에서 읽기)
        self.current_drawdown = 0.0  # 현재 낙폭
        self.peak_equity = self.equity  # 최고점 자본
        self.active_positions_count = 0
        self.symbol_exposures = {}  # {symbol: position_value}
        
        # Flash Guard (급등락 감지 - Circuit Breaker)
        self.config = config
        _fg = (config.get('flash_guard') or {}) if isinstance(config.get('flash_guard'), dict) else {}
        if _fg:
            try:
                config['enable_flash_guard'] = bool(_fg.get('enabled', _fg.get('enable', False)))
                config['flash_window_sec'] = int(_fg.get('window_sec', _fg.get('window', 60)))
                _thr = _fg.get('threshold_pct', _fg.get('threshold', _fg.get('pct')))
                if _thr is not None:
                    try:
                        _thr_val = float(_thr)
                    except Exception:
                        _thr_val = 0.03
                    if _thr_val > 1:
                        _thr_val = _thr_val / 100.0
                    config['flash_pct'] = _thr_val
                config['flash_pause_candles'] = int(_fg.get('pause_candles', _fg.get('pause', 3)))
            except Exception:
                pass
        self.flash_buffers = {}
        self.flash_pause_until = {}
        try:
            # flash_guard 섹션에서 log_throttle_sec 읽기 (기본값: 300초 = 5분)
            flash_guard_cfg = config.get('flash_guard', {})
            throttle_sec = float(flash_guard_cfg.get('log_throttle_sec', 300))
            self._flash_log_throttle_ms = int(throttle_sec * 1000)
        except Exception:
            self._flash_log_throttle_ms = 300000  # 5분 기본값
        self._last_flash_log_ts = {}
        
        # ⭐ TUNING_VIBLE: 연속 손실 쿨다운
        _max_consec = get_value('max_consecutive_losses', 4)
        self.max_consecutive_losses = None if _max_consec is None else int(_max_consec)
        self.consecutive_losses = 0  # 현재 연속 손실 횟수
        self.in_cooldown = False  # 쿨다운 상태
        self.cooldown_start_time = 0  # 쿨다운 시작 시각
        
        # 쿨다운 시간 (분 단위)
        _cooldown = get_value('cooldown_after_consecutive', 30)
        self.cooldown_minutes = 0 if _cooldown is None else int(_cooldown)
        
        # 백테스트에서도 일일 손실 한도 적용 여부
        self.enforce_daily_loss_in_backtest = get_value('enforce_daily_loss_in_backtest', True)
        
        # 전체 자산 중지 한도 (equity stop)
        _eq_stop = get_value('equity_stop_pct', None)
        self.equity_stop_pct = None if _eq_stop is None else float(_eq_stop)
        self.equity_stop_limit = None if self.equity_stop_pct is None else (self.equity_stop_pct / 100.0 * self.equity)
        
        # 로그 출력
        daily_info = "OFF" if self.daily_loss_limit is None else f"${self.daily_loss_limit:,.0f}"
        consec_info = "OFF" if self.max_consecutive_losses is None else f"{self.max_consecutive_losses}회"
        cooldown_info = "OFF" if self.cooldown_minutes == 0 else f"{self.cooldown_minutes}분"
        logger.info(f"✅ RiskManager 초기화: Daily={daily_info}, Consecutive={consec_info}, Cooldown={cooldown_info}")
        # Guard alert throttle
        self._guard_alert_reason = ""
        self._guard_alert_ts = 0

    def _notify_guard(self, reason: str):
        """Send Telegram alert for guard blocks with basic throttling."""
        alerts_cfg = {}
        try:
            alerts_cfg = (self.config.get('telegram', {}).get('alerts', {})) if isinstance(self.config.get('telegram'), dict) else {}
        except Exception:
            alerts_cfg = {}
        if alerts_cfg.get('guard_blocks', True) and self.mode in ['paper', 'live']:
            now = time.time()
            if reason == getattr(self, "_guard_alert_reason", "") and now - getattr(self, "_guard_alert_ts", 0) < 300:
                return
            try:
                tg(f"🛑 Guard block [{self.mode.upper()}]: {reason}", self.config)
            except Exception:
                pass
            self._guard_alert_reason = reason
            self._guard_alert_ts = now
    
    # ============================================
    # Flash Guard (급등락 감지 - Circuit Breaker)
    # ============================================
    def _tf_ms(self) -> int:
        """타임프레임을 밀리초로 변환"""
        tf = self.config.get("timeframe", "5m")
        if tf.endswith("m"): return int(tf[:-1]) * 60 * 1000
        if tf.endswith("h"): return int(tf[:-1]) * 60 * 60 * 1000
        if tf.endswith("d"): return int(tf[:-1]) * 24 * 60 * 60 * 1000
        return 5*60*1000
    
    def flash_guard_update(self, symbol: str, price: float, ts_ms: int):
        """
        Flash Guard 업데이트 (급등락 감지)
        
        Args:
            symbol: 심볼
            price: 현재 가격
            ts_ms: 타임스탬프 (ms)
        """
        if not self.config.get("enable_flash_guard", False):
            return
        
        from collections import deque
        
        # Buffer 초기화
        if symbol not in self.flash_buffers:
            self.flash_buffers[symbol] = deque(maxlen=600)
        
        buf = self.flash_buffers[symbol]
        buf.append((ts_ms, price))
        
        # 최소 샘플 확보 전에는 판단/로그 생략
        if len(buf) < 10:
            return
        
        # 윈도우 밖 데이터 제거
        window = self.config.get("flash_window_sec", 60) * 1000
        while buf and ts_ms - buf[0][0] > window:
            buf.popleft()
        
        # 변동률 체크
        if len(buf) >= 2:
            p0 = buf[0][1]
            if p0 is None or p0 <= 0:
                return
            change = abs(price - p0) / p0
            flash_pct = self.config.get("flash_pct", 0.03)
            
            if change >= flash_pct:
                pause_candles = self.config.get("flash_pause_candles", 3)
                self.flash_pause_until[symbol] = ts_ms + self._tf_ms() * pause_candles
                last_log = self._last_flash_log_ts.get(symbol, 0)
                now_ms = int(time.time() * 1000)
                if now_ms - last_log >= self._flash_log_throttle_ms:
                    logger.warning(f"🛡 {symbol} Flash-Guard: {self.config.get('flash_window_sec', 60)}초에 {change*100:.2f}% 변동 → 신호 일시 보류")
                    self._last_flash_log_ts[symbol] = now_ms
    
    def flash_guard_allowed(self, symbol: str, ts_ms: int) -> bool:
        """
        Flash Guard 허용 여부 확인
        
        Args:
            symbol: 심볼
            ts_ms: 타임스탬프 (ms)
        
        Returns:
            bool: 허용 여부
        """
        until = self.flash_pause_until.get(symbol)
        if not until:
            return True
        return ts_ms >= until
    
    
    # ============================================
    # Pre-Trade Risk Checks
    # ============================================
    def check_order(self, signal: Dict, qty: float, position_value: float = None) -> Tuple[bool, str]:
        """
        주문 실행 전 리스크 체크
        
        Args:
            signal: 신호 dict
            qty: 수량
            position_value: 포지션 가치 (position_sizer 계산값, None이면 재계산)
        
        Returns:
            (allowed, reason)
        """
        symbol = signal.get('symbol', 'UNKNOWN')
        # ⭐ position_sizer 계산값 우선 사용 (재계산 방지!)
        if position_value is None:
            position_value = qty * signal['entry_price']
        
        # 0-1) ⭐⭐⭐ 자본 소진 체크 (모든 모드)
        if self.equity <= 0:
            return False, f"자본 소진: ${self.equity:.2f}"
        
        # 0-2) ⭐ TUNING_VIBLE: 연속 손실 쿨다운 체크 (프로파일에 따라)
        if self.in_cooldown:
            # 쿨다운 시간 경과 확인
            if self.cooldown_minutes > 0:
                elapsed = (time.time() - self.cooldown_start_time) / 60  # 분 단위
                if elapsed >= self.cooldown_minutes:
                    self.in_cooldown = False
                    logger.info(f"✅ 쿨다운 해제 ({self.cooldown_minutes}분 경과)")
                else:
                    remaining = max(0, self.cooldown_minutes - int(elapsed))
                    self._notify_guard(f"Cooldown active: {self.consecutive_losses} losses, {remaining}m left")
                    return False, f"연속 손실 쿨다운 ({self.consecutive_losses}회, {remaining}분 남음)"
            else:
                # 쿨다운 OFF 모드
                self.in_cooldown = False
        
        # 1) 일일 손실 한도 체크 (프로파일에 따라 ON/OFF)
        if self.daily_loss_limit is not None and self.portfolio is not None:
            daily_pnl = self.portfolio.get_daily_pnl()
            if ((self.mode != 'backtest') or self.enforce_daily_loss_in_backtest) and abs(daily_pnl) >= self.daily_loss_limit:
                self._notify_guard(f"Daily loss limit hit: {daily_pnl:.2f} ≥ {self.daily_loss_limit:.2f}")
                return False, f"일일 손실 한도 초과: {daily_pnl:.2f}"
        
        # 1-1) 전체 자산 중지 한도 (equity stop)
        if self.equity_stop_limit is not None:
            dd = max(0.0, self.initial_equity - self.equity)
            if dd >= self.equity_stop_limit:
                self._notify_guard(f"Equity stop hit: DD={dd:.2f} ≥ {self.equity_stop_limit:.2f}")
                return False, f"전체 자산 중지 한도 초과: {dd:.2f}"
        
        # 2) 동시 포지션 수 체크 (⭐ PHASE16+: 0 = 무제한)
        if self.max_positions > 0 and self.active_positions_count >= self.max_positions:
            self._notify_guard(f"Max positions reached: {self.active_positions_count}/{self.max_positions}")
            return False, f"동시 포지션 한도 도달: {self.active_positions_count}/{self.max_positions}"
        
        # 3) 심볼별 노출 한도 체크
        max_per_symbol = self.equity * self.max_exposure_per_symbol_pct
        current_exposure = self.symbol_exposures.get(symbol, 0.0)
        
        # 디버깅 로그
        logger.debug(f"💰 Exposure 체크: {symbol}")
        logger.debug(f"   현재: ${current_exposure:.2f}")
        logger.debug(f"   신규: ${position_value:.2f}")
        logger.debug(f"   합계: ${current_exposure + position_value:.2f}")
        logger.debug(f"   한도: ${max_per_symbol:.2f}")
        
        # ⭐ 부동소수점 안전 비교 (금융 프로그램 표준, epsilon=0.1 USDT)
        # 실제 반올림 오차는 0.01~0.09 범위이므로 0.1 적용
        epsilon = 0.1
        total_exposure = current_exposure + position_value
        if total_exposure > max_per_symbol + epsilon:
            self._notify_guard(f"Per-symbol exposure limit: {symbol} {total_exposure:.2f} > {max_per_symbol:.2f}")
            return False, f"심볼별 한도 초과: {symbol} {total_exposure:.2f} > {max_per_symbol:.2f}"
        
        # 모든 체크 통과
        return True, "OK"
    
    # =========================================================================
    # ⭐ PHASE17: Per-symbol Exposure Guard 3단계 의사결정
    # =========================================================================
    
    def check_symbol_exposure_with_adjustment(
        self,
        symbol: str,
        requested_notional: float,
        current_exposure: float = None,
        min_position_notional: float = None
    ) -> ExposureDecision:
        """
        ⭐ PHASE17: Per-symbol Exposure 체크 + 사이즈 조정
        
        3단계 의사결정:
        1. ALLOW: 정상 진입 (노출도 범위 내)
        2. ALLOW_REDUCED: 사이즈 축소 후 진입 (노출도 초과 시)
        3. BLOCK: 완전 차단 (현재 노출도가 이미 한계)
        
        Args:
            symbol: 심볼 (BTCUSDT 등)
            requested_notional: 요청한 포지션 금액 (USDT)
            current_exposure: 현재 심볼 노출도 (None이면 symbol_exposures에서 읽기)
            min_position_notional: 최소 포지션 금액 (None이면 config에서 읽기)
        
        Returns:
            ExposureDecision: 의사결정 결과
        """
        # 1. 현재 노출도 파악
        if current_exposure is None:
            current_exposure = self.symbol_exposures.get(symbol, 0.0)
        
        # 2. 최대 노출도 한도 계산
        max_symbol_exposure = self.equity * self.max_exposure_per_symbol_pct
        
        # 3. 최소 포지션 금액
        if min_position_notional is None:
            min_position_notional = self.config.get('position_sizing', {}).get('min_position_notional', 100)
        
        # 4. 총 노출도 계산
        total_exposure = current_exposure + requested_notional
        
        # 5. 3단계 의사결정
        
        # 5-1. ALLOW: 정상 진입
        if total_exposure <= max_symbol_exposure:
            logger.debug(
                f"✅ {symbol} Exposure ALLOW: "
                f"현재=${current_exposure:.2f}, "
                f"요청=${requested_notional:.2f}, "
                f"합계=${total_exposure:.2f}, "
                f"한도=${max_symbol_exposure:.2f}"
            )
            return ExposureDecision(
                decision="ALLOW",
                adjusted_notional=requested_notional,
                reason="Within exposure limit",
                original_notional=requested_notional,
                current_exposure=current_exposure,
                max_exposure=max_symbol_exposure
            )
        
        # 5-2. ALLOW_REDUCED: 사이즈 축소 후 진입
        if current_exposure < max_symbol_exposure:
            available_exposure = max_symbol_exposure - current_exposure
            
            # 안전 마진 적용 (95%)
            exposure_reduction_factor = self.config.get('position_sizing', {}).get('exposure_reduction_factor', 0.95)
            adjusted_notional = available_exposure * exposure_reduction_factor
            
            # 최소 포지션 크기 체크
            if adjusted_notional >= min_position_notional:
                logger.warning(
                    f"⚠️  {symbol} Exposure ALLOW_REDUCED: "
                    f"현재=${current_exposure:.2f}, "
                    f"요청=${requested_notional:.2f}, "
                    f"조정=${adjusted_notional:.2f}, "
                    f"한도=${max_symbol_exposure:.2f}"
                )
                return ExposureDecision(
                    decision="ALLOW_REDUCED",
                    adjusted_notional=adjusted_notional,
                    reason=f"Reduced from ${requested_notional:.2f} to stay within limit",
                    original_notional=requested_notional,
                    current_exposure=current_exposure,
                    max_exposure=max_symbol_exposure
                )
            else:
                # 조정한 금액이 최소 크기보다 작음 → BLOCK
                logger.error(
                    f"❌ {symbol} Exposure BLOCK: "
                    f"조정 금액=${adjusted_notional:.2f} < 최소=${min_position_notional:.2f}"
                )
                return ExposureDecision(
                    decision="BLOCK",
                    adjusted_notional=0.0,
                    reason=f"Adjusted size (${adjusted_notional:.2f}) below minimum (${min_position_notional:.2f})",
                    original_notional=requested_notional,
                    current_exposure=current_exposure,
                    max_exposure=max_symbol_exposure
                )
        
        # 5-3. BLOCK: 완전 차단
        logger.error(
            f"❌ {symbol} Exposure BLOCK: "
            f"현재=${current_exposure:.2f} ≥ 한도=${max_symbol_exposure:.2f}"
        )
        return ExposureDecision(
            decision="BLOCK",
            adjusted_notional=0.0,
            reason=f"Per-symbol exposure already at limit (${current_exposure:.2f} ≥ ${max_symbol_exposure:.2f})",
            original_notional=requested_notional,
            current_exposure=current_exposure,
            max_exposure=max_symbol_exposure
        )
    
    def update_consecutive_losses(self, pnl: float):
        """PnL에 따른 연속 손실 추적 (쿨다운 관리)"""
        # ⭐ TUNING_VIBLE: 연속 손실 추적 (프로파일에 따라 ON/OFF)
        if self.max_consecutive_losses is not None:
            if pnl < 0:
                self.consecutive_losses += 1
                logger.info(f"📊 연속 손실: {self.consecutive_losses}/{self.max_consecutive_losses}회")
                
                # 연속 손실 한도 도달 → 쿨다운 시작
                if self.consecutive_losses >= self.max_consecutive_losses and self.cooldown_minutes > 0:
                    self.in_cooldown = True
                    self.cooldown_start_time = time.time()
                    logger.warning(f"🛑 연속 손실 {self.consecutive_losses}회 도달 → 쿨다운 시작 ({self.cooldown_minutes}분)")
                    self._notify_guard(f"Consecutive loss cooldown started: {self.consecutive_losses} losses, {self.cooldown_minutes}m")
            else:
                # 승리 시 연속 손실 리셋
                if self.consecutive_losses > 0:
                    logger.info(f"✅ 연속 손실 리셋 ({self.consecutive_losses}회 → 0회)")
                self.consecutive_losses = 0
                self.in_cooldown = False
    
    def add_position(self, symbol: str, position_value: float):
        """포지션 추가"""
        self.active_positions_count += 1
        self.symbol_exposures[symbol] = self.symbol_exposures.get(symbol, 0.0) + position_value
        logger.info(f"➕ 포지션 추가: {symbol}, 총 {self.active_positions_count}개")
    
    def remove_position(self, symbol: str, position_value: float):
        """포지션 제거"""
        self.active_positions_count = max(0, self.active_positions_count - 1)
        if symbol in self.symbol_exposures:
            self.symbol_exposures[symbol] = max(0.0, self.symbol_exposures[symbol] - position_value)
        logger.info(f"➖ 포지션 제거: {symbol}, 남은 {self.active_positions_count}개")
    
    def reset_consecutive_losses(self):
        """연속 손실 리셋 (PR12: daily PnL은 portfolio로 이동)"""
        self.consecutive_losses = 0
        self.in_cooldown = False
        logger.info("📅 RiskManager 연속 손실 리셋")
    
    def check_daily_loss_limit(self) -> bool:
        """
        일일 손실 한도 (포트폴리오에서 PnL 가져옴)
        
        Returns:
            bool: True=허용, False=차단
        """
        # 포트폴리오에서 daily_pnl 가져오기
        if self.portfolio is None or self.daily_loss_limit is None:
            return True
            
        daily_pnl = self.portfolio.get_daily_pnl()
        
        if self.daily_loss_limit and daily_pnl < -self.daily_loss_limit:
            logger.error(f"🚨 일일 손실 한도: ${daily_pnl:,.2f} < -${self.daily_loss_limit:,.2f}")
            self._notify_guard(f"Daily loss limit: {daily_pnl:,.2f} < -{self.daily_loss_limit:,.2f}")
            return False
            
        return True
    
    def reset_cooldown(self):
        """쿨다운 수동 리셋 (관리자 개입용)"""
        self.consecutive_losses = 0
        self.in_cooldown = False
        logger.warning("🔓 연속 손실 쿨다운 수동 리셋")
    
    def check_drawdown_guard(self, current_equity: float) -> bool:
        """
        ⭐ PR11: 최대 낙폭 가드 체크
        
        Args:
            current_equity: 현재 자본
            
        Returns:
            bool: True=허용, False=차단
        """
        # ⭐ PR12: 포트폴리오에서 initial_equity 가져오기
        initial_equity = self.portfolio.initial_equity if self.portfolio else self.initial_equity
        
        # 최고점 업데이트
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.current_drawdown = 0.0
        else:
            # 현재 낙폭 계산
            self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        # 최대 낙폭 초과 시 차단
        if self.current_drawdown > self.max_drawdown_pct:
            logger.error(f"🚨 최대 낙폭 초과: {self.current_drawdown*100:.2f}% > {self.max_drawdown_pct*100:.1f}%")
            self._notify_guard(f"Drawdown guard triggered: {self.current_drawdown*100:.2f}% > {self.max_drawdown_pct*100:.1f}%")
            return False
        
        return True
    
    def check_slippage_guard(self, expected_price: float, market_price: float) -> bool:
        """
        ⭐ PR11: 슬리피지 가드 체크
        
        Args:
            expected_price: 예상 체결 가격
            market_price: 현재 시장 가격
            
        Returns:
            bool: True=허용, False=차단
        """
        if expected_price <= 0 or market_price <= 0:
            return True  # 가격이 유효하지 않으면 통과
        
        # 슬리피지 계산
        slippage = abs(market_price - expected_price) / expected_price
        
        # 슬리피지 한도 초과 시 차단
        if slippage > self.max_slippage_pct:
            logger.error(f"🚨 슬리피지 초과: {slippage*100:.2f}% > {self.max_slippage_pct*100:.2f}%")
            self._notify_guard(f"Slippage guard triggered: {slippage*100:.2f}% > {self.max_slippage_pct*100:.2f}%")
            return False
        
        return True
    
    def check_extreme_loss_guard(self, position_pnl_pct: float) -> bool:
        """
        ⭐ PR11: 극단 손실 가드 체크 (PR10 연계, 중복 방지)
        
        Note: PR10 position_tracker.py L198-207에서 -50% cutoff 이미 구현됨
              여기서는 더 보수적인 -30% 임계값으로 조기 경고
        
        Args:
            position_pnl_pct: 포지션 PNL 퍼센트 (-0.3 = -30%)
            
        Returns:
            bool: True=허용, False=차단
        """
        # 극단 손실 임계값 초과 시 차단 (PR10보다 보수적)
        if position_pnl_pct < self.extreme_loss_cutoff_pct:
            logger.error(f"🚨 극단 손실 가드: {position_pnl_pct*100:.1f}% < {self.extreme_loss_cutoff_pct*100:.1f}% (PR10 -50% 이전 조기 차단)")
            self._notify_guard(f"Extreme loss guard triggered: {position_pnl_pct*100:.1f}% < {self.extreme_loss_cutoff_pct*100:.1f}%")
            return False
        
        return True

    def update_equity(self, new_equity: float):
        """
        자본 업데이트 + 한도 재계산 - 복리 효과
        
        Args:
            new_equity: 새로운 자본 (거래 후)
        """
        old_equity = self.equity
        self.equity = max(0.0, new_equity)  # 음수 방지
        
        # 일일 손실 한도 재계산 (한도가 있을 때만)
        if self.daily_loss_limit_pct is not None:
            old_limit = self.daily_loss_limit
            self.daily_loss_limit = self.daily_loss_limit_pct * self.equity
            
            if abs(self.equity - old_equity) > 0.01:  # 유의미한 변화만 로그
                change_pct = ((self.equity - old_equity) / old_equity * 100) if old_equity > 0 else 0
                logger.info(f"💰 Equity 업데이트: ${old_equity:,.2f} → ${self.equity:,.2f} ({change_pct:+.2f}%), DDL: ${old_limit:.2f} → ${self.daily_loss_limit:.2f}")
        else:
            if abs(self.equity - old_equity) > 0.01:
                change_pct = ((self.equity - old_equity) / old_equity * 100) if old_equity > 0 else 0
                logger.info(f"💰 Equity 업데이트: ${old_equity:,.2f} → ${self.equity:,.2f} ({change_pct:+.2f}%)")
