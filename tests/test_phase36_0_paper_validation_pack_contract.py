"""
PHASE36-0: Paper Trading Validation Pack 계약 테스트
===================================================
재발 방지: PHASE35-5 SSOT 재사용, Paper 모드 특화 체크

재발 방지 항목 (PHASE35-5 계승):
1. Runner 스크립트 존재 및 stage 옵션 지원
2. database.enabled=True 강제
3. persist_trace 계측 포함
4. to_native() 패치 포함 (numpy scalar 방지)
5. qualified query (trading.trades) 사용
6. Artifacts 표준 경로
7. AC 체크 프레임워크

Paper 특화 추가:
8. Duration 매핑 (smoke/baseline/longrun → 시간)
9. mode='paper' 강제
10. 레이트리밋/네트워크 허용 (선택)
"""
import pytest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestPhase36_0_PaperValidationPackContract:
    """PHASE36-0 Paper Trading Validation Pack 계약 테스트"""
    
    # ========================================================================
    # 기본 구조 검증 (PHASE35-5 패턴)
    # ========================================================================
    
    def test_runner_script_exists(self):
        """Runner 스크립트가 존재하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        assert runner_path.exists(), f"Runner not found: {runner_path}"
    
    def test_preflight_script_exists(self):
        """Preflight 스크립트가 존재하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        assert preflight_path.exists(), f"Preflight not found: {preflight_path}"
    
    # ========================================================================
    # Stage 옵션 검증 (PHASE36-0 신규)
    # ========================================================================
    
    def test_runner_has_stage_option(self):
        """Runner가 --stage 옵션을 지원하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "--stage" in content, "Runner must support --stage option"
        assert "smoke" in content and "baseline" in content and "longrun" in content, \
            "Runner must support smoke/baseline/longrun stages"
    
    def test_runner_has_duration_mapping(self):
        """Runner가 stage → duration 매핑을 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "DURATION_MAP" in content, "Runner must have DURATION_MAP"
        assert "0.33" in content or "20" in content, "Runner must map smoke to ~20 minutes"
        assert "1.0" in content or "1h" in content, "Runner must map baseline to 1 hour"
        assert "3.0" in content or "3h" in content, "Runner must map longrun to 3 hours"
    
    def test_runner_has_profile_option(self):
        """Runner가 --profile 옵션을 지원하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "--profile" in content, "Runner must support --profile option"
        assert "L4" in content or "L3" in content or "L0" in content, \
            "Runner must support L4/L3/L0 profiles"
    
    # ========================================================================
    # Paper 모드 강제 (PHASE36-0 신규)
    # ========================================================================
    
    def test_runner_forces_paper_mode(self):
        """Runner가 mode='paper'를 강제하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "'paper'" in content or '"paper"' in content, \
            "Runner must force mode='paper'"
        assert "mode='paper'" in content or 'mode="paper"' in content or "['mode'] = 'paper'" in content, \
            "Runner must set mode to paper"
    
    # ========================================================================
    # database.enabled=True 강제 (PHASE35-5 재발 방지)
    # ========================================================================
    
    def test_runner_forces_db_enabled(self):
        """Runner가 database.enabled=True를 강제하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert ("'enabled': True" in content or '"enabled": True' in content or 
                "['enabled'] = True" in content), \
            "Runner must force database.enabled=True"
    
    # ========================================================================
    # persist_trace 계측 (PHASE35-5 재사용)
    # ========================================================================
    
    def test_runner_has_persist_trace(self):
        """Runner가 persist_trace 계측을 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "PERSIST_TRACE" in content, "Runner must have PERSIST_TRACE"
        assert "db_persist_called" in content, "Runner must track db_persist_called"
        assert "db_insert_success" in content, "Runner must track db_insert_success"
        assert "db_insert_fail" in content, "Runner must track db_insert_fail"
    
    def test_runner_has_trace_reset(self):
        """Runner가 reset_trace()를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "reset_trace" in content, "Runner must have reset_trace()"
        assert "def reset_trace" in content, "Runner must define reset_trace()"
    
    def test_runner_has_instrumented_save_trade_to_db(self):
        """Runner가 instrumented_save_trade_to_db를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "instrumented_save_trade_to_db" in content, \
            "Runner must have instrumented_save_trade_to_db"
        assert "inc_trace" in content, "Runner must call inc_trace"
    
    # ========================================================================
    # to_native() 패치 (PHASE35-5 재사용 - numpy scalar 방지)
    # ========================================================================
    
    def test_runner_has_to_native(self):
        """Runner가 to_native() 패치를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "to_native" in content, "Runner must have to_native()"
        assert "def to_native" in content, "Runner must define to_native()"
        assert "numpy" in content or "np." in content, \
            "Runner must handle numpy types in to_native()"
    
    def test_runner_installs_to_native_patch(self):
        """Runner가 to_native() 전역 패치를 설치하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "install_to_native_patch" in content or "builtins.to_native" in content, \
            "Runner must install to_native() as global"
    
    # ========================================================================
    # qualified query (PHASE35-5 재발 방지)
    # ========================================================================
    
    def test_runner_uses_qualified_query(self):
        """Runner가 qualified query (trading.trades)를 사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # trading.trades 사용 확인
        assert "trading.trades" in content, \
            "Runner must use qualified query (trading.trades)"
        
        # unqualified query (FROM trades) 금지
        import re
        # "FROM trades" 패턴 검색 (trading.trades는 제외)
        unqualified_pattern = r'FROM\s+trades(?!\s*WHERE)'
        # 더 정확한 검사를 위해 trading.trades를 제외한 "FROM trades" 찾기
        lines = content.split('\n')
        for line in lines:
            if 'FROM' in line.upper() and 'trades' in line.lower():
                if 'trading.trades' not in line:
                    # SELECT/INSERT/UPDATE/DELETE ... FROM trades 형태 체크
                    if re.search(r'\bFROM\s+trades\b', line, re.IGNORECASE):
                        pytest.fail(f"Unqualified query found: {line.strip()}")
    
    # ========================================================================
    # AC 체크 프레임워크 (PHASE35-5 재사용)
    # ========================================================================
    
    def test_runner_has_ac_checks(self):
        """Runner가 AC 체크를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # 필수 AC들
        required_acs = [
            "ac1_trades_gt_zero",
            "ac2_db_persist_valid",
            "ac3_persist_trace_valid",
            "ac4_report_generated",
            "ac5_run_complete"
        ]
        
        for ac in required_acs:
            assert ac in content, f"Runner must check {ac}"
    
    def test_runner_has_check_acceptance_criteria_function(self):
        """Runner가 check_acceptance_criteria 함수를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "check_acceptance_criteria" in content, \
            "Runner must have check_acceptance_criteria function"
        assert "def check_acceptance_criteria" in content, \
            "Runner must define check_acceptance_criteria"
    
    # ========================================================================
    # Artifacts 표준 경로 (PHASE36-0)
    # ========================================================================
    
    def test_runner_saves_results(self):
        """Runner가 결과를 저장하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "RESULTS_DIR" in content, "Runner must have RESULTS_DIR"
        assert "RUNS_DIR" in content, "Runner must have RUNS_DIR"
        assert "json.dump" in content, "Runner must save JSON results"
    
    def test_artifacts_directory_structure(self):
        """Artifacts 디렉토리 구조가 표준을 따르는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # 표준 경로들 (백슬래시/슬래시 모두 허용)
        assert ("artifacts/phase36/phase36_0" in content or 
                "artifacts\\phase36\\phase36_0" in content or
                '"phase36" / "phase36_0"' in content), \
            "Runner must use standard artifacts path"
        assert "results" in content, "Runner must have results subdirectory"
        assert "runs" in content, "Runner must have runs subdirectory"
        assert "preflight" in content, "Runner must have preflight subdirectory"
    
    # ========================================================================
    # DB Evidence 수집 (PHASE35-5 재사용)
    # ========================================================================
    
    def test_runner_has_get_db_evidence(self):
        """Runner가 get_db_evidence 함수를 포함하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "get_db_evidence" in content, "Runner must have get_db_evidence"
        assert "def get_db_evidence" in content, "Runner must define get_db_evidence"
    
    def test_db_evidence_uses_qualified_query(self):
        """get_db_evidence가 qualified query를 사용하는지 검증"""
        runner_path = PROJECT_ROOT / "scripts" / "phase36" / "run_phase36_0_paper_validation_pack.py"
        content = runner_path.read_text(encoding="utf-8")
        
        # get_db_evidence 함수 내에서 trading.trades 사용 확인
        assert "trading.trades" in content, \
            "get_db_evidence must use qualified query (trading.trades)"
    
    # ========================================================================
    # Preflight 검증
    # ========================================================================
    
    def test_preflight_checks_docker(self):
        """Preflight가 Docker 체크를 포함하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        content = preflight_path.read_text(encoding="utf-8")
        
        assert "docker" in content.lower(), "Preflight must check Docker"
        assert "trading_db_postgres" in content, "Preflight must check trading_db_postgres"
        assert "trading_redis" in content, "Preflight must check trading_redis"
    
    def test_preflight_checks_db(self):
        """Preflight가 DB 체크를 포함하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        content = preflight_path.read_text(encoding="utf-8")
        
        assert "get_db_connection" in content, "Preflight must check DB connection"
        assert "trading.trades" in content, "Preflight must check trading.trades table"
    
    def test_preflight_cleans_db(self):
        """Preflight가 DB cleanup을 수행하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        content = preflight_path.read_text(encoding="utf-8")
        
        assert "DELETE FROM" in content or "clean" in content.lower(), \
            "Preflight must clean DB"
    
    def test_preflight_cleans_redis(self):
        """Preflight가 Redis cleanup을 수행하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        content = preflight_path.read_text(encoding="utf-8")
        
        assert "redis" in content.lower(), "Preflight must clean Redis"
        assert "cooldown" in content.lower() or "portfolio" in content.lower(), \
            "Preflight must clean cooldown/portfolio keys"
    
    def test_preflight_saves_evidence(self):
        """Preflight가 evidence를 저장하는지 검증"""
        preflight_path = PROJECT_ROOT / "scripts" / "phase36" / "preflight_phase36_0.py"
        content = preflight_path.read_text(encoding="utf-8")
        
        assert "evidence" in content.lower(), "Preflight must save evidence"
        assert "json.dump" in content, "Preflight must save JSON evidence"
        assert "preflight" in content.lower(), "Preflight must save to preflight directory"


# ============================================================================
# 통합 실행 테스트 (선택, 실제 실행은 STEP E에서)
# ============================================================================

class TestPhase36_0_Integration:
    """PHASE36-0 통합 테스트 (선택)"""
    
    @pytest.mark.skip(reason="Integration test - run manually in STEP E")
    def test_smoke_run_executes(self):
        """Smoke run이 실행되는지 검증 (수동 실행)"""
        pass
    
    @pytest.mark.skip(reason="Integration test - run manually in STEP E")
    def test_baseline_run_executes(self):
        """Baseline run이 실행되는지 검증 (수동 실행)"""
        pass
    
    @pytest.mark.skip(reason="Integration test - run manually in STEP E")
    def test_longrun_run_executes(self):
        """Long-run이 실행되는지 검증 (수동 실행)"""
        pass
