#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 매니저
=================
멀티 심볼 환경에서 포트폴리오 수준의 리스크 관리

주요 기능:
1. 심볼별 exposure 제한
2. 전략별 budget 배분
3. 동시 포지션 수 제어
4. 집중도 리스크 관리
"""
from typing import Dict, List, Optional, Any
from collections import defaultdict
import time
from datetime import datetime
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class PortfolioManager:
    """
    포트폴리오 수준 리스크 관리자
    
    멀티 심볼 환경에서:
    - 심볼별 최대 exposure 제한
    - 전략별 budget 배분
    - 동시 포지션 수 제어
    """
    
    def __init__(self, config: Dict, load_existing: bool = True):
        """
        초기화
        
        Args:
            config: 전체 설정 (config.yml)
            load_existing: 기존 OPEN 포지션 로드 여부 (backtest=False, paper/live=True)
        """
        self.config = config
        self.load_existing = load_existing
        
        # 기본 설정 (필수 파라미터 - config.yml 필수)
        self.equity = config['capital']['initial']
        self.max_positions = config['risk']['max_positions']
        self.max_exposure_per_symbol = config['risk'].get('max_exposure_per_symbol', 0.3)  # 기본 30%
        
        # 포트폴리오 설정 (필수)
        self.max_total_exposure = config['portfolio']['max_total_exposure']
        self.max_strategy_positions = config['portfolio']['max_strategy_positions']  # 기본값
        
        # ⭐ PR8: 동적 설정 활성화 플래그
        self.use_dynamic_exposure = config.get('portfolio', {}).get('use_dynamic_exposure', True)
        self.use_dynamic_budget = config.get('portfolio', {}).get('use_dynamic_budget', True)
        
        # ⭐ PHASE8-2b: 현재 상태 추적 (backtest 모드에서는 빈 상태로 시작)
        self.positions: Dict[str, List[Dict]] = defaultdict(list)  # {symbol: [positions]}
        self.strategy_positions: Dict[str, int] = defaultdict(int)  # {strategy: count}
        
        # ⭐ PHASE8-2b: 기존 포지션 로드 (paper/live에서만)
        if load_existing:
            self._load_existing_positions()
        else:
            logger.info("🔒 [BACKTEST] 기존 포지션 로드 스킵 (완전 격리 모드)")
        
        # ⭐ PR8: 심볼별 쿨다운 (거부 후 반복 시도 방지)
        self.symbol_cooldown: Dict[str, float] = {}  # {symbol: last_reject_time}
        self.cooldown_seconds = config.get('portfolio', {}).get('symbol_cooldown_seconds', 60)  # 기본 60초
        
        # ⭐ PR12: PnL 추적 추가
        self.initial_equity = self.equity
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # ⭐ PR12: 전략별 예산 및 상관관계 가드 설정
        portfolio_cfg = config.get('portfolio', {})
        
        # 전략별 예산 설정
        budget_cfg = portfolio_cfg.get('budget', {})
        self.strategy_budget = budget_cfg.get('strategy_allocation', {})  # {전략ID: 비율}
        self.default_budget_pct = budget_cfg.get('default_allocation', 0.2)  # 기본 20%
        
        # 상관관계 가드 설정
        correlation_cfg = portfolio_cfg.get('correlation', {})
        self.max_correlation = correlation_cfg.get('max_pair_corr', 0.7)  # 기본 0.7
        self.correlation_window = correlation_cfg.get('window', 30)  # 기본 30일
        self.use_correlation_guard = correlation_cfg.get('enabled', False)  # 기본 비활성화
        
        # 심볼 갖 상관관계 캐시
        self.correlation_cache = {}  # {(symbol1, symbol2): correlation}
        self.correlation_timestamp = time.time()
        self.correlation_ttl = 3600  # 1시간 캐시 유효기간
        
        logger.info(f"✅ PortfolioManager 초기화: Equity=${self.equity:,.0f}, Max Positions={self.max_positions}, Max Exposure/Symbol={self.max_exposure_per_symbol*100:.0f}%, Max Total={self.max_total_exposure*100:.0f}%, Symbol Cooldown={self.cooldown_seconds}s")
    
    def can_open_position(
        self,
        symbol: str,
        strategy: str,
        position_value: float,
        side: str
    ) -> tuple[bool, str]:
        """
        새 포지션 시작 가능 여부 검사
        
        Args:
            symbol: 심볼 (BTCUSDT)
            strategy: 전략 ID
            position_value: 포지션 가치 (USD)
            side: 방향 ("LONG" | "SHORT")
            
        Returns:
            (allowed, reason): 허용 여부와 사유
        """
        equity = self.equity
        
        # 1. 심볼 쿨다운 여부 검사 (⭐ PHASE16+: 0 = 비활성화)
        if self.cooldown_seconds > 0 and symbol in self.symbol_cooldown:
            cooldown_end = self.symbol_cooldown[symbol] + self.cooldown_seconds
            now = time.time()
            
            if now < cooldown_end:
                remaining = int(cooldown_end - now)
                return False, f"심볼 {symbol} 쿨다운 중: {remaining}초 남음"
        
        # 2. 포지션 최대 수 검사 (⭐ PHASE16+: 0 = 무제한)
        if self.max_positions > 0 and len(self.get_all_positions()) >= self.max_positions:
            return False, f"포지션 최대 한강 도달: {self.max_positions}개"
        
        # 3. 심볼별 exposure 체크
        symbol_exposure = self._get_symbol_exposure(symbol)
        new_symbol_exposure = (symbol_exposure + position_value) / equity
        if new_symbol_exposure > self.max_exposure_per_symbol:
            return False, f"{symbol} exposure 초과 ({new_symbol_exposure*100:.1f}% > {self.max_exposure_per_symbol*100:.0f}%)"
        
        # 4. 전체 포트폴리오 exposure 체크
        total_exposure = self._get_total_exposure()
        new_total_exposure = (total_exposure + position_value) / self.equity
        
        if new_total_exposure > self.max_total_exposure:
            return False, f"총 exposure 초과 ({new_total_exposure*100:.1f}% > {self.max_total_exposure*100:.0f}%)"
        
        # 5. 전략별 포지션 수 체크
        if self.strategy_positions[strategy] >= self.max_strategy_positions:
            return False, f"{strategy} 최대 포지션 도달 ({self.strategy_positions[strategy]}/{self.max_strategy_positions})"
        
        # 6. ⭐ PR12: 전략별 예산 한도 검사
        strategy_budget = self.calculate_strategy_budget(strategy)
        strategy_exposure = 0.0
        
        # 동일 전략의 기존 포지션 가치 합계
        for pos_list in self.positions.values():
            for pos in pos_list:
                if pos.get('strategy') == strategy:
                    strategy_exposure += pos.get('value', 0)
        
        # 새 포지션 추가 후 전략 노출 예산
        new_strategy_exposure = strategy_exposure + position_value
        if new_strategy_exposure > strategy_budget:
            return False, f"전략 예산 초과: {strategy} ${new_strategy_exposure:,.2f} > ${strategy_budget:,.2f}"
        
        # 7. ⭐ PR12: 상관관계 가드 검사
        if self.use_correlation_guard:
            allowed, reason = self.check_correlation_guard(symbol)
            if not allowed:
                return False, reason
        
        return True, "OK"
    
    def add_position(
        self,
        symbol: str,
        strategy: str,
        position_value: float,
        side: str,
        position_id: str
    ):
        """
        포지션 추가
        
        Args:
            symbol: 심볼
            strategy: 전략 이름
            position_value: 포지션 가치
            side: LONG | SHORT
            position_id: 포지션 ID
        """
        position = {
            'id': position_id,
            'symbol': symbol,
            'strategy': strategy,
            'value': position_value,
            'side': side
        }
        
        self.positions[symbol].append(position)
        self.strategy_positions[strategy] += 1
        
        # 로그
        total_positions = sum(len(p) for p in self.positions.values())
        total_exposure = self._get_total_exposure()
        exposure_pct = total_exposure / self.equity * 100
        
        logger.info(f"📊 포트폴리오 상태: 총 포지션={total_positions}/{self.max_positions}, 총 exposure={exposure_pct:.1f}% (${total_exposure:,.0f}), {strategy}={self.strategy_positions[strategy]}/{self.max_strategy_positions}개")
    
    def remove_position(self, symbol: str, position_id: str):
        """
        포지션 제거
        
        Args:
            symbol: 심볼
            position_id: 포지션 ID
        """
        if symbol not in self.positions:
            return
        
        # 해당 포지션 찾기
        for i, pos in enumerate(self.positions[symbol]):
            if pos['id'] == position_id:
                strategy = pos['strategy']
                self.positions[symbol].pop(i)
                self.strategy_positions[strategy] -= 1
                
                # 빈 리스트 정리
                if not self.positions[symbol]:
                    del self.positions[symbol]
                
                logger.info(f"📉 포지션 제거: {symbol} ({strategy})")
                break
    
    def _get_symbol_exposure(self, symbol: str) -> float:
        """심볼별 현재 exposure (USDT)"""
        if symbol not in self.positions:
            return 0.0
        return sum(pos['value'] for pos in self.positions[symbol])
    
    def _get_total_exposure(self) -> float:
        """총 exposure (모든 포지션 가치 합)"""
        total = 0.0
        for positions in self.positions.values():
            total += sum(pos['value'] for pos in positions)
        return total

    def get_all_positions(self) -> List[Dict]:
        """모든 포지션 목록 반환"""
        all_positions = []
        for positions in self.positions.values():
            all_positions.extend(positions)
        return all_positions
    
    def get_stats(self) -> Dict:
        """
        포트폴리오 통계
        
        Returns:
            dict: 통계 정보
        """
        total_positions = sum(len(p) for p in self.positions.values())
        total_exposure = self._get_total_exposure()
        exposure_pct = total_exposure / self.equity * 100 if self.equity > 0 else 0
        
        # 심볼별 통계
        symbol_stats = {}
        for symbol, positions in self.positions.items():
            symbol_exposure = sum(pos['value'] for pos in positions)
            symbol_stats[symbol] = {
                'count': len(positions),
                'exposure': symbol_exposure,
                'exposure_pct': symbol_exposure / self.equity * 100
            }
        
        # 전략별 통계
        strategy_stats = dict(self.strategy_positions)
        
        return {
            'total_positions': total_positions,
            'max_positions': self.max_positions,
            'total_exposure': total_exposure,
            'total_exposure_pct': exposure_pct,
            'symbols': symbol_stats,
            'strategies': strategy_stats
        }
    
    def get_equity(self) -> float:
        """현재 자본 반환"""
        return self.equity
        
    def update_pnl(self, pnl: float, realized: bool = True):
        """PnL 업데이트"""
        if realized:
            self.realized_pnl += pnl
            self.daily_pnl += pnl
            self.total_pnl += pnl
            
            # Equity 업데이트
            old_equity = self.equity
            self.equity = max(0.0, self.equity + pnl)
            
            if abs(pnl) > 0.01:  # 유의미한 변화만 로그
                logger.info(f"💰 PnL 업데이트: ${pnl:+,.2f}, Daily: ${self.daily_pnl:+,.2f}, Total: ${self.total_pnl:+,.2f}, Equity: ${old_equity:,.2f} → ${self.equity:,.2f}")
        else:
            self.unrealized_pnl = pnl
    
    def get_daily_pnl(self) -> float:
        """일일 누적 PnL 반환"""
        return self.daily_pnl
    
    def get_total_pnl(self) -> float:
        """전체 누적 PnL 반환"""
        return self.total_pnl
    
    def reset_daily(self):
        """일일 리셋 (자정)"""
        logger.info(f"📅 일일 PnL 리셋: ${self.daily_pnl:+,.2f} → $0.00")
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def check_and_reset_daily(self):
        """날짜 체크 및 자동 리셋"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.reset_daily()
    
    def sync_equity_with_broker(self, broker: Any) -> float:
        """
        브로커와 자산 동기화 (Live 모드에서만 의미)
        
        Args:
            broker: PaperBroker 또는 LiveBroker
            
        Returns:
            float: 동기화 후 자산값
        """
        # 기존 자산 값 기록
        initial_equity = self.equity
        logger.debug(f"\u23f3 [PORTFOLIO] 자산 동기화 시도: 현재=${initial_equity:,.2f} USDT")
        
        if hasattr(broker, 'sync_equity_with_exchange'):
            try:
                # 거래소 API 통한 자산 조회
                exchange_equity = broker.sync_equity_with_exchange()
                
                if exchange_equity > 0:
                    # 유의미한 변화가 있을 때만 동기화
                    if abs(exchange_equity - self.equity) > 0.01:
                        logger.info(f"\u2705 [PORTFOLIO] 자산 동기화: ${self.equity:,.2f} \u2192 ${exchange_equity:,.2f} USDT")
                        self.equity = exchange_equity
                    else:
                        logger.debug(f"\u2139\ufe0f [PORTFOLIO] 자산 동기화 불필요: 변화량=${abs(exchange_equity - self.equity):,.2f} USDT")
                else:
                    logger.warning(f"\u26a0\ufe0f [PORTFOLIO] 거래소 잔고 없음 (API 값: ${exchange_equity:,.2f})")
                    
                return exchange_equity
                    
            except Exception as e:
                logger.error(f"\u274c [PORTFOLIO] 자산 동기화 실패: {e}")
        else:
            logger.warning(f"\u26a0\ufe0f [PORTFOLIO] 브로커에 'sync_equity_with_exchange' 기능 없음")
        
        return self.equity  # 변경 없음
                
    def calculate_strategy_budget(self, strategy_id: str) -> float:
        """
        ⭐ PR12: 전략별 예산 한도 계산
        
        Args:
            strategy_id: 전략 ID
            
        Returns:
            float: 전략 예산 한도 (USD 값)
        """
        equity = self.equity
        
        # 전략별 예산 할당
        if strategy_id in self.strategy_budget:
            budget_pct = self.strategy_budget[strategy_id]
        else:
            # 기본 비율 사용
            budget_pct = self.default_budget_pct
            
        # 전략별 예산 = 자산 * 할당 비율
        budget = equity * budget_pct
        
        logger.info(f"💰 전략 예산: {strategy_id} = ${budget:,.2f} ({budget_pct*100:.1f}%)")
        return budget
        
    def check_correlation_guard(self, new_symbol: str) -> tuple[bool, str]:
        """
        ⭐ PR12: 심볼 간 상관관계 가드
        
        Args:
            new_symbol: 새로 추가하려는 심볼
            
        Returns:
            (allowed, reason): 허용 여부와 사유
        """
        # 가드 비활성화된 경우 허용
        if not self.use_correlation_guard:
            return True, "OK"
            
        # 기존 포지션이 없으면 허용
        if not self.positions:
            return True, "OK"
            
        # 현재 활성 심볼 목록
        active_symbols = list(self.positions.keys())
        if not active_symbols:
            return True, "OK"
            
        # 고상관 심볼 검색
        high_corr_symbols = []
        
        for symbol in active_symbols:
            # 동일 심볼 제외
            if symbol == new_symbol:
                continue
                
            # 상관관계 계산 (or 캐시 사용)
            corr = self._get_correlation(symbol, new_symbol)
            
            # 상관관계 가드 체크
            if abs(corr) > self.max_correlation:
                high_corr_symbols.append(f"{symbol} ({corr:.2f})")
        
        # 고상관 심볼이 있으면 차단
        if high_corr_symbols:
            reason = f"상관관계 가드: {new_symbol}은 {', '.join(high_corr_symbols)}와 고상관"
            return False, reason
        
        return True, "OK"
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        두 심볼 간의 상관관계 계산 (캐시 지원)
        
        Args:
            symbol1: 첫번째 심볼
            symbol2: 두번째 심볼
            
        Returns:
            float: -1.0 ~ +1.0 범위의 상관계수
        """
        # 기본값 (API 접근 불가능 시)
        default_corr = 0.0
        
        # 캐시 키 생성 (알파벳 순)
        key = tuple(sorted([symbol1, symbol2]))
        current_time = time.time()
        
        # 캐시 데이터 확인
        if key in self.correlation_cache:
            cache_time, corr = self.correlation_cache[key]
            
            # TTL 내 캐시 데이터 사용
            if current_time - cache_time < self.correlation_ttl:
                return corr
        
        # ⭐ TODO: 실제 API 호출 필요 (PR12 후 분리 구현)
        try:
            # 임의의 테스트 값 (병렬 테스트용)
            import random
            corr = random.uniform(-0.8, 0.8)
            
            # 캐시 업데이트
            self.correlation_cache[key] = (current_time, corr)
            return corr
            
        except Exception as e:
            logger.warning(f"⚠️ 상관관계 계산 실패: {e}")
            return default_corr
    
    def update_equity(self, new_equity: float = None, pnl: float = None):
        """
        자본 업데이트 (단일 소스)
        
        Args:
            new_equity: 새로운 자본 (직접 설정)
            pnl: PnL (증감분)
            
        Raises:
            ValueError: new_equity와 pnl이 모두 None이거나 모두 제공된 경우
        """
        if new_equity is not None and pnl is not None:
            raise ValueError("new_equity와 pnl 중 하나만 제공해야 합니다")
            
        if new_equity is not None:
            old_equity = self.equity
            self.equity = max(0.0, new_equity)
            
            if abs(self.equity - old_equity) > 0.01:
                logger.info(f"💰 Equity 설정: ${old_equity:,.0f} → ${new_equity:,.0f}")
        
        elif pnl is not None:
            self.update_pnl(pnl, realized=True)
        
        else:
            raise ValueError("new_equity 또는 pnl 중 하나는 제공해야 합니다")
    
    # =========================================================================
    # ⭐ PR8: 동적 설정 계산
    # =========================================================================
    
    def calculate_dynamic_exposure(self, symbol: str, atr_pct: float = None) -> float:
        """
        변동성 기반 동적 Exposure 한도 계산
        
        Args:
            symbol: 심볼
            atr_pct: ATR % (변동성)
        
        Returns:
            해당 심볼의 최대 exposure % (0~1)
        
        Example:
            >>> pm.calculate_dynamic_exposure('BTCUSDT', 0.01)  # 저변동성
            0.4  # 40% 허용
            
            >>> pm.calculate_dynamic_exposure('ALTCOIN', 0.05)  # 고변동성
            0.2  # 20% 제한
        """
        if not self.use_dynamic_exposure or atr_pct is None:
            return self.max_exposure_per_symbol  # 기본값
        
        base_exposure = self.max_exposure_per_symbol  # 기본 30%
        
        # 변동성 구간별 조정
        if atr_pct > 0.03:  # 고변동성 (3%+)
            mult = 0.7  # 20% (30% × 0.7)
        elif atr_pct < 0.01:  # 저변동성 (1% 미만)
            mult = 1.3  # 40% (30% × 1.3)
        else:  # 중간 변동성
            mult = 1.0  # 30%
        
        dynamic_exposure = base_exposure * mult
        logger.debug(f"📊 [{symbol}] 동적 Exposure: {dynamic_exposure*100:.0f}% (ATR {atr_pct*100:.2f}%, mult={mult})")
        
        return min(dynamic_exposure, 0.5)  # 최대 50%
    
    def calculate_strategy_positions(self, strategy: str, performance: dict = None) -> int:
        """
        전략 성과 기반 동적 최대 포지션 수 계산
        
        Args:
            strategy: 전략 이름
            performance: {'sharpe': float, 'winrate': float, 'trades': int}
        
        Returns:
            해당 전략의 최대 포지션 수
        
        Example:
            >>> pm.calculate_strategy_positions('scalping', {'sharpe': 1.5, 'winrate': 0.65})
            5  # 우수한 전략
            
            >>> pm.calculate_strategy_positions('weak', {'sharpe': 0.3, 'winrate': 0.45})
            1  # 약한 전략
        """
        if not self.use_dynamic_budget or performance is None:
            return self.max_strategy_positions  # 기본값
        
        base_positions = self.max_strategy_positions  # 기본 5개
        
        sharpe = performance.get('sharpe', 0)
        winrate = performance.get('winrate', 0.5)
        trades = performance.get('trades', 0)
        
        # 1. Sharpe 기준
        if sharpe > 1.5:
            sharpe_mult = 1.5  # 우수
        elif sharpe > 1.0:
            sharpe_mult = 1.2  # 좋음
        elif sharpe > 0.5:
            sharpe_mult = 1.0  # 보통
        else:
            sharpe_mult = 0.5  # 약함
        
        # 2. Winrate 기준
        if winrate > 0.6:
            wr_mult = 1.2
        elif winrate > 0.5:
            wr_mult = 1.0
        else:
            wr_mult = 0.8
        
        # 3. 샘플 신뢰도
        if trades < 30:
            sample_mult = 0.7  # 샘플 부족
        else:
            sample_mult = 1.0
        
        # 최종 계산
        total_mult = (sharpe_mult + wr_mult) / 2 * sample_mult
        dynamic_positions = int(base_positions * total_mult)
        
        # 범위 제한 (1~10)
        dynamic_positions = max(1, min(dynamic_positions, 10))
        
        logger.debug(f"📊 [{strategy}] 동적 Budget: {dynamic_positions}개 (Sharpe={sharpe:.2f}, WR={winrate*100:.0f}%, mult={total_mult:.2f})")
        
        return dynamic_positions
    
    def _load_existing_positions(self):
        """
        DB에서 OPEN 상태의 포지션을 로드하여 portfolio.positions에 추가
        paper/live 모드에서만 호출됨 (backtest에서는 스킵)
        """
        try:
            from common.database import get_db_connection
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # mode와 상관없이 모든 OPEN 거래 조회 (paper/live 구분 안 함)
                    cur.execute("""
                        SELECT trade_id, symbol, strategy_id, side, entry_price, 
                               quantity, leverage, ts_open, sl_price, tp_price, 
                               mode, pnl, pnl_pct
                        FROM trading.trades
                        WHERE status = 'OPEN'
                        ORDER BY ts_open ASC
                    """)
                    
                    rows = cur.fetchall()
                    
                    if not rows:
                        logger.info("✅ 기존 OPEN 포지션 없음")
                        return
                    
                    # 각 row를 positions에 추가
                    for row in rows:
                        trade_id, symbol, strategy_id, side, entry_price, quantity, \
                            leverage, ts_open, sl_price, tp_price, mode, pnl, pnl_pct = row
                        
                        position = {
                            'id': trade_id,  # ⭐ PHASE9 FIX: remove_position과 일관성 유지
                            'trade_id': trade_id,
                            'symbol': symbol,
                            'strategy': strategy_id,
                            'side': side,
                            'entry_price': float(entry_price) if entry_price else 0,
                            'quantity': float(quantity) if quantity else 0,
                            'leverage': int(leverage) if leverage else 1,
                            'value': float(entry_price * quantity) if entry_price and quantity else 0,
                            'ts_open': ts_open,
                            'sl_price': float(sl_price) if sl_price else None,
                            'tp_price': float(tp_price) if tp_price else None,
                            'mode': mode,
                            'pnl': float(pnl) if pnl else 0,
                            'pnl_pct': float(pnl_pct) if pnl_pct else 0
                        }
                        
                        self.positions[symbol].append(position)
                        self.strategy_positions[strategy_id] += 1
                    
                    logger.info(f"✅ 기존 OPEN 포지션 로드: {len(rows)}개")
                    
                    # 심볼별 포지션 수 로그
                    for symbol, pos_list in self.positions.items():
                        logger.info(f"  - {symbol}: {len(pos_list)}개 ({', '.join([p['strategy'] for p in pos_list])})")
                        
        except Exception as e:
            logger.warning(f"⚠️ 기존 포지션 로드 실패 (계속 진행): {e}")


if __name__ == '__main__':
    # 테스트
    config = {
        'capital': {'initial': 10000},
        'risk': {
            'max_positions': 5,
            'max_exposure_per_symbol': 0.3
        },
        'portfolio': {
            'max_total_exposure': 0.8,
            'max_strategy_positions': 3,
            'max_correlated_positions': 2
        }
    }
    
    pm = PortfolioManager(config)
    
    # 테스트 1: 첫 포지션
    can_open, reason = pm.can_open_position('BTCUSDT', 'scalping', 2000, 'LONG')
    print(f"Test 1: {can_open}, {reason}")
    
    if can_open:
        pm.add_position('BTCUSDT', 'scalping', 2000, 'LONG', 'pos1')
    
    # 테스트 2: 같은 심볼
    can_open, reason = pm.can_open_position('BTCUSDT', 'daytrade', 2000, 'LONG')
    print(f"Test 2: {can_open}, {reason}")
    
    # 통계
    stats = pm.get_stats()
    print(f"\n📊 Stats: {stats}")
