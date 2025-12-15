#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35-2 ITER5.5: Config Preflight & Provenance
=================================================

목적:
- Config 파일 로드 시 fingerprint 기록 (절대경로, mtime, sha256)
- 필수 키 검증을 "한 번에" 수행 (누락 시 전체 리스트 출력 후 종료)
- 런타임에서 "하나씩 발견" 방식 완전 금지

의존성: 순수 Python 표준 라이브러리만 사용
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


def compute_file_fingerprint(path: Path) -> Dict[str, Any]:
    """
    파일의 fingerprint 계산
    
    Returns:
        {
            "abs_path": str,
            "size": int,
            "mtime_iso": str,
            "sha256": str
        }
    """
    if not path.exists():
        raise FileNotFoundError(f"Config 파일이 존재하지 않습니다: {path}")
    
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    # SHA256 계산
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    return {
        "abs_path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_iso": mtime,
        "sha256": sha256_hash.hexdigest()[:16]  # 앞 16자리만
    }


def get_by_dotpath(config: Dict[str, Any], dotpath: str) -> Optional[Any]:
    """
    Dot-notation 경로로 중첩 dict 값 조회
    
    Examples:
        get_by_dotpath({"a": {"b": 1}}, "a.b") -> 1
        get_by_dotpath({"a": {}}, "a.b.c") -> None
    
    Args:
        config: 설정 딕셔너리
        dotpath: "a.b.c" 형태의 경로
    
    Returns:
        값 또는 None (경로가 존재하지 않으면)
    """
    keys = dotpath.split(".")
    current = config
    
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    
    return current


def validate_required_dotpaths(
    config: Dict[str, Any],
    required_dotpaths: List[str]
) -> List[str]:
    """
    필수 dotpath 리스트를 검증하고 누락된 키 리스트 반환
    
    Args:
        config: 설정 딕셔너리
        required_dotpaths: 필수 dotpath 리스트 (예: ["risk.per_trade", "capital.initial"])
    
    Returns:
        누락된 dotpath 리스트 (빈 리스트면 모두 존재)
    """
    missing = []
    
    for dotpath in required_dotpaths:
        value = get_by_dotpath(config, dotpath)
        if value is None:
            missing.append(dotpath)
    
    return missing


def assert_required(
    config: Dict[str, Any],
    required_dotpaths: List[str],
    context: str = "Config"
) -> None:
    """
    필수 키 검증 후 누락 시 RuntimeError 발생 (전체 누락 리스트 출력)
    
    Args:
        config: 설정 딕셔너리
        required_dotpaths: 필수 dotpath 리스트
        context: 에러 메시지에 표시될 컨텍스트
    
    Raises:
        RuntimeError: 누락된 키가 있을 경우
    """
    missing = validate_required_dotpaths(config, required_dotpaths)
    
    if missing:
        missing_str = "\n  - ".join(missing)
        raise RuntimeError(
            f"❌ {context} 필수 키 누락 ({len(missing)}개):\n  - {missing_str}\n\n"
            f"해결 방법:\n"
            f"1. configs/phase35/phase35_2_iter3_ssot.yaml에 누락 키 추가\n"
            f"2. common/config_required.py의 REQUIRED_DOTPATHS 확인\n"
            f"3. scripts/phase35/run_iter5_isolated.py의 ensure_required_keys() 확인"
        )


def print_fingerprint(fingerprint: Dict[str, Any], label: str = "Config") -> None:
    """
    Fingerprint를 읽기 쉬운 형태로 출력
    
    Args:
        fingerprint: compute_file_fingerprint() 결과
        label: 출력 레이블
    """
    print(f"📁 {label} Fingerprint:")
    print(f"   Path: {fingerprint['abs_path']}")
    print(f"   Size: {fingerprint['size']:,} bytes")
    print(f"   Modified: {fingerprint['mtime_iso']}")
    print(f"   SHA256: {fingerprint['sha256']}")
