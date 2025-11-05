# PR7 테스트 방법론 검토

**작성**: 2025-11-03 10:50  
**목적**: Paper 모드 전략별 Docker vs 앙상블 접근 방법 비교

---

## 현재 접근 (개별 Docker)

### 구조
```bash
# Scalping만 실행
docker compose --profile paper-scalping up -d

# 6개 전략 각각 실행
docker compose --profile paper up -d  # 6개 컨테이너
```

### 장점
- ✅ **독립성**: 전략별 완전 격리
- ✅ **실거래 확인**: 각 전략의 실제 거래 발생 테스트
- ✅ **개발 효율**: 수정 시 해당 전략만 재시작
- ✅ **디버깅**: 로그/메모리 분리

### 단점
- ❌ **리소스 소모**: 6개 컨테이너 = 6× 메모리/CPU
- ❌ **시간 소모**: 각 전략이 신호 조건 충족 대기 (scalping도 43분에 0건)
- ❌ **앙상블 미검증**: 전략 간 조합/가중치 검증 불가
- ❌ **포트폴리오 미검증**: 전체 리스크 관리 검증 불가

---

## 대안: 앙상블 Paper 모드

### 구조
```yaml
# config.yml
strategy:
  use_ensemble: true  # 앙상블 활성화
  selector: null      # 모든 전략 활성

mode: paper           # Paper 모드 (실거래 X)
```

### 동작
1. **모든 전략 동시 실행** (1개 컨테이너)
2. **신호 생성**: 6개 전략 모두 `signal_logic()` 호출
3. **앙상블 조합**: `ensemble.combine_signals()` 가중치 적용
4. **실거래 없음**: Paper 모드이므로 실제 주문 없음
5. **DB 기록**: 모든 신호/결정 기록 (`trading.decisions` 테이블)

### 장점
- ✅ **리소스 절약**: 1개 컨테이너 = 1× 메모리/CPU
- ✅ **전체 흐름 검증**: 앙상블 + 포트폴리오 + 리스크 관리
- ✅ **신호 빈도**: 6개 전략 → 더 많은 신호 기회
- ✅ **튜닝 준비**: 앙상블 가중치 최적화 가능
- ✅ **DB 분석**: `trading.decisions`로 각 전략 기여도 분석

### 단점
- ⚠️ **실거래 미검증**: Paper 모드이므로 실제 거래 없음
- ⚠️ **전략별 격리 없음**: 한 전략 에러가 전체 영향

---

## 권장 접근: 하이브리드

### Phase 1: 앙상블 Paper (현재 → 익일)
**목적**: 전체 흐름 검증, 신호 빈도 확인

```bash
# 1. config.yml 수정
strategy:
  use_ensemble: true
  selector: null

# 2. 실행
docker compose --profile paper-scalping up -d  # 1개만 사용

# 3. 24시간 실행
# 4. DB 확인
SELECT strategy_id, COUNT(*) 
FROM trading.decisions 
GROUP BY strategy_id;
```

**수용 기준**:
- ✅ 6개 전략 모두 신호 생성 (각 ≥1건)
- ✅ 앙상블 조합 동작
- ✅ 포트폴리오/리스크 관리 동작
- ✅ DB 기록 정상

### Phase 2: 개별 전략 Paper (필요시)
**목적**: 특정 전략 실거래 검증 (문제 발견 시만)

```bash
# 문제 전략만 격리 테스트
docker compose --profile paper-scalping up -d

# 실거래 1건 이상 확인
SELECT * FROM trading.trades WHERE strategy_id='scalping';
```

### Phase 3: Live 진입
**목적**: 소액 실거래

```bash
# config.yml
mode: live
equity: 100  # $100부터 시작

# 앙상블 또는 개별 전략
strategy:
  use_ensemble: true  # 또는 false + selector: scalping
```

---

## 결론 및 권장사항

### 즉시 적용 (오늘)
1. **앙상블 Paper 모드로 전환**
   - `config.yml`: `use_ensemble: true`
   - 1개 컨테이너로 6개 전략 동시 실행
   - 24시간 실행

2. **신호 빈도 확인**
   - `trading.decisions` 테이블 조회
   - 각 전략별 신호 건수 확인

3. **조건 완화 (필요시)**
   - Scalping `volume_spike: false`
   - 다른 전략도 필요시 완화

### 다음 단계 (익일)
1. **앙상블 결과 분석**
   - 전략별 기여도
   - 신호 조합 패턴
   - 포트폴리오 제약 빈도

2. **개별 전략 검증 (선택)**
   - 앙상블에서 문제 발견 시
   - 특정 전략만 격리 테스트

3. **Live 준비**
   - $100 소액 시작
   - 앙상블 or 단일 전략 선택

---

## 테이블 비교

| 항목 | 개별 Docker (현재) | 앙상블 Paper (권장) |
|------|-------------------|-------------------|
| 컨테이너 | 6개 | 1개 |
| 메모리 | ~720MB | ~120MB |
| 격리 | ✅ 완전 | ⚠️ 공유 |
| 앙상블 검증 | ❌ 불가 | ✅ 가능 |
| 신호 빈도 | 낮음 (1전략) | 높음 (6전략) |
| 실거래 | ✅ 가능 | ❌ Paper만 |
| 디버깅 | ✅ 쉬움 | ⚠️ 복잡 |
| 리소스 | ❌ 많음 | ✅ 적음 |
| 개발 속도 | ✅ 빠름 | ⚠️ 재시작 필요 |

---

## 최종 판단

**✅ 앙상블 Paper 모드 우선 추천**

**이유**:
1. **PR7 목적**: 전체 흐름 검증 (앙상블 포함)
2. **신호 빈도**: 6개 전략 → 더 많은 검증 기회
3. **리소스**: 1개 컨테이너로 충분
4. **실거래**: Paper 모드여서 리스크 없음
5. **튜닝 준비**: 앙상블 가중치 최적화 기반

**개별 Docker 사용 시기**:
- 특정 전략 에러 격리
- 전략별 실거래 검증
- 개발 중 수정/재시작 반복

**하이브리드 권장**:
- 평소: 앙상블 Paper (전체 검증)
- 문제 시: 개별 Docker (격리 디버깅)
- Live: 앙상블 or 단일 (성과 기준)
