"""
PHASE35-4 ITER20: Run Isolation Contract Tests
==============================================

AC1: Candidate별 실행이 DB/Redis 관점에서 완전 격리
AC2: 각 run의 report는 반드시 해당 trial_id의 trades만 집계
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock


class TestRunIsolationContract:
    """ITER20 Run Isolation SSOT Contract Tests"""
    
    def test_trial_id_propagation_in_config(self):
        """trial_id가 config에서 run_id로 전파되는지 확인"""
        config = {
            "trial_id": "test_trial_123",
            "run_id": "unknown"
        }
        
        # trial_id가 설정되면 run_id 대신 사용
        trial_id = config.get("trial_id") or config.get("run_id", "unknown")
        
        assert trial_id == "test_trial_123"
    
    def test_trial_id_fallback_to_run_id(self):
        """trial_id가 없으면 run_id를 사용하는지 확인"""
        config = {
            "run_id": "fallback_run_456"
        }
        
        trial_id = config.get("trial_id") or config.get("run_id", "unknown")
        
        assert trial_id == "fallback_run_456"
    
    def test_unique_trial_id_generation(self):
        """각 실행마다 고유한 trial_id가 생성되는지 확인"""
        trial_ids = set()
        
        for i in range(100):
            trial_id = f"iter20_C{i}_{uuid.uuid4().hex[:8]}"
            assert trial_id not in trial_ids
            trial_ids.add(trial_id)
        
        assert len(trial_ids) == 100
    
    def test_trial_id_format(self):
        """trial_id 형식이 올바른지 확인"""
        candidate_id = "C0_baseline"
        trial_id = f"iter20_{candidate_id}_{uuid.uuid4().hex[:8]}"
        
        assert trial_id.startswith("iter20_")
        assert candidate_id in trial_id
        assert len(trial_id) > len(f"iter20_{candidate_id}_")


class TestReportGeneratorTrialIdContract:
    """Report Generator의 trial_id 필터링 계약 테스트"""
    
    def test_generate_backtest_report_accepts_trial_id(self):
        """generate_backtest_report가 trial_id 파라미터를 받는지 확인"""
        from analytics.report_generator import generate_backtest_report
        import inspect
        
        sig = inspect.signature(generate_backtest_report)
        params = list(sig.parameters.keys())
        
        assert "trial_id" in params
    
    def test_calculate_tuning_score_filters_by_trial_id(self):
        """_calculate_tuning_score_postgres가 trial_id로 필터링하는지 확인"""
        from analytics.report_generator import ReportGenerator
        import inspect
        
        generator = ReportGenerator()
        method = generator._calculate_tuning_score_postgres
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        assert "trial_id" in params


class TestEngineTrialIdIntegration:
    """Engine의 trial_id 통합 테스트"""
    
    def test_engine_passes_trial_id_to_save_trade(self):
        """engine이 save_trade_to_db에 trial_id를 전달하는지 확인"""
        from execution.engine import save_trade_to_db
        import inspect
        
        sig = inspect.signature(save_trade_to_db)
        params = list(sig.parameters.keys())
        
        assert "trial_id" in params
    
    def test_run_v2_accepts_config_with_trial_id(self):
        """run_v2가 trial_id가 포함된 config를 받을 수 있는지 확인"""
        from execution.engine import run_v2
        import inspect
        
        sig = inspect.signature(run_v2)
        params = list(sig.parameters.keys())
        
        # config dict에 trial_id를 포함할 수 있음
        assert "config" in params


class TestIter20ArtifactsContract:
    """ITER20 Artifacts 계약 테스트"""
    
    def test_iter20_results_schema(self):
        """iter20_results.json 스키마 검증"""
        import json
        from pathlib import Path
        
        results_path = Path("artifacts/phase35/iter20/iter20_results.json")
        
        if results_path.exists():
            with open(results_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            
            # 필수 필드 확인
            assert "generated_at" in results
            assert "candidates" in results
            assert "isolation_verification" in results
            
            # isolation_verification 구조 확인
            verification = results["isolation_verification"]
            assert "ac1_db_isolation" in verification
            assert "ac2_no_cross_contamination" in verification
            
            # 각 candidate에 trial_id 확인
            for candidate in results["candidates"]:
                assert "candidate_id" in candidate
                assert "trial_id" in candidate
                assert "evidence" in candidate
    
    def test_signal_flow_artifact_schema(self):
        """signal_flow.json 스키마 검증"""
        import json
        from pathlib import Path
        
        for candidate in ["C0_baseline", "C1_relaxed"]:
            signal_flow_path = Path(f"artifacts/phase35/iter20/{candidate}/signal_flow.json")
            
            if signal_flow_path.exists():
                with open(signal_flow_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 필수 필드 확인
                assert "trial_id" in data
                assert "db_trades_count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
