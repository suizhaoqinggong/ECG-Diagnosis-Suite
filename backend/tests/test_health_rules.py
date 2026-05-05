from app.services.health_pipeline.rules import normalize_findings


def test_normalize_findings_marks_high_ldl_for_recheck():
    findings = normalize_findings(
        [
            {
                "source_type": "lab",
                "text": "血脂结果：LDL 4.9 mmol/L，总胆固醇 6.2 mmol/L",
            }
        ]
    )

    ldl_finding = next(finding for finding in findings if "LDL" in finding["title"])

    assert ldl_finding["sourceType"] == "lab"
    assert ldl_finding["severity"] == "medium"
    assert ldl_finding["actionHint"] == "recheck"
