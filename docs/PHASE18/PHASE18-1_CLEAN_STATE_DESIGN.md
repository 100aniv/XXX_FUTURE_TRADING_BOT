# PHASE18-1: 실행 전 환경 초기화 스크립트 설계

**작성일**: 2025-11-19  
**목표**: 실행 간 상태 간섭 방지를 위한 clean-state 보장  
**우선순위**: P0 (필수)

---

## 1. Objective

**"실행마다 깨끗한 상태에서 시작"을 보장하여, 이전 실행의 잔여 상태로 인한 예측 불가능한 동작을 방지한다.**

### 1.1 Background

PHASE17 12H Acceptance 테스트 중 발견된 문제:
- Redis에 이전 실행의 Guard 상태가 남아있을 가능성
- DB에 이전 run_id의 포지션/트레이드가 혼재
- 로그 파일이 계속 누적되어 분석 어려움

### 1.2 Goal

다음을 자동으로 수행하는 표준 스크립트 작성:
1. **Redis 초기화**: Guard/Cooldown/Dedup 키 전체 삭제
2. **DB 초기화** (optional): run_id 기반 포지션/트레이드 삭제
3. **로그 백업**: 기존 로그를 타임스탬프 백업
4. **통합**: run_backtest.py / run_paper.py에 --clean-state 플래그 추가

---

## 2. Design

### 2.1 스크립트 구조

**파일**: `scripts/ops/init_clean_state.py`

**인터페이스**:
```bash
# 전체 초기화 (Redis + 로그)
python scripts/ops/init_clean_state.py

# Redis만 초기화
python scripts/ops/init_clean_state.py --redis-only

# DB도 초기화 (run_id 지정)
python scripts/ops/init_clean_state.py --db --run-id XXX

# 로그만 백업
python scripts/ops/init_clean_state.py --logs-only
```

### 2.2 Redis 초기화 범위

**삭제 대상 키 패턴**:
- `candle:seen:*` - Dedup 캔들 중복 제거 키
- `flow_guard:*` - FlowGuardian Guard 상태
- `cooldown:*` - 전략별 쿨다운 상태
- `signal:*` - 신호 큐 (optional)

**삭제 방법**:
```python
import redis
client = redis.Redis(host='localhost', port=6379)
patterns = ['candle:seen:*', 'flow_guard:*', 'cooldown:*']
for pattern in patterns:
    keys = client.keys(pattern)
    if keys:
        client.delete(*keys)
```

### 2.3 DB 초기화 범위

**삭제 대상** (run_id 기반):
- `positions` 테이블: `WHERE run_id = ?`
- `trades` 테이블: `WHERE run_id = ?`

**주의사항**:
- 기본적으로 DB 초기화는 실행하지 않음 (--db 플래그 필요)
- run_id를 명시하지 않으면 DB 초기화 안 함 (안전장치)

### 2.4 로그 백업

**대상 파일**:
- `logs/application.log`
- `logs/trading.log`

**백업 방식**:
```python
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_name = f"application.log.{timestamp}.bak"
# logs/application.log → logs/application.log.20251119_110000.bak
```

**새 로그 초기화**:
- 백업 후 빈 파일로 초기화

### 2.5 run_backtest.py / run_paper.py 통합

**추가 CLI 인자**:
```python
parser.add_argument(
    '--clean-state',
    action='store_true',
    default=False,
    help='실행 전 Redis/로그 초기화 (PHASE18)'
)
```

**실행 위치**:
```python
def main():
    args = parse_args()
    
    # 1. Clean-state 초기화 (필요 시)
    if args.clean_state:
        import subprocess
        result = subprocess.run([
            'python', 'scripts/ops/init_clean_state.py'
        ])
        if result.returncode != 0:
            logger.error("Clean-state 초기화 실패")
            sys.exit(1)
    
    # 2. 기존 실행 로직...
```

---

## 3. Acceptance Criteria

### 3.1 스크립트 단독 실행

- [ ] `python scripts/ops/init_clean_state.py` 실행 성공
- [ ] Redis 키 삭제 확인 (keys * 로 검증)
- [ ] 로그 백업 파일 생성 확인
- [ ] 콘솔에 초기화 전/후 상태 출력

### 3.2 run_paper.py 통합

- [ ] `python scripts/run_paper.py --clean-state ...` 실행 성공
- [ ] 실행 전 자동으로 초기화 수행 확인
- [ ] 로그에 "Clean-state initialized" 메시지 출력

### 3.3 안전성

- [ ] DB 초기화는 --db + --run-id 모두 지정 시만 실행
- [ ] Redis 연결 실패 시 경고 출력 후 계속 진행
- [ ] 로그 백업 실패 시에도 실행 중단 안 함

---

## 4. Implementation Plan

### 4.1 Phase 1: init_clean_state.py 작성

**구현 내용**:
- Redis 연결 및 키 삭제 함수
- DB 초기화 함수 (optional)
- 로그 백업 함수
- CLI 인자 파싱
- 메인 함수

### 4.2 Phase 2: run_paper.py / run_backtest.py 통합

**구현 내용**:
- --clean-state 플래그 추가
- 실행 전 init_clean_state.py 호출
- 초기화 성공/실패 로깅

### 4.3 Phase 3: 자동 테스트

**테스트 시나리오**:
1. Redis에 더미 키 생성
2. init_clean_state.py 실행
3. Redis 키 삭제 확인
4. run_paper.py --clean-state로 5분 실행
5. 로그 확인

---

## 5. Files to Create/Modify

### 5.1 신규 파일

- `scripts/ops/init_clean_state.py` (핵심 스크립트)

### 5.2 수정 파일

- `scripts/run_paper.py` (--clean-state 플래그 추가)
- `scripts/run_backtest.py` (--clean-state 플래그 추가)

---

## 6. Risks & Mitigations

| 리스크 | 완화 전략 |
|--------|----------|
| Redis 연결 실패 | 경고 출력 후 계속 진행 (Redis는 필수 아님) |
| 로그 백업 실패 | 경고 출력, 기존 로그 보존 |
| DB 초기화 오류 | --db + --run-id 명시적 지정 시만 실행 |
| 실행 중인 프로세스 간섭 | 스크립트는 실행 전에만 수행 (실행 중 절대 안 함) |

---

## 7. Next Steps (PHASE18-2)

PHASE18-1 완료 후:
- PHASE18-2: run_id 네임스페이스 전역 적용
- Redis 키를 `flow_guard:{run_id}:{symbol}` 형태로 변경
- DB 테이블에 run_id 인덱스 추가

---

**작성자**: Cascade AI  
**승인**: PHASE18-1 설계 완료
