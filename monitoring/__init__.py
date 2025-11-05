"""
Monitoring Package - System Performance & Telemetry

FlowGuardian Facade를 포함하여 시스템 성능, 연결 상태, 백필, 큐, 레이턴시 등을 모니터링합니다.
"""

from typing import Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

# 하위 모듈에서 import (구현 후)
# from .performance_monitor import SystemPerformanceMonitor, QueueHealth, LatencyTracker
# from .telemetry_profiler import TelemetryProfiler


class FlowGuardian:
    """
    FlowGuardian Facade - 모니터링 & 애널리틱스 통합 관문
    
    책임:
    - 이벤트 수집/분배 (emit_event)
    - 시스템 성능 샘플링 (sample_system)
    - 통합 스냅샷 생성 (snapshot)
    - 일일/주간 리포트 (report_daily, report_weekly)
    - 임계값 기반 알림 (alert_if_needed)
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: 전체 설정 dict (config.yml)
        """
        self.config = config
        self.mon_cfg = config.get("monitoring", {}).get("flowguardian", {})
        
        # 캐시 초기화
        self.mon_cache: Dict[str, Any] = {
            "system": {},
            "connection": {},
            "backfill": {},
            "queue": {},
            "latency": {}
        }
        self.an_cache: Dict[str, Any] = {
            "daily_kpis": {},
            "strategy_rank": []
        }
        
        # 설정
        self.enabled = self.mon_cfg.get("enabled", True)
        self.sample_interval_sec = self.mon_cfg.get("sample_interval_sec", 10)
        self.sinks = self.mon_cfg.get("sinks", ["log"])
        self.alerts = self.mon_cfg.get("alerts", {})
        
        logger.info(f"✅ FlowGuardian 초기화: enabled={self.enabled}, sinks={self.sinks}")
    
    def emit_event(self, event: dict) -> None:
        """
        이벤트 수집 및 내부 캐시 업데이트
        
        Args:
            event: {type: str, ts: float|int, payload: dict}
                   예: {"type": "system.performance", "ts": 1730280000, "payload": {...}}
        """
        if not self.enabled:
            return
        
        event_type = event.get("type", "")
        payload = event.get("payload", {})
        
        # 이벤트 타입별 캐시 업데이트
        if event_type == "system.performance":
            self.mon_cache["system"] = payload
        elif event_type == "ws.connection":
            self.mon_cache["connection"] = payload
        elif event_type == "backfill.stat":
            self.mon_cache["backfill"] = payload
        elif event_type == "queue.health":
            self.mon_cache["queue"] = payload
        elif event_type == "latency.stat":
            self.mon_cache["latency"] = payload
        elif event_type == "trade.metric":
            # analytics 캐시 업데이트 (일일 KPI 누적)
            pass
        
        # 싱크 처리 (log, telegram, json, db)
        if "log" in self.sinks:
            logger.debug(f"[FlowGuardian] {event_type}: {payload}")
    
    def sample_system(self) -> dict:
        """
        시스템 성능 샘플링 (CPU/Memory/Latency/Score)
        
        Returns:
            {cpu_pct, mem_mb, rss_mb, avg_latency_ms, score}
        """
        try:
            # performance_monitor에서 수집 (구현 후 활성화)
            # from .performance_monitor import get_system_metrics
            # return get_system_metrics()
            
            # monitoring/performance_monitor.py 사용
            from monitoring.performance_monitor import calculate_performance_scores
            scores = calculate_performance_scores()
            perf = scores
            return {
                "cpu_pct": perf.get("cpu_percent", 0),
                "mem_mb": perf.get("memory_mb", 0),
                "rss_mb": perf.get("rss_mb", 0),
                "avg_latency_ms": perf.get("latency_ms", 0),
                "score": perf.get("score", 0)
            }
        except Exception as e:
            logger.warning(f"⚠️ sample_system 실패: {e}")
            return {"cpu_pct": 0, "mem_mb": 0, "rss_mb": 0, "avg_latency_ms": 0, "score": 0}
    
    def snapshot(self) -> dict:
        """
        통합 스냅샷 생성 (monitoring + analytics 병합)
        
        Returns:
            {ts, monitoring: {...}, analytics: {...}}
        """
        return {
            "ts": int(time.time()),
            "monitoring": {
                "system": self.mon_cache.get("system", {}),
                "connection": self.mon_cache.get("connection", {}),
                "backfill": self.mon_cache.get("backfill", {}),
                "queue": self.mon_cache.get("queue", {}),
                "latency": self.mon_cache.get("latency", {})
            },
            "analytics": {
                "daily_kpis": self.an_cache.get("daily_kpis", {}),
                "strategy_rank": self.an_cache.get("strategy_rank", [])
            }
        }
    
    def report_daily(self) -> dict:
        """
        일일 리포트 생성 (KPI 집계 + 파일/텔레그램 발송)
        
        Returns:
            {status, report_path, telegram_sent}
        """
        try:
            # analytics.trade_analyzer에서 KPI 집계 (구현 후 활성화)
            # from analytics.trade_analyzer import get_daily_kpis
            # kpis = get_daily_kpis(...)
            
            # analytics.report_generator에서 HTML/JSON 생성 (구현 후 활성화)
            # from analytics.report_generator import generate_daily_report
            # report_path = generate_daily_report(kpis, ...)
            
            logger.info("📊 [FlowGuardian] 일일 리포트 생성 (구현 예정)")
            return {"status": "pending", "report_path": None, "telegram_sent": False}
        except Exception as e:
            logger.error(f"❌ report_daily 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def report_weekly(self) -> dict:
        """
        주간 리포트 생성
        
        Returns:
            {status, report_path, telegram_sent}
        """
        try:
            logger.info("📊 [FlowGuardian] 주간 리포트 생성 (구현 예정)")
            return {"status": "pending", "report_path": None, "telegram_sent": False}
        except Exception as e:
            logger.error(f"❌ report_weekly 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def alert_if_needed(self, snapshot: dict) -> None:
        """
        임계값 기반 알림 발송
        
        Args:
            snapshot: snapshot() 반환값
        """
        if not self.enabled:
            return
        
        monitoring = snapshot.get("monitoring", {})
        system = monitoring.get("system", {})
        connection = monitoring.get("connection", {})
        queue = monitoring.get("queue", {})
        
        # CPU 임계값 체크
        cpu_pct = system.get("cpu_pct", 0)
        cpu_warning = self.alerts.get("cpu_pct_warning", 85)
        cpu_critical = self.alerts.get("cpu_pct_critical", 95)
        
        if cpu_pct >= cpu_critical:
            self._send_alert("CRITICAL", f"CPU 사용률 위험: {cpu_pct:.1f}%")
        elif cpu_pct >= cpu_warning:
            self._send_alert("WARNING", f"CPU 사용률 경고: {cpu_pct:.1f}%")
        
        # WebSocket 메시지 지연 체크
        last_msg_ago = connection.get("last_message_ago_sec", 0)
        ws_threshold = self.alerts.get("ws_last_message_ago_sec", 60)
        if last_msg_ago > ws_threshold:
            self._send_alert("WARNING", f"WebSocket 메시지 지연: {last_msg_ago:.0f}초")
        
        # 큐 드롭률 체크
        drop_rate = queue.get("drop_rate", 0)
        drop_threshold = self.alerts.get("queue_drop_rate_pct", 1.0)
        if drop_rate > drop_threshold:
            self._send_alert("WARNING", f"큐 드롭률 초과: {drop_rate:.2f}%")
    
    def _send_alert(self, level: str, message: str) -> None:
        """
        알림 발송 (텔레그램/로그)
        
        Args:
            level: "WARNING" | "CRITICAL"
            message: 알림 메시지
        """
        if "telegram" in self.sinks:
            try:
                from common.messaging import system_alert
                system_alert(f"[{level}] {message}")
            except Exception as e:
                logger.warning(f"⚠️ 텔레그램 알림 실패: {e}")
        
        if "log" in self.sinks:
            if level == "CRITICAL":
                logger.critical(f"🚨 {message}")
            else:
                logger.warning(f"⚠️ {message}")


# 전역 인스턴스 (선택, engine에서 초기화 후 사용)
_guardian_instance = None

def get_guardian() -> FlowGuardian:
    """전역 FlowGuardian 인스턴스 반환"""
    global _guardian_instance
    if _guardian_instance is None:
        raise RuntimeError("FlowGuardian이 초기화되지 않았습니다. init_guardian(config)를 먼저 호출하세요.")
    return _guardian_instance

def init_guardian(config: dict) -> FlowGuardian:
    """전역 FlowGuardian 초기화"""
    global _guardian_instance
    _guardian_instance = FlowGuardian(config)
    return _guardian_instance


__all__ = ["FlowGuardian", "get_guardian", "init_guardian"]
