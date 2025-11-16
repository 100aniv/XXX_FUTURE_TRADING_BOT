#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 베이지안 튜너 CLI (Generic Bayesian Tuner CLI)
====================================================
모든 전략에 대해 페이퍼/백테스트 모드 베이지안 최적화 실행

사용법:
    # 페이퍼 모드
    python -m tuning.tuning_cli --strategy scalping --study scalp_paper --trials 5 --mode paper
    
    # 백테스트 모드
    python -m tuning.tuning_cli \\
        --strategy scalping --study scalping_1m_v1 --trials 30 --mode backtest \\
        --symbol BTCUSDT --timeframe 1m \\
        --start-date 2024-10-01 --end-date 2024-12-30 \\
        --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv

주요 기능:
- 페이퍼 모드: Postgres에서 7일 롤링 메트릭 수집
- 백테스트 모드: subprocess로 백테스트 실행, scorecard.csv 파싱
- Train/Validation 분할로 Overfitting 방지
- Optuna TPE 샘플러로 하이퍼파라미터 탐색
- 최적 파라미터를 configs/<전략>/active.yml에 자동 발행
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

from tuning.tuning_core import TunerCore, get_optuna_storage


def parse_args():
    """공용 CLI 인자 파싱"""
    p = argparse.ArgumentParser(description="범용 베이지안 튜너 (페이퍼/백테스트)")
    
    # 필수 인자
    p.add_argument("--strategy", required=True, 
                   choices=["scalping", "daytrade", "trend", "swing", "reversion", "breakout"],
                   help="튜닝할 전략 선택")
    p.add_argument("--study", required=True,
                   help="Study 이름 (예: scalping_paper_20251027)")
    
    # 모드 선택 (paper|backtest)
    p.add_argument("--mode", 
                   choices=["paper", "backtest"],
                   default="paper",
                   help="튜닝 모드 (paper: 페이퍼 모드, backtest: 백테스트 모드)")
    
    # Optuna 설정
    p.add_argument("--storage", 
                   default=None,
                   help="Optuna Storage (기본: Postgres trading_db, Env: TUNING_DB_URL 또는 DATABASE_URL)")
    p.add_argument("--trials", type=int, default=1,
                   help="실행할 Trial 횟수 (기본: 1)")
    p.add_argument("--phase", 
                   choices=["14", "15"],
                   default="14",
                   help="튜닝 페이즈 (14: PHASE14 기본, 15: PHASE15 RR 재탐색)")
    
    # 메트릭 윈도우 설정 (페이퍼 모드 전용)
    p.add_argument("--window-days", type=int, 
                   default=int(os.getenv("TUNE_WINDOW_DAYS", 7)),
                   help="[페이퍼 모드] 롤링 메트릭 윈도우 (일 단위, 기본: 7일)")
    p.add_argument("--t-min", type=int, default=None, 
                   help="최소 거래수 (미지정 시 전략별 기본값 사용)")
    p.add_argument("--mdd-cap", type=float, 
                   default=float(os.getenv("MDD_CAP", 8.0)),
                   help="최대 허용 MDD %% (기본: 8.0)")
    
    # 파라미터 발행 설정
    p.add_argument("--publish", choices=["none", "file"], 
                   default=os.getenv("TUNE_PUBLISH", "none"),
                   help="파라미터 발행 모드 (none: 발행 안함, file: YAML 파일 생성)")
    p.add_argument("--publish-dir", 
                   default=os.getenv("TUNE_PUBLISH_DIR", ""),
                   help="발행 디렉토리 (미지정 시 configs/<전략>/)")
    
    # 백테스트 모드 전용 파라미터
    p.add_argument("--symbol", 
                   default=None,
                   help="[백테스트 모드] 심볼 (예: BTCUSDT)")
    p.add_argument("--timeframe", 
                   default=None,
                   help="[백테스트 모드] 타임프레임 (예: 1m, 5m, 15m)")
    p.add_argument("--start-date", 
                   default=None,
                   help="[백테스트 모드] 시작 날짜 (YYYY-MM-DD)")
    p.add_argument("--end-date", 
                   default=None,
                   help="[백테스트 모드] 종료 날짜 (YYYY-MM-DD)")
    p.add_argument("--data-path", 
                   default=None,
                   help="[백테스트 모드] 데이터 파일 경로 (선택)")
    p.add_argument("--train-val-split", 
                   action="store_true",
                   default=True,
                   help="[백테스트 모드] Train/Val 분할 여부 (기본: True)")
    p.add_argument("--no-train-val-split", 
                   dest="train_val_split",
                   action="store_false",
                   help="[백테스트 모드] Train/Val 분할 비활성화")
    p.add_argument("--val-penalty-weight", 
                   type=float,
                   default=0.3,
                   help="[백테스트 모드] Validation penalty 가중치 (기본: 0.3)")
    
    return p.parse_args()


def main():
    """메인 함수: 튜너 초기화 및 실행"""
    args = parse_args()

    # Study 이름
    study_name = args.study

    # Storage 자동 결정 (Postgres ONLY)
    if args.storage is None:
        storage = get_optuna_storage()  # ValueError if SQLite detected
    else:
        storage = args.storage
        
        # SQLite 감지 → 즉시 에러
        if "sqlite" in storage.lower():
            print("❌ CRITICAL ERROR: SQLite is FORBIDDEN for tuning storage!")
            print(f"   Detected: {storage}")
            print("   Solution: Remove --storage or use PostgreSQL URL")
            print("   Example: --storage postgresql://trading_user:trading_pw_2024@localhost:5432/trading_db")
            return 1
        
        print(f"📌 [TUNING STORAGE] 사용자 지정: {storage.split('@')[1] if '@' in storage else storage}")

    # 발행 디렉토리 생성
    publish_dir = args.publish_dir or None
    if args.publish == "file" and publish_dir:
        Path(publish_dir).mkdir(parents=True, exist_ok=True)

    # 백테스트 모드 파라미터 검증
    if args.mode == "backtest":
        missing = []
        if not args.symbol:
            missing.append("--symbol")
        if not args.timeframe:
            missing.append("--timeframe")
        if not args.start_date:
            missing.append("--start-date")
        if not args.end_date:
            missing.append("--end-date")
        
        if missing:
            print(f"❌  백테스트 모드 실행 실패: 다음 필수 파라미터가 누락되었습니다:")
            for param in missing:
                print(f"   - {param}")
            print("\n사용 예시:")
            print("  python -m tuning.tuning_cli \\")
            print("    --strategy scalping --study scalping_1m_test --trials 1 --mode backtest \\")
            print("    --symbol BTCUSDT --timeframe 1m \\")
            print("    --start-date 2024-10-01 --end-date 2024-12-30 \\")
            print("    --data-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv")
            return 1
        
        # 백테스트 설정 확인 로그
        print("\n" + "="*80)
        print("🔍 백테스트 튜닝 설정 확인")
        print("="*80)
        print(f"  전략:     {args.strategy}")
        print(f"  Study:    {study_name}")
        print(f"  Trials:   {args.trials}회")
        print(f"  심볼/TF:  {args.symbol} / {args.timeframe}")
        print(f"  기간:     {args.start_date} ~ {args.end_date}")
        if args.data_path:
            print(f"  데이터:   {args.data_path}")
        else:
            print(f"  데이터:   (기본 경로 사용)")
        print(f"  Train/Val 분할: {'활성화' if args.train_val_split else '비활성화'}")
        if args.train_val_split:
            print(f"  Val Penalty 가중치: {args.val_penalty_weight}")
        print(f"  최소 거래수 (t_min): {args.t_min if args.t_min else '전략별 기본값'}")
        print(f"  MDD Cap:  {args.mdd_cap}%")
        print("="*80 + "\n")

    # TunerCore 초기화
    tuner = TunerCore(
        strategy_id=args.strategy,
        study_name=study_name,
        storage=storage,  # 자동 결정된 storage 사용
        mode=args.mode,
        window_days=args.window_days,
        t_min=args.t_min,
        mdd_cap=args.mdd_cap,
        publish_mode=args.publish,
        publish_dir=publish_dir,
        # 백테스트 모드 파라미터
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start_date,
        end_date=args.end_date,
        data_path=args.data_path,
        train_val_split=args.train_val_split,
        val_penalty_weight=args.val_penalty_weight,
        # PHASE15 모드
        phase=args.phase,
    )

    # 베이지안 최적화 실행
    print(f"🚀 [{args.strategy.upper()}|{study_name}] 튜닝 시작: {args.trials}회 Trial ({args.mode} 모드)", flush=True)
    tuner.optimize(n_trials=args.trials)
    print(f"✅ [{args.strategy.upper()}|{study_name}] 튜닝 완료", flush=True)


if __name__ == "__main__":
    main()
