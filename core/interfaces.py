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
    
    참고:
    - 일부 문맥에서 IExecutor로 지칭
    - dry_run: 시뮬레이션 실행 (게이트용)
    - place: 실제 주문 (PAPER/LIVE용)
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
