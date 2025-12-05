#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 설정 모듈
==============
환경변수 기반 설정 로드 및 검증

⚠️  리팩토링 완료 (2025-10-19)
- 옛날 signal bot 기준 → execution 모듈 기준으로 변경

⚠️  리팩토링 완료 (2025-10-28)
- config_merge.py, config_merger.py 통합
- 모든 설정 관련 기능을 config.py에서 관리
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from copy import deepcopy
from dotenv import load_dotenv

# .env 로드
load_dotenv()

from .logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ============================================
# 환경변수 파싱 헬퍼
# ============================================

def get_bool(name: str, default: str = "false") -> bool:
    """
    환경변수를 boolean으로 파싱
    
    Args:
        name: 환경변수 이름
        default: 기본값
    
    Returns:
        bool: 파싱된 값
    """
    val = os.getenv(name, default).strip().lower()
    return val in ("1", "true", "yes", "y", "on")


def get_float(name: str, default: str) -> float:
    """
    환경변수를 float으로 파싱 (주석 제거)
    
    Args:
        name: 환경변수 이름
        default: 기본값
    
    Returns:
        float: 파싱된 값
    """
    val = os.getenv(name, default).split('#')[0].strip()
    return float(val)


def get_int(name: str, default: str) -> int:
    """
    환경변수를 int로 파싱 (주석 제거)
    
    Args:
        name: 환경변수 이름
        default: 기본값
    
    Returns:
        int: 파싱된 값
    """
    val = os.getenv(name, default).split('#')[0].strip()
    return int(val)


def get_str(name: str, default: str = "") -> str:
    """
    환경변수를 string으로 파싱 (주석 제거)
    
    Args:
        name: 환경변수 이름
        default: 기본값
    
    Returns:
        str: 파싱된 값
    """
    return os.getenv(name, default).split('#')[0].strip()


def get_list(name: str, default: str = "", separator: str = ",") -> List[str]:
    """
    환경변수를 리스트로 파싱
    
    Args:
        name: 환경변수 이름
        default: 기본값
        separator: 구분자
    
    Returns:
        List[str]: 파싱된 리스트
    """
    val = get_str(name, default)
    return [s.strip().upper() for s in val.split(separator) if s.strip()]


# ============================================
# 설정 로드
# ============================================

def load_yaml_config(config_path: str = "config.yml") -> Dict[str, Any]:
    """
    config.yml에서 설정 로드 (우선순위 1)
    환경변수 치환 지원: ${VAR_NAME}
    
    Args:
        config_path: config.yml 경로
    
    Returns:
        Dict[str, Any]: 설정 딕셔너리
    """
    path = Path(config_path)
    
    if not path.exists():
        logger.warning(f"⚠️ {config_path} 없음, 환경변수 사용")
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 환경변수 치환: ${VAR_NAME} → 환경변수 값
    import re
    def replace_env_var(match):
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))
    
    content = re.sub(r'\$\{([A-Z_]+)\}', replace_env_var, content)
    
    config = yaml.safe_load(content)
    
    logger.info(f"✅ {config_path} 로드 완료 (환경변수 치환 적용)")
    return config


def load_config() -> Dict[str, Any]:
    """
    통합 설정 로드 (config.yml 우선, 환경변수 fallback)
    
    Returns:
        Dict[str, Any]: 설정 딕셔너리
        
    Examples:
        >>> CFG = load_config()
        >>> print(CFG['strategy']['selector'])
        'ensemble'
    """
    # 1. config.yml 로드 (우선순위)
    #    CONFIG_PATH 환경변수로 대체 경로를 허용 (백테스트 튜너용 비침투 오버레이)
    config_path = os.getenv('CONFIG_PATH', 'config.yml')
    yaml_config = load_yaml_config(config_path)

    # 1-a. CONFIG_PATH가 지정되었지만 파일이 없거나 비어있을 경우, 기본 config.yml 재시도
    if (not yaml_config) and config_path != 'config.yml':
        logger.warning(f"⚠️ CONFIG_PATH='{config_path}' 유효한 설정 아님, 기본 config.yml로 재시도")
        yaml_config = load_yaml_config('config.yml')

    if yaml_config:
        # YAML 설정을 반환 (베이지안 튜닝 결과 보존)
        # CONFIG_PATH로 active.yml 로드 시 튜닝 결과를 ENV가 덮어쓰면 안 됨
        
        # TRADING_MODE만 ENV 오버레이 허용 (paper/live/backtest 모드 전환용)
        env_mode = os.getenv('TRADING_MODE', '').strip()
        if env_mode:
            yaml_config['mode'] = env_mode
        
        logger.info(f"✅ 설정 로드 ({config_path if config_path else 'config.yml'}): mode={yaml_config.get('mode', 'unknown')}")
        return yaml_config

    # 2. 환경변수 fallback (하위 호환)
    logger.warning("⚠️ config.yml 없음, 환경변수 사용 (deprecated)")
    config = {
        # ============================================
        # 실행 설정 (execution 모듈)
        # ============================================
        "strategy_selector": get_str("STRATEGY_SELECTOR", "ensemble"),  # ensemble | trend | reversion | breakout | scalping | daytrade | swing
        "trading_mode": get_str("TRADING_MODE", "paper"),  # backtest | paper | live
        
        # 백테스트 설정
        "backtest_start_date": get_str("BACKTEST_START_DATE", "2024-07-01"),
        "backtest_end_date": get_str("BACKTEST_END_DATE", "2024-10-17"),
        
        # ============================================
        # 기본 설정 (collector, signals)
        # ============================================
        "symbols": get_list("SYMBOLS", ""),  # 빈 값이면 REST API로 자동 로드
        "symbol_mode": get_str("SYMBOL_MODE", "top50"),  # all | top50 | top100 | manual
        "timeframe": get_str("TIMEFRAME", "5m"),
        "lookback": get_int("LOOKBACK", "400"),
        
        # ============================================
        # 리스크 관리 (execution/position_sizer, risk_manager)
        # ============================================
        "equity_usdt": get_float("EQUITY_USDT", "10000"),
        "risk_per_trade": get_float("RISK_PER_TRADE", "0.01"),  # 1%
        
        # 포지션 사이징
        "quality_weight_min": get_float("QUALITY_WEIGHT_MIN", "0.7"),
        "quality_weight_max": get_float("QUALITY_WEIGHT_MAX", "1.3"),
        "max_position_value": get_float("MAX_POSITION_VALUE", "5000"),
        "min_position_value": get_float("MIN_POSITION_VALUE", "10"),
        
        # 리스크 한도
        "daily_loss_limit_pct": get_float("DAILY_LOSS_LIMIT_PCT", "0.03"),  # 3%
        "max_concurrent_positions": get_int("MAX_CONCURRENT_POSITIONS", "5"),
        "max_exposure_per_symbol_pct": get_float("MAX_EXPOSURE_PER_SYMBOL_PCT", "0.3"),  # 30%
        
        # ============================================
        # 전략 파라미터 (strategies/ 모듈)
        # ============================================
        "rr": get_float("RR", "1.8"),
        "atr_mult_sl": get_float("ATR_MULT_SL", "1.2"),
        "atr_mult_trail": get_float("ATR_MULT_TRAIL", "1.2"),
        "max_leverage": get_int("MAX_LEVERAGE", "10"),
        "min_leverage": get_int("MIN_LEVERAGE", "2"),
        
        # ============================================
        # 텔레그램 알림 (선택적)
        # ============================================
        "telegram_token": get_str("TELEGRAM_TOKEN", ""),
        "telegram_chat_id": get_str("TELEGRAM_CHAT_ID", ""),
        "enable_telegram": get_bool("ENABLE_TELEGRAM", "false"),
        "system_name": get_str("SYSTEM_NAME", "TRADING"),  # 메시지 prefix
        
        # ============================================
        # 쿨다운 (신호 생성)
        # ============================================
        "cooldown_candles": get_int("COOLDOWN_CANDLES", "3"),
        
        # ============================================
        # TP/SL 트레일링 (execution/position_tracker)
        # ============================================
        "enable_tp_trail": get_bool("ENABLE_TP_TRAIL", "true"),
        "tp1_rr": get_float("TP1_RR", "1.0"),
        "tp2_rr": get_float("TP2_RR", "2.0"),
        "trail_after_tp1": get_bool("TRAIL_AFTER_TP1", "true"),
        
        # ============================================
        # 시장 레짐 (신호 생성)
        # ============================================
        "enable_regime_alert": get_bool("ENABLE_REGIME_ALERT", "true"),
        
        # ============================================
        # 거래량 스파이크 필터 (신호 생성)
        # ============================================
        "enable_vol_spike_filter": get_bool("ENABLE_VOL_SPIKE_FILTER", "true"),
        "vol_spike_mult": get_float("VOL_SPIKE_MULT", "2.0"),
        "vol_ma_len": get_int("VOL_MA_LEN", "30"),
        
        # ============================================
        # 멀티 타임프레임 확인 (신호 생성)
        # ============================================
        "enable_mtf_confirm": get_bool("ENABLE_MTF_CONFIRM", "true"),
        "htf": get_str("HTF", "1h"),
        "require_htf_aligned": get_bool("REQUIRE_HTF_ALIGNED", "true"),
        
        # 목표 추적
        "enable_goal_tracker": get_bool("ENABLE_GOAL_TRACKER", "true"),
        "daily_goal_pct": get_float("DAILY_GOAL_PCT", "0.10"),
        
        # ============================================
        # Flash Guard (execution/risk_manager)
        # ============================================
        "enable_flash_guard": get_bool("ENABLE_FLASH_GUARD", "true"),
        "flash_window_sec": get_int("FLASH_WINDOW_SEC", "60"),
        "flash_pct": get_float("FLASH_PCT", "0.03"),
        "flash_pause_candles": get_int("FLASH_PAUSE_CANDLES", "3"),
        
        # ============================================
        # Binance API (live 모드)
        # ============================================
        "binance_api_key": get_str("BINANCE_API_KEY", ""),
        "binance_secret": get_str("BINANCE_SECRET", ""),
        
        # ============================================
        # 기타
        # ============================================
        "poll_interval_sec": get_int("POLL_INTERVAL_SEC", "5"),
    }
    
    logger.info(f"✅ 설정 로드 완료: {config['strategy_selector']}/{config['trading_mode']}, 심볼={', '.join(config['symbols']) if config['symbols'] else '(자동 로드)'}, 타임프레임={config['timeframe']}, 자본금={config['equity_usdt']:,.0f} USDT, 거래당 리스크={config['risk_per_trade']*100:.2f}%")
    
    return config


def load_backtest_config():
    """
    백테스트 설정 로드 (data/backtest_config.yaml)
    
    Returns:
        dict: 백테스트 설정
    """
    config_path = Path('data/backtest_config.yaml')
    
    if not config_path.exists():
        logger.warning(f"⚠️ {config_path} 없음, 기본값 사용")
        return {
            'periods': {
                'one_year': {'start_date': '2024-01-01', 'end_date': '2024-12-31'},
                'ten_years': {'start_date': '2015-01-01', 'end_date': '2024-12-31'},
            },
            'symbols': ['BTCUSDT'],
            'timeframes': ['5m', '15m', '1h', '4h'],
            'initial_capital': 10000,
            'fee_rate': 0.0004,
            'slippage_pct': 0.0005,
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    설정 검증
    
    Args:
        config: 설정 딕셔너리
    
    Returns:
        bool: 검증 성공 여부
        
    Raises:
        ValueError: 설정이 유효하지 않을 때
    """
    errors = []
    
    # 필수 필드 체크
    required_fields = ["strategy_selector", "trading_mode", "symbols", "timeframe"]
    for field in required_fields:
        if not config.get(field):
            errors.append(f"❌ 필수 필드 누락: {field}")
    
    # 전략 선택 체크
    valid_strategies = ["ensemble", "trend", "reversion", "breakout", "scalping", "daytrade", "swing"]
    if config.get("strategy_selector") not in valid_strategies:
        errors.append(f"❌ 유효하지 않은 전략: {config.get('strategy_selector')} (가능: {', '.join(valid_strategies)})")
    
    # 거래 모드 체크
    valid_modes = ["backtest", "paper", "live"]
    if config.get("trading_mode") not in valid_modes:
        errors.append(f"❌ 유효하지 않은 모드: {config.get('trading_mode')} (가능: {', '.join(valid_modes)})")
    
    # 심볼 체크
    if not config.get("symbols"):
        errors.append("❌ 심볼이 비어있습니다")
    
    # RR 체크
    if config.get("rr", 0) <= 0:
        errors.append("❌ RR은 0보다 커야 합니다")
    
    # 리스크 체크
    risk = config.get("risk_per_trade", 0)
    if risk <= 0 or risk > 0.1:
        errors.append(f"❌ 리스크는 0~10% 사이여야 합니다 (현재: {risk*100:.2f}%)")
    
    # 레버리지 체크
    min_lev = config.get("min_leverage", 0)
    max_lev = config.get("max_leverage", 0)
    if min_lev <= 0 or max_lev <= 0:
        errors.append("❌ 레버리지는 0보다 커야 합니다")
    if min_lev > max_lev:
        errors.append(f"❌ min_leverage({min_lev}) > max_leverage({max_lev})")
    
    # Live 모드 API 키 체크
    if config.get("trading_mode") == "live":
        if not config.get("binance_api_key") or not config.get("binance_secret"):
            errors.append("❌ Live 모드는 BINANCE_API_KEY, BINANCE_SECRET 필수")
    
    # 텔레그램 체크 (경고만)
    if config.get("enable_telegram"):
        if not config.get("telegram_token") or not config.get("telegram_chat_id"):
            logger.warning("⚠️  텔레그램 활성화되었으나 토큰/채팅ID 미설정")
    
    # 에러가 있으면 로그 출력 및 예외 발생
    if errors:
        for error in errors:
            logger.error(error)
        raise ValueError(f"설정 검증 실패: {len(errors)}개 오류")
    
    logger.info("✅ 설정 검증 성공")
    return True


# ============================================
# 편의 함수
# ============================================

def print_config(config: Dict[str, Any]) -> None:
    """
    설정을 보기 좋게 출력
    
    Args:
        config: 설정 딕셔너리
    """
    logger.info("=" * 60)
    logger.info("📋 봇 설정")
    logger.info("=" * 60)
    
    logger.info(f"📊 전략: {config['strategy_selector']}")
    logger.info(f"🎯 모드: {config['trading_mode']}")
    logger.info(f"💱 심볼: {', '.join(config['symbols'])}")
    logger.info(f"⏱️  타임프레임: {config['timeframe']}")
    logger.info(f"💰 자본금: {config['equity_usdt']:,.0f} USDT")
    logger.info(f"⚠️  거래당 리스크: {config['risk_per_trade']*100:.2f}%")
    logger.info(f"📦 최대 포지션: {config['max_concurrent_positions']}개")
    logger.info(f"🚨 일일 손실 한도: {config['daily_loss_limit_pct']*100:.1f}%")
    logger.info(f"🔧 고급 옵션: TP 트레일링={'ON' if config['enable_tp_trail'] else 'OFF'}, Flash Guard={'ON' if config['enable_flash_guard'] else 'OFF'}, MTF 확인={'ON' if config['enable_mtf_confirm'] else 'OFF'}, 텔레그램={'ON' if config.get('enable_telegram') else 'OFF'}")
    
    logger.info("=" * 60)


# ============================================
# 설정 병합 (전략별 설정 통합)
# ============================================

def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any], list_policy: str = 'replace') -> Dict[str, Any]:
    """
    Dict deep merge. overlay가 우선.
    
    Args:
        base: 기본 딕셔너리
        overlay: 병합할 딕셔너리 (우선순위 높음)
        list_policy: 리스트 병합 정책 ('replace' 또는 'append')
    
    Returns:
        병합된 딕셔너리
    
    Examples:
        >>> base = {'a': 1, 'b': {'c': 2}}
        >>> overlay = {'b': {'d': 3}, 'e': 4}
        >>> deep_merge(base, overlay)
        {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}
    """
    if base is None:
        base = {}
    if overlay is None:
        return base

    out: Dict[str, Any] = dict(base)

    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v, list_policy=list_policy)
        elif isinstance(v, (list, tuple)):
            if list_policy == 'replace' or not isinstance(out.get(k), (list, tuple)):
                out[k] = list(v)
            else:
                # append unique (미사용 기본)
                existing = list(out.get(k, []))
                out[k] = existing + [x for x in v if x not in existing]
        else:
            out[k] = v
    return out


def merge_strategy_config(base_config: Dict[str, Any], strategy_id: str) -> Dict[str, Any]:
    """
    전략별 설정을 base_config에 병합
    
    Args:
        base_config: 전체 config (CFG)
        strategy_id: 전략 ID (scalping, daytrade, trend, reversion, breakout, swing)
    
    Returns:
        병합된 config (lookback, timeframe, 전략 설정 포함)
    
    Examples:
        >>> CFG = load_config()
        >>> merged = merge_strategy_config(CFG, 'scalping')
        >>> print(merged['lookback'])  # 100
        >>> print(merged['timeframe'])  # 3m
    """
    # Deep copy로 원본 보호
    merged = deepcopy(base_config)
    
    # 전략별 설정 가져오기
    strategies = base_config.get('strategies', {})
    strategy_cfg = strategies.get(strategy_id, {})
    
    if not strategy_cfg:
        raise ValueError(f"Strategy '{strategy_id}' not found in config")
    
    # ✅ 1. 전략별 timeframe (전략 우선)
    if 'timeframe' in strategy_cfg:
        merged['timeframe'] = strategy_cfg['timeframe']
    elif 'timeframe' not in merged:
        merged['timeframe'] = '5m'  # 기본값
    
    # ✅ 2. lookback (base에서 유지)
    if 'lookback' not in merged:
        merged['lookback'] = 100  # 기본값
    
    # ✅ 3. min_bars_for_signal (전략 우선)
    if 'min_bars_for_signal' in strategy_cfg:
        merged['min_bars_for_signal'] = strategy_cfg['min_bars_for_signal']
    elif 'min_bars_for_signal' not in merged:
        merged['min_bars_for_signal'] = 50  # 기본값
    
    # ✅ 4. 전략별 필터 설정 병합
    strat_filters = strategy_cfg.get('filters', {})
    
    # MTF 확인
    if 'mtf_confirm' in strat_filters:
        merged['enable_mtf_confirm'] = bool(strat_filters['mtf_confirm'])
    
    # 거래량 필터
    if 'volume_ratio_min' in strat_filters:
        merged['volume_ratio_min'] = float(strat_filters['volume_ratio_min'])
    
    # 레짐 필터
    if 'regime' in strat_filters:
        merged['enable_regime_filter'] = bool(strat_filters['regime'])
    
    # ✅ 5. 쿨다운
    if 'cooldown_candles' in strategy_cfg:
        merged['cooldown_candles'] = int(strategy_cfg['cooldown_candles'])
    
    # ✅ 6. 전략 설정 전체 저장 (하위 모듈이 직접 접근할 수 있도록)
    merged['strategy_config'] = strategy_cfg
    merged['strategy_id'] = strategy_id
    
    # ✅ 7. 지표 파라미터 (전략 우선)
    indicators = strategy_cfg.get('indicators', {})
    for key, value in indicators.items():
        merged[key] = value
    
    # ✅ 8. PHASE28-1-FIX: 전략 파라미터를 top-level로 복사
    #    전략 코드가 config.get('rsi_long_threshold', default)처럼 직접 읽으므로
    #    strategy_cfg의 모든 키를 top-level로 복사 (nested dict 제외)
    for key, value in strategy_cfg.items():
        # filters, leverage 같은 nested dict는 제외
        if not isinstance(value, dict):
            merged[key] = value
    
    return merged


# ============================================
# PHASE8: Config 병합 및 스냅샷 (재현성)
# ============================================

def load_config_with_mode(mode: str = None, base_path: str = "configs/base.yml") -> Dict[str, Any]:
    """
    PHASE8: 병합 순서에 따른 설정 로드
    
    병합 순서 (우선순위):
        1. configs/base.yml
        2. configs/modes/{mode}.yml (mode 지정 시)
        3. configs/active/current.yml
        4. CLI/ENV (TRADING_MODE, CONFIG_PATH 등)
    
    Args:
        mode: 모드 이름 (backtest_clean, paper, live 등)
        base_path: base.yml 경로
    
    Returns:
        Dict[str, Any]: 병합된 설정 딕셔너리
    
    Examples:
        >>> cfg = load_config_with_mode(mode='backtest_clean')
        >>> print(cfg['execution']['fill_policy'])
        'next_open'
    """
    # 1. base.yml 로드
    base_cfg = {}
    if Path(base_path).exists():
        with open(base_path, 'r', encoding='utf-8') as f:
            base_cfg = yaml.safe_load(f) or {}
        logger.info(f"✅ [1/4] base.yml 로드 완료")
    else:
        logger.warning(f"⚠️  base.yml 없음: {base_path}")
    
    # 2. modes/{mode}.yml 로드 및 병합 (mode 지정 시)
    if mode:
        mode_path = Path(f"configs/modes/{mode}.yml")
        if mode_path.exists():
            with open(mode_path, 'r', encoding='utf-8') as f:
                mode_cfg = yaml.safe_load(f) or {}
            base_cfg = deep_merge(base_cfg, mode_cfg)
            logger.info(f"✅ [2/4] modes/{mode}.yml 병합 완료")
        else:
            logger.warning(f"⚠️  modes/{mode}.yml 없음")
    else:
        logger.info(f"ℹ️  [2/4] mode 미지정, 건너뜀")
    
    # 3. active/current.yml 로드 및 병합
    active_path = Path("configs/active/current.yml")
    if active_path.exists():
        with open(active_path, 'r', encoding='utf-8') as f:
            active_cfg = yaml.safe_load(f) or {}
        base_cfg = deep_merge(base_cfg, active_cfg)
        logger.info(f"✅ [3/4] active/current.yml 병합 완료")
    else:
        logger.info(f"ℹ️  [3/4] active/current.yml 없음, 건너뜀")
    
    # 4. CLI/ENV 오버라이드
    env_mode = os.getenv('TRADING_MODE', '').strip()
    if env_mode:
        base_cfg['mode'] = env_mode
        logger.info(f"✅ [4/4] ENV 오버라이드: mode={env_mode}")
    else:
        logger.info(f"ℹ️  [4/4] ENV 오버라이드 없음")
    
    # mode 기본값 설정
    if 'mode' not in base_cfg and mode:
        base_cfg['mode'] = mode
    
    return base_cfg


def generate_run_id() -> str:
    """
    PHASE8: run_id 생성 (YYYYMMDD_HHMMSS_random4)
    
    Returns:
        str: run_id (예: 20251114_135030_a7f3)
    
    Examples:
        >>> run_id = generate_run_id()
        >>> print(run_id)
        '20251114_135030_a7f3'
    """
    import datetime
    import random
    import string
    
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    return f"{timestamp}_{random_suffix}"


def save_effective_config(cfg: Dict[str, Any], env: str, run_id: str) -> Path:
    """
    PHASE8: effective_config.yml 스냅샷 저장
    
    Args:
        cfg: 병합된 설정 딕셔너리
        env: 환경 이름 (backtest_clean, paper, live)
        run_id: 실행 ID
    
    Returns:
        Path: 저장된 파일 경로
    
    Examples:
        >>> cfg = load_config_with_mode('backtest_clean')
        >>> run_id = generate_run_id()
        >>> path = save_effective_config(cfg, 'backtest_clean', run_id)
        >>> print(path)
        artifacts/backtest_clean/20251114_135030_a7f3/effective_config.yml
    """
    # artifacts 디렉토리 생성
    artifacts_dir = Path(f"artifacts/{env}/{run_id}")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # ⭐ PHASE18-3: runtime_context는 직렬화 불가 (threading.Event 포함)
    cfg_snapshot = {k: v for k, v in cfg.items() if k != 'runtime_context'}
    
    # effective_config.yml 저장
    config_path = artifacts_dir / "effective_config.yml"
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg_snapshot, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    logger.info(f"✅ [SNAPSHOT] effective_config.yml 저장: {config_path}")
    
    return config_path


def load_universe_config(config: Dict[str, Any]) -> Any:
    """
    PHASE26-0: Universe Provider 설정 로딩
    
    Args:
        config: 전체 config dict
    
    Returns:
        UniverseProviderConfig or None (universe.enabled=false일 때)
    
    Examples:
        >>> config = load_config_with_mode('paper')
        >>> universe_cfg = load_universe_config(config)
        >>> if universe_cfg:
        ...     provider = create_universe_provider(universe_cfg)
        ...     universe = await provider.get_universe()
    """
    from common.universe_provider import (
        UniverseProviderConfig,
        UniverseFilterConfig
    )
    
    universe_cfg = config.get('universe', {})
    
    # universe.enabled가 false이거나 없으면 None 반환
    if not universe_cfg.get('enabled', False):
        return None
    
    provider_cfg = universe_cfg.get('provider', {})
    filters_cfg = universe_cfg.get('filters', {})
    
    # UniverseProviderConfig 생성
    return UniverseProviderConfig(
        provider_type=provider_cfg.get('type', 'static'),
        top_n=provider_cfg.get('top_n', 10),
        filters=UniverseFilterConfig(
            quote_assets=filters_cfg.get('quote_assets', ['USDT']),
            exclude_symbols=filters_cfg.get('exclude_symbols', []),
            min_24h_volume_usd=filters_cfg.get('min_24h_volume_usd', 0.0),
            market_types=filters_cfg.get('market_types', ['PERPETUAL']),
            contract_status=filters_cfg.get('contract_status', 'TRADING')
        ),
        static_symbols=provider_cfg.get('static_symbols', []),
        cache_ttl_sec=provider_cfg.get('cache_ttl_sec', 3600)
    )
