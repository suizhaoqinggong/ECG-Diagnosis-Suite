from __future__ import annotations

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def compose_health_report(findings: list[dict], ecg_result: dict | None = None) -> dict:
    highest_risk_finding = max(
        findings,
        default=None,
        key=lambda item: RISK_ORDER.get(item["severity"], -1),
    )
    overall = (
        highest_risk_finding["severity"]
        if highest_risk_finding is not None
        else "low"
    )
    next_steps = [
        item["title"]
        for item in findings
        if item["actionHint"] in {"recheck", "clinic_visit", "urgent_visit"}
    ]
    return {
        "summary": (
            highest_risk_finding["summary"]
            if highest_risk_finding is not None
            else "未从上传资料中识别到明确异常。"
        ),
        "overallRisk": overall,
        "findings": findings,
        "nextSteps": next_steps,
        "limitations": ["仅基于上传资料解释"],
        "disclaimer": "本结果仅供参考，不作为临床诊断依据",
        "ecgResult": ecg_result,
    }
