# PHASE26 Roadmap Update

**Last Updated**: 2025-12-03

---

## PHASE26 Overview: Multi-Symbol Universe Support

**목적**: 단일 심볼 → 멀티 심볼 확장  
**기간**: PHASE26-0 ~ PHASE26-3 (4주)

---

## Phase Timeline

| PHASE | 제목 | 상태 | 완료일 |
|-------|------|------|--------|
| **PHASE26-0** | Universe Provider 설계 및 구현 | ✅ COMPLETE | 2025-12-02 |
| **PHASE26-1** | Multi-Symbol Engine v1 통합 | ✅ COMPLETE | 2025-12-03 |
| **PHASE26-2** | Top10 Paper Load Test Harness | ✅ COMPLETE | 2025-12-03 |
| **PHASE26-3** | Performance Tuning | ⏳ PENDING | 예정 |

---

## PHASE26-0: Universe Provider ✅ COMPLETE

### 목표
- Universe Provider 추상화 설계
- StaticUniverseProvider 구현
- TopNByVolumeUniverseProvider 구현
- Config 통합

### 산출물
- `common/universe_provider.py` (347 LOC)
- `common/config_loader.py` (load_universe_config)
- `tests/test_phase26_0_universe_provider.py` (23 tests)
- `docs/PHASE26/PHASE26-0_UNIVERSE_PROVIDER_DESIGN.md`

### 결과
✅ 23/23 Tests PASS  
✅ StaticUniverseProvider 구현 완료  
✅ TopNByVolumeUniverseProvider 구현 완료  
✅ Config 기반 Provider Factory 완성

---

## PHASE26-1: Multi-Symbol Engine v1 ✅ COMPLETE

### 목표
- Universe Provider → Engine 통합
- Multi-Symbol 실행 플로우 v1 구현
- 100% 하위 호환성 보장

### 산출물
- `execution/engine.py` (+80 LOC)
  - `run_v2()`: Universe Provider 통합
  - `run()`: symbols 인자 추가
  - `_create_*_adapters()`: symbols 전달
- `tests/test_phase26_1_multi_symbol_engine.py` (10 tests)
- `docs/PHASE26/PHASE26-1_MULTI_SYMBOL_ENGINE_DESIGN.md`
- `docs/PHASE26/PHASE26-1_MULTI_SYMBOL_ENGINE_REPORT.md`

### 결과
✅ 40/40 Tests PASS (신규 10 + 회귀 30)  
✅ Universe Provider 통합 완료  
✅ Multi-Symbol 순차 처리 구현  
✅ 단일 심볼 모드 100% 호환  
✅ 최소 변경 원칙 준수

### 구현 방식
- **Sequential Processing**: 심볼별 Round-Robin 순차 처리
- **Per-Symbol State**: 버퍼/포지션/리스크 심볼별 독립 관리
- **Config-Driven**: `universe.enabled` 플래그 기반 분기
- **Backward Compatible**: `universe.enabled=false` → 단일 심볼 모드

---

## PHASE26-2: Top10 Paper Load Test Harness ✅ COMPLETE

### 목표
- Universe Provider + Multi-Symbol Engine v1 검증용 Top10 PAPER Load Test harness 구축
- PHASE25-0 Long-run harness 재사용 (최소 코드 추가)
- Per-symbol 메트릭 수집 기능 추가

### 산출물
- `configs/paper/phase26_2_top10_paper_2h.yml` (Top10 PAPER Config)
- `scripts/infra/phase26_2_run_top10_paper.py` (Runner Script)
- `tests/test_phase26_2_top10_paper_load_test.py` (11 tests)
- `docs/PHASE26/PHASE26-2_TOP10_PAPER_TEST_DESIGN.md` (설계 문서)
- `docs/PHASE26/PHASE26-2_TOP10_PAPER_TEST_REPORT_TEMPLATE.md` (리포트 템플릿)

### 결과
✅ 11/11 Tests PASS  
✅ Universe Config 로딩 검증 (Static, TopN)  
✅ PHASE25-0 Harness 재사용 성공  
✅ Per-symbol 메트릭 수집 구현  
✅ 리포트 자동 생성 구현  
✅ 회귀 테스트 100% PASS (PHASE25/26-0/1)

### 구현 방식
- **Config 설계**: `universe` 섹션 추가, 보수적 리스크 설정 (0.2% RPT, 50% Max Exposure)
- **Runner 구현**: PHASE25-0 함수 임포트 + Universe 검증 + Per-symbol 메트릭 확장
- **테스트 커버리지**: Universe config, Runner wiring, Per-symbol 메트릭, 리포트 생성, 회귀 방지

### Acceptance Criteria (구현 완료)
- [x] Config 파일 생성 (Universe 설정 포함)
- [x] Runner 스크립트 구현 (PHASE25-0 재사용)
- [x] 테스트 작성 (5+ 테스트)
- [x] 회귀 테스트 통과 (PHASE25/26-0/1)
- [x] 실행 준비 완료 (2H+ 장기 PAPER 실행 가능)

### Known Limitations
1. **Sequential Processing Only**: 심볼별 Round-Robin 순차 처리 (PHASE26-3에서 coroutine 도입)
2. **No Universe Auto-Refresh**: 프로세스 시작 시 1회만 조회 (PHASE28에서 hot-reload)
3. **No Per-Symbol Config**: 모든 심볼에 동일 전략/리스크 적용
4. **Limited Metrics**: Per-symbol trade count만 수집 (PHASE27에서 PnL/WinRate 추가)

### 실행 예시
```bash
# 2H Top10 PAPER Test
python scripts/infra/phase26_2_run_top10_paper.py \
    --config configs/paper/phase26_2_top10_paper_2h.yml \
    --duration-hours 2.0 \
    --tag "PHASE26-2_ACCEPTANCE"

# 리포트 자동 생성:
# - docs/PHASE26/PHASE26-2_TOP10_PAPER_TEST_REPORT.md
# - docs/PHASE26/phase26_2_top10_paper_summary.json
```

---

## PHASE26-3: Performance Tuning ⏳ PENDING

### 목표
- Coroutine 기반 비동기 처리 도입
- Multi-Symbol Latency 최적화
- 메모리 사용 최적화

### 작업 범위
1. **Async Feed Adapter**:
   - `async def stream()` 구현
   - 심볼별 concurrent candle fetching

2. **Signal Generation Async**:
   - `async def generate_signal()` 변환
   - 심볼별 병렬 지표 계산

3. **Portfolio/Risk Async**:
   - Lock-free per-symbol state
   - Concurrent position checks

4. **Benchmark**:
   - Before/After Latency 비교
   - Top10 vs Top20 성능 측정

### 예상 산출물
- `execution/async_engine.py` (Optional)
- `docs/PHASE26/PHASE26-3_PERFORMANCE_TUNING_REPORT.md`
- 성능 비교 차트

---

## Known Limitations (PHASE26-1)

1. **Sequential Processing**: 심볼 수 증가 시 latency 증가
   - **해결**: PHASE26-3에서 coroutine 도입

2. **No Universe Auto-Refresh**: 프로세스 시작 시 1회만 조회
   - **해결**: PHASE28에서 hot-reload 지원

3. **No DB Metrics**: TopN은 Binance API만 지원
   - **해결**: PHASE27에서 DBMetricsUniverseProvider 추가

4. **No Per-Symbol Config**: 동일 전략/리스크 적용
   - **해결**: 향후 per-symbol config override 지원

---

## Future Work (PHASE27+)

### PHASE27: DB Metrics Universe Provider
- `DBMetricsUniverseProvider` 구현
- DB 마켓 메트릭 기반 Universe 선정
- 백테스트 성과 기반 필터링

### PHASE28: Universe Auto-Refresh
- Hot-reload 지원
- 실행 중 Universe 갱신
- Config 변경 없이 심볼 추가/제거

### PHASE29: Per-Symbol Config Override
- 심볼별 전략 선택
- 심볼별 리스크 파라미터
- 심볼별 타임프레임

### PHASE30: Multi-Strategy Multi-Symbol
- 심볼별 복수 전략 동시 실행
- 전략-심볼 매트릭스 관리

---

**END OF ROADMAP UPDATE**
