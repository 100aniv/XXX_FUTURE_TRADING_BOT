#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE13 Optuna 튜닝 모니터링 스크립트
======================================
실행 중인 Optuna study의 진행 상황을 실시간으로 모니터링합니다.

사용법:
    python scripts/monitor_tuning.py --study phase13_3m_production
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

try:
    import optuna
except ImportError:
    print("❌ Optuna가 설치되지 않았습니다: pip install optuna")
    exit(1)

# 로컬 Postgres storage
STORAGE_URL = "postgresql://trading_user:trading_pw_2024@localhost:5433/trading_db"


def monitor_study(study_name: str, refresh_interval: int = 30):
    """Study 진행 상황을 주기적으로 모니터링"""
    try:
        storage = optuna.storages.RDBStorage(STORAGE_URL)
        study = optuna.load_study(study_name=study_name, storage=storage)
        
        print(f"📊 [MONITOR] Study: {study_name}")
        print(f"🔄 [MONITOR] 새로고침 간격: {refresh_interval}초")
        print("=" * 80)
        
        last_trial_count = 0
        
        while True:
            trials = study.get_trials(deepcopy=False)
            current_trial_count = len(trials)
            
            # 새로운 trial이 완료되었을 때만 출력
            if current_trial_count > last_trial_count:
                print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] 진행 상황:")
                print(f"   완료된 Trials: {current_trial_count}")
                
                if trials:
                    # 최신 trial 정보
                    latest_trial = trials[-1]
                    print(f"\n   📌 최근 Trial #{latest_trial.number}:")
                    print(f"      상태: {latest_trial.state}")
                    if latest_trial.value is not None:
                        print(f"      Score: {latest_trial.value:.4f}")
                    if latest_trial.params:
                        print(f"      주요 파라미터:")
                        for k in ['rr', 'max_cross_age_candles', 'rsi_oversold', 'rsi_overbought']:
                            if k in latest_trial.params:
                                print(f"         {k}: {latest_trial.params[k]}")
                    
                    # Best trial
                    try:
                        best_trial = study.best_trial
                        print(f"\n   🏆 현재 Best Trial #{best_trial.number}:")
                        print(f"      Score: {best_trial.value:.4f}")
                        print(f"      주요 파라미터:")
                        for k in ['rr', 'max_cross_age_candles', 'rsi_oversold', 'rsi_overbought']:
                            if k in best_trial.params:
                                print(f"         {k}: {best_trial.params[k]}")
                    except ValueError:
                        print("   ⚠️  아직 성공한 trial이 없습니다.")
                
                print("=" * 80)
                last_trial_count = current_trial_count
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n✋ [MONITOR] 모니터링을 종료합니다.")
    except Exception as e:
        print(f"\n❌ [MONITOR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Optuna 튜닝 모니터링")
    parser.add_argument("--study", type=str, required=True, help="Study 이름")
    parser.add_argument("--interval", type=int, default=30, help="새로고침 간격(초)")
    
    args = parser.parse_args()
    monitor_study(args.study, args.interval)


if __name__ == "__main__":
    main()
