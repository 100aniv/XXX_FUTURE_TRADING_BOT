# Config 파일 관리 가이드

**작성일**: 2025-10-30 07:50 UTC+09:00  
**목적**: Config 설정 변경 시 삭제 대신 주석 처리 규칙

---

## 🎯 핵심 원칙

> **"설정은 삭제하지 말고 주석 처리한다"**

### 이유
1. **재사용성**: 나중에 다시 필요할 때 즉시 활성화 가능
2. **기록 보존**: 과거 설정 이력 유지
3. **시간 절약**: 재작성 불필요
4. **실수 방지**: 설정값 유실 방지

---

## 📋 주석 처리 규칙

### 1. 기본 형식

```yaml
# ========================================
# 섹션 제목
# ========================================
section:
  active_option: value  # (현재 사용)
  
  # disabled_option: value  # (미사용, 보관용)
  # disabled_option2: value  # (미사용, 백업)
```

### 2. 상태 표시 주석

| 상태 | 주석 | 예시 |
|------|------|------|
| 사용 중 | `# (현재 사용)` | `mode: top100  # (현재 사용)` |
| 미사용 | `# (미사용, 보관용)` | `# mode: manual  # (미사용, 보관용)` |
| 테스트 | `# (테스트용)` | `# mode: all  # (테스트용)` |
| 백업 | `# (백업)` | `# old_value: 100  # (백업)` |
| 금지 | `# (사용 금지)` | `# dangerous_option: true  # (사용 금지)` |

### 3. 그룹화

**관련 설정끼리 묶기**:
```yaml
# --- Manual 모드 (미사용) ---
# mode: manual
# manual_list:
#   - BTCUSDT
#   - ETHUSDT
# --- Manual 모드 끝 ---
```

---

## 🔧 실전 예시

### Example 1: 심볼 선택 방식

**❌ 잘못된 방법 (삭제)**:
```yaml
symbols:
  mode: top100
```

**✅ 올바른 방법 (주석 처리)**:
```yaml
# ========================================
# 심볼 선택
# ========================================
symbols:
  mode: top100  # (현재 사용)
  top100:
    min_volume_24h: 5000000
    exclude_stablecoins: true
  
  # --- Manual 모드 (미사용, 보관용) ---
  # mode: manual
  # manual_list:
  #   - BTCUSDT
  #   - ETHUSDT
  #   - BNBUSDT
  # --- Manual 모드 끝 ---
  
  # --- Top50 모드 (미사용, 보관용) ---
  # mode: top50
  # top50:
  #   min_volume_24h: 10000000
  # --- Top50 모드 끝 ---
  
  # --- All 모드 (테스트용만, 운영 금지) ---
  # mode: all  # (사용 금지: 리소스 과다)
  # --- All 모드 끝 ---
```

---

### Example 2: 전략 필터

**❌ 잘못된 방법**:
```yaml
strategies:
  scalping:
    filters:
      mtf_confirm: false
      regime: true
```

**✅ 올바른 방법**:
```yaml
strategies:
  scalping:
    filters:
      mtf_confirm: false  # (현재 비활성화, 테스트 후 활성화 예정)
      regime: true  # (현재 사용)
      # volume_spike: true  # (미사용, 거래 빈도 낮아짐)
      # trend_alignment: true  # (미사용, 테스트 필요)
```

---

### Example 3: 리스크 프로파일

**❌ 잘못된 방법**:
```yaml
risk:
  profiles:
    paper:
      max_daily_loss_pct: 0.05
```

**✅ 올바른 방법**:
```yaml
risk:
  profiles:
    paper:
      max_daily_loss_pct: 0.05  # (현재: 5%)
      # max_daily_loss_pct: 0.02  # (백업: 2%, 보수적)
      # max_daily_loss_pct: 0.10  # (백업: 10%, 공격적, 테스트 전용)
      
      max_consecutive_losses: 7  # (현재)
      # max_consecutive_losses: 5  # (백업: 보수적)
      # max_consecutive_losses: 10  # (백업: 완화)
```

---

### Example 4: 청산 설정

**❌ 잘못된 방법**:
```yaml
exits:
  take_profit:
    tp1:
      enabled: true
      ratio: 1.0
```

**✅ 올바른 방법**:
```yaml
exits:
  # --- 손절 ---
  stop:
    k: 1.8  # (현재: ATR × 1.8)
    # k: 1.5  # (백업: 타이트)
    # k: 2.0  # (백업: 여유)
    type: atr  # (현재 사용)
    # type: fixed_pct  # (미사용, 고정 퍼센트)
  
  # --- 분할 익절 ---
  take_profit:
    tp1:
      enabled: true  # (현재 사용)
      ratio: 1.0  # (현재: 1R)
      # ratio: 0.8  # (백업: 빠른 익절)
      # ratio: 1.2  # (백업: 여유)
      partial_close_pct: 0.5  # (현재: 50% 청산)
      # partial_close_pct: 0.3  # (백업: 30%)
      # partial_close_pct: 0.7  # (백업: 70%)
    
    tp2:
      enabled: true  # (현재 사용)
      ratio: 2.0  # (현재: 2R)
      # enabled: false  # (비활성화 옵션)
```

---

## 🔄 변경 프로세스

### 1. 변경 전 백업
```bash
# Windows
Copy-Item config.yml config_backup_20251030.yml

# Linux/Mac
cp config.yml config_backup_$(date +%Y%m%d).yml
```

### 2. 변경 사항 주석 추가
```yaml
# 변경일: 2025-10-30
# 변경자: [이름]
# 변경 사유: 거래 빈도 증가 위해 필터 완화
```

### 3. 기존 설정 주석 처리
```yaml
# 기존 (2025-10-29까지 사용)
# filters:
#   mtf_confirm: true
#   regime: true
#   volume_spike: true

# 신규 (2025-10-30부터)
filters:
  mtf_confirm: false  # 완화
  regime: true  # 유지
  volume_spike: false  # 완화
```

### 4. 테스트 및 검증
```bash
# Config 문법 검증
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# 백테스트 실행
python main.py
```

### 5. 문서 업데이트
- 변경 이력 기록
- 성능 비교 기록
- 다음 변경 계획 작성

---

## 📊 변경 이력 템플릿

**config.yml 맨 위에 추가**:

```yaml
# ========================================
# Config 변경 이력
# ========================================
# 2025-10-30: 거래 빈도 증가 위해 scalping 필터 완화 (mtf_confirm, volume_spike OFF)
# 2025-10-29: 리스크 프로파일 paper 모드 5% → 5% (유지)
# 2025-10-28: Phase 4 완료, config 통합 및 하드코딩 제거
# ========================================
```

---

## ⚠️ 주의사항

### 1. 완전 삭제 가능한 경우
- **테스트 전용 임시 설정**
- **폐기된 기능** (코드에서 제거됨)
- **오타 수정**

### 2. 반드시 보관해야 하는 경우
- **프로덕션에서 사용했던 설정**
- **성능 벤치마크용 설정**
- **백업/복구용 설정**
- **A/B 테스트 대안**

### 3. 주석 설명 필수 항목
- **왜 비활성화했는지** (이유)
- **언제 다시 활성화할지** (조건)
- **대안이 있는지** (다른 옵션)

---

## 🎯 체크리스트

Config 변경 시 아래 항목을 모두 확인:

- [ ] 백업 파일 생성 (`config_backup_YYYYMMDD.yml`)
- [ ] 기존 설정 주석 처리 (삭제 금지)
- [ ] 상태 표시 주석 추가 (`# (현재 사용)`, `# (미사용, 보관용)`)
- [ ] 변경 이유 주석 추가
- [ ] 관련 설정 그룹화
- [ ] Config 문법 검증 (YAML 파싱)
- [ ] 로컬 테스트 (백테스트 또는 paper 모드)
- [ ] 변경 이력 업데이트 (파일 상단)
- [ ] Git 커밋 메시지에 변경 사유 명시
- [ ] 문서 업데이트 (관련 MD 파일)

---

## 📝 샘플 커밋 메시지

```
config: scalping 필터 완화 (거래 빈도 증가)

- mtf_confirm: true → false (주석 처리로 보관)
- volume_spike: true → false (주석 처리로 보관)
- regime: true 유지

기대 효과: 거래 빈도 1건/일 → 5-10건/일
백업: config_backup_20251030.yml
테스트: 백테스트 통과 (2024-01-01 ~ 2024-03-31)
```

---

## 🔗 관련 문서

- `PROJECT_ANALYSIS_COMPLETE.md`: 전체 프로젝트 분석
- `docs/PHASE5/REFACTORING_개선계획.md`: 개선 계획
- `docs/PHASE4/PHASE4_COMPLETE_AND_VERIFIED.md`: Phase 4 완료 보고서
