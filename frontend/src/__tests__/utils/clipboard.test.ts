import { describe, expect, it } from 'vitest'
import type { DiagnosisResultData } from '@/api'
import { formatReportAsText } from '@/utils/clipboard'

const resultWithWarnings: DiagnosisResultData = {
  prediction: 'ST-T改变',
  confidence: 0.84,
  severity: '中等',
  icd_code: 'I20.0',
  description: 'Test description',
  recommendations: null,
  timestamp: '2026-04-01T10:00:00.000Z',
  disclaimer: '本结果仅供参考，不作为临床诊断依据',
  all_probabilities: null,
  top3_predictions: null,
  quality_warning: 'warn',
  pipeline_warnings: [
    '导联 3 信号提取质量较差',
    '信号插值比例较高 (34.0%)',
  ],
  report: {
    source: 'template',
    summary: 'Summary text',
    clinical_interpretation: 'Clinical interpretation',
    key_findings: [],
    recommendations: [],
    follow_up: [],
    limitations: [],
  },
}

describe('formatReportAsText', () => {
  it('includes quality warnings when present', () => {
    const text = formatReportAsText(resultWithWarnings)

    expect(text).toContain('Quality Warning: warn')
    expect(text).toContain('Pipeline Warnings:')
    expect(text).toContain('1. 导联 3 信号提取质量较差')
    expect(text).toContain('2. 信号插值比例较高 (34.0%)')
  })
})
