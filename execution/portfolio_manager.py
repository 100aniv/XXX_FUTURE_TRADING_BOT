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
from typing import Dict, List, Optional
from collections import defaultdict
import time
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
    
    def __init__(self, config: Dict):
        """
        초기화
        
        Args:
            config: 전체 설정 (config.yml)
        """
        self.config = config
        
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
        
        # 현재 상태 추적
        self.positions: Dict[str, List[Dict]] = defaultdict(list)  # {symbol: [positions]}
        self.strategy_positions: Dict[str, int] = defaultdict(int)  # {strategy: count}
        
        # ⭐ PR8: 심볼별 쿨다운 (거부 후 반복 시도 방지)
        self.symbol_cooldown: Dict[str, float] = {}  # {symbol: last_reject_time}
        self.cooldown_seconds = config.get('portfolio', {}).get('symbol_cooldown_seconds', 60)  # 기본 60초
        
        logger.info(f"✅ PortfolioManager 초기화: Equity=${self.equity:,.0f}, Max Positions={self.max_positions}, Max Exposure/Symbol={self.max_exposure_per_symbol*100:.0f}%, Max Total={self.max_total_exposure*100:.0f}%, Symbol Cooldown={self.cooldown_seconds}s")
    
    def can_open_position(
        self,
        symbol: str,
        strategy: str,
        position_value: float,
        side: str
    ) -> tuple[bool, str]:
        """
        포지션 진입 가능 여부 확인
        
        Args:
            symbol: 심볼 (BTCUSDT)
            strategy: 전략 이름 (scalping)
            position_value: 포지션 가치 (USDT)
            side: LONG | SHORT
            
        Returns:
            (가능 여부, 사유)
        """
        # 0. ⭐ PR8: 심볼별 쿨다운 체크 (거부 후 반복 시도 방지)
        if symbol in self.symbol_cooldown:
            elapsed = time.time() - self.symbol_cooldown[symbol]
            if elapsed < self.cooldown_seconds:
                remaining = int(self.cooldown_seconds - elapsed)
                return False, f"{symbol} 쿨다운 중 ({remaining}초 남음)"
            else:
                # 쿨다운 종료
                del self.symbol_cooldown[symbol]
                logger.info(f"✅ [{symbol}] 쿨다운 해제")
        
        # 1. 동일 심볼 중복 진입 완전 차단 (추매/헤지 로직 없음)
        logger.debug(f"🔍 [{symbol}] 포지션 체크: {symbol in self.positions}, 개수: {len(self.positions.get(symbol, []))}")
        if symbol in self.positions and len(self.positions[symbol]) > 0:
            logger.warning(f"⛔ [{symbol}] 이미 포지션 보유 중: {len(self.positions[symbol])}개")
            return False, f"{symbol} 이미 포지션 보유 중 (중복 진입 불가)"
        
        # 2. 최대 포지션 수 체크
        total_positions = sum(len(positions) for positions in self.positions.values())
        if total_positions >= self.max_positions:
            return False, f"최대 포지션 수 도달 ({total_positions}/{self.max_positions})"
        
        # 3. 심볼별 exposure 체크
        symbol_exposure = self._get_symbol_exposure(symbol)
        new_symbol_exposure = (symbol_exposure + position_value) / self.equity
        
        if new_symbol_exposure > self.max_exposure_per_symbol:
            # ⭐ PR8: 거부 시 쿨다운 설정
            self.symbol_cooldown[symbol] = time.time()
            logger.warning(f"⛔ [{symbol}] 쿨다운 설정 ({self.cooldown_seconds}초): exposure 초과")
            return False, f"{symbol} exposure 초과 ({new_symbol_exposure*100:.1f}% > {self.max_exposure_per_symbol*100:.0f}%)"
        
        # 4. 전체 포트폴리오 exposure 체크
        total_exposure = self._get_total_exposure()
        new_total_exposure = (total_exposure + position_value) / self.equity
        
        if new_total_exposure > self.max_total_exposure:
            return False, f"총 exposure 초과 ({new_total_exposure*100:.1f}% > {self.max_total_exposure*100:.0f}%)"
        
        # 5. 전략별 포지션 수 체크
        if self.strategy_positions[strategy] >= self.max_strategy_positions:
            return False, f"{strategy} 최대 포지션 도달 ({self.strategy_positions[strategy]}/{self.max_strategy_positions})"
        
        # 상관성 체크 제거: 심볼 선택은 symbol_manager에서 이미 처리 (manual/top50/top100/all)
        # max_positions로 전체 포지션 수 제한으로 충분
        
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
    
    def update_equity(self, new_equity: float):
        """자본 업데이트 (PnL 반영)"""
        old_equity = self.equity
        self.equity = max(0.0, new_equity)
        
        if abs(new_equity - old_equity) > 0.01:
            logger.info(f"💰 Equity 업데이트: ${old_equity:,.0f} → ${new_equity:,.0f}")
    
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
    
    def calculate_strategy_budget(self, strategy: str, performance: dict = None) -> int:
        """
        전략 성과 기반 동적 Budget (최대 포지션 수) 계산
        
        Args:
            strategy: 전략 이름
            performance: {'sharpe': float, 'winrate': float, 'trades': int}
        
        Returns:
            해당 전략의 최대 포지션 수
        
        Example:
            >>> pm.calculate_strategy_budget('scalping', {'sharpe': 1.5, 'winrate': 0.65})
            5  # 우수한 전략
            
            >>> pm.calculate_strategy_budget('weak', {'sharpe': 0.3, 'winrate': 0.45})
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
