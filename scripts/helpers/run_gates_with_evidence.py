#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSOT Gate Execution with UTF-8 Evidence Logs (PHASE36-1 S4)
"""
import subprocess
import sys
from pathlib import Path


def run_gate(name: str, cmd: list, log_path: Path) -> tuple[int, str]:
    """Execute gate and save UTF-8 log"""
    print(f"🚪 Running Gate: {name}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )
        
        output = result.stdout + result.stderr
        
        # Write UTF-8 log
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"✅ {name}: Exit code {result.returncode}")
        print(f"📄 Evidence: {log_path}")
        
        return result.returncode, output
    
    except Exception as e:
        error_msg = f"❌ {name} FAILED: {e}"
        print(error_msg)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        
        return 1, error_msg


def main():
    evidence_dir = Path("logs/evidence/phase36_1_s4_gates")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    gates = [
        {
            "name": "Gate 0 (doctor)",
            "cmd": [sys.executable, "--version"],
            "log": evidence_dir / "doctor_final.log"
        },
        {
            "name": "Gate 1 (fast)",
            "cmd": [sys.executable, "-m", "pytest", "tests/unit", "--tb=short", "-v", "--maxfail=3"],
            "log": evidence_dir / "fast_final.log"
        },
        {
            "name": "Gate 2 (regression)",
            "cmd": [sys.executable, "-m", "pytest", "tests/regression", "--tb=short", "-v", "--maxfail=5"],
            "log": evidence_dir / "regression_final.log"
        }
    ]
    
    # Gate 0: Doctor (version + dependencies)
    print("=" * 60)
    print("SSOT GATE 0: DOCTOR")
    print("=" * 60)
    
    doctor_log = evidence_dir / "doctor_final.log"
    with open(doctor_log, 'w', encoding='utf-8') as f:
        # Python version
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True, encoding='utf-8')
        f.write(result.stdout + result.stderr + "\n")
        
        # Core dependencies
        dep_result = subprocess.run(
            [sys.executable, "-c", "import psutil, redis, sqlalchemy, pandas, numpy, yaml; print('Core dependencies OK')"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        f.write(dep_result.stdout + dep_result.stderr + "\n")
        
        if dep_result.returncode == 0:
            f.write("✅ Gate 0 (doctor): PASS\n")
            print("✅ Gate 0 (doctor): PASS")
        else:
            f.write(f"❌ Dependency check failed with exit code {dep_result.returncode}\n")
            print(f"❌ Gate 0 (doctor): FAIL")
            return 1
    
    # Gate 1 & 2
    for gate in gates[1:]:
        print("=" * 60)
        print(gate["name"].upper())
        print("=" * 60)
        
        exit_code, output = run_gate(gate["name"], gate["cmd"], gate["log"])
        
        if exit_code != 0:
            print(f"❌ {gate['name']} FAILED")
            return exit_code
        
        # Parse test count from output
        if "passed" in output.lower():
            print(f"✅ {gate['name']}: PASS")
        else:
            print(f"⚠️ {gate['name']}: Check log for details")
    
    print("=" * 60)
    print("✅ ALL GATES PASS")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
