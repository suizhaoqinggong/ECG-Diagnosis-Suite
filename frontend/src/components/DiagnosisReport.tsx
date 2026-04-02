import { useState } from 'react'
import toast from 'react-hot-toast'
import type { DiagnosisResultData } from '@/api'
import { copyToClipboard, formatReportAsText } from '@/utils/clipboard'
import { formatConfidence } from '@/utils'
import QCWarning from './QCWarning'

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

  const handleCopy = async () => {
    const text = formatReportAsText(result)
    const success = await copyToClipboard(text)
    if (success) {
      setCopied(true)
      toast.success('Report copied to clipboard')
      setTimeout(() => setCopied(false), 2000)
    } else {
      toast.error('Failed to copy report')
    }
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <section className="printable-report space-y-8 rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)] md:p-8">
      {/* Overview */}
      <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_220px] md:items-end">
        <div className="space-y-3">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Diagnosis Overview
          </p>
          <h3 className="reading-copy text-4xl leading-none tracking-tight text-[var(--ink)] md:text-[3.2rem]">
            {result.prediction}
          </h3>
          {result.report?.summary ? (
            <p className="reading-copy text-lg leading-8 text-[var(--ink-soft)]">
              {result.report.summary}
            </p>
          ) : null}
        </div>

        <div className="rounded-[24px] border border-[var(--border)] bg-[rgba(245,241,234,0.8)] p-5">
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--ink-muted)]">
            Confidence
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">
            {formatConfidence(result.confidence)}
          </p>
          {result.severity ? (
            <p className="mt-4 text-sm text-[var(--ink-soft)]">
              Severity: {result.severity}
            </p>
          ) : null}
          {result.icd_code ? (
            <p className="mt-1 text-sm text-[var(--ink-soft)]">
              ICD: {result.icd_code}
            </p>
          ) : null}
          <p className="mt-4 text-xs uppercase tracking-[0.24em] text-[var(--ink-muted)]">
            Report: {result.report.source === 'llm' ? 'LLM enhanced' : 'Template'}
          </p>
        </div>
      </div>

      {/* Copy / Print Buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          className="rounded-full border border-[var(--border)] bg-white/60 px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
          aria-label="Copy report as text"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
        <button
          onClick={handlePrint}
          className="rounded-full border border-[var(--border)] bg-white/60 px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
          aria-label="Print report"
        >
          Print
        </button>
      </div>

      {showQualityBanner ? (
        <QCWarning
          quality_warning={result.quality_warning}
          pipeline_warnings={result.pipeline_warnings}
          per_lead_qc={result.per_lead_qc}
        />
      ) : null}

      {/* Clinical Interpretation */}
      {result.report?.clinical_interpretation ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Clinical Interpretation
          </p>
          <div className="rounded-[22px] border border-[var(--border)] bg-white/60 px-5 py-5">
            <p className="reading-copy text-lg leading-8 text-[var(--ink-soft)]">
              {result.report.clinical_interpretation}
            </p>
          </div>
        </div>
      ) : null}

      {/* Key Findings */}
      {result.report?.key_findings?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Key Findings
          </p>
          <div className="space-y-3">
            {result.report.key_findings.map((finding, index) => (
              <div
                key={`${finding}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {finding}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Top Predictions */}
      {result.top3_predictions && result.top3_predictions.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Top Signals
          </p>
          <div className="space-y-3">
            {result.top3_predictions.map((prediction) => (
              <div
                key={`${prediction.class}-${prediction.probability}`}
                className="grid gap-2 rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 md:grid-cols-[minmax(0,1fr)_90px]"
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
        </div>
      ) : null}

      {/* All Probabilities as Bar Charts */}
      {result.all_probabilities && Object.keys(result.all_probabilities).length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            All Predictions (Model Probabilities)
          </p>
          <div className="space-y-4">
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
        </div>
      ) : null}

      {/* Recommendations */}
      {result.report?.recommendations?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Recommendations
          </p>
          <div className="space-y-3">
            {result.report.recommendations.map((recommendation, index) => (
              <div
                key={`${recommendation}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {recommendation}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Follow-up */}
      {result.report?.follow_up?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Follow-up
          </p>
          <div className="space-y-3">
            {result.report.follow_up.map((item, index) => (
              <div
                key={`${item}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Limitations */}
      {result.report?.limitations?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Limitations
          </p>
          <div className="space-y-3">
            {result.report.limitations.map((item, index) => (
              <div
                key={`${item}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-[rgba(245,241,234,0.7)] px-4 py-4 text-base leading-7 text-[var(--ink-muted)]"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Disclaimer */}
      <p className="text-sm leading-7 text-[var(--ink-muted)]">
        {result.disclaimer}
      </p>
    </section>
  )
}
