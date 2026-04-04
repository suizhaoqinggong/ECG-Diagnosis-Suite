"""
Backward-compatible re-export module.

The implementation has been split into the ``app.services.report`` sub-package.
This module re-exports the public API so that existing imports such as::

    from app.services.diagnosis_report_service import DiagnosisEnhancedReport

continue to work without changes.
"""

from app.services.report import (  # noqa: F401
    DiagnosisEnhancedReport,
    DiagnosisReportService,
    _LLMReportBody,
    get_diagnosis_report_service,
)
