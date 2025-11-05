# GitHub 연동 설정 가이드

**작성**: 2025-11-06 01:10 UTC+09:00  
**대상**: Windows PowerShell 사용자

---

## 1️⃣ Git 설치 (Windows)

### 옵션 A: Chocolatey 사용 (권장)
```powershell
# 관리자 권한으로 PowerShell 실행 후:
choco install git -y
```

### 옵션 B: 직접 다운로드
1. https://git-scm.com/download/win 방문
2. 64-bit Git for Windows Setup 다운로드
3. 설치 마법사 실행 (기본 설정 유지)

### 설치 확인
```powershell
git --version
# 출력: git version 2.x.x
```

---

## 2️⃣ Git 초기 설정

### 사용자 정보 설정
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

**예시**:
```powershell
git config --global user.name "bback"
git config --global user.email "your-email@gmail.com"
```

### 설정 확인
```powershell
git config --global --list
# 출력:
# user.name=bback
# user.email=your-email@gmail.com
```

---

## 3️⃣ GitHub 계정 연동 (2가지 방법)

### 방법 1: Personal Access Token (권장, 더 안전)

#### Step 1: GitHub에서 Token 생성
1. GitHub 로그인: https://github.com/login
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token (classic)" 클릭
4. 설정:
   - Token name: `git-cli-token`
   - Expiration: 90 days (또는 원하는 기간)
   - Scopes: `repo` (전체 선택)
5. "Generate token" 클릭
6. **토큰 복사 (다시 볼 수 없음!)**

#### Step 2: Git Credential Manager 설정
```powershell
# Git Credential Manager 활성화
git config --global credential.helper manager-core

# 또는 Windows Credential Manager 사용
git config --global credential.helper wincred
```

#### Step 3: 첫 번째 push 시 인증
```powershell
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot
git push origin main
# 프롬프트:
# Username: your-github-username
# Password: [위에서 복사한 Personal Access Token 붙여넣기]
```

---

### 방법 2: SSH Key (더 편함, 한 번만 설정)

#### Step 1: SSH Key 생성
```powershell
ssh-keygen -t ed25519 -C "your-email@gmail.com"
# 또는 (구형 시스템):
ssh-keygen -t rsa -b 4096 -C "your-email@gmail.com"
```

**프롬프트**:
```
Enter file in which to save the key: [Enter 누르기]
Enter passphrase: [비밀번호 입력 또는 Enter]
Enter same passphrase again: [확인]
```

#### Step 2: SSH Key 확인
```powershell
cat ~/.ssh/id_ed25519.pub
# 또는:
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

**출력 예**:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJx... your-email@gmail.com
```

#### Step 3: GitHub에 SSH Key 등록
1. GitHub 로그인: https://github.com/login
2. Settings → SSH and GPG keys → New SSH key
3. Title: `My Windows PC`
4. Key type: Authentication Key
5. Key: [위에서 복사한 전체 내용 붙여넣기]
6. "Add SSH key" 클릭

#### Step 4: SSH 연결 테스트
```powershell
ssh -T git@github.com
# 출력: Hi username! You've successfully authenticated...
```

---

## 4️⃣ 프로젝트 초기화 및 업로드

### Step 1: 로컬 Git 저장소 초기화
```powershell
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot

# 기존 .git 폴더 있으면 삭제
Remove-Item -Recurse -Force .git

# 새로 초기화
git init
```

### Step 2: .gitignore 생성 (중요!)
```powershell
# 다음 내용으로 .gitignore 파일 생성:
# (프로젝트 루트에 저장)
```

**`.gitignore` 내용**:
```
# 환경 변수
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 가상환경
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 테스트
.pytest_cache/
.coverage
htmlcov/

# 로그 및 데이터
logs/
*.log
data/
pgdata/
redisdata/

# 임시 파일
*.tmp
*.bak
runs/

# OS
.DS_Store
Thumbs.db
```

### Step 3: 파일 추가 및 커밋
```powershell
# 모든 파일 스테이징
git add .

# 커밋
git commit -m "Initial commit: PR8 verification complete"
```

### Step 4: GitHub 저장소 생성

1. GitHub 로그인: https://github.com/new
2. Repository name: `future_alarm_bot` (또는 원하는 이름)
3. Description: `Automated trading bot with FlowGuardian gate`
4. Public/Private 선택 (Private 권장)
5. "Create repository" 클릭

### Step 5: 원격 저장소 연결 및 푸시

**SSH 사용 (권장)**:
```powershell
git remote add origin git@github.com:your-username/future_alarm_bot.git
git branch -M main
git push -u origin main
```

**HTTPS 사용**:
```powershell
git remote add origin https://github.com/your-username/future_alarm_bot.git
git branch -M main
git push -u origin main
```

---

## 5️⃣ .env 파일 관리 (중요!)

### ⚠️ .env는 절대 커밋하지 말 것!

`.env` 파일은 민감한 정보 포함:
- 데이터베이스 비밀번호
- API 키
- Telegram 토큰

**이미 커밋했다면**:
```powershell
# 저장소에서 제거 (로컬 파일은 유지)
git rm --cached .env
git commit -m "Remove .env from tracking"
git push origin main
```

### .env.example 생성 (권장)
```powershell
# .env.example 파일 생성 (민감 정보 제외)
```

**`.env.example` 내용**:
```
# Database
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=trading_db

# Telegram
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Trading
EQUITY_USDT=50000
TRADING_MODE=paper
```

---

## 6️⃣ 일상적 사용 명령어

### 변경사항 확인
```powershell
git status
```

### 변경사항 추가
```powershell
git add .
# 또는 특정 파일만:
git add filename.py
```

### 커밋
```powershell
git commit -m "Fix: PR8 verification complete"
```

### 푸시 (원격에 업로드)
```powershell
git push origin main
```

### 풀 (원격에서 다운로드)
```powershell
git pull origin main
```

### 로그 확인
```powershell
git log --oneline -10
```

---

## 7️⃣ 문제 해결

### "fatal: not a git repository"
```powershell
git init
```

### "Permission denied (publickey)"
```powershell
# SSH Key 다시 확인
ssh -T git@github.com

# 또는 SSH Agent 시작
ssh-agent -s
ssh-add ~/.ssh/id_ed25519
```

### "fatal: The current branch main has no upstream branch"
```powershell
git push -u origin main
```

### 커밋 취소
```powershell
# 마지막 커밋 취소 (파일은 유지)
git reset --soft HEAD~1

# 마지막 커밋 완전 취소
git reset --hard HEAD~1
```

---

## 📋 체크리스트

- [ ] Git 설치 완료
- [ ] 사용자 정보 설정 완료 (`git config --global user.name`)
- [ ] GitHub 계정 연동 완료 (Token 또는 SSH)
- [ ] .gitignore 파일 생성
- [ ] GitHub 저장소 생성
- [ ] 로컬 저장소 초기화 (`git init`)
- [ ] 원격 저장소 연결 (`git remote add origin`)
- [ ] 첫 번째 푸시 완료 (`git push -u origin main`)
- [ ] .env 파일 .gitignore에 추가 확인

---

## 🎯 다음 단계

1. **GitHub Actions 활성화**
   - `.github/workflows/pre-commit.yml` 자동 실행
   - 모든 PR에서 자동 테스트

2. **Branch 전략**
   - `main`: 프로덕션 (안정 버전)
   - `develop`: 개발 (최신 기능)
   - `feature/*`: 기능 개발

3. **PR 워크플로우**
   - `develop`에서 `feature/pr9` 브랜치 생성
   - 기능 개발 후 PR 생성
   - GitHub Actions 자동 테스트 통과 후 merge

---

**작성**: 2025-11-06 01:10 UTC+09:00  
**상태**: 준비 완료
