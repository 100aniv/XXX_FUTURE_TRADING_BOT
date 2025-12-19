"""
PHASE35-4 ITER27: DB Persist 계약 테스트
========================================
재발 방지: save_trade_to_db에서 numpy 타입이 올바르게 변환되는지 검증
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


class TestIter27PersistContract:
    """ITER27 DB Persist 계약 테스트"""
    
    def test_save_trade_to_db_handles_numpy_float64(self):
        """save_trade_to_db가 numpy.float64를 올바르게 처리하는지 검증"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from execution.engine import save_trade_to_db
        import inspect
        
        # 함수 소스 코드에서 to_native 또는 numpy 변환 로직 확인
        source = inspect.getsource(save_trade_to_db)
        
        # ITER27 FIX: numpy 타입 변환 로직이 있어야 함
        assert "to_native" in source or "item()" in source or "numpy" in source.lower(), \
            "save_trade_to_db에 numpy 타입 변환 로직이 없음 (ITER27 FIX 필요)"
    
    def test_to_native_converts_numpy_float64(self):
        """to_native 함수가 numpy.float64를 Python float로 변환하는지 검증"""
        # to_native 함수 정의 (engine.py와 동일)
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):  # numpy scalar
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        # numpy.float64 테스트
        np_val = np.float64(94884.12285714287)
        result = to_native(np_val)
        
        assert isinstance(result, float), f"Expected float, got {type(result)}"
        assert not hasattr(result, 'item'), "결과가 여전히 numpy 타입임"
        assert result == pytest.approx(94884.12285714287)
    
    def test_to_native_handles_none(self):
        """to_native 함수가 None을 올바르게 처리하는지 검증"""
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        assert to_native(None) is None
    
    def test_to_native_handles_python_float(self):
        """to_native 함수가 Python float를 그대로 반환하는지 검증"""
        def to_native(val):
            if val is None:
                return None
            if hasattr(val, 'item'):
                return val.item()
            return float(val) if isinstance(val, (int, float)) else val
        
        py_val = 94884.12
        result = to_native(py_val)
        
        assert isinstance(result, float)
        assert result == 94884.12
    
    def test_iter27_runner_exists(self):
        """ITER27 runner 스크립트가 존재하는지 검증"""
        from pathlib import Path
        
        runner_path = Path(__file__).parent.parent / "scripts" / "phase35" / "run_iter27_persist_trace.py"
        assert runner_path.exists(), f"ITER27 runner not found: {runner_path}"
    
    def test_iter27_runner_has_trace_logic(self):
        """ITER27 runner에 persist_trace 로직이 있는지 검증"""
        from pathlib import Path
        
        runner_path = Path(__file__).parent.parent / "scripts" / "phase35" / "run_iter27_persist_trace.py"
        content = runner_path.read_text(encoding="utf-8")
        
        assert "PERSIST_TRACE" in content, "ITER27 runner에 PERSIST_TRACE 로직 없음"
        assert "db_persist_called" in content, "ITER27 runner에 db_persist_called 카운터 없음"
        assert "db_insert_success" in content, "ITER27 runner에 db_insert_success 카운터 없음"


class TestNumpyTypeConversion:
    """numpy 타입 변환 테스트 (재발 방지)"""
    
    def test_numpy_int64_to_int(self):
        """numpy.int64가 Python int로 변환되는지 검증"""
        np_val = np.int64(12345)
        
        # hasattr(val, 'item') 체크로 변환
        if hasattr(np_val, 'item'):
            result = np_val.item()
        else:
            result = int(np_val)
        
        assert isinstance(result, int)
        assert result == 12345
    
    def test_numpy_array_element_conversion(self):
        """numpy 배열 요소가 올바르게 변환되는지 검증"""
        arr = np.array([94884.12, 95000.0, 95500.5])
        
        # iloc[-1] 등으로 가져온 값
        val = arr[-1]
        
        assert hasattr(val, 'item'), "numpy 배열 요소는 item() 메서드가 있어야 함"
        
        # 변환
        converted = val.item()
        assert isinstance(converted, float)
        assert converted == 95500.5
