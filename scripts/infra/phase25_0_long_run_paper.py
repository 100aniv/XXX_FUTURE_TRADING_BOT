#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE25-0: Long-run PAPER Regression Harness
==============================================
장시간 PAPER 테스트 자동화 (최소 2H)

핵심 원칙:
- 6분 스모크는 개발/CI용, 2H+는 Acceptance용 (절대 혼용 금지)
- 완전 자동화: Pre-flight → Clean State → Run → Monitor → 분석 → 리포트
- 실시간 ERROR 감지 & 즉시 중단
- 명확한 Exit Code (0: PASS, 1: FAIL)

Usage:
    python scripts/infra/phase25_0_long_run_paper.py --config configs/paper/phase25_0_long_run_2h.yml --duration-hours 2.0
"""

import os
import sys
import time
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# 상수
# ============================================================================

# 기본값 (Acceptance용 최소값)
DEFAULT_DURATION_HOURS = 2.0
MIN_DURATION_FOR_ACCEPTANCE = 2.0

# 로그 파일
LOG_FILE = project_root / "logs" / "application.log"
ERROR_LOG_FILE = project_root / "logs" / "phase25_0_error_log.txt"

# 리포트 파일
REPORT_MD = project_root / "docs" / "PHASE25" / "PHASE25-0_LONG_RUN_PAPER_REPORT.md"
SUMMARY_JSON = project_root / "logs" / "phase25_0_long_run_summary.json"

# 모니터링 설정
MONITOR_INTERVAL_SEC = 30  # 로그 체크 주기 (30초)
# 치명적 에러만 감지 (텔레그램 전송 실패는 제외)
ERROR_PATTERNS = ["[CRITICAL]", "EXCEPTION"]

# ============================================================================
# 유틸리티 함수
# ============================================================================

def print_section(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step_num: int, step_name: str):
    """스텝 헤더 출력"""
    print(f"\n[STEP {step_num}] {step_name}")
    print("-" * 80)


def safe_print(msg: str, level: str = "INFO"):
    """안전한 출력 (UTF-8 인코딩 고려)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO": "  [INFO]",
        "WARN": "  [WARN]",
        "ERROR": "  [ERROR]",
        "OK": "  [✓]",
        "FAIL": "  [✗]"
    }.get(level, "  [INFO]")
    
    print(f"{prefix} {msg}")


# ============================================================================
# STEP 1: 환경 정리 - 프로세스 정리 헬퍼
# ============================================================================

def _parse_wmic_output_for_future_alarm_pids(output: str) -> List[int]:
    """wmic 출력에서 future_alarm_bot/run_v2 관련 python PID 목록을 추출한다.

    Args:
        output: wmic process where name='python.exe' get ProcessId,CommandLine /FORMAT:LIST 결과

    Returns:
        List[int]: 종료 대상 PID 목록
    """
    pids: List[int] = []
    current_cmd: str = ""
    current_pid: str = ""

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            # 블록 경계: 현재까지 누적된 항목 평가
            if current_cmd and current_pid:
                lower_cmd = current_cmd.lower()
                if "future_alarm_bot" in lower_cmd or "run_v2.py" in lower_cmd:
                    try:
                        pids.append(int(current_pid))
                    except ValueError:
                        pass
            current_cmd = ""
            current_pid = ""
            continue

        if line.startswith("CommandLine="):
            current_cmd = line[len("CommandLine="):]
        elif line.startswith("ProcessId="):
            current_pid = line[len("ProcessId="):]

    # 마지막 블록 처리
    if current_cmd and current_pid:
        lower_cmd = current_cmd.lower()
        if "future_alarm_bot" in lower_cmd or "run_v2.py" in lower_cmd:
            try:
                pids.append(int(current_pid))
            except ValueError:
                pass

    return pids


def _find_future_alarm_python_pids() -> List[int]:
    """현재 실행 중인 future_alarm_bot 관련 python PID를 조회한다.

    Returns:
        List[int]: 종료 대상 PID 목록 (없으면 빈 리스트)
    """
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                "name='python.exe'",
                "get",
                "ProcessId,CommandLine",
                "/FORMAT:LIST",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except FileNotFoundError:
        # 일부 환경에서 wmic 미존재
        safe_print("wmic 명령을 찾을 수 없어 프로세스 자동 정리를 건너뜁니다", "WARN")
        return []
    except Exception as e:  # pragma: no cover - 방어적 코드
        safe_print(f"wmic 호출 중 예외 발생: {e}", "WARN")
        return []

    return _parse_wmic_output_for_future_alarm_pids(result.stdout or "")


def _terminate_process(pid: int) -> None:
    """단일 프로세스를 안전하게 종료한다 (Windows 전용 taskkill)."""
    try:
        subprocess.run([
            "taskkill",
            "/PID",
            str(pid),
            "/T",  # 자식 포함
            "/F",  # 강제 종료
        ], capture_output=True, text=True)
        safe_print(f"종료된 python 프로세스 PID={pid}", "OK")
    except Exception as e:  # pragma: no cover - OS 종속 예외
        safe_print(f"PID={pid} 종료 중 예외 발생: {e}", "WARN")


# ============================================================================
# STEP 1: 환경 정리
# ============================================================================

def cleanup_environment() -> bool:
    """
    환경 정리
    - future_alarm_bot/run_v2 관련 Python 프로세스 자동 정리
    - Docker 상태 확인
    
    Returns:
        bool: 성공 여부
    """
    print_step(1, "환경 정리")
    
    try:
        # 1) future_alarm_bot 관련 python 프로세스 정리
        safe_print("future_alarm_bot 관련 Python 프로세스 정리 중...")
        pids = _find_future_alarm_python_pids()
        
        if not pids:
            safe_print("종료할 future_alarm_bot Python 프로세스 없음", "OK")
        else:
            safe_print(f"종료 대상 프로세스 수: {len(pids)}", "WARN")
            for pid in pids:
                _terminate_process(pid)
        
        # 2) Docker 상태 확인 (기존 로직 유지)
        safe_print("Docker 컨테이너 상태 확인 중...")
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        containers = result.stdout.strip().split("\n") if result.stdout.strip() else []
        required = ["trading_db_postgres", "trading_redis"]
        
        for container in required:
            if container in containers:
                safe_print(f"Docker 컨테이너 '{container}' 실행 중", "OK")
            else:
                safe_print(f"Docker 컨테이너 '{container}' 없음", "FAIL")
                safe_print("Docker Compose를 실행해주세요: docker-compose up -d", "ERROR")
                return False
        
        return True
    
    except Exception as e:
        safe_print(f"환경 정리 실패: {e}", "ERROR")
        return False


# ============================================================================
# STEP 2: Pre-flight Check
# ============================================================================

def run_preflight_checks(config_path: str) -> bool:
    """
    Pre-flight Check 실행
    - env_config_validator.py (특정 config만 검증)
    - phase24_1_infra_diagnostics.py
    
    Args:
        config_path: 사용할 config 파일 경로
    
    Returns:
        bool: 모든 체크 PASS 여부
    """
    print_step(2, "Pre-flight Check")
    
    # 1. Env & Config Validator (특정 config만 검증)
    safe_print("환경변수 & Config 검증 중...")
    validator_path = project_root / "scripts" / "infra" / "env_config_validator.py"
    
    result = subprocess.run(
        [sys.executable, str(validator_path), "--config", config_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        safe_print("환경변수/Config 검증 실패", "FAIL")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        safe_print("환경변수/Config 검증 완료", "OK")
    
    # 2. Infra Diagnostics
    safe_print("인프라 진단 중 (DB/Redis/Engine)...")
    diagnostics_path = project_root / "scripts" / "infra" / "phase24_1_infra_diagnostics.py"
    
    result = subprocess.run(
        [sys.executable, str(diagnostics_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        safe_print("인프라 진단 실패", "FAIL")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        safe_print("인프라 진단 완료", "OK")
    
    return True


# ============================================================================
# STEP 3: Clean State
# ============================================================================

def run_clean_state() -> bool:
    """
    Clean State 실행
    - clean_state_complete.py
    
    Returns:
        bool: 성공 여부
    """
    print_step(3, "Clean State (DB/Redis 정리)")
    
    safe_print("DB/Redis 상태 초기화 중...")
    clean_state_path = project_root / "scripts" / "clean_state_complete.py"
    
    result = subprocess.run(
        [sys.executable, str(clean_state_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        safe_print("Clean State 실패", "FAIL")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        safe_print("Clean State 완료", "OK")
        return True


# ============================================================================
# STEP 4: Long-run 실행
# ============================================================================

def start_long_run(config_path: str, duration_hours: float, tag: str = None) -> subprocess.Popen:
    """
    Long-run PAPER 실행 (새 CMD 창)
    
    Args:
        config_path: Config 파일 경로
        duration_hours: 실행 시간 (hours)
        tag: Run 태그 (선택)
    
    Returns:
        subprocess.Popen: 실행 중인 프로세스
    """
    print_step(4, f"Long-run PAPER 실행 (Duration: {duration_hours}H)")
    
    # 가상환경 activate 스크립트
    venv_activate = project_root / "trading_bot_env" / "Scripts" / "activate.bat"
    
    # run_v2.py 경로
    run_v2_path = project_root / "scripts" / "run_v2.py"
    
    # 명령어 구성
    cmd = f'cmd /c start "LONG_RUN_PAPER" cmd /k "{venv_activate} && python {run_v2_path} --mode paper --config {config_path} --duration-hours {duration_hours}"'
    
    safe_print(f"Config: {config_path}")
    safe_print(f"Duration: {duration_hours} hours ({duration_hours * 3600} seconds)")
    if tag:
        safe_print(f"Tag: {tag}")
    
    safe_print("새 CMD 창에서 실행 중...")
    safe_print("(로그는 logs/application.log에서 실시간 모니터링됩니다)")
    
    # 프로세스 시작
    process = subprocess.Popen(cmd, shell=True)
    
    # 프로세스 시작 대기 (로그 파일 생성 대기)
    time.sleep(5)
    
    safe_print(f"프로세스 시작됨 (PID: {process.pid})", "OK")
    
    return process


# ============================================================================
# STEP 5: 실시간 모니터링
# ============================================================================

def monitor_logs(target_duration_sec: float, start_time: datetime) -> Dict:
    """
    실시간 로그 모니터링
    
    Args:
        target_duration_sec: 목표 duration (초)
        start_time: 실행 시작 시각
    
    Returns:
        dict: {
            'status': 'PASS' | 'FAIL',
            'error_lines': [...],
            'last_200_lines': [...],
            'actual_duration_sec': float
        }
    """
    print_step(5, "실시간 로그 모니터링")
    
    safe_print(f"목표 Duration: {target_duration_sec / 3600:.2f}H ({target_duration_sec:.0f}초)")
    safe_print(f"모니터링 주기: {MONITOR_INTERVAL_SEC}초")
    safe_print(f"로그 파일: {LOG_FILE}")
    
    error_lines = []
    last_200_lines = []
    
    # 로그 파일이 없으면 생성 대기
    retry_count = 0
    while not LOG_FILE.exists() and retry_count < 10:
        safe_print("로그 파일 생성 대기 중...", "WARN")
        time.sleep(3)
        retry_count += 1
    
    if not LOG_FILE.exists():
        safe_print("로그 파일이 생성되지 않음", "FAIL")
        return {
            'status': 'FAIL',
            'error_lines': ["로그 파일이 생성되지 않음"],
            'last_200_lines': [],
            'actual_duration_sec': 0
        }
    
    # 시작 시점의 로그 파일 위치를 기록 (이전 로그 무시)
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(0, 2)  # 파일 끝으로 이동
            last_position = f.tell()
        safe_print(f"로그 파일 시작 위치: {last_position} bytes (이전 로그 무시)", "OK")
    except Exception as e:
        safe_print(f"로그 파일 위치 확인 실패: {e}", "WARN")
        last_position = 0
    
    # 모니터링 루프
    while True:
        # 1. Wall-clock 체크
        elapsed = (datetime.now() - start_time).total_seconds()
        remaining = target_duration_sec - elapsed
        
        if elapsed >= target_duration_sec:
            # Duration 경과 → 정상 종료 확인
            safe_print(f"Duration 경과 ({elapsed / 3600:.2f}H)", "OK")
            break
        
        # 진행률 표시 (매 30초마다)
        progress = (elapsed / target_duration_sec) * 100
        safe_print(f"진행률: {progress:.1f}% ({elapsed / 3600:.2f}H / {target_duration_sec / 3600:.2f}H) - 남은 시간: {remaining / 60:.1f}분")
        
        # 2. 로그 파일 tail
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                last_position = f.tell()
                
                # 마지막 200줄 유지
                last_200_lines.extend(new_lines)
                if len(last_200_lines) > 200:
                    last_200_lines = last_200_lines[-200:]
                
                # 3. ERROR/CRITICAL 패턴 검색 (텔레그램 제외)
                for line in new_lines:
                    # 텔레그램 전송 실패는 무시
                    if "텔레그램 전송 실패" in line or "telegram" in line.lower():
                        continue
                    
                    for pattern in ERROR_PATTERNS:
                        if pattern in line.upper():
                            error_lines.append(line.strip())
                            safe_print(f"치명적 패턴 감지: {pattern}", "FAIL")
                            safe_print(f"Line: {line.strip()}")
                            
                            # 즉시 중단
                            safe_print("Long-run 중단 (ERROR 감지)", "FAIL")
                            
                            # 에러 로그 저장
                            with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as ef:
                                ef.write(f"ERROR 감지 시각: {datetime.now()}\n")
                                ef.write(f"경과 시간: {elapsed / 3600:.2f}H\n\n")
                                ef.write("=" * 80 + "\n")
                                ef.write("마지막 200줄:\n")
                                ef.write("=" * 80 + "\n")
                                ef.writelines(last_200_lines)
                            
                            safe_print(f"에러 로그 저장: {ERROR_LOG_FILE}", "OK")
                            
                            return {
                                'status': 'FAIL',
                                'error_lines': error_lines,
                                'last_200_lines': last_200_lines,
                                'actual_duration_sec': elapsed
                            }
        
        except Exception as e:
            safe_print(f"로그 읽기 오류: {e}", "WARN")
        
        # 4. 대기
        time.sleep(MONITOR_INTERVAL_SEC)
    
    # 정상 종료
    actual_duration = (datetime.now() - start_time).total_seconds()
    safe_print(f"실제 Duration: {actual_duration / 3600:.2f}H ({actual_duration:.0f}초)", "OK")
    
    return {
        'status': 'PASS',
        'error_lines': error_lines,
        'last_200_lines': last_200_lines,
        'actual_duration_sec': actual_duration
    }


# ============================================================================
# STEP 6: Post-run 분석
# ============================================================================

def analyze_results(start_time: datetime, end_time: datetime) -> Dict:
    """
    Post-run 메트릭 수집
    
    Args:
        start_time: 실행 시작 시각
        end_time: 실행 종료 시각
    
    Returns:
        dict: {
            'db_metrics': {...},
            'log_metrics': {...},
            'duration_metrics': {...}
        }
    """
    print_step(6, "Post-run 분석")
    
    metrics = {
        'db_metrics': {},
        'log_metrics': {},
        'duration_metrics': {}
    }
    
    # 1. DB 메트릭
    safe_print("DB 메트릭 수집 중...")
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5433')),
            database=os.getenv('DB_NAME', 'trading_db'),
            user=os.getenv('DB_USER', 'trading_user'),
            password=os.getenv('DB_PASSWORD', 'trading_pw_2024')
        )
        
        with conn.cursor() as cur:
            # Time range 기반 trades 필터
            cur.execute(
                """
                SELECT COUNT(*) FROM trading.trades
                WHERE ts_open >= %s AND ts_open <= %s;
                """,
                (start_time, end_time)
            )
            trade_count = cur.fetchone()[0]
            
            # Entry/Exit 구분 (side 기반)
            cur.execute(
                """
                SELECT side, COUNT(*) FROM trading.trades
                WHERE ts_open >= %s AND ts_open <= %s
                GROUP BY side;
                """,
                (start_time, end_time)
            )
            side_counts = dict(cur.fetchall())
            
            # 활성 포지션 (ts_close가 NULL)
            cur.execute(
                """
                SELECT COUNT(*) FROM trading.trades
                WHERE ts_open >= %s AND ts_close IS NULL;
                """,
                (start_time,)
            )
            active_positions = cur.fetchone()[0]
        
        conn.close()
        
        metrics['db_metrics'] = {
            'trade_count': trade_count,
            'entry_count': side_counts.get('LONG', 0) + side_counts.get('SHORT', 0),
            'exit_count': trade_count - active_positions,  # 근사치
            'active_positions': active_positions,
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
        }
        
        safe_print(f"Trade 수: {trade_count}", "OK")
        safe_print(f"활성 포지션: {active_positions}", "OK")
    
    except Exception as e:
        safe_print(f"DB 메트릭 수집 실패: {e}", "ERROR")
        metrics['db_metrics'] = {'error': str(e)}
    
    # 2. 로그 메트릭 (시작 시점 이후만)
    safe_print("로그 메트릭 수집 중...")
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            
            # 시작 시점 이후 로그만 필터링
            # 로그 형식: "2025-12-02 20:21:10,860 [INFO] ..."
            start_timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
            filtered_lines = []
            for line in all_lines:
                if len(line) < 19:
                    continue
                try:
                    # 로그 라인의 타임스탬프 추출 (첫 19글자: "YYYY-MM-DD HH:MM:SS")
                    log_timestamp = line[:19]
                    if log_timestamp >= start_timestamp:
                        filtered_lines.append(line)
                except:
                    continue
            lines = filtered_lines
            
            # Ensemble V2 aggregate 카운트
            aggregate_count = sum(1 for line in lines if "Ensemble V2" in line or "aggregate" in line.lower())
            
            # Tier 카운트
            tier1_count = sum(1 for line in lines if "Tier1" in line or "HIGH_CONFIDENCE" in line)
            tier2_count = sum(1 for line in lines if "Tier2" in line or "CONSENSUS" in line)
            skip_count = sum(1 for line in lines if "Skip" in line or "SKIP" in line)
            
            # ERROR/CRITICAL 카운트 (텔레그램 제외)
            error_count = sum(
                1 for line in lines 
                if "ERROR" in line.upper() and "텔레그램" not in line and "telegram" not in line.lower()
            )
            critical_count = sum(1 for line in lines if "CRITICAL" in line.upper())
            
            metrics['log_metrics'] = {
                'ensemble_aggregate_count': aggregate_count,
                'tier1_count': tier1_count,
                'tier2_count': tier2_count,
                'skip_count': skip_count,
                'error_count': error_count,
                'critical_count': critical_count
            }
            
            safe_print(f"Ensemble Aggregate: {aggregate_count}회", "OK")
            safe_print(f"ERROR: {error_count}건, CRITICAL: {critical_count}건", "OK" if error_count == 0 and critical_count == 0 else "FAIL")
        else:
            safe_print("로그 파일 없음", "WARN")
            metrics['log_metrics'] = {'error': '로그 파일 없음'}
    
    except Exception as e:
        safe_print(f"로그 메트릭 수집 실패: {e}", "ERROR")
        metrics['log_metrics'] = {'error': str(e)}
    
    # 3. Duration 메트릭
    actual_duration_sec = (end_time - start_time).total_seconds()
    metrics['duration_metrics'] = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'actual_duration_sec': actual_duration_sec,
        'actual_duration_hours': actual_duration_sec / 3600
    }
    
    safe_print(f"실제 Duration: {actual_duration_sec / 3600:.2f}H", "OK")
    
    return metrics


# ============================================================================
# STEP 7: 결과 저장
# ============================================================================

def save_report(metrics: Dict, config_path: str, duration_hours: float, monitor_result: Dict):
    """
    MD 리포트 + JSON 요약 저장
    
    Args:
        metrics: 분석 메트릭
        config_path: Config 파일 경로
        duration_hours: 목표 duration
        monitor_result: 모니터링 결과
    """
    print_step(7, "결과 저장")
    
    # 1. JSON 요약 저장
    safe_print(f"JSON 요약 저장: {SUMMARY_JSON}")
    
    log_metrics = metrics.get('log_metrics', {}) or {}
    error_count = log_metrics.get('error_count', 0)
    critical_count = log_metrics.get('critical_count', 0)
    ensemble_agg = log_metrics.get('ensemble_aggregate_count', 0)
    trade_count = metrics.get('db_metrics', {}).get('trade_count', 0)
    active_positions = metrics.get('db_metrics', {}).get('active_positions', 999)

    # Infra-critical Acceptance (PHASE25-0 PASS 기준)
    duration_pass = monitor_result['actual_duration_sec'] >= (duration_hours * 3600 * 0.98)
    error_pass_infra = (monitor_result['status'] == 'PASS' and critical_count == 0)
    active_positions_pass = (active_positions == 0)
    ensemble_pass = (ensemble_agg >= 1000)
    
    # Strategy KPI (경고/참고용)
    trade_target = 50
    trade_warning = (trade_count < trade_target)
    
    # 최종 인프라 Acceptance
    infra_pass = all([duration_pass, error_pass_infra, active_positions_pass, ensemble_pass])
    
    # 전체 상태
    if infra_pass and not trade_warning:
        overall_status = "PASS"
    elif infra_pass and trade_warning:
        overall_status = "PASS_WITH_STRATEGY_WARNING"
    else:
        overall_status = "FAIL"

    summary = {
        'timestamp': datetime.now().isoformat(),
        'config': config_path,
        'target_duration_hours': duration_hours,
        'monitor_result': monitor_result,
        'metrics': metrics,
        'acceptance': {
            # Infra-critical (PHASE25-0 PASS 기준)
            'infra': {
                'duration_pass': duration_pass,
                'error_pass_infra': error_pass_infra,
                'active_positions_pass': active_positions_pass,
                'ensemble_pass': ensemble_pass,
                'overall': infra_pass
            },
            # Strategy KPI (경고/참고용)
            'strategy': {
                'trade_count': trade_count,
                'trade_target': trade_target,
                'trade_warning': trade_warning
            },
            # 최종 상태
            'overall_status': overall_status,
            'infra_pass': infra_pass,
            'strategy_warning': trade_warning
        }
    }
    
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    safe_print("JSON 저장 완료", "OK")
    
    # 2. MD 리포트 저장
    safe_print(f"MD 리포트 저장: {REPORT_MD}")
    
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write(f"# PHASE25-0: Long-run PAPER Regression - 실행 리포트\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")

        overall_status = summary['acceptance']['overall_status']
        infra_pass = summary['acceptance']['infra_pass']
        f.write(f"**Status**: {overall_status}  \n")
        f.write(f"**Infra Acceptance**: {'✅ PASS' if infra_pass else '❌ FAIL'}  \n")
        f.write(f"**Config**: `{config_path}`  \n")
        f.write(f"**Duration**: {duration_hours}H (목표), {monitor_result['actual_duration_sec'] / 3600:.2f}H (실제)  \n\n")
        
        f.write("---\n\n")
        f.write("## 1. Executive Summary\n\n")
        f.write(f"- **실행 시작**: {metrics['duration_metrics']['start_time']}\n")
        f.write(f"- **실행 종료**: {metrics['duration_metrics']['end_time']}\n")
        f.write(f"- **Duration**: {metrics['duration_metrics']['actual_duration_hours']:.2f}H ({metrics['duration_metrics']['actual_duration_sec']:.0f}초)\n")
        f.write(f"- **Trade 수**: {trade_count} (목표: {trade_target})\n")
        f.write(f"- **활성 포지션**: {active_positions}\n")
        f.write(f"- **ERROR/CRITICAL**: {error_count} / {critical_count}\n")
        f.write(f"- **Ensemble Aggregate**: {ensemble_agg}\n")
        f.write(f"- **인프라 Acceptance**: {'✅ PASS' if infra_pass else '❌ FAIL'}\n")
        f.write(f"- **전략 KPI**: {'⚠️ WARNING (Trade 수 부족)' if trade_warning else '✅ OK'}\n")
        f.write(f"- **최종 판정**: {overall_status}\n\n")
        
        f.write("---\n\n")
        f.write("## 2. Acceptance Criteria\n\n")
        
        f.write("### 2.1 인프라 Acceptance (PHASE25-0 PASS 기준)\n\n")
        f.write("| 항목 | 조건 | 결과 | 판정 |\n")
        f.write("|------|------|------|------|\n")
        f.write(f"| Duration | ≥ {duration_hours * 0.98:.2f}H | {metrics['duration_metrics']['actual_duration_hours']:.2f}H | {'✅' if duration_pass else '❌'} |\n")
        f.write(f"| CRITICAL 오류 | = 0 | {critical_count} | {'✅' if error_pass_infra else '❌'} |\n")
        f.write(f"| 활성 포지션 | = 0 | {active_positions} | {'✅' if active_positions_pass else '❌'} |\n")
        f.write(f"| Ensemble Aggregate | ≥ 1000 | {ensemble_agg} | {'✅' if ensemble_pass else '❌'} |\n")
        f.write(f"| **인프라 종합** | - | - | {'✅ PASS' if infra_pass else '❌ FAIL'} |\n\n")
        
        f.write("### 2.2 전략 KPI (경고/참고용)\n\n")
        f.write("| 항목 | 목표 | 결과 | 상태 |\n")
        f.write("|------|------|------|------|\n")
        f.write(f"| Trade 수 | ≥ {trade_target} | {trade_count} | {'⚠️ WARNING' if trade_warning else '✅ OK'} |\n\n")
        
        f.write("**NOTE**: Trade 수는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, PHASE25-0 인프라 Acceptance 기준에는 포함되지 않습니다. 전략 KPI는 이후 PHASE에서 다룹니다.\n\n")
        
        f.write("---\n\n")
        f.write("## 3. 메트릭 상세\n\n")
        f.write("### 3.1 DB 메트릭\n")
        f.write(f"```json\n{json.dumps(metrics.get('db_metrics', {}), indent=2, ensure_ascii=False)}\n```\n\n")
        f.write("### 3.2 로그 메트릭\n")
        f.write(f"```json\n{json.dumps(metrics.get('log_metrics', {}), indent=2, ensure_ascii=False)}\n```\n\n")
        f.write("### 3.3 Duration 메트릭\n")
        f.write(f"```json\n{json.dumps(metrics.get('duration_metrics', {}), indent=2, ensure_ascii=False)}\n```\n\n")
        
        f.write("---\n\n")
        f.write("## 4. 모니터링 결과\n\n")
        f.write(f"- **상태**: {monitor_result['status']}\n")
        f.write(f"- **ERROR 라인 수**: {len(monitor_result['error_lines'])}\n\n")
        
        if monitor_result['error_lines']:
            f.write("### ERROR 라인 샘플:\n")
            f.write("```\n")
            for line in monitor_result['error_lines'][:10]:  # 최대 10줄만
                f.write(f"{line}\n")
            f.write("```\n\n")
        
        f.write("---\n\n")
        f.write("## 5. 최종 판정\n\n")
        
        if overall_status == "PASS":
            f.write("✅ **PASS** - 인프라 Acceptance 충족 & 전략 KPI 양호\n\n")
            f.write("PHASE25-0 완료 조건을 모두 만족했습니다. Long-run PAPER Harness가 정상적으로 작동하며, 2H 이상 안정적으로 실행되었습니다.\n")
        elif overall_status == "PASS_WITH_STRATEGY_WARNING":
            f.write("✅ **INFRA PASS (전략 KPI 경고)** - 인프라 Acceptance 충족\n\n")
            f.write("**인프라 Acceptance**: ✅ PASS\n")
            f.write(f"- Duration: {metrics['duration_metrics']['actual_duration_hours']:.2f}H ≥ {duration_hours * 0.98:.2f}H\n")
            f.write(f"- CRITICAL 오류: {critical_count}건 (모니터링 {monitor_result['status']})\n")
            f.write(f"- 활성 포지션: {active_positions}\n")
            f.write(f"- Ensemble Aggregate: {ensemble_agg} ≥ 1000\n\n")
            f.write("**전략 KPI**: ⚠️ WARNING\n")
            f.write(f"- Trade 수: {trade_count} < 목표 {trade_target}건\n")
            f.write("- 이는 전략/스캘핑/앙상블 파라미터 튜닝 영역이며, 이후 PHASE에서 다룹니다.\n\n")
            f.write("**결론**: PHASE25-0는 인프라 기준으로 PASS. Long-run PAPER Harness가 안정적으로 작동하며, 장시간 실행 인프라가 확립되었습니다.\n")
        else:
            f.write("❌ **FAIL** - 인프라 Acceptance 미충족\n\n")
            infra_result = summary['acceptance']['infra']
            failed_infra = [k for k, v in infra_result.items() if k != 'overall' and not v]
            f.write(f"실패한 인프라 조건: {', '.join(failed_infra)}\n\n")
            f.write("재실행 또는 코드 수정이 필요합니다.\n")
    
    safe_print("MD 리포트 저장 완료", "OK")

    return summary


# ============================================================================
# 메인 함수
# ============================================================================

def main():
    """메인 진입점"""
    print_section("PHASE25-0: Long-run PAPER Regression Harness")
    
    # CLI 파싱
    parser = argparse.ArgumentParser(
        description='PHASE25-0: Long-run PAPER Regression Harness (2H+ 최소)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--config', type=str, required=True,
                        help='PAPER config 파일 경로')
    parser.add_argument('--duration-hours', type=float, default=DEFAULT_DURATION_HOURS,
                        help=f'실행 시간 (hours, 기본: {DEFAULT_DURATION_HOURS}, Acceptance 최소: {MIN_DURATION_FOR_ACCEPTANCE})')
    parser.add_argument('--tag', type=str, default=None,
                        help='Run 태그 (선택)')
    
    args = parser.parse_args()
    
    # Duration 경고
    if args.duration_hours < MIN_DURATION_FOR_ACCEPTANCE:
        safe_print(f"경고: Duration {args.duration_hours}H는 Acceptance 최소값({MIN_DURATION_FOR_ACCEPTANCE}H) 미만입니다", "WARN")
        safe_print("이 실행은 개발/테스트용이며, PHASE25-0 Acceptance로는 인정되지 않습니다", "WARN")
    
    safe_print(f"Config: {args.config}")
    safe_print(f"Duration: {args.duration_hours}H")
    if args.tag:
        safe_print(f"Tag: {args.tag}")
    
    # STEP 1: 환경 정리
    if not cleanup_environment():
        safe_print("환경 정리 실패 - 중단", "FAIL")
        return 1
    
    # STEP 2: Pre-flight Check
    if not run_preflight_checks(args.config):
        safe_print("Pre-flight Check 실패 - 중단", "FAIL")
        return 1
    
    # STEP 3: Clean State
    if not run_clean_state():
        safe_print("Clean State 실패 - 중단", "FAIL")
        return 1
    
    # STEP 4: Long-run 실행
    start_time = datetime.now()
    process = start_long_run(args.config, args.duration_hours, args.tag)
    
    # STEP 5: 실시간 모니터링
    target_duration_sec = args.duration_hours * 3600
    monitor_result = monitor_logs(target_duration_sec, start_time)
    
    end_time = datetime.now()
    
    # STEP 6: Post-run 분석
    metrics = analyze_results(start_time, end_time)
    
    # STEP 7: 결과 저장
    summary = save_report(metrics, args.config, args.duration_hours, monitor_result)
    
    # 최종 판정 (모든 Acceptance 플래그 기준)
    print_section("최종 결과")
    all_pass = all(summary['acceptance'].values())
    
    if all_pass:
        safe_print("Long-run PAPER Acceptance PASS", "OK")
        safe_print(f"리포트: {REPORT_MD}", "OK")
        safe_print(f"JSON 요약: {SUMMARY_JSON}", "OK")
        return 0
    else:
        safe_print("Long-run PAPER Acceptance FAIL", "FAIL")
        safe_print(f"에러 로그: {ERROR_LOG_FILE}", "WARN")
        safe_print(f"리포트: {REPORT_MD}", "OK")
        return 1


if __name__ == "__main__":
    sys.exit(main())
