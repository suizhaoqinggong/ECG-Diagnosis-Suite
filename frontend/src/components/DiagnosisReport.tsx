import { useState } from 'react'
import toast from 'react-hot-toast'
import type { DiagnosisResultData } from '@/api'
import { copyToClipboard, formatReportAsText } from '@/utils/clipboard'
import { formatConfidence } from '@/utils'
import { mapDiagnosisSeverityToRiskOrDefault } from '@/utils/severity'
import QCWarning from './QCWarning'
import ReportShell from './result/ReportShell'
import ConclusionHero from './result/ConclusionHero'
import WhatItMeans from './result/WhatItMeans'
import RiskCard from './result/RiskCard'
import NextStepsChecklist from './result/NextStepsChecklist'
import DoctorQuestions from './result/DoctorQuestions'
import EvidenceAndLimits from './result/EvidenceAndLimits'

interface DiagnosisReportProps {
  result: DiagnosisResultData
}

function ProbabilityBar({ prediction, index }: { prediction: { class: string; probability: number; class_en?: string }; index: number }) {
  const percentage = (prediction.probability * 100).toFixed(1)
  const isTop3 = index < 3

  return (
    <div className="flex items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-sm font-semibold text-[var(--ink)]">
            {prediction.class}
          </p>
          <p className="shrink-0 text-sm font-medium text-[var(--ink-soft)]">
            {percentage}%
          </p>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">
          <div
            className={`h-full transition-all duration-500 ${
              isTop3 ? 'bg-[var(--accent)]' : 'bg-[var(--border-strong)]'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {prediction.class_en && (
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            {prediction.class_en}
          </p>
        )}
      </div>
    </div>
  )
}

export default function DiagnosisReport({ result }: DiagnosisReportProps) {
  const [copied, setCopied] = useState(false)
  const showQualityBanner = result.quality_warning === 'warn' || result.quality_warning === 'fail' || (result.pipeline_warnings ?? []).length > 0

  const riskLevel = mapDiagnosisSeverityToRiskOrDefault(result.severity)

  const handleCopy = async () => {
    const text = formatReportAsText(result)
    const success = await copyToClipboard(text)
    if (success) {
      setCopied(true)
      toast.success('报告已复制到剪贴板')
      setTimeout(() => setCopied(false), 2000)
    } else {
      toast.error('复制报告失败')
    }
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <ReportShell>
      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
          aria-label="复制报告文本"
        >
          {copied ? '已复制' : '复制报告'}
        </button>
        <button
          onClick={handlePrint}
          className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
          aria-label="打印报告"
        >
          打印
        </button>
      </div>

      {showQualityBanner ? (
        <QCWarning
          quality_warning={result.quality_warning}
          pipeline_warnings={result.pipeline_warnings}
          per_lead_qc={result.per_lead_qc}
        />
      ) : null}

      {/* Section 1: Core Conclusion */}
      <ConclusionHero
        title={result.prediction}
        summary={result.report?.summary}
        reportType="心电图分析报告"
        sourceType="ECG AI 分析"
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
      <RiskCard riskLevel={riskLevel} />

      {/* Section 4: Next Steps */}
      <NextStepsChecklist
        recommendations={result.report?.recommendations}
        followUp={result.report?.follow_up}
      />

      {/* Section 5: Questions for Doctor */}
      <DoctorQuestions
        findings={result.report?.key_findings?.map((f, i) => ({
          id: `finding-${i}`,
          sourceType: 'ecg_ai' as const,
          title: result.prediction,
          summary: f,
          severity: riskLevel,
          actionHint: 'clinic_visit' as const,
          evidence: [],
        }))}
      />

      {/* Section 6: Evidence & Limitations */}
      <EvidenceAndLimits
        confidence={result.confidence}
        pipelineWarnings={result.pipeline_warnings}
        limitations={result.report?.limitations}
        disclaimer={result.disclaimer}
      />

      {/* Technical details: collapsible */}
      <details className="group space-y-4 rounded-[20px] border border-[var(--border)] bg-[var(--bg-muted)]/50 p-5">
        <summary className="cursor-pointer text-sm font-medium text-[var(--ink-soft)]">
          查看技术详情 (模型概率分布)
        </summary>

        <div className="mt-4 space-y-4">
          {result.top3_predictions && result.top3_predictions.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                主要预测
              </p>
              {result.top3_predictions.map((prediction) => (
                <div
                  key={`${prediction.class}-${prediction.probability}`}
                  className="grid gap-2 rounded-[16px] border border-[var(--border)] bg-[var(--surface)] p-4 md:grid-cols-[minmax(0,1fr)_90px]"
                >
                  <div>
                    <p className="text-base font-semibold text-[var(--ink)]">
                      {prediction.class}
                    </p>
                    {prediction.class_en ? (
                      <p className="mt-1 text-sm text-[var(--ink-muted)]">
                        {prediction.class_en}
                      </p>
                    ) : null}
                  </div>
                  <p className="text-base font-medium text-[var(--ink-soft)] md:text-right">
                    {formatConfidence(prediction.probability)}
                  </p>
                </div>
              ))}
            </div>
          ) : null}

          {result.all_probabilities && Object.keys(result.all_probabilities).length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                所有概率分布
              </p>
              {Object.entries(result.all_probabilities)
                .sort(([, a], [, b]) => b - a)
                .map(([className, probability], index) => (
                  <ProbabilityBar
                    key={className}
                    prediction={{ class: className, probability }}
                    index={index}
                  />
                ))}
            </div>
          ) : null}
        </div>
      </details>

      {/* Confidence sidebar card (legacy) */}
      <div className="rounded-[20px] border border-[var(--border)] bg-[var(--bg-muted)]/50 p-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-muted)]">
          置信度
        </p>
        <p className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]">
          {formatConfidence(result.confidence)}
        </p>
        {result.severity && (
          <p className="mt-2 text-sm text-[var(--ink-soft)]">
            严重程度: {result.severity}
          </p>
        )}
        {result.icd_code && (
          <p className="mt-1 text-sm text-[var(--ink-soft)]">
            ICD: {result.icd_code}
          </p>
        )}
      </div>
    </ReportShell>
  )
}
