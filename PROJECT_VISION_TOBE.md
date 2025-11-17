좋아, 이제 “진짜 최종형” 그림 한 번 박제해보자.
아래 문서는 지피티 프로젝트에 그대로 첨부해서 컨텍스트용으로 쓰기 좋은 버전으로 썼다.

⸻

==========================================================

0. 프로젝트 정체성 / 최종 비전

==========================================================
	•	프로젝트명(가칭): Future Alarm Bot – Ensemble Edition
	•	최종 목표:
	•	6개 이상의 서로 다른 전략 모듈을 하나의 앙상블 구조로 묶어서
	•	Binance Futures / (추후) Upbit Spot / (옵션) 국내 증권 API까지
	•	완전 자동·반자동 모드를 지원하는 상용급 트레이딩 시스템 완성.
	•	현재 상태:
	•	과거에 이미 6전략 앙상블 + 베이시안 튜닝까지 갔다가
구조가 꼬이고 하드코딩·중복·불일치가 심해져서,
	•	지금은 엔진/백테스트/스캘핑부터 “다시 제대로” 리빌드 중.
	•	이 스캘핑 엔진/인프라가 엔진 표준(TEMPLATE) 이 되고,
이후 다른 전략(Swing, Trend-following, Mean-Reversion, Breakout, AI/News 등)을
같은 패턴으로 붙일 계획.
	•	철학(Philosophy):
	•	엔진 코어 = DO-NOT-TOUCH 레이어
→ 백테스트 / 페이퍼 / 라이브가 모두 동일 엔진을 사용.
	•	모든 행동은 config-based / YAML 기반
→ 전략/리스크/포트폴리오 파라미터는 전부 설정파일로 관리.
	•	Risk & Guard 우선
→ 슬리피지/일일 손실/계좌 손실/익스포저/플래시가드 등
FlowGuardian 계층에서 모두 통제.
	•	문서 → 코드 → 테스트 → 문서 업데이트 순환 루프를 절대 깨지 않는다.
	•	“앙상블”은 나중에 거창한 거 붙이는 게 아니라,
각 전략이 표준화된 인터페이스를 공유할 때 자연스럽게 얻는 구조로 간다.

⸻

==========================================================

1. 최종 TO-BE 아키텍처 개요

==========================================================

최종적으로 시스템은 아래 4개의 큰 레이어로 정리된다.
	1.	Core Engine Layer (DO-NOT-TOUCH)
	•	공통 엔진 로직 (캔들 처리, 시그널 호출, 포지션 관리, 주문 시뮬레이션 등)
	•	Backtest / Paper / Live 모드 공통 사용
	2.	Strategy & Ensemble Layer
	•	스캘핑 / 스윙 / 트렌드 / 역추세 / 브레이크아웃 / AI·뉴스 전략 등
	•	각 전략은 “전략 인터페이스”를 통해 엔진과만 이야기
	•	EnsembleManager가 여러 전략의 시그널을 취합·조합
	3.	Risk & Portfolio Layer
	•	RiskManager: per-trade / per-symbol / per-day / per-account 리스크 관리
	•	PortfolioManager: 멀티 심볼/멀티 전략의 포지션·PnL·DD를 단일 소스로 관리
	•	FlowGuardian: Drawdown, Exposure, Flash Guard, Slippage, Cooldown 등 가드
	4.	Infra & UX Layer
	•	데이터 수집 / Redis / Postgres · Timeseries DB
	•	CLI, Runbook, 모니터링, 로그, 리포트, 대시보드, 간단한 UI/UX (웹/데스크톱)
	•	Docker 기반 실행, Windsurf/Cursor 기반 개발 파이프라인

⸻

==========================================================

2. Core Engine Layer (DO-NOT-TOUCH) – TO-BE

==========================================================

2.1 공통 엔진 구조
	•	/execution/engine.py
	•	단일 메인 루프:
	•	시세 수집(WebSocket/REST → 표준 Tick/Candle 스트림)
	•	전략 호출 (strategy.generate_signals())
	•	시그널 → 주문 후보
	•	RiskManager 검사
	•	PortfolioManager 업데이트
	•	ExchangeAdapter(Paper/Live)로 주문 전송 or 시뮬레이션
	•	모드:
	•	BACKTEST: 과거 데이터, 빠른 반복
	•	PAPER: 실시간 시세 + 가상 체결
	•	LIVE: 실 계정 체결 (마지막 단계에서만 enable)
	•	공통 규칙:
	•	엔진의 기본 시그니처/입출력/이벤트 흐름은 모두 모드 공통.
	•	“이벤트가 어떻게 흐르는가”는 Core에서만 정의 →
전략/리스크/포트폴리오는 이 흐름 안에서만 동작.

2.2 모드 별 파라미터
	•	Backtest:
	•	파일·DB 기반 시세, 빠른 loop, wall-clock 무시.
	•	Paper:
	•	실시간 시세, duration_mode = wall_clock / market_time 선택.
	•	1h / 12h / 72h 같은 soak test에 사용.
	•	Live:
	•	실시간 시세 + 실제 주문.
	•	FlowGuardian + RiskGuard가 통과해야 주문이 실제로 나감.

⸻

==========================================================

3. Strategy & Ensemble Layer – TO-BE

==========================================================

3.1 전략 인터페이스 (공통)
	•	공통 인터페이스 예:
	•	StrategyBase:
	•	on_init(config, context)
	•	on_candle(symbol, timeframe, candle, context) -> list[Signal]
	•	on_position_update(position, context)
	•	get_state_snapshot() / load_state(snapshot) (장기간 실행 대비)
	•	각 전략은 “시그널 생성기” 역할만:
	•	포지션 크기, 계좌 레벨 리스크, 익스포저, DD 같은 것은
Risk/Portfolio Layer에서 관리.

3.2 전략 구성 (최소 6개)
	•	S1: Scalping Strategy (현재 리빌딩 중 – 기준 전략)
	•	짧은 타임프레임 (1m/3m/5m)
	•	MTF(예: 1m + 15m) 확인
	•	RSI, MACD, EMA, 볼린저, 볼륨, 실행 강도, 패턴 기반
	•	S2: Short-term Swing
	•	1h~4h 타임프레임, 며칠 단위 포지션
	•	S3: Trend-following
	•	추세 방향, MA/Ichimoku/ADX 계열.
	•	S4: Mean Reversion/Range
	•	과매수·과매도 구간에서 되돌림 노리는 전략.
	•	S5: Breakout / Momentum
	•	박스 돌파, 거래량 급증, 변동성 확대 구간.
	•	S6: AI/Sentiment/News-Driven
	•	(향후) GPT/LLM 분석, 온체인·뉴스·소셜 시그널 통합.

3.3 EnsembleManager – 최종 구조
	•	역할:
	•	여러 전략에서 나오는 시그널을 하나의 “실행 계획”으로 통합.
	•	기능:
	•	시그널 우선순위:
	•	예: 스캘핑 vs 스윙 충돌 시, 상위 타임프레임/우선 전략 우선.
	•	전략 가중치 / 활성도:
	•	전략별 weight, 최대 동시 전략 수 등.
	•	상황별 전략 온오프:
	•	변동성 높음 → 스캘핑/브레이크아웃 강화
	•	횡보 → Mean Reversion 강화, 트렌드 약화
	•	리밸런싱/비중 조절:
	•	Equity, PnL, DD에 따라 전략별 비중 동적으로 변경.

⸻

==========================================================

4. Risk & Portfolio Layer – TO-BE

==========================================================

4.1 PortfolioManager
	•	책임:
	•	PnL, Equity, Max DD, Exposure의 단일 소스.
	•	전략/심볼/포지션 레벨 통계 모두 여기서 계산.
	•	기능:
	•	Per-symbol/Per-strategy PnL aggregation
	•	Equity curve, daily PnL, running max-dd
	•	Scorecard 생성 시 사용되는 모든 핵심 메트릭 제공.

4.2 RiskManager & FlowGuardian
	•	RiskManager:
	•	per-trade 리스크 (R 단위, ATR 기반 SL, TP, 트레일링 등)
	•	레버리지 캡, 최대 포지션 수, per-symbol 노출 제한
	•	일일 손실 한도, 계좌 전체 DD 제한
	•	FlowGuardian (Guard 세트):
	•	Drawdown Guard
	•	Exposure Guard
	•	Slippage Guard
	•	Flash Guard (특정 시간 내 급격한 변동 감지)
	•	Cooldown Guard (연속 진입 제한)
	•	규칙:
	•	모든 주문 전 FlowGuardian에서 최종 승인.
	•	Guard triggered → 엔진은 안전하게 종료 또는 대기 상태로 들어감.
	•	Guard의 설정값은 전략별·환경별(YAML)로 제어 가능.

⸻

==========================================================

5. Data / Infra / 실행 구조 – TO-BE

==========================================================

5.1 데이터 & 스토리지
	•	Postgres(+TimescaleDB 가능):
	•	시세 히스토리, 트레이드 로그, 튜닝 결과, 전략 메타데이터.
	•	Redis:
	•	실시간 시그널 큐, 상태 캐싱, Guard 상태, run_id·env 네임스페이스 구조.
	•	파일 시스템:
	•	scorecards/ – 각 run_id별 effective_config, scorecard.csv/md
	•	logs/ – application.log, guard 로그, 모니터링 스냅샷
	•	configs/ – 전략/리스크/포폴/모드별 YAML

5.2 실행 모드
	•	로컬 개발:
	•	Windows/WSL/Ubuntu + Docker Desktop
	•	Windsurf/Cursor를 통한 AI 주도 개발.
	•	Docker Compose:
	•	trading_redis, trading_db_postgres, (추후) api-server, ui 등.
	•	향후:
	•	필요 시 K8s로 확장 (단, 이 프로젝트에서는 우선 Docker·단일 서버 기준).

⸻

==========================================================

6. 튜닝/백테스트/검증 파이프라인 – TO-BE

==========================================================

6.1 Backtest Flow
	1.	설정된 기간·심볼·전략·파라미터로 backtest 실행.
	2.	엔진은 backtest 모드로 동일 코어를 사용.
	3.	결과:
	•	PnL, Winrate, PF, Max DD, MFE/MAE, trade-by-trade 로그.

6.2 Tuning Flow (중장기 TO-BE)
	•	Tuning Engine:
	•	Grid Search + Bayesian Optimization 조합.
	•	파라미터 공간 정의(YAML) → job-list(JSONL) 생성 → 병렬 실행 → result aggregate.
	•	목적:
	•	각 전략별 baseline parameter set 찾기.
	•	환경(예: BTC/ETH/Alt, 1m/3m/5m, Bull/Bear regime)에 따라 프리셋 생성.

⸻

==========================================================

7. UI / UX / Ops – TO-BE

==========================================================

7.1 운영 관점
	•	CLI Runbook:
	•	run_backtest.py
	•	run_paper.py
	•	run_live.py (마지막 단계에서만)
	•	각 스크립트는 Runbook 문서와 1:1 대응 (STEP 0~N).
	•	모니터링:
	•	실시간 로그 tail + Redis/DB 상태 확인 스크립트.
	•	Guard 발생 시 Slack/Telegram 알림 (404 같은 오류는 거래와 분리).

7.2 UI/UX (후반 단계)
	•	간단한 Web UI or Desktop UI (예: FastAPI + 간단 대시보드):
	•	현재 Equity / DD / 포지션 / 전략별 PnL / 최근 트레이드.
	•	Guard 상태 (ON/OFF, 최근 트리거 원인).
	•	전략별 on/off 토글 (단, 엔진/로직은 그대로 유지한 채 제어만).

⸻

==========================================================

8. 확장성 & 장기 확장 TO-BE

==========================================================

8.1 전략 확장
	•	새로운 전략 추가 시 요구사항:
	•	StrategyBase 상속, 공통 인터페이스 준수.
	•	설정은 전부 configs/strategies/<name>.yml에서 관리.
	•	엔진/리스크/포트폴리오 코어는 건드리지 않고 추가.

8.2 자산·거래소 확장
	•	현재 타겟:
	•	1차: Binance Futures (BTCUSDT, 주요 페어)
	•	2차: Upbit Spot (FK, 현물 기반 전략)
	•	3차(옵션): 국내 증권(키움 API) – 별도 모듈.
	•	확장 방식:
	•	exchanges/ 아래에 거래소 별 어댑터 추가.
	•	공통 인터페이스만 맞추면 Ensemble/엔진은 그대로 재사용.

8.3 AI/ML 확장
	•	시그널 레벨:
	•	GPT/LLM이 “시장 상태 요약/시나리오/리스크 코멘트” 제공.
	•	튜닝 레벨:
	•	AI가 파라미터 공간 설계/축소/변형 제안.
	•	운영 레벨:
	•	AI가 로그·Scorecard를 읽고 “오늘은 어떤 전략만 ON” 같은 제안 모드.

⸻

==========================================================

9. 현재 위치 & 마이그레이션 로드맵

==========================================================

9.1 현재 위치 (이 채팅 기준)
	•	과거:
	•	이미 6전략 앙상블 + 베이시안 튜닝까지 구조를 올렸다가
DRY/SRP 깨지고, 하드코딩·중복·Guard 불일치 등으로 유지불가 상태.
	•	지금:
	•	스캘핑 엔진 + 백테스트 + Paper 모드 + Guard + Scorecard를
“표준 구조”로 재구성 중.
	•	PHASE16 근처에서:
	•	단일 엔진으로 Backtest/Paper 모드를 일치시키고,
	•	Real-time Paper 1h/12h/72h soak test를 통해
구조적 문제(Guard, exposure, DD, duration 등)를 드러내는 단계.

9.2 앞으로 순서(요약)
	1.	스캘핑 전략 + 엔진/리스크/포폴 구조 안정화
	•	Real Paper 72h soak test PASS가 최소 목표.
	2.	스윙/트렌드/역추세/브레이크아웃 전략을
스캘핑과 동일한 패턴으로 이식
	3.	EnsembleManager 구현
	•	전략 간 시그널 조합/우선순위/비중 관리.
	4.	튜닝 파이프라인 정리
	•	각 전략별 튜닝 → 전략 프리셋 확정 → 앙상블 레벨 튜닝.
	5.	UI/대시보드 + 운영 자동화
	•	모니터링, 리포트, 설정 관리, 환경 전환.
	6.	Live 모드 제한적 오픈
	•	소액/낮은 레버리지/강력한 Guard 묶어서
실제 계좌에서 “상용 수준” 안정성을 검증.

⸻

==========================================================

10. 새 채팅에서 사용할 한 줄 요약

==========================================================

“우리는 원래 6개 전략 앙상블 봇 + 베이시안 튜닝까지 만든 상태였지만,
구조가 꼬여서 지금은 스캘핑 엔진/백테스트/페이퍼/리스크/포트폴리오/가드를
‘표준 코어’로 다시 설계·구현 중이다.
이 코어가 안정되면, 기존 6전략 + 앙상블 + 튜닝을 이 위에 재구축해서
최종적으로 상용급 완전 자동 앙상블 트레이딩 봇을 만드는 것이 TO-BE다.”

이 문서랑 아까 만든 Context Snapshot 둘 다 프로젝트에 첨부해두면,
새 채팅 열었을 때 “이거 두 개 읽고 시작해” 라고만 하면 웬만한 건 복구 가능하게 설계된 거라 보면 된다.