# PHASE16+ Engine Structural Fixes
=====================================================
날짜: 2025-11-17  
목적: Paper Trading 거래 발생 차단 문제 근본 해결

---

## 문제 요약

### 증상
- Paper Trading 실행 시 신호는 생성되지만 거래 체결 0건
- 로그 메시지:
  - `[ENTRY BLOCK] reason=portfolio_check_failed detail="포지션 최대 한강 도달: 20개"`
  - `[ENTRY BLOCK] reason=scalping_cooldown_active remaining_seconds=50~60`

### 근본 원인

1. **포트폴리오 초기 상태 문제** (CRITICAL)
   - 위치: `execution/portfolio_manager.py` 라인 605-664
   - 문제: `_load_existing_positions()` 메서드가 DB의 **모든 OPEN 포지션**을 로드
   - 결과: 이전 Paper 세션의 포지션(최대 20개)이 새 세션에서도 유지됨
   - 영향: 초기부터 max_positions 제한 도달 → 새 진입 불가능

2. **쿨다운 설정 이중 관리** (SECONDARY)
   - 엔진 레벨: `execution/engine.py` 라인 1147-1150
   - 포트폴리오 레벨: `execution/portfolio_manager.py` 라인 69
   - 문제: 두 쿨다운이 중첩되어 작동, 기본값 60초
   - 영향: 빠른 재시도 불가능

---

## 구조적 수정 내역

### 수정 1: Paper 모드 포트폴리오 깨끗한 시작

**파일**: `execution/engine.py` 라인 169-178

**변경 전**:
```python
is_backtest_mode = mode in ['backtest', 'backtest_clean', 'backtest_raw']
portfolio = PortfolioManager(config, load_existing=not is_backtest_mode)
```

**변경 후**:
```python
is_backtest_mode = mode in ['backtest', 'backtest_clean', 'backtest_raw']
is_paper_test_mode = mode == 'paper' and config.get('paper', {}).get('clean_start', True)
load_existing = not (is_backtest_mode or is_paper_test_mode)

if is_paper_test_mode:
    logger.info("🔄 [PAPER TEST] 깨끗한 시작: 기존 포지션 로드 스킵")

portfolio = PortfolioManager(config, load_existing=load_existing)
```

**효과**:
- Paper 모드에서 `clean_start: True` 설정 시 기존 포지션 무시
- 항상 0개 포지션에서 시작

---

### 수정 2: run_paper.py에 clean_start 플래그 추가

**파일**: `scripts/run_paper.py` 라인 138

**추가**:
```python
cfg['paper']['clean_start'] = True  # ⭐ PHASE16+: 깨끗한 시작
```

**효과**:
- 모든 Paper 테스트가 자동으로 깨끗한 상태에서 시작

---

### 수정 3: Paper 테스트 전용 설정 파일 생성

**파일**: `configs/scalping/paper_testing.yml` (신규)

**내용**:
```yaml
# Portfolio 제한 완화
portfolio:
  symbol_cooldown_seconds: 5  # 60초 → 5초
  max_positions: 0  # 20개 → 무제한 (0 = 제한 없음)

# 실행 설정 완화
execution:
  reject_cooldown_seconds: 5  # 60초 → 5초

# 전략 쿨다운 완화
strategies:
  scalping:
    entry_cooldown_seconds: 3  # 5초 → 3초

# 리스크 설정 완화
risk:
  max_positions: 0  # 무제한
  per_trade: 0.01  # 1% (명확한 거래 확인)
  profiles:
    paper:
      max_daily_loss_pct: 0.50  # 50%
      max_consecutive_losses: 50  # 50회
      cooldown_after_consecutive: 5  # 5초
```

**목적**:
- 거래 발생 여부 검증에 집중
- Production 설정과 명확히 분리
- Testing ONLY (Live 사용 금지)

---

### 수정 4: run_paper.py에서 테스트 설정 자동 오버레이

**파일**: `scripts/run_paper.py` 라인 113-131

**추가**:
```python
# Paper 테스트 설정 자동 오버레이
paper_test_config_path = Path("configs/scalping/paper_testing.yml")
if paper_test_config_path.exists():
    logger.info("📝 Paper 테스트 설정 로드 중...")
    with open(paper_test_config_path, 'r', encoding='utf-8') as f:
        paper_overlay = yaml.safe_load(f)
    
    # Deep merge
    for section in ['portfolio', 'execution', 'risk', 'strategies']:
        if section in paper_overlay:
            cfg[section].update(paper_overlay[section])
```

**효과**:
- 자동으로 테스트 설정 적용
- CLI 인자 없이 실행 가능

---

### 수정 5: base.yml을 Production 설정으로 복원

**파일**: `configs/base.yml`

**복원**:
```yaml
portfolio:
  symbol_cooldown_seconds: 60  # Production: 60s

risk:
  max_positions: 20  # Production: 20개
```

**목적**:
- Production 안정성 유지
- Testing 설정과 분리

---

## 설정 전환 방식

### Production (Live/Real Paper)
- **파일**: `configs/base.yml`
- **특징**: 보수적, 안전 우선
- **쿨다운**: 60초
- **max_positions**: 20개

### Testing (Paper Testing)
- **파일**: `configs/scalping/paper_testing.yml` (오버레이)
- **특징**: 완화, 거래 발생 확인
- **쿨다운**: 3~5초
- **max_positions**: 무제한 (0)

### 전환 방법
- **자동**: `scripts/run_paper.py` 실행 시 자동으로 testing 설정 적용
- **수동**: `--config` 인자로 다른 설정 파일 지정 가능

---

## 검증 체크리스트

### 엔진 로그 확인
```
✅ 🔄 [PAPER TEST] 깨끗한 시작: 기존 포지션 로드 스킵
✅ 📝 Paper 테스트 설정 로드 중...
✅   Portfolio cooldown: 5s
✅   Max positions: 0
```

### 실행 중 확인
```bash
# 1. 프로세스 상태
Get-Process python

# 2. Redis 활성도
docker exec trading_redis redis-cli DBSIZE

# 3. 로그 분석
Get-Content logs\application.log -Tail 100 | Select-String "ENTRY CHECK|ENTRY BLOCK"
```

### 60분 시점 확인
```bash
# Scorecard 존재 여부
Get-ChildItem scorecards\paper_phase16 -Recurse -Filter "scorecard.csv"

# 거래 체결 여부
Get-Content logs\application.log | Select-String "FILLED|closed" -CaseSensitive
```

---

## 알려진 제한사항

1. **DB 포지션 정리 안 함**
   - 이전 Paper 세션의 OPEN 포지션이 DB에 남아 있음
   - 하지만 `load_existing=False`로 무시됨
   - 향후: DB 정리 스크립트 추가 고려

2. **Broker 포지션과 Portfolio 포지션 분리**
   - Broker의 `open_positions`는 별도 관리
   - 현재: run_paper.py에서 수동 초기화 유지

3. **Redis 쿨다운**
   - Redis FLUSHALL 후에도 엔진 재시작 전까지 메모리 쿨다운 유지 가능
   - 해결: 프로세스 완전 종료 후 재시작

---

## 향후 개선 사항

1. **DB 포지션 정리**
   - Paper 모드 시작 시 DB의 paper 포지션을 자동으로 CLOSED 처리
   - 또는 mode별 포지션 필터링 강화

2. **쿨다운 통합**
   - 엔진 레벨과 포트폴리오 레벨 쿨다운 통합
   - 단일 소스로 관리

3. **설정 검증**
   - 시작 시 effective_config.yml의 핵심 값 검증
   - 잘못된 설정 조기 감지

---

## 참고 문서

- `docs/PHASE16_REAL_PAPER_MODE.md`: Paper Trading 실행 가이드
- `execution/engine.py`: 통합 엔진 구현
- `execution/portfolio_manager.py`: 포트폴리오 관리
- `configs/scalping/paper_testing.yml`: Testing 전용 설정
