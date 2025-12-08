#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Sizer - 포지션 크기 동적 계산
======================================

업계 표준 구현:
1. 리스크-퍼-트레이드 (RPT)
2. 신호 품질 가중치 (confidence, experience)
3. 컨텍스트 스케일링 (regime, volatility)
4. 포트폴리오 제약 (caps)
5. 안전 장치 (brakes)

⭐ PHASE17 추가 기능:
6. Multi-position Scaling (동시 포지션 수에 따른 크기 조정)
7. Exposure Guard 통합 (3단계 의사결정: ALLOW/ALLOW_REDUCED/BLOCK)
8. 심볼별 노출도 한계 내에서 최대한 거래 가능하도록 조정
"""
import os
from typing import Tuple, Dict

from common.logger import setup_logger
from common.calculations import position_size

logger = setup_logger(__name__, log_type="trading")


class PositionSizer:
    """
    포지션 크기 동적 계산 + 청산가 검증 (TUNING_VIBLE P0)
    (업계 표준: Risk-per-trade + Quality weighting + Liquidation safety)
    """
    
    def __init__(self, config: dict, activity_tracker=None):
        """
        Args:
            config: config.yml 전체 설정
            activity_tracker: TradeActivityTracker instance (PHASE28-10, optional)
        """
        # ⭐ PHASE28-10: Activity Tracker (Guard Telemetry)
        self.activity_tracker = activity_tracker
        
        # 기본 설정 (config.yml에서)
        self.config = config
        self.equity = config['capital']['initial']
        self.risk_per_trade = config['risk']['per_trade']
        
        # 품질 가중치 범위
        self.quality_weight_min = config['position_sizing']['quality_weight_min']
        self.quality_weight_max = config['position_sizing']['quality_weight_max']
        
        # 포지션 한도
        self.max_position_value = config['position_sizing']['max_position_value']
        self.min_position_value = config['position_sizing']['min_position_value']
        
        # ⭐ TUNING_VIBLE P0: 청산가 검증 설정
        risk = config.get('risk', {})
        self.liq_buffer_multiple = risk.get('liq_buffer_multiple_of_SL', 4)
        self.leverage_cap = risk.get('leverage_cap', 5)
        
        leverage = config.get('leverage', {})
        self.max_leverage = min(leverage.get('max', 10), self.leverage_cap)

        # 컨텍스트 스케일링 설정 (옵션)
        ps_cfg = config.get('position_sizing', {}) or {}
        cs = ps_cfg.get('context_scaling', {}) or {}
        # 활성화 여부 및 파라미터(기본 비활성)
        self.cs_enabled = bool(cs.get('enabled', True))
        self.cs_low_atr = float(cs.get('atr_low_pct', 0.004))   # 0.4%
        self.cs_high_atr = float(cs.get('atr_high_pct', 0.02))  # 2.0%
        self.cs_low_mult = float(cs.get('low_vol_mult', 1.2))   # 저변동: 리스크 상향
        self.cs_high_mult = float(cs.get('high_vol_mult', 0.7)) # 고변동: 리스크 하향
        self.cs_neutral_mult = float(cs.get('neutral_mult', 1.0))
        
        # ⭐ PHASE17: Multi-position Scaling 설정
        self.multi_position_scaling_enabled = ps_cfg.get('multi_position_scaling', True)
        self.exposure_reduction_factor = ps_cfg.get('exposure_reduction_factor', 0.95)  # 95% 안전 마진
        self.allow_partial_entry = ps_cfg.get('allow_partial_entry', True)
        
        logger.info(f"✅ PositionSizer 초기화: Equity={self.equity}, RPT={self.risk_per_trade}, Liq Buffer={self.liq_buffer_multiple}×SL")
        logger.info(f"   PHASE17: Multi-pos Scaling={self.multi_position_scaling_enabled}, Allow Partial={self.allow_partial_entry}")
    
    def calculate(self, signal: Dict, available_budget: float = None) -> Tuple[float, Dict]:
        """
        포지션 크기 계산 (⭐ common.calculations 활용)
        
        Args:
            signal: {
                'entry_price': float,
                'sl_price': float,
                'confidence': float (0~1, 선택),
                'atr': float (선택),
                'symbol': str
            }
            available_budget: ⭐ PHASE17: 사용 가능한 예산 (USDT). None이면 무제한.
        
        Returns:
            (qty, metadata)
        """
        entry = signal['entry_price']
        sl = signal['sl_price']
        
        # 1) 컨텍스트 스케일링에 따른 유효 RPT 계산
        eff_rpt = float(self.risk_per_trade)
        if self.cs_enabled:
            atr_val = float(signal.get('atr', 0.0))
            entry = float(signal.get('entry_price', 0.0)) or entry
            atr_pct = (atr_val / entry) if entry > 0 else 0.0
            # 구간형 스케일링 (선형 보간)
            if atr_pct <= self.cs_low_atr:
                mult = self.cs_low_mult
            elif atr_pct >= self.cs_high_atr:
                mult = self.cs_high_mult
            else:
                # low→neutral→high 사이 선형 보간 두 구간으로 나눔
                mid = (self.cs_low_atr + self.cs_high_atr) / 2.0
                if atr_pct <= mid:
                    # low -> neutral
                    t = (atr_pct - self.cs_low_atr) / max(1e-9, (mid - self.cs_low_atr))
                    mult = self.cs_low_mult + (self.cs_neutral_mult - self.cs_low_mult) * t
                else:
                    # neutral -> high
                    t = (atr_pct - mid) / max(1e-9, (self.cs_high_atr - mid))
                    mult = self.cs_neutral_mult + (self.cs_high_mult - self.cs_neutral_mult) * t
            eff_rpt = max(0.0001, min(0.05, eff_rpt * mult))

        # 2) 기본 리스크 기반 계산 (⭐ 공통 함수 사용)
        base_qty, risk_usdt = position_size(
            entry=entry,
            sl=sl,
            equity=self.equity,
            risk_frac=eff_rpt
        )
        
        if base_qty <= 0:
            return 0.0, {"reason": "invalid_stop"}
        
        # 3) 품질 가중치 적용 (confidence 있으면)
        quality_weight = self._calculate_quality_weight(signal)
        adjusted_qty = base_qty * quality_weight
        
        # 4) 포지션 가치 한도 적용 (⭐ 강화)
        position_value = adjusted_qty * entry
        
        # ⭐ max_position_value 한도 먼저 체크
        if position_value > self.max_position_value:
            adjusted_qty = self.max_position_value / entry
            position_value = adjusted_qty * entry  # 재계산
        
        # ⭐ PHASE17: available_budget 한도 적용 (Budget Cap)
        budget_capped = False
        
        # DEBUG: Budget Cap 조건 상세 로그
        logger.info(
            f"🔍 [Budget Check] available_budget={available_budget}, "
            f"position_value=${position_value:.2f}, "
            f"will_cap={available_budget is not None and position_value > available_budget}"
        )
        
        if available_budget is not None and position_value > available_budget:
            logger.info(
                f"📉 [Budget Cap] Position capped by available budget: "
                f"${position_value:.2f} → ${available_budget:.2f}"
            )
            adjusted_qty = available_budget / entry
            position_value = available_budget
            budget_capped = True
        
        # min_position_value 체크
        if position_value < self.min_position_value:
            # ⭐ PHASE28-10: Guard Telemetry
            symbol = signal.get('symbol', 'UNKNOWN')
            if self.activity_tracker:
                self.activity_tracker.record_guard_block(symbol, "GUARD_MIN_NOTIONAL")
            return 0.0, {"reason": "below_min_value"}
        
        # 5) 거래소 최소 수량
        final_qty = float(round(adjusted_qty, 3))  # float 변환
        if final_qty < 0.001:
            return 0.0, {"reason": "below_min_qty"}
        
        # ⭐ 최종 포지션 가치 재확인 (반올림 후)
        final_position_value = final_qty * entry
        # ⭐ PR10 Bug Fix #3: 부동소수점 안전 비교 (epsilon 완화)
        # 실제 반올림 오차는 0.01~0.5 범위이므로 1.0 USDT 허용
        epsilon = 1.0
        if final_position_value > self.max_position_value + epsilon:
            # 한도 내로 다시 조정
            logger.warning(f"⚠️ 포지션 가치 초과: ${final_position_value:.2f} > ${self.max_position_value:.2f}, 조정 중...")
            final_qty = float(round(self.max_position_value / entry, 3))
            final_position_value = final_qty * entry
            logger.info(f"✅ 조정 완료: qty={final_qty}, value=${final_position_value:.2f}")
        
        metadata = {
            "risk_usdt": float(risk_usdt),
            "stop_distance": float(abs(entry - sl)),
            "quality_weight": float(quality_weight),
            "base_qty": float(base_qty),
            "final_qty": final_qty,
            "position_value": float(final_position_value),
            "available_budget": float(available_budget) if available_budget is not None else None,
            "budget_capped": budget_capped
        }
        
        logger.debug(f"📊 Position Size: qty={final_qty}, value=${final_position_value:.2f}, max=${self.max_position_value:.2f}")
        
        return final_qty, metadata
    
    def _calculate_quality_weight(self, signal: Dict) -> float:
        """
        신호 품질 기반 가중치 (⭐ PR8 Phase2: 다차원 개선)
        
        고려 요소:
        1. 신호 신뢰도 (confidence)
        2. 전략 성과 (strategy_metrics: sharpe, winrate, trades)
        3. 현재 DD (current_dd)
        """
        confidence = signal.get('confidence', 0.8)  # 기본값 0.8
        
        # 1. 기본 가중치 (신뢰도)
        base_weight = self.quality_weight_min + (confidence - 0.5) * 1.2
        
        # 2. 전략 성과 배수 (선택)
        perf_mult = 1.0
        strategy_metrics = signal.get('strategy_metrics')
        if strategy_metrics:
            sharpe = strategy_metrics.get('sharpe', 0)
            winrate = strategy_metrics.get('winrate', 0.5)
            trades = strategy_metrics.get('trades', 0)
            
            # Sharpe 배수 (0~1.5 → 0.85~1.15)
            if sharpe > 0:
                sharpe_mult = 0.85 + min(1.5, sharpe) * 0.2
            else:
                sharpe_mult = 0.85
            
            # Winrate 배수 (40~70% → 0.9~1.1)
            if 0.4 <= winrate <= 0.7:
                wr_mult = 0.9 + (winrate - 0.4) * (0.2 / 0.3)
            elif winrate > 0.7:
                wr_mult = 1.1
            else:
                wr_mult = 0.9
            
            # 샘플 신뢰도 (거래 수)
            if trades >= 100:
                sample_mult = 1.0
            elif trades >= 30:
                sample_mult = 0.9 + (trades - 30) * 0.1 / 70
            else:
                sample_mult = 0.85
            
            perf_mult = (sharpe_mult + wr_mult) / 2 * sample_mult
        
        # 3. Drawdown 페널티 (선택)
        dd_mult = 1.0
        current_dd = signal.get('current_dd', 0)
        if current_dd > 0:
            # DD 5% → 0.95x, 10% → 0.85x
            dd_mult = max(0.7, 1.0 - current_dd * 0.01)
        
        # 최종 가중치
        weight = base_weight * perf_mult * dd_mult
        
        # 범위 제한
        return max(self.quality_weight_min, min(weight, self.quality_weight_max))
    
    # =========================================================================
    # ⭐ TUNING_VIBLE P0: 청산가 검증 (liquidation_checker 통합)
    # =========================================================================
    
    def calculate_liquidation_price(self, entry: float, side: str, 
                                   leverage: float, margin_ratio: float = None) -> float:
        """
        청산가 계산 (격리 마진 모드)
        
        Args:
            entry: 진입가
            side: LONG/SHORT
            leverage: 레버리지
            margin_ratio: 유지 증거금 비율 (None이면 config에서 읽기)
        
        Returns:
            청산가
        """
        # ⭐ margin_ratio config에서 읽기
        if margin_ratio is None:
            margin_ratio = self.config.get('risk', {}).get('margin_ratio', 0.01)
        if side == 'LONG':
            # LONG: Liq = Entry × (1 - 1/Leverage + margin_ratio)
            liq = entry * (1 - 1/leverage + margin_ratio)
        else:
            # SHORT: Liq = Entry × (1 + 1/Leverage - margin_ratio)
            liq = entry * (1 + 1/leverage - margin_ratio)
        
        return liq
    
    def verify_liquidation_buffer(self, entry: float, stop: float, side: str,
                                 leverage: float) -> Tuple[bool, float, str]:
        """
        청산가 여유 검증
        
        Args:
            entry: 진입가
            stop: 손절가
            side: LONG/SHORT
            leverage: 레버리지
        
        Returns:
            (통과 여부, 실제 배수, 메시지)
        """
        # 1R (SL 거리)
        if side == 'LONG':
            one_r = abs(entry - stop)
        else:
            one_r = abs(stop - entry)
        
        # 청산가 계산
        liq = self.calculate_liquidation_price(entry, side, leverage)
        
        # 청산가 여유 계산
        if side == 'LONG':
            liq_buffer = abs(entry - liq)
        else:
            liq_buffer = abs(liq - entry)
        
        # 실제 배수
        actual_multiple = liq_buffer / one_r if one_r > 0 else 0
        
        # 검증
        passed = actual_multiple >= self.liq_buffer_multiple
        
        if passed:
            msg = f"✅ 청산가 여유 충분: {actual_multiple:.2f}×SL (목표 {self.liq_buffer_multiple}×)"
        else:
            msg = f"❌ 청산가 여유 부족: {actual_multiple:.2f}×SL (목표 {self.liq_buffer_multiple}×)"
        
        return passed, actual_multiple, msg
    
    def suggest_max_leverage(self, entry: float, stop: float, side: str,
                            atr_pct: float = None,
                            strategy_metrics: dict = None,
                            signal_confidence: float = None,
                            current_dd: float = 0.0) -> float:
        """
        적정 레버리지 제안 (⭐ PR8: 중복 제거, calculations 모듈 활용)
        
        프로세스:
        1. common.calculations.leverage_suggestion() 호출 (다차원 분석)
        2. 청산가 안전성 검증
        3. 둘 중 안전한 값 반환
        
        Args:
            entry: 진입가
            stop: 손절가
            side: LONG/SHORT
            atr_pct: ATR % (선택, 다차원 계산용)
            strategy_metrics: 전략 성과 (선택)
            signal_confidence: 신호 신뢰도 (선택)
            current_dd: 현재 DD (선택)
        
        Returns:
            안전한 레버리지
        """
        from common.calculations import leverage_suggestion
        
        # 1. 다차원 레버리지 제안
        if atr_pct is not None:
            suggested_lev = leverage_suggestion(
                atr_pct=atr_pct,
                min_leverage=self.config.get('leverage', {}).get('min', 2),
                max_leverage=self.config.get('leverage', {}).get('max', 50),
                strategy_metrics=strategy_metrics,
                signal_confidence=signal_confidence,
                current_dd=current_dd
            )
        else:
            # ATR 없으면 기본값
            suggested_lev = self.config.get('leverage', {}).get('default', 2)
        
        # 2. 청산가 안전성 검증 (이진 탐색)
        safe_lev = self._find_safe_leverage(entry, stop, side, suggested_lev)
        
        # 3. 둘 중 작은 값 (안전한 값)
        final_lev = min(suggested_lev, safe_lev, self.max_leverage)
        
        logger.debug(f"💡 레버리지 제안: suggested={suggested_lev}, safe={safe_lev}, final={final_lev}")
        
        return final_lev
    
    def _find_safe_leverage(self, entry: float, stop: float, side: str, max_lev: float) -> float:
        """
        청산가 안전성 검증 (이진 탐색)
        
        Args:
            entry, stop, side: 포지션 정보
            max_lev: 최대 레버리지 (다차원 계산 결과)
        
        Returns:
            안전한 레버리지
        """
        target_multiple = self.liq_buffer_multiple  # 청산가 버퍼 (4× SL)
        
        low, high = 1.0, float(max_lev)
        best_lev = 1.0
        
        for _ in range(20):
            mid = (low + high) / 2.0
            
            passed, actual_mult, _ = self.verify_liquidation_buffer(
                entry, stop, side, mid
            )
            
            if passed:
                best_lev = mid
                low = mid
            else:
                high = mid
            
            if abs(actual_mult - target_multiple) < 0.1:
                break
        
        return best_lev
    
    # =========================================================================
    # ⭐ PHASE17: Multi-position Scaling + Exposure Guard 통합
    # =========================================================================
    
    def apply_multi_position_scaling(
        self, 
        base_risk: float, 
        num_open_positions: int, 
        max_positions: int
    ) -> float:
        """
        동시 포지션 수에 따른 리스크 크기 조정
        
        공식: scaling_factor = 1.0 / (1 + num_open / max_positions)
        
        예시:
        - max_positions=2, num_open=0 → scaling=1.0 (100%)
        - max_positions=2, num_open=1 → scaling=0.667 (67%)
        - max_positions=2, num_open=2 → scaling=0.5 (50%)
        
        Args:
            base_risk: 기본 리스크 금액 (USDT)
            num_open_positions: 현재 열린 포지션 수
            max_positions: 최대 포지션 수
        
        Returns:
            scaled_risk: 조정된 리스크 금액
        """
        if not self.multi_position_scaling_enabled:
            return base_risk
        
        if max_positions <= 0:
            # max_positions=0은 무제한 의미 → 스케일링 안 함
            return base_risk
        
        # 스케일링 공식
        scaling_factor = 1.0 / (1.0 + num_open_positions / max_positions)
        scaled_risk = base_risk * scaling_factor
        
        logger.debug(
            f"📊 Multi-position Scaling: base=${base_risk:.2f}, "
            f"open={num_open_positions}/{max_positions}, "
            f"factor={scaling_factor:.3f}, "
            f"scaled=${scaled_risk:.2f}"
        )
        
        return scaled_risk
    
    def calculate_with_exposure_check(
        self,
        signal: Dict,
        current_symbol_exposure: float,
        max_symbol_exposure: float,
        num_open_positions: int = 0
    ) -> Tuple[float, Dict, str]:
        """
        ⭐ PHASE17: 포지션 크기 계산 + Exposure Guard 통합
        
        프로세스:
        1. 기본 포지션 크기 계산 (calculate 메서드 재사용)
        2. Multi-position scaling 적용
        3. Per-symbol Exposure 체크
           - ALLOW: 정상 진입
           - ALLOW_REDUCED: 사이즈 축소 후 진입
           - BLOCK: 완전 차단
        
        Args:
            signal: 신호 dict (entry_price, sl_price, symbol 등)
            current_symbol_exposure: 현재 심볼 노출도 (USDT)
            max_symbol_exposure: 최대 심볼 노출도 (USDT)
            num_open_positions: 현재 열린 포지션 수
        
        Returns:
            (qty, metadata, action)
            - qty: 최종 수량 (0이면 거부)
            - metadata: 계산 상세 정보
            - action: "ALLOW" | "ALLOW_REDUCED" | "BLOCK"
        """
        symbol = signal.get('symbol', 'UNKNOWN')
        entry_price = signal['entry_price']
        
        # 1. 기본 포지션 크기 계산
        base_qty, base_metadata = self.calculate(signal)
        
        if base_qty <= 0:
            return 0.0, base_metadata, "BLOCK"
        
        # 2. Multi-position Scaling 적용
        max_positions = self.config['risk']['max_positions']
        base_risk = base_metadata.get('risk_usdt', 0)
        
        if self.multi_position_scaling_enabled and max_positions > 0:
            scaled_risk = self.apply_multi_position_scaling(
                base_risk, 
                num_open_positions, 
                max_positions
            )
            # 리스크 조정 비율을 수량에 반영
            risk_ratio = scaled_risk / base_risk if base_risk > 0 else 1.0
            scaled_qty = base_qty * risk_ratio
        else:
            scaled_qty = base_qty
            scaled_risk = base_risk
        
        # 3. Per-symbol Exposure 체크
        position_value = scaled_qty * entry_price
        total_exposure = current_symbol_exposure + position_value
        
        # 디버깅 로그
        logger.debug(f"💰 Exposure 체크: {symbol}")
        logger.debug(f"   현재 노출: ${current_symbol_exposure:.2f}")
        logger.debug(f"   신규 포지션: ${position_value:.2f}")
        logger.debug(f"   합계: ${total_exposure:.2f}")
        logger.debug(f"   한도: ${max_symbol_exposure:.2f}")
        
        # 3-1. ALLOW: 정상 진입
        if total_exposure <= max_symbol_exposure:
            metadata = {
                **base_metadata,
                'scaled_qty': float(scaled_qty),
                'position_value': float(position_value),
                'multi_position_scaling': self.multi_position_scaling_enabled,
                'num_open_positions': num_open_positions
            }
            return float(scaled_qty), metadata, "ALLOW"
        
        # 3-2. ALLOW_REDUCED: 사이즈 축소 후 진입
        if self.allow_partial_entry and current_symbol_exposure < max_symbol_exposure:
            available_exposure = max_symbol_exposure - current_symbol_exposure
            # 안전 마진 적용 (기본 95%)
            adjusted_exposure = available_exposure * self.exposure_reduction_factor
            
            # 최소 포지션 크기 체크
            if adjusted_exposure >= self.min_position_value:
                adjusted_qty = adjusted_exposure / entry_price
                adjusted_qty = float(round(adjusted_qty, 3))
                
                # 거래소 최소 수량 체크
                if adjusted_qty >= 0.001:
                    metadata = {
                        **base_metadata,
                        'scaled_qty': float(scaled_qty),
                        'adjusted_qty': adjusted_qty,
                        'position_value': float(adjusted_exposure),
                        'reduction_reason': 'exposure_limit',
                        'original_exposure': float(position_value),
                        'adjusted_exposure': float(adjusted_exposure),
                        'multi_position_scaling': self.multi_position_scaling_enabled,
                        'num_open_positions': num_open_positions
                    }
                    
                    logger.warning(
                        f"⚠️  {symbol} 사이즈 축소: "
                        f"${position_value:.2f} → ${adjusted_exposure:.2f} "
                        f"(노출 한도: ${max_symbol_exposure:.2f})"
                    )
                    
                    return adjusted_qty, metadata, "ALLOW_REDUCED"
        
        # 3-3. BLOCK: 완전 차단
        metadata = {
            **base_metadata,
            'block_reason': 'exposure_limit_exceeded',
            'current_exposure': float(current_symbol_exposure),
            'max_exposure': float(max_symbol_exposure),
            'requested_exposure': float(position_value)
        }
        
        logger.error(
            f"❌ {symbol} Entry 차단: "
            f"현재=${current_symbol_exposure:.2f}, "
            f"요청=${position_value:.2f}, "
            f"한도=${max_symbol_exposure:.2f}"
        )
        
        return 0.0, metadata, "BLOCK"
    
    def update_equity(self, new_equity: float):
        """
        자본 업데이트 (PnL 반영) - 복리 효과
        
        Args:
            new_equity: 새로운 자본 (거래 후)
        """
        old_equity = self.equity
        self.equity = max(0.0, new_equity)  # 음수 방지
        
        if abs(self.equity - old_equity) > 0.01:  # 유의미한 변화만 로그
            change_pct = ((self.equity - old_equity) / old_equity * 100) if old_equity > 0 else 0
            logger.info(f"💰 Equity 업데이트: ${old_equity:,.2f} → ${self.equity:,.2f} ({change_pct:+.2f}%)")
