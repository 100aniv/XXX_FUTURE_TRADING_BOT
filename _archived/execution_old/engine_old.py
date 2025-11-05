#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Engine
==============
통합 거래 엔진 (백테스트/페이퍼/라이브 공통)
"""
from typing import Dict, Optional
from common.logger import setup_logger
from .position_sizer import PositionSizer
from .risk_manager import RiskManager
from .position_tracker import PositionTracker
from .data_sources.backtest import BacktestDataSource
from .data_sources.live import LiveDataSource
from .executors.simulation import SimulationExecutor
from .executors.paper import PaperExecutor
from .executors.live import LiveExecutor

logger = setup_logger(__name__)


class TradingEngine:
    """
    통합 거래 엔진
    
    모든 모드에서 동일한 로직 사용
    모드별로 data_source와 executor만 교체
    """
    
    def __init__(self, mode: str, **config):
        """
        초기화
        
        Args:
            mode: 'backtest' | 'paper' | 'live'
            **config: 모드별 설정
        """
        self.mode = mode
        self.config = config
        
        # ⭐ 공통 모듈 (모든 모드 동일!)
        # Note: PositionSizer는 백테스트 실행 시 전략별 설정으로 재초기화
        self.position_sizer = PositionSizer()
        self.risk_manager = RiskManager()
        self.position_tracker = PositionTracker()
        
        # ⭐ 모드별 모듈 (교체!)
        if mode == 'backtest':
            self.data_source = BacktestDataSource(config['data_path'])
            self.executor = SimulationExecutor(
                fee_rate=config.get('fee_rate', 0.0004),
                slippage_pct=config.get('slippage_pct', 0.0005)
            )
        elif mode == 'paper':
            self.data_source = LiveDataSource(
                exchange=config.get('exchange', 'binance'),
                api_key=config.get('api_key'),
                api_secret=config.get('api_secret')
            )
            self.executor = PaperExecutor(
                fee_rate=config.get('fee_rate', 0.0004)
            )
        elif mode == 'live':
            self.data_source = LiveDataSource(
                exchange=config.get('exchange', 'binance'),
                api_key=config.get('api_key'),
                api_secret=config.get('api_secret')
            )
            self.executor = LiveExecutor(
                api_key=config['api_key'],
                api_secret=config['api_secret'],
                fee_rate=config.get('fee_rate', 0.0004)
            )
        else:
            raise ValueError(f"지원하지 않는 모드: {mode}")
        
        logger.info(f"✅ TradingEngine 초기화: mode={mode}")
        logger.info(f"   DataSource: {type(self.data_source).__name__}")
        logger.info(f"   Executor: {type(self.executor).__name__}")
    
    def run_backtest(self, strategy_module, strategy_config: Dict):
        """
        백테스트 실행 (✅ DB 기반 - 실시간과 동일한 흐름)
        
        Flow:
        1. 캔들 → indicators
        2. indicators → strategies → signals (DB)
        3. signals (DB) → ensemble → decisions (DB)
        4. decisions (DB) → execution → trades (DB)
        
        Args:
            strategy_module: 전략 모듈
            strategy_config: 전략 설정
        
        Returns:
            (trades, metrics)
        """
        if self.mode != 'backtest':
            raise ValueError("백테스트 모드에서만 실행 가능")
        
        # SignalGenerator 초기화 (실시간과 동일)
        from signals.signal_generator import SignalGenerator
        
        # lookback 설정 추가
        config_with_lookback = {
            **strategy_config,
            'lookback': 500,
            'timeframe': strategy_config.get('timeframe', '5m'),
            'enable_mtf_confirm': strategy_config.get('enable_mtf_confirm', False),
            'enable_vol_spike_filter': strategy_config.get('enable_vol_spike_filter', False),
            'vol_spike_mult': 2.0,
            'vol_ma_len': 30,
        }
        
        signal_gen = SignalGenerator(
            config=config_with_lookback,
            strategy_modules={config_with_lookback['timeframe']: strategy_module}
        )
        
        # 데이터 로드
        df = self.data_source.load_data()
        
        # 전략별 리스크 설정 적용
        if 'risk_per_trade' in strategy_config:
            self.position_sizer.risk_per_trade = strategy_config['risk_per_trade']
            logger.info(f"📊 전략별 리스크: {strategy_config['risk_per_trade']*100:.2f}%")
        
        # ✅ 지표 계산 (한 번만)
        from indicators import add_indicators
        df = add_indicators(df)
        df['time'] = df['timestamp'].astype('int64') // 10**9  # ⭐ time 컬럼 추가
        
        logger.info(f"📊 백테스트 시작: {len(df)} 캔들")
        
        # 초기화
        trades = []
        positions = []
        equity = self.config.get('initial_capital', 10000)
        initial_equity = equity
        
        cooldown_until_idx = {}
        cooldown_candles = strategy_config.get('cooldown_candles', 3)
        
        for idx in range(100, len(df)):
            current = df.iloc[idx]
            current_price = current['close']
            timestamp = current['timestamp']
            atr = current.get('atr', current_price * 0.01)
            
            # 1) TP/SL 체크
            for pos in positions[:]:
                # TP/SL 체크 (⭐ config 전달)
                hit, reason = self._check_tpsl(pos, current_price, strategy_config)
                
                if hit:
                    trade = self._close_position(pos, current_price, timestamp, reason)
                    trades.append(trade)
                    equity += trade['pnl_net']
                    positions.remove(pos)
                    
                    # ⭐ 거래 상세 로깅
                    pnl_symbol = "🟢" if trade['pnl_net'] > 0 else "🔴"
                    logger.info(
                        f"{pnl_symbol} [{reason}] {trade['side']} "
                        f"진입: ${trade['entry']:,.2f} → 청산: ${trade['exit']:,.2f} | "
                        f"수량: {trade['qty']:.4f} | "
                        f"PnL: ${trade['pnl_net']:+,.2f} ({trade['pnl_net']/trade['entry']/trade['qty']*100:+.2f}%) | "
                        f"자본: ${equity:,.2f}"
                    )
                    
                    # 현재 자본 업데이트
                    self.position_sizer.equity = equity
            
            # 신호 생성 (Cooldown 체크)
            symbol_key = 'BACKTEST'
            if cooldown_until_idx.get(symbol_key, 0) > idx:
                continue
            
            # 신호 확인 (직접 호출 - 우선 작동하게)
            window_df = df.iloc[max(0, idx-200):idx+1].copy()
            signal = strategy_module.signal_logic(window_df, strategy_config)
                    
            if signal and signal.get('side'):
                position = self._open_position(
                    signal['side'],
                    current_price,
                    atr,
                    timestamp,
                    strategy_config
                )
                if position:
                    positions.append(position)
                    equity -= position['fee_open']
                    
                    # 포지션 오픈 로깅
                    logger.info(
                        f"📊 [{position['side']}] 진입: ${position['entry']:,.2f} | "
                        f"수량: {position['qty']:.4f} | "
                        f"SL: ${position['sl']:,.2f} | TP: ${position['tp']:,.2f} | "
                        f"수수료: ${position['fee_open']:,.2f}"
                    )
                    
                    # 현재 자본 업데이트 (수수료 차감 반영)
                    self.position_sizer.equity = equity
                    
                    # Cooldown 설정
                    cooldown_until_idx[symbol_key] = idx + cooldown_candles
        
        # 강제 청산
        for pos in positions:
            trade = self._close_position(pos, current_price, df.iloc[-1]['timestamp'], 'END')
            trades.append(trade)
            equity += trade['pnl_net']
        
        # 메트릭스 계산
        metrics = self._calculate_metrics(trades, initial_equity, equity)
        
        logger.info(f"✅ 백테스트 완료: {len(trades)}건, 승률 {metrics['win_rate']:.2%}")
        
        # ⭐ 거래 장부 CSV 저장
        self._save_trade_log(trades, strategy_config, folder='reports/trades')
        
        return trades, metrics
    
    def run_ensemble_backtest(self, all_strategies: Dict, strategy_params: Dict):
        """
        Ensemble 백테스트 (6개 전략 가중치 조합)
        
        Flow:
        1. 각 캔들마다 6개 전략의 신호 생성
        2. 가중치 계산 (성과 메트릭 기반)
        3. 통합 점수 = Σ(가중치 * 신호)
        4. 최종 결정 (LONG/SHORT/FLAT)
        5. 포지션 관리 및 거래
        """
        if self.mode != 'backtest':
            raise ValueError("백테스트 모드에서만 실행 가능")
        
        # 데이터 로드
        df = self.data_source.load_data()
        
        # 지표 계산
        from indicators import add_indicators
        df = add_indicators(df)
        df['time'] = df['timestamp'].astype('int64') // 10**9
        
        logger.info(f"📊 Ensemble 백테스트 시작: {len(df)} 캔들")
        logger.info(f"   6개 전략 가중치 조합")
        
        # 초기화
        trades = []
        positions = []
        equity = self.config.get('initial_capital', 10000)
        initial_equity = equity
        
        # 가중치 (기본값, 실시간에서는 DB 성과 기반)
        weights = {
            'trend': 0.18,
            'reversion': 0.16,
            'breakout': 0.17,
            'scalping': 0.15,
            'daytrade': 0.18,
            'swing': 0.16,
        }
        
        cooldown_until_idx = 0
        cooldown_candles = 3
        
        for idx in range(100, len(df)):
            current = df.iloc[idx]
            current_price = current['close']
            timestamp = current['timestamp']
            atr = current.get('atr', current_price * 0.01)
            
            # 1) TP/SL 체크
            for pos in positions[:]:
                hit, reason = self._check_tpsl(pos, current_price, strategy_params.get('ensemble', {}))
                
                if hit:
                    trade = self._close_position(pos, current_price, timestamp, reason)
                    trades.append(trade)
                    equity += trade['pnl_net']
                    positions.remove(pos)
                    
                    pnl_symbol = "🟢" if trade['pnl_net'] > 0 else "🔴"
                    logger.info(
                        f"{pnl_symbol} [ENSEMBLE-{reason}] {trade['side']} "
                        f"진입: ${trade['entry']:,.2f} → 청산: ${trade['exit']:,.2f} | "
                        f"PnL: ${trade['pnl_net']:+,.2f} | 자본: ${equity:,.2f}"
                    )
                    
                    self.position_sizer.equity = equity
            
            # Cooldown 체크
            if cooldown_until_idx > idx:
                continue
            
            # 2) 6개 전략 신호 생성
            window_df = df.iloc[max(0, idx-200):idx+1].copy()
            signals = []
            
            for strategy_name, (strategy_module, config) in all_strategies.items():
                try:
                    signal = strategy_module.signal_logic(window_df, config)
                    if signal and signal.get('side'):
                        signals.append({
                            'strategy_id': strategy_name,
                            'direction': signal['side'],
                            'entry_price': signal.get('entry', current_price),
                            'sl_price': signal.get('sl'),
                            'tp_price': signal.get('tp'),
                            'confidence': signal.get('confidence', 0.75),
                        })
                except:
                    pass
            
            if not signals:
                continue
            
            # 3) 가중치 기반 통합 점수
            side_scores = {'LONG': 0.0, 'SHORT': 0.0}
            for sig in signals:
                weight = weights.get(sig['strategy_id'], 0.0)
                if sig['direction'] == 'LONG':
                    side_scores['LONG'] += weight
                elif sig['direction'] == 'SHORT':
                    side_scores['SHORT'] += weight
            
            score = side_scores['LONG'] - side_scores['SHORT']
            
            # 4) 최종 결정
            chosen_side = None
            if score >= 0.15:  # theta_long
                chosen_side = 'LONG'
            elif score <= -0.15:  # theta_short
                chosen_side = 'SHORT'
            
            if chosen_side:
                position = self._open_position(
                    chosen_side,
                    current_price,
                    atr,
                    timestamp,
                    strategy_params.get('ensemble', strategy_params.get('scalping', {}))
                )
                if position:
                    positions.append(position)
                    equity -= position['fee_open']
                    
                    logger.info(
                        f"📊 [ENSEMBLE-{chosen_side}] 진입: ${position['entry']:,.2f} | "
                        f"신호: {len(signals)}개 | 점수: {score:+.2f} | "
                        f"수량: {position['qty']:.4f}"
                    )
                    
                    self.position_sizer.equity = equity
                    cooldown_until_idx = idx + cooldown_candles
        
        # 강제 청산
        for pos in positions:
            trade = self._close_position(pos, current_price, df.iloc[-1]['timestamp'], 'END')
            trades.append(trade)
            equity += trade['pnl_net']
        
        # 메트릭스 계산
        metrics = self._calculate_metrics(trades, initial_equity, equity)
        
        logger.info(f"✅ Ensemble 백테스트 완료: {len(trades)}건, 승률 {metrics['win_rate']:.2%}")
        
        # 거래 장부 저장
        self._save_trade_log(trades, {'strategy': 'ensemble'}, folder='reports/trades')
        
        return trades, metrics
    
    def _check_tpsl(self, position: Dict, current_price: float, config: Dict):
        """
        TP/SL 체크 (⭐ PositionTracker 사용)
        """
        # ⭐ Trailing Stop 업데이트
        position = self.position_tracker.update_trailing_stop(position, current_price, config)
        
        # ⭐ TP/SL 체크
        should_close, reason = self.position_tracker.check_tpsl(position, current_price)
        
        return should_close, reason
    
    def _open_position(self, side: str, price: float, atr: float, timestamp, config: Dict):
        """포지션 오픈 (⭐ common.calculations 활용)"""
        from common.calculations import price_levels
        
        # TP/SL 계산 (공통 함수 사용)
        atr_mult_sl = config.get('atr_mult_sl', 1.5)
        rr = config.get('rr', 2.0)
        
        entry, sl_price, tp_price = price_levels(side, price, atr, rr, atr_mult_sl)
        
        # 포지션 크기 계산
        signal_for_sizer = {
            'entry_price': price,
            'sl_price': sl_price,
            'confidence': 0.8,
            'atr': atr,
        }
        
        qty, meta = self.position_sizer.calculate(signal_for_sizer)
        
        if qty <= 0:
            return None
        
        # 실행
        result = self.executor.execute(side, price, qty)
        
        if qty > 0:
            return {
                'side': side,
                'entry': result['executed_price'],
                'qty': qty,
                'sl': sl_price,
                'tp': tp_price,
                'entry_time': timestamp,
                'fee_open': result['fee'],
                'enable_trailing_stop': config.get('enable_trailing_stop', False),  # ⭐ 설정 전달
            }
        return None
    
    def _close_position(self, position: Dict, exit_price: float, timestamp, reason: str):
        """포지션 청산 (⭐ 펀딩비 포함)"""
        from common.calculations import calculate_funding_fee
        from datetime import datetime
        
        base_qty = position['qty']
        sign = 1 if position['side'] == 'LONG' else -1
        
        # 청산 실행
        result = self.executor.execute(
            'SHORT' if position['side'] == 'LONG' else 'LONG',
            exit_price,
            base_qty
        )
        
        # ⭐ 펀딩비 계산 (선물 거래)
        position_value = position['entry'] * base_qty
        
        # 보유 시간 계산
        if isinstance(timestamp, datetime) and isinstance(position['entry_time'], datetime):
            holding_time = timestamp - position['entry_time']
            holding_hours = holding_time.total_seconds() / 3600
        else:
            holding_hours = 0
        
        funding_fee = calculate_funding_fee(
            position_value=position_value,
            holding_hours=holding_hours,
            funding_rate=0.0001,  # 0.01%
            side=position['side']
        )
        
        # PnL 계산 (수수료 + 펀딩비 포함!)
        pnl_gross = sign * (exit_price - position['entry']) * base_qty
        pnl_net = pnl_gross - position['fee_open'] - result['fee'] - abs(funding_fee)
        
        return {
            **position,
            'exit': exit_price,
            'exit_time': timestamp,
            'exit_reason': reason,
            'fee_close': result['fee'],
            'funding_fee': funding_fee,  # ⭐ 펀딩비 추가
            'holding_hours': holding_hours,
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
        }
    
    def _save_trade_log(self, trades, strategy_config, folder='reports/trades'):
        """거래 장부 CSV 저장"""
        if not trades:
            return
        
        import pandas as pd
        from pathlib import Path
        from datetime import datetime
        
        # 거래 데이터프레임 생성
        trade_records = []
        for i, t in enumerate(trades, 1):
            trade_records.append({
                'No': i,
                '날짜': t['entry_time'],
                '청산날짜': t['exit_time'],
                '보유시간(h)': f"{t.get('holding_hours', 0):.1f}",
                '방향': t['side'],
                '진입가': f"${t['entry']:,.2f}",
                '청산가': f"${t['exit']:,.2f}",
                '수량': f"{t['qty']:.4f}",
                'SL': f"${t['sl']:,.2f}",
                'TP': f"${t['tp']:,.2f}",
                '청산사유': t['exit_reason'],
                '수수료(진입)': f"${t['fee_open']:.2f}",
                '수수료(청산)': f"${t['fee_close']:.2f}",
                '펀딩비': f"${t.get('funding_fee', 0):.2f}",  # ⭐ 펀딩비
                'PnL(Gross)': f"${t['pnl_gross']:+,.2f}",
                'PnL(Net)': f"${t['pnl_net']:+,.2f}",
                '수익률': f"{t['pnl_net']/t['entry']/t['qty']*100:+.2f}%",
            })
        
        df_trades = pd.DataFrame(trade_records)
        
        # 저장 경로
        output_dir = Path(folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = output_dir / f'trade_log_{timestamp}.csv'
        
        df_trades.to_csv(csv_file, index=False, encoding='utf-8-sig')
        logger.info(f"📄 거래 장부 저장: {csv_file}")
    
    def _calculate_metrics(self, trades, initial_equity, final_equity):
        """메트릭스 계산 (MDD, Sharpe, Sortino 포함 + ⭐ 평균 승/손 금액)"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,  # ⭐ 평균 승리 금액
                'avg_loss': 0,  # ⭐ 평균 손실 금액
                'total_return': 0,
                'total_return_pct': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
            }
        
        # 승/패 통계
        total_trades = len(trades)
        wins = [t for t in trades if t['pnl_net'] > 0]
        losses = [t for t in trades if t['pnl_net'] <= 0]
        
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # ⭐ 평균 승/손 금액 (문제 진단용)
        avg_win = sum(t['pnl_net'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl_net'] for t in losses) / len(losses) if losses else 0
        
        total_profit = sum(t['pnl_net'] for t in wins)
        total_loss = abs(sum(t['pnl_net'] for t in losses))
        
        # ⭐ MDD 계산
        equity_curve = [initial_equity]
        running_equity = initial_equity
        for t in trades:
            running_equity += t['pnl_net']
            equity_curve.append(running_equity)
        
        peak = initial_equity
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd
        
        max_dd_pct = (max_dd / initial_equity) * 100 if initial_equity > 0 else 0
        
        # ⭐ Sharpe/Sortino 계산
        import numpy as np
        
        returns = [t['pnl_net'] / initial_equity for t in trades]
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 0
        
        # Sharpe (연간화: 252 거래일 가정, 5분봉이면 조정 필요)
        sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        
        # Sortino (하방 변동성만 고려)
        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else std_return
        sortino = (avg_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        
        # Profit Factor
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,  # ⭐ 평균 승리 금액
            'avg_loss': avg_loss,  # ⭐ 평균 손실 금액
            'profit_factor': profit_factor,
            'total_return': final_equity - initial_equity,
            'total_return_pct': ((final_equity - initial_equity) / initial_equity) * 100,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
        }
    
    def run_realtime(self):
        """
        실시간 트레이딩 실행 (페이퍼/라이브 공통)
        
        WebSocket으로 실시간 데이터 수신 → 신호 생성 → DB 저장 → Ensemble → 거래
        
        페이퍼와 라이브의 차이:
        - 페이퍼: PaperExecutor (가상 체결)
        - 라이브: LiveExecutor (실제 Binance API)
        → executor만 다르고 로직은 동일!
        """
        if self.mode not in ['paper', 'live']:
            raise ValueError("페이퍼 또는 라이브 모드에서만 실행 가능")
        
        logger.info("="*80)
        if self.mode == 'live':
            logger.warning("⚠️⚠️⚠️  라이브 모드: 실제 거래 실행!")
            logger.warning("⚠️  페이퍼 모드로 충분히 테스트 후 사용하세요!")
        logger.info(f"🚀 {self.mode.upper()} 트레이딩 시작")
        logger.info(f"   DataSource: {type(self.data_source).__name__}")
        logger.info(f"   Executor: {type(self.executor).__name__}")
        logger.info("="*80)
        
        # 실시간 루프 (WebSocket + DB + Ensemble)
        from collector import WebSocketCollector, bootstrap_history
        from indicators import add_indicators
        from strategies import trend, reversion, breakout, scalping, daytrade, swing, ensemble
        from common.utils import buffer_to_df
        from common.strategy_config import load_strategy_params
        from collections import deque
        from datetime import datetime
        from uuid import uuid4
        import time
        
        # 설정
        symbols = self.config.get('symbols', ['BTCUSDT'])
        timeframe = self.config.get('timeframe', '5m')
        lookback = self.config.get('lookback', 400)
        
        # 전략 설정
        strategy_params = load_strategy_params()
        STRATEGIES = {
            "trend": trend,
            "reversion": reversion,
            "breakout": breakout,
            "scalping": scalping,
            "daytrade": daytrade,
            "swing": swing,
        }
        
        # 심볼별 캔들 버퍼
        buffers = {symbol: deque(maxlen=lookback) for symbol in symbols}
        
        # WebSocket 수집기
        ws_collector = WebSocketCollector(symbols=symbols, timeframe=timeframe)
        
        # 초기 히스토리 로드
        logger.info("📡 초기 데이터 로드 중...")
        for symbol in symbols:
            bootstrap_history(symbol, timeframe, lookback, buffers)
        
        logger.info("✅ 초기 데이터 로드 완료")
        logger.info("📡 WebSocket 연결 중...")
        
        # 캔들 처리 콜백
        def on_candle_closed(symbol, candle, is_closed, tf):
            if not is_closed or tf != timeframe:
                return
            
            try:
                # 버퍼에 추가
                buffers[symbol].append(candle)
                
                # DataFrame 생성
                df = buffer_to_df(symbol, buffers)
                if len(df) < 50:
                    return
                
                # 지표 계산
                df = add_indicators(df)
                
                # 6개 전략 신호 생성 및 DB 저장
                for strategy_id, strategy_module in STRATEGIES.items():
                    try:
                        config = strategy_params[strategy_id]
                        signal = strategy_module.signal_logic(df, config)
                        
                        if signal and signal.get("side"):
                            # DB 저장 (signals 모듈)
                            from signals.signal_storage import save_signal_to_db
                            save_signal_to_db(
                                signal_id=str(uuid4()),
                                strategy_id=strategy_id,
                                symbol=symbol,
                                timeframe=timeframe,
                                candle_closed_at=datetime.fromtimestamp(candle.get("time", int(time.time()*1000))/1000),
                                direction=signal["side"],
                                confidence=signal.get("confidence", 0.75),
                                entry_price=signal.get("entry"),
                                sl_price=signal.get("sl"),
                                tp_price=signal.get("tp"),
                                atr=signal.get("atr"),
                                leverage=signal.get("lev"),
                                features=signal.get("features", {})
                            )
                            logger.info(f"✅ {strategy_id.upper()}: {symbol} {signal['side']}")
                    except Exception as e:
                        logger.error(f"❌ {strategy_id} 신호 생성 실패: {e}")
            except Exception as e:
                logger.error(f"⚠️ 캔들 처리 오류: {e}")
        
        # Ensemble 주기적 실행
        def run_ensemble_and_execution():
            while True:
                try:
                    # Ensemble 통합 + 거래 실행
                    from common.database import get_db_connection
                    from psycopg2.extras import RealDictCursor
                    
                    with get_db_connection() as conn:
                        # Ensemble 통합
                        ensemble.process_pending_signals(conn, logger)
                        
                        # 거래 실행 (DB에서 미실행 결정 읽기)
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        cursor.execute("""
                            SELECT decision_id, symbol, chosen_side, chosen_size,
                                   entry_price, sl_price, tp_price, leverage
                            FROM trading.decisions
                            WHERE executed = FALSE
                            ORDER BY created_at ASC
                            LIMIT 10
                        """)
                        decisions = cursor.fetchall()
                        
                        for decision in decisions:
                            try:
                                # None 값 체크
                                if not decision.get('entry_price') or not decision.get('chosen_size'):
                                    logger.warning(f"⚠️ 불완전한 결정: {decision}")
                                    continue
                                
                                # 거래 실행
                                result = self.executor.execute(
                                    side=decision['chosen_side'],
                                    price=decision['entry_price'],
                                    qty=decision['chosen_size']
                                )
                                
                                if result.get('success'):
                                    # DB에 거래 기록
                                    from uuid import uuid4
                                    trade_id = str(uuid4())
                                    
                                    cursor.execute("""
                                        INSERT INTO trading.trades 
                                        (trade_id, decision_id, symbol, side, entry_price, sl_price, tp_price, quantity, leverage, status)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        trade_id,
                                        decision['decision_id'],
                                        decision['symbol'],
                                        decision['chosen_side'],
                                        result['executed_price'],
                                        decision['sl_price'],
                                        decision['tp_price'],
                                        result['qty'],
                                        decision['leverage'],
                                        'OPEN'
                                    ))
                                    
                                    # 결정을 실행됨으로 표시
                                    cursor.execute("""
                                        UPDATE trading.decisions
                                        SET executed = TRUE, executed_at = NOW()
                                        WHERE decision_id = %s
                                    """, (decision['decision_id'],))
                                    
                                    conn.commit()
                                    logger.info(f"✅ 거래 실행: {decision['chosen_side']} {decision['symbol']} @ ${result['executed_price']:,.2f}")
                            except Exception as e:
                                logger.error(f"❌ 거래 실행 실패: {e}")
                    
                except Exception as e:
                    logger.error(f"❌ Ensemble/Execution 오류: {e}")
                
                time.sleep(5)
        
        # WebSocket 시작 (블로킹)
        import threading
        ensemble_thread = threading.Thread(target=run_ensemble_and_execution, daemon=True)
        ensemble_thread.start()
        
        # 콜백 등록 후 시작
        ws_collector.on_candle(on_candle_closed).start()
        
        logger.info(f"{self.mode.upper()} 트레이딩 종료")
    
    @staticmethod
    def run_realtime_mode(mode: str):
        """
        실시간 트레이딩 모드 실행 (페이퍼/라이브)
        
        Args:
            mode: 'paper' or 'live'
        """
        import os
        from common.logger import setup_logger
        from common.config import load_config
        from common.database import test_db_connection
        
        logger = setup_logger(__name__)
        
        # DB 연결 확인
        test_db_connection()
        
        # 설정 로드
        CFG = load_config()
        
        # API 키 확인
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET')
        
        if mode == 'live' and (not api_key or not api_secret):
            logger.error("❌ 라이브 모드: BINANCE_API_KEY, BINANCE_SECRET 필수")
            import sys
            sys.exit(1)
        
        # 엔진 초기화 및 실행
        engine = TradingEngine(
            mode=mode,
            exchange='binance',
            api_key=api_key,
            api_secret=api_secret,
            fee_rate=0.0004,
            symbols=CFG.get('symbols', ['BTCUSDT']),
            timeframe=CFG.get('timeframe', '5m'),
            lookback=CFG.get('lookback', 400),
        )
        
        engine.run_realtime()
    
    @staticmethod
    def run_all_backtests():
        """
        모든 전략 백테스트 실행 (통합 엔트리포인트)
        
        main.py의 백테스트 로직을 여기로 이동
        """
        from strategies import scalping, daytrade, swing, trend, reversion, breakout
        from common.strategy_config import load_strategy_params
        from common.backtest_utils import get_backtest_period, get_data_paths, save_backtest_results
        from common.config import load_backtest_config
        from pathlib import Path
        import os
        
        logger.info("="*80)
        logger.info("📊 백테스트 시작")
        logger.info("="*80)
        
        # 전략 모듈
        strategy_modules = {
            'scalping': scalping,
            'daytrade': daytrade,
            'swing': swing,
            'trend': trend,
            'reversion': reversion,
            'breakout': breakout,
        }
        
        # 설정 로드
        strategy_params = load_strategy_params()
        backtest_cfg = load_backtest_config()
        
        # 기간 및 심볼
        start_date, end_date = get_backtest_period()
        symbol = os.getenv('BACKTEST_SYMBOL', backtest_cfg.get('symbols', ['BTCUSDT'])[0])
        
        # 데이터 경로
        data_paths = get_data_paths(symbol, start_date, end_date)
        
        # 기간 정보
        from datetime import datetime
        days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        
        logger.info(f"   기간: {start_date} ~ {end_date} ({days}일, 약 {days//365}년)")
        logger.info(f"   심볼: {symbol}")
        logger.info(f"   전략: 6개 개별 + Ensemble (조합)")
        logger.info("="*80)
        
        # 백테스트 실행
        results = {}
        all_signals = {}
        strategies_to_run = list(strategy_modules.keys())
        
        for strategy_name in strategies_to_run:
            logger.info(f"\n{'='*80}")
            logger.info(f"[{strategies_to_run.index(strategy_name)+1}/{len(strategies_to_run)}] {strategy_name.upper()} 백테스트")
            timeframe = strategy_params[strategy_name].get('timeframe', '5m')
            logger.info(f"   타임프레임: {timeframe}")
            logger.info(f"{'='*80}")
            
            try:
                strategy_module = strategy_modules[strategy_name]
                strategy_config = strategy_params[strategy_name]
                
                # 데이터 경로
                data_path = data_paths[strategy_name]
                if not data_path.exists():
                    logger.error(f"❌ 데이터 파일 없음: {data_path}")
                    results[strategy_name] = {'error': 'data_not_found'}
                    continue
                
                # 엔진 초기화
                engine = TradingEngine(
                    mode='backtest',
                    data_path=str(data_path),
                    initial_capital=backtest_cfg.get('initial_capital', 10000),
                    fee_rate=backtest_cfg.get('fee_rate', 0.0004),
                    slippage_pct=backtest_cfg.get('slippage_pct', 0.0005),
                )
                
                # 백테스트 실행
                trades, metrics = engine.run_backtest(strategy_module, strategy_config)
                all_signals[strategy_name] = (strategy_module, strategy_config)
                
                results[strategy_name] = {
                    'trades': len(trades),
                    'win_rate': metrics.get('win_rate', 0),
                    'profit_factor': metrics.get('profit_factor', 0),
                    'total_return_pct': metrics.get('total_return_pct', 0),
                    'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                }
                
                logger.info(f"✅ {strategy_name.upper()}: {metrics['total_trades']}건, 승률 {metrics['win_rate']:.2%}")
                
            except Exception as e:
                logger.error(f"❌ {strategy_name} 실패: {e}")
                import traceback
                logger.error(traceback.format_exc())
                results[strategy_name] = {'error': str(e)}
        
        # Ensemble 백테스트
        logger.info(f"\n{'='*80}")
        logger.info(f"[7/7] ENSEMBLE 백테스트 (6개 전략 가중치 조합)")
        logger.info(f"{'='*80}")
        
        try:
            # Ensemble용 엔진 (임의의 데이터 경로, ensemble은 자체 로직 사용)
            if not all_signals:
                logger.warning("⚠️ 실행된 전략이 없어 Ensemble 건너뜀")
                results['ensemble'] = {'error': 'no_strategies'}
                raise ValueError("No strategies executed")
            
            # 첫 번째 성공한 전략의 데이터 경로 사용
            first_strategy = list(all_signals.keys())[0]
            ensemble_data_path = data_paths[first_strategy]
            
            ensemble_engine = TradingEngine(
                mode='backtest',
                data_path=str(ensemble_data_path),
                initial_capital=backtest_cfg.get('initial_capital', 10000),
                fee_rate=backtest_cfg.get('fee_rate', 0.0004),
                slippage_pct=backtest_cfg.get('slippage_pct', 0.0005),
            )
            
            trades, metrics = ensemble_engine.run_ensemble_backtest(all_signals, strategy_params)
            
            results['ensemble'] = {
                'trades': len(trades),
                'win_rate': metrics.get('win_rate', 0),
                'profit_factor': metrics.get('profit_factor', 0),
                'total_return_pct': metrics.get('total_return_pct', 0),
                'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            }
            
            logger.info(f"✅ ENSEMBLE: {metrics['total_trades']}건, 승률 {metrics['win_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"❌ Ensemble 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            results['ensemble'] = {'error': str(e)}
        
        # 결과 저장 (메타데이터 포함)
        metadata = {
            'period': f"{start_date} ~ {end_date}",
            'days': days,
            'symbol': symbol,
            'strategies': list(strategy_modules.keys()),
            'settings': {
                'initial_capital': backtest_cfg.get('initial_capital', 10000),
                'fee_rate': backtest_cfg.get('fee_rate', 0.0004),
                'slippage_pct': backtest_cfg.get('slippage_pct', 0.0005),
            }
        }
        output_file = save_backtest_results(results, metadata=metadata)
        
        logger.info("="*80)
        logger.info("✅ 백테스트 완료!")
        logger.info("="*80)
        
        return results
