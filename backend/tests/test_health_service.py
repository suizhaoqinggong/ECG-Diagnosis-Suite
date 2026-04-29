import asyncio

from app.services.health_pipeline.composer import compose_health_report
from app.services.health_pipeline.service import HealthPipelineService


def test_compose_health_report_promotes_highest_risk():
    report = compose_health_report(
        findings=[
            {"id": "f1", "title": "LDL 偏高", "severity": "medium", "action_hint": "recheck"},
            {"id": "f2", "title": "心电图异常", "severity": "high", "action_hint": "clinic_visit"},
        ]
    )
    assert report["overallRisk"] == "high"


class StubEcgAdapter:
    async def analyze_bundle(self, paths):
        return {"prediction": "正常", "confidence": 0.91}


def test_service_preserves_ecg_result_in_final_payload():
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter())
    payload = asyncio.run(service._build_completed_payload(
        findings=[{"id": "f1", "title": "LDL 偏高", "severity": "medium", "action_hint": "recheck"}],
        ecg_result={"prediction": "正常", "confidence": 0.91},
    ))
    assert payload["ecgResult"]["prediction"] == "正常"
