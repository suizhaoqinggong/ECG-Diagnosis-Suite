from __future__ import annotations

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def compose_health_report(findings: list[dict], ecg_result: dict | None = None) -> dict:
    overall = max((item["severity"] for item in findings), default="low", key=RISK_ORDER.get)
    next_steps = [item["title"] for item in findings if item["action_hint"] in {"recheck", "clinic_visit", "urgent_visit"}]
    return {
        "summary": findings[0]["title"] if findings else "未识别到明确异常",
        "overallRisk": overall,
        "findings": findings,
        "nextSteps": next_steps,
        "limitations": ["仅基于上传资料解释"],
        "disclaimer": "本结果仅供参考，不作为临床诊断依据",
        "ecgResult": ecg_result,
    }
