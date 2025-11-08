#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Interfaces (Protocol-based Contracts)
===========================================
FlowGuardian 및 모듈 간 계약 정의

목적:
- 타입 안정성 및 계약 명시화
- 기존 모듈을 어댑터로 래핑하여 연결
- 새 구현 추가 시 계약 준수 강제

제약:
- 이 파일 변경 시 PR 제안 필수 (.windsurfrules)
- 시그니처는 최소/안정 형태 유지
- 기존 모듈 로직 변경 금지
"""
from typing import Protocol, Any, Dict, Literal
import pandas as pd


class IDataSource(Protocol):
    """
    데이터 소스 계약
    
    구현 대상:
    - execution/data_sources/backtest.py::BacktestDataSource (골든 CSV)
    - collectors/rest_collector.py::fetch_history (REST API)
    """
    
    def fetch(self, candle_range: Dict[str, Any]) -> pd.DataFrame:
        """
        캔들 데이터 조회
        
        Args:
            candle_range: {"symbol": str, "tf": str, "limit": int, ...}
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        
        Raises:
            Exception: 데이터 수집 실패 시
        """
        ...


class IStrategy(Protocol):
    """
    전략 계약
    
    구현 대상:
    - signals/signal_generator.py::SignalGenerator (단일 전략 모드)
    - strategies/*.py::signal_logic 래퍼
    """
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        시그널 생성
        
        Args:
            df: 캔들 데이터 (timestamp, open, high, low, close, volume)
        
        Returns:
            {
                "signal": str,  # "BUY", "SELL", "HOLD"
                "confidence": float,  # 0.0~1.0
                "order_intent": Dict[str, Any] | None,  # 주문 의도
                ...
            }
        
        Raises:
            Exception: 시그널 생성 실패 시
        """
        ...


class IRisk(Protocol):
    """
    리스크 관리 계약
    
    구현 대상:
    - execution/risk_manager.py::RiskManager
    """
    
    def assess(self, order_intent: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
        """
        리스크 평가 및 주문 조정
        
        Args:
            order_intent: {
                "symbol": str,
                "side": str,  # "BUY" or "SELL"
                "quantity": float,
                "price": float,
                ...
            }
            account: {
                "balance": float,
                "positions": Dict[str, Any],
                ...
            }
        
        Returns:
            {
                "allowed": bool,  # True: 허용, False: 차단
                "reason": str,  # 차단 사유 (allowed=False 시)
                "adjusted_intent": Dict[str, Any] | None,  # 조정된 주문 의도
                ...
            }
        
        Raises:
            Exception: 평가 실패 시
        """
        ...


class IBroker(Protocol):
    """
    브로커/실행자 계약 (시뮬/페이퍼 겸용)
    
    구현 대상:
    - execution/executors/simulation.py::SimulationExecutor
    - execution/executors/paper.py::PaperExecutor
    - execution/adapters/brokers.py::PaperBroker
    - execution/adapters/brokers.py::LiveBroker
    
    참고:
    - 일부 문맥에서 IExecutor로 지칭
    - dry_run: 시뮬레이션 실행 (게이트용)
    - place: 실제 주문 (PAPER/LIVE용)
    - get_account_balance: 계좌 자산 조회 (PR12)
    - sync_equity_with_exchange: 자산 동기화 (PR12)
    """
    
    def dry_run(self, order_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        주문 시뮬레이션 (실제 체결 없이 결과 계산)
        
        Args:
            order_intent: {
                "symbol": str,
                "side": str,
                "quantity": float,
                "price": float,
                "sl": float,
                "tp": float,
                ...
            }
        
        Returns:
            {
                "filled": bool,
                "fill_price": float,
                "pnl": float,
                "commission": float,
                ...
            }
        
        Raises:
            Exception: 시뮬레이션 실패 시
        """
        ...
    
    def place(self, order_intent: Dict[str, Any]) -> str:
        """
        실제 주문 배치 (PAPER/LIVE 모드)
        
        Args:
            order_intent: 주문 의도
        
        Returns:
            order_id: 주문 ID
        
        Raises:
            Exception: 주문 실패 시
        """
        ...
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        계정 자산 조회 (PR12)
        
        Returns:
            {
                "success": bool,
                "balances": List[Dict[str, Any]],  # [{"asset": "USDT", "balance": "1000.00", ...}, ...]
            }
        
        Raises:
            Exception: 조회 실패 시
        """
        ...
    
    def sync_equity_with_exchange(self) -> float:
        """
        거래소 자산과 동기화 (PR12)
        
        Returns:
            float: 현재 가용 USDT 자산
        
        Raises:
            Exception: 동기화 실패 시
        """
        ...


class IMetrics(Protocol):
    """
    메트릭 계산 계약
    
    구현 대상:
    - metrics/compute.py::MetricsEngine (신규)
    """
    
    def compute(self, trade_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        거래 메트릭 계산
        
        Args:
            trade_log: {
                "trades": List[Dict],  # 거래 내역
                "sim": Dict[str, Any],  # 시뮬 결과 (선택)
                "intent": Dict[str, Any],  # 주문 의도 (선택)
                ...
            }
        
        Returns:
            {
                "profit_factor": float,  # 총이익/총손실
                "winrate": float,  # 승률 (0.0~1.0)
                "exp_score": float,  # 기대값 점수
                "score_total": float,  # 종합 점수
                "total_trades": int,  # 총 거래 수
                ...
            }
        
        Raises:
            Exception: 계산 실패 시
        """
        ...


class IPortfolio(Protocol):
    """
    포트폴리오 관리자 계약 (PR12)
    
    구현 대상:
    - execution/portfolio_manager.py::PortfolioManager
    
    목적:
    - 중앙 집중식 자산(equity) 관리
    - PnL 통합 관리 (daily, total, realized, unrealized)
    - 포지션 노출 및 분산 관리
    - 브로커와 자산 동기화
    """
    
    def get_equity(self) -> float:
        """
        현재 자본 반환
        
        Returns:
            float: 현재 자본 (USDT)
        """
        ...
    
    def update_equity(self, new_equity: float = None, pnl: float = None) -> None:
        """
        자본 업데이트 (단일 소스)
        
        Args:
            new_equity: 새 자본 직접 설정 (둘 중 하나만 제공)
            pnl: PnL 증감분 (둘 중 하나만 제공)
        
        Raises:
            ValueError: new_equity와 pnl이 모두 None이거나 모두 제공된 경우
        """
        ...
    
    def update_pnl(self, pnl: float, realized: bool = True) -> None:
        """
        PnL 업데이트
        
        Args:
            pnl: 손익 (USDT)
            realized: 실현 여부 (True=실현, False=미실현)
        """
        ...
    
    def get_daily_pnl(self) -> float:
        """
        일일 누적 PnL 반환
        
        Returns:
            float: 일일 누적 PnL (USDT)
        """
        ...
    
    def get_total_pnl(self) -> float:
        """
        전체 누적 PnL 반환
        
        Returns:
            float: 전체 누적 PnL (USDT)
        """
        ...
    
    def reset_daily(self) -> None:
        """
        일일 PnL 리셋 (자정)
        """
        ...
    
    def check_and_reset_daily(self) -> None:
        """
        날짜 체크 및 일일 PnL 자동 리셋
        """
        ...
    
    def sync_equity_with_broker(self, broker: Any) -> None:
        """
        브로커와 자산 동기화 (Live 모드)
        
        Args:
            broker: 브로커 객체 (IBroker 구현체)
        """
        ...


class IFlowGuardian(Protocol):
    """
    FlowGuardian 게이트 계약 (.windsurfrules 준수)
    
    목적:
    - READY 플래그 없이는 PAPER/LIVE 실행 불가
    - config.yml 유효성, DB/Redis 헬스체크, 계약 불변 조건 검증
    
    구현 대상:
    - core/flow_guardian.py::FlowGuardian
    """
    
    def ready(self) -> bool:
        """
        READY 상태 판정
        
        검증 항목:
        - config.yml 유효성 (필수 키 존재/타입 체크)
        - DB·Redis 헬스체크 (선택)
        - 전략/튜닝 계약 불변 조건 일치
        - 최근 테스트 타임스탬프 신선도 확인 (옵션)
        
        Returns:
            bool: READY 상태 (True=준비됨, False=미준비)
        """
        ...
    
    def assert_ready(self, mode: Literal["paper", "live"]) -> None:
        """
        READY 상태 강제 검증
        
        Args:
            mode: 실행 모드 ("paper" | "live")
            
        Raises:
            RuntimeError: READY 미준수 시 예외 발생
            ValueError: 잘못된 모드
        """
        ...
