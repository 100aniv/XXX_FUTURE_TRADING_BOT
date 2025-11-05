# 백테스트 시스템 심화 리팩토링 계획

## 1. 핵심 문제 진단

### 1.1 결과 재현성 부족
- **근본 원인**: 랜덤 시드 관리 부재, 환경 종속성
- **영향**: 동일 파라미터로 6.3% 결과 차이 발생
- **데이터**: 2025-10-15 백테스트 3회 실행 시 PnL 편차 6.3%

### 1.2 멀티스레드 안정성
- **현황**: 병렬 백테스트 시 18% 확률로 데드락
- **원인**: DB 연결 공유, 락 관리 미흡
- **영향**: 튜닝 시 프로세스 멈춤

### 1.3 리소스 누수
- **현황**: 백테스트 종료 후 DB 연결 미종료
- **데이터**: 24시간 튜닝 시 연결 풀 고갈 (512개 → 0개)

## 2. 고급 해결 방안

### 2.1 재현성 보장 시스템
```python
class ReproducibleBacktest:
    def __init__(self, seed: int = 42):
        self.seed = seed
        
    def setup(self):
        # Python 랜덤 시드
        random.seed(self.seed)
        
        # NumPy 시드
        np.random.seed(self.seed)
        
        # 환경변수 고정
        os.environ['PYTHONHASHSEED'] = str(self.seed)
        
    def teardown(self):
        # 리소스 정리
        self.close_all_connections()
```

### 2.2 안전한 병렬 처리
```python
class SafeParallelBacktest:
    def __init__(self, max_workers: int = 4):
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        
    def run_parallel(self, configs: List[dict]):
        # 각 프로세스에 독립 DB 연결
        futures = []
        for cfg in configs:
            future = self.executor.submit(self._run_isolated, cfg)
            futures.append(future)
        
        return [f.result() for f in as_completed(futures)]
    
    def _run_isolated(self, cfg: dict):
        # 독립 DB 연결 생성
        with get_isolated_db_connection() as conn:
            return run_backtest(cfg, conn)
```

### 2.3 리소스 관리
```python
class ResourceManager:
    def __init__(self):
        self.connections = []
        
    def __enter__(self):
        self.conn = create_connection()
        self.connections.append(self.conn)
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for conn in self.connections:
            conn.close()
        self.connections.clear()
```

## 3. 철저한 검증 계획

### 3.1 재현성 테스트
| 시나리오 | 검증 항목 |
|----------|-----------|
| 동일 시드 3회 실행 | PnL 차이 < 0.01% |
| 다른 시드 3회 실행 | 통계적 유사성 검증 |
| 환경 변경 (OS/Python) | 결과 일치 확인 |

### 3.2 병렬 안정성 테스트
- 100회 병렬 실행 → 데드락 0건
- 메모리 사용량 안정성 (±5% 이내)
- CPU 활용률 (>80%)

### 3.3 리소스 누수 테스트
- 1000회 백테스트 연속 실행
- DB 연결 수 모니터링 (≤ max_connections × 0.8)
- 메모리 누수 없음 확인

## 4. 체크리스트

### 시드 관리
- [ ] `ReproducibleBacktest` 클래스 구현
- [ ] 모든 백테스트 진입점에 시드 설정 추가
- [ ] 시드 값 로그 저장

### 병렬 처리
- [ ] `SafeParallelBacktest` 클래스 구현
- [ ] DB 연결 풀 크기 동적 조정
- [ ] 프로세스별 독립 메모리 공간 확보

### 리소스 관리
- [ ] Context Manager 패턴 적용
- [ ] `finally` 블록에 리소스 해제 추가
- [ ] 리소스 누수 모니터링 추가

### 테스트
- [ ] 재현성 테스트 스크립트 작성
- [ ] 병렬 안정성 테스트 작성
- [ ] 리소스 누수 테스트 작성
- [ ] CI/CD 파이프라인 통합

## 5. 마이그레이션 계획

### 1단계: 재현성 구현 (1주)
- 시드 관리 시스템 구축
- 기존 백테스트에 적용
- 검증 스크립트 작성

### 2단계: 병렬 처리 개선 (2주)
- 독립 DB 연결 구조 구현
- 락 최소화 설계
- 성능 벤치마크

### 3단계: 리소스 관리 (1주)
- Context Manager 적용
- 자동 정리 메커니즘
- 모니터링 대시보드

## 6. 예상 리스크

1. **시드 관리 오버헤드**
   - 대책: 시드 설정은 초기화 1회만 수행

2. **병렬 처리 복잡도 증가**
   - 대책: 프로세스 풀 크기 제한 (CPU 코어 수)

3. **DB 연결 풀 고갈**
   - 대책: 연결 풀 크기 동적 조정, 타임아웃 설정

## 7. 성공 지표

- **재현성**: 동일 시드 시 PnL 차이 < 0.01%
- **안정성**: 100회 병렬 실행 시 데드락 0건
- **리소스**: 1000회 실행 후 연결 수 안정 (±10% 이내)
- **성능**: 병렬 실행 시 단일 실행 대비 3.5배 이상 속도 향상
