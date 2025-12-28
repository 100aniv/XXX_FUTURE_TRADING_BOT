"""
PHASE36-2 S8-FIX: LiveProof 모듈
================================
실제 LIVE 주문 증거 수집 (exchange_order_id 검증)

목적:
- 주문 제출 시 exchange_order_id 확보
- 주문 직후 REST로 조회해서 "존재 확인" 저장
- 종료 시 MyTrades/OrderHistory로 재조회 증거 저장
- 위 증거 없으면 FAIL
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LiveProof:
    """실제 LIVE 주문 증거 수집"""
    
    def __init__(self):
        self.submitted_orders: List[Dict] = []
        self.verified_orders: List[Dict] = []
        self.account_snapshot_start: Optional[Dict] = None
        self.account_snapshot_end: Optional[Dict] = None
        self.run_id: str = ""
    
    def set_run_id(self, run_id: str):
        """실행 ID 설정"""
        self.run_id = run_id
    
    def set_account_snapshot_start(self, snapshot: Dict):
        """시작 시점 계정 스냅샷 저장 (마스킹)"""
        masked = {
            'totalWalletBalance': snapshot.get('totalWalletBalance', 0),
            'availableBalance': snapshot.get('availableBalance', 0),
            'timestamp': datetime.now().isoformat()
        }
        self.account_snapshot_start = masked
        logger.info(f"✅ [LiveProof] 계정 스냅샷 저장 (시작): ${masked['totalWalletBalance']}")
    
    def set_account_snapshot_end(self, snapshot: Dict):
        """종료 시점 계정 스냅샷 저장 (마스킹)"""
        masked = {
            'totalWalletBalance': snapshot.get('totalWalletBalance', 0),
            'availableBalance': snapshot.get('availableBalance', 0),
            'timestamp': datetime.now().isoformat()
        }
        self.account_snapshot_end = masked
        logger.info(f"✅ [LiveProof] 계정 스냅샷 저장 (종료): ${masked['totalWalletBalance']}")
    
    def record_order_submitted(self, order_result: Dict):
        """
        주문 제출 기록
        
        Args:
            order_result: broker.execute() 반환값
                {
                    'success': bool,
                    'filled_price': float,
                    'qty': float,
                    'value': float,
                    'fee': float,
                    'timestamp': datetime,
                    'order_id': int or str  ← exchange_order_id
                }
        """
        if not order_result.get('success'):
            logger.warning(f"⚠️ [LiveProof] 주문 실패: {order_result.get('error')}")
            return
        
        exchange_order_id = order_result.get('order_id')
        if not exchange_order_id:
            logger.error("❌ [LiveProof] exchange_order_id 없음 - LIVE 주문 증거 불완전")
            return
        
        record = {
            'clientOrderId': f"LIVE_{self.run_id}_{len(self.submitted_orders)}",
            'exchange_order_id': exchange_order_id,
            'symbol': order_result.get('symbol', 'UNKNOWN'),
            'side': order_result.get('side', 'UNKNOWN'),
            'qty': order_result.get('qty', 0),
            'price': order_result.get('filled_price', 0),
            'status': 'SUBMITTED',
            'verified_by_rest': False,
            'timestamp': datetime.now().isoformat()
        }
        
        self.submitted_orders.append(record)
        logger.info(f"✅ [LiveProof] 주문 기록: {record['clientOrderId']} (exchange_id={exchange_order_id})")
    
    def record_order_verified(self, clientOrderId: str, exchange_order_id: int, status: str):
        """
        주문 검증 기록 (REST 조회 성공)
        
        Args:
            clientOrderId: 클라이언트 주문 ID
            exchange_order_id: 거래소 주문 ID
            status: 주문 상태 ('FILLED', 'PARTIALLY_FILLED', 'PENDING', etc.)
        """
        verified = {
            'clientOrderId': clientOrderId,
            'exchange_order_id': exchange_order_id,
            'status': status,
            'verified_by_rest': True,
            'verified_timestamp': datetime.now().isoformat()
        }
        
        self.verified_orders.append(verified)
        logger.info(f"✅ [LiveProof] 주문 검증 완료: {clientOrderId} → {status}")
    
    def to_json(self) -> Dict:
        """
        증거 JSON 생성
        
        Returns:
            {
                'run_id': str,
                'account_snapshot_start': dict,
                'account_snapshot_end': dict,
                'submitted_orders': list,
                'verified_orders': list,
                'summary': {
                    'total_submitted': int,
                    'total_verified': int,
                    'verification_rate': float,
                    'pass_fail': 'PASS' | 'FAIL'
                }
            }
        """
        total_submitted = len(self.submitted_orders)
        total_verified = len(self.verified_orders)
        verification_rate = (total_verified / total_submitted * 100) if total_submitted > 0 else 0
        
        # PASS 조건: 최소 1건 이상 제출 + 100% 검증
        pass_fail = 'PASS' if (total_submitted > 0 and verification_rate == 100.0) else 'FAIL'
        
        return {
            'run_id': self.run_id,
            'account_snapshot_start': self.account_snapshot_start,
            'account_snapshot_end': self.account_snapshot_end,
            'submitted_orders': self.submitted_orders,
            'verified_orders': self.verified_orders,
            'summary': {
                'total_submitted': total_submitted,
                'total_verified': total_verified,
                'verification_rate_pct': round(verification_rate, 2),
                'pass_fail': pass_fail,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def save_to_file(self, filepath: str):
        """증거 JSON 파일 저장"""
        data = self.to_json()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ [LiveProof] 증거 저장: {filepath}")


# 글로벌 싱글톤
_live_proof_instance: Optional[LiveProof] = None


def get_live_proof() -> LiveProof:
    """LiveProof 싱글톤 반환"""
    global _live_proof_instance
    if _live_proof_instance is None:
        _live_proof_instance = LiveProof()
    return _live_proof_instance


def reset_live_proof():
    """LiveProof 리셋 (테스트용)"""
    global _live_proof_instance
    _live_proof_instance = None
