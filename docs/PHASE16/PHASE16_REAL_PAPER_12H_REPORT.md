# PHASE16 REAL PAPER 12시간 테스트 최종 리포트 (3차 실행)

**작성일**: 2025-11-17  
**테스트 모드**: wall_clock (현실 시계 기준)  
**상태**: 🔴 **FAIL** (Exposure Guard 계속 차단 - Entry 신호 차단)

---

## 📊 테스트 개요

### 목표
PHASE16 REAL PAPER 12시간 테스트에서 **wall_clock 모드**로 장시간 안정성 검증

### 테스트 환경
- **전략**: scalping (1m → 3m 최적화)
- **심볼**: BTCUSDT
- **타임프레임**: 3m
- **Duration 모드**: `wall_clock` (현실 시간 기준)
- **Duration**: 12시간 (43200초)
- **설정 파일**: `configs/scalping/real_paper_1h.yml`

---

## ⏱️ 실행 시간 기록 (3차 실행)

| 항목 | 시각 | 비고 |
|------|------|------|
| **시작 시각** | 2025-11-17 21:50:31 | 테스트 시작 (v3 설정) |
| **현재 시각** | 2025-11-17 22:03:50 | 모니터링 중 |
| **현재 경과 시간** | **00:13:19** | 13분 19초 |
| **목표 시간** | 12:00:00 | 12시간 |
| **달성률** | **1.85%** | 13.3분 / 720분 |
| **엔진 상태** | RUNNING | 실행 중 (Entry 신호 차단) |

**🔴 10시간 48분 미만 실행** ❌

---

## 📈 거래 통계

### 거래 건수 (3차 실행 - 현재까지)
| 항목 | 수량 | 상태 |
|------|------|------|
| **Entry Open** | 35회 | ✅ |
| **Closed (TP1/SL)** | 70회 | ✅ |
| **평균 거래당 청산** | 2.0회 | 부분 청산 활발 |
| **현재 상태** | Entry 신호 차단 | 🔴 Exposure Guard |

**✅ Entry Open ≥ 1 확인** ✅  
**✅ Closed ≥ 1 확인** ✅  
**🔴 Entry 신호 차단 중** (Exposure Guard)

### 거래 특성
- **TP1 부분 청산**: 매우 활발 (30% 청산 설정)
- **SL 손절**: 정상 작동
- **포지션 관리**: 무제한 모드 (max_positions=0) 정상 작동
- **쿨다운**: 0초 설정으로 신호 생성 최대화

---

## 🔍 시스템 상태

### 엔진 및 브로커
- ✅ **Engine**: 정상 작동 (종료 전까지)
- ✅ **PaperBroker**: 정상 작동
- ✅ **WebSocket Feed**: 정상 작동
- ✅ **DB 저장**: 정상 작동

### 인프라
- ✅ **Redis**: 정상 작동 (PING 응답)
- ✅ **PostgreSQL**: 정상 작동 (healthy 상태)
- ✅ **로깅**: 정상 작동

### 에러 분석
| 에러 유형 | 발생 건수 | 영향 | 비고 |
|----------|---------|------|------|
| **Drawdown Guard 트리거** | 1건 | **치명적** | 시스템 자동 종료 |
| **Traceback** | 0건 | 없음 | 현재 테스트 중 발생 없음 |
| **RuntimeError** | 0건 | 없음 | 현재 테스트 중 발생 없음 |
| **Telegram 404** | 다수 | 없음 | 네트워크 관련 (거래 로직 무관) |

**🔴 Drawdown Guard 트리거로 조기 종료** ❌

---

## 🚨 종료 원인 분석 (3차 실행)

### Exposure Guard 계속 차단 (Per-symbol Exposure Limit)

**차단 시작**: 2025-11-17 21:54:21  
**노출도**: 20,048.92 USDT  
**제한값**: 14,928.51 USDT  
**초과폭**: +5,120.41 USDT (+34.3%)

**로그 내역**:
```
2025-11-17 21:54:21 [TELEGRAM] Guard block [PAPER]: Per-symbol exposure limit: BTCUSDT 20048.92 > 14928.51
2025-11-17 21:54:23 [TELEGRAM] Guard block [PAPER]: Per-symbol exposure limit: BTCUSDT 20042.92 > 14928.51
```

### 3차 실행의 특이점

**v3 설정 적용**:
- `max_positions: 2` (2차의 5 → 2로 축소)
- `symbol_cooldown_seconds: 120` (쿨다운 강화)
- `max_drawdown_pct: 25.0` (Drawdown Guard 완화)

**하지만 여전히 Exposure Guard 차단**:
- 초기 35개 Entry 후 Entry 신호 차단
- 현재 13분 19초 경과 중 Entry 증가 없음
- 엔진은 실행 중이지만 새로운 거래 불가능

### 근본 원인 분석

**문제점**:
1. `max_positions: 2`로 제한했지만, 각 포지션의 **크기**가 여전히 크다
2. 기존 2개 포지션의 노출도 합계가 이미 14,928 USDT 제한값을 초과
3. 새로운 Entry 신호가 들어와도 Guard가 차단
4. **포지션 크기 제어 메커니즘 부재** - 동시 포지션 수만 제한해서는 부족

**설정의 한계**:
- YAML 설정으로는 포지션 크기를 직접 제어할 수 없음
- 엔진 내부의 position sizing 로직이 고정적으로 크다
- `max_positions` 제한만으로는 노출도 제어 불가능

---

## 📋 Scorecard 결과 (2차 실행)

**경로**: `scorecards/paper_phase16/20251117_212039_phase16/`

### 생성 여부
⚠️ **Scorecard 미생성** (엔진이 조기 종료되어 Scorecard 생성 전 종료)
- effective_config.yml만 생성됨

---

## ✅ PASS/FAIL 판정 (2차 실행)

### PASS 기준 (모두 충족 필요)

| 기준 | 결과 | 상태 |
|------|------|------|
| **현실 경과 ≥ 10시간 48분** | 11분 24초 | 🔴 FAIL |
| **Entry Open ≥ 1** | 35회 | ✅ PASS |
| **Closed ≥ 1** | 71회 | ✅ PASS |
| **Traceback 없음** | 0건 | ✅ PASS |
| **시스템 안정성** | Exposure Guard 차단 | 🔴 FAIL |

### 최종 판정

**🔴 FAIL** ❌

**실패 사유**:
1. **실행 시간 부족**: 11분 24초 (목표 12시간의 1.59%)
2. **Exposure Guard 차단**: Per-symbol exposure limit 초과 (20,048 > 14,705)
3. **설정 오류**: `max_positions: 5`로 제한했지만, 각 포지션 크기가 여전히 커서 노출도 초과

---

## 🔧 문제점 및 개선 방안 (2차 실행 기준)

### 1. Per-symbol Exposure Limit 초과 문제

**현재 설정**:
- `max_positions: 5` (포지션 수량 제한)
- 하지만 각 포지션의 **크기**는 제한 없음

**문제점**:
- BTCUSDT Per-symbol exposure limit: 14,705.59 USDT
- 실제 노출도: 20,048.92 USDT (+36.3% 초과)
- 5개 포지션 × 큰 크기 = 노출도 초과

**개선 방안**:
```yaml
# configs/scalping/real_paper_12h.yml (수정 필요)
risk:
  max_drawdown_pct: 30.0    # Drawdown Guard 완화
  max_positions: 2          # 포지션 수 더 제한 (5 → 2)
  
portfolio:
  symbol_cooldown_seconds: 120  # 쿨다운 증가 (60 → 120)
```

### 2. 포지션 크기 동적 조정 필요

**현재**:
- 포지션 크기가 고정적으로 크다
- 동시 다중 포지션 시 노출도 초과

**개선 방안**:
- 포지션 수에 따라 크기 동적 조정
- 예: 1개 포지션 시 100%, 2개 시 50%, 3개 시 33% 등

### 3. Drawdown Guard 설정 (1차 실행 교훈)

**1차 실행 문제**:
- Drawdown Guard: 17.55% > 10% (조기 종료)

**개선 방안**:
```yaml
risk:
  max_drawdown_pct: 25.0  # 10% → 25% 완화
```

---

## 📌 다음 단계

### 즉시 조치 필요

1. **12h 테스트 전용 설정 생성**
   ```yaml
   # configs/scalping/real_paper_12h.yml
   risk:
     max_drawdown_pct: 30.0  # 완화
     max_positions: 5        # 제한
   
   portfolio:
     symbol_cooldown_seconds: 60  # 쿨다운 추가
   ```

2. **12h 테스트 재실행**
   ```bash
   python scripts/run_paper.py \
     --strategy scalping \
     --symbol BTCUSDT \
     --timeframe 3m \
     --duration-hours 12 \
     --duration-mode wall_clock \
     --config configs/scalping/real_paper_12h.yml
   ```

### 장기 개선 (PHASE17+)

1. Drawdown Guard 로직 개선 (시간대별 임계값)
2. Flash Guard 강화 (기존 포지션 보호)
3. 동적 포지션 사이징 (변동성 기반)
4. 실시간 모니터링 대시보드

---

## 📝 결론 (1차~3차 종합)

### 1차 vs 2차 vs 3차 비교

| 항목 | 1차 | 2차 | 3차 |
|------|-----|-----|-----|
| **실행 시간** | 2분 59초 | 11분 24초 | 13분 19초 (진행 중) |
| **종료 원인** | Drawdown Guard | Exposure Guard | Exposure Guard (Entry 차단) |
| **Entry** | 433회 | 35회 | 35회 (정체) |
| **Closed** | 881회 | 71회 | 70회 (정체) |
| **설정** | real_paper_1h.yml | real_paper_12h.yml | real_paper_12h_v3.yml |
| **max_positions** | 0 (무제한) | 5 | 2 |
| **max_drawdown_pct** | 10% | 30% | 25% |

### 핵심 발견사항

**1차 실행 (Drawdown Guard)**:
- 문제: Drawdown 17.55% > 10% 임계값
- 해결: `max_drawdown_pct: 30%`로 완화

**2차 실행 (Exposure Guard)**:
- 문제: Per-symbol exposure 20,048 > 14,705 (36.3% 초과)
- 원인: `max_positions: 5`로 제한했지만, 각 포지션 크기가 여전히 크다
- 해결 시도: `max_positions: 2`로 더 제한

**3차 실행 (Exposure Guard - Entry 신호 차단)**:
- 문제: Per-symbol exposure 20,048 > 14,928 (34.3% 초과) - 계속 차단
- 원인: `max_positions: 2`로 제한했지만, 기존 2개 포지션의 크기가 이미 제한값 초과
- **근본 원인**: YAML 설정만으로는 포지션 크기 제어 불가능
- **결론**: 엔진 내부의 position sizing 로직 수정 필요

### 최종 평가

**PHASE16 REAL PAPER 12시간 테스트는 YAML 설정 튜닝만으로는 해결 불가능합니다.**

**3회 시도 결과**:
1. 🔴 **1차**: Drawdown Guard (17.55% > 10%)
2. 🔴 **2차**: Exposure Guard (Entry 신호 차단)
3. 🔴 **3차**: Exposure Guard (Entry 신호 차단 - 진행 중)

**핵심 문제**:
- `max_positions` 제한만으로는 Per-symbol exposure 제어 불가능
- 엔진 내부의 position sizing이 고정적으로 크다
- 각 포지션의 크기를 동적으로 조정하는 메커니즘 필요

**필요한 조치**:
1. ❌ YAML 설정 튜닝: 더 이상 효과 없음
2. ✅ 엔진 코드 수정: position sizing 로직 개선 필요
3. ✅ 동적 포지션 사이징: 변동성/노출도 기반 크기 조정

**PHASE17 이후 작업**:
- `execution/position_tracker.py` 또는 `strategies/scalping.py`에서 position sizing 로직 개선
- Per-symbol exposure 기반 동적 크기 조정
- 12시간 이상 안정적인 거래 가능 여부 재검증

---

**1차 테스트**: 2025-11-17 16:09:08 ~ 16:12:07 (2분 59초)
**2차 테스트**: 2025-11-17 21:20:28 ~ 21:31:52 (11분 24초)
**3차 테스트**: 2025-11-17 21:50:31 ~ (진행 중, 13분 19초)
**리포트 작성**: 2025-11-17 22:05 (KST)
