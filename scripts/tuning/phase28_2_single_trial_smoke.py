#!/usr/bin/env python3
"""
PHASE28-2: 단일 Trial 스모크 테스트

목적:
- 튜닝 클러스터를 사용하지 않고 단일 trial을 직접 실행
- Config SSOT 검증 및 "Trades = 0" 문제 추적
- 30일 backtest 실행 후 거래 발생 여부 확인

실행 방법:
    python scripts/tuning/phase28_2_single_trial_smoke.py
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from execution.engine import run_v2

logger = setup_logger(__name__, log_type="trading")


def load_base_config():
    """튜닝 base config 로드"""
    config_path = project_root / "configs" / "backtest" / "phase28_2_btc5m_tuning_base.yml"
    
    logger.info(f"📄 Loading base config: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"✅ Base config loaded")
    return config


def apply_test_params(config: dict) -> dict:
    """
    테스트용 파라미터 적용 (ParamSpace 중앙값 사용)
    
    이 파라미터들은 PHASE27-4 Grid Search Top 1 결과를 기반으로 한다.
    """
    test_params = {
        'rsi_long_threshold': 42,
        'rsi_short_threshold': 58,
        'bb_std_main': 1.2,
        'bb_std_strong': 1.5,
        'adx_trend_threshold': 20,
        'momentum_lookback': 5,
        'momentum_threshold': 0.001,
        'atr_mult_sl': 1.5,
        'rr': 1.5,
        'max_hold_minutes': 60,
    }
    
    logger.info("📊 Applying test parameters:")
    for key, value in test_params.items():
        logger.info(f"   {key}: {value}")
    
    # strategies.btc5m_baseline_v1에 적용
    if 'strategies' not in config:
        config['strategies'] = {}
    if 'btc5m_baseline_v1' not in config['strategies']:
        config['strategies']['btc5m_baseline_v1'] = {}
    
    for key, value in test_params.items():
        config['strategies']['btc5m_baseline_v1'][key] = value
    
    return config


def configure_test_run(config: dict) -> dict:
    """테스트 실행을 위한 config 설정"""
    # Run ID 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config['run_id'] = f"phase28_2_single_trial_smoke_{timestamp}"
    
    # Backtest 기간 (30일 전체)
    config['backtest']['start_date'] = "2024-11-30"
    config['backtest']['end_date'] = "2024-12-30"
    
    # TradeActivityTracker 활성화 (결과 확인용)
    config['trade_activity_tracker'] = {
        'enabled': True,
        'log_interval': 300,
        'output_file': f"reports/phase28_2_single_trial_smoke_{timestamp}.json"
    }
    
    logger.info(f"🆔 Run ID: {config['run_id']}")
    logger.info(f"📅 Period: {config['backtest']['start_date']} ~ {config['backtest']['end_date']}")
    
    return config


def validate_config(config: dict):
    """Config 필수 키 검증 (Worker와 동일한 로직)"""
    required_keys = {
        'timeframe': 'config["timeframe"]',
        'lookback': 'config["lookback"]',
        'equity': 'config["equity"]',
        'capital.initial': 'config["capital"]["initial"]',
        'risk.per_trade': 'config["risk"]["per_trade"]',
        'risk.max_positions': 'config["risk"]["max_positions"]',
        'position_sizing.quality_weight_min': 'config["position_sizing"]["quality_weight_min"]',
        'position_sizing.quality_weight_max': 'config["position_sizing"]["quality_weight_max"]',
        'position_sizing.min_position_value': 'config["position_sizing"]["min_position_value"]',
        'position_sizing.max_position_value': 'config["position_sizing"]["max_position_value"]',
        'portfolio.max_symbol_exposure_pct': 'config["portfolio"]["max_symbol_exposure_pct"]',
        'portfolio.max_exposure_pct': 'config["portfolio"]["max_exposure_pct"]',
    }
    
    missing_keys = []
    
    for key_path, config_ref in required_keys.items():
        parts = key_path.split('.')
        value = config
        try:
            for part in parts:
                value = value[part]
        except (KeyError, TypeError):
            missing_keys.append(f"  - {key_path} ({config_ref})")
    
    if missing_keys:
        error_msg = (
            "❌ Config 필수 키 누락!\n"
            "누락된 키:\n" + "\n".join(missing_keys)
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("✅ Config validation passed")


def run_smoke_test():
    """스모크 테스트 실행"""
    logger.info("=" * 80)
    logger.info("PHASE28-2: 단일 Trial 스모크 테스트")
    logger.info("=" * 80)
    
    try:
        # 1. Base config 로드
        config = load_base_config()
        
        # 2. 테스트 파라미터 적용
        config = apply_test_params(config)
        
        # 3. 테스트 실행 설정
        config = configure_test_run(config)
        
        # 4. Config 검증
        validate_config(config)
        
        # 5. 엔진 실행
        logger.info("=" * 80)
        logger.info("🚀 Engine 실행 시작")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        run_v2(
            mode='backtest',
            config=config,
            clean_state=True
        )
        
        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info(f"✅ Engine 실행 완료 (소요 시간: {runtime:.1f}초)")
        logger.info("=" * 80)
        
        # 6. 결과 확인
        logger.info("\n📊 결과 확인:")
        logger.info(f"   - TradeActivityTracker 출력: {config['trade_activity_tracker']['output_file']}")
        logger.info(f"   - DB 조회: trading.trades 테이블 (run_id={config['run_id']})")
        
        # 7. DB에서 거래 수 확인
        from database import get_db_connection
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*), 
                           SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) as closed_count,
                           SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as win_count
                    FROM trading.trades
                    WHERE mode='backtest'
                """)
                result = cur.fetchone()
                
                total_trades = result[0] or 0
                closed_trades = result[1] or 0
                win_trades = result[2] or 0
                
                logger.info(f"\n📈 DB 거래 통계 (최근 1000건):")
                logger.info(f"   - 총 거래: {total_trades}")
                logger.info(f"   - 완료된 거래: {closed_trades}")
                logger.info(f"   - 승리: {win_trades}")
                
                if closed_trades == 0:
                    logger.warning("⚠️  WARNING: 완료된 거래가 0건입니다!")
                    logger.warning("   원인 분석 필요:")
                    logger.warning("   1. 신호 생성 문제 (전략 파라미터)")
                    logger.warning("   2. Risk/Portfolio Guard 문제")
                    logger.warning("   3. FlowGuardian 과도한 차단")
                else:
                    logger.info(f"✅ 거래 발생 확인: {closed_trades}건")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ 스모크 테스트 완료")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 스모크 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
