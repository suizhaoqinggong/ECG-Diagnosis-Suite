"""Report generation sub-package.

Re-exports the public API so that existing imports keep working:
    from app.services.report import DiagnosisEnhancedReport, …
"""

from .parser import strip_markdown_fences, parse_llm_text, LLMReportBody, _LLMReportBody
from .schemas import DiagnosisEnhancedReport
from .service import DiagnosisReportService, get_diagnosis_report_service
from .template_builder import TemplateReportBuilder

__all__ = [
    "DiagnosisEnhancedReport",
    "DiagnosisReportService",
    "TemplateReportBuilder",
    "get_diagnosis_report_service",
    "strip_markdown_fences",
    "parse_llm_text",
    "LLMReportBody",
    "_LLMReportBody",
]
