#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE27-3: Baseline Strategy Execution Validation Runner
=========================================================
ADX 통합 베이스라인 전략 실행 검증

목표:
- btc5m_baseline_v1 전략 (ADX 레짐 기반) 실행
- 10-15분 PAPER 모드 실행
- Strategy Signals (True) > 0 확인 (Signal Dropout 해소 검증)
- ActivityTracker 요약 출력

역할:
1. Pre-flight 체크 (Docker, DB/Redis 상태)
2. Clean state 실행 (이전 실행 데이터 초기화)
3. run_v2.py를 통해 PAPER 실행
4. ActivityTracker 요약 JSON 출력
"""
import sys
import subprocess
import json
import time
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def log(msg: str):
    """간단한 로그 출력"""
    print(f"[PHASE27-3] {msg}")


def run_command(cmd: list, cwd: Path = PROJECT_ROOT) -> tuple:
    """
    명령어 실행 (Unicode 에러 방지)
    Returns: (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'  # Unicode 에러 방지
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def check_docker():
    """Docker 컨테이너 상태 확인"""
    log("Docker 상태 확인 중...")
    exit_code, stdout, stderr = run_command(["docker", "ps"])
    
    if exit_code != 0:
        log(f"ERROR: Docker가 실행 중이지 않습니다: {stderr}")
        return False
    
    # Redis/Postgres 컨테이너 확인
    if "redis" not in stdout.lower():
        log("WARNING: Redis 컨테이너가 보이지 않습니다.")
    
    if "postgres" not in stdout.lower():
        log("WARNING: Postgres 컨테이너가 보이지 않습니다.")
    
    log("Docker 상태: OK")
    return True


def clean_state():
    """DB/Redis 상태 초기화"""
    log("Clean state 실행 중...")
    clean_script = PROJECT_ROOT / "scripts" / "clean_state_complete.py"
    
    if not clean_script.exists():
        log(f"WARNING: Clean script 없음: {clean_script}")
        return True
    
    exit_code, stdout, stderr = run_command(["python", str(clean_script)])
    
    if exit_code != 0:
        log(f"WARNING: Clean state 실패 (계속 진행): {stderr[:200]}")
    else:
        log("Clean state: OK")
    
    return True


def run_paper_execution(config_path: str):
    """
    run_v2.py를 통해 PAPER 실행
    
    Args:
        config_path: Config 파일 경로 (상대 경로 or 절대 경로)
    """
    log(f"PAPER 실행 시작: {config_path}")
    log("=" * 60)
    
    run_script = PROJECT_ROOT / "scripts" / "run_v2.py"
    
    if not run_script.exists():
        log(f"ERROR: run_v2.py 없음: {run_script}")
        return False
    
    # run_v2.py 실행 (출력은 실시간으로)
    cmd = ["python", str(run_script), "--config", config_path]
    
    log(f"실행 명령: {' '.join(cmd)}")
    log("=" * 60)
    
    try:
        # 실시간 출력을 위해 subprocess.Popen 사용
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 실시간 출력
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line, end='')
        
        process.wait()
        
        if process.returncode != 0:
            log(f"ERROR: PAPER 실행 실패 (exit code: {process.returncode})")
            return False
        
        log("=" * 60)
        log("PAPER 실행 완료")
        return True
    
    except Exception as e:
        log(f"ERROR: 실행 중 예외 발생: {e}")
        return False


def print_activity_summary(summary_file: Path):
    """ActivityTracker 요약 JSON 출력"""
    if not summary_file.exists():
        log(f"WARNING: ActivityTracker 요약 파일 없음: {summary_file}")
        return
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        log("=" * 60)
        log("ActivityTracker 요약:")
        log("=" * 60)
        
        # 핵심 지표 출력
        if 'strategy_signals' in data:
            total = data['strategy_signals'].get('total', 0)
            true_count = data['strategy_signals'].get('true', 0)
            false_count = data['strategy_signals'].get('false', 0)
            
            log(f"Strategy Signals:")
            log(f"  - Total: {total}")
            log(f"  - True: {true_count} ({true_count/total*100:.1f}%)" if total > 0 else "  - True: 0")
            log(f"  - False: {false_count} ({false_count/total*100:.1f}%)" if total > 0 else "  - False: 0")
        
        if 'ensemble_decisions' in data:
            ens = data['ensemble_decisions']
            log(f"Ensemble Decisions:")
            log(f"  - Total: {ens.get('total', 0)}")
            log(f"  - Tier1: {ens.get('tier1', 0)}")
            log(f"  - Tier2: {ens.get('tier2', 0)}")
            log(f"  - Skip: {ens.get('skip', 0)}")
        
        if 'orders' in data:
            orders = data['orders']
            log(f"Orders:")
            log(f"  - Submitted: {orders.get('submitted', 0)}")
            log(f"  - Filled: {orders.get('filled', 0)}")
            log(f"  - Rejected: {orders.get('rejected', 0)}")
        
        log("=" * 60)
        log(f"전체 요약 파일: {summary_file}")
        
    except Exception as e:
        log(f"ERROR: 요약 파일 읽기 실패: {e}")


def main():
    """메인 실행"""
    log("=" * 60)
    log("PHASE27-3: Baseline Strategy Execution Validation")
    log("=" * 60)
    
    # Config 경로
    config_path = "configs/paper/phase27_3_single_symbol_15m_adx.yml"
    summary_file = PROJECT_ROOT / "docs" / "PHASE27" / "phase27_3_single_symbol_15m_adx_summary.json"
    
    # 1. Pre-flight: Docker 확인
    if not check_docker():
        log("ERROR: Pre-flight 실패 (Docker)")
        return 1
    
    # 2. Clean state
    clean_state()
    
    # 3. 잠시 대기 (Redis/DB 안정화)
    log("2초 대기 (시스템 안정화)...")
    time.sleep(2)
    
    # 4. PAPER 실행
    success = run_paper_execution(config_path)
    
    if not success:
        log("ERROR: PAPER 실행 실패")
        return 1
    
    # 5. ActivityTracker 요약 출력
    print_activity_summary(summary_file)
    
    log("=" * 60)
    log("PHASE27-3 실행 완료")
    log("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
