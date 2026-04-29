import type { HealthAnalysisResult } from '@/types/health'

interface HealthReportProps {
  result: HealthAnalysisResult
}

export default function HealthReport({ result }: HealthReportProps) {
  return (
    <section className="printable-report space-y-8 rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)] md:p-8">
      {/* Summary */}
      <div className="space-y-3">
        <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
          Health Summary
        </p>
        <h3 className="reading-copy text-4xl leading-none tracking-tight text-[var(--ink)] md:text-[3.2rem]">
          Overall Risk: {result.overallRisk}
        </h3>
        <p className="reading-copy text-lg leading-8 text-[var(--ink-soft)]">
          {result.summary}
        </p>
      </div>

      {/* Findings */}
      {result.findings.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Findings
          </p>
          <div className="space-y-3">
            {result.findings.map((finding) => (
              <div
                key={finding.id}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                <p className="font-semibold text-[var(--ink)]">{finding.title}</p>
                <p className="mt-1">{finding.summary}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--ink-muted)]">
                  severity: {finding.severity} · action: {finding.actionHint}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Next Steps */}
      {result.nextSteps.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Next Steps
          </p>
          <div className="space-y-3">
            {result.nextSteps.map((step, index) => (
              <div
                key={`${step}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {step}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Limitations */}
      {result.limitations.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Limitations
          </p>
          <div className="space-y-3">
            {result.limitations.map((item, index) => (
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
