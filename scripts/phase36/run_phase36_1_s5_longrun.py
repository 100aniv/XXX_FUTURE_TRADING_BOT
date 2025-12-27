#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE36-1 S5: LONGRUN Funnel Analysis Runner
==============================================
6시간 PAPER 실행 + 1시간 간격 checkpoint + Funnel 분석

목표:
1. 6시간 동안 프로세스 크래시 0
2. 1시간 간격 체크포인트 N개(>=6) 생성
3. Funnel 상위 block reason TOP 5 확정

STOP RULES (시간 낭비 방지):
- 60-90분 trades=0 & signals=0 → 즉시 중단
- 특정 block reason 99%+ → 즉시 중단
- 예외/오류/DB persist 실패 급증 → 즉시 중단

Usage:
    python scripts/phase36/run_phase36_1_s5_longrun.py
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("phase36_1_s5_longrun")

# ============================================================================
# 상수
# ============================================================================

CONFIG_PATH = project_root / "configs" / "paper" / "phase36_1_s5_longrun_6h.yml"
DURATION_HOURS = 6.0
CHECKPOINT_INTERVAL_MINUTES = 60
EVIDENCE_DIR = project_root / "logs" / "evidence" / "phase36_1_s5_longrun"
CHECKPOINT_DIR = project_root / "logs" / "checkpoints" / "phase36_1_s5"

# STOP RULES
NO_ACTIVITY_THRESHOLD_MINUTES = 90  # 90분 동안 trades=0 & signals=0 → 중단
BLOCK_REASON_DOMINANCE_THRESHOLD = 0.99  # 특정 block reason 99%+ → 중단

# ============================================================================
# 유틸리티
# ============================================================================

def print_section(title: str):
    """섹션 헤더 출력"""
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def check_stop_rules(checkpoint_files: list) -> tuple[bool, str]:
    """
    STOP RULES 검증
    Returns: (should_stop, reason)
    """
    if not checkpoint_files:
        return False, ""
    
    # 최신 checkpoint 읽기
    latest_checkpoint = checkpoint_files[-1]
    try:
        with open(latest_checkpoint, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        counters = data.get("counters", {})
        signals = counters.get("signal_evaluated_total", 0)
        trades = counters.get("order_filled_total", 0)
        
        # STOP RULE A: 90분 동안 활동 없음
        if len(checkpoint_files) >= 2 and signals == 0 and trades == 0:
            elapsed_minutes = len(checkpoint_files) * CHECKPOINT_INTERVAL_MINUTES
            if elapsed_minutes >= NO_ACTIVITY_THRESHOLD_MINUTES:
                return True, f"NO_ACTIVITY: {elapsed_minutes}분 동안 signals=0, trades=0"
        
        # STOP RULE B: Block reason dominance
        block_reasons = counters.get("block_reasons", {})
        if block_reasons:
            total_blocks = sum(block_reasons.values())
            if total_blocks > 0:
                top_reason = max(block_reasons.items(), key=lambda x: x[1])
                dominance = top_reason[1] / total_blocks
                if dominance >= BLOCK_REASON_DOMINANCE_THRESHOLD:
                    return True, f"BLOCK_DOMINANCE: {top_reason[0]} = {dominance:.1%}"
        
        return False, ""
    
    except Exception as e:
        logger.warning(f"⚠️  Checkpoint 읽기 실패 (stop rules 체크 스킵): {e}")
        return False, ""


def collect_checkpoints() -> list:
    """Checkpoint 파일 수집"""
    if not CHECKPOINT_DIR.exists():
        return []
    
    checkpoint_files = sorted(CHECKPOINT_DIR.glob("checkpoint_*.json"))
    return checkpoint_files


def monitor_longrun(process: subprocess.Popen, start_time: datetime) -> int:
    """
    Longrun 모니터링
    - 1시간마다 checkpoint 확인
    - STOP RULES 체크
    - 프로세스 종료 대기
    """
    logger.info("🔍 Longrun 모니터링 시작...")
    
    check_interval = 60  # 1분마다 체크
    next_checkpoint_check = start_time + timedelta(minutes=CHECKPOINT_INTERVAL_MINUTES)
    
    while True:
        # 프로세스 종료 확인
        exit_code = process.poll()
        if exit_code is not None:
            logger.info(f"✅ 프로세스 종료: exit_code={exit_code}")
            return exit_code
        
        # 1분 대기
        time.sleep(check_interval)
        
        # Checkpoint 체크 시간?
        now = datetime.now()
        if now >= next_checkpoint_check:
            checkpoint_files = collect_checkpoints()
            logger.info(f"📊 Checkpoint 수집: {len(checkpoint_files)}개")
            
            # STOP RULES 체크
            should_stop, reason = check_stop_rules(checkpoint_files)
            if should_stop:
                logger.warning(f"⚠️  STOP RULE 발동: {reason}")
                logger.info("🛑 프로세스 중단...")
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    logger.warning("⚠️  프로세스 강제 종료...")
                    process.kill()
                return 1
            
            next_checkpoint_check += timedelta(minutes=CHECKPOINT_INTERVAL_MINUTES)
        
        # 최대 실행 시간 초과 체크 (safety)
        elapsed = (now - start_time).total_seconds() / 3600
        if elapsed > DURATION_HOURS + 0.5:  # 30분 버퍼
            logger.warning(f"⚠️  최대 실행 시간 초과: {elapsed:.2f}h > {DURATION_HOURS}h")
            logger.info("🛑 프로세스 중단...")
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            return 1


def save_summary(exit_code: int, start_time: datetime, end_time: datetime):
    """실행 요약 저장"""
    checkpoint_files = collect_checkpoints()
    
    summary = {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_hours": (end_time - start_time).total_seconds() / 3600,
        "checkpoint_count": len(checkpoint_files),
        "checkpoint_files": [str(f) for f in checkpoint_files],
    }
    
    # 최종 checkpoint 데이터 포함
    if checkpoint_files:
        try:
            with open(checkpoint_files[-1], 'r', encoding='utf-8') as f:
                final_checkpoint = json.load(f)
            summary["final_counters"] = final_checkpoint.get("counters", {})
        except Exception as e:
            logger.warning(f"⚠️  최종 checkpoint 읽기 실패: {e}")
    
    summary_path = EVIDENCE_DIR / "longrun_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 실행 요약 저장: {summary_path}")
    return summary


# ============================================================================
# 메인
# ============================================================================

def main():
    print_section("PHASE36-1 S5: LONGRUN Funnel Analysis")
    
    # 0. 환경 확인
    if not CONFIG_PATH.exists():
        logger.error(f"❌ Config 파일 없음: {CONFIG_PATH}")
        return 1
    
    logger.info(f"✅ Config: {CONFIG_PATH}")
    logger.info(f"⏱️  Duration: {DURATION_HOURS}h")
    logger.info(f"📊 Checkpoint 간격: {CHECKPOINT_INTERVAL_MINUTES}분")
    
    # 1. Checkpoint 디렉토리 초기화
    if CHECKPOINT_DIR.exists():
        import shutil
        shutil.rmtree(CHECKPOINT_DIR)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Checkpoint 디렉토리 초기화: {CHECKPOINT_DIR}")
    
    # 2. Evidence 디렉토리 준비
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Evidence 디렉토리: {EVIDENCE_DIR}")
    
    # 3. Paper 실행
    print_section("Paper 실행 시작")
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "run_paper.py"),
        "--config", str(CONFIG_PATH),
    ]
    
    logger.info(f"🚀 실행 명령: {' '.join(cmd)}")
    
    start_time = datetime.now()
    logger.info(f"⏰ 시작 시각: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 프로세스 시작 (stdout/stderr를 파일로 리다이렉트)
        log_file = EVIDENCE_DIR / "longrun.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=project_root
            )
        
        logger.info(f"✅ 프로세스 시작: PID={process.pid}")
        logger.info(f"📄 로그 파일: {log_file}")
        
        # 4. 모니터링
        exit_code = monitor_longrun(process, start_time)
        
        end_time = datetime.now()
        logger.info(f"⏰ 종료 시각: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 5. 요약 저장
        print_section("실행 요약")
        summary = save_summary(exit_code, start_time, end_time)
        
        logger.info(f"✅ Exit Code: {exit_code}")
        logger.info(f"⏱️  Duration: {summary['duration_hours']:.2f}h")
        logger.info(f"📊 Checkpoint Count: {summary['checkpoint_count']}")
        
        if exit_code == 0:
            logger.info("✅ LONGRUN 완료")
        else:
            logger.warning(f"⚠️  LONGRUN 종료 (exit_code={exit_code})")
        
        return exit_code
    
    except Exception as e:
        logger.error(f"❌ LONGRUN 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
