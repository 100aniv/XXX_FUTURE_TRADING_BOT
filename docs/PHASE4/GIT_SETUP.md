# Git 환경 세팅 가이드

**작성**: 2025-10-29 00:05 UTC+09:00

---

## 1. Git 설치

### Windows 설치

```bash
# 1. Git 다운로드
# https://git-scm.com/download/win

# 2. 설치 옵션
# - Use Git from Git Bash only (기본값)
# - Checkout Windows-style, commit Unix-style (기본값)
# - Use MinTTY (기본값)

# 3. 설치 확인
git --version
```

---

## 2. Git 초기 설정

```bash
# 사용자 정보 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 한글 파일명 깨짐 방지
git config --global core.quotepath false

# 줄바꿈 설정 (Windows)
git config --global core.autocrlf true

# 기본 에디터 설정 (VS Code)
git config --global core.editor "code --wait"

# 설정 확인
git config --list
```

---

## 3. 저장소 초기화

```bash
# 프로젝트 디렉토리로 이동
cd c:/Users/bback/OneDrive/Documents/future_alarm_bot

# Git 저장소 초기화
git init

# 기본 브랜치를 main으로 설정
git branch -M main

# 원격 저장소 추가 (GitHub 사용 시)
git remote add origin https://github.com/yourusername/future_alarm_bot.git
```

---

## 4. 첫 커밋

```bash
# 상태 확인
git status

# 모든 파일 추가
git add .

# 커밋
git commit -m "Phase 4 완료: 리팩토링 + 검증 + 설정 시스템 수정"

# 원격 저장소로 푸시 (GitHub 설정 후)
git push -u origin main
```

---

## 5. 중요 파일 버전 관리

### 반드시 커밋할 파일

```bash
# 설정 파일
git add config.yml
git add docker-compose.yml

# 튜닝 결과 (중요!)
git add configs/scalping/active.yml
git add configs/scalping/last_published.json

# 문서
git add docs/PHASE4/*.md

# 코드
git add common/ execution/ strategies/ signals/ collectors/

# 커밋
git commit -m "설정 및 튜닝 결과 저장"
```

### .gitignore에 포함된 항목

```
# 이미 .gitignore에 설정됨
__pycache__/
*.pyc
.env
logs/
*.log
pgdata/
redisdata/
```

---

## 6. 튜닝 결과 관리 워크플로우

### 시나리오: 베이지안 튜닝 후

```bash
# 1. 튜닝 실행
python common/tuning_cli.py --strategy scalping --trials 20

# 2. active.yml 생성 확인
ls configs/scalping/active.yml

# 3. Git 상태 확인
git status
# 변경된 파일: configs/scalping/active.yml

# 4. 커밋
git add configs/scalping/active.yml
git add configs/scalping/last_published.json
git commit -m "Tuning: scalping rr=2.5, atr_mult_sl=1.8"

# 5. 푸시 (백업)
git push origin main
```

### 시나리오: 튜닝 결과 롤백

```bash
# 1. 이전 버전으로 되돌리기
git log --oneline configs/scalping/active.yml

# 2. 특정 커밋으로 복원
git checkout <commit-hash> configs/scalping/active.yml

# 3. Docker 재시작
docker compose restart trading_bot_paper_scalping

# 4. 확인 후 커밋
git commit -m "Rollback: scalping tuning to previous version"
```

---

## 7. GitHub 설정 (선택)

### GitHub 저장소 생성

1. https://github.com/new 접속
2. Repository name: `future_alarm_bot`
3. Private 선택
4. Create repository

### SSH 키 설정 (권장)

```bash
# SSH 키 생성
ssh-keygen -t ed25519 -C "your.email@example.com"

# 키 복사
cat ~/.ssh/id_ed25519.pub

# GitHub에 등록
# Settings → SSH and GPG keys → New SSH key
```

### HTTPS 대신 SSH 사용

```bash
# 기존 origin 제거
git remote remove origin

# SSH로 재설정
git remote add origin git@github.com:yourusername/future_alarm_bot.git

# 푸시
git push -u origin main
```

---

## 8. 브랜치 전략 (선택)

### 기본 브랜치 구조

```
main (stable)
  ├── develop (개발)
  ├── feature/scalping-tuning (기능)
  └── hotfix/config-fix (긴급 수정)
```

### 사용 예시

```bash
# 튜닝 작업용 브랜치 생성
git checkout -b feature/scalping-tuning

# 작업 및 커밋
git add configs/scalping/active.yml
git commit -m "Tuning: scalping optimization"

# main에 병합
git checkout main
git merge feature/scalping-tuning

# 브랜치 삭제
git branch -d feature/scalping-tuning
```

---

## 9. 체크리스트

- [ ] Git 설치 완료
- [ ] Git 초기 설정 완료 (user.name, user.email)
- [ ] 저장소 초기화 (git init)
- [ ] .gitignore 확인
- [ ] 첫 커밋 완료
- [ ] GitHub 저장소 생성 (선택)
- [ ] SSH 키 설정 (선택)
- [ ] 원격 저장소 연결 (선택)

---

## 10. 유용한 Git 명령어

```bash
# 상태 확인
git status

# 변경 내역 확인
git diff

# 커밋 히스토리
git log --oneline

# 특정 파일 히스토리
git log --oneline configs/scalping/active.yml

# 최근 커밋 취소 (커밋만)
git reset --soft HEAD~1

# 최근 커밋 취소 (변경사항도)
git reset --hard HEAD~1

# 원격 저장소 최신 상태로 업데이트
git pull origin main
```

---

**상태**: ⏳ Git 설치 후 진행  
**다음**: 첫 커밋 및 튜닝 결과 버전 관리
