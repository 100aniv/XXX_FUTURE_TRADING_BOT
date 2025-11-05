# PHASE3 | Scalping Bayesian Tuning Runbook

## 목표
- 스캘핑 전략을 Optuna 기반 베이지안 최적화로 자동 튜닝하여 OOS 통과(≥ A, 가능하면 S)를 달성한다.
- 제약 충족: MDD ≥ -20%, Max Losing Streak ≤ 6, (Win Rate × RR) ≥ 2.0.
- 달성 시 조기 종료 및 베스트 설정 적용.

## 범위
- 스캘핑 전용(다른 전략은 보류). TEST_SCENARIO 및 BACKTEST_PERIODS 준수.
- Trial 단위 단일 변경 사이클 유지. 각 Trial 결과는 TEST_CHECKLIST에 자동 append.

## 구조


- 튜너 컨테이너: trading_bot_backtest 이미지를 사용, 커맨드 오버라이드로 `scripts/tuning/tune_scalping.py` 실행
- 백테스트 거래 기록: 컨테이너 내부 SQLite (세그먼트별 고유 경로)
- 산출물 경로:
  - Trial configs: `configs/scalping/<tuning>/trial_*.yml`
  - Trial logs: `logs/tuning/trial_<tuning>_<nnnn>.json`
  - Optuna DB: PostgreSQL `trading_db` (기본값, 병렬 튜닝 지원)
  - 체크리스트: `docs/PHASE3/TEST_CHECKLIST.md`

## 실행 커맨드 (Docker)
1) Postgres (Optuna Storage)
```
docker compose up -d db_postgres
```

2) 스캘핑 튜너 실행 (진행/완료 알림, 베스트 자동 적용)
```
docker compose run -d --name tuner_scalping_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=SCALPING_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_scalping.py \
    --study scalping_v4_wide \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db
```
- Note: `--study`는 Optuna 표준 용어로, Study 이름을 지정합니다.

## 모니터링
- 컨테이너 로그: `docker logs -f tuner_scalping_1`
- Trial JSON 생성 확인: `logs/tuning/trial_<study>_*.json`
- Optuna 진행: Postgres의 스터디 테이블 (또는 trial 로그 누적)로 확인
- 텔레그램 알림: Trial 완료/진행(%) 및 완료 시 요약 메시지 수신
 - OOS 커버리지: 튜너 시작 시 `[OOS] WFA OOS files detected: <N>` 출력, `<3`일 경우 경고 로그(`[OOS][WARN] ...`)로 알림

### 알림 정책 (공통)
- 진행 알림은 아래 조건 중 하나일 때만 전송됨:
  - 첫 알림(최초 1회)
  - 최고 점수(`score_total`)가 ≥ 5점 개선
  - 등급(grade) 변경 발생
  - S 등급 최초 달성
- 메시지 포맷 예시:
  - `📊 [TUNING] <tuning> i/n (p%)` + `🏆 Best: <점수>(<등급>) | 거래 <T>` + `💰 ROI <..>% | PF <..> | MDD <..>%` + `⏱ ETA ~XmYs` + `| S까지 <gap>`

## 텔레그램 설정 (.env 또는 환경변수)
- TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 필수
- ENABLE_TELEGRAM=true

## 조기 종료(early-stop) 동작
- `--early-stop-grade OFF|NONE|0` → 조기 종료 비활성화
- `--early-stop-grade S|A|B|C` → 최고 Trial의 `score_total`이 지정 등급 임계치(예: A=70)에 도달하면 종료

## 자동 안전장치
- 거래 부족 자동 중단: 연속 5회 Trial에서 거래 < 10건이면 경고 후 종료 (탐색공간 문제)
- 세그먼트별 최소 거래수 게이트: `--min-trades-oos` 미달 시 prune (robust)
- 레짐 하한 게이트: `--penalty-regime-min` 미달 세그먼트 존재 시 prune (robust)
- 분산 패널티: `--penalty-variance λ` 적용, 세그먼트 간 성과 분산에 비례 감점 (robust)
 - 컨텍스트 스케일링(Context Scaling): ATR% 구간에 따라 RPT 자동 조절(저변동↑, 고변동↓) — PositionSizer에 내장

## 탐색 공간(요지)
- 세션: none | london | london+ny (필요 시 전체 시간 허용)
- Short 허용 옵션 추가
- BB bounce 범위 확대 (진입 기회 증가)
- Volume, RR, Cooldown, Trailing 범위 확장
 - 레짐 프리셋 분기: OOS 파일명(ETF_APPROVAL/HALVING/SUMMER_RANGE/Q4_VOLATILITY/YEAR_END) 힌트를 바탕으로 각 전략이 RSI/BB/볼륨 임계치를 소폭 자동 조절

## 산출물 정리
- 베스트 설정: `configs/best_scalping_<tuning>.yml` + (옵션) `configs/best_scalping.yml` 자동 승격
- 체크리스트: `docs/PHASE3/TEST_CHECKLIST.md` 자동 append
- 튜닝 DB: Postgres (Docker 분산) 또는 `db/tuning/optuna.db` (로컬)

## 타 전략 적용(병렬 튜너)
- 동일 정책/옵션이 trend, reversion, breakout, daytrade, swing 튜너에 동일 적용됨
- 적용 파일명(자동 승격):
  - trend → `configs/best_trend.yml`
  - reversion → `configs/best_reversion.yml`
  - breakout → `configs/best_breakout.yml`
  - daytrade → `configs/best_daytrade.yml`
  - swing → `configs/best_swing.yml`

## 병렬 실행 (6개 튜너)
- 본 섹션은 기존 스캘핑 단독 실행 지침을 삭제하지 않고, 추가적으로 6개 전략을 병렬로 실행하는 방법을 제시한다.
- TEST_SCENARIO와 BACKTEST_PERIODS는 변경하지 않는다. 각 튜너는 동일한 정책(robust 옵션, OOS 커버리지 로깅, 체크리스트 append)을 따른다.

### Docker Compose: 6개 튜너 병렬 실행 예시
```
# 0) Postgres 스토리지 (공용)
docker compose up -d db_postgres

# 1) SCALPING
docker compose run -d --name tuner_scalping_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=SCALPING_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_scalping.py \
    --study scalping_v4_wide \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# 2) TREND
docker compose run -d --name tuner_trend_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=TREND_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_trend.py \
    --study trend_v1 \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# 3) REVERSION
docker compose run -d --name tuner_reversion_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=REVERSION_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_reversion.py \
    --study reversion_v1 \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# 4) BREAKOUT
docker compose run -d --name tuner_breakout_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=BREAKOUT_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_breakout.py \
    --study breakout_v1 \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# 5) DAYTRADE
docker compose run -d --name tuner_daytrade_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=DAYTRADE_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_daytrade.py \
    --study daytrade_v1 \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db

# 6) SWING
docker compose run -d --name tuner_swing_1 \
  -e DATABASE_URL=postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db \
  -e TELEGRAM_TOKEN=${env:TELEGRAM_TOKEN} \
  -e TELEGRAM_CHAT_ID=${env:TELEGRAM_CHAT_ID} \
  -e ENABLE_TELEGRAM=true \
  -e SYSTEM_NAME=SWING_TUNER \
  -v ${PWD}/configs:/app/configs \
  -v ${PWD}/data:/app/data \
  -v ${PWD}/logs:/app/logs \
  trading_bot_backtest \
  python -u scripts/tuning/tune_swing.py \
    --study swing_v1 \
    --trials 200 \
    --use-wfa 1 \
    --notify-progress 1 \
    --notify-completion 1 \
    --early-stop-grade OFF \
    --dod-mode robust \
    --min-trades-oos 30 \
    --penalty-variance 0.5 \
    --penalty-regime-min B \
    --apply-best 1 \
    --optuna-storage postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db
```

### 모니터링/중지
- 로그: `docker logs -f tuner_<strategy>_1`
- 중지: `docker stop tuner_<strategy>_1` (필요 시 `docker rm`)


## 수용 기준 (AC)
- 등급 ≥ A (가능하면 S) 달성은 중간 체크포인트일 뿐. 최종 완료는 DoD(아래) 충족 기준.
- 제약(MDD/연속손실/승률×RR) 충족
- Trial 로그/체크리스트 누락 없음
- 베스트 설정 자동 승격 동작

## Robust DoD (Definition of Done)
- WFA 전 폴드 OOS 합격: 각 폴드 최소 등급 ≥ B, 평균 ≥ A
- 세그먼트 최소 거래수 충족: `--min-trades-oos` (예: 30)
- 레짐 테스트(트렌드/레인지/고·저변동) 평균 A, 최저 B 유지
- 민감도 테스트(±5~10%) 3회 평균: 등급 하락 ≤ 1
- 스트레스 테스트: 수수료/슬리피지(+20~100%)에서 PF/MDD 급락 없음
- 실전 전 단계: 4주 페이퍼 성능 손상률 ≤ 25%, 주문 일치율 ~100%

> 단일 S는 과최적화 가능성. Robust 모드에서 레짐 하한과 분산 패널티, 거래수 게이트로 강건성 보장.

## 엔진/전략 사용 여부
- 본 튜닝은 별도 프로그램이 아니라, `main.py`(엔진) 실행을 통해 실제 봇 모듈을 사용함
- 신호 생성은 `signals/SignalGenerator` + `strategies/<name>.py`를 그대로 호출
- 설정은 Overlay YAML로 주입되어 `config.yml` + `strategies.<selector>`에 병합됨
 - 리스크/세이프티: RiskManager가 `risk.max_daily_loss_pct`(%)를 표준으로 사용(내부에서 /100 처리). `flash_guard.*` 키는 엔진 키로 자동 매핑됨.

## 주의 / 규칙
- TEST_SCENARIO 사전 점검, BACKTEST_PERIODS 범위 준수
- PowerShell: 단순 명령만 사용 (docker, docker-compose, timeout, Copy-Item)
- config.yml 중복 설정 금지, 변경 시 백업
- 완료 후 PHASE3 문서 비교 및 업데이트

## 모드 파리티(Backtest = Paper = Live) 정책
- **[오프라인 MTF(백테스트)]**
  - 백테스트에서는 `SignalGenerator`가 현재 DF를 HTF로 리샘플하여 MTF 정렬을 판정함.
  - 설정 키: `backtest.use_offline_mtf: true`(기본값). 비활성화 시 라이브 API 경로로 폴백.
  - 효과: 백테스트 중에도 “동일 과거 구간”으로 MTF를 계산하여 드라이/라이브와 논리 일치성 향상.

- **[일일 손실 한도(백테스트에도 적용 가능)]**
  - `RiskManager`가 백테스트에서도 일일 손실 한도를 적용할 수 있도록 옵션화.
  - 설정 키: `risk.enforce_daily_loss_in_backtest: true`(기본값). false면 백테스트에 한해 일일 한도 미적용.
  - 권장: 베이시스 튜닝 시 true로 두어 실전 게이트와 동일 조건으로 최적화.

- **[슬리피지/수수료 파리티]**
  - Backtest: `fees.taker` + `fees.slippage` 적용.
  - Paper: `PaperBroker`에 `slippage_pct` 추가 → `fees.slippage`를 동일 적용하여 파리티 유지.
  - Live: 실제 체결가 기준(시뮬 슬리피지 비적용). 실거래 체결과의 차이를 모니터링 권장.
  - 설정 키: `fees.taker`, `fees.slippage`.

- **[엔진 모드 전달]**
  - `main.py`가 `config['mode'] = backtest|paper|live`를 엔진/리스크에 전달하여 모드별 기능 동작을 일관화.

- **[Docker/분산 튜닝 주의]**
  - 세그먼트별 SQLite 경합 방지를 위해 `BACKTEST_DB_PATH`를 Trial/Segment 단위로 분리 저장.
  - WFA-OOS 파일 다중 평가 시 각 세그먼트에 대해 별도 DB 스냅샷을 생성/집계.

> 위 파리티 정책으로 백테스트 튜닝 결과를 드라이/라이브에 보다 신뢰성 있게 이식할 수 있습니다.

## 트러블슈팅
- 텔레그램 알림 없음: 토큰/채널ID/ENABLE_TELEGRAM 확인. 첫 Trial 완료 전에는 안 올 수 있음.
- 컨테이너가 main.py 실행함: run 시 커맨드 오버라이드(튜너) 사용 여부 확인
- trial JSON 미생성: 로그 파싱 실패 시 DB 스냅샷으로 계산, `logs/tuning/<tuning>/db/*.db` 확인

