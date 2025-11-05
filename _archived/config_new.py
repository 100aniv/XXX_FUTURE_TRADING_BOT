#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 설정 모듈 (Unified Config)
================================
config.yml + .env 통합 로더

사용법:
    from common.config import CFG
    
    print(CFG['mode'])  # 'paper'
    print(CFG['capital']['initial'])  # 10000
    print(CFG['strategy']['selector'])  # 'ensemble'
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# .env 로드 (비밀 정보)
load_dotenv()

from .logger import setup_logger

logger = setup_logger(__name__, log_type="application")


class Config:
    """통합 설정 클래스"""
    
    def __init__(self, config_path: str = "config.yml"):
        """
        설정 초기화
        
        Args:
            config_path: config.yml 경로
        """
        self._config = {}
        self._load(config_path)
        self._inject_env()
        self._validate()
    
    def _load(self, config_path: str):
        """YAML 파일 로드"""
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"❌ 설정 파일 없음: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        logger.info(f"✅ 설정 파일 로드: {config_path}")
    
    def _inject_env(self):
        """환경 변수 주입 (비밀 정보)"""
        # Database
        self._config['database'] = {
            'url': os.getenv('DATABASE_URL'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5433')),
            'name': os.getenv('DB_NAME', 'trading_db'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
        }
        
        # Binance API
        self._config['binance'] = {
            'api_key': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET'),
        }
        
        # Telegram
        if 'notifications' not in self._config:
            self._config['notifications'] = {}
        if 'telegram' not in self._config['notifications']:
            self._config['notifications']['telegram'] = {}
        
        self._config['notifications']['telegram']['token'] = os.getenv('TELEGRAM_TOKEN')
        self._config['notifications']['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
    
    def _validate(self):
        """설정 검증"""
        errors = []
        
        # 필수 필드 체크
        if not self._config.get('mode'):
            errors.append("❌ mode 필수")
        
        if self._config.get('mode') not in ['backtest', 'paper', 'live']:
            errors.append(f"❌ 유효하지 않은 mode: {self._config.get('mode')}")
        
        # Live 모드 API 키 체크
        if self._config.get('mode') == 'live':
            if not self._config['binance'].get('api_key'):
                errors.append("❌ Live 모드: BINANCE_API_KEY 필수")
            if not self._config['binance'].get('secret'):
                errors.append("❌ Live 모드: BINANCE_SECRET 필수")
        
        # 심볼 체크
        if not self._config.get('symbols', {}).get('list'):
            errors.append("❌ symbols.list 필수")
        
        # 리스크 체크
        risk_per_trade = self._config.get('risk', {}).get('per_trade', 0)
        if risk_per_trade <= 0 or risk_per_trade > 0.1:
            errors.append(f"❌ risk.per_trade는 0~10% 사이 (현재: {risk_per_trade*100:.2f}%)")
        
        # 에러 발생
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError(f"설정 검증 실패: {len(errors)}개 오류")
        
        logger.info("✅ 설정 검증 완료")
    
    def get(self, key: str, default=None):
        """설정 값 가져오기 (dict 스타일)"""
        return self._config.get(key, default)
    
    def __getitem__(self, key: str):
        """설정 값 가져오기 (dict 스타일)"""
        return self._config[key]
    
    def __contains__(self, key: str):
        """설정 포함 여부"""
        return key in self._config
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return self._config.copy()
    
    def print_summary(self):
        """설정 요약 출력"""
        logger.info("=" * 80)
        logger.info("📋 트레이딩 시스템 설정")
        logger.info("=" * 80)
        
        # 모드
        mode = self._config['mode']
        logger.info(f"🎯 모드: {mode.upper()}")
        
        # 전략
        strategy = self._config['strategy']['selector']
        logger.info(f"📊 전략: {strategy.upper()}")
        
        # 심볼
        symbols = self._config['symbols']['list']
        logger.info(f"💱 심볼: {', '.join(symbols)}")
        
        # 타임프레임
        timeframe = self._config['timeframe']
        logger.info(f"⏱️  타임프레임: {timeframe}")
        
        # 자본
        capital = self._config['capital']['initial']
        logger.info(f"💰 초기 자본: {capital:,.0f} USDT")
        
        # 리스크
        risk_per_trade = self._config['risk']['per_trade']
        logger.info(f"⚠️  거래당 리스크: {risk_per_trade*100:.2f}%")
        
        daily_loss = self._config['risk']['daily_loss_limit']
        logger.info(f"🚨 일일 손실 한도: {daily_loss*100:.1f}%")
        
        max_positions = self._config['risk']['max_positions']
        logger.info(f"📦 최대 포지션: {max_positions}개")
        
        # 필터
        logger.info("\n🔧 필터:")
        filters = self._config['filters']
        logger.info(f"   쿨다운: {filters['cooldown_candles']}캔들")
        logger.info(f"   거래량 스파이크: {'ON' if filters['volume_spike'] else 'OFF'}")
        logger.info(f"   레짐 필터: {'ON' if filters['regime_filter'] else 'OFF'}")
        logger.info(f"   MTF 확인: {'ON' if filters['mtf_confirm'] else 'OFF'}")
        
        # Flash Guard
        logger.info(f"\n⚡ Flash Guard: {'ON' if self._config['flash_guard']['enabled'] else 'OFF'}")
        
        # Telegram
        telegram_enabled = self._config['notifications']['telegram']['enabled']
        logger.info(f"📱 Telegram: {'ON' if telegram_enabled else 'OFF'}")
        
        logger.info("=" * 80)


# ============================================
# 싱글톤 인스턴스
# ============================================

# 전역 설정 객체 (앱 전체에서 사용)
CFG = None

def load_config(config_path: str = "config.yml") -> Config:
    """
    설정 로드 (싱글톤)
    
    Args:
        config_path: config.yml 경로
    
    Returns:
        Config: 설정 객체
    
    Examples:
        >>> from common.config import load_config, CFG
        >>> load_config()
        >>> print(CFG['mode'])
        'paper'
    """
    global CFG
    if CFG is None:
        CFG = Config(config_path)
        CFG.print_summary()
    return CFG


# ============================================
# 하위 호환성 (기존 코드용)
# ============================================

def get_bool(name: str, default: str = "false") -> bool:
    """환경변수를 boolean으로 (하위 호환)"""
    val = os.getenv(name, default).strip().lower()
    return val in ("1", "true", "yes", "y", "on")


def get_float(name: str, default: str) -> float:
    """환경변수를 float으로 (하위 호환)"""
    val = os.getenv(name, default).split('#')[0].strip()
    return float(val)


def get_int(name: str, default: str) -> int:
    """환경변수를 int로 (하위 호환)"""
    val = os.getenv(name, default).split('#')[0].strip()
    return int(val)


def get_str(name: str, default: str = "") -> str:
    """환경변수를 string으로 (하위 호환)"""
    return os.getenv(name, default).split('#')[0].strip()


# 앱 시작 시 자동 로드
if __name__ != "__main__":
    try:
        CFG = load_config()
    except FileNotFoundError:
        logger.warning("⚠️  config.yml 없음, 수동 로드 필요")
    except Exception as e:
        logger.error(f"❌ 설정 로드 실패: {e}")
