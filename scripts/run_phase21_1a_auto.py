#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE21-1A: Automated Single Strategy Smoke Tests
==================================================
7개 전략을 순차적으로 1시간씩 테스트 (Ensemble OFF)
각 테스트마다:
- Clean-State 초기화
- CMD 새 창에서 실행
- 초반 5분간 초단위 모니터링
- 로그 파일 PermissionError 방지 (고유 파일명)
"""
import os
import sys
import time
import subprocess
import psycopg2
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 전략 목록
STRATEGIES = [
    "scalping",
    "breakout",
    "reversion",
    "trend",
    "swing",
    "swing_bb",
    "daytrade",
]

# DB 설정
DB_HOST = "localhost"
DB_PORT = 5433
DB_NAME = "trading_db"
DB_USER = "trading_user"
DB_PASSWORD = "trading_pw_2024"


def clean_state():
    """Clean-State 초기화"""
    print("\n" + "="*60)
    print("Clean-State 초기화 중...")
    print("="*60)
    
    # 환경변수 설정
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run(
        [r".\trading_bot_env\Scripts\python.exe", "scripts/phase20_clean_state.py"],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    
    # 출력 (인코딩 안전하게)
    try:
        print(result.stdout)
    except UnicodeEncodeError:
        print("[출력 생략 - 인코딩 오류]")
    
    if result.returncode != 0:
        print(f"Clean-State 반환 코드: {result.returncode}")
        if result.stderr:
            try:
                print(f"stderr: {result.stderr}")
            except UnicodeEncodeError:
                print("[stderr 생략 - 인코딩 오류]")
        return False
    return True


def get_trade_count():
    """현재 거래 수 확인"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trading.trades")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"⚠️ DB 조회 실패: {e}")
        return -1


def run_strategy_test(strategy_name):
    """단일 전략 테스트 실행"""
    print("\n" + "="*60)
    print(f"🚀 {strategy_name.upper()} 테스트 시작")
    print("="*60)
    
    # 1. Clean-State
    if not clean_state():
        print(f"❌ {strategy_name}: Clean-State 실패")
        return {"status": "FAIL", "reason": "Clean-State Failed"}
    
    initial_trades = get_trade_count()
    print(f"📊 초기 거래 수: {initial_trades}")
    
    # 2. 로그 파일명 설정 (고유)
    log_file = f"logs/phase21_1a_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 3. CMD 새 창에서 실행
    config_path = f"configs/paper/phase21_{strategy_name}_solo.yml"
    cmd = f'start "PHASE21-{strategy_name}" cmd /k ".\\trading_bot_env\\Scripts\\activate && python scripts/run_paper.py --config {config_path} 2>&1 | tee {log_file}"'
    
    print(f"📝 실행 명령: {cmd}")
    print(f"📁 로그 파일: {log_file}")
    
    # CMD 새 창 실행
    subprocess.Popen(cmd, shell=True, cwd=project_root)
    
    # 4. 초반 5분간 초단위 모니터링
    print("\n🔍 초반 5분간 초단위 모니터링 시작...")
    start_time = time.time()
    monitor_duration = 300  # 5분
    check_interval = 1  # 1초
    
    last_trade_count = initial_trades
    error_detected = False
    
    while (time.time() - start_time) < monitor_duration:
        time.sleep(check_interval)
        elapsed = int(time.time() - start_time)
        
        # 로그 파일 체크 (존재하면)
        if Path(log_file).exists():
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # 최근 10줄 체크
                    recent_lines = lines[-10:] if len(lines) > 10 else lines
                    for line in recent_lines:
                        # 에러 감지
                        if "ERROR" in line or "CRITICAL" in line or "Traceback" in line or "PermissionError" in line:
                            print(f"\n❌ [{elapsed}s] 에러 감지: {line.strip()}")
                            error_detected = True
                            break
                
                if error_detected:
                    break
                    
            except Exception as e:
                pass  # 로그 파일 읽기 실패는 무시
        
        # 거래 수 체크
        current_trades = get_trade_count()
        if current_trades > last_trade_count:
            print(f"✅ [{elapsed}s] 거래 감지: {current_trades} (증가: +{current_trades - last_trade_count})")
            last_trade_count = current_trades
        
        # 1분마다 상태 출력
        if elapsed % 60 == 0:
            print(f"⏱️ [{elapsed}s] 모니터링 중... (거래: {current_trades})")
    
    if error_detected:
        print(f"\n❌ {strategy_name}: 초반 모니터링 중 에러 감지. 프로세스 종료 필요.")
        # Python 프로세스 종료
        subprocess.run("taskkill /F /FI \"WINDOWTITLE eq PHASE21-*\" /T", shell=True, capture_output=True)
        return {"status": "FAIL", "reason": "Error Detected in First 5 Minutes"}
    
    print(f"\n✅ 초반 5분 모니터링 완료. 나머지 55분 대기 중...")
    
    # 5. 나머지 55분 대기 (1시간 총)
    remaining_time = 3600 - monitor_duration
    print(f"⏳ {remaining_time}초 대기 중... (15분마다 체크)")
    
    check_interval_long = 900  # 15분
    checks = int(remaining_time / check_interval_long)
    
    for i in range(checks):
        time.sleep(check_interval_long)
        current_trades = get_trade_count()
        elapsed_total = int(time.time() - start_time)
        print(f"⏱️ [{elapsed_total}s / 3600s] 진행 중... (거래: {current_trades})")
    
    # 남은 시간 대기
    final_wait = remaining_time - (checks * check_interval_long)
    if final_wait > 0:
        time.sleep(final_wait)
    
    # 6. 최종 결과 확인
    final_trades = get_trade_count()
    trades_generated = final_trades - initial_trades
    
    print("\n" + "="*60)
    print(f"✅ {strategy_name.upper()} 테스트 완료")
    print(f"📊 초기 거래: {initial_trades}")
    print(f"📊 최종 거래: {final_trades}")
    print(f"📊 생성된 거래: {trades_generated}")
    print("="*60)
    
    # 프로세스 종료
    subprocess.run("taskkill /F /FI \"WINDOWTITLE eq PHASE21-*\" /T", shell=True, capture_output=True)
    time.sleep(2)
    
    return {
        "status": "PASS" if trades_generated > 0 else "WARN",
        "initial_trades": initial_trades,
        "final_trades": final_trades,
        "trades_generated": trades_generated,
        "log_file": log_file
    }


def safe_print(msg):
    """안전한 출력 (인코딩 오류 방지)"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # ASCII만 출력
        print(msg.encode('ascii', 'replace').decode('ascii'))


def main():
    """메인 실행"""
    safe_print("\n" + "="*60)
    safe_print("PHASE21-1A: Single Strategy Smoke Tests (7 Strategies)")
    safe_print("="*60)
    safe_print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    safe_print(f"Strategies: {', '.join(STRATEGIES)}")
    safe_print(f"Runtime per strategy: 1 hour")
    safe_print(f"Total estimated time: {len(STRATEGIES)} hours")
    safe_print("="*60)
    
    results = {}
    
    for idx, strategy in enumerate(STRATEGIES, 1):
        print(f"\n{'='*60}")
        print(f"진행: {idx}/{len(STRATEGIES)} - {strategy.upper()}")
        print(f"{'='*60}")
        
        result = run_strategy_test(strategy)
        results[strategy] = result
        
        print(f"\n📋 {strategy} 결과: {result['status']}")
        if result['status'] == "FAIL":
            print(f"⚠️ 실패 이유: {result.get('reason', 'Unknown')}")
            # 실패 시 계속 진행할지 여부 (일단 계속 진행)
            print("⏭️ 다음 전략으로 계속 진행...")
        
        # 다음 전략 전 대기
        if idx < len(STRATEGIES):
            print("\n⏳ 다음 전략 시작 전 10초 대기...")
            time.sleep(10)
    
    # 최종 요약
    print("\n" + "="*60)
    print("🎉 PHASE21-1A 전체 테스트 완료!")
    print("="*60)
    print(f"완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📊 전략별 결과:")
    for strategy, result in results.items():
        status_icon = "✅" if result['status'] == "PASS" else ("⚠️" if result['status'] == "WARN" else "❌")
        print(f"  {status_icon} {strategy.upper()}: {result['status']}")
        if 'trades_generated' in result:
            print(f"      거래 생성: {result['trades_generated']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
        subprocess.run("taskkill /F /FI \"WINDOWTITLE eq PHASE21-*\" /T", shell=True, capture_output=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        subprocess.run("taskkill /F /FI \"WINDOWTITLE eq PHASE21-*\" /T", shell=True, capture_output=True)
        sys.exit(1)
