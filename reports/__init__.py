"""
Reports Module (DEPRECATED)
===========================
⚠️ 이 모듈은 DEPRECATED되었습니다.

모든 리포트 기능은 analytics.report_generator로 이관되었습니다.
하위 호환성을 위해 wrapper만 제공합니다.

새로운 코드는 다음을 사용하세요:
    from analytics.report_generator import generate_backtest_report
"""
import warnings
import logging

logger = logging.getLogger(__name__)

# Analytics 모듈로 라우팅
from analytics.report_generator import (
    generate_backtest_report as _generate_backtest_report,
    generate_daily_report as _generate_daily_report,
)


def generate_trading_report(json_file=None, output_file=None, mode="backtest", **kwargs):
    """DEPRECATED: analytics.report_generator.generate_backtest_report를 사용하세요."""
    warnings.warn(
        "reports.generate_trading_report()는 deprecated되었습니다. "
        "analytics.report_generator.generate_backtest_report()를 사용하세요.",
        DeprecationWarning, stacklevel=2
    )
    logger.warning("⚠️ DEPRECATED: reports.generate_trading_report")
    result = _generate_backtest_report(
        trial_id=kwargs.get('trial_id'),
        output_file=output_file,
        sinks=["log", "html"] if output_file else ["log"]
    )
    return result.get("html_path", output_file)


def generate_performance_report(metrics_file=None, output_file=None, **kwargs):
    """DEPRECATED: analytics.report_generator.generate_daily_report를 사용하세요."""
    warnings.warn(
        "reports.generate_performance_report()는 deprecated되었습니다. "
        "analytics.report_generator.generate_daily_report()를 사용하세요.",
        DeprecationWarning, stacklevel=2
    )
    logger.warning("⚠️ DEPRECATED: reports.generate_performance_report")
    result = _generate_daily_report(kpis=kwargs.get('kpis', {}), sinks=["log", "html"])
    return result.get("html_path", output_file)


def calculate_tuning_score_from_db(db_path=None):
    """DEPRECATED: SQLite 지원 중단. PostgreSQL을 사용하세요."""
    warnings.warn(
        "reports.calculate_tuning_score_from_db()는 deprecated되었습니다. "
        "analytics.report_generator.generate_backtest_report()를 사용하세요.",
        DeprecationWarning, stacklevel=2
    )
    logger.error("❌ SQLite 지원 중단. PostgreSQL을 사용하세요.")
    raise NotImplementedError("SQLite 지원 중단. analytics.report_generator를 사용하세요.")


__all__ = ['generate_trading_report', 'generate_performance_report', 'calculate_tuning_score_from_db']
