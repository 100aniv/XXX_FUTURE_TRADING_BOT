# Git & GitHub 빠른 시작 가이드 (Windows PowerShell)

**작성**: 2025-11-06 01:15 UTC+09:00

---

## 🚀 5분 안에 GitHub에 업로드하기

### 1단계: Git 설치 확인 (1분)

```powershell
git --version
```

**결과 예**:
```
git version 2.42.0.windows.2
```

만약 "git : '용어가 인식되지 않습니다" 오류가 나면:
- Git 설치: https://git-scm.com/download/win
- 설치 후 PowerShell 재시작

---

### 2단계: Git 사용자 설정 (1분)

```powershell
git config --global user.name "bback"
git config --global user.email "your-email@gmail.com"
```

**확인**:
```powershell
git config --global --list
```

---

### 3단계: GitHub 계정 연동 (2분)

#### 방법 1: Personal Access Token (권장)

**Step A: GitHub에서 Token 생성**
1. https://github.com/settings/tokens 방문
2. "Generate new token (classic)" 클릭
3. 설정:
   - Token name: `git-cli-token`
   - Expiration: 90 days
   - Scopes: `repo` 체크
4. "Generate token" 클릭
5. **토큰 복사** (다시 볼 수 없음!)

**Step B: Git Credential Manager 설정**
```powershell
git config --global credential.helper manager-core
```

---

#### 방법 2: SSH Key (더 편함)

**Step A: SSH Key 생성**
```powershell
ssh-keygen -t ed25519 -C "your-email@gmail.com"
```

**프롬프트**:
```
Enter file in which to save the key: [Enter]
Enter passphrase: [Enter 또는 비밀번호]
Enter same passphrase again: [확인]
```

**Step B: SSH Key 확인**
```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

**Step C: GitHub에 등록**
1. https://github.com/settings/ssh/new 방문
2. Title: `My Windows PC`
3. Key type: Authentication Key
4. Key: [위에서 복사한 전체 내용]
5. "Add SSH key" 클릭

**Step D: 연결 테스트**
```powershell
ssh -T git@github.com
```

**성공 메시지**:
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

---

### 4단계: 프로젝트 초기화 (1분)

```powershell
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot

# 기존 .git 폴더 있으면 삭제
Remove-Item -Recurse -Force .git -ErrorAction SilentlyContinue

# 새로 초기화
git init
```

---

### 5단계: GitHub 저장소 생성 (1분)

1. https://github.com/new 방문
2. Repository name: `future_alarm_bot`
3. Description: `Automated trading bot with FlowGuardian gate`
4. Public 또는 Private 선택 (Private 권장)
5. "Create repository" 클릭

---

### 6단계: 파일 추가 및 커밋 (1분)

```powershell
# 모든 파일 스테이징
git add .

# 커밋
git commit -m "Initial commit: PR8 verification complete with CI/CD pipeline"
```

---

### 7단계: 원격 저장소 연결 및 푸시 (1분)

#### SSH 사용 (권장):
```powershell
git remote add origin git@github.com:your-username/future_alarm_bot.git
git branch -M main
git push -u origin main
```

#### 또는 HTTPS 사용:
```powershell
git remote add origin https://github.com/your-username/future_alarm_bot.git
git branch -M main
git push -u origin main
```

**첫 푸시 시 인증**:
- SSH: 자동 (이미 설정됨)
- HTTPS: 
  - Username: your-github-username
  - Password: [Personal Access Token 붙여넣기]

---

## ✅ 완료!

GitHub에 업로드 완료! 🎉

확인:
```powershell
git remote -v
# 출력:
# origin  git@github.com:your-username/future_alarm_bot.git (fetch)
# origin  git@github.com:your-username/future_alarm_bot.git (push)
```

---

## 📝 일상적 사용 명령어

### 변경사항 확인
```powershell
git status
```

### 변경사항 추가
```powershell
git add .
```

### 커밋
```powershell
git commit -m "Fix: description of changes"
```

### 푸시 (GitHub에 업로드)
```powershell
git push origin main
```

### 풀 (GitHub에서 다운로드)
```powershell
git pull origin main
```

### 로그 확인
```powershell
git log --oneline -10
```

---

## 🔐 .env 파일 관리

### ⚠️ .env는 절대 커밋하지 말 것!

`.gitignore`에 이미 포함됨:
```
.env
.env.*
```

### 실수로 커밋했다면:
```powershell
# 저장소에서 제거 (로컬 파일은 유지)
git rm --cached .env
git commit -m "Remove .env from tracking"
git push origin main
```

### .env 설정 방법:
1. `.env.example` 복사
2. `.env` 파일 생성
3. 실제 값 입력
4. `.env`는 절대 커밋 금지

---

## 🆘 문제 해결

### "fatal: not a git repository"
```powershell
git init
```

### "Permission denied (publickey)"
SSH 재설정:
```powershell
ssh-agent -s
ssh-add $env:USERPROFILE\.ssh\id_ed25519
ssh -T git@github.com
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

## 🎯 다음 단계

1. **GitHub Actions 확인**
   - `.github/workflows/pre-commit.yml` 자동 실행
   - 모든 PR에서 자동 테스트

2. **Branch 전략**
   ```powershell
   # develop 브랜치 생성
   git checkout -b develop
   git push -u origin develop
   
   # 기능 개발 시
   git checkout -b feature/pr9
   # ... 개발 ...
   git push -u origin feature/pr9
   # GitHub에서 PR 생성
   ```

3. **PR 워크플로우**
   - `develop`에서 `feature/*` 브랜치 생성
   - 기능 개발 후 PR 생성
   - GitHub Actions 자동 테스트 통과 확인
   - Merge

---

**작성**: 2025-11-06 01:15 UTC+09:00  
**상태**: 준비 완료 ✅
