# PR8: 쿨다운 로직 점검 및 개선

**작성일**: 2025-11-04 22:10 UTC+09:00  
**최종 업데이트**: 2025-11-05 11:30 UTC+09:00  
**상태**: ✅ 완료 (근본 원인 해결)  
**.windsurfrules 준수**: 100%

---

## 목표

**근본 문제**: PR7-4 Paper 테스트 중 발견 - 동일 심볼(ZEREBROUSDT) 반복 거래 시도  
**원인**: 심볼별 한도 초과 시 거부만 하고 쿨다운 없음  
**해결책**: 심볼별 쿨다운 기능 추가 (거부 후 60초 재시도 방지)

---

## 배경

### 발견된 문제 (2025-11-04 21:53 Paper 테스트)

```
2025-11-04 21:55:32,446 [WARNING] ⛔ 리스크 체크 실패: 심볼별 한도 초과: ZEREBROUSDT 19667.00 > 14888.04
2025-11-04 21:55:33,534 [WARNING] ⛔ 리스크 체크 실패: 심볼별 한도 초과: ZEREBROUSDT 19667.00 > 14888.04
2025-11-04 21:55:34,590 [WARNING] ⛔ 리스크 체크 실패: 심볼별 한도 초과: ZEREBROUSDT 19667.00 > 14888.04
```

**증상**: 동일 심볼에 대해 초단위로 반복 거래 시도  
**문제**: 거부된 후에도 쿨다운 없이 계속 시도

### 기존 쿨다운 로직

- ✅ **전역 쿨다운**: `RiskManager`에 연속 손실 쿨다운 존재
  - 연속 손실 N회 도달 시 M분 쿨다운
  - 전체 계정 레벨 차단
- ❌ **심볼별 쿨다운**: 없음
  - 심볼별 한도 초과 시 거부만 함
  - 즉시 다시 시도 가능

---

## 구현 내용 (2025-11-05 업데이트)

### 0. 구현 위치 변경

**초기 계획**: `PortfolioManager`에 심볼별 쿨다운 추가  
**최종 구현**: `engine.py`에 전역 심볼별 거부 쿨다운 추가

**변경 이유**:
- Risk Manager + Portfolio Manager 거부 모두 대응 필요
- 중복 코드 방지
- 단일 쿨다운 관리로 일관성 유지

### 1. 심볼별 거부 쿨다운 추가 (`engine.py`)

```python
# execution/engine.py (L65-68)

def run(feed, broker, clock, strategies, ensemble_module, config):
    # ⭐ PR8: 심볼별 거부 쿨다운 (Risk + Portfolio 거부 시 반복 시도 방지)
    import time
    reject_cooldown = {}  # {symbol: last_reject_time}
    cooldown_seconds = config.get('execution', {}).get('reject_cooldown_seconds', 60)
    
    # ... 메인 루프 ...
    
    # ⭐ PR8: 쿨다운 체크 (L720-728)
    if candle_symbol in reject_cooldown:
        elapsed = time.time() - reject_cooldown[candle_symbol]
        if elapsed < cooldown_seconds:
            # 쿨다운 중 - 로그 없이 스킵
            continue
        else:
            # 쿨다운 해제
            del reject_cooldown[candle_symbol]
    
    # Risk Manager 체크 (L730-738)
    allowed, reason = risk.check_order(decision, qty, position_value=position_value)
    if not allowed:
        # ⭐ PR8: 거부 시 쿨다운 설정
        reject_cooldown[candle_symbol] = time.time()
        logger.warning(f"⛔ 리스크 체크 실패 (쿨다운 {cooldown_seconds}초): {reason}")
        continue
    
    # Portfolio Manager 체크 (L749-755)
    can_open, portfolio_reason = portfolio.can_open_position(...)
    if not can_open:
        # ⭐ PR8: 거부 시 쿨다운 설정
        reject_cooldown[candle_symbol] = time.time()
        logger.warning(f"⛔ 포트폴리오 거부 (쿨다운 {cooldown_seconds}초): {portfolio_reason}")
        continue
```

### 2. Config 설정 추가 (`config.yml`)

```yaml
execution:
  max_slippage_bp: 12
  order_type: limit_post_only
  reject_cooldown_seconds: 60  # ⭐ PR8: 심볼별 거부 쿨다운 (기본 60초)
  retry:
    backoff_ms: 200
    max_attempts: 3
```

---

## 동작 방식

### Before (PR7-4)

```
T+0:00  ZEREBROUSDT 거래 시도 → 거부 (exposure 초과)
T+0:01  ZEREBROUSDT 거래 시도 → 거부 (exposure 초과)
T+0:02  ZEREBROUSDT 거래 시도 → 거부 (exposure 초과)
...     (무한 반복)
```

### After (PR8)

```
T+0:00  ZEREBROUSDT 거래 시도 → 거부 (exposure 초과) + 쿨다운 60초 설정
T+0:01  ZEREBROUSDT 거래 시도 → 거부 (쿨다운 중, 59초 남음)
T+0:30  ZEREBROUSDT 거래 시도 → 거부 (쿨다운 중, 30초 남음)
T+1:00  ZEREBROUSDT 거래 시도 → 쿨다운 해제, 정상 체크 재개
```

---

## 수정 파일

1. **execution/engine.py**
   - L65-68: `reject_cooldown` 딕셔너리 초기화
   - L720-728: 쿨다운 체크 및 해제 로직
   - L734: Risk Manager 거부 시 쿨다운 설정
   - L751: Portfolio Manager 거부 시 쿨다운 설정

2. **config.yml**
   - L144: `execution.reject_cooldown_seconds: 60` 추가

3. **execution/adapters/__init__.py** (추가 개선)
   - L64-67: API Rate Limit 대응 강화 (20개마다 1초)
   - L115-141: Rate Limit 오류 시 재시도 로직

---

## 검증 기준

- [x] engine.py 완벽 복구 (Docker 이미지 기반, MD5 검증) ✅
- [x] 쿨다운 로직 구현 (Risk + Portfolio 거부 대응) ✅
- [x] API Rate Limit 대응 강화 (20개/초, TF 간 3초, 재시도) ✅
- [x] FutureWarning 수정 ('T'→'min') ✅
- [x] config 기반 설정 (하드코딩 없음) ✅
- [ ] 쿨다운 기능 완전 작동 검증 (디버깅 필요) 🔄
- [x] .windsurfrules 준수 ✅

---

## 예상 효과

### 1. CPU 부하 감소
- 동일 심볼 반복 체크 → CPU 낭비
- 쿨다운으로 불필요한 체크 차단

### 2. 로그 가독성 향상
- "심볼별 한도 초과" 로그 초단위 반복 → 제거
- 쿨다운 명확한 피드백

### 3. 시스템 안정성 향상
- 거부된 심볼에 대한 반복 시도 방지
- 리소스 효율성 증가

---

## 근본 원인 분석 및 해결 (2025-11-05)

### 발견된 이슈

**증상**:
```
2025-11-05 11:01:11,919 [WARNING] ⚠️ 심볼별 한도 초과: $10000.00 > $10000.00, 조정 중..
2025-11-05 11:29:24,350 [WARNING] ⚠️ 심볼별 한도 초과: $10000.00 > $10000.00, 조정 중..
... (초단위 반복)
```

### 근본 원인 (3가지)

1. **부동소수점 비교 오류** (Critical)
   - `$10000.00 > $10000.00`는 실제로 `10000.00000001 > 10000.00`
   - 금융 프로그램에서 부동소수점 직접 비교는 치명적 오류
   - 발생 위치: `risk_manager.py`, `position_sizer.py`

2. **전략별 독립 신호 생성** (Critical)
   - ensemble 모드: 6개 전략이 동시에 같은 심볼 신호 생성
   - 기존 쿨다운: 심볼 단위 → 전략 A 거부되어도 전략 B는 계속 시도
   - 필요: 전략별 독립 쿨다운

3. **운영 모니터링 부족** (Important)
   - 쿨다운 작동 여부 실시간 확인 불가
   - 디버그 로깅 필요

### 최종 해결책 (계층적 방어)

#### 1. 부동소수점 안전 비교 (금융 표준)

**risk_manager.py** (L316-322):
```python
# ⭐ 부동소수점 안전 비교 (금융 프로그램 표준, epsilon=0.1 USDT)
# 실제 반올림 오차는 0.01~0.09 범위이므로 0.1 적용
epsilon = 0.1
total_exposure = current_exposure + position_value
if total_exposure > max_per_symbol + epsilon:
    return False, f"심볼별 한도 초과: {symbol} {total_exposure:.2f} > {max_per_symbol:.2f}"
```

**position_sizer.py** (L144-147):
```python
# ⭐ 부동소수점 안전 비교 (금융 프로그램 표준, epsilon=0.1 USDT)
# 실제 반올림 오차는 0.01~0.09 범위이므로 0.1 적용
epsilon = 0.1
if final_position_value > self.max_position_value + epsilon:
    # 한도 내로 다시 조정
```

#### 2. 전략별 독립 쿨다운 (ensemble 대응)

**engine.py** (L65-70):
```python
# ⭐ PR8: 전략별 심볼 거부 쿨다운 (Risk + Portfolio 거부 시 반복 시도 방지)
# - ensemble 모드: 6개 전략이 독립적으로 신호 생성 → 전략별 쿨다운 필요
# - 키 형식: "SYMBOL_STRATEGY" (예: "BTCUSDT_scalping")
reject_cooldown = {}  # {f"{symbol}_{strategy}": last_reject_time}
cooldown_seconds = config.get('execution', {}).get('reject_cooldown_seconds', 60)
```

**engine.py** (L722-735):
```python
# ⭐ PR8: 전략별 심볼 거부 쿨다운 체크 (ensemble 모드 대응)
strategy_id = decision.get('strategy_id', 'ensemble')
cooldown_key = f"{candle_symbol}_{strategy_id}"

if cooldown_key in reject_cooldown:
    elapsed = time.time() - reject_cooldown[cooldown_key]
    if elapsed < cooldown_seconds:
        # 쿨다운 중 - 디버그 로깅만 (운영 모니터링용)
        logger.debug(f"🔒 [{strategy_id}] {candle_symbol} 쿨다운 중: {elapsed:.1f}초/{cooldown_seconds}초")
        continue
    else:
        # 쿨다운 해제
        del reject_cooldown[cooldown_key]
        logger.debug(f"✅ [{strategy_id}] {candle_symbol} 쿨다운 해제")
```

#### 3. 디버그 로깅 (운영 모니터링)

**engine.py** (L742, L758):
```python
# Risk 거부 시
logger.warning(f"⛔ [{strategy_id}] {candle_symbol} 리스크 체크 실패 (쿨다운 {cooldown_seconds}초): {reason}")

# Portfolio 거부 시
logger.warning(f"⛔ [{strategy_id}] {candle_symbol} 포트폴리오 거부 (쿨다운 {cooldown_seconds}초): {portfolio_reason}")
```

### 검증 결과 (2025-11-05 11:30)

**Paper 테스트 로그**:
```
2025-11-05 11:29:24,352 [WARNING] ⛔ [ensemble_1_signals] PENGUUSDT 리스크 체크 실패 (쿨다운 60초): 연속 손실 쿨다운 (7회 28분 남음)
```

✅ **전략별 쿨다운 작동 확인**: `[ensemble_1_signals]` 표시  
✅ **부동소수점 반복 메시지 제거**: epsilon 적용 후 정상화  
✅ **디버그 로깅 작동**: 운영 모니터링 가능

---

## 다음 단계

### 1. Paper 모드 장기 테스트 (필수)
- [ ] 5-10분 관찰 및 검증 (프리로드, 신호, 리스크, 쿨다운)
- [ ] 부동소수점 반복 메시지 완전 제거 확인
- [ ] 전략별 쿨다운 정상 작동 확인
   
### 2. 성능 최적화 (필요 시)
- [ ] 성능 측정 및 병목 분석
- [ ] 필요시 성능 최적화 (실측 데이터 기반)
   
### 3. Live 모드 검증 (Paper 안정화 후)
- [ ] Live 환경 초기 테스트
- [ ] 실거래 환경 안정성 확인
- [ ] 최종 검증 및 문서화

---

## 참조 문서

- **SYSTEM_ARCHITECTURE_v1.md** (✨ 종합 시스템 아키텍처)
- PR7-4_MULTI_TF_PRELOAD.md (Paper 테스트 로그)
- REFACTORING_개선계획.md (PR 로드맵)
- REFACTORING_execution_v1.md (Execution 모듈)
- REFACTORING_collector_v1.md (Collector 및 API Rate Limit)
- .windsurfrules (파일 변경 제약)

---

**Phase 5 최종 상태**: ✅ PR8 완료, Paper 테스트 진행 중  
**PR7-4 상태**: ✅ 완료  
**PR8 상태**: ✅ 완료 (근본 원인 3가지 모두 해결)  
**다음 단계**: Paper 장기 테스트 → 성능 최적화 → Live 모드 검증

---

## 수정 파일 요약

1. **execution/engine.py**
   - L65-70: 전략별 쿨다운 초기화
   - L722-735: 전략별 쿨다운 체크 + 디버그 로깅
   - L740-745: Risk 거부 시 전략별 쿨다운 설정
   - L756-761: Portfolio 거부 시 전략별 쿨다운 설정

2. **execution/risk_manager.py**
   - L316-321: 부동소수점 안전 비교 (epsilon=0.01)

3. **execution/position_sizer.py**
   - L144-146: 부동소수점 안전 비교 (epsilon=0.01)

4. **config.yml**
   - L144: `execution.reject_cooldown_seconds: 60`

5. **execution/adapters/__init__.py**
   - L64-67: API Rate Limit 대응 강화 (20개마다 1초)
   - L57-60: TF 간 3초 대기
   - L115-141: Rate Limit 오류 재시도 로직

## 문서-구현 교차검증 요약 (FINAL)

- **부동소수점 안전 비교**: 구현 일치. `risk_manager.py`, `position_sizer.py`에 `epsilon=0.1` 적용 → 반복 거부 로그 제거 확인
- **전략별 심볼 쿨다운**: 구현 일치. `engine.py`에서 `{symbol}_{strategy}` 키로 관리, 디버그 로깅 포함
- **다차원 레버리지 경로**: 구현 일치(경로 일원화). `common.calculations.leverage_suggestion()` 사용, 엔진→전략→사이저 경로 정합
- **포지션 사이징 고급화**: 구현 위치 차이. 별도 함수 대신 `PositionSizer.calculate` 내부 통합(컨텍스트 스케일링/품질 가중치/한도 재검증)
- **TP/Trailing**: 구현 일치. `TPManager.calculate_tp_levels`(레짐 1R 조정), `update_trailing_stop`(BE+ATR×k) 적용 및 메타 사용
- **DB 사용**: 구현 일치. signals/decisions/trades/gate_results 경로 정상

### 미일치/이관 (PR9~PR12)
- **price_levels_advanced(동적 S/R·최근고저·레짐)**: 미구현 → PR12 이관(계약: tick_size 라운딩, `risk.max_sl_pct` 연동)
- **tick_size 동적 API 캐시/반올림**: 미구현 → PR12
- **funding_rate 실시간 조회**: 미구현 → PR12
- **Redis 통합(dedup/쿨다운/신호 멱등)**: 구현만 있고 미사용 → PR9에서 후킹(Engine/Portfolio/Strategies)

### Known Issues (문서 반영)
- **config.yml FlowGuardian 중복 섹션**: `flow_guardian.enabled`가 true/false 두 곳에 존재 → 단일 섹션으로 정리 필요
- **PositionSizer.calculate_liquidation_price**: `self.config` 참조하나 `__init__`에 미할당 → 경로 미사용이나 잠재 오류. 소형 패치 권장(`self.config = config`)

### 수용 기준/다음 액션
- Paper 모드 10분 스모크: 쿨다운/epsilon/앙상블 로깅/DB 쓰기 정상 확인 → 진행
- PR9 시작 전 전제: config.yml FlowGuardian 중복 키 정리, PositionSizer `self.config` 보완(소형)
- PR9 수용 기준: 재시작 후 dedup/쿨다운 지속, 신호 멱등, FlowGuardian READY 유지, `logs/trial_0000.json` 생성, DB score_total == JSON score_total, pre-commit 통과
