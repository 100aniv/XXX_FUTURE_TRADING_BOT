#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Symbol Manager
==============
Binance REST API로 거래 가능한 모든 심볼 자동 로드
"""
import requests
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SymbolManager:
    """Binance 심볼 관리 클래스"""
    
    # Binance Futures API
    FUTURES_EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    
    def __init__(self):
        self.all_symbols: List[str] = []
        self.symbol_info: Dict = {}
    
    def fetch_all_usdt_symbols(self, min_volume_24h: float = 1000000) -> List[str]:
        """
        USDT 선물 심볼 전체 로드
        
        Args:
            min_volume_24h: 최소 24시간 거래량 (USDT 기준)
        
        Returns:
            List[str]: 심볼 리스트 (예: ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            logger.info("🔍 Binance Futures 심볼 조회 중...")
            
            # Exchange Info 요청
            response = requests.get(self.FUTURES_EXCHANGE_INFO_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # USDT 선물만 필터링
            usdt_symbols = []
            
            for symbol_data in data['symbols']:
                symbol = symbol_data['symbol']
                
                # USDT로 끝나는 선물 계약만
                if (symbol.endswith('USDT') and 
                    symbol_data['status'] == 'TRADING' and
                    symbol_data['contractType'] == 'PERPETUAL'):
                    
                    # 심볼 정보 저장
                    self.symbol_info[symbol] = {
                        'baseAsset': symbol_data['baseAsset'],
                        'quoteAsset': symbol_data['quoteAsset'],
                        'pricePrecision': symbol_data['pricePrecision'],
                        'quantityPrecision': symbol_data['quantityPrecision'],
                        'minQty': float(symbol_data['filters'][1]['minQty']),
                        'maxQty': float(symbol_data['filters'][1]['maxQty']),
                        'stepSize': float(symbol_data['filters'][1]['stepSize']),
                    }
                    
                    usdt_symbols.append(symbol)
            
            # 정렬
            usdt_symbols.sort()
            
            self.all_symbols = usdt_symbols
            
            logger.info(f"✅ {len(usdt_symbols)}개 USDT 선물 심볼 로드 완료")
            logger.info(f"   예시: {', '.join(usdt_symbols[:10])}...")
            
            return usdt_symbols
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Binance API 요청 실패: {e}")
            # 기본값 반환
            return self._get_default_symbols()
        except Exception as e:
            logger.error(f"❌ 심볼 로드 실패: {e}")
            return self._get_default_symbols()
    
    def fetch_top_volume_symbols(self, top_n: int = 50) -> List[str]:
        """
        거래량 상위 N개 심볼 로드
        
        Args:
            top_n: 상위 N개
        
        Returns:
            List[str]: 심볼 리스트
        """
        try:
            logger.info(f"🔍 거래량 상위 {top_n}개 심볼 조회 중...")
            
            # 24시간 티커 정보 요청
            ticker_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            response = requests.get(ticker_url, timeout=10)
            response.raise_for_status()
            tickers = response.json()
            
            # USDT 선물만 필터링 & 거래량 기준 정렬
            usdt_tickers = [
                t for t in tickers 
                if t['symbol'].endswith('USDT')
            ]
            
            # 거래량(USDT) 기준 정렬
            usdt_tickers.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
            
            # 상위 N개
            top_symbols = [t['symbol'] for t in usdt_tickers[:top_n]]
            
            logger.info(f"✅ 거래량 상위 {len(top_symbols)}개 심볼 로드 완료")
            logger.info(f"   상위 10: {', '.join(top_symbols[:10])}")
            
            return top_symbols
            
        except Exception as e:
            logger.error(f"❌ 상위 심볼 로드 실패: {e}")
            return self._get_default_symbols()
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """심볼 상세 정보 조회"""
        return self.symbol_info.get(symbol, {})
    
    def _get_default_symbols(self) -> List[str]:
        """기본 심볼 (API 실패 시)"""
        default = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'LTCUSDT',
            'LINKUSDT', 'AVAXUSDT', 'ATOMUSDT', 'UNIUSDT', 'ETCUSDT',
            'XLMUSDT', 'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'FILUSDT'
        ]
        logger.warning(f"⚠️  기본 심볼 사용: {len(default)}개")
        return default


# 전역 인스턴스
symbol_manager = SymbolManager()


def get_all_symbols(mode: str = "top50") -> List[str]:
    """
    거래 가능한 심볼 리스트 반환
    
    Args:
        mode: "all" (전체), "top50" (상위 50개), "top100" (상위 100개)
    
    Returns:
        List[str]: 심볼 리스트
    """
    if mode == "all":
        return symbol_manager.fetch_all_usdt_symbols()
    elif mode == "top50":
        return symbol_manager.fetch_top_volume_symbols(50)
    elif mode == "top100":
        return symbol_manager.fetch_top_volume_symbols(100)
    else:
        return symbol_manager.fetch_top_volume_symbols(50)


def load_symbols_from_config(config: dict) -> List[str]:
    """
    설정 기반 심볼 로딩 (main.py 로직 모듈화)
    
    Args:
        config: 전체 설정 딕셔너리
    
    Returns:
        심볼 리스트 (가드레일 적용 후)
    
    Examples:
        >>> from common.config_loader import load_config
        >>> from common.symbol_manager import load_symbols_from_config
        >>> config = load_config()
        >>> symbols = load_symbols_from_config(config)
        ['BTCUSDT', 'ETHUSDT', ...]
    """
    symbols_config = config.get('symbols', {})
    
    # 방어: symbols가 list면 dict로 변환
    if isinstance(symbols_config, list):
        symbols_config = {'manual': symbols_config, 'mode': 'manual'}
    elif not isinstance(symbols_config, dict):
        symbols_config = {}
    
    symbol_mode = symbols_config.get('mode', 'manual')
    
    logger.info(f"📥 심볼 로딩 시작: mode={symbol_mode}")
    
    # 모드별 심볼 로드
    if symbol_mode == 'manual':
        symbols = symbols_config.get('manual', ['BTCUSDT'])
        logger.info(f"✅ Manual 모드: {len(symbols)}개 심볼")
    
    elif symbol_mode == 'top50':
        logger.info("📊 Top50 심볼 조회 중...")
        symbols = symbol_manager.fetch_top_volume_symbols(50)
        # core 심볼 추가
        core = symbols_config.get('core', [])
        symbols = list(set(core + symbols))
        logger.info(f"✅ Top50 모드: {len(symbols)}개 심볼 로드 완료")
    
    elif symbol_mode == 'top100':
        logger.info("📊 Top100 심볼 조회 중...")
        symbols = symbol_manager.fetch_top_volume_symbols(100)
        core = symbols_config.get('core', [])
        symbols = list(set(core + symbols))
        logger.info(f"✅ Top100 모드: {len(symbols)}개 심볼 로드 완료")
    
    elif symbol_mode == 'all':
        logger.info("📊 전체 USDT 심볼 조회 중...")
        symbols = symbol_manager.fetch_all_usdt_symbols()
        core = symbols_config.get('core', [])
        symbols = list(set(core + symbols))
        logger.info(f"✅ All 모드: {len(symbols)}개 심볼 로드 완료")
    
    else:
        symbols = ['BTCUSDT']
        logger.warning(f"⚠️ 알 수 없는 모드 '{symbol_mode}', BTCUSDT 사용")
    
    # 가드레일: 최대 스트림 수 제한 (Binance WebSocket 제한)
    max_streams = symbols_config.get('max_streams', 50)
    if len(symbols) > max_streams:
        logger.warning(f"⚠️ 심볼 {len(symbols)}개 → {max_streams}개로 제한 (Binance WebSocket 제한)")
        symbols = symbols[:max_streams]
    
    logger.info(f"📊 최종 심볼: {len(symbols)}개 (예: {', '.join(symbols[:5])}...)")
    
    return symbols


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    print("="*60)
    print("Symbol Manager 테스트")
    print("="*60)
    
    # 상위 50개
    symbols = get_all_symbols("top50")
    print(f"\n✅ {len(symbols)}개 심볼 로드")
    print(f"상위 20개: {symbols[:20]}")
