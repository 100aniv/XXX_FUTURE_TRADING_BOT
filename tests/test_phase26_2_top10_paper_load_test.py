"""
PHASE26-2: Top10 Multi-Symbol PAPER Load Test - Unit Tests
============================================================
Universe Provider + Multi-Symbol Engine v1 + PHASE25-0 Harness 통합 검증

테스트 범위:
1. Universe Config 로딩 (Static, TopN)
2. Runner Wiring (engine.run_v2 호출 경로)
3. Per-symbol 메트릭 수집
4. 리포트 생성 (Multi-Symbol 섹션)
5. 회귀 방지 (PHASE25-0 하위 호환)
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json


# 테스트 픽스처
@pytest.fixture
def phase26_2_config_path():
    """PHASE26-2 Config 파일 경로"""
    config_path = Path(__file__).parent.parent / "configs" / "paper" / "phase26_2_top10_paper_2h.yml"
    assert config_path.exists(), f"Config 파일 없음: {config_path}"
    return str(config_path)


@pytest.fixture
def sample_config_static():
    """Static Universe Provider Config (샘플)"""
    return {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'timeframe': '5m',
        'universe': {
            'enabled': True,
            'provider': {
                'type': 'static',
                'static_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            },
            'filters': {
                'quote_assets': ['USDT']
            }
        },
        'paper': {
            'duration_mode': 'wall_clock',
            'duration_hours': 2.0
        }
    }


@pytest.fixture
def sample_config_topn():
    """TopN Universe Provider Config (샘플)"""
    return {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'timeframe': '5m',
        'universe': {
            'enabled': True,
            'provider': {
                'type': 'topn_volume',
                'top_n': 10
            },
            'filters': {
                'quote_assets': ['USDT'],
                'min_24h_volume_usd': 10000000
            }
        },
        'paper': {
            'duration_mode': 'wall_clock',
            'duration_hours': 2.0
        }
    }


@pytest.fixture
def mock_db_connection():
    """Mock DB Connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # Per-symbol trades mock data
    mock_cursor.fetchall.return_value = [
        ('BTCUSDT', 10),
        ('ETHUSDT', 8),
        ('BNBUSDT', 5)
    ]
    
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None
    
    return mock_conn


# ========================================
# TEST 1: Universe Config 로딩 (Static)
# ========================================
def test_universe_config_loading_static(sample_config_static, tmp_path):
    """
    Static Universe Provider Config 로딩 테스트
    
    검증:
    - universe.enabled=true 확인
    - provider.type='static' 확인
    - static_symbols 리스트 확인
    """
    # Config 파일 생성
    config_path = tmp_path / "test_static.yml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_static, f)
    
    # Runner 모듈 임포트
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    from phase26_2_run_top10_paper import validate_universe_config
    
    # 검증
    assert validate_universe_config(str(config_path)), "Static config 검증 실패"
    
    # Config 다시 로딩해서 확인
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    assert config['universe']['enabled'] is True
    assert config['universe']['provider']['type'] == 'static'
    assert len(config['universe']['provider']['static_symbols']) == 3


# ========================================
# TEST 2: Universe Config 로딩 (TopN)
# ========================================
def test_universe_config_loading_topn(sample_config_topn, tmp_path):
    """
    TopN Universe Provider Config 로딩 테스트
    
    검증:
    - universe.enabled=true 확인
    - provider.type='topn_volume' 확인
    - top_n 값 확인
    """
    # Config 파일 생성
    config_path = tmp_path / "test_topn.yml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_topn, f)
    
    # Runner 모듈 임포트
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    from phase26_2_run_top10_paper import validate_universe_config
    
    # 검증
    assert validate_universe_config(str(config_path)), "TopN config 검증 실패"
    
    # Config 다시 로딩해서 확인
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    assert config['universe']['enabled'] is True
    assert config['universe']['provider']['type'] == 'topn_volume'
    assert config['universe']['provider']['top_n'] == 10


# ========================================
# TEST 3: Universe Config 없음 (Fallback)
# ========================================
def test_universe_config_missing_fallback(tmp_path):
    """
    Universe 섹션 없는 Config (Fallback 모드)
    
    검증:
    - universe 섹션 없어도 검증 통과 (Warning만)
    - 단일 심볼 모드로 fallback
    """
    config = {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'timeframe': '5m',
        'paper': {'duration_mode': 'wall_clock', 'duration_hours': 2.0}
    }
    
    config_path = tmp_path / "test_no_universe.yml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    # Runner 모듈 임포트
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    from phase26_2_run_top10_paper import validate_universe_config
    
    # 검증: Warning이지만 검증 통과 (fallback 허용)
    assert validate_universe_config(str(config_path)), "No universe config 검증 실패"


# ========================================
# TEST 4: Per-Symbol 메트릭 수집
# ========================================
def test_per_symbol_metrics_collection(mock_db_connection):
    """
    Per-Symbol 메트릭 수집 테스트
    
    검증:
    - DB에서 symbol별 trade_count 조회
    - multi_symbol 메트릭 생성
    - symbols 리스트 추출
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    
    # Mock psycopg2
    with patch('psycopg2.connect', return_value=mock_db_connection):
        from phase26_2_run_top10_paper import analyze_results_multi_symbol
        
        # Mock 시간 범위
        start_time = datetime.now() - timedelta(hours=2)
        end_time = datetime.now()
        
        # Mock analyze_results (PHASE25-0)
        with patch('phase26_2_run_top10_paper.analyze_results', return_value={'db': {}}):
            metrics = analyze_results_multi_symbol(start_time, end_time, "dummy_config.yml")
        
        # 검증
        assert 'multi_symbol' in metrics
        assert metrics['multi_symbol']['symbol_count'] == 3
        assert 'BTCUSDT' in metrics['multi_symbol']['symbols']
        assert metrics['multi_symbol']['per_symbol_trades']['BTCUSDT'] == 10


# ========================================
# TEST 5: 리포트 생성 (Multi-Symbol 섹션)
# ========================================
def test_report_generation_multi_symbol(tmp_path):
    """
    Multi-Symbol 리포트 생성 테스트
    
    검증:
    - MD 리포트에 Multi-Symbol 섹션 포함
    - JSON 요약에 multi_symbol 메트릭 포함
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    
    # Mock 메트릭
    metrics = {
        'db': {
            'trade_count': 23,
            'active_positions': 0,
            'actual_duration': '2.0H'
        },
        'multi_symbol': {
            'symbol_count': 3,
            'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            'per_symbol_trades': {
                'BTCUSDT': 10,
                'ETHUSDT': 8,
                'BNBUSDT': 5
            }
        }
    }
    
    monitor_result = {
        'status': 'PASS',
        'error_count': 0,
        'critical_count': 0
    }
    
    # Report 파일 경로 임시로 변경
    import phase26_2_run_top10_paper as runner_module
    original_report_md = runner_module.REPORT_MD
    original_summary_json = runner_module.SUMMARY_JSON
    
    try:
        runner_module.REPORT_MD = tmp_path / "test_report.md"
        runner_module.SUMMARY_JSON = tmp_path / "test_summary.json"
        
        # 리포트 생성
        runner_module.save_report_multi_symbol(
            metrics=metrics,
            config_path="test_config.yml",
            duration_hours=2.0,
            monitor_result=monitor_result
        )
        
        # MD 리포트 검증
        assert runner_module.REPORT_MD.exists(), "MD 리포트 파일 없음"
        
        with open(runner_module.REPORT_MD, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert 'Multi-Symbol 메트릭' in content, "Multi-Symbol 섹션 없음"
        assert 'BTCUSDT' in content, "심볼 리스트 없음"
        assert '10' in content, "Per-symbol trade count 없음"
        
        # JSON 요약 검증
        assert runner_module.SUMMARY_JSON.exists(), "JSON 요약 파일 없음"
        
        with open(runner_module.SUMMARY_JSON, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        assert 'metrics' in summary
        assert 'multi_symbol' in summary['metrics']
        assert summary['metrics']['multi_symbol']['symbol_count'] == 3
    
    finally:
        # 복원
        runner_module.REPORT_MD = original_report_md
        runner_module.SUMMARY_JSON = original_summary_json


# ========================================
# TEST 6: Runner Wiring (엔진 호출 경로)
# ========================================
def test_runner_wiring_engine_call(phase26_2_config_path):
    """
    Runner가 engine.run_v2를 올바른 인자로 호출하는지 검증
    
    검증:
    - PHASE25-0 start_long_run 호출
    - run_v2.py subprocess 시작
    - Config 경로 전달
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    from phase26_2_run_top10_paper import validate_universe_config
    
    # Config 검증 (실제 PHASE26-2 config 파일)
    assert validate_universe_config(phase26_2_config_path), "실제 config 검증 실패"
    
    # start_long_run 호출 테스트 (Mock)
    with patch('phase25_0_long_run_paper.subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        from phase25_0_long_run_paper import start_long_run
        
        # start_long_run 호출
        process = start_long_run(phase26_2_config_path, duration_hours=2.0, tag="test")
        
        # 검증: subprocess.Popen 호출됨
        assert mock_popen.called, "subprocess.Popen 호출되지 않음"
        
        # 호출 인자 확인 (cmd는 string으로 전달됨)
        call_args = mock_popen.call_args
        # args[0]는 첫 번째 위치 인자 (cmd string)
        cmd_string = call_args[0][0] if call_args[0] else call_args.kwargs.get('cmd', '')
        
        # cmd string에 run_v2.py와 config가 포함되어 있는지 확인
        assert 'run_v2.py' in cmd_string, f"run_v2.py 호출되지 않음: {cmd_string}"
        assert 'phase26_2_top10_paper_2h.yml' in cmd_string, f"Config 전달되지 않음: {cmd_string}"
        
        # Process 객체 반환 확인
        assert process is not None, "프로세스 객체 없음"
        assert process.pid == 12345, "프로세스 PID 불일치"


# ========================================
# TEST 7: 회귀 방지 (PHASE25-0 하위 호환)
# ========================================
def test_backward_compatibility_phase25():
    """
    PHASE25-0 함수 임포트 가능 여부 확인
    
    검증:
    - PHASE25-0 harness 함수들이 정상 임포트되는지
    - 기존 함수 인터페이스 유지 확인
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    
    # PHASE25-0 함수 임포트
    from phase25_0_long_run_paper import (
        cleanup_environment,
        run_preflight_checks,
        run_clean_state,
        start_long_run,
        monitor_logs,
        analyze_results
    )
    
    # 함수 존재 확인
    assert callable(cleanup_environment), "cleanup_environment 함수 없음"
    assert callable(run_preflight_checks), "run_preflight_checks 함수 없음"
    assert callable(run_clean_state), "run_clean_state 함수 없음"
    assert callable(start_long_run), "start_long_run 함수 없음"
    assert callable(monitor_logs), "monitor_logs 함수 없음"
    assert callable(analyze_results), "analyze_results 함수 없음"


# ========================================
# TEST 8: Universe Provider 타입 검증
# ========================================
@pytest.mark.parametrize("provider_type,is_valid", [
    ('static', True),
    ('topn_volume', True),
    ('invalid_type', False),
    ('', False),
])
def test_universe_provider_type_validation(provider_type, is_valid, tmp_path):
    """
    Universe Provider 타입 검증 (여러 타입)
    
    검증:
    - 지원하는 타입 (static, topn_volume): 통과
    - 지원하지 않는 타입: 실패
    """
    config = {
        'mode': 'paper',
        'symbol': 'BTCUSDT',
        'universe': {
            'enabled': True,
            'provider': {
                'type': provider_type,
                'top_n': 10 if provider_type == 'topn_volume' else None
            }
        }
    }
    
    # Static일 경우 static_symbols 추가
    if provider_type == 'static':
        config['universe']['provider']['static_symbols'] = ['BTCUSDT']
    
    config_path = tmp_path / f"test_{provider_type}.yml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "infra"))
    from phase26_2_run_top10_paper import validate_universe_config
    
    result = validate_universe_config(str(config_path))
    assert result == is_valid, f"Provider type '{provider_type}' 검증 결과 불일치"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
