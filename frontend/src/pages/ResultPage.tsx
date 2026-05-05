import type { HealthAnalysisResult } from '@/types/health'
import type { DiagnosisResultData } from '@/api'
import { formatConversationTimestamp } from '@/utils'
import { mapRiskToPatientLabel } from '@/utils/patient-language'
import { mapDiagnosisSeverityToRiskOrDefault } from '@/utils/severity'
import ReportShell from '@/components/result/ReportShell'
import ConclusionHero from '@/components/result/ConclusionHero'
import WhatItMeans from '@/components/result/WhatItMeans'
import RiskCard from '@/components/result/RiskCard'
import NextStepsChecklist from '@/components/result/NextStepsChecklist'
import DoctorQuestions from '@/components/result/DoctorQuestions'
import EvidenceAndLimits from '@/components/result/EvidenceAndLimits'

interface ResultPageProps {
  result: HealthAnalysisResult | DiagnosisResultData
  timestamp?: string
  onSave?: () => void
  isSaved?: boolean
}

function isHealthResult(result: HealthAnalysisResult | DiagnosisResultData): result is HealthAnalysisResult {
  return 'overallRisk' in result && 'findings' in result
}

export default function ResultPage({ result, timestamp, onSave, isSaved }: ResultPageProps) {
  const formattedTime = timestamp ? formatConversationTimestamp(timestamp) : undefined

  if (isHealthResult(result)) {
    const riskLabel = mapRiskToPatientLabel(result.overallRisk)

    return (
      <div className="mx-auto max-w-3xl px-4 py-8 md:px-8 md:py-12">
        <ReportShell className="rounded-none border-0 bg-transparent shadow-none p-0 md:p-0 space-y-10">
          {/* Save button */}
          {onSave && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={onSave}
                disabled={isSaved}
                className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                  isSaved
                    ? 'border border-[var(--border)] bg-[var(--surface)] text-[var(--ink-muted)] cursor-not-allowed'
                    : 'bg-[var(--accent)] text-white hover:opacity-90'
                }`}
              >
                {isSaved ? '已保存到我的报告' : '保存到我的报告'}
              </button>
            </div>
          )}

          {/* Section 1: Core Conclusion */}
          <ConclusionHero
            title={result.summary || riskLabel}
            summary={result.summary}
            reportType="健康分析报告"
            sourceType="综合健康分析"
            timestamp={formattedTime}
          />

          {/* Section 2: What This Means */}
          <WhatItMeans
            summary={result.summary}
            findings={result.findings}
          />

          {/* Section 3: Risk Judgment */}
          <RiskCard riskLevel={result.overallRisk} />

          {/* Section 4: Next Steps */}
          <NextStepsChecklist nextSteps={result.nextSteps} />

          {/* Section 5: Questions for Doctor */}
          <DoctorQuestions findings={result.findings} />

          {/* Section 6: Evidence & Limitations */}
          <EvidenceAndLimits
            confidence={result.ecgResult?.confidence}
            limitations={result.limitations}
            disclaimer={result.disclaimer}
          />
        </ReportShell>
      </div>
    )
  }

  // DiagnosisResultData (legacy ECG-only result)
  const riskLevel = mapDiagnosisSeverityToRiskOrDefault(result.severity)

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-8 md:py-12">
      <ReportShell className="rounded-none border-0 bg-transparent shadow-none p-0 md:p-0 space-y-10">
        {/* Save button */}
        {onSave && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onSave}
              disabled={isSaved}
              className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                isSaved
                  ? 'border border-[var(--border)] bg-[var(--surface)] text-[var(--ink-muted)] cursor-not-allowed'
                  : 'bg-[var(--accent)] text-white hover:opacity-90'
              }`}
            >
              {isSaved ? '已保存到我的报告' : '保存到我的报告'}
            </button>
          </div>
        )}

        {/* Section 1: Core Conclusion */}
        <ConclusionHero
          title={result.prediction}
          summary={result.report?.summary}
          reportType="心电图分析报告"
          sourceType="ECG AI 分析"
          timestamp={formattedTime}
        />

        {/* Section 2: What This Means */}
        <WhatItMeans
          summary={result.report?.summary}
          clinicalInterpretation={result.report?.clinical_interpretation}
          findings={result.report?.key_findings?.map((f, i) => ({
            id: `finding-${i}`,
            sourceType: 'ecg_ai' as const,
            title: result.top3_predictions?.[0]?.class || result.prediction,
            summary: f,
            severity: riskLevel,
            actionHint: 'clinic_visit' as const,
            evidence: [],
          }))}
        />

        {/* Section 3: Risk Judgment */}
        <RiskCard
          riskLevel={riskLevel}
        />

        {/* Section 4: Next Steps */}
        <NextStepsChecklist
          recommendations={result.report?.recommendations}
          followUp={result.report?.follow_up}
        />

        {/* Section 5: Questions for Doctor */}
        <DoctorQuestions findings={result.report?.key_findings?.map((f, i) => ({
          id: `finding-${i}`,
          sourceType: 'ecg_ai' as const,
          title: result.prediction,
          summary: f,
          severity: riskLevel,
          actionHint: 'clinic_visit' as const,
          evidence: [],
        }))} />

        {/* Section 6: Evidence & Limitations */}
        <EvidenceAndLimits
          confidence={result.confidence}
          pipelineWarnings={result.pipeline_warnings}
          limitations={result.report?.limitations}
          disclaimer={result.disclaimer}
        />
      </ReportShell>
    </div>
  )
}
