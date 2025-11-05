# 튜닝 시스템 구조 (2025-10-25 리팩터링)

## 개요
Optuna 기반 베이지안 튜닝 시스템의 파일 구조를 간소화하여 유지보수성과 가독성을 향상.

## 디렉토리 구조

```
project_root/
├── scripts/
│   └── tuning/
│       └── tune_scalping.py          # 튜닝 스크립트 (이동됨)
├── configs/
│   └── scalping/
│       └── <tuning>/
│           ├── trial_0000.yml        # Trial 설정
│           ├── trial_0000_seg1.yml   # WFA 세그먼트별 설정
│           └── ...
├── logs/
│   └── tuning/
│       ├── trial_<tuning>_0000.json  # Trial 메트릭 (평탄화)
│       ├── trial_<tuning>_0001.json
│       └── ...
└── data/
    └── trading.db                     # 백테스트 결과 DB (공용)
```

## 주요 변경 사항

### 1. Trial Configs 경로
- **이전**: `logs/tuning/<study>/configs/trial_*.yml`
- **변경**: `configs/scalping/<tuning>/trial_*.yml`
- **이유**: 설정 파일은 코드/설정 전용 폴더에 위치하는 것이 관례에 부합

### 2. Trial Logs (JSON) 평탄화
- **이전**: `logs/tuning/<study>/logs/trial_*.json`
- **변경**: `logs/tuning/trial_<tuning>_<trial>.json`
- **이유**: 
  - 중첩 깊이 감소
  - 스터디 간 파일명 충돌 방지 (prefix로 구분)
  - 파일 탐색/관리 용이

### 3. 튜닝 스크립트 이동
- **이전**: `scripts/tune_scalping.py`
- **변경**: `scripts/tuning/tune_scalping.py`
- **이유**: 
  - 튜닝 관련 스크립트 그룹화
  - 향후 다른 전략 튜너 추가 시 일관성 유지

### 4. 유지 항목
- **Tuning DB**: `db/tuning/optuna.db` (Optuna 메타데이터, 단일 파일)
- **DB 스냅샷**: `logs/tuning/<tuning>/db/trial_*_seg*.db` (백테 전용 메트릭 계산용)
- **Backtest DB**: `data/trading.db` (공용, 매 실행마다 초기화)

## 실행 방법

### 기본 실행 (페이퍼 모드 권장)
```bash
python -u common/tuner_cli.py --strategy scalping --tuning scalping_v1 --trials 20
```

### 파라미터
- `--tuning`: 튜닝 이름 (프리셋/버전 구분용)
- `--trials`: 실행할 Trial 수
- (백테스트 튜너 전용) `--use-wfa`: WFA OOS 평가 활성화 (1=ON, 0=OFF)

## 파일 명명 규칙

### Trial Config
- 베이스: `trial_NNNN.yml`
- 세그먼트: `trial_NNNN_segN.yml`

### Trial Log (JSON)
- 형식: `trial_<tuning>_NNNN.json`
- 예시: `trial_scalping_v3_prod_0000.json`

### DB 스냅샷
- 형식: `trial_NNNN_segN.db`
- 위치: `logs/tuning/<tuning>/db/`

## 메트릭 수집 흐름

```
1. Trial 실행 (6개 OOS 세그먼트)
   ↓
2. 각 세그먼트 실행 후:
   - data/trading.db를 세그먼트별 스냅샷으로 복사
   - 스냅샷에서 TUNING_VIBLE 점수 계산
   ↓
3. 6개 세그먼트 평균 점수 산출
   ↓
4. Trial 메트릭 저장:
   - logs/tuning/trial_<tuning>_NNNN.json
   ↓
5. TEST_CHECKLIST.md 자동 업데이트
```

## 리팩터링 효과

### 장점
1. **디렉토리 깊이 감소**: 3단계 → 2단계
2. **파일 위치 직관성**: 설정은 configs/, 로그는 logs/
3. **튜닝 간 충돌 방지**: 파일명에 tuning 이름 포함
4. **유지보수 용이**: 관련 파일 그룹화
5. **기존 인프라 활용**: data/trading.db, logs/ 재사용

### 마이그레이션
- 기존 `runs/` 폴더: 삭제됨 (더 이상 생성되지 않음)
- 기존 스터디 (`logs/tuning/<old_study>/`): 보존 (수동 정리 가능)

## 향후 확장

### Docker 병렬화 (예정)
- Postgres 기반 Optuna Storage 전환
- 다중 워커로 세그먼트 병렬 평가
- 현재 구조 유지하면서 성능만 향상

### 다른 전략 튜너
- `scripts/tuning/tune_reversion.py`
- `scripts/tuning/tune_breakout.py`
- 동일한 구조 패턴 적용

## 참고 문서
- [TEST_SCENARIO.md](TEST_SCENARIO.md): 테스트 시나리오
- [TUNING_VIBLE.md](TUNING_VIBLE.md): 100점 만점 시스템
- [RUNBOOK_CHECKLIST.md](RUNBOOK_CHECKLIST.md): 실행 가이드
