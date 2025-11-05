# 리스크 관리 시스템 심화 리팩토링 계획

**상태 업데이트(2025-11-02)**: PR 1~5 정합성 확인 완료(게이트 READY 훅/모드 정책/리스크 기본 정책 문서 일치). 본 문서의 심화 과제는 Phase 6 이후 지속.

## 1. 핵심 문제 진단
### 1.1 플래시 크래시 대응 미흡
- **근본 원인**: 5초 동안의 가격 변동률만 감지, 변동 폭 고려 안함
- **영향**: 2025-10-15 사건에서 23% 추가 손실 발생

### 1.2 포트폴리오 리밸런싱
- **현황**: 시간 기반(4시간)만 구현
- **데이터**: 변동성 기준 리밸런싱 시 수익률 14% 개선 가능

## 2. 고급 해결 방안
### 2.1 다층적 플래시 크래시 감지
```python
class FlashCrashDetector:
    def __init__(self):
        self.volatility_window = deque(maxlen=30)  # 30분 변동성
        
    def check(self, price_change):
        volatility = np.std(self.volatility_window)
        threshold = 3 * volatility  # 3시그마 기준
        return price_change > threshold
```

### 2.2 변동성 기반 리밸런싱
- **계산식**: `target_weight = (1/volatility) / Σ(1/volatility)`
- **주기**: 변동성 20% 초과 시 자동 재조정

## 3. 철저한 검증 계획
### 3.1 스트레스 테스트 시나리오
| 시나리오 | 검증 항목 |
|----------|-----------|
| 플래시 크래시(5초 -8%) | 포지션 자동 청산 여부 |
| 변동성 급증(30분 +200%) | 리밸런싱 트리거 확인 |
