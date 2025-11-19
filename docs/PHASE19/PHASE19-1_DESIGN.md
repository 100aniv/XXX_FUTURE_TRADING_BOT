# PHASE19-1 설계: Strategy Registry 구축

**작성일**: 2025-11-19  
**작업 ID**: PHASE19-1  
**목적**: 전략 앙상블 프레임워크의 기반 인프라 구축  
**선행 조건**: PHASE18 완료 (인프라 안정화)

---

## 1. Executive Summary

### 1.1 목표

전략군 앙상블 시스템의 기반이 되는 **Strategy Registry** 인프라를 구축한다.

**핵심 기능**:
- 전략 자동 스캔 및 등록
- 전략 Metadata 표준화
- BaseStrategy 인터페이스 정의
- 전략군 중앙 관리

**다음 단계 연계**:
- PHASE19-2: 앙상블 Score 시스템
- PHASE19-3: 앙상블 Signal Aggregation
- PHASE19-4: 멀티 전략 실행 엔진

### 1.2 현재 상태

**문제점**:
1. 전략 파일들이 산발적 (`strategies/*.py`)
2. 형식 불일치 (모두 함수 기반 `signal_logic()`)
3. Metadata 없음 (지원 심볼, 타임프레임 등)
4. 전략 자동 로드 메커니즘 없음
5. 인터페이스 표준 없음

**기존 전략**:
- `scalping.py` (PHASE12, 3m, 고빈도)
- `breakout.py` (15m, 돌파)
- `reversion.py` (v3, 평균회귀)
- `swing.py` (4h, 스윙)
- `swing_bb.py` (4h, BB 기반)
- `daytrade.py` (15m, 데이 트레이딩)
- `trend.py` (1h, 추세 추종)
- `ensemble.py` (과거 구조, PHASE19에서 재설계)

### 1.3 설계 방향

**원칙**:
1. **최소 변경**: 기존 전략 로직 보존
2. **하위 호환**: 기존 `signal_logic()` 래핑
3. **확장 가능**: 새로운 전략 추가 용이
4. **자동화**: Registry가 전략 자동 발견

---

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                 StrategyRegistry                     │
│  - scan() : 전략 자동 스캔                           │
│  - register(strategy_cls) : 전략 등록                │
│  - get(name) : 전략 인스턴스 반환                     │
│  - list_metadata() : 전체 전략 메타데이터             │
└─────────────────────────────────────────────────────┘
                        │
                        │ manages
                        ▼
        ┌───────────────────────────────┐
        │      BaseStrategy              │
        │  (Abstract Base Class)         │
        │  - compute_signal()            │
        │  - validate()                  │
        │  - @property metadata          │
        └───────────────────────────────┘
                        △
                        │ inherits
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  ScalpingStr │ │ BreakoutStr │ │ReversionStr│
│  (신규 래퍼) │ │  (신규 래퍼)│ │ (신규 래퍼)│
│              │ │             │ │            │
│ - metadata   │ │ - metadata  │ │ - metadata │
│ - compute_   │ │ - compute_  │ │ - compute_ │
│   signal()   │ │   signal()  │ │   signal() │
│   → 기존     │ │   → 기존    │ │   → 기존   │
│   signal_    │ │   signal_   │ │   signal_  │
│   logic()    │ │   logic()   │ │   logic()  │
│   호출       │ │   호출      │ │   호출     │
└──────────────┘ └─────────────┘ └────────────┘
```

### 2.2 Data Flow

```
1. 시스템 시작
   ↓
2. StrategyRegistry.scan()
   - strategies/ 디렉토리 스캔
   - *.py 파일 찾기
   - BaseStrategy 상속 클래스 검색
   ↓
3. 전략 자동 등록
   - {strategy_name: StrategyClass} 딕셔너리 생성
   - metadata 수집 및 검증
   ↓
4. 실행 시점
   - registry.get('scalping') → ScalpingStrategy 인스턴스
   - strategy.compute_signal(candle) → 신호 생성
   ↓
5. 앙상블 (PHASE19-2+)
   - 여러 전략 신호 수집
   - Score 계산 및 집계
```

---

## 3. Component Design

### 3.1 StrategyMetadata (dataclass)

**파일**: `common/registry/strategy_metadata.py`

```python
from dataclasses import dataclass
from typing import List

@dataclass
class StrategyMetadata:
    """전략 메타데이터"""
    strategy_name: str          # 전략 이름 (예: 'scalping')
    strategy_type: str          # 전략 타입 (예: 'scalping', 'reversion', 'trend')
    supported_symbols: List[str]  # 지원 심볼 (예: ['BTCUSDT', 'ETHUSDT'])
    supported_timeframes: List[str]  # 지원 타임프레임 (예: ['1m', '3m', '5m'])
    version: str                # 버전 (예: 'v3.0')
    description: str            # 설명
    
    def validate(self) -> bool:
        """메타데이터 유효성 검사"""
        if not self.strategy_name:
            return False
        if not self.strategy_type:
            return False
        if not self.supported_symbols:
            return False
        if not self.supported_timeframes:
            return False
        return True
```

**필드 설명**:
- `strategy_name`: 고유 식별자 (소문자, 공백 없음)
- `strategy_type`: 전략 분류 (scalping, reversion, trend, breakout, swing)
- `supported_symbols`: 지원하는 심볼 리스트 (빈 리스트 = 모든 심볼)
- `supported_timeframes`: 지원하는 타임프레임 리스트
- `version`: 전략 버전 (SemVer 형식)
- `description`: 전략 간단 설명

### 3.2 BaseStrategy (Abstract Base Class)

**파일**: `common/registry/base_strategy.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from .strategy_metadata import StrategyMetadata

class BaseStrategy(ABC):
    """
    전략 기본 인터페이스
    
    모든 전략은 이 클래스를 상속해야 한다.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화
        
        Args:
            config: 전략 설정 (CFG에서 로드)
        """
        self.config = config
        self._validate_metadata()
    
    @property
    @abstractmethod
    def metadata(self) -> StrategyMetadata:
        """전략 메타데이터 반환"""
        pass
    
    @abstractmethod
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        신호 계산
        
        Args:
            df: OHLCV + 지표가 포함된 DataFrame
        
        Returns:
            dict: 신호 정보
            {
                'direction': 'LONG' | 'SHORT' | None,
                'reason': str,
                'entry': float,
                'sl': float,
                'tp': float,
                ...
            }
        """
        pass
    
    def validate(self) -> bool:
        """전략 유효성 검사"""
        return self.metadata.validate()
    
    def _validate_metadata(self):
        """메타데이터 유효성 검사 (초기화 시 자동 실행)"""
        if not self.validate():
            raise ValueError(f"Invalid metadata for strategy: {self.metadata.strategy_name}")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.metadata.strategy_name}, version={self.metadata.version})"
```

**핵심 메서드**:
- `metadata`: 전략 메타데이터 프로퍼티 (필수 구현)
- `compute_signal(df)`: 신호 계산 (필수 구현)
- `validate()`: 메타데이터 유효성 검사
- `__init__`: 설정 초기화 및 자동 검증

### 3.3 StrategyRegistry

**파일**: `common/registry/strategy_registry.py`

```python
import os
import importlib
import inspect
from typing import Dict, Type, List, Optional
from pathlib import Path
import logging

from .base_strategy import BaseStrategy
from .strategy_metadata import StrategyMetadata

logger = logging.getLogger(__name__)

class StrategyRegistry:
    """
    전략 중앙 레지스트리
    
    전략 자동 스캔, 등록, 관리를 담당한다.
    """
    
    def __init__(self, strategies_dir: str = 'strategies'):
        """
        레지스트리 초기화
        
        Args:
            strategies_dir: 전략 디렉토리 경로
        """
        self.strategies_dir = strategies_dir
        self._registry: Dict[str, Type[BaseStrategy]] = {}
        self._metadata_cache: Dict[str, StrategyMetadata] = {}
    
    def scan(self) -> int:
        """
        전략 디렉토리 자동 스캔
        
        Returns:
            int: 발견된 전략 수
        """
        strategies_path = Path(self.strategies_dir)
        if not strategies_path.exists():
            logger.warning(f"Strategies directory not found: {self.strategies_dir}")
            return 0
        
        count = 0
        for py_file in strategies_path.glob('*.py'):
            if py_file.name.startswith('__'):
                continue  # __init__.py, __pycache__ 등 제외
            
            module_name = py_file.stem
            try:
                # 모듈 임포트
                module = importlib.import_module(f'{self.strategies_dir}.{module_name}')
                
                # BaseStrategy 상속 클래스 찾기
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj is BaseStrategy:
                        continue
                    if issubclass(obj, BaseStrategy) and obj.__module__ == module.__name__:
                        self.register(obj)
                        count += 1
                        logger.info(f"✅ Registered strategy: {name} from {module_name}.py")
            except Exception as e:
                logger.warning(f"⚠️  Failed to load strategy from {module_name}.py: {e}")
        
        logger.info(f"📊 Total strategies registered: {count}")
        return count
    
    def register(self, strategy_cls: Type[BaseStrategy]) -> None:
        """
        전략 클래스 등록
        
        Args:
            strategy_cls: BaseStrategy를 상속한 전략 클래스
        """
        # 임시 인스턴스 생성하여 metadata 가져오기 (config는 빈 딕셔너리)
        try:
            temp_instance = strategy_cls({})
            metadata = temp_instance.metadata
            
            if not metadata.validate():
                logger.warning(f"⚠️  Invalid metadata for {strategy_cls.__name__}, skipping")
                return
            
            strategy_name = metadata.strategy_name
            self._registry[strategy_name] = strategy_cls
            self._metadata_cache[strategy_name] = metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to register strategy {strategy_cls.__name__}: {e}")
    
    def get(self, name: str, config: Optional[Dict] = None) -> Optional[BaseStrategy]:
        """
        전략 인스턴스 반환
        
        Args:
            name: 전략 이름
            config: 전략 설정 (None이면 빈 딕셔너리)
        
        Returns:
            BaseStrategy 인스턴스 또는 None
        """
        strategy_cls = self._registry.get(name)
        if not strategy_cls:
            logger.warning(f"Strategy not found: {name}")
            return None
        
        return strategy_cls(config or {})
    
    def list_strategies(self) -> List[str]:
        """등록된 전략 이름 리스트 반환"""
        return list(self._registry.keys())
    
    def list_metadata(self) -> Dict[str, StrategyMetadata]:
        """전체 전략 메타데이터 반환"""
        return self._metadata_cache.copy()
    
    def get_metadata(self, name: str) -> Optional[StrategyMetadata]:
        """특정 전략의 메타데이터 반환"""
        return self._metadata_cache.get(name)
    
    def __repr__(self) -> str:
        return f"StrategyRegistry(strategies={len(self._registry)})"
```

**핵심 기능**:
- `scan()`: 전략 디렉토리 자동 스캔 및 등록
- `register(cls)`: 전략 클래스 수동 등록
- `get(name, config)`: 전략 인스턴스 생성 및 반환
- `list_strategies()`: 등록된 전략 이름 리스트
- `list_metadata()`: 전체 메타데이터 조회

---

## 4. Strategy Migration (기존 전략 래핑)

### 4.1 Migration 전략

**목표**: 기존 전략 로직 보존, 최소 변경

**방법**:
1. 기존 `signal_logic(df, config)` 함수는 그대로 유지
2. 새로운 클래스 래퍼 생성 (예: `ScalpingStrategy`)
3. 클래스의 `compute_signal()` 메서드가 기존 함수 호출
4. metadata 프로퍼티 추가

### 4.2 예시: scalping.py

**Before** (현재):
```python
def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """기존 로직"""
    # ... 전략 로직 ...
    return {"direction": "LONG", ...}
```

**After** (PHASE19-1):
```python
# 기존 함수 유지
def signal_logic(df: pd.DataFrame, config: dict) -> Dict[str, Any]:
    """기존 로직 (변경 없음)"""
    # ... 전략 로직 ...
    return {"direction": "LONG", ...}


# 신규 클래스 래퍼
from common.registry.base_strategy import BaseStrategy
from common.registry.strategy_metadata import StrategyMetadata

class ScalpingStrategy(BaseStrategy):
    """Scalping 전략 (PHASE12, 3m 고빈도)"""
    
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            strategy_name='scalping',
            strategy_type='scalping',
            supported_symbols=['BTCUSDT', 'ETHUSDT'],  # 설정 가능
            supported_timeframes=['1m', '3m', '5m'],
            version='v3.0',
            description='3분봉 기반 EMA Fresh Trend + Optional MR'
        )
    
    def compute_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """신호 계산 (기존 함수 호출)"""
        return signal_logic(df, self.config)
```

**장점**:
- 기존 로직 보존 (테스트된 코드)
- 점진적 마이그레이션 가능
- 하위 호환성 유지
- Registry 시스템 통합

### 4.3 Migration 대상

| 전략 | 파일 | 타입 | 타임프레임 | 우선순위 |
|------|------|------|-----------|---------|
| scalping | `scalping.py` | scalping | 1m, 3m | 1 (메인) |
| breakout | `breakout.py` | breakout | 15m | 2 |
| reversion | `reversion.py` | reversion | 5m, 15m | 2 |
| trend | `trend.py` | trend | 1h, 4h | 3 |
| swing | `swing.py` | swing | 4h | 3 |
| swing_bb | `swing_bb.py` | swing | 4h | 3 |
| daytrade | `daytrade.py` | daytrade | 15m | 3 |
| ensemble | `ensemble.py` | ensemble | N/A | PHASE19-2+ |

**참고**: `ensemble.py`는 PHASE19-2에서 재설계

---

## 5. Integration Points

### 5.1 시스템 초기화

**run_paper.py / run_backtest.py 수정**:
```python
from common.registry.strategy_registry import StrategyRegistry

# 전략 레지스트리 초기화
registry = StrategyRegistry()
count = registry.scan()
logger.info(f"✅ {count}개 전략 로드 완료")

# 사용 예시
strategy = registry.get('scalping', cfg['strategies']['scalping'])
signal = strategy.compute_signal(df)
```

### 5.2 기존 코드 영향

**DO-NOT-TOUCH 영역** (변경 없음):
- `execution/engine.py`
- `execution/portfolio_manager.py`
- `execution/risk_manager.py`
- `execution/position_sizer.py`
- `execution/position_tracker.py`

**최소 변경 영역**:
- `scripts/run_paper.py`: Registry 초기화 추가 (선택적)
- `scripts/run_backtest.py`: Registry 초기화 추가 (선택적)

**참고**: Registry는 **선택적 기능**이므로, 기존 직접 import 방식도 유지 가능.

---

## 6. Testing Strategy

### 6.1 Unit Tests

**파일**: `tests/test_phase19_1_strategy_registry.py`

**테스트 항목**:
1. StrategyMetadata 생성 및 검증
2. BaseStrategy 추상 클래스 검증
3. StrategyRegistry scan() 기능
4. 전략 자동 등록
5. 전략 인스턴스 생성
6. metadata 조회
7. 예외 처리 (잘못된 metadata, 없는 전략 등)

### 6.2 Integration Tests

**REAL PAPER 2분 Smoke Test**:
```bash
python scripts/run_paper.py \
  --clean-state \
  --duration-hours 0.033 \
  --duration-mode wall_clock \
  --symbol BTCUSDT \
  --timeframe 1m \
  --strategy scalping
```

**검증**:
- Registry 초기화 성공
- 전략 자동 로드 성공
- 신호 생성 정상
- ERROR/CRITICAL 로그 없음

---

## 7. Performance Considerations

### 7.1 성능 영향

**Registry 초기화**:
- 한 번만 실행 (시스템 시작 시)
- 전략 8개 × 0.1초 ≈ 0.8초 (무시 가능)

**런타임 오버헤드**:
- 클래스 래핑: < 0.01ms (함수 호출 1회 추가)
- 메타데이터 조회: O(1) (딕셔너리)

**메모리**:
- Registry: < 1KB
- 전략 클래스 8개: < 100KB

**판정**: 성능 영향 없음

---

## 8. Migration Roadmap

### 8.1 PHASE19-1 (현재)

- [x] StrategyMetadata 설계
- [x] BaseStrategy 인터페이스 설계
- [x] StrategyRegistry 구현
- [ ] 전략 래핑 (7개)
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 문서화

### 8.2 PHASE19-2

- Ensemble Score 시스템
- 전략별 가중치 관리
- 신호 집계 로직

### 8.3 PHASE19-3

- 멀티 전략 동시 실행
- 포트폴리오 할당 최적화

### 8.4 PHASE19-4

- Optuna 기반 전략 파라미터 튜닝
- A/B 테스트 프레임워크

---

## 9. Risk Mitigation

### 9.1 회귀 방지

**원칙**:
1. 기존 `signal_logic()` 함수 보존
2. 기존 import 방식 유지 가능
3. Registry는 선택적 기능
4. 점진적 마이그레이션

### 9.2 Rollback Plan

**문제 발생 시**:
1. Registry 비활성화 (기존 방식으로 복귀)
2. Git revert
3. 전략별 독립 롤백 가능

---

## 10. Acceptance Criteria

### 10.1 필수 조건

- [x] StrategyMetadata 구현
- [x] BaseStrategy 인터페이스 구현
- [x] StrategyRegistry 구현
- [ ] 전략 7개 래핑 (scalping, breakout, reversion, trend, swing, swing_bb, daytrade)
- [ ] 단위 테스트 100% PASS
- [ ] REAL PAPER 2분 정상 실행
- [ ] DO-NOT-TOUCH 영역 보존
- [ ] 설계 문서 작성
- [ ] 완료 리포트 작성

### 10.2 성공 기준

**기능**:
- Registry가 전략 자동 스캔
- 전략 metadata 정상 제공
- compute_signal() 정상 작동
- 기존 기능 회귀 없음

**성능**:
- 초기화 시간 < 1초
- 런타임 오버헤드 < 0.01ms
- 메모리 영향 < 100KB

**문서**:
- 설계 문서 완성
- 완료 리포트 작성
- 코드 주석 충분

---

## 11. Next Steps (PHASE19-2+)

### 11.1 Ensemble Score System

**목표**: 전략 신호의 신뢰도 점수화

**구현**:
- 전략별 가중치 (winrate, profit factor 기반)
- 시장 상황별 가중치 조정 (volatile, trending, ranging)
- Score 집계 및 임계값 판단

### 11.2 Signal Aggregation

**목표**: 여러 전략 신호를 하나로 통합

**구현**:
- 동의 기반 (2/3 이상 동의 시 진입)
- 가중 평균 기반 (score 합산)
- 거부권 (Critical 전략이 반대 시 취소)

### 11.3 Multi-Strategy Engine

**목표**: 여러 전략을 동시에 실행

**구현**:
- 전략별 독립 포지션 관리
- 포트폴리오 할당 최적화
- 전략 간 간섭 방지

---

**문서 작성**: 2025-11-19  
**작성자**: Cascade AI (Claude 4.5 Thinking)  
**상태**: 설계 완료, 구현 대기
