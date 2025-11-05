# Windsurf Terminal 설정 가이드

**작성**: 2025-10-29 00:20 UTC+09:00

---

## 문제

PowerShell 명령어가 제대로 작동하지 않아 매번 스크립트 파일을 만들어야 함.

## 해결 방법

Windsurf IDE에서 Terminal 모드로 전환하면 가상환경도 자동 로드됩니다.

---

## 설정 방법

### 1. Windsurf 설정 열기

- 메뉴: `File` → `Preferences` → `Settings`
- 또는 단축키: `Ctrl + ,`

### 2. Terminal 검색

검색창에 `terminal.integrated.defaultProfile.windows` 입력

### 3. 기본 프로파일 변

**현재**: PowerShell  
**변경**: Command Prompt (cmd) 또는 Git Bash

선택 옵션:
- `Command Prompt` - Windows 기본 CMD
- `PowerShell` - 현재 사용 중 (문제 발생)
- `Git Bash` - Unix 스타일 명령어 (권장!)
- `WSL` - Windows Subsystem for Linux

### 4. Git Bash 설치 (권장)

Git Bash를 사용하면 Unix 스타일 명령어를 Windows에서 사용 가능:

**다운로드**: https://git-scm.com/download/win

설치 후 Windsurf 재시작

---

## Terminal 모드 사용 방법

### Windsurf 내장 터미널

1. 터미널 열기: `Ctrl + ~` (백틱)
2. 새 터미널: `Ctrl + Shift + ~`
3. 터미널 분할: `Ctrl + \`

### Cascade AI와 함께 사용

Cascade AI가 명령어를 실행할 때 자동으로 선택한 Shell을 사용합니다:

```bash
# Git Bash로 설정하면
docker compose up -d  # 정상 작동
python script.py      # 정상 작동
```

---

## 가상환경 자동 활성화

### 1. activate 스크립트 확인

```bash
# 가상환경 위치 확인
ls .venv/Scripts/activate     # Windows
ls .venv/bin/activate          # Linux/Mac
```

### 2. 터미널 시작 시 자동 활성화

**Git Bash (.bash_profile)**:

```bash
# .bash_profile 또는 .bashrc에 추가
if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
fi
```

**CMD (자동 실행 배치 파일)**:

```cmd
REM startup.bat
@echo off
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
```

**PowerShell (프로필)**:

```powershell
# Microsoft.PowerShell_profile.ps1
if (Test-Path .venv\Scripts\Activate.ps1) {
    . .venv\Scripts\Activate.ps1
}
```

---

## 권장 설정

### Git Bash 사용 시

**장점**:
- Unix 스타일 명령어 사용 가능
- `ls`, `grep`, `find` 등 사용 가능
- Docker Compose 명령어 완벽 지원
- 가상환경 자동 활성화 쉬움

**설정**:

1. Git Bash 설치
2. Windsurf 설정: `terminal.integrated.defaultProfile.windows` → `Git Bash`
3. `.bash_profile` 작성:

```bash
# .bash_profile
# 프로젝트 디렉토리로 이동 시 자동 활성화
cd() {
    builtin cd "$@"
    if [ -f .venv/Scripts/activate ]; then
        source .venv/Scripts/activate
    fi
}

# 시작 시 가상환경 활성화
if [ -f .venv/Scripts/activate ]; then
    source .venv/Scripts/activate
fi
```

---

## 테스트

### 1. 터미널 타입 확인

```bash
echo $SHELL        # Git Bash
echo %COMSPEC%     # CMD
$PSVersionTable    # PowerShell
```

### 2. Docker 명령어 테스트

```bash
docker ps
docker compose version
```

### 3. Python 가상환경 확인

```bash
which python       # Git Bash
where python       # CMD/PowerShell
python --version
```

---

**추천**: Git Bash 사용으로 PowerShell 문제 완전 해결!
