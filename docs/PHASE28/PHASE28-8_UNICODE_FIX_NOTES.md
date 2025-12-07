# PHASE28-8: Unicode 로깅 오류 완전 해결

**Date**: 2025-12-08  
**Status**: ✅ **FIXED**

---

## 📋 문제 요약

PHASE28-7 Smoke Backtest 실행 중 Unicode (한글/이모지) 문자 출력 시 Windows 환경에서 인코딩 오류 발생:
- **증상**: 로그 출력 시 `UnicodeEncodeError` 또는 `PermissionError` 발생
- **영향**: 백테스트 결과 로그를 확인할 수 없음
- **근본 원인**: 
  1. Windows 콘솔 기본 인코딩이 cp949 (한글 Windows)
  2. `TimedRotatingFileHandler`의 파일 로테이션 시 PermissionError

---

## 🔧 수정 내용

### 1. 콘솔 Handler UTF-8 강제 설정

**변경 파일**: `common/logger.py`

```python
# Before (PHASE22-1)
console_handler = logging.StreamHandler(sys.stdout)
# StreamHandler는 encoding을 직접 설정할 수 없음

# After (PHASE28-8)
import sys

# Windows 환경에서 sys.stdout이 cp949일 경우 UTF-8로 재설정
try:
    if hasattr(sys.stdout, 'reconfigure'):
        # Python 3.7+
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass  # reconfigure 실패 시 무시 (이미 UTF-8이거나 지원 안함)

console_handler = logging.StreamHandler(sys.stdout)
```

**효과**: 
- Windows 콘솔에서 한글/이모지 정상 출력
- `sys.stdout.reconfigure()` 사용 (Python 3.7+)
- 실패 시 무시 (이미 UTF-8 환경이거나 미지원 환경)

---

### 2. TimedRotatingFileHandler 제거

**변경 파일**: `common/logger.py`

```python
# Before (PHASE22-1)
from logging.handlers import TimedRotatingFileHandler
app_handler = TimedRotatingFileHandler(
    app_log_file, 
    when='midnight', 
    interval=1, 
    backupCount=7,
    encoding='utf-8',
    delay=True
)

# After (PHASE28-8)
# TimedRotatingFileHandler 제거 (백테스트 환경에서는 로테이션 불필요)
app_handler = logging.FileHandler(app_log_file, encoding='utf-8', delay=True, mode='a')
```

**이유**: 
- `TimedRotatingFileHandler.rotate()` 실행 시 PermissionError 발생
- 다른 프로세스가 로그 파일을 사용 중일 때 rename 실패
- 백테스트/튜닝 환경에서는 세션별로 독립 실행되므로 로테이션 불필요

**효과**: 
- PermissionError 완전 제거
- 파일 핸들러 안정성 향상

---

## ✅ 검증 결과

### Unicode 로깅 테스트

**테스트 스크립트**: `scripts/temp_test_unicode_logging.py`

```python
logger.info("✅ 한글 로깅 테스트: 안녕하세요")
logger.info("🚀 이모지 테스트: 🎯 📊 💰 ⚠️ ❌ ✅")
logger.info("📈 PHASE28-8: Multi-Period Baseline Validation 시작")
logger.warning("⚠️ 경고: Unicode 테스트 중입니다")
logger.error("❌ 에러: 이것은 테스트 에러 메시지입니다")
```

**실행 결과**: 
```
2025-12-08 00:25:48,034 [INFO] ✅ 한글 로깅 테스트: 안녕하세요
2025-12-08 00:25:48,034 [INFO] 🚀 이모지 테스트: 🎯 📊 💰 ⚠️ ❌ ✅
2025-12-08 00:25:48,034 [INFO] 📈 PHASE28-8: Multi-Period Baseline Validation 시작
2025-12-08 00:25:48,035 [WARNING] ⚠️ 경고: Unicode 테스트 중입니다
2025-12-08 00:25:48,035 [ERROR] ❌ 에러: 이것은 테스트 에러 메시지입니다
```

✅ **모든 Unicode 문자 정상 출력**  
✅ **PermissionError 없음**  
✅ **로그 파일에도 정상 기록**

---

## 📝 추가 개선 사항

### 파일 핸들러 encoding 명시

기존에도 `encoding='utf-8'`이 설정되어 있었으나, 재확인 및 명시적 주석 추가:

```python
# 날짜별 파일 핸들러
file_handler = logging.FileHandler(log_file, encoding='utf-8', delay=True)

# 에러 전용 핸들러
error_handler = logging.FileHandler(error_log_file, encoding='utf-8', delay=True)

# 통합 로그 핸들러
app_handler = logging.FileHandler(app_log_file, encoding='utf-8', delay=True, mode='a')
```

---

## 🎯 향후 권장 사항

### Production 환경 (Live Trading)

Live Trading 환경에서는 로그 로테이션이 필요할 수 있으므로:

1. **Option 1**: `TimedRotatingFileHandler` 재도입 + 프로세스 격리
   - 각 봇이 독립적인 로그 파일 사용 (`bot1.log`, `bot2.log`)
   - 로테이션 시간을 겹치지 않도록 조정

2. **Option 2**: 외부 로그 관리 시스템 사용
   - Logrotate (Linux)
   - 로그 수집 에이전트 (Fluentd, Filebeat)

### Backtest/Tuning 환경 (현재)

- 현재 방식 (단순 FileHandler) 유지
- 로그 정리는 `cleanup_old_logs()` 함수로 충분

---

## 📌 결론

✅ **Unicode 로깅 오류 완전 해결**  
✅ **Windows 환경 UTF-8 강제 적용**  
✅ **PermissionError 제거**  
✅ **백테스트 실행 준비 완료**

---

**관련 파일**: 
- `common/logger.py` (수정)
- `scripts/temp_test_unicode_logging.py` (테스트)
- `docs/PHASE28/PHASE28-8_UNICODE_FIX_NOTES.md` (본 문서)

**다음 단계**: 
- Multi-Period Baseline Backtest 실행 (Bull/Bear/Range)
