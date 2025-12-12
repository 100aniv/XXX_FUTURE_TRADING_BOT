#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE34-0: Backtest/Paper Run Watchdog
======================================
실행 종료를 강제 보장하는 감시자 래퍼

기능:
1. 대상 커맨드 실행 + timeout
2. 종료 후 3종 체크 자동화:
   - Exit code == 0
   - Summary JSON 존재
   - 잔존 프로세스 0
3. 실패 시 프로세스 트리 kill + 로그 덤프

Usage:
    python scripts/utils/run_watchdog.py \
        --command "python scripts/run_backtest.py --config configs/backtest/xxx.yml" \
        --timeout 3600 \
        --summary-path "reports/backtest/xxx/summary.json" \
        --run-id "xxx"
"""
import sys
import argparse
import subprocess
import time
import json
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("run_watchdog")


class WatchdogResult:
    """Watchdog 실행 결과"""
    def __init__(self):
        self.success = False
        self.exit_code = None
        self.duration_seconds = 0
        self.timeout_triggered = False
        self.checks = {
            "exit_code": {"passed": False, "value": None},
            "summary_json": {"passed": False, "value": None},
            "process_remnants": {"passed": False, "value": None}
        }
        self.error_message = None
        self.log_tail = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "timeout_triggered": self.timeout_triggered,
            "checks": self.checks,
            "error_message": self.error_message,
            "log_tail_lines": len(self.log_tail)
        }


def find_process_by_cmdline(search_string: str) -> List[psutil.Process]:
    """커맨드라인에 특정 문자열이 포함된 프로세스 찾기"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any(search_string in arg for arg in cmdline):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes


def kill_process_tree(pid: int, timeout: int = 5):
    """프로세스 트리 전체 종료"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # 자식부터 종료
        for child in children:
            try:
                logger.warning(f"🔪 Killing child process: {child.pid} ({child.name()})")
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 부모 종료
        try:
            logger.warning(f"🔪 Killing parent process: {parent.pid} ({parent.name()})")
            parent.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # 정리 대기
        gone, alive = psutil.wait_procs([parent] + children, timeout=timeout)
        
        # 강제 종료
        for proc in alive:
            try:
                logger.error(f"⚠️  Force killing: {proc.pid}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to kill process tree: {e}")
        return False


def check_exit_code(exit_code: int) -> bool:
    """Exit code 검증"""
    return exit_code == 0


def check_summary_json(summary_path: Path) -> bool:
    """Summary JSON 존재 및 유효성 검증"""
    if not summary_path.exists():
        return False
    
    try:
        with open(summary_path, 'r') as f:
            data = json.load(f)
        # 최소 필수 키 확인
        return 'run_id' in data and 'timestamp' in data
    except Exception as e:
        logger.error(f"❌ Summary JSON 파싱 실패: {e}")
        return False


def check_process_remnants(run_id: Optional[str] = None) -> Dict[str, Any]:
    """Python 프로세스 잔존 확인 (watchdog 자신 제외)"""
    search_terms = ["run_backtest", "run_paper", "engine.py"]
    if run_id:
        search_terms.append(run_id)
    
    current_pid = psutil.Process().pid
    remnants = []
    
    for term in search_terms:
        procs = find_process_by_cmdline(term)
        for proc in procs:
            try:
                # Watchdog 자신 제외
                if proc.pid == current_pid:
                    continue
                
                remnants.append({
                    "pid": proc.pid,
                    "name": proc.name(),
                    "cmdline": ' '.join(proc.cmdline()[:3])  # 처음 3개 인자만
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    return {
        "passed": len(remnants) == 0,
        "count": len(remnants),
        "processes": remnants
    }


def run_with_timeout(command: List[str], timeout: int, log_file: Optional[Path] = None) -> tuple[int, bool]:
    """
    커맨드 실행 + timeout
    
    Returns:
        (exit_code, timeout_triggered)
    """
    logger.info(f"🚀 실행 시작: {' '.join(command)}")
    logger.info(f"⏱️  Timeout: {timeout}초")
    
    start_time = time.time()
    timeout_triggered = False
    
    try:
        # 로그 파일 핸들
        log_handle = None
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(log_file, 'w', encoding='utf-8')
        
        # 프로세스 시작
        proc = subprocess.Popen(
            command,
            stdout=log_handle or subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # 라인 버퍼링
        )
        
        # Wait with timeout
        try:
            exit_code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ TIMEOUT: {timeout}초 초과")
            timeout_triggered = True
            
            # 프로세스 트리 강제 종료
            kill_process_tree(proc.pid, timeout=10)
            exit_code = -1
        
        duration = time.time() - start_time
        logger.info(f"⏱️  실행 종료: {duration:.1f}초")
        
        if log_handle:
            log_handle.close()
        
        return exit_code, timeout_triggered
    
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return -1, False


def read_log_tail(log_file: Path, lines: int = 50) -> List[str]:
    """로그 파일 마지막 N줄 읽기"""
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        logger.error(f"❌ 로그 읽기 실패: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="PHASE34-0: Run Watchdog")
    parser.add_argument('--command', required=True, help='실행할 커맨드 (full command line)')
    parser.add_argument('--timeout', type=int, default=7200, help='타임아웃 (초, 기본 2시간)')
    parser.add_argument('--summary-path', required=True, help='Summary JSON 경로')
    parser.add_argument('--run-id', help='Run ID (프로세스 검색용)')
    parser.add_argument('--log-file', help='로그 출력 파일 (선택)')
    parser.add_argument('--report-file', help='Watchdog 리포트 JSON (선택)')
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🐕 PHASE34-0: Run Watchdog Started")
    logger.info("=" * 80)
    
    result = WatchdogResult()
    summary_path = Path(args.summary_path)
    log_file = Path(args.log_file) if args.log_file else None
    
    # 1. 실행
    command_list = args.command.split()
    exit_code, timeout_triggered = run_with_timeout(
        command_list,
        args.timeout,
        log_file
    )
    
    result.exit_code = exit_code
    result.timeout_triggered = timeout_triggered
    
    # 2. Exit code 체크
    logger.info(f"✅ CHECK 1/3: Exit Code = {exit_code}")
    result.checks["exit_code"]["value"] = exit_code
    result.checks["exit_code"]["passed"] = check_exit_code(exit_code)
    
    # 3. Summary JSON 체크
    logger.info(f"✅ CHECK 2/3: Summary JSON = {summary_path}")
    result.checks["summary_json"]["value"] = str(summary_path)
    result.checks["summary_json"]["passed"] = check_summary_json(summary_path)
    
    # 4. 프로세스 잔존 체크
    logger.info("✅ CHECK 3/3: Process Remnants")
    time.sleep(2)  # 종료 대기
    remnants_result = check_process_remnants(args.run_id)
    result.checks["process_remnants"] = remnants_result
    
    # 5. 판정
    all_checks_passed = all(
        check.get("passed", False) for check in result.checks.values()
    )
    result.success = all_checks_passed and not timeout_triggered
    
    # 6. 로그 tail (실패 시만)
    if not result.success and log_file:
        result.log_tail = read_log_tail(log_file, lines=50)
    
    # 7. 결과 출력
    logger.info("=" * 80)
    logger.info("📊 WATCHDOG RESULT")
    logger.info("=" * 80)
    logger.info(f"Success: {result.success}")
    logger.info(f"Exit Code: {result.exit_code} ({'PASS' if result.checks['exit_code']['passed'] else 'FAIL'})")
    logger.info(f"Summary JSON: {'EXISTS' if result.checks['summary_json']['passed'] else 'MISSING'}")
    logger.info(f"Process Remnants: {remnants_result['count']} ({'PASS' if remnants_result['passed'] else 'FAIL'})")
    
    if timeout_triggered:
        logger.error(f"⏰ TIMEOUT TRIGGERED: {args.timeout}초")
    
    if not remnants_result['passed']:
        logger.warning("⚠️  잔존 프로세스:")
        for proc in remnants_result['processes']:
            logger.warning(f"  - PID {proc['pid']}: {proc['name']} ({proc['cmdline']})")
    
    # 8. 리포트 저장
    if args.report_file:
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"📄 리포트 저장: {report_path}")
    
    logger.info("=" * 80)
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
