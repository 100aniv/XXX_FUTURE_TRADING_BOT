#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trade Manager - 매매 오케스트레이터
==================================
⚠️  리팩토링 완료: execution/ 모듈로 분리됨

이 파일은 더 이상 사용되지 않습니다.
새로운 구조:
- execution/executor.py: TradingExecutor 클래스
- execution/position_sizer.py: PositionSizer 클래스
- execution/risk_manager.py: RiskManager 클래스
- execution/position_tracker.py: PositionTracker 클래스
- execution/manager.py: 매매 오케스트레이션 함수들

실행 방법:
1. run_trading.py 사용
2. 또는 main_trading.py 스크립트 작성

참고: docs/implementation/EXECUTION_MODULE_REFACTORING.md
"""
import os
import sys
import time
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

# ⚠️  리팩토링 완료: 아래 import는 더 이상 사용되지 않습니다
# 새로운 경로: from execution import TradingExecutor, PositionTracker, PositionSizer, RiskManager
from trading_executor import TradingExecutor, PositionTracker, PositionSizer, RiskManager

# ============================================
# 0. LOGGING (로그 설정) - 공통 모듈 사용
# ============================================
from common.logger import setup_logger
logger = setup_logger(__name__, log_type="trading")

# ============================================
# 1. DATABASE (공통 모듈 사용)
# ============================================
from common.database import get_db_connection, test_db_connection

# DB 연결 테스트
test_db_connection()


# ============================================
# 2. TRADING BOT (매매 실행 봇)
# ============================================
# 리팩토링 시: execution/manager.py로 분리 완료
# - TradingBot 클래스 → 순수 함수들로 변환
# - fetch_signals() → fetch_ensemble_decisions(), fetch_strategy_signals()
# - process_signals() → process_trades()
# - _convert_to_order() → convert_to_order()
# - _save_trade() → save_trade()
# - _mark_as_executed() → mark_as_executed()
# - run() 메서드의 while 루프 → 실행 스크립트로 이동 (run_trading.py)
# ============================================
class TradingBot:
    """
    매매 실행 봇
    - 전략 선택
    - 신호/결정 읽기
    - 주문 실행
    - DB 저장
    """
    
    def __init__(self):
        """초기화"""
        # 전략 선택
        self.strategy = os.getenv('STRATEGY_SELECTOR', 'ensemble')
        
        # Trading Executor 초기화
        mode = os.getenv('TRADING_MODE', 'backtest')
        api_key = os.getenv('BINANCE_API_KEY')
        secret = os.getenv('BINANCE_SECRET')
        
        self.executor = TradingExecutor(mode=mode, binance_api_key=api_key, binance_secret=secret)
        
        logger.info(f"✅ Trading Bot 초기화 완료")
        logger.info(f"   전략: {self.strategy}")
        logger.info(f"   모드: {mode}")
    
    # ============================================
    # 3. SIGNAL FETCHING (신호 조회)
    # ============================================
    
    def fetch_signals(self) -> List[Dict]:
        """
        선택한 전략의 신호 가져오기
        """
        if self.strategy == 'ensemble':
            return self.fetch_ensemble_decisions()
        else:
            return self.fetch_strategy_signals(self.strategy)
    
    def fetch_ensemble_decisions(self) -> List[Dict]:
        """
        앙상블 통합 결정 조회
        """
        sql = """
        SELECT 
            decision_id, symbol, timeframe, candle_closed_at,
            chosen_side, final_score, created_at
        FROM trading.decisions
        WHERE executed_at IS NULL
          AND chosen_side != 'FLAT'
        ORDER BY created_at ASC
        LIMIT 10
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    decisions = cur.fetchall()
                    
                    if decisions:
                        logger.info(f"📥 앙상블 결정 {len(decisions)}개 조회")
                    
                    return decisions
        except Exception as e:
            logger.error(f"❌ 앙상블 결정 조회 실패: {e}")
            return []
    
    def fetch_strategy_signals(self, strategy_id: str) -> List[Dict]:
        """
        특정 전략 신호 조회
        """
        sql = """
        SELECT 
            signal_id, strategy_id, symbol, timeframe, candle_closed_at,
            direction, confidence, entry_price, sl_price, tp_price,
            atr, leverage, created_at
        FROM monitoring.signals
        WHERE strategy_id = %s
          AND created_at > NOW() - INTERVAL '24 hours'
          AND direction != 'FLAT'
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql, (strategy_id,))
                    signals = cur.fetchall()
                    
                    if signals:
                        logger.info(f"📥 {strategy_id} 신호 {len(signals)}개 조회")
                    
                    return signals
        except Exception as e:
            logger.error(f"❌ {strategy_id} 신호 조회 실패: {e}")
            return []
    
    # ============================================
    # 4. ORDER EXECUTION (주문 실행)
    # ============================================
    
    def process_signals(self):
        """
        신호 처리 및 주문 실행
        """
        signals = self.fetch_signals()
        
        if not signals:
            return
        
        for signal in signals:
            try:
                # 신호 → 주문 변환
                order_signal = self._convert_to_order(signal)
                
                if not order_signal:
                    continue
                
                # 주문 실행
                order = self.executor.execute_order(order_signal)
                
                if order:
                    # DB 저장
                    self._save_trade(signal, order)
                    
                    # 실행 완료 표시
                    self._mark_as_executed(signal)
                    
            except Exception as e:
                logger.error(f"❌ 신호 처리 실패: {e}")
    
    def _convert_to_order(self, signal: Dict) -> Optional[Dict]:
        """
        신호를 주문 형식으로 변환
        """
        if self.strategy == 'ensemble':
            # 앙상블 결정
            # decisions 테이블에는 entry/sl/tp가 없으므로
            # 현재 가격 기준으로 계산 필요 (TODO)
            logger.warning("⚠️  앙상블 결정은 현재 entry/sl/tp 계산 필요 (구현 예정)")
            return None
        else:
            # 개별 전략 신호
            return {
                'symbol': signal['symbol'],
                'side': signal['direction'],
                'entry_price': float(signal['entry_price']),
                'sl_price': float(signal['sl_price']),
                'tp_price': float(signal['tp_price']),
                'confidence': float(signal.get('confidence', 0.8))
            }
    
    def _save_trade(self, signal: Dict, order: Dict):
        """
        거래 결과를 DB에 저장
        """
        sql = """
        INSERT INTO trading.trades (
            trade_id, strategy_id, symbol, side,
            entry_price, quantity, ts_open,
            leverage, status, created_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        trade_id = str(uuid4())
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        trade_id,
                        self.strategy,
                        order['symbol'],
                        order['side'],
                        order['fill_price'],
                        order['qty'],
                        order['timestamp'],
                        signal.get('leverage', 1),
                        'open',
                        datetime.now()
                    ))
                conn.commit()
                logger.info(f"💾 거래 저장 완료: {trade_id}")
        except Exception as e:
            logger.error(f"❌ 거래 저장 실패: {e}")
    
    def _mark_as_executed(self, signal: Dict):
        """
        신호/결정을 실행 완료로 표시
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if self.strategy == 'ensemble':
                        # decisions 테이블 업데이트
                        cur.execute("""
                            UPDATE trading.decisions
                            SET executed_at = %s
                            WHERE decision_id = %s
                        """, (datetime.now(), signal['decision_id']))
                    else:
                        # signals 테이블에는 executed_at 없음
                        # 대신 created_at으로 5분 이내만 조회하므로 자동 필터링됨
                        pass
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 실행 완료 표시 실패: {e}")
    
    # ============================================
    # 5. MAIN LOOP (메인 루프)
    # ============================================
    
    def run(self):
        """
        메인 실행 루프
        """
        logger.info("="*50)
        logger.info(f"Trading Bot 시작: {self.strategy}")
        logger.info("="*50)
        
        while True:
            try:
                self.process_signals()
                time.sleep(5)  # 5초마다 확인
            except KeyboardInterrupt:
                logger.info("⏹️  Trading Bot 종료")
                break
            except Exception as e:
                logger.error(f"❌ 메인 루프 에러: {e}")
                time.sleep(5)


# ============================================
# 6. MAIN (실행)
# ============================================
# 리팩토링 시: run_trading.py로 분리
# - if __name__ 블록 제거
# - while 루프는 실행 스크립트에서 관리
# ============================================
if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
