#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 베이지안 튜너 CLI (Generic Bayesian Tuner CLI)
====================================================
모든 전략에 대해 페이퍼/백테스트 모드 베이지안 최적화 실행

사용법:
    python -u common/tuner_cli.py --strategy scalping --tuning scalp_paper --trials 5 --publish file

주요 기능:
- Postgres에서 7일 롤링 메트릭 수집 (trading.trades 테이블)
- Optuna TPE 샘플러로 하이퍼파라미터 탐색
- 최적 파라미터를 configs/<전략>/active.yml에 자동 발행
- 발행된 설정으로 페이퍼 컨테이너 바로 실행 가능
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

from tuning.tuning_core import TunerCore


def parse_args():
    """CLI 인자 파싱"""
    p = argparse.ArgumentParser(description="범용 베이지안 튜너 (페이퍼/백테스트)")
    
    # 필수 인자
    p.add_argument("--strategy", required=True, 
                   choices=["scalping", "daytrade", "trend", "swing", "reversion", "breakout"],
                   help="튜닝할 전략 선택")
    p.add_argument("--study", required=True,
                   help="Study 이름 (예: scalping_paper_20251027)")
    
    # Optuna 설정
    p.add_argument("--storage", 
                   default=os.getenv("OPTUNA_STORAGE", "postgresql://trading_user:trading_pw_2024@db_postgres:5432/trading_db"),
                   help="Optuna 스토리지 (PostgreSQL URL). 기본: PostgreSQL")
    p.add_argument("--trials", type=int, default=1,
                   help="실행할 Trial 횟수 (기본: 1)")
    
    # 메트릭 윈도우 설정
    p.add_argument("--window-days", type=int, 
                   default=int(os.getenv("TUNE_WINDOW_DAYS", 7)),
                   help="롤링 메트릭 윈도우 (일 단위, 기본: 7일)")
    p.add_argument("--t-min", type=int, default=None, 
                   help="최소 거래수 (미지정 시 전략별 기본값 사용)")
    p.add_argument("--mdd-cap", type=float, 
                   default=float(os.getenv("MDD_CAP", 8.0)),
                   help="최대 허용 MDD % (기본: 8.0)")
    
    # 파라미터 발행 설정
    p.add_argument("--publish", choices=["none", "file"], 
                   default=os.getenv("TUNE_PUBLISH", "none"),
                   help="파라미터 발행 모드 (none: 발행 안함, file: YAML 파일 생성)")
    p.add_argument("--publish-dir", 
                   default=os.getenv("TUNE_PUBLISH_DIR", ""),
                   help="발행 디렉토리 (미지정 시 configs/<전략>/)")
    
    return p.parse_args()


def main():
    """메인 함수: 튜너 초기화 및 실행"""
    args = parse_args()

    # Study 이름
    study_name = args.study

    # 발행 디렉토리 생성
    publish_dir = args.publish_dir or None
    if args.publish == "file" and publish_dir:
        Path(publish_dir).mkdir(parents=True, exist_ok=True)

    # SQLite 스토리지일 경우 디렉토리 보장
    if isinstance(args.storage, str) and args.storage.startswith("sqlite///"):
        # 잘못된 형식 보호 (실제 기본은 sqlite:///)
        pass
    if isinstance(args.storage, str) and args.storage.startswith("sqlite:///"):
        db_path = args.storage.replace("sqlite:///", "", 1)
        try:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # TunerCore 초기화
    tuner = TunerCore(
        strategy_id=args.strategy,
        study_name=study_name,
        storage=args.storage,
        window_days=args.window_days,
        t_min=args.t_min,
        mdd_cap=args.mdd_cap,
        publish_mode=args.publish,
        publish_dir=publish_dir,
    )

    # 베이지안 최적화 실행
    print(f"🚀 [{args.strategy.upper()}|{study_name}] 튜닝 시작: {args.trials}회 Trial", flush=True)
    tuner.optimize(n_trials=args.trials)
    print(f"✅ [{args.strategy.upper()}|{study_name}] 튜닝 완료", flush=True)


if __name__ == "__main__":
    main()
