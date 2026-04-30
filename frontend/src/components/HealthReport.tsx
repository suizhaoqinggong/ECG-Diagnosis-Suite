import type { HealthAnalysisResult } from '@/types/health'
import ConclusionHero from './result/ConclusionHero'
import WhatItMeans from './result/WhatItMeans'
import RiskCard from './result/RiskCard'
import NextStepsChecklist from './result/NextStepsChecklist'
import DoctorQuestions from './result/DoctorQuestions'
import EvidenceAndLimits from './result/EvidenceAndLimits'

interface HealthReportProps {
  result: HealthAnalysisResult
}

export default function HealthReport({ result }: HealthReportProps) {
  return (
    <section className="printable-report space-y-8 rounded-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_16px_40px_rgba(84,69,53,0.06)] md:p-8">
      {/* Section 1: Core Conclusion */}
      <ConclusionHero
        title={result.summary || `Overall Risk: ${result.overallRisk}`}
        summary={result.summary}
        reportType="健康分析报告"
        sourceType="综合健康分析"
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

      {result.ecgResult ? (
        <div className="space-y-4">
          <p className="text-lg font-semibold tracking-tight text-[var(--ink)]">
            ECG 详细分析
          </p>
          <div className="rounded-[20px] border border-[var(--border)] bg-[var(--surface)] p-5">
            <p className="font-semibold text-[var(--ink)]">{result.ecgResult.prediction}</p>
            <p className="mt-1 text-base text-[var(--ink-soft)]">{result.ecgResult.report?.summary}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--ink-muted)]">
              confidence: {Math.round(result.ecgResult.confidence * 100)}%
            </p>
          </div>
        </div>
      ) : null}
    </section>
  )
}
