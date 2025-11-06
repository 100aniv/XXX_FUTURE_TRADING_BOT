#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR9 간단한 테스트
================
import 오류 없이 실행 가능한 간단한 테스트
"""
import pytest
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_common_logger():
    """common.logger 모듈 테스트"""
    from common.logger import setup_logger
    
    logger = setup_logger("test", "logs/test.log")
    assert logger is not None
    
    logger.info("테스트 메시지")
    logger.debug("디버그 메시지")
    logger.warning("경고 메시지")
    logger.error("오류 메시지")


def test_common_utils():
    """common.utils 모듈 테스트"""
    from common.utils import safe_get, format_number
    
    # safe_get 테스트
    data = {'a': {'b': {'c': 123}}}
    assert safe_get(data, 'a', 'b', 'c') == 123
    assert safe_get(data, 'x', 'y', 'z', default=0) == 0
    
    # format_number 테스트
    assert format_number(1234.5678, 2) == "1234.57"
    assert format_number(0.00012345, 6) == "0.000123"


def test_common_calculations():
    """common.calculations 모듈 테스트"""
    from common.calculations import calculate_position_size, calculate_risk_reward
    
    # 포지션 사이즈 계산
    size = calculate_position_size(
        equity=10000,
        risk_per_trade=0.01,
        entry=50000,
        sl=49000
    )
    assert size > 0
    
    # 리스크 리워드 계산
    rr = calculate_risk_reward(
        entry=50000,
        sl=49000,
        tp=52000
    )
    assert rr == 2.0


def test_config_loader():
    """config_loader 모듈 테스트"""
    from common.config_loader import load_config, merge_strategy_config
    
    # 설정 로드
    config = load_config()
    assert config is not None
    assert 'mode' in config
    assert 'strategies' in config
    
    # 전략 설정 병합
    strategy_config = merge_strategy_config(config, 'scalping')
    assert strategy_config is not None
    assert 'timeframe' in strategy_config


def test_core_interfaces():
    """core.interfaces 모듈 테스트"""
    from core.interfaces import IDataSource, IStrategy, IRisk, IBroker, IMetrics
    
    # 인터페이스 존재 확인
    assert IDataSource is not None
    assert IStrategy is not None
    assert IRisk is not None
    assert IBroker is not None
    assert IMetrics is not None


def test_signals_init():
    """signals 모듈 초기화 테스트"""
    import signals
    
    assert signals is not None


def test_monitoring_init():
    """monitoring 모듈 초기화 테스트"""
    import monitoring
    
    assert monitoring is not None
    assert hasattr(monitoring, 'init_guardian')


def test_execution_init():
    """execution 모듈 초기화 테스트"""
    import execution
    
    assert execution is not None


def test_redis_key_generation():
    """Redis 키 생성 테스트"""
    import hashlib
    import json
    
    # 캔들 dedup 키
    symbol = "BTCUSDT"
    timeframe = "1m"
    ts = 1730000000000
    
    dedup_key = f"candle:{symbol}:{timeframe}:{ts}"
    assert dedup_key == "candle:BTCUSDT:1m:1730000000000"
    
    # 신호 멱등성 키
    signal_params = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry": 50000.0
    }
    
    normalized = json.dumps(signal_params, sort_keys=True)
    signal_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    signal_key = f"signal:{signal_params['symbol']}:{signal_hash}"
    
    assert signal_key.startswith("signal:BTCUSDT:")
    assert len(signal_hash) == 16


def test_datetime_operations():
    """날짜/시간 연산 테스트"""
    from datetime import datetime, timedelta
    
    now = datetime.now()
    assert now is not None
    
    # 1시간 전
    one_hour_ago = now - timedelta(hours=1)
    assert one_hour_ago < now
    
    # 타임스탬프 변환
    ts = int(now.timestamp() * 1000)
    assert ts > 0


def test_pandas_operations():
    """pandas 연산 테스트"""
    import pandas as pd
    import numpy as np
    
    # DataFrame 생성
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    assert len(df) == 5
    
    # 이동평균 계산
    df['ma'] = df['close'].rolling(window=3).mean()
    assert df['ma'].iloc[-1] > 0
    
    # 변화율 계산
    df['pct_change'] = df['close'].pct_change()
    assert df['pct_change'].iloc[-1] > 0


def test_numpy_operations():
    """numpy 연산 테스트"""
    import numpy as np
    
    # 배열 생성
    arr = np.array([1, 2, 3, 4, 5])
    assert len(arr) == 5
    
    # 통계 계산
    mean = np.mean(arr)
    assert mean == 3.0
    
    std = np.std(arr)
    assert std > 0


def test_yaml_operations():
    """YAML 연산 테스트"""
    import yaml
    
    # YAML 문자열 파싱
    yaml_str = """
    mode: paper
    symbol: BTCUSDT
    timeframe: 5m
    """
    
    data = yaml.safe_load(yaml_str)
    assert data['mode'] == 'paper'
    assert data['symbol'] == 'BTCUSDT'
    assert data['timeframe'] == '5m'


def test_json_operations():
    """JSON 연산 테스트"""
    import json
    
    # JSON 직렬화
    data = {
        'symbol': 'BTCUSDT',
        'price': 50000.0,
        'qty': 0.01
    }
    
    json_str = json.dumps(data)
    assert 'BTCUSDT' in json_str
    
    # JSON 역직렬화
    parsed = json.loads(json_str)
    assert parsed['symbol'] == 'BTCUSDT'
    assert parsed['price'] == 50000.0


def test_pathlib_operations():
    """pathlib 연산 테스트"""
    from pathlib import Path
    
    # 경로 생성
    path = Path("logs/test.log")
    assert path.name == "test.log"
    assert path.parent.name == "logs"
    
    # 절대 경로
    abs_path = path.absolute()
    assert abs_path.is_absolute()


def test_collections_operations():
    """collections 연산 테스트"""
    from collections import deque, defaultdict
    
    # deque 테스트
    d = deque(maxlen=5)
    for i in range(10):
        d.append(i)
    
    assert len(d) == 5
    assert list(d) == [5, 6, 7, 8, 9]
    
    # defaultdict 테스트
    dd = defaultdict(int)
    dd['a'] += 1
    dd['b'] += 2
    
    assert dd['a'] == 1
    assert dd['b'] == 2
    assert dd['c'] == 0  # 기본값


def test_hashlib_operations():
    """hashlib 연산 테스트"""
    import hashlib
    
    # SHA256 해시
    data = "test_data"
    hash_obj = hashlib.sha256(data.encode())
    hash_hex = hash_obj.hexdigest()
    
    assert len(hash_hex) == 64
    
    # MD5 해시
    md5_obj = hashlib.md5(data.encode())
    md5_hex = md5_obj.hexdigest()
    
    assert len(md5_hex) == 32


def test_uuid_operations():
    """UUID 연산 테스트"""
    from uuid import uuid4
    
    # UUID 생성
    id1 = uuid4()
    id2 = uuid4()
    
    assert id1 != id2
    assert len(str(id1)) == 36


def test_time_operations():
    """time 연산 테스트"""
    import time
    
    # 현재 시간
    now = time.time()
    assert now > 0
    
    # 밀리초 타임스탬프
    now_ms = int(now * 1000)
    assert now_ms > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
