# Execution 모듈 리팩토링 체크리스트

**작성일:** 2025-10-19  
**목적:** trading_executor.py를 execution/ 모듈로 분리  
**참고:** 실밥 리팩토링 주석 기준

---

## 📋 실밥 리팩토링 주석 위치

| 라인 | 주석 내용 | 대상 클래스 |
|------|----------|-----------|
| **283** | `# 리팩토링 시: execution/position_sizer.py로 분리` | PositionSizer |
| **381** | `# 리팩토링 시: execution/risk_manager.py로 분리` | RiskManager |
| **538** | `# 리팩토링 시: execution/position_tracker.py로 분리` | PositionTracker |

---

## 📊 분할 계획

### **원본 파일: trading_executor.py (699줄)**

| 라인 범위 | 내용 | 새 파일 | 상태 |
|----------|------|---------|------|
| 1-27 | 헤더, import, logger | 각 파일에 필요한 것만 | - |
| 30-278 | TradingExecutor 클래스 | execution/executor.py | ⏳ |
| 289-376 | PositionSizer 클래스 | execution/position_sizer.py | ⏳ |
| 387-533 | RiskManager 클래스 | execution/risk_manager.py | ⏳ |
| 540-661 | PositionTracker 클래스 | execution/position_tracker.py | ⏳ |
| 666-699 | if __name__ 블록 | 삭제 (테스트용) | ⏳ |

---

## ✅ 진행 체크리스트

### **Phase 1: 디렉터리 및 기본 구조**
- [x] execution/ 디렉터리 생성 ✅
- [x] execution/__init__.py 작성 ✅
- [x] 다른 모듈 패턴 확인 (common, signals, collector) ✅

### **Phase 2: 파일 분할**
- [x] execution/position_sizer.py 생성 (라인 289-376) ✅
- [x] execution/risk_manager.py 생성 (라인 387-533) ✅
- [x] execution/position_tracker.py 생성 (라인 540-661) ✅
- [x] execution/executor.py 생성 (라인 30-278) ✅

### **Phase 3: trading_manager.py 리팩토링**
- [x] trading_manager.py 분석 ✅
- [x] TradingBot 클래스 → 순수 함수로 변환 ✅
- [x] while True 루프 제거 ✅
- [x] execution/manager.py 생성 ✅
- [x] trading_manager.py에 리팩토링 완료 주석 추가 ✅
- [x] trading_executor.py에 리팩토링 완료 주석 추가 ✅

### **Phase 5: Import 경로 수정**
- [x] tests/test_full_flow.py import 수정 ✅
- [x] test_e2e_trading.py import 수정 ✅
- [x] trading_manager.py import 주석 추가 ✅
- [x] 모든 참조 파일 확인 완료 ✅

### **Phase 4: 실행 스크립트**
- [x] run_trading.py 확인 및 수정 ✅
- [x] 새로운 execution 모듈 사용 ✅
- [x] while 루프 구현 ✅
- [x] signal handler 추가 ✅

### **Phase 6: 문서화**
- [x] docs/architecture/EXECUTION_MODULE.md 작성 ✅
- [x] REFACTORING_COMPLETE.md 업데이트 ✅
- [x] PROJECT_STRUCTURE.md 업데이트 ✅
- [ ] README.md 업데이트

### **Phase 7: 정리**
- [ ] trading_executor.py → _archived/ 이동
- [ ] trading_manager.py → _archived/ 이동 또는 삭제
- [ ] 불필요한 trading/ 디렉터리 정리

### **Phase 8: 테스트**
- [ ] import 테스트
- [ ] 기본 동작 테스트
- [ ] 통합 테스트

---

## 📝 세부 내용

### **1. execution/position_sizer.py**
**원본:** trading_executor.py 라인 289-376  
**클래스:** PositionSizer  
**메서드:**
- `__init__()` (295-308)
- `calculate()` (310-362)
- `_calculate_quality_weight()` (364-375)

**의존성:** 없음 (독립적)

**필요 import:**
```python
import os
from typing import Dict, Tuple
from common.logger import setup_logger
```

---

### **2. execution/risk_manager.py**
**원본:** trading_executor.py 라인 387-533  
**클래스:** RiskManager  
**메서드:**
- `__init__()` (393-412)
- `_tf_ms()` (417-423)
- `flash_guard_update()` (425-460)
- `flash_guard_allowed()` (462-476)
- `check_order()` (482-509)
- `update_daily_pnl()` (511-514)
- `add_position()` (516-520)
- `remove_position()` (522-527)
- `reset_daily()` (529-532)

**의존성:**
- `from collections import deque` (동적 import, 라인 437)

**필요 import:**
```python
import os
from typing import Dict, Tuple
from common.logger import setup_logger
```

---

### **3. execution/position_tracker.py**
**원본:** trading_executor.py 라인 540-661  
**클래스:** PositionTracker  
**메서드:**
- `__init__()` (546-564)
- `track_new_position()` (566-589)
- `check_tp_sl()` (591-644)
- `get_goal_progress()` (646-652)
- `get_active_positions()` (654-656)
- `get_daily_pnl()` (658-660)

**의존성:**
- `from common.calculations import tp_from_rr` (라인 572)

**필요 import:**
```python
import os
import time
from typing import Dict, Optional
from common.logger import setup_logger
from common.calculations import tp_from_rr
```

---

### **4. execution/executor.py**
**원본:** trading_executor.py 라인 30-278  
**클래스:** TradingExecutor  
**메서드:**
- `__init__()` (39-67)
- `execute_order()` (73-126)
- `_backtest_order()` (128-153)
- `_paper_order()` (155-172)
- `_live_order_with_retry()` (174-215)
- `_wait_for_fill()` (217-245)
- `_calculate_qty()` (251-273) - 사용 안 하지만 유지
- `get_mode()` (275-277)

**의존성:**
- `from .position_sizer import PositionSizer` (라인 52)
- `from .risk_manager import RiskManager` (라인 53)

**필요 import:**
```python
import os
import time
from typing import Dict, Optional
from datetime import datetime
from common.logger import setup_logger
from .position_sizer import PositionSizer
from .risk_manager import RiskManager
```

---

## 🔄 다음 단계

1. ✅ Phase 1 완료 (디렉터리 및 기본 구조)
2. ✅ Phase 2 완료 (파일 분할 - 4개 파일 생성)
3. ✅ Phase 3 완료 (trading_manager.py 리팩토링)
4. ⏳ Phase 4 진행 중 - 실행 스크립트 작성
5. ⏳ Phase 5 대기 - import 경로 수정

---

## 📝 Phase 2 완료 내역

**생성된 파일:**
1. `execution/position_sizer.py` - 118줄 (PositionSizer 클래스)
2. `execution/risk_manager.py` - 187줄 (RiskManager 클래스)
3. `execution/position_tracker.py` - 172줄 (PositionTracker 클래스)
4. `execution/executor.py` - 305줄 (TradingExecutor 클래스)

**특징:**
- 모든 파일에 원본 참조 주석 포함
- 실밥 리팩토링 주석 위치 명시
- 필요한 import만 포함
- 깔끔한 docstring 작성
- 다른 모듈(common, signals) 패턴 준수

---

## 📝 Phase 3 완료 내역

**생성된 파일:**
1. `execution/manager.py` - 277줄 (매매 오케스트레이션 함수들)

**리팩토링 내용:**
- ✅ `TradingBot` 클래스 → 순수 함수들로 변환
- ✅ `while True` 루프 제거 (실행 스크립트로 이동)
- ✅ `if __name__` 블록 제거
- ✅ 함수 분리:
  - `fetch_ensemble_decisions()`: 앙상블 결정 조회
  - `fetch_strategy_signals()`: 개별 전략 신호 조회
  - `fetch_signals()`: 전략별 신호 가져오기
  - `convert_to_order()`: 신호 → 주문 형식 변환
  - `save_trade()`: 거래 결과 DB 저장
  - `mark_as_executed()`: 실행 완료 표시
  - `process_trades()`: 메인 오케스트레이션 (1 사이클)

**주석 추가:**
- ✅ `trading_manager.py`: 헤더 및 각 섹션에 리팩토링 완료 주석
- ✅ `trading_executor.py`: 헤더 및 if __name__ 블록에 리팩토링 완료 주석

---

## 📝 Phase 4 완료 내역

**재작성된 파일:**
1. `run_trading.py` - 124줄 (매매 실행 스크립트)

**새로운 구조:**
- ✅ execution 모듈 import
- ✅ TradingExecutor 초기화
- ✅ manager.process_trades() 호출
- ✅ while 루프 구현
- ✅ signal handler (Ctrl+C 처리)
- ✅ .env 파일 지원
- ✅ 전략/모드 설정 지원

---

## 📚 참고 문서

- [REFACTORING.md](../architecture/REFACTORING.md)
- [TRADING_EXECUTOR.md](../architecture/TRADING_EXECUTOR.md)
- [PROJECT_STRUCTURE.md](../../PROJECT_STRUCTURE.md)

---

## 📝 Phase 5 완료 내역

**수정된 파일:**
1. `tests/test_full_flow.py` - import 경로 수정
2. `test_e2e_trading.py` - import 경로 수정
3. `trading_manager.py` - import 주석 추가

**변경 내용:**
- ✅ `from trading_executor import ...` → `from execution import ...`
- ✅ 모든 테스트 파일 호환성 확보

---

## 📝 Phase 6 완료 내역

**작성/업데이트된 문서:**
1. `docs/architecture/EXECUTION_MODULE.md` - 412줄 (완전 신규 작성)
2. `REFACTORING_COMPLETE.md` - Phase 9 추가
3. `PROJECT_STRUCTURE.md` - execution/ 모듈 반영

**문서 내용:**
- ✅ 모듈별 상세 설명
- ✅ 실행 흐름 다이어그램
- ✅ 환경 변수 가이드
- ✅ DB 스키마
- ✅ 테스트 예시
- ✅ 빠른 시작 가이드

---

**Last Updated:** 2025-10-19 16:00  
**Status:** Phase 6 완료 (문서화 완료)
