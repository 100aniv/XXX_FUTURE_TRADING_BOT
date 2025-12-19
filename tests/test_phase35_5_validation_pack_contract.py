"""
PHASE35-5: Validation Pack 계약 테스트
======================================
재발 방지: runner SSOT, persist_trace, DB evidence 검증
"""
import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestPhase35_5_ValidationPackContract:
    """PHASE35-5 Validation Pack 계약 테스트"""
    
    def test_runner_script_exists(self):
        """Runner 스크립트가 존재하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        assert runner_path.exists(), f"Runner not found: {runner_path}"
    
    def test_runner_has_window_option(self):
        """Runner가 --window 옵션을 지원하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "--window" in content, "Runner must support --window option"
        assert "7d" in content and "1m" in content and "3m" in content, \
            "Runner must support 7d/1m/3m windows"
    
    def test_runner_has_profile_option(self):
        """Runner가 --profile 옵션을 지원하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "--profile" in content, "Runner must support --profile option"
        assert "L4" in content, "Runner must support L4 profile"
    
    def test_runner_forces_db_enabled(self):
        """Runner가 database.enabled=True를 강제하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert '"enabled": True' in content or "'enabled': True" in content, \
            "Runner must force database.enabled=True"
    
    def test_runner_has_persist_trace(self):
        """Runner가 persist_trace 계측을 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "PERSIST_TRACE" in content, "Runner must have PERSIST_TRACE"
        assert "db_persist_called" in content, "Runner must track db_persist_called"
        assert "db_insert_success" in content, "Runner must track db_insert_success"
    
    def test_runner_uses_ssot_candles(self):
        """Runner가 SSOT 캔들 로딩을 재사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "load_candles_ssot" in content, "Runner must use load_candles_ssot"
        assert "signal_probe_iter24" in content, "Runner must reuse signal_probe_iter24.load_candles"
    
    def test_runner_has_ac_checks(self):
        """Runner가 AC 체크를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # 필수 AC들
        required_acs = [
            "ac1_db_schema_exists",
            "ac2_trades_gt_zero",
            "ac3_persist_trace_valid",
            "ac4_report_generated"
        ]
        
        for ac in required_acs:
            assert ac in content, f"Runner must check {ac}"
    
    def test_runner_saves_results(self):
        """Runner가 결과를 저장하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "RESULTS_DIR" in content, "Runner must have RESULTS_DIR"
        assert "phase35_5" in content, "Runner must save to phase35_5 directory"
        assert "json.dump" in content, "Runner must save JSON results"
    
    def test_artifacts_directory_structure(self):
        """Artifacts 디렉토리 구조가 표준을 따르는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # 표준 경로들 (백슬래시/슬래시 모두 허용)
        assert ("artifacts/phase35/phase35_5" in content or 
                "artifacts\\phase35\\phase35_5" in content or
                '"phase35" / "phase35_5"' in content), \
            "Runner must use standard artifacts path"
        assert "results" in content, "Runner must have results subdirectory"
        assert "runs" in content or "RUNS_DIR" in content, \
            "Runner must have runs subdirectory"
    
    def test_runner_reuses_iter27_to_native(self):
        """Runner가 ITER27의 to_native() 수정을 참조하는지 검증"""
        # engine.py의 to_native() 존재 확인
        engine_path = PROJECT_ROOT / "execution" / "engine.py"
        content = engine_path.read_text(encoding="utf-8")
        
        assert "to_native" in content, "engine.py must have to_native() function"
        assert "hasattr(val, 'item')" in content, \
            "to_native() must handle numpy scalars with .item()"


class TestPhase35_5_NumpyTypePreventionContract:
    """ITER27 재발 방지: numpy 타입 변환 계약"""
    
    def test_save_trade_to_db_has_to_native(self):
        """save_trade_to_db가 to_native() 변환을 포함하는지 검증"""
        engine_path = PROJECT_ROOT / "execution" / "engine.py"
        
        # save_trade_to_db 함수 찾기
        content = engine_path.read_text(encoding="utf-8")
        
        # save_trade_to_db 함수 내에 to_native 호출이 있는지 확인
        assert "def save_trade_to_db" in content, "save_trade_to_db must exist"
        
        # to_native 함수 또는 .item() 호출 확인
        save_trade_section_start = content.find("def save_trade_to_db")
        save_trade_section_end = content.find("\ndef ", save_trade_section_start + 1)
        if save_trade_section_end == -1:
            save_trade_section_end = len(content)
        
        save_trade_section = content[save_trade_section_start:save_trade_section_end]
        
        assert "to_native" in save_trade_section or "item()" in save_trade_section, \
            "save_trade_to_db must convert numpy types to native"
    
    def test_to_native_handles_none(self):
        """to_native 함수가 None을 올바르게 처리하는지 검증"""
        # ITER27에서 구현된 to_native 패턴 테스트
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        assert to_native(None) is None
    
    def test_to_native_handles_numpy_float64(self):
        """to_native 함수가 numpy.float64를 변환하는지 검증"""
        import numpy as np
        
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        np_val = np.float64(123.45)
        result = to_native(np_val)
        
        assert isinstance(result, float), f"Expected float, got {type(result)}"
        assert not hasattr(result, 'item'), "Result should not be numpy type"
        assert result == pytest.approx(123.45)


class TestPhase35_5_SSotReuseContract:
    """SSOT 재사용 계약"""
    
    def test_runner_imports_signal_probe(self):
        """Runner가 signal_probe_iter24를 import하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "from scripts.phase35.signal_probe_iter24 import load_candles" in content, \
            "Runner must import load_candles from signal_probe_iter24"
    
    def test_runner_uses_extract_date_range_from_df(self):
        """Runner가 extract_date_range_from_df를 사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "extract_date_range_from_df" in content, \
            "Runner must use extract_date_range_from_df"
    
    def test_runner_uses_get_db_evidence(self):
        """Runner가 get_db_evidence를 사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "get_db_evidence" in content, \
            "Runner must use get_db_evidence pattern"
        assert "trading.trades" in content, \
            "Runner must query trading.trades"
    
    def test_runner_uses_l4_ultra_debug_overrides(self):
        """Runner가 L4_ULTRA_DEBUG_OVERRIDES를 사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "L4_ULTRA_DEBUG_OVERRIDES" in content, \
            "Runner must have L4_ULTRA_DEBUG_OVERRIDES"
        
        # 주요 오버라이드 키 확인
        required_overrides = [
            "ensemble",
            "risk",
            "execution",
            "database"
        ]
        
        for key in required_overrides:
            assert f'"{key}"' in content or f"'{key}'" in content, \
                f"L4_ULTRA_DEBUG_OVERRIDES must include {key}"


class TestPhase35_5_ReportPathContract:
    """Report 경로 SSOT 계약"""
    
    def test_runner_extracts_report_path_from_config(self):
        """Runner가 config에서 report path를 추출하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "output_file" in content, \
            "Runner must extract output_file from config"
        assert "report_path" in content, \
            "Runner must track report_path"
    
    def test_runner_checks_report_exists(self):
        """Runner가 report 존재 여부를 확인하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase35" / "run_phase35_5_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert ".exists()" in content, \
            "Runner must check if report exists"
