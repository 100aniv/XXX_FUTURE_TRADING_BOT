# PHASE26-0: Universe Provider Implementation - Design Document

**작성일**: 2025-12-03  
**상태**: 🔄 IN PROGRESS  
**목적**: TopN 심볼 선정 인프라 구축 (Multi-Symbol 준비)

---

## 1. AS-IS 구조 분석

### 1.1. 현재 심볼 관리 방식

#### `common/symbol_manager.py` (기존)
- **SymbolManager 클래스**: Binance Futures API에서 심볼 조회
  - `fetch_all_usdt_symbols()`: 전체 USDT 선물 조회
  - `fetch_top_volume_symbols(top_n)`: **거래량 상위 N개 조회 (이미 구현됨!)**
  - `get_symbol_info(symbol)`: 심볼 상세 정보 (pricePrecision, quantityPrecision 등)
- **필터링**: USDT 선물, PERPETUAL 계약만, TRADING 상태만
- **load_symbols_from_config(config)**: Config 기반 심볼 로딩 (mode: manual/top50/top100/all)

#### 현재 Config 구조 (`configs/base.yml`)
```yaml
symbol: BTCUSDT  # 단일 심볼 (engine에서 사용)

symbols:
  mode: top100  # manual | top50 | top100 | all
  manual:
    - BTCUSDT
  core:
    - BTCUSDT
    - ETHUSDT
  max_streams: 120
  topN:
    n: 50
    min_volume_24h: 30000000
    refresh_interval: 3600
```

#### 현재 엔진 진입점 (`execution/engine.py::run_v2`)
```python
def run_v2(mode: str, config: dict, clean_state: bool = False):
    symbol = config.get('symbol', 'BTCUSDT')  # 단일 심볼만 지원
    # ...
```

### 1.2. 문제점 및 한계

1. **No Protocol/Interface**: `SymbolManager`는 구체 클래스이며, 인터페이스가 없음
2. **Single Symbol Only**: 엔진은 단일 심볼만 처리 가능
3. **No Universe Concept**: "Universe"라는 개념이 없음 (심볼 집합 관리 부재)
4. **Config Duplication**: `symbol` (단일) vs `symbols` (다중) 구조 혼재
5. **No Filtering Abstraction**: 필터링 로직이 `SymbolManager` 내부에 하드코딩

---

## 2. PHASE26-0 목표 및 범위

### 2.1. 목표

**Universe Provider 계층 추가**로:
- TopN 심볼 선정 로직
- 필터(볼륨/블랙리스트/마켓 타입 등) 기반 심볼 리스트 결정
- 단일 책임 모듈 (심볼 선정만 담당)

### 2.2. 범위 제한 (중요!)

✅ **PHASE26-0 포함**:
- `UniverseProvider` Protocol/ABC 정의
- `TopNByVolumeUniverseProvider` 구현 (기존 `SymbolManager` 로직 재사용)
- `StaticUniverseProvider` 구현 (테스트용)
- `UniverseProviderConfig` / `UniverseFilterConfig` 정의
- Config 스키마 확장 (`universe` 섹션 추가)
- 테스트 (단위 테스트만)

❌ **PHASE26-0 제외** (다음 단계로 연기):
- 엔진 멀티 심볼 코루틴 구조 → **PHASE26-1**
- per-symbol state/queue/risk/portfolio → **PHASE26-1**
- Top10 Paper Load Test → **PHASE26-2**
- DB 기반 리얼 마켓 메트릭 → **PHASE27+**

### 2.3. Acceptance Criteria

1. ✅ `UniverseProvider` Protocol 정의 완료
2. ✅ 최소 2개 구현 (`TopNByVolumeUniverseProvider`, `StaticUniverseProvider`)
3. ✅ Config 스키마 확장 (`universe` 섹션)
4. ✅ **단일 심볼 모드 100% 호환** (기존 동작 절대 깨지지 않음)
5. ✅ 테스트 통과 (`tests/test_phase26_0_universe_provider.py`)
6. ✅ 설계 문서 + 리포트 + PHASE_ROADMAP 업데이트 + Git 커밋

---

## 3. Universe Provider 아키텍처 설계

### 3.1. 핵심 타입 정의

#### 3.1.1. `SymbolInfo` (기존 확장)

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SymbolInfo:
    """심볼 메타데이터 (거래소 스펙 포함)"""
    symbol: str                     # 예: BTCUSDT
    base_asset: str                 # 예: BTC
    quote_asset: str                # 예: USDT
    exchange: str = "binance"       # 거래소 이름
    
    # 거래소 스펙
    price_precision: int = 2
    quantity_precision: int = 3
    min_qty: float = 0.001
    max_qty: float = 10000.0
    step_size: float = 0.001
    
    # 마켓 타입
    is_futures: bool = True
    is_margin_enabled: bool = True
    contract_type: str = "PERPETUAL"  # PERPETUAL | DELIVERY
    
    # 메트릭 (선택)
    volume_24h_usdt: Optional[float] = None
    price: Optional[float] = None
```

#### 3.1.2. `UniverseFilterConfig`

```python
@dataclass
class UniverseFilterConfig:
    """Universe 필터링 설정"""
    quote_assets: List[str] = None  # 기본: ["USDT"]
    exclude_symbols: List[str] = None  # 블랙리스트
    min_24h_volume_usd: float = 0.0  # 최소 24h 거래량 (USDT)
    market_types: List[str] = None  # ["PERPETUAL"] | ["DELIVERY"] | None (전체)
    contract_status: str = "TRADING"  # TRADING | PRE_TRADING | ...
    
    def __post_init__(self):
        self.quote_assets = self.quote_assets or ["USDT"]
        self.exclude_symbols = self.exclude_symbols or []
        self.market_types = self.market_types or ["PERPETUAL"]
```

#### 3.1.3. `UniverseProviderConfig`

```python
@dataclass
class UniverseProviderConfig:
    """UniverseProvider 설정"""
    provider_type: str  # "topn_volume" | "static" | "db_metrics" (미래 확장)
    top_n: int = 10  # TopN 개수
    filters: UniverseFilterConfig = field(default_factory=UniverseFilterConfig)
    
    # Static Provider용
    static_symbols: List[str] = None
    
    # 캐시 설정
    cache_ttl_sec: int = 3600  # 1시간 (Binance 마켓 정보 변경 빈도 낮음)
    
    def __post_init__(self):
        self.static_symbols = self.static_symbols or []
```

### 3.2. UniverseProvider Protocol

```python
from typing import Protocol, List

class UniverseProvider(Protocol):
    """Universe Provider 인터페이스 (Protocol-based)"""
    
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
```

**Protocol 사용 이유**:
- Duck Typing 지원 (엄격한 ABC보다 유연)
- 기존 `SymbolManager`를 점진적으로 마이그레이션 가능
- 테스트 시 Mock 구현 용이

### 3.3. 구체 구현

#### 3.3.1. `StaticUniverseProvider`

```python
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
            raise ValueError(f"Invalid provider_type: {config.provider_type}")
        self.config = config
        self.logger = setup_logger(__name__)
    
    async def get_universe(self) -> List[SymbolInfo]:
        symbols = self.config.static_symbols
        
        if not symbols:
            self.logger.warning("⚠️ StaticUniverseProvider: 빈 심볼 리스트")
            return []
        
        # SymbolInfo 객체로 변환 (최소 정보만)
        result = []
        for symbol in symbols:
            if symbol in self.config.filters.exclude_symbols:
                continue
            
            base_asset = symbol.replace("USDT", "")  # 간단한 파싱
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
```

#### 3.3.2. `TopNByVolumeUniverseProvider`

```python
class TopNByVolumeUniverseProvider:
    """
    거래량 상위 N개 심볼 제공자 (Binance API 기반)
    
    - 기존 SymbolManager.fetch_top_volume_symbols() 로직 재사용
    - 필터링: quote_asset, volume, market_type, exclude_list
    - 정렬: 24h volume (quoteVolume) 기준 내림차순
    
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
            raise ValueError(f"Invalid provider_type: {config.provider_type}")
        
        self.config = config
        self.logger = setup_logger(__name__)
        self._cache: Optional[List[SymbolInfo]] = None
        self._cache_time: Optional[datetime] = None
    
    async def get_universe(self) -> List[SymbolInfo]:
        """
        거래량 상위 N개 심볼 조회 + 필터링
        
        Flow:
            1. 캐시 체크 (TTL 확인)
            2. Binance 24h Ticker API 호출
            3. 필터링 (quote_asset, volume, market_type, exclude_list)
            4. 정렬 (volume 기준 내림차순)
            5. Top N 선택
            6. Exchange Info로 SymbolInfo 보강
        """
        # 1. 캐시 체크
        if self._is_cache_valid():
            self.logger.debug("✅ Cache hit (Universe)")
            return self._cache
        
        # 2. 24h Ticker 조회
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.TICKER_24H_URL, timeout=10) as resp:
                    resp.raise_for_status()
                    tickers = await resp.json()
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
                continue
            
            # 필터 3: volume
            volume = float(t['quoteVolume'])
            if volume < filters.min_24h_volume_usd:
                continue
            
            filtered_tickers.append(t)
        
        # 4. 정렬 (volume 기준 내림차순)
        filtered_tickers.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        # 5. Top N 선택
        top_n_tickers = filtered_tickers[:self.config.top_n]
        
        # 6. Exchange Info 조회 (SymbolInfo 보강)
        exchange_info = await self._fetch_exchange_info()
        symbol_info_map = {s['symbol']: s for s in exchange_info.get('symbols', [])}
        
        result = []
        for t in top_n_tickers:
            symbol = t['symbol']
            info = symbol_info_map.get(symbol, {})
            
            # market_type 필터 (PERPETUAL만 or 전체)
            contract_type = info.get('contractType', 'PERPETUAL')
            if filters.market_types and contract_type not in filters.market_types:
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
                volume_24h_usdt=float(t['quoteVolume']),
                price=float(t['lastPrice'])
            ))
        
        # 7. 캐시 업데이트
        self._cache = result
        self._cache_time = datetime.now()
        
        self.logger.info(f"✅ TopN Universe: {len(result)}개 심볼 (Top {self.config.top_n})")
        if result:
            top_5 = [f"{s.symbol}(${s.volume_24h_usdt/1e6:.1f}M)" for s in result[:5]]
            self.logger.info(f"   상위 5: {', '.join(top_5)}")
        
        return result
    
    async def _fetch_exchange_info(self) -> dict:
        """Exchange Info API 호출 (심볼 스펙 조회)"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(self.EXCHANGE_INFO_URL, timeout=10) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            self.logger.error(f"❌ Binance Exchange Info 조회 실패: {e}")
            return {'symbols': []}
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 체크 (TTL 기반)"""
        if self._cache is None or self._cache_time is None:
            return False
        
        elapsed_sec = (datetime.now() - self._cache_time).total_seconds()
        return elapsed_sec < self.config.cache_ttl_sec
    
    def _get_min_qty(self, info: dict) -> float:
        """최소 수량 추출 (filters[1] = LOT_SIZE)"""
        try:
            return float(info['filters'][1]['minQty'])
        except (KeyError, IndexError, ValueError):
            return 0.001
    
    def _get_max_qty(self, info: dict) -> float:
        """최대 수량 추출"""
        try:
            return float(info['filters'][1]['maxQty'])
        except (KeyError, IndexError, ValueError):
            return 10000.0
    
    def _get_step_size(self, info: dict) -> float:
        """수량 단위 추출"""
        try:
            return float(info['filters'][1]['stepSize'])
        except (KeyError, IndexError, ValueError):
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
```

### 3.4. Factory Function

```python
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
        raise ValueError(f"Unsupported provider_type: {config.provider_type}")
```

---

## 4. Config 스키마 확장

### 4.1. 새로운 `universe` 섹션 추가

`configs/base.yml`에 추가:

```yaml
# ========================================
# Universe Provider (PHASE26-0)
# ========================================
universe:
  enabled: false  # Universe Provider 사용 여부 (기본: false, 단일 심볼 모드 유지)
  
  provider:
    type: topn_volume  # "topn_volume" | "static" | "db_metrics" (미래 확장)
    top_n: 10  # TopN 개수
    cache_ttl_sec: 3600  # 캐시 TTL (1시간)
    
    # Static Provider용 (테스트/Fallback)
    static_symbols:
      - BTCUSDT
      - ETHUSDT
    
  filters:
    quote_assets:
      - USDT
    exclude_symbols:
      - BTCDOWNUSDT
      - BTCUPUSDT
      - ETHDOWNUSDT
      - ETHUPUSDT
    min_24h_volume_usd: 10000000  # 10M USDT
    market_types:
      - PERPETUAL
    contract_status: TRADING

# ========================================
# 기존 symbol/symbols 구조 유지 (하위 호환)
# ========================================
symbol: BTCUSDT  # 단일 심볼 (universe.enabled=false일 때 사용)

symbols:
  mode: top100
  manual:
    - BTCUSDT
  # ... (기존 구조 유지)
```

### 4.2. Config Loader 확장

`common/config_loader.py`에 추가:

```python
def load_universe_config(config: dict) -> Optional[UniverseProviderConfig]:
    """
    Universe Provider 설정 로딩
    
    Args:
        config: 전체 config dict
    
    Returns:
        UniverseProviderConfig or None (universe.enabled=false일 때)
    """
    universe_cfg = config.get('universe', {})
    
    if not universe_cfg.get('enabled', False):
        return None
    
    provider_cfg = universe_cfg.get('provider', {})
    filters_cfg = universe_cfg.get('filters', {})
    
    return UniverseProviderConfig(
        provider_type=provider_cfg.get('type', 'static'),
        top_n=provider_cfg.get('top_n', 10),
        filters=UniverseFilterConfig(
            quote_assets=filters_cfg.get('quote_assets', ['USDT']),
            exclude_symbols=filters_cfg.get('exclude_symbols', []),
            min_24h_volume_usd=filters_cfg.get('min_24h_volume_usd', 0.0),
            market_types=filters_cfg.get('market_types', ['PERPETUAL']),
            contract_status=filters_cfg.get('contract_status', 'TRADING')
        ),
        static_symbols=provider_cfg.get('static_symbols', []),
        cache_ttl_sec=provider_cfg.get('cache_ttl_sec', 3600)
    )
```

---

## 5. 엔진 통합 (최소 침습)

### 5.1. `execution/engine.py` 수정 (PHASE26-1 준비용 Hook만)

```python
def run_v2(mode: str, config: dict, clean_state: bool = False):
    """
    PHASE23-1: Single-Engine Entry Point
    PHASE26-0: Universe Provider Hook 추가 (아직 사용 안 함)
    """
    logger.info("=" * 80)
    logger.info(f"🚀 [PHASE23-1] Engine V2 시작 - Mode: {mode.upper()}")
    logger.info("=" * 80)
    
    # ... (기존 코드) ...
    
    # PHASE26-0: Universe Provider 초기화 (옵션)
    universe_provider = _init_universe_provider(config)
    if universe_provider:
        logger.info("🌐 [PHASE26-0] UniverseProvider 활성화")
        # TODO: PHASE26-1에서 멀티 심볼 루프 구현
        universe = await universe_provider.get_universe()
        logger.info(f"   Universe: {len(universe)}개 심볼")
        
        # PHASE26-0: 첫 심볼만 선택 (단일 심볼 모드 유지)
        if universe:
            symbol = universe[0].symbol
            logger.info(f"   선택된 심볼: {symbol} (나머지는 PHASE26-1에서 처리)")
        else:
            symbol = config.get('symbol', 'BTCUSDT')
            logger.warning(f"⚠️ Universe 비어있음, 기본 심볼 사용: {symbol}")
    else:
        # Universe Provider 비활성화 시 기존 로직
        symbol = config.get('symbol', 'BTCUSDT')
        logger.info(f"📊 Symbol: {symbol} (단일 심볼 모드)")
    
    # 나머지 기존 로직...
    # (strategies, ensemble, adapters, run() 호출 등)
```

### 5.2. Helper Function

```python
def _init_universe_provider(config: dict) -> Optional[UniverseProvider]:
    """
    Universe Provider 초기화 (PHASE26-0)
    
    Args:
        config: 전체 config dict
    
    Returns:
        UniverseProvider or None (universe.enabled=false일 때)
    """
    from common.config_loader import load_universe_config
    from common.universe_provider import create_universe_provider
    
    universe_cfg = load_universe_config(config)
    if universe_cfg is None:
        return None
    
    try:
        provider = create_universe_provider(universe_cfg)
        logger.info(f"✅ UniverseProvider 초기화: {universe_cfg.provider_type}")
        return provider
    except Exception as e:
        logger.error(f"❌ UniverseProvider 초기화 실패: {e}")
        return None
```

---

## 6. 모듈 위치 및 파일 구조

### 6.1. 파일 구조

```
common/
├── symbol_manager.py          # 기존 (유지, 점진적 마이그레이션)
├── universe_provider.py       # 신규 (PHASE26-0)
│   ├── SymbolInfo
│   ├── UniverseFilterConfig
│   ├── UniverseProviderConfig
│   ├── UniverseProvider (Protocol)
│   ├── StaticUniverseProvider
│   ├── TopNByVolumeUniverseProvider
│   └── create_universe_provider()
└── config_loader.py           # 수정 (load_universe_config 추가)

execution/
└── engine.py                  # 수정 (_init_universe_provider Hook 추가)

tests/
└── test_phase26_0_universe_provider.py  # 신규

docs/
└── PHASE26/
    ├── PHASE26-0_UNIVERSE_PROVIDER_DESIGN.md    # 본 문서
    └── PHASE26-0_UNIVERSE_PROVIDER_REPORT.md    # 실행 리포트 (나중)
```

### 6.2. 기존 `symbol_manager.py` 처리 방침

**점진적 마이그레이션**:
- PHASE26-0: `symbol_manager.py` 유지 (호환성)
- `TopNByVolumeUniverseProvider`가 `symbol_manager.SymbolManager`의 메서드 재사용
- PHASE26-1~2: 엔진에서 `UniverseProvider`를 주 인터페이스로 사용
- PHASE27+: `symbol_manager.py` Deprecated 표시 후 점진 제거

---

## 7. 테스트 전략

### 7.1. 테스트 파일: `tests/test_phase26_0_universe_provider.py`

#### 7.1.1. StaticUniverseProvider 테스트
- ✅ 설정한 심볼 리스트 그대로 반환
- ✅ Exclude 필터 적용 확인
- ✅ 빈 리스트 처리

#### 7.1.2. TopNByVolumeUniverseProvider 테스트
- ✅ Top N 선택 (volume 기준 정렬)
- ✅ 필터 적용:
  - quote_asset (USDT만)
  - exclude_symbols (블랙리스트)
  - min_24h_volume_usd
  - market_types (PERPETUAL만)
- ✅ 캐시 동작 (TTL 확인)
- ✅ API 실패 시 Fallback

#### 7.1.3. Config 테스트
- ✅ UniverseProviderConfig validation
- ✅ UniverseFilterConfig validation
- ✅ load_universe_config() 파싱

#### 7.1.4. Factory 테스트
- ✅ create_universe_provider() 정상 동작
- ✅ 지원하지 않는 provider_type 에러

### 7.2. 회귀 테스트

**필수**: 기존 PHASE23/24/25 테스트 전부 PASS
- `pytest tests/test_phase23_*`
- `pytest tests/test_phase24_*`
- `pytest tests/test_phase25_*`

**확인**: Universe Provider 비활성화 시 기존 동작 100% 동일

---

## 8. Known Limitations & Future Work

### 8.1. Limitations (PHASE26-0)

1. **No Real Multi-Symbol**: 아직 엔진이 멀티 심볼 처리 불가 (PHASE26-1)
2. **No DB Metrics**: DB 기반 마켓 메트릭 미연동 (PHASE27+)
3. **No Dynamic Refresh**: Universe 자동 갱신 없음 (수동 재시작 필요)
4. **Synchronous Fallback**: `TopNByVolumeUniverseProvider`는 async지만, 일부 헬퍼는 sync

### 8.2. Future Work

- **PHASE26-1**: 멀티 심볼 코루틴 구조
- **PHASE26-2**: Top10 Paper Load Test
- **PHASE27**: DB 기반 Universe Provider (`DBMetricsUniverseProvider`)
- **PHASE28**: Universe 자동 갱신 (주기적 refresh)
- **PHASE29**: Universe Monitoring (심볼 변동 추적, 알림)

---

## 9. 체크리스트 (1조짜리 기준)

### 9.1. 구현 전 체크

- [ ] AS-IS 구조 완전 파악 (symbol_manager, config, engine)
- [ ] 기존 모듈 재사용 계획 수립
- [ ] Protocol vs ABC 선택 (Protocol 선택)
- [ ] Config 스키마 하위 호환성 보장

### 9.2. 구현 중 체크

- [ ] 기존 `symbol_manager.py` 유지 (점진적 마이그레이션)
- [ ] `UniverseProvider` Protocol 정의
- [ ] `StaticUniverseProvider` 구현
- [ ] `TopNByVolumeUniverseProvider` 구현 (기존 로직 재사용)
- [ ] Config 로더 확장 (`load_universe_config`)
- [ ] 엔진 Hook 추가 (`_init_universe_provider`)

### 9.3. 구현 후 체크

- [ ] 단일 심볼 모드 100% 호환 (universe.enabled=false)
- [ ] UniverseProvider 단일 책임 유지 (심볼 선정만)
- [ ] 중복 구조 없음 (symbol_manager와 충돌 없음)
- [ ] PHASE25 튜닝 인프라 미영향
- [ ] 테스트 전부 PASS (신규 + 회귀)

### 9.4. 문서 & Git

- [ ] 설계 문서 완료 (본 문서)
- [ ] 리포트 완료 (`PHASE26-0_UNIVERSE_PROVIDER_REPORT.md`)
- [ ] PHASE_ROADMAP 업데이트
- [ ] Git commit (의미 있는 메시지)

---

## 10. 참고 자료

- **PHASE_ROADMAP.md**: PHASE26 정의
- **PHASE23**: Engine V2 아키텍처
- **PHASE24**: Infra 안정성
- **PHASE25**: Tuning Infrastructure
- **common/symbol_manager.py**: 기존 심볼 관리 로직
- **execution/engine.py**: run_v2 진입점
- **configs/base.yml**: Config 구조

---

**END OF DESIGN DOCUMENT**
