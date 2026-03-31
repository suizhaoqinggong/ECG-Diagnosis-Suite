import type { DiagnosisResultData } from '@/api'

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function formatReportAsText(result: DiagnosisResultData): string {
  const lines: string[] = []

  lines.push('ECG Diagnosis Report')
  lines.push('='.repeat(40))
  lines.push('')
  lines.push(`Diagnosis: ${result.prediction}`)
  lines.push(`Confidence: ${(result.confidence * 100).toFixed(1)}%`)

  if (result.severity) lines.push(`Severity: ${result.severity}`)
  if (result.icd_code) lines.push(`ICD Code: ${result.icd_code} (Reference only)`)

  lines.push('')
  lines.push(`Generated: ${new Date(result.timestamp).toLocaleString()}`)
  lines.push(`Report Source: ${result.report.source === 'llm' ? 'LLM Enhanced' : 'Template'}`)

  if (result.report.summary) {
    lines.push('')
    lines.push('Summary:')
    lines.push(result.report.summary)
  }

  if (result.report.clinical_interpretation) {
    lines.push('')
    lines.push('Clinical Interpretation:')
    lines.push(result.report.clinical_interpretation)
  }

  if (result.report.key_findings?.length) {
    lines.push('')
    lines.push('Key Findings:')
    result.report.key_findings.forEach((finding, i) => {
      lines.push(`${i + 1}. ${finding}`)
    })
  }

  if (result.all_probabilities) {
    lines.push('')
    lines.push('All Predictions:')
    Object.entries(result.all_probabilities)
      .sort(([, a], [, b]) => b - a)
      .forEach(([className, prob]) => {
        lines.push(`  ${className}: ${(prob * 100).toFixed(1)}%`)
      })
  }

  if (result.report.recommendations?.length) {
    lines.push('')
    lines.push('Recommendations:')
    result.report.recommendations.forEach((rec, i) => {
      lines.push(`${i + 1}. ${rec}`)
    })
  }

  if (result.report.follow_up?.length) {
    lines.push('')
    lines.push('Follow-up Steps:')
    result.report.follow_up.forEach((item, i) => {
      lines.push(`${i + 1}. ${item}`)
    })
  }

  lines.push('')
  lines.push(`Disclaimer: ${result.disclaimer}`)

  return lines.join('\n')
}
