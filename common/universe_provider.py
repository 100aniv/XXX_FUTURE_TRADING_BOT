#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universe Provider - PHASE26-0
==============================
TopN 심볼 선정 인프라 (Multi-Symbol 준비)

Design Principles:
    - Single Responsibility: 심볼 선정 + 필터링만 담당
    - Protocol-based: Duck Typing 지원, 유연한 확장
    - Async-first: API 호출 비동기 처리
    - Cache-aware: TTL 기반 캐싱으로 API 부하 최소화
"""
from dataclasses import dataclass, field
from typing import Protocol, List, Optional, Dict, Any
from datetime import datetime
import logging

from common.logger import setup_logger

logger = setup_logger(__name__)


# ========================================
# 1. Core Types
# ========================================

@dataclass
class SymbolInfo:
    """
    심볼 메타데이터 (거래소 스펙 포함)
    
    Attributes:
        symbol: 심볼명 (예: BTCUSDT)
        base_asset: 기초 자산 (예: BTC)
        quote_asset: 견적 자산 (예: USDT)
        exchange: 거래소 이름 (기본: binance)
        price_precision: 가격 정밀도
        quantity_precision: 수량 정밀도
        min_qty: 최소 주문 수량
        max_qty: 최대 주문 수량
        step_size: 수량 단위
        is_futures: 선물 여부
        is_margin_enabled: 마진 활성화 여부
        contract_type: 계약 타입 (PERPETUAL | DELIVERY)
        volume_24h_usdt: 24시간 거래량 (USDT)
        price: 현재 가격
    """
    symbol: str
    base_asset: str
    quote_asset: str
    exchange: str = "binance"
    
    # 거래소 스펙
    price_precision: int = 2
    quantity_precision: int = 3
    min_qty: float = 0.001
    max_qty: float = 10000.0
    step_size: float = 0.001
    
    # 마켓 타입
    is_futures: bool = True
    is_margin_enabled: bool = True
    contract_type: str = "PERPETUAL"
    
    # 메트릭 (선택)
    volume_24h_usdt: Optional[float] = None
    price: Optional[float] = None


@dataclass
class UniverseFilterConfig:
    """
    Universe 필터링 설정
    
    Attributes:
        quote_assets: 허용할 견적 자산 (기본: USDT만)
        exclude_symbols: 블랙리스트 (제외할 심볼)
        min_24h_volume_usd: 최소 24h 거래량 (USDT)
        market_types: 허용할 계약 타입 (기본: PERPETUAL만)
        contract_status: 계약 상태 (기본: TRADING만)
    """
    quote_assets: List[str] = field(default_factory=lambda: ["USDT"])
    exclude_symbols: List[str] = field(default_factory=list)
    min_24h_volume_usd: float = 0.0
    market_types: List[str] = field(default_factory=lambda: ["PERPETUAL"])
    contract_status: str = "TRADING"


@dataclass
class UniverseProviderConfig:
    """
    UniverseProvider 설정
    
    Attributes:
        provider_type: 제공자 타입 (topn_volume | static | db_metrics)
        top_n: TopN 개수
        filters: 필터링 설정
        static_symbols: Static Provider용 심볼 리스트
        cache_ttl_sec: 캐시 TTL (초)
    """
    provider_type: str
    top_n: int = 10
    filters: UniverseFilterConfig = field(default_factory=UniverseFilterConfig)
    static_symbols: List[str] = field(default_factory=list)
    cache_ttl_sec: int = 3600  # 1시간


# ========================================
# 2. Protocol (Interface)
# ========================================

class UniverseProvider(Protocol):
    """
    Universe Provider 인터페이스 (Protocol-based)
    
    모든 Universe Provider는 이 인터페이스를 구현해야 함.
    Protocol 사용 이유:
        - Duck Typing 지원 (ABC보다 유연)
        - 점진적 마이그레이션 가능
        - 테스트 Mock 용이
    """
    
    async def get_universe(self) -> List[SymbolInfo]:
        """
        현재 Universe (심볼 리스트) 반환
        
        Returns:
            List[SymbolInfo]: 필터링 + 정렬된 심볼 리스트
        
        Raises:
            ValueError: 설정 오류
            RuntimeError: API 호출 실패 등
        """
        ...
    
    def get_config(self) -> UniverseProviderConfig:
        """현재 설정 반환"""
        ...


# ========================================
# 3. Concrete Implementations
# ========================================

class StaticUniverseProvider:
    """
    정적 심볼 리스트 제공자 (테스트/Fallback용)
    
    Usage:
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=["BTCUSDT", "ETHUSDT"]
        )
        provider = StaticUniverseProvider(config)
        universe = await provider.get_universe()
    """
    
    def __init__(self, config: UniverseProviderConfig):
        if config.provider_type != "static":
            raise ValueError(f"Invalid provider_type: {config.provider_type}, expected 'static'")
        
        self.config = config
        self.logger = setup_logger(f"{__name__}.StaticUniverseProvider")
    
    async def get_universe(self) -> List[SymbolInfo]:
        """정적 심볼 리스트 반환"""
        symbols = self.config.static_symbols
        
        if not symbols:
            self.logger.warning("⚠️ StaticUniverseProvider: 빈 심볼 리스트")
            return []
        
        # SymbolInfo 객체로 변환 (최소 정보만)
        result = []
        for symbol in symbols:
            # Exclude 필터 적용
            if symbol in self.config.filters.exclude_symbols:
                self.logger.debug(f"   Excluded: {symbol}")
                continue
            
            # 간단한 파싱 (USDT 기준)
            base_asset = symbol.replace("USDT", "")
            
            result.append(SymbolInfo(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset="USDT",
                exchange="binance"
            ))
        
        self.logger.info(f"✅ StaticUniverseProvider: {len(result)}개 심볼")
        return result
    
    def get_config(self) -> UniverseProviderConfig:
        return self.config


class TopNByVolumeUniverseProvider:
    """
    거래량 상위 N개 심볼 제공자 (Binance API 기반)
    
    Features:
        - 24h Volume 기준 TopN 선택
        - 필터링: quote_asset, volume, market_type, exclude_list
        - 정렬: quoteVolume 내림차순
        - 캐싱: TTL 기반 (API 부하 최소화)
    
    Usage:
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=10,
            filters=UniverseFilterConfig(
                quote_assets=["USDT"],
                min_24h_volume_usd=10_000_000,
                exclude_symbols=["BTCDOWNUSDT"]
            )
        )
        provider = TopNByVolumeUniverseProvider(config)
        universe = await provider.get_universe()
    """
    
    TICKER_24H_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    
    def __init__(self, config: UniverseProviderConfig):
        if config.provider_type != "topn_volume":
            raise ValueError(f"Invalid provider_type: {config.provider_type}, expected 'topn_volume'")
        
        self.config = config
        self.logger = setup_logger(f"{__name__}.TopNByVolumeUniverseProvider")
        
        # 캐시
        self._cache: Optional[List[SymbolInfo]] = None
        self._cache_time: Optional[datetime] = None
    
    async def get_universe(self) -> List[SymbolInfo]:
        """
        거래량 상위 N개 심볼 조회 + 필터링
        
        Flow:
            1. 캐시 체크 (TTL 확인)
            2. Binance 24h Ticker API 호출
            3. 필터링 (quote_asset, volume, exclude_list)
            4. 정렬 (volume 기준 내림차순)
            5. Top N 선택
            6. Exchange Info로 SymbolInfo 보강
            7. 캐시 업데이트
        """
        # 1. 캐시 체크
        if self._is_cache_valid():
            self.logger.debug("✅ Cache hit (Universe)")
            return self._cache
        
        self.logger.info("🔍 Fetching TopN Universe from Binance API...")
        
        # 2. 24h Ticker 조회
        try:
            tickers = await self._fetch_24h_ticker()
        except Exception as e:
            self.logger.error(f"❌ Binance 24h Ticker 조회 실패: {e}")
            return self._get_fallback_universe()
        
        # 3. 필터링
        filters = self.config.filters
        filtered_tickers = []
        
        for t in tickers:
            symbol = t['symbol']
            
            # 필터 1: quote_asset
            if not any(symbol.endswith(qa) for qa in filters.quote_assets):
                continue
            
            # 필터 2: exclude_list
            if symbol in filters.exclude_symbols:
                self.logger.debug(f"   Excluded: {symbol}")
                continue
            
            # 필터 3: volume
            try:
                volume = float(t['quoteVolume'])
            except (KeyError, ValueError):
                continue
            
            if volume < filters.min_24h_volume_usd:
                continue
            
            filtered_tickers.append(t)
        
        self.logger.info(f"   Filtered: {len(filtered_tickers)}개 심볼 (조건 충족)")
        
        # 4. 정렬 (volume 기준 내림차순)
        filtered_tickers.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        
        # 5. Top N 선택
        top_n_tickers = filtered_tickers[:self.config.top_n]
        self.logger.info(f"   Top {self.config.top_n} 선택: {len(top_n_tickers)}개 심볼")
        
        # 6. Exchange Info 조회 (SymbolInfo 보강)
        try:
            exchange_info = await self._fetch_exchange_info()
            symbol_info_map = {s['symbol']: s for s in exchange_info.get('symbols', [])}
        except Exception as e:
            self.logger.warning(f"⚠️ Exchange Info 조회 실패, 기본값 사용: {e}")
            symbol_info_map = {}
        
        result = []
        for t in top_n_tickers:
            symbol = t['symbol']
            info = symbol_info_map.get(symbol, {})
            
            # market_type 필터 (PERPETUAL만 or 전체)
            contract_type = info.get('contractType', 'PERPETUAL')
            if filters.market_types and contract_type not in filters.market_types:
                self.logger.debug(f"   Excluded by market_type: {symbol} ({contract_type})")
                continue
            
            # contract_status 필터
            status = info.get('status', 'TRADING')
            if status != filters.contract_status:
                self.logger.debug(f"   Excluded by status: {symbol} ({status})")
                continue
            
            # SymbolInfo 생성
            result.append(SymbolInfo(
                symbol=symbol,
                base_asset=info.get('baseAsset', symbol.replace('USDT', '')),
                quote_asset=info.get('quoteAsset', 'USDT'),
                exchange="binance",
                price_precision=info.get('pricePrecision', 2),
                quantity_precision=info.get('quantityPrecision', 3),
                min_qty=self._get_min_qty(info),
                max_qty=self._get_max_qty(info),
                step_size=self._get_step_size(info),
                is_futures=True,
                is_margin_enabled=True,
                contract_type=contract_type,
                volume_24h_usdt=float(t.get('quoteVolume', 0)),
                price=float(t.get('lastPrice', 0))
            ))
        
        # 7. 캐시 업데이트
        self._cache = result
        self._cache_time = datetime.now()
        
        self.logger.info(f"✅ TopN Universe: {len(result)}개 심볼 (Top {self.config.top_n})")
        if result:
            top_5 = [f"{s.symbol}(${s.volume_24h_usdt/1e6:.1f}M)" for s in result[:5]]
            self.logger.info(f"   상위 5: {', '.join(top_5)}")
        
        return result
    
    async def _fetch_24h_ticker(self) -> List[Dict[str, Any]]:
        """Binance 24h Ticker API 호출"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.TICKER_24H_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            self.logger.error(f"❌ 24h Ticker API 호출 실패: {e}")
            raise
    
    async def _fetch_exchange_info(self) -> Dict[str, Any]:
        """Binance Exchange Info API 호출 (심볼 스펙 조회)"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.EXCHANGE_INFO_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            self.logger.error(f"❌ Exchange Info API 호출 실패: {e}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 체크 (TTL 기반)"""
        if self._cache is None or self._cache_time is None:
            return False
        
        elapsed_sec = (datetime.now() - self._cache_time).total_seconds()
        is_valid = elapsed_sec < self.config.cache_ttl_sec
        
        if not is_valid:
            self.logger.debug(f"   Cache expired ({elapsed_sec:.0f}s > {self.config.cache_ttl_sec}s)")
        
        return is_valid
    
    def _get_min_qty(self, info: Dict) -> float:
        """최소 수량 추출 (filters[1] = LOT_SIZE)"""
        try:
            filters = info.get('filters', [])
            for f in filters:
                if f.get('filterType') == 'LOT_SIZE':
                    return float(f['minQty'])
            # Fallback: filters[1]
            return float(filters[1]['minQty'])
        except (KeyError, IndexError, ValueError, TypeError):
            return 0.001
    
    def _get_max_qty(self, info: Dict) -> float:
        """최대 수량 추출"""
        try:
            filters = info.get('filters', [])
            for f in filters:
                if f.get('filterType') == 'LOT_SIZE':
                    return float(f['maxQty'])
            return float(filters[1]['maxQty'])
        except (KeyError, IndexError, ValueError, TypeError):
            return 10000.0
    
    def _get_step_size(self, info: Dict) -> float:
        """수량 단위 추출"""
        try:
            filters = info.get('filters', [])
            for f in filters:
                if f.get('filterType') == 'LOT_SIZE':
                    return float(f['stepSize'])
            return float(filters[1]['stepSize'])
        except (KeyError, IndexError, ValueError, TypeError):
            return 0.001
    
    def _get_fallback_universe(self) -> List[SymbolInfo]:
        """Fallback: 기본 심볼 리스트 (API 실패 시)"""
        fallback_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.logger.warning(f"⚠️ Fallback Universe: {fallback_symbols}")
        
        return [
            SymbolInfo(
                symbol=s,
                base_asset=s.replace("USDT", ""),
                quote_asset="USDT",
                exchange="binance"
            )
            for s in fallback_symbols
        ]
    
    def get_config(self) -> UniverseProviderConfig:
        return self.config


# ========================================
# 4. Factory Function
# ========================================

def create_universe_provider(config: UniverseProviderConfig) -> UniverseProvider:
    """
    UniverseProvider Factory
    
    Args:
        config: UniverseProviderConfig
    
    Returns:
        UniverseProvider: 구체 구현체
    
    Raises:
        ValueError: 지원하지 않는 provider_type
    
    Example:
        >>> config = UniverseProviderConfig(provider_type="topn_volume", top_n=10)
        >>> provider = create_universe_provider(config)
        >>> universe = await provider.get_universe()
    """
    if config.provider_type == "static":
        return StaticUniverseProvider(config)
    elif config.provider_type == "topn_volume":
        return TopNByVolumeUniverseProvider(config)
    else:
        raise ValueError(
            f"Unsupported provider_type: {config.provider_type}. "
            f"Supported: 'static', 'topn_volume'"
        )
