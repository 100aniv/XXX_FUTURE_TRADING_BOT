#!/usr/bin/env python3
"""
PHASE17 V6.1 12H Acceptance 모니터링 스크립트

주기적으로 로그를 파싱하여 통계를 수집하고 체크포인트 리포트 생성
"""
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
import json

LOG_FILE = Path("logs/application.log")
CHECKPOINT_FILE = Path("docs/PHASE17/checkpoints_12h_acceptance.json")
START_TIME_FILE = Path("temp_start_time.txt")

def parse_logs():
    """로그 파일 파싱하여 통계 추출"""
    if not LOG_FILE.exists():
        return None
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        stats = {
            'entry_success': len(re.findall(r'ENTRY.*SUCCESS|ENTRY OPEN', content)),
            'entry_reduced': len(re.findall(r'ENTRY.*REDUCED', content)),
            'budget_cap': len(re.findall(r'Budget Cap', content)),
            'portfolio_block': len(re.findall(r'portfolio_check_failed', content)),
            'volume_guard_block': len(re.findall(r'volume_guard.*block|Volume Guard.*BLOCK', content, re.IGNORECASE)),
            'exposure_guard_block': len(re.findall(r'exposure.*block|Exposure Guard.*BLOCK', content, re.IGNORECASE)),
            'cooldown_block': len(re.findall(r'cooldown.*block|Cooldown.*BLOCK', content, re.IGNORECASE)),
            'exit_fill': len(re.findall(r'EXIT.*FILL', content)),
            'errors': len(re.findall(r'ERROR(?!.*텔레그램)', content)),
            'criticals': len(re.findall(r'CRITICAL', content)),
            'log_size_kb': LOG_FILE.stat().st_size / 1024
        }
        
        # Equity 추출 (최근 로그에서)
        equity_matches = re.findall(r'Equity[:\s]+\$?([\d,]+)', content)
        if equity_matches:
            try:
                stats['equity'] = float(equity_matches[-1].replace(',', ''))
            except:
                stats['equity'] = None
        else:
            stats['equity'] = None
        
        # Block Rate 계산
        total_attempts = stats['entry_success'] + stats['entry_reduced'] + stats['portfolio_block']
        if total_attempts > 0:
            stats['block_rate_pct'] = round(stats['portfolio_block'] / total_attempts * 100, 1)
        else:
            stats['block_rate_pct'] = 0.0
        
        # Budget Cap Rate 계산
        if stats['entry_success'] + stats['entry_reduced'] > 0:
            stats['budget_cap_rate_pct'] = round(stats['budget_cap'] / (stats['entry_success'] + stats['entry_reduced']) * 100, 1)
        else:
            stats['budget_cap_rate_pct'] = 0.0
        
        return stats
    except Exception as e:
        print(f"Error parsing logs: {e}")
        return None

def get_elapsed_time():
    """경과 시간 계산"""
    if not START_TIME_FILE.exists():
        # 로그 파일의 첫 번째 타임스탬프 사용
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', first_line)
                if match:
                    start_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    with open(START_TIME_FILE, 'w') as f2:
                        f2.write(start_time.isoformat())
                    return (datetime.now() - start_time).total_seconds()
        except:
            pass
        return 0
    
    try:
        with open(START_TIME_FILE, 'r') as f:
            start_time = datetime.fromisoformat(f.read().strip())
            return (datetime.now() - start_time).total_seconds()
    except:
        return 0

def save_checkpoint(stats, elapsed_seconds):
    """체크포인트 데이터 저장"""
    checkpoint = {
        'timestamp': datetime.now().isoformat(),
        'elapsed_seconds': elapsed_seconds,
        'elapsed_minutes': round(elapsed_seconds / 60, 1),
        'elapsed_hours': round(elapsed_seconds / 3600, 2),
        'stats': stats
    }
    
    # 기존 체크포인트 로드
    checkpoints = []
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                checkpoints = json.load(f)
        except:
            pass
    
    checkpoints.append(checkpoint)
    
    # 저장
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoints, f, indent=2, ensure_ascii=False)
    
    return checkpoint

def print_checkpoint(checkpoint):
    """체크포인트 출력"""
    stats = checkpoint['stats']
    elapsed = checkpoint['elapsed_hours']
    
    print(f"\n{'='*70}")
    print(f"CHECKPOINT: {elapsed:.2f}H ({checkpoint['elapsed_minutes']:.0f}min)")
    print(f"Time: {checkpoint['timestamp']}")
    print(f"{'='*70}")
    print(f"Entry SUCCESS:       {stats['entry_success']:>5}")
    print(f"Entry REDUCED:       {stats['entry_reduced']:>5}")
    print(f"Exit FILL:           {stats['exit_fill']:>5}")
    print(f"Budget Cap Applied:  {stats['budget_cap']:>5} ({stats['budget_cap_rate_pct']:.1f}%)")
    print(f"Portfolio BLOCK:     {stats['portfolio_block']:>5} ({stats['block_rate_pct']:.1f}%)")
    print(f"  - Volume Guard:    {stats['volume_guard_block']:>5}")
    print(f"  - Exposure Guard:  {stats['exposure_guard_block']:>5}")
    print(f"  - Cooldown:        {stats['cooldown_block']:>5}")
    print(f"Errors:              {stats['errors']:>5}")
    print(f"Criticals:           {stats['criticals']:>5}")
    if stats['equity']:
        print(f"Equity:              ${stats['equity']:>,.0f}")
    print(f"Log Size:            {stats['log_size_kb']:>,.0f} KB")
    print(f"{'='*70}\n")

def monitor_loop():
    """메인 모니터링 루프"""
    print("PHASE17 V6.1 12H Acceptance 모니터링 시작")
    print(f"로그 파일: {LOG_FILE}")
    print(f"체크포인트 파일: {CHECKPOINT_FILE}")
    print(f"시작 시각: {datetime.now()}")
    print("\n체크포인트: 5분 간격")
    
    checkpoint_count = 0
    
    while True:
        time.sleep(300)  # 5분 대기
        
        elapsed = get_elapsed_time()
        if elapsed == 0:
            print("경과 시간 계산 불가, 대기 중...")
            continue
        
        stats = parse_logs()
        if stats is None:
            print("로그 파싱 실패, 대기 중...")
            continue
        
        checkpoint = save_checkpoint(stats, elapsed)
        checkpoint_count += 1
        
        print_checkpoint(checkpoint)
        
        # 12시간 경과 시 종료
        if elapsed >= 12 * 3600:
            print("✅ 12시간 완료!")
            break
        
        # 프로세스 종료 감지
        if stats['log_size_kb'] > 0 and checkpoint_count > 2:
            # 최근 2개 체크포인트에서 로그 크기가 변하지 않으면 종료된 것으로 판단
            try:
                with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                    recent = json.load(f)[-2:]
                    if len(recent) == 2:
                        if recent[0]['stats']['log_size_kb'] == recent[1]['stats']['log_size_kb']:
                            print("⚠️ 프로세스 종료 감지 (로그 크기 변화 없음)")
                            break
            except:
                pass

if __name__ == "__main__":
    try:
        monitor_loop()
    except KeyboardInterrupt:
        print("\n모니터링 중단됨")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
