import type { HealthRiskLevel } from '@/types/health'

/**
 * Map a backend `severity` field on a diagnosis result to a `HealthRiskLevel`.
 *
 * The backend currently emits Chinese labels via `SYMPTOM_DATABASE` in
 * `backend/app/services/diagnosis_service.py` ("正常" / "中等" / "严重"), and
 * legacy/test fixtures may still use English labels. Both are recognised here.
 *
 * Unknown / null / undefined inputs map to `null` rather than to "high" — the
 * previous default treated any missing severity as a red-flag warning, which
 * is a clinical-safety bug. Callers should decide how to render unknown
 * severity (typically as "medium" or by hiding the risk badge entirely).
 */
const SEVERITY_MAP: Record<string, HealthRiskLevel> = {
  // Chinese (current backend output)
  '正常': 'low',
  '轻度': 'low',
  '边缘': 'medium',
  '中等': 'medium',
  '中度': 'medium',
  '严重': 'high',
  '重度': 'high',
  '危急': 'urgent',
  '紧急': 'urgent',

  // English (legacy / external sources)
  normal: 'low',
  mild: 'low',
  borderline: 'medium',
  moderate: 'medium',
  severe: 'high',
  high: 'high',
  critical: 'urgent',
  urgent: 'urgent',
}

export function mapDiagnosisSeverityToRisk(
  severity?: string | null,
): HealthRiskLevel | null {
  if (!severity) return null
  const key = severity.trim().toLowerCase()
  return SEVERITY_MAP[severity.trim()] ?? SEVERITY_MAP[key] ?? null
}

/**
 * Like `mapDiagnosisSeverityToRisk` but falls back to "medium" for unknown
 * values. Use this when the consumer needs a definite `HealthRiskLevel`
 * (e.g., to colour a `RiskCard`) and "medium" is the safest neutral default.
 */
export function mapDiagnosisSeverityToRiskOrDefault(
  severity?: string | null,
  fallback: HealthRiskLevel = 'medium',
): HealthRiskLevel {
  return mapDiagnosisSeverityToRisk(severity) ?? fallback
}
