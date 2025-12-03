#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE26-0: Universe Provider Tests
===================================
Universe Provider 모듈 단위 테스트

Test Coverage:
    1. StaticUniverseProvider
    2. TopNByVolumeUniverseProvider (Mock API)
    3. UniverseProviderConfig validation
    4. create_universe_provider() factory
    5. load_universe_config() from YAML
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from common.universe_provider import (
    SymbolInfo,
    UniverseFilterConfig,
    UniverseProviderConfig,
    StaticUniverseProvider,
    TopNByVolumeUniverseProvider,
    create_universe_provider
)
from common.config_loader import load_universe_config


# ========================================
# 1. StaticUniverseProvider Tests
# ========================================

class TestStaticUniverseProvider:
    """StaticUniverseProvider 테스트"""
    
    def test_static_provider_basic(self):
        """기본 동작: 설정한 심볼 리스트 반환"""
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        )
        provider = StaticUniverseProvider(config)
        
        universe = asyncio.run(provider.get_universe())
        
        assert len(universe) == 3
        assert universe[0].symbol == "BTCUSDT"
        assert universe[0].base_asset == "BTC"
        assert universe[0].quote_asset == "USDT"
        assert universe[1].symbol == "ETHUSDT"
        assert universe[2].symbol == "BNBUSDT"
    
    def test_static_provider_exclude_filter(self):
        """Exclude 필터 적용"""
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            filters=UniverseFilterConfig(
                exclude_symbols=["ETHUSDT"]
            )
        )
        provider = StaticUniverseProvider(config)
        
        universe = asyncio.run(provider.get_universe())
        
        assert len(universe) == 2
        symbols = [s.symbol for s in universe]
        assert "BTCUSDT" in symbols
        assert "BNBUSDT" in symbols
        assert "ETHUSDT" not in symbols
    
    def test_static_provider_empty_list(self):
        """빈 리스트 처리"""
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=[]
        )
        provider = StaticUniverseProvider(config)
        
        universe = asyncio.run(provider.get_universe())
        
        assert len(universe) == 0
    
    def test_static_provider_invalid_type(self):
        """잘못된 provider_type 에러"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",  # Static이 아님
            static_symbols=["BTCUSDT"]
        )
        
        with pytest.raises(ValueError, match="Invalid provider_type"):
            StaticUniverseProvider(config)
    
    def test_static_provider_get_config(self):
        """get_config() 메서드"""
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=["BTCUSDT"]
        )
        provider = StaticUniverseProvider(config)
        
        returned_config = provider.get_config()
        
        assert returned_config == config
        assert returned_config.provider_type == "static"


# ========================================
# 2. TopNByVolumeUniverseProvider Tests
# ========================================

class TestTopNByVolumeUniverseProvider:
    """TopNByVolumeUniverseProvider 테스트 (Mock API)"""
    
    @pytest.fixture
    def mock_ticker_data(self) -> List[Dict[str, Any]]:
        """Mock 24h Ticker 데이터"""
        return [
            {"symbol": "BTCUSDT", "quoteVolume": "50000000000", "lastPrice": "42000"},
            {"symbol": "ETHUSDT", "quoteVolume": "20000000000", "lastPrice": "2200"},
            {"symbol": "BNBUSDT", "quoteVolume": "5000000000", "lastPrice": "300"},
            {"symbol": "SOLUSDT", "quoteVolume": "3000000000", "lastPrice": "100"},
            {"symbol": "XRPUSDT", "quoteVolume": "2000000000", "lastPrice": "0.5"},
            {"symbol": "BTCDOWNUSDT", "quoteVolume": "1000000000", "lastPrice": "10"},  # Leverage token
            {"symbol": "ADAUSDT", "quoteVolume": "1500000000", "lastPrice": "0.4"},
            {"symbol": "DOGEUSDT", "quoteVolume": "1200000000", "lastPrice": "0.08"},
        ]
    
    @pytest.fixture
    def mock_exchange_info(self) -> Dict[str, Any]:
        """Mock Exchange Info 데이터"""
        symbols = []
        for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "BTCDOWNUSDT", "ADAUSDT", "DOGEUSDT"]:
            symbols.append({
                "symbol": sym,
                "baseAsset": sym.replace("USDT", ""),
                "quoteAsset": "USDT",
                "status": "TRADING",
                "contractType": "PERPETUAL",
                "pricePrecision": 2,
                "quantityPrecision": 3,
                "filters": [
                    {},  # filters[0]
                    {  # filters[1] = LOT_SIZE
                        "filterType": "LOT_SIZE",
                        "minQty": "0.001",
                        "maxQty": "10000",
                        "stepSize": "0.001"
                    }
                ]
            })
        return {"symbols": symbols}
    
    def test_topn_provider_basic(self, mock_ticker_data, mock_exchange_info):
        """기본 동작: Top 5 선택"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=5
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        async def run_test():
            # Mock API 호출
            with patch.object(provider, '_fetch_24h_ticker', new=AsyncMock(return_value=mock_ticker_data)), \
                 patch.object(provider, '_fetch_exchange_info', new=AsyncMock(return_value=mock_exchange_info)):
                
                universe = await provider.get_universe()
            
            # Top 5 검증
            assert len(universe) == 5
            assert universe[0].symbol == "BTCUSDT"
            assert universe[1].symbol == "ETHUSDT"
            assert universe[2].symbol == "BNBUSDT"
            assert universe[3].symbol == "SOLUSDT"
            assert universe[4].symbol == "XRPUSDT"
            
            # Volume 정렬 확인
            assert universe[0].volume_24h_usdt > universe[1].volume_24h_usdt
        
        asyncio.run(run_test())
    
    def test_topn_provider_exclude_filter(self, mock_ticker_data, mock_exchange_info):
        """Exclude 필터 적용"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=3,
            filters=UniverseFilterConfig(
                exclude_symbols=["ETHUSDT", "BTCDOWNUSDT"]
            )
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        async def run_test():
            with patch.object(provider, '_fetch_24h_ticker', new=AsyncMock(return_value=mock_ticker_data)), \
                 patch.object(provider, '_fetch_exchange_info', new=AsyncMock(return_value=mock_exchange_info)):
                
                universe = await provider.get_universe()
            
            symbols = [s.symbol for s in universe]
            assert "ETHUSDT" not in symbols
            assert "BTCDOWNUSDT" not in symbols
            assert "BTCUSDT" in symbols
        
        asyncio.run(run_test())
    
    def test_topn_provider_volume_filter(self, mock_ticker_data, mock_exchange_info):
        """최소 거래량 필터"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=10,
            filters=UniverseFilterConfig(
                min_24h_volume_usd=3_000_000_000  # 30억 이상
            )
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        async def run_test():
            with patch.object(provider, '_fetch_24h_ticker', new=AsyncMock(return_value=mock_ticker_data)), \
                 patch.object(provider, '_fetch_exchange_info', new=AsyncMock(return_value=mock_exchange_info)):
                
                universe = await provider.get_universe()
            
            # 30억 이상: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT
            assert len(universe) == 4
            for s in universe:
                assert s.volume_24h_usdt >= 3_000_000_000
        
        asyncio.run(run_test())
    
    def test_topn_provider_cache(self, mock_ticker_data, mock_exchange_info):
        """캐시 동작 확인"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=3,
            cache_ttl_sec=3600  # 1시간
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        async def run_test():
            mock_fetch_ticker = AsyncMock(return_value=mock_ticker_data)
            mock_fetch_exchange = AsyncMock(return_value=mock_exchange_info)
            
            with patch.object(provider, '_fetch_24h_ticker', new=mock_fetch_ticker), \
                 patch.object(provider, '_fetch_exchange_info', new=mock_fetch_exchange):
                
                # 첫 호출: API 호출
                universe1 = await provider.get_universe()
                assert mock_fetch_ticker.call_count == 1
                
                # 두 번째 호출: 캐시 히트
                universe2 = await provider.get_universe()
                assert mock_fetch_ticker.call_count == 1  # 증가 안 함
                
                # 결과 동일
                assert len(universe1) == len(universe2)
                assert universe1[0].symbol == universe2[0].symbol
        
        asyncio.run(run_test())
    
    def test_topn_provider_api_failure_fallback(self):
        """API 실패 시 Fallback"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=3
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        async def run_test():
            # API 호출 실패 Mock
            with patch.object(provider, '_fetch_24h_ticker', side_effect=Exception("Network error")):
                universe = await provider.get_universe()
            
            # Fallback: 기본 심볼 (BTCUSDT, ETHUSDT, BNBUSDT)
            assert len(universe) == 3
            symbols = [s.symbol for s in universe]
            assert "BTCUSDT" in symbols
            assert "ETHUSDT" in symbols
            assert "BNBUSDT" in symbols
        
        asyncio.run(run_test())
    
    def test_topn_provider_invalid_type(self):
        """잘못된 provider_type 에러"""
        config = UniverseProviderConfig(
            provider_type="static",  # TopN이 아님
            top_n=10
        )
        
        with pytest.raises(ValueError, match="Invalid provider_type"):
            TopNByVolumeUniverseProvider(config)
    
    def test_topn_provider_get_config(self):
        """get_config() 메서드"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=10
        )
        provider = TopNByVolumeUniverseProvider(config)
        
        returned_config = provider.get_config()
        
        assert returned_config == config
        assert returned_config.top_n == 10


# ========================================
# 3. Factory Tests
# ========================================

class TestFactory:
    """create_universe_provider() 팩토리 테스트"""
    
    def test_factory_static(self):
        """Static Provider 생성"""
        config = UniverseProviderConfig(
            provider_type="static",
            static_symbols=["BTCUSDT"]
        )
        
        provider = create_universe_provider(config)
        
        assert isinstance(provider, StaticUniverseProvider)
    
    def test_factory_topn_volume(self):
        """TopN Volume Provider 생성"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=10
        )
        
        provider = create_universe_provider(config)
        
        assert isinstance(provider, TopNByVolumeUniverseProvider)
    
    def test_factory_unsupported_type(self):
        """지원하지 않는 provider_type"""
        config = UniverseProviderConfig(
            provider_type="db_metrics",  # 아직 미구현
            top_n=10
        )
        
        with pytest.raises(ValueError, match="Unsupported provider_type"):
            create_universe_provider(config)


# ========================================
# 4. Config Loading Tests
# ========================================

class TestConfigLoading:
    """load_universe_config() 테스트"""
    
    def test_load_universe_config_enabled(self):
        """universe.enabled=true일 때"""
        config_dict = {
            "universe": {
                "enabled": True,
                "provider": {
                    "type": "topn_volume",
                    "top_n": 15,
                    "cache_ttl_sec": 1800
                },
                "filters": {
                    "quote_assets": ["USDT", "BUSD"],
                    "exclude_symbols": ["BTCDOWNUSDT"],
                    "min_24h_volume_usd": 5000000
                }
            }
        }
        
        universe_cfg = load_universe_config(config_dict)
        
        assert universe_cfg is not None
        assert universe_cfg.provider_type == "topn_volume"
        assert universe_cfg.top_n == 15
        assert universe_cfg.cache_ttl_sec == 1800
        assert "USDT" in universe_cfg.filters.quote_assets
        assert "BUSD" in universe_cfg.filters.quote_assets
        assert "BTCDOWNUSDT" in universe_cfg.filters.exclude_symbols
        assert universe_cfg.filters.min_24h_volume_usd == 5000000
    
    def test_load_universe_config_disabled(self):
        """universe.enabled=false일 때"""
        config_dict = {
            "universe": {
                "enabled": False,
                "provider": {
                    "type": "topn_volume"
                }
            }
        }
        
        universe_cfg = load_universe_config(config_dict)
        
        assert universe_cfg is None
    
    def test_load_universe_config_missing(self):
        """universe 섹션 없을 때"""
        config_dict = {}
        
        universe_cfg = load_universe_config(config_dict)
        
        assert universe_cfg is None
    
    def test_load_universe_config_defaults(self):
        """기본값 적용"""
        config_dict = {
            "universe": {
                "enabled": True,
                "provider": {}  # 최소 설정
            }
        }
        
        universe_cfg = load_universe_config(config_dict)
        
        assert universe_cfg is not None
        assert universe_cfg.provider_type == "static"  # 기본값
        assert universe_cfg.top_n == 10  # 기본값
        assert universe_cfg.cache_ttl_sec == 3600  # 기본값
        assert universe_cfg.filters.quote_assets == ["USDT"]  # 기본값


# ========================================
# 5. Config Validation Tests
# ========================================

class TestConfigValidation:
    """UniverseProviderConfig / UniverseFilterConfig 검증"""
    
    def test_universe_provider_config_valid(self):
        """정상 설정"""
        config = UniverseProviderConfig(
            provider_type="topn_volume",
            top_n=20,
            cache_ttl_sec=7200
        )
        
        assert config.provider_type == "topn_volume"
        assert config.top_n == 20
        assert config.cache_ttl_sec == 7200
    
    def test_universe_filter_config_defaults(self):
        """필터 기본값"""
        config = UniverseFilterConfig()
        
        assert config.quote_assets == ["USDT"]
        assert config.exclude_symbols == []
        assert config.min_24h_volume_usd == 0.0
        assert config.market_types == ["PERPETUAL"]
        assert config.contract_status == "TRADING"
    
    def test_symbol_info_complete(self):
        """SymbolInfo 완전한 데이터"""
        symbol_info = SymbolInfo(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            exchange="binance",
            price_precision=2,
            quantity_precision=3,
            min_qty=0.001,
            max_qty=10000.0,
            step_size=0.001,
            is_futures=True,
            is_margin_enabled=True,
            contract_type="PERPETUAL",
            volume_24h_usdt=50_000_000_000.0,
            price=42000.0
        )
        
        assert symbol_info.symbol == "BTCUSDT"
        assert symbol_info.volume_24h_usdt == 50_000_000_000.0
    
    def test_symbol_info_minimal(self):
        """SymbolInfo 최소 데이터"""
        symbol_info = SymbolInfo(
            symbol="ETHUSDT",
            base_asset="ETH",
            quote_asset="USDT"
        )
        
        assert symbol_info.symbol == "ETHUSDT"
        assert symbol_info.exchange == "binance"  # 기본값
        assert symbol_info.is_futures is True  # 기본값
        assert symbol_info.volume_24h_usdt is None  # 선택


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
