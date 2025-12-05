#!/usr/bin/env python
"""
PHASE17 REAL PAPER 12H Supervised Execution Script

   :
1.   (Docker/Redis/Logs/Processes)
2. REAL PAPER  ( )
3.     
4.     

:
    python scripts/run_real_paper_12h_supervised.py --duration 12h
    python scripts/run_real_paper_12h_supervised.py --duration 10m --config configs/scalping/real_paper_12h_v6_1_phase17.yml
"""

import argparse
import subprocess
import time
import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

#   
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
LOGS_DIR = PROJECT_ROOT / "logs"
BACKUP_DIR = LOGS_DIR / "backup"
DOCS_DIR = PROJECT_ROOT / "docs" / "PHASE17"


def parse_duration(duration_str):
    """duration    (: '12h'  43200, '10m'  600)"""
    match = re.match(r'^(\d+)([hms])$', duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}. Use format like '12h', '60m', '10m'")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit == 'h':
        return value * 3600
    elif unit == 'm':
        return value * 60
    elif unit == 's':
        return value
    else:
        raise ValueError(f"Unknown unit: {unit}")


def init_environment():
    """  """
    print("\n" + "="*70)
    print("[*] ENVIRONMENT INITIALIZATION")
    print("="*70)
    
    # 1. Docker  
    print("\n[1/5] Checking Docker containers...")
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=trading', '--format', '{{.Names}}: {{.Status}}'],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f" Docker check failed: {e}")
        sys.exit(1)
    
    # 2. Python  
    print("\n[2/5] Terminating existing Python processes...")
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                      capture_output=True, check=False)
        time.sleep(2)
        print(" Python processes terminated")
    except Exception as e:
        print(f" Process termination warning: {e}")
    
    # 3. Redis 
    print("\n[3/5] Flushing Redis...")
    try:
        subprocess.run(
            ['docker', 'exec', 'trading_redis', 'redis-cli', 'FLUSHALL'],
            capture_output=True,
            text=True,
            check=True
        )
        result = subprocess.run(
            ['docker', 'exec', 'trading_redis', 'redis-cli', 'DBSIZE'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f" Redis flushed (DBSIZE={result.stdout.strip()})")
    except subprocess.CalledProcessError as e:
        print(f" Redis flush failed: {e}")
        sys.exit(1)
    
    # 4.  
    print("\n[4/5] Backing up logs...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for log_file in ['application.log', 'trading.log']:
        log_path = LOGS_DIR / log_file
        if log_path.exists():
            backup_path = BACKUP_DIR / f"{log_file.replace('.log', '')}_{timestamp}.log"
            try:
                log_path.rename(backup_path)
                print(f"   Backed up: {log_file}  {backup_path.name}")
            except Exception as e:
                print(f"   Backup warning for {log_file}: {e}")
    
    # 5.    
    print("\n[5/5] Creating fresh log files...")
    for log_file in ['application.log', 'trading.log']:
        log_path = LOGS_DIR / log_file
        log_path.touch()
        print(f"   Created: {log_file}")
    
    print("\n Environment initialized successfully!\n")


def start_paper_trading(config_path):
    """REAL PAPER   ( )"""
    print("="*70)
    print(" STARTING REAL PAPER TRADING")
    print("="*70)
    print(f"Config: {config_path}")
    print(f"Time: {datetime.now()}")
    print()
    
    # venv python  
    venv_python = PROJECT_ROOT / "trading_bot_env" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = sys.executable  # fallback
    
    run_paper_script = PROJECT_ROOT / "scripts" / "run_paper.py"
    
    cmd = [
        str(venv_python),
        str(run_paper_script),
        '--config',
        str(config_path)
    ]
    
    print(f"Command: {' '.join(cmd)}\n")
    
    #   
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(PROJECT_ROOT)
    )
    
    print(f" Process started (PID: {process.pid})\n")
    return process


def monitor_logs(duration_seconds, check_interval=30):
    """    """
    print("="*70)
    print(" MONITORING STARTED")
    print("="*70)
    print(f"Duration: {duration_seconds}s ({duration_seconds/60:.1f}m)")
    print(f"Check Interval: {check_interval}s")
    print()
    
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration_seconds)
    
    stats = {
        'checkpoints': [],
        'entry_success': 0,
        'entry_reduced': 0,
        'entry_block': 0,
        'budget_cap': 0,
        'portfolio_block': 0,
        'errors': 0,
        'last_check_line': 0
    }
    
    app_log_path = LOGS_DIR / "application.log"
    
    checkpoint_count = 0
    
    while datetime.now() < end_time:
        elapsed = (datetime.now() - start_time).total_seconds()
        remaining = (end_time - datetime.now()).total_seconds()
        
        #   
        if app_log_path.exists():
            try:
                with open(app_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[stats['last_check_line']:]
                    stats['last_check_line'] += len(lines)
                    
                    for line in lines:
                        if '[ENTRY SUCCESS]' in line or 'ENTRY OPEN' in line:
                            stats['entry_success'] += 1
                        elif '[ENTRY REDUCED]' in line:
                            stats['entry_reduced'] += 1
                        elif '[ENTRY BLOCK]' in line:
                            stats['entry_block'] += 1
                            if 'portfolio_check_failed' in line:
                                stats['portfolio_block'] += 1
                        elif '[Budget Cap]' in line or 'Budget Cap Applied' in line:
                            stats['budget_cap'] += 1
                        elif 'ERROR' in line or 'Traceback' in line:
                            stats['errors'] += 1
            except Exception as e:
                print(f" Log read error: {e}")
        
        #  
        checkpoint_count += 1
        checkpoint = {
            'time': datetime.now().isoformat(),
            'elapsed_min': round(elapsed / 60, 1),
            'remaining_min': round(remaining / 60, 1),
            'entry_success': stats['entry_success'],
            'entry_reduced': stats['entry_reduced'],
            'entry_block': stats['entry_block'],
            'budget_cap': stats['budget_cap'],
            'portfolio_block': stats['portfolio_block'],
            'errors': stats['errors']
        }
        stats['checkpoints'].append(checkpoint)
        
        #   
        print(f"\n[M{checkpoint['elapsed_min']:.0f}] Checkpoint #{checkpoint_count}")
        print(f"  Time: {checkpoint['time']}")
        print(f"  Progress: {checkpoint['elapsed_min']:.1f}m / {duration_seconds/60:.1f}m")
        print(f"   Entry SUCCESS: {checkpoint['entry_success']}")
        print(f"   Entry REDUCED: {checkpoint['entry_reduced']}")
        print(f"   Entry BLOCK: {checkpoint['entry_block']}")
        print(f"   Budget Cap: {checkpoint['budget_cap']}")
        print(f"   Portfolio BLOCK: {checkpoint['portfolio_block']}")
        print(f"    Errors: {checkpoint['errors']}")
        
        # 
        time.sleep(min(check_interval, remaining))
    
    print("\n Monitoring completed!\n")
    return stats


def generate_report(stats, duration_seconds, config_path, start_time, end_time):
    """  """
    print("="*70)
    print(" GENERATING REPORT")
    print("="*70)
    
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "PHASE17_REAL_PAPER_12H_V6_1_REPORT.md"
    
    #  
    total_entries = stats['entry_success'] + stats['entry_reduced']
    block_rate = (stats['portfolio_block'] / total_entries * 100) if total_entries > 0 else 0
    cap_rate = (stats['budget_cap'] / total_entries * 100) if total_entries > 0 else 0
    
    report_content = f"""# PHASE17 REAL PAPER V6.1  

****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
****: {config_path}  
** **: {duration_seconds/3600:.1f} ({duration_seconds/60:.1f})

---

##  Executive Summary

###  
|  |  |  |  |
|------|-----|------|------|
| ** ** | {duration_seconds/60:.1f} | {duration_seconds/60:.1f} | {'' if duration_seconds >= 600 else ''} |
| **Entry SUCCESS** | {stats['entry_success']} | 10 | {'' if stats['entry_success'] >= 10 else ''} |
| **Budget Cap** | {stats['budget_cap']} ({cap_rate:.1f}%) | 50% | {'' if cap_rate >= 50 else ''} |
| **Portfolio BLOCK** | {stats['portfolio_block']} ({block_rate:.1f}%) | <10% | {'' if block_rate < 10 else ''} |
| **Errors** | {stats['errors']} | 0 | {'' if stats['errors'] == 0 else ''} |

### V6 vs V6.1 
|  | V6 | V6.1 |
|------|-----|------|
| **Entry SUCCESS** | 1-2 | {stats['entry_success']} |
| **Budget Cap ** |  0 | {'' if stats['budget_cap'] > 0 else ''} {stats['budget_cap']} |
| **Portfolio BLOCK** | 28+ (80%+) | {stats['portfolio_block']} ({block_rate:.1f}%) |
| ** ** | Position   |   |

---

##  V6.1  

### Critical Bug Fix
****: `add_position()` `'value'`  , `_get_used_budget()` `'position_value'`    
****: used_budget  0, available_budget  total_budget, Budget Cap 

****:
```python
# portfolio_manager.py - add_position()
position = {{
    'id': position_id,
    'symbol': symbol,
    'strategy': strategy,
    'position_value': position_value,  #  
    'value': position_value,  #  
    'side': side,
    'status': 'OPEN'  #  
}}
```

###  
1. **_get_used_budget()**   
2. **position_value=0**  (qty * entry_price )
3. **Budget Check**  

---

##   

###  

|  | Entry | Budget Cap | Portfolio BLOCK |  Entry |
|------|-------|------------|-----------------|------------|
"""
    
    for i, cp in enumerate(stats['checkpoints']):
        report_content += f"| M{cp['elapsed_min']:.0f} | {cp['entry_success']} | {cp['budget_cap']} | {cp['portfolio_block']} | {cp['entry_success']} |\n"
    
    report_content += f"""

###  
- ** **: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
- ** **: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- ** **: {duration_seconds/60:.1f}
- **Entry SUCCESS**: {stats['entry_success']}
- **Entry REDUCED**: {stats['entry_reduced']}
- **Entry BLOCK**: {stats['entry_block']}
  - Portfolio Budget BLOCK: {stats['portfolio_block']}
- **Budget Cap Applied**: {stats['budget_cap']}
- **Errors**: {stats['errors']}

---

##  

### V6.1  
"""
    
    if stats['budget_cap'] > 0 and block_rate < 10:
        report_content += """
** SUCCESS**: Budget Cap  , Portfolio Budget BLOCK  .

** **:
1. Budget Cap   (V6: 0  V6.1: {budget_cap})
2. Portfolio Budget BLOCK   (V6: 80%+  V6.1: {block_rate:.1f}%)
3. Entry   (V6: 1-2  V6.1: {entry_success})

** **:
-  12 REAL PAPER   
- : `python scripts/run_real_paper_12h_supervised.py --duration 12h`
""".format(budget_cap=stats['budget_cap'], block_rate=block_rate, entry_success=stats['entry_success'])
    else:
        report_content += f"""
** NEEDS REVIEW**: Budget Cap    .

** **:
- Budget Cap: {stats['budget_cap']} (: >0)
- Portfolio BLOCK: {stats['portfolio_block']} ({block_rate:.1f}%, : <10%)
- Entry SUCCESS: {stats['entry_success']}

** **:
1.   `logs/application.log`  
2. Budget   
3.    
"""
    
    report_content += f"""

---

##   
- Config: `{config_path}`
- Logs: `logs/application.log`, `logs/trading.log`
- Code: `execution/portfolio_manager.py`, `execution/position_sizer.py`, `execution/engine.py`

---

** **: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    #  
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f" Report saved: {report_path}\n")
    
    #   
    print("="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Entry SUCCESS: {stats['entry_success']}")
    print(f"Budget Cap: {stats['budget_cap']} ({cap_rate:.1f}%)")
    print(f"Portfolio BLOCK: {stats['portfolio_block']} ({block_rate:.1f}%)")
    print(f"Errors: {stats['errors']}")
    print("="*70)
    
    return report_path


def main():
    parser = argparse.ArgumentParser(description='PHASE17 REAL PAPER 12H Supervised Execution')
    parser.add_argument('--config', type=str, 
                       default='configs/scalping/real_paper_12h_v6_1_phase17.yml',
                       help='Config file path')
    parser.add_argument('--duration', type=str, default='12h',
                       help='Duration (e.g., 12h, 60m, 10m)')
    parser.add_argument('--check-interval', type=int, default=30,
                       help='Log check interval in seconds')
    
    args = parser.parse_args()
    
    # Duration 
    try:
        duration_seconds = parse_duration(args.duration)
    except ValueError as e:
        print(f" Error: {e}")
        sys.exit(1)
    
    config_path = PROJECT_ROOT / args.config
    if not config_path.exists():
        print(f" Config file not found: {config_path}")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("PHASE17 REAL PAPER 12H SUPERVISED EXECUTION")
    print("="*70)
    print(f"Config: {config_path.name}")
    print(f"Duration: {args.duration} ({duration_seconds}s)")
    print(f"Start: {datetime.now()}")
    print("="*70)
    
    start_time = datetime.now()
    
    try:
        # 1.  
        init_environment()
        
        # 2. REAL PAPER 
        process = start_paper_trading(config_path)
        
        # 3. 
        stats = monitor_logs(duration_seconds, args.check_interval)
        
        # 4.  
        print("\n" + "="*70)
        print(" STOPPING REAL PAPER PROCESS")
        print("="*70)
        try:
            process.terminate()
            process.wait(timeout=10)
            print(" Process terminated gracefully\n")
        except subprocess.TimeoutExpired:
            process.kill()
            print(" Process killed (timeout)\n")
        
        end_time = datetime.now()
        
        # 5.  
        report_path = generate_report(stats, duration_seconds, config_path, start_time, end_time)
        
        print("\n" + "="*70)
        print(" SUPERVISED EXECUTION COMPLETED")
        print("="*70)
        print(f"Duration: {(end_time - start_time).total_seconds()/60:.1f}m")
        print(f"Report: {report_path}")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n Interrupted by user")
        if 'process' in locals():
            process.kill()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n Error: {e}")
        import traceback
        traceback.print_exc()
        if 'process' in locals():
            process.kill()
        sys.exit(1)


if __name__ == "__main__":
    main()
