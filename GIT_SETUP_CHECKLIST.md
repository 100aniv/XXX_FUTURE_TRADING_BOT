# Git & GitHub 설정 체크리스트

**작성**: 2025-11-06 01:15 UTC+09:00  
**대상**: Windows PowerShell 사용자

---

## 📋 설정 단계별 체크리스트

### Phase 1: Git 설치 및 기본 설정

- [ ] **Git 설치**
  - 방법 1: Chocolatey
    ```powershell
    choco install git -y
    ```
  - 방법 2: 직접 다운로드
    - https://git-scm.com/download/win
  - 확인: `git --version`

- [ ] **사용자 정보 설정**
  ```powershell
  git config --global user.name "bback"
  git config --global user.email "your-email@gmail.com"
  ```
  - 확인: `git config --global --list`

---

### Phase 2: GitHub 계정 연동 (2가지 방법 중 선택)

#### 방법 A: Personal Access Token (권장)

- [ ] **Token 생성**
  1. https://github.com/settings/tokens 방문
  2. "Generate new token (classic)" 클릭
  3. Token name: `git-cli-token`
  4. Expiration: 90 days
  5. Scopes: `repo` 체크
  6. "Generate token" 클릭
  7. **토큰 복사** (다시 볼 수 없음!)

- [ ] **Credential Manager 설정**
  ```powershell
  git config --global credential.helper manager-core
  ```

#### 방법 B: SSH Key (더 편함)

- [ ] **SSH Key 생성**
  ```powershell
  ssh-keygen -t ed25519 -C "your-email@gmail.com"
  ```
  - 프롬프트: 모두 Enter 누르기

- [ ] **SSH Key 확인**
  ```powershell
  type $env:USERPROFILE\.ssh\id_ed25519.pub
  ```

- [ ] **GitHub에 SSH Key 등록**
  1. https://github.com/settings/ssh/new 방문
  2. Title: `My Windows PC`
  3. Key type: Authentication Key
  4. Key: [위에서 복사한 전체 내용]
  5. "Add SSH key" 클릭

- [ ] **SSH 연결 테스트**
  ```powershell
  ssh -T git@github.com
  ```
  - 성공 메시지: "Hi username! You've successfully authenticated..."

---

### Phase 3: 프로젝트 준비

- [ ] **.gitignore 확인**
  - 파일 위치: `c:/Users/bback/OneDrive/Documents/future_alarm_bot/.gitignore`
  - 포함 항목: `.env`, `__pycache__/`, `logs/`, `pgdata/`, `redisdata/`

- [ ] **.env.example 생성**
  - 파일 위치: `c:/Users/bback/OneDrive/Documents/future_alarm_bot/.env.example`
  - 포함 항목: 모든 환경변수 (민감 정보 제외)

- [ ] **.env 파일 생성 및 설정**
  ```powershell
  # .env.example 복사
  Copy-Item .env.example .env
  
  # 텍스트 에디터로 .env 열기
  notepad .env
  ```
  - 필수 설정:
    - `POSTGRES_PASSWORD`: 실제 비밀번호
    - `TELEGRAM_BOT_TOKEN`: 실제 토큰
    - `TELEGRAM_CHAT_ID`: 실제 Chat ID
    - `BINANCE_API_KEY`: 실제 API 키
    - `BINANCE_API_SECRET`: 실제 API 시크릿

---

### Phase 4: GitHub 저장소 생성

- [ ] **GitHub 저장소 생성**
  1. https://github.com/new 방문
  2. Repository name: `future_alarm_bot`
  3. Description: `Automated trading bot with FlowGuardian gate`
  4. Public 또는 Private 선택 (Private 권장)
  5. "Create repository" 클릭
  6. **저장소 URL 복사** (SSH 또는 HTTPS)

---

### Phase 5: 로컬 저장소 초기화

- [ ] **프로젝트 디렉토리로 이동**
  ```powershell
  cd c:/Users/bback/OneDrive/Documents/future_alarm_bot
  ```

- [ ] **기존 .git 폴더 삭제** (있으면)
  ```powershell
  Remove-Item -Recurse -Force .git -ErrorAction SilentlyContinue
  ```

- [ ] **Git 저장소 초기화**
  ```powershell
  git init
  ```

- [ ] **원격 저장소 연결**
  
  SSH 사용:
  ```powershell
  git remote add origin git@github.com:your-username/future_alarm_bot.git
  ```
  
  또는 HTTPS 사용:
  ```powershell
  git remote add origin https://github.com/your-username/future_alarm_bot.git
  ```

- [ ] **원격 저장소 확인**
  ```powershell
  git remote -v
  ```

---

### Phase 6: 파일 추가 및 커밋

- [ ] **모든 파일 스테이징**
  ```powershell
  git add .
  ```

- [ ] **변경사항 확인**
  ```powershell
  git status
  ```
  - `.env` 파일이 제외되었는지 확인

- [ ] **커밋**
  ```powershell
  git commit -m "Initial commit: PR8 verification complete with CI/CD pipeline"
  ```

---

### Phase 7: GitHub에 푸시

- [ ] **브랜치 이름 변경**
  ```powershell
  git branch -M main
  ```

- [ ] **GitHub에 푸시**
  ```powershell
  git push -u origin main
  ```

- [ ] **인증** (HTTPS 사용 시)
  - Username: your-github-username
  - Password: [Personal Access Token 붙여넣기]

- [ ] **푸시 완료 확인**
  - https://github.com/your-username/future_alarm_bot 방문
  - 파일 목록 확인

---

## ✅ 최종 확인

- [ ] Git 설치 완료: `git --version`
- [ ] 사용자 정보 설정: `git config --global --list`
- [ ] GitHub 계정 연동: `ssh -T git@github.com` (SSH) 또는 첫 푸시 (Token)
- [ ] .gitignore 설정: `.env` 파일 제외 확인
- [ ] .env 파일 생성: 모든 필수 값 입력
- [ ] GitHub 저장소 생성: 저장소 URL 확인
- [ ] 로컬 저장소 초기화: `git init` 완료
- [ ] 원격 저장소 연결: `git remote -v` 확인
- [ ] 파일 추가 및 커밋: `git commit` 완료
- [ ] GitHub에 푸시: `git push` 완료
- [ ] GitHub 저장소 확인: 파일 목록 표시

---

## 🎯 다음 단계

### 즉시 (필수)
1. GitHub Actions 워크플로우 확인
   - `.github/workflows/pre-commit.yml` 자동 실행
   - 모든 push 시 자동 테스트

2. 로컬 개발 환경 설정
   - `.env` 파일 설정 완료
   - Docker 컨테이너 실행 확인

### 단기 (권장)
1. Branch 전략 수립
   - `main`: 프로덕션 (안정 버전)
   - `develop`: 개발 (최신 기능)
   - `feature/*`: 기능 개발

2. PR 워크플로우 설정
   - `develop`에서 `feature/pr9` 브랜치 생성
   - 기능 개발 후 PR 생성
   - GitHub Actions 자동 테스트 통과 확인
   - Merge

### 장기 (선택)
1. GitHub Pages로 문서 호스팅
2. Codecov 연동 (커버리지 리포트)
3. 자동 배포 (CD) 설정

---

## 📚 참고 문서

- **상세 가이드**: `GITHUB_SETUP_GUIDE.md`
- **빠른 시작**: `QUICK_START_GIT.md`
- **PR8 검증**: `docs/PHASE6/PR8_VERIFICATION_SUMMARY.md`
- **CI/CD 파이프라인**: `.github/workflows/pre-commit.yml`

---

## 🆘 문제 해결

### "git : '용어가 인식되지 않습니다"
→ Git 설치 필요: https://git-scm.com/download/win

### "fatal: not a git repository"
→ `git init` 실행

### "Permission denied (publickey)"
→ SSH Key 재설정:
```powershell
ssh-agent -s
ssh-add $env:USERPROFILE\.ssh\id_ed25519
ssh -T git@github.com
```

### "fatal: The current branch main has no upstream branch"
→ `git push -u origin main` 실행

### ".env 파일이 커밋됨"
→ 저장소에서 제거:
```powershell
git rm --cached .env
git commit -m "Remove .env from tracking"
git push origin main
```

---

**작성**: 2025-11-06 01:15 UTC+09:00  
**상태**: 준비 완료 ✅

---

## 📞 지원

문제가 발생하면:
1. 이 체크리스트의 "문제 해결" 섹션 확인
2. `GITHUB_SETUP_GUIDE.md` 상세 가이드 참고
3. `QUICK_START_GIT.md` 빠른 시작 가이드 참고
