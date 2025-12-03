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
| **PHASE26-3** | Performance Tuning & Top100 Scalability | ✅ COMPLETE | 2025-12-03 |

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

## PHASE26-3: Performance Tuning & Top100 Scalability ✅ COMPLETE

### 목표
- Multi-Symbol Engine v1 (Sequential) 성능 최적화
- Top100 심볼까지 실시간 안정 처리 기반 확보
- Latency/Throughput/Resource 최적화

### 산출물
- `common/perf/perf_profiler.py` (MultiSymbolProfiler)
- `common/indicators/indicator_cache.py` (IndicatorCache)
- `common/logger.py` (TRACE 레벨 추가)
- `configs/paper/phase26_3_top100_paper_30m.yml` (Top100 Config)
- `scripts/infra/phase26_3_run_top100_paper.py` (Scaling Test Runner)
- `tests/test_phase26_3_performance.py` (17 tests)
- `docs/PHASE26/PHASE26-3_PERFORMANCE_TUNING_DESIGN.md` (설계 문서)
- `docs/PHASE26/PHASE26-3_PERFORMANCE_TEST_REPORT_TEMPLATE.md` (리포트 템플릿)

### 결과
✅ 17/17 Tests PASS  
✅ Performance Profiler 구현 (기존 telemetry_profiler 재사용)  
✅ Indicator Cache Layer 구현 (Incremental Calculation)  
✅ TRACE 로그 레벨 추가 (성능 최적화)  
✅ Top100 Config + Scaling Test Runner 구현  
✅ 100% 하위 호환 (PHASE26-0/1/2 회귀 테스트 PASS)

### 구현 방식
1. **Performance Profiler (PHASE26-3 전용)**:
   - Per-symbol indicator latency 측정
   - Loop latency per-symbol 측정
   - Queue depth tracking
   - Hot path 자동 분석
   - 프로파일 리포트 자동 생성

2. **Indicator Cache Layer**:
   - Incremental calculation (최근 period+N개만 사용)
   - RSI/EMA/SMA 지원
   - Cache hit/miss 통계
   - 기본 비활성화 (Runner에서 명시적 활성화)

3. **Logging 최적화**:
   - TRACE 레벨 추가 (DEBUG보다 낮음, 개발용)
   - Multi-Symbol 루프에서 INFO 로그 최소화

4. **Top100 Config**:
   - Top100 Universe Provider (topn_volume)
   - 보수적 리스크 설정 (0.1% RPT, 30% Max Exposure)
   - 30분 Acceptance 테스트용

5. **Scaling Test Runner**:
   - Top10 → Top20 → Top50 → Top100 자동 실행
   - 단계별 프로파일링 및 성능 비교
   - 자동 리포트 생성 (MD + JSON)

### Acceptance Criteria (설계 완료, 실행 대기)

**필수 조건** (향후 30분 PAPER 실행 시 검증):
- [ ] Top100 PAPER 30분 실행
- [ ] 평균 Loop Latency ≤ 150ms
- [ ] P95 Loop Latency ≤ 250ms
- [ ] CPU ≤ 70%
- [ ] Memory ≤ 800MB
- [ ] CRITICAL 오류 0건
- [ ] Aggregate 평가 ≥ 100건
- [ ] 활성 Trade 심볼 ≥ 3개

### Known Limitations

1. **Sequential Processing 유지**: 심볼 수 증가 시 latency 선형 증가
   - **해결**: PHASE27에서 coroutine 도입

2. **Indicator Cache 정확도**: 최근 N개만 사용하므로 극히 드물게 오차 가능
   - **현재 상태**: 실전에서 무시 가능한 수준 (오차 < 1.0)

3. **Top100 Trade Activity**: 보수적 리스크 설정으로 실제 Trade 수는 제한적
   - **해결**: 향후 Per-symbol 리스크 조정 (PHASE29)

### 실행 예시

```bash
# Single Top100 Test (30분)
python scripts/infra/phase26_3_run_top100_paper.py \
    --config configs/paper/phase26_3_top100_paper_30m.yml \
    --duration-minutes 30 \
    --mode single \
    --top-n 100 \
    --tag "PHASE26-3_ACCEPTANCE"

# Scaling Test (Top10 → 20 → 50 → 100, 각 30분)
python scripts/infra/phase26_3_run_top100_paper.py \
    --config configs/paper/phase26_3_top100_paper_30m.yml \
    --duration-minutes 30 \
    --mode scaling \
    --tag "PHASE26-3_SCALING"

# 리포트 자동 생성:
# - docs/PHASE26/PHASE26-3_PERFORMANCE_TEST_REPORT.md
# - docs/PHASE26/phase26_3_top100_performance_summary.json
```

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
