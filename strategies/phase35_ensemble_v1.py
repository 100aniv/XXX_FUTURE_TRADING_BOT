#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35 Ensemble Strategy V1 - Moderate Hybrid
===============================================
STATUS: PHASE35-1 IMPLEMENTATION

Design: Multi-Module Ensemble with Regime Filter
- 3 Sub-Models: Trend-Following, Mean-Reversion, Breakout
- Ensemble Method: 2-out-of-3 Majority Vote
- Regime Filter: ATR-based (TREND/RANGE/CHOP)
- Exit Logic: Time-based + Adverse Move

Design Document: docs/PHASE35/PHASE35_STRATEGY_ARCHITECTURE.md
Reuse Map: docs/PHASE35/PHASE35_1_REUSE_MAP.md

Key Principles:
1. Infrastructure Reuse: 기존 engine/portfolio/risk 100% 재사용
2. Config-Driven: 모든 파라미터는 config에서 관리 (하드코딩 금지)
3. DecisionTrace: 진입/차단 사유를 구조화하여 기록
4. Quality over Frequency: PHASE34 교훈 - 빈도가 아닌 품질 개선 목표
"""
from typing import Dict, Any, List
import pandas as pd
import logging

from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)


class Phase35EnsembleV1(BaseStrategy):
    """
    PHASE35 Ensemble Strategy V1

    Multi-Module Ensemble:
    - Sub-Model 1: Trend-Following (EMA Cross + ADX)
    - Sub-Model 2: Mean-Reversion (RSI + Bollinger Bands)
    - Sub-Model 3: Breakout (ATR + Volume)

    Ensemble: 2-out-of-3 Majority Vote
    Regime Filter: ATR-based (TREND/RANGE/CHOP)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # decision_trace can be bool or dict
        dt = config.get("decision_trace", False)
        self._diag_enabled = dt if isinstance(dt, bool) else dt.get("enabled", False)
        self._diag_counters = {}
        self._total_signals_checked = 0
        self._last_signal_bar_index = -999

        ensemble_cfg = self._get_cfg(
            [
                "ensemble",
                "strategy.ensemble",
                "strategies.phase35_ensemble_v1.params.ensemble",
            ],
            {},
        )
        self._cooldown_bars = ensemble_cfg.get("cooldown_bars", 0)
        self._min_votes = ensemble_cfg.get("min_votes", 2)
        self._confidence_threshold = ensemble_cfg.get("confidence_threshold", 0.5)

        # ITER17: effective params 소스 추적
        self._effective_params_source = self._resolve_config_source()
        
        # ITER21: sub_models config SSOT - 멀티패스 리졸브
        self._sub_models_cfg = self._resolve_sub_models_cfg()
        self._sub_models_source = self._resolve_sub_models_source()
        
        if self._diag_enabled and config.get("mode") == "backtest":
            logger.info(
                f"ITER17 CONFIG: cooldown={self._cooldown_bars}, min_votes={self._min_votes}, threshold={self._confidence_threshold}, source={self._effective_params_source}"
            )
            # ITER21: sub_models resolved 값 로깅
            logger.info(
                f"ITER21 SUB_MODELS: source={self._sub_models_source}, "
                f"trend.adx={self._sub_models_cfg.get('trend', {}).get('adx_threshold', 'N/A')}, "
                f"reversion.rsi_oversold={self._sub_models_cfg.get('reversion', {}).get('rsi_oversold', 'N/A')}"
            )

    def _resolve_sub_models_cfg(self) -> Dict[str, Any]:
        """
        ITER21 SSOT: sub_models config 멀티패스 리졸브
        
        우선순위:
        1. config["sub_models"]
        2. config["strategy"]["sub_models"]
        3. config["strategies"][<selector>]["params"]["sub_models"]
        4. config["strategy_params"]["sub_models"]
        5. {} (기본값)
        """
        path_variants = [
            "sub_models",
            "strategy.sub_models",
            "strategies.phase35_ensemble_v1.params.sub_models",
            "strategy_params.sub_models",
        ]
        return self._get_cfg(path_variants, {})
    
    def _resolve_sub_models_source(self) -> str:
        """ITER21: sub_models config가 어느 경로에서 왔는지 추적"""
        path_variants = [
            "sub_models",
            "strategy.sub_models",
            "strategies.phase35_ensemble_v1.params.sub_models",
            "strategy_params.sub_models",
        ]
        for path in path_variants:
            parts = path.split(".")
            value = self.config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is not None and isinstance(value, dict):
                return path
        return "defaults"

    def _resolve_config_source(self) -> str:
        """Config가 어느 경로에서 왔는지 추적 (ITER17 SSOT)"""
        path_variants = [
            "ensemble",
            "strategy.ensemble",
            "strategies.phase35_ensemble_v1.params.ensemble",
        ]
        for path in path_variants:
            parts = path.split(".")
            value = self.config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is not None and isinstance(value, dict):
                if "min_votes" in value or "confidence_threshold" in value or "cooldown_bars" in value:
                    return path
        return "defaults"

    def get_effective_params(self) -> Dict[str, Any]:
        """
        ITER17 SSOT: 실제 사용되는 ensemble params 반환
        
        Returns:
            {
                'min_votes': int,
                'confidence_threshold': float,
                'cooldown_bars': int,
                'source': str,  # 'ensemble' | 'strategy.ensemble' | 'strategies.phase35_ensemble_v1.params.ensemble' | 'defaults'
            }
        """
        return {
            "min_votes": self._min_votes,
            "confidence_threshold": self._confidence_threshold,
            "cooldown_bars": self._cooldown_bars,
            "source": self._effective_params_source,
            # ITER21: sub_models resolved 값 포함
            "sub_models": self._sub_models_cfg,
            "sub_models_source": self._sub_models_source,
        }

    def _get_cfg(self, path_variants: List[str], default: Any) -> Any:
        for path in path_variants:
            parts = path.split(".")
            value = self.config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            if value is not None:
                return value
        return default

    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name="phase35_ensemble_v1",
            strategy_type="ensemble",
            supported_symbols=["BTCUSDT"],
            supported_timeframes=["15m"],
            version="1.0.0",
            description="PHASE35 Ensemble V1: 3 Sub-Models + 2/3 Vote + ATR Regime",
        )

    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Compute ensemble signal

        Args:
            df: 15m OHLCV + indicators

        Returns:
            dict: {
                'side': 'LONG' | 'SHORT' | None,
                'reason': str,
                'entry': float,
                'sl': float,
                'tp': float,
                'confidence': float (0~1),
                'sub_model_votes': dict,
                'regime': str
            }
        """
        if self._diag_enabled:
            self._total_signals_checked += 1

        try:
            # 1. Regime Detection
            regime_info = self._detect_regime(df)
            regime = regime_info["regime"]

            # DecisionTrace: 레짐 차단
            if regime == "CHOP":
                if self._diag_enabled:
                    self._diag_inc("REGIME_CHOP_BLOCK")
                return {
                    "side": None,
                    "reason": "regime_chop",
                    "regime": regime,
                    "regime_info": regime_info,
                }

            # 2. Sub-Model Voting
            sub_votes = self._get_sub_model_votes(df, regime)

            # 3. Ensemble Decision (2-out-of-3 Majority Vote)
            ensemble_decision = self._ensemble_vote(sub_votes)

            # 4. Final Signal Generation
            if ensemble_decision["direction"] is None:
                if self._diag_enabled:
                    reason = ensemble_decision.get("reason", "no_consensus")
                    self._diag_inc(f"ENSEMBLE_{reason.upper()}")

                return {
                    "side": None,
                    "reason": ensemble_decision["reason"],
                    "sub_model_votes": sub_votes,
                    "regime": regime,
                    "regime_info": regime_info,
                }

            # 5. Entry/SL/TP 계산
            signal = self._calculate_entry_exit(
                df=df,
                direction=ensemble_decision["direction"],
                confidence=ensemble_decision["confidence"],
                regime=regime,
            )

            signal.update(
                {
                    "sub_model_votes": sub_votes,
                    "regime": regime,
                    "regime_info": regime_info,
                    "ensemble_confidence": ensemble_decision["confidence"],
                }
            )

            return signal

        except Exception as e:
            logger.exception(
                f"❌ [phase35_ensemble_v1] Signal computation exception: {e}"
            )
            if self._diag_enabled:
                self._diag_inc(f"EXCEPTION_{type(e).__name__}")
            return {"side": None, "reason": f"exception_{type(e).__name__}"}

    def _detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ATR-based Regime Detection (간이 버전)

        Regimes:
        - TREND: ATR% >= trend_min (강한 추세)
        - RANGE: ATR% <= range_max (횡보)
        - CHOP: 그 외 (노이즈, 진입 금지)

        Returns:
            {
                'regime': 'TREND' | 'RANGE' | 'CHOP',
                'atr_pct': float,
                'confidence': float
            }
        """
        regime_cfg = self.config.get("regime_filter", {})

        if not regime_cfg.get("enabled", True):
            return {"regime": "TREND", "atr_pct": 0.0, "confidence": 1.0}

        atr_period = regime_cfg.get("atr_period", 14)
        trend_min = regime_cfg.get("thresholds", {}).get("trend_min", 0.015)  # 1.5%
        range_max = regime_cfg.get("thresholds", {}).get("range_max", 0.008)  # 0.8%

        # ATR% 계산
        if "atr" not in df.columns:
            logger.warning("[Regime] ATR not in df, calculating...")
            df["atr"] = self._calculate_atr(df, atr_period)

        current_price = df["close"].iloc[-1]
        current_atr = df["atr"].iloc[-1]
        atr_pct = current_atr / current_price

        # Regime 분류
        if atr_pct >= trend_min:
            regime = "TREND"
            confidence = min(1.0, atr_pct / trend_min)
        elif atr_pct <= range_max:
            regime = "RANGE"
            confidence = min(1.0, (range_max - atr_pct) / range_max)
        else:
            regime = "CHOP"
            confidence = 0.5  # 중간 영역

        return {"regime": regime, "atr_pct": atr_pct, "confidence": confidence}

    def _get_sub_model_votes(
        self, df: pd.DataFrame, regime: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get votes from 3 sub-models

        Returns:
            {
                'trend': {'direction': 'LONG'|'SHORT'|None, 'confidence': float, 'reasons': []},
                'reversion': {...},
                'breakout': {...}
            }
        """
        # ITER21: SSOT - self._sub_models_cfg 사용 (멀티패스 리졸브된 값)
        sub_cfg = self._sub_models_cfg

        votes = {
            "trend": self._sub_model_trend(df, regime, sub_cfg.get("trend", {})),
            "reversion": self._sub_model_reversion(
                df, regime, sub_cfg.get("reversion", {})
            ),
            "breakout": self._sub_model_breakout(
                df, regime, sub_cfg.get("breakout", {})
            ),
        }

        return votes

    def _sub_model_trend(
        self, df: pd.DataFrame, regime: str, cfg: dict
    ) -> Dict[str, Any]:
        """
        Sub-Model 1: Trend-Following (EMA Cross + ADX)

        Logic:
        - LONG: fast_ema > slow_ema AND adx > threshold
        - SHORT: fast_ema < slow_ema AND adx > threshold
        - Regime Filter: TREND만 허용
        """
        if regime != "TREND":
            return {
                "direction": None,
                "confidence": 0.0,
                "reasons": ["regime_not_trend"],
            }

        fast_period = cfg.get("ema_fast", 20)
        slow_period = cfg.get("ema_slow", 50)
        adx_threshold = cfg.get("adx_threshold", 25)

        # Indicators
        if f"ema_{fast_period}" not in df.columns:
            df[f"ema_{fast_period}"] = (
                df["close"].ewm(span=fast_period, adjust=False).mean()
            )
        if f"ema_{slow_period}" not in df.columns:
            df[f"ema_{slow_period}"] = (
                df["close"].ewm(span=slow_period, adjust=False).mean()
            )
        if "adx" not in df.columns:
            df["adx"] = self._calculate_adx(df, 14)

        fast_ema = df[f"ema_{fast_period}"].iloc[-1]
        slow_ema = df[f"ema_{slow_period}"].iloc[-1]
        adx = df["adx"].iloc[-1]

        reasons = []

        # ADX 체크
        if adx < adx_threshold:
            return {"direction": None, "confidence": 0.0, "reasons": ["adx_weak"]}

        # EMA Cross
        if fast_ema > slow_ema:
            direction = "LONG"
            confidence = min(1.0, (fast_ema - slow_ema) / slow_ema * 100)  # % 차이
            reasons.append("ema_bullish_cross")
        elif fast_ema < slow_ema:
            direction = "SHORT"
            confidence = min(1.0, (slow_ema - fast_ema) / fast_ema * 100)
            reasons.append("ema_bearish_cross")
        else:
            return {"direction": None, "confidence": 0.0, "reasons": ["ema_flat"]}

        reasons.append(f"adx_{adx:.1f}")

        return {
            "direction": direction,
            "confidence": confidence * 0.7 + (adx / 100) * 0.3,  # EMA 70% + ADX 30%
            "reasons": reasons,
        }

    def _sub_model_reversion(
        self, df: pd.DataFrame, regime: str, cfg: dict
    ) -> Dict[str, Any]:
        """
        Sub-Model 2: Mean-Reversion (RSI + Bollinger Bands)

        Logic:
        - LONG: rsi < oversold AND close < lower_bb
        - SHORT: rsi > overbought AND close > upper_bb
        - Regime Filter: RANGE 선호
        """
        if regime == "CHOP":
            return {"direction": None, "confidence": 0.0, "reasons": ["regime_chop"]}

        rsi_period = cfg.get("rsi_period", 14)
        rsi_oversold = cfg.get("rsi_oversold", 30)
        rsi_overbought = cfg.get("rsi_overbought", 70)
        bb_period = cfg.get("bb_period", 20)
        bb_std = cfg.get("bb_std", 2.0)

        # Indicators
        if "rsi" not in df.columns:
            df["rsi"] = self._calculate_rsi(df, rsi_period)
        if "bb_upper" not in df.columns or "bb_lower" not in df.columns:
            bb = self._calculate_bollinger(df, bb_period, bb_std)
            df["bb_upper"] = bb["upper"]
            df["bb_lower"] = bb["lower"]

        rsi = df["rsi"].iloc[-1]
        close = df["close"].iloc[-1]
        bb_upper = df["bb_upper"].iloc[-1]
        bb_lower = df["bb_lower"].iloc[-1]

        reasons = []

        # LONG: Oversold
        if rsi < rsi_oversold and close < bb_lower:
            direction = "LONG"
            confidence = (rsi_oversold - rsi) / rsi_oversold  # 0~1
            reasons.extend(["rsi_oversold", "bb_lower_breach"])

        # SHORT: Overbought
        elif rsi > rsi_overbought and close > bb_upper:
            direction = "SHORT"
            confidence = (rsi - rsi_overbought) / (100 - rsi_overbought)
            reasons.extend(["rsi_overbought", "bb_upper_breach"])

        else:
            return {"direction": None, "confidence": 0.0, "reasons": ["no_extreme"]}

        # Regime 보정: RANGE에서 더 강한 신뢰도
        if regime == "RANGE":
            confidence *= 1.2
            reasons.append("regime_range_boost")

        return {
            "direction": direction,
            "confidence": min(1.0, confidence),
            "reasons": reasons,
        }

    def _sub_model_breakout(
        self, df: pd.DataFrame, regime: str, cfg: dict
    ) -> Dict[str, Any]:
        """
        Sub-Model 3: Breakout (ATR + Volume)

        Logic:
        - LONG: close > high_lookback AND volume > volume_ma * threshold
        - SHORT: close < low_lookback AND volume > volume_ma * threshold
        - Regime Filter: TREND 선호
        """
        if regime == "CHOP":
            return {"direction": None, "confidence": 0.0, "reasons": ["regime_chop"]}

        lookback = cfg.get("lookback", 20)
        volume_threshold = cfg.get("volume_threshold", 1.5)
        volume_ma_period = cfg.get("volume_ma_period", 20)

        # Indicators
        if "volume_ma" not in df.columns:
            df["volume_ma"] = df["volume"].rolling(volume_ma_period).mean()

        close = df["close"].iloc[-1]
        high_lookback = df["high"].iloc[-lookback:].max()
        low_lookback = df["low"].iloc[-lookback:].min()
        volume = df["volume"].iloc[-1]
        volume_ma = df["volume_ma"].iloc[-1]

        reasons = []

        # Volume 체크
        if volume < volume_ma * volume_threshold:
            return {"direction": None, "confidence": 0.0, "reasons": ["volume_low"]}

        # Breakout
        if close > high_lookback:
            direction = "LONG"
            confidence = (close - high_lookback) / high_lookback
            reasons.extend(["breakout_high", "volume_spike"])
        elif close < low_lookback:
            direction = "SHORT"
            confidence = (low_lookback - close) / close
            reasons.extend(["breakout_low", "volume_spike"])
        else:
            return {"direction": None, "confidence": 0.0, "reasons": ["no_breakout"]}

        # Regime 보정: TREND에서 더 강한 신뢰도
        if regime == "TREND":
            confidence *= 1.3
            reasons.append("regime_trend_boost")

        return {
            "direction": direction,
            "confidence": min(1.0, confidence * 5),  # Scale up for visibility
            "reasons": reasons,
        }

    def _ensemble_vote(self, sub_votes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        N-out-of-3 Majority Vote (ITER17: self._min_votes 사용)

        Returns:
            {
                'direction': 'LONG' | 'SHORT' | None,
                'confidence': float,
                'reason': str,
                'vote_counts': dict
            }
        """
        # ITER17 FIX: __init__에서 설정된 인스턴스 변수 사용 (SSOT)
        min_votes = self._min_votes
        confidence_threshold = self._confidence_threshold
        
        # 디버그 로그 (첫 호출 시에만)
        if self._diag_enabled and self._total_signals_checked <= 1:
            logger.info(f"🔧 [ITER17] _ensemble_vote using: min_votes={min_votes}, confidence_threshold={confidence_threshold}")

        # Count votes
        vote_counts = {"LONG": 0, "SHORT": 0, "FLAT": 0}
        confidence_sum = {"LONG": 0.0, "SHORT": 0.0}

        for model_name, vote in sub_votes.items():
            direction = vote["direction"]
            confidence = vote["confidence"]

            if direction is None:
                vote_counts["FLAT"] += 1
            else:
                vote_counts[direction] += 1
                confidence_sum[direction] += confidence

        # N-out-of-3 Decision (ITER17: min_votes 사용)
        if vote_counts["LONG"] >= min_votes:
            direction = "LONG"
            avg_confidence = confidence_sum["LONG"] / vote_counts["LONG"]
            reason = f"majority_long_{vote_counts['LONG']}/3_min{min_votes}"

        elif vote_counts["SHORT"] >= min_votes:
            direction = "SHORT"
            avg_confidence = confidence_sum["SHORT"] / vote_counts["SHORT"]
            reason = f"majority_short_{vote_counts['SHORT']}/3_min{min_votes}"

        else:
            return {
                "direction": None,
                "confidence": 0.0,
                "reason": f"no_consensus_L{vote_counts['LONG']}_S{vote_counts['SHORT']}_F{vote_counts['FLAT']}",
                "vote_counts": vote_counts,
            }

        # Confidence Threshold 체크
        if avg_confidence < confidence_threshold:
            return {
                "direction": None,
                "confidence": avg_confidence,
                "reason": f"confidence_low_{avg_confidence:.2f}<{confidence_threshold}",
                "vote_counts": vote_counts,
            }

        return {
            "direction": direction,
            "confidence": avg_confidence,
            "reason": reason,
            "vote_counts": vote_counts,
        }

    def _calculate_entry_exit(
        self, df: pd.DataFrame, direction: str, confidence: float, regime: str
    ) -> Dict[str, Any]:
        """
        Calculate Entry/SL/TP levels

        Args:
            df: OHLCV data
            direction: 'LONG' or 'SHORT'
            confidence: Ensemble confidence (0~1)
            regime: Market regime

        Returns:
            dict: {
                'side': 'LONG' | 'SHORT',
                'entry': float,
                'sl': float,
                'tp': float,
                'confidence': float,
                'reason': str
            }
        """
        # Access regime config (engine merges params at top level via **strategy_params)
        regime_cfg = self.config.get("regime", {})

        entry = df["close"].iloc[-1]
        atr = df["atr"].iloc[-1] if "atr" in df.columns else entry * 0.02  # 2% fallback

        # SL/TP Distance (ATR 기반)
        sl_atr_mult = regime_cfg.get('sl_atr_multiplier', 1.5)
        tp_atr_mult = regime_cfg.get('tp_atr_multiplier', 3.0)  # RR 2.0

        sl_distance = atr * sl_atr_mult
        tp_distance = atr * tp_atr_mult

        if direction == "LONG":
            sl = entry - sl_distance
            tp = entry + tp_distance
            side = "LONG"
        else:  # SHORT
            sl = entry + sl_distance
            tp = entry - tp_distance
            side = "SHORT"

        return {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "confidence": confidence,
            "reason": f"ensemble_{direction.lower()}_conf_{confidence:.2f}",
        }

    # ========================================
    # Helper Functions (Indicator Calculations)
    # ========================================

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        return atr

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self._calculate_atr(df, period)

        plus_di = 100 * (plus_dm.rolling(period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()

        return adx

    def _calculate_bollinger(
        self, df: pd.DataFrame, period: int = 20, std: float = 2.0
    ) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = df["close"].rolling(period).mean()
        rolling_std = df["close"].rolling(period).std()

        upper = sma + (rolling_std * std)
        lower = sma - (rolling_std * std)

        return {"middle": sma, "upper": upper, "lower": lower}

    # ========================================
    # DecisionTrace Diagnostics
    # ========================================

    def _diag_inc(self, reason: str):
        """차단 사유 카운터 증가"""
        if self._diag_enabled:
            self._diag_counters[reason] = self._diag_counters.get(reason, 0) + 1

    def get_diagnostics(self) -> Dict[str, Any]:
        """DecisionTrace 진단 결과 반환"""
        if not self._diag_enabled:
            return {}

        sorted_reasons = sorted(
            self._diag_counters.items(), key=lambda x: x[1], reverse=True
        )

        total_blocks = sum(self._diag_counters.values())

        return {
            "total_signals_checked": self._total_signals_checked,
            "total_blocks": total_blocks,
            "block_rate": total_blocks / self._total_signals_checked
            if self._total_signals_checked > 0
            else 0.0,
            "top_blockers": sorted_reasons[:10],
            "all_counters": self._diag_counters,
        }
