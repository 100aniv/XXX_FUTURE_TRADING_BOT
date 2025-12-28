# PHASE36-2 S8: LIVE Mode Final Validation (Shadow OFF)

**작성일**: 2025-12-28  
**작성자**: Windsurf Cascade  
**Baseline**: 0b9924fd (S7 PASS 완료 후)  
**상태**: 📋 PLANNED (S7 완료 후 진입)

---

## 📋 Executive Summary

PHASE36-2 S8은 **실제 주문 제출을 활성화한 LIVE 모드 최종 검증** 단계입니다. S7에서 Shadow Mode로 6시간 장시간 안정성을 입증했으므로, 이제 Shadow Mode를 해제하고 실제 주문 제출/체결/수수료/슬리피지가 정상 작동하는지 검증합니다.

**목표**: 1~2시간 동안 최소 1~5건의 실제 거래를 발생시켜, 전체 트레이딩 파이프라인(신호 생성 → 주문 제출 → 체결 → DB 저장 → PnL 계산)이 Production 환경에서 정상 작동함을 증명합니다.

---

## 🎯 목표 (Objectives)

### 주요 목표
1. **Shadow Mode OFF**: Live adapters에서 실제 주문 제출 활성화
2. **실거래 검증**: 1~5건의 실제 주문 제출 및 체결
3. **체결/수수료/슬리피지**: 실제 비용 발생 및 훅 작동 확인
4. **DB 저장**: 거래 기록 100% DB persist
5. **PnL 추적**: 실제 손익 계산 및 포트폴리오 업데이트
6. **리스크 가드**: Position Sizing, Risk Manager, Budget Cap 실전 작동
7. **에러 대응**: 429/Rate Limit 발생 시 Backoff 로직 작동

### S7과의 차이점
| 항목 | S7 (Shadow Mode) | S8 (Shadow OFF) |
|------|------------------|-----------------|
| 주문 제출 | 차단 (0건) | 활성화 (1~5건) |
| 체결 | 없음 | 실제 체결 |
| 수수료/슬리피지 | 없음 | 실제 발생 |
| PnL | 시뮬레이션 | 실제 계산 |
| 리스크 가드 | 로직만 작동 | 실제 포지션 제한 |
| Duration | 6시간 | 1~2시간 (충분) |

---

## 🚨 Acceptance Criteria (AC)

| AC | 내용 | 검증 방법 |
|----|------|----------|
| **AC-1** | 실행 완료 (Exit Code 0) | 1~2h 후 정상 종료 확인 |
| **AC-2** | 주문 제출 ≥ 1건 | Telemetry `order_submitted_total >= 1` |
| **AC-3** | 주문 체결 ≥ 1건 | Telemetry `order_filled_total >= 1` |
| **AC-4** | DB 저장 100% | `db_insert_success == order_filled_total` |
| **AC-5** | PnL 계산 정상 | PortfolioManager equity 변동 확인 |
| **AC-6** | 에러 0건 | ERROR/CRITICAL 로그 0건 |
| **AC-7** | 리스크 가드 작동 | Position Sizing, Budget Cap 적용 확인 |

**PASS 조건**: 7/7 AC 충족  
**CONDITIONAL PASS**: 6/7 AC 충족 (AC-6 제외 가능, 단 에러 해결 필요)  
**FAIL**: AC-2, AC-3 미달 (거래 미발생)

---

## 📝 실행 계획 (Execution Plan)

### 1. Pre-flight 준비 (5분)

#### 1.1 환경 확인
```bash
# 가상환경 활성화
.\trading_bot_env\Scripts\Activate.ps1

# Docker 상태 확인
docker ps | Select-String "trading"

# Gate 실행 (fast + regression)
python scripts/helpers/run_gates_with_evidence.py
```

#### 1.2 Config 준비
- 파일: `configs/live/phase36_2_s8_live_final_validation.yml`
- 설정:
  - **Shadow Mode**: `false` (주문 제출 활성화)
  - **Duration**: 1~2 hours (wall_clock)
  - **Symbol**: BTCUSDT
  - **Timeframe**: 15m
  - **Checkpoint Interval**: 30 minutes
  - **Strategy**: scalping (기존 검증된 전략)

#### 1.3 Redis/DB 초기화
```bash
# Redis cooldown/guard 초기화
redis-cli FLUSHDB

# DB portfolio 초기화 (선택)
# (또는 기존 상태 유지하여 연속성 테스트)
```

### 2. 실행 (1~2시간)

#### 2.1 실행 명령
```bash
python scripts/run_live.py --config configs/live/phase36_2_s8_live_final_validation.yml
```

#### 2.2 모니터링 (실시간)
- **주기**: 10~15분마다 로그 확인
- **확인 항목**:
  - 신호 생성 여부
  - 주문 제출 로그 (`[ORDER]` 태그)
  - 체결 확인 로그 (`[FILL]` 태그)
  - 에러 발생 여부
  - WebSocket 연결 상태

#### 2.3 자동 종료
- Duration 만료 시 자동 종료
- Exit Code 0 확인

### 3. 검증 (30분)

#### 3.1 Telemetry 분석
```bash
# Checkpoint 파일 확인
ls logs/checkpoints/phase36_2_s8_live_final_validation/

# Telemetry 요약
python scripts/report_telemetry_checkpoints.py \
  --checkpoint-dir logs/checkpoints/phase36_2_s8_live_final_validation \
  --output docs/PHASE36/PHASE36_2_S8_CHECKPOINT_REPORT.md
```

#### 3.2 DB 검증
```sql
-- 거래 기록 확인
SELECT COUNT(*) FROM trades WHERE created_at > '2025-12-28 12:00:00';

-- DB persist 확인
SELECT order_id, status, filled_qty FROM trades ORDER BY created_at DESC LIMIT 10;
```

#### 3.3 로그 분석
```powershell
# ERROR/CRITICAL 카운트
$log = Get-Content "logs\application\2025-12-28.log" -Encoding UTF8
($log | Select-String "\[ERROR\]" | Measure-Object).Count
($log | Select-String "\[CRITICAL\]" | Measure-Object).Count
```

### 4. 문서화 (30분)

#### 4.1 최종 리포트 작성
- 파일: `docs/PHASE36/PHASE36_2_S8_LIVE_FINAL_VALIDATION_REPORT.md`
- 내용:
  - 실행 결과 요약
  - AC 검증 결과
  - Telemetry 분석
  - 거래 내역 (익명화)
  - PnL 추적
  - 에러/이슈 (있을 경우)
  - 최종 판정

#### 4.2 Evidence 저장
- JSON: `logs/evidence/phase36_2_s8_live_final_validation_evidence.json`
- 포함 항목:
  - 실행 시간
  - Exit code
  - 주문 제출/체결 수
  - DB persist 성공률
  - PnL 결과
  - AC 통과 여부

### 5. SSOT 동기화 (15분)

#### 5.1 ROADMAP 업데이트
- `PHASE_ROADMAP.md`: S8 섹션 추가

#### 5.2 CHECKPOINT 업데이트
- `CHECKPOINT_2025-12-21_ENSANBLE_MID_REVIEW.md`: S8 완료 반영

### 6. Git Commit & Push (10분)

```bash
git add configs/live/phase36_2_s8_live_final_validation.yml \
        docs/PHASE36/PHASE36_2_S8_*.md \
        logs/evidence/phase36_2_s8_*.json \
        PHASE_ROADMAP.md \
        CHECKPOINT_2025-12-21_ENSANBLE_MID_REVIEW.md

git commit -m "PHASE36-2 S8: LIVE Mode Final Validation PASS - Real Trading Verified"

git push origin main
```

---

## ⚠️ 위험 요소 및 대응책

### 위험 1: 신호 미발생 (거래 0건)
**원인**: 시장 조건이 전략 조건에 맞지 않음  
**대응**:
- Duration을 2~3시간으로 연장
- 또는 다른 시간대(변동성 높은 시간) 재실행
- Config 조정 (진입 조건 완화)

### 위험 2: API Rate Limit 429 발생
**원인**: 주문 빈도가 Binance 제한 초과  
**대응**:
- Backoff 로직 작동 확인
- 429 발생 카운트 기록
- 필요 시 cooldown 조정

### 위험 3: 체결 실패 (슬리피지 과다)
**원인**: 시장 유동성 부족 또는 주문 크기 과다  
**대응**:
- Position Sizing 검증
- 슬리피지 허용 범위 Config 확인
- 거래 시간대 조정 (유동성 높은 시간)

### 위험 4: DB 저장 실패
**원인**: DB 연결 끊김 또는 트랜잭션 에러  
**대응**:
- DB connection pool 상태 확인
- `db_insert_failed` 카운터 모니터링
- 실패 시 재시도 로직 작동 확인

---

## 📊 성공 기준 (Success Criteria)

### Minimum Viable Success (MVS)
- ✅ 주문 제출 1건 이상
- ✅ 주문 체결 1건 이상
- ✅ DB 저장 100%
- ✅ Exit Code 0

### Full Success
- ✅ MVS + 주문 3~5건
- ✅ PnL 정상 계산
- ✅ 리스크 가드 실전 작동
- ✅ 에러 0건

### Exceptional Success
- ✅ Full Success + 429 Backoff 검증
- ✅ 수수료/슬리피지 실제 측정
- ✅ Position Sizing 동적 조정 확인

---

## 🔗 관련 문서

### 선행 단계
- `docs/PHASE36/PHASE36_2_S6_LIVE_SHADOW_MODE_FINAL_REPORT.md` (S6)
- `docs/PHASE36/PHASE36_2_S7_SHADOW_LONGRUN_6H_REPORT.md` (S7)

### 참고 Config
- `configs/live/phase36_2_s7_shadow_longrun_6h.yml` (S7 base)

### Evidence 경로
- `logs/evidence/phase36_2_s7_6h_shadow_longrun_evidence.json` (S7)

---

## 📅 Timeline

| 단계 | 소요 시간 | 누적 시간 |
|------|-----------|-----------|
| Pre-flight | 5분 | 5분 |
| 실행 (LIVE) | 1~2시간 | 1h 5m ~ 2h 5m |
| 검증 | 30분 | 1h 35m ~ 2h 35m |
| 문서화 | 30분 | 2h 5m ~ 3h 5m |
| SSOT 동기화 | 15분 | 2h 20m ~ 3h 20m |
| Git Commit | 10분 | 2h 30m ~ 3h 30m |

**총 예상 시간**: 2.5 ~ 3.5시간

---

## ✅ 체크리스트

### Pre-flight
- [ ] 가상환경 활성화
- [ ] Docker 정상 실행 확인
- [ ] Gate 3단 PASS (fast + regression)
- [ ] Config 파일 준비 (shadow_mode: false)
- [ ] Redis/DB 초기화 (선택)

### 실행
- [ ] LIVE 모드 실행 (run_live.py)
- [ ] 실시간 모니터링 (10~15분 간격)
- [ ] 주문 제출 확인 (로그)
- [ ] 체결 확인 (로그)
- [ ] 정상 종료 (Exit Code 0)

### 검증
- [ ] Telemetry checkpoint 파일 확인
- [ ] DB 거래 기록 확인
- [ ] 로그 분석 (ERROR/CRITICAL)
- [ ] AC 7개 검증

### 문서화
- [ ] 최종 리포트 작성
- [ ] Evidence JSON 생성
- [ ] ROADMAP 업데이트
- [ ] CHECKPOINT 업데이트

### Git
- [ ] git add (모든 변경 파일)
- [ ] git commit (의미 있는 메시지)
- [ ] git push origin main

---

## 🎯 Next Steps (S8 완료 후)

### S8 PASS 시
- ✅ **PHASE36-2 완료 선언**
- 🔜 **Production Deployment 준비**
- 🔜 **PHASE37: Scaling & Optimization**

### S8 FAIL/CONDITIONAL 시
- 🔧 **원인 분석 및 수정**
- 🔄 **S8 재실행**
- 📋 **Post-Mortem 문서 작성**

---

**작성 완료**: 2025-12-28  
**Baseline**: PHASE36-2 S7 PASS (0b9924fd)  
**Status**: ✅ PLAN READY
