"""Normalize parsed report fields into structured clinical findings."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


LDL_PATTERN = re.compile(r"\bLDL\b[^0-9]{0,12}(\d+(?:\.\d+)?)", re.IGNORECASE)
TC_PATTERN = re.compile(r"(?:总胆固醇|total cholesterol)[^0-9]{0,12}(\d+(?:\.\d+)?)", re.IGNORECASE)
TIRADS_PATTERN = re.compile(r"TI[-\s]?RADS\s*([1-5])", re.IGNORECASE)
URGENT_KEYWORDS = ("急诊", "urgent", "立即就医")
ABNORMAL_KEYWORDS = ("异常", "偏高", "增高", "结节", "占位", "high")


def _make_finding(
    *,
    source_type: str,
    title: str,
    summary: str,
    severity: str,
    action_hint: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "sourceType": source_type,
        "title": title,
        "summary": summary,
        "severity": severity,
        "actionHint": action_hint,
        "evidence": evidence,
    }


def _normalize_lab_text(source_type: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    ldl_match = LDL_PATTERN.search(text)
    if ldl_match:
        ldl = float(ldl_match.group(1))
        if ldl >= 4.1:
            findings.append(
                _make_finding(
                    source_type=source_type,
                    title="LDL 胆固醇偏高",
                    summary="低密度脂蛋白高于常见参考范围，建议结合既往血脂和心血管风险复查。",
                    severity="medium",
                    action_hint="recheck",
                    evidence=[f"LDL {ldl:.1f} mmol/L"],
                )
            )

    tc_match = TC_PATTERN.search(text)
    if tc_match:
        total_cholesterol = float(tc_match.group(1))
        if total_cholesterol >= 6.2:
            findings.append(
                _make_finding(
                    source_type=source_type,
                    title="总胆固醇升高",
                    summary="总胆固醇高于常见参考范围，建议结合饮食、体重和复查结果综合评估。",
                    severity="low",
                    action_hint="observe",
                    evidence=[f"总胆固醇 {total_cholesterol:.1f} mmol/L"],
                )
            )

    return findings


def _normalize_tirads(source_type: str, text: str) -> list[dict[str, Any]]:
    match = TIRADS_PATTERN.search(text)
    if not match:
        return []

    grade = int(match.group(1))
    if grade >= 5:
        severity = "urgent"
        action_hint = "urgent_visit"
    elif grade == 4:
        severity = "high"
        action_hint = "clinic_visit"
    else:
        severity = "medium"
        action_hint = "recheck"

    return [
        _make_finding(
            source_type=source_type,
            title=f"影像报告提示 TI-RADS {grade}",
            summary="报告提示结节需要按分级进行复查或专科随访。",
            severity=severity,
            action_hint=action_hint,
            evidence=[match.group(0)],
        )
    ]


def _normalize_generic(source_type: str, text: str) -> list[dict[str, Any]]:
    compact = " ".join(text.split())
    if not compact:
        return []

    if any(keyword in compact for keyword in URGENT_KEYWORDS):
        return [
            _make_finding(
                source_type=source_type,
                title="报告提示需要尽快就医",
                summary="上传资料中包含需要尽快线下评估的提示，请结合原报告结论和症状处理。",
                severity="urgent",
                action_hint="urgent_visit",
                evidence=[compact[:140]],
            )
        ]

    if any(keyword in compact.lower() for keyword in ABNORMAL_KEYWORDS):
        return [
            _make_finding(
                source_type=source_type,
                title="报告出现异常提示",
                summary="资料中存在异常描述，建议结合原始报告和既往病史安排复查或门诊评估。",
                severity="medium",
                action_hint="clinic_visit",
                evidence=[compact[:140]],
            )
        ]

    return []


def normalize_findings(raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for item in raw_items:
        source_type = str(item.get("source_type") or "health_check_summary")
        text = str(item.get("text") or "").strip()
        if not text:
            continue

        findings.extend(_normalize_lab_text(source_type, text))
        findings.extend(_normalize_tirads(source_type, text))

        if not any(
            evidence and evidence[0] in text
            for evidence in (finding.get("evidence") for finding in findings if finding.get("sourceType") == source_type)
        ):
            findings.extend(_normalize_generic(source_type, text))

    return findings


def build_ecg_finding(ecg_result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not ecg_result:
        return None

    prediction = str(ecg_result.get("prediction") or "ECG 已分析")
    confidence = ecg_result.get("confidence")
    confidence_text = (
        f"{confidence:.0%}" if isinstance(confidence, (float, int)) else "未提供"
    )

    if prediction == "正常":
        severity = "low"
        action_hint = "observe"
        summary = "ECG AI 未提示急性高风险异常，可结合症状和既往结果继续观察。"
    elif prediction == "信号质量不足":
        severity = "medium"
        action_hint = "recheck"
        summary = "当前 ECG 信号质量不足，建议重新上传更清晰的图像或信号文件。"
    else:
        severity = "high"
        action_hint = "clinic_visit"
        summary = "ECG AI 提示存在需要结合临床进一步评估的异常。"

    return _make_finding(
        source_type="ecg_ai",
        title=f"ECG AI：{prediction}",
        summary=summary,
        severity=severity,
        action_hint=action_hint,
        evidence=[f"预测结果：{prediction}", f"置信度：{confidence_text}"],
    )
