import type { DiagnosisResultData } from '@/api'
import { formatConfidence } from '@/utils'

interface DiagnosisReportProps {
  result: DiagnosisResultData
}

export default function DiagnosisReport({ result }: DiagnosisReportProps) {
  return (
    <section className="space-y-8 rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)] md:p-8">
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
