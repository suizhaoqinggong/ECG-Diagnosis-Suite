import type { ClinicalFindingView } from '@/types/health'
import { explainMedicalTerm } from '@/utils/patient-language'

interface WhatItMeansProps {
  summary?: string
  clinicalInterpretation?: string
  findings?: ClinicalFindingView[]
}

export default function WhatItMeans({ summary, clinicalInterpretation, findings }: WhatItMeansProps) {
  const hasContent = summary || clinicalInterpretation || (findings && findings.length > 0)

  if (!hasContent) return null

  return (
    <div className="space-y-5">
      <h3 className="text-xl font-semibold tracking-tight text-[var(--ink)]">
        这意味着什么
      </h3>

      <div className="space-y-5 text-base leading-8 text-[var(--ink-soft)]">
        {clinicalInterpretation && (
          <p>{clinicalInterpretation}</p>
        )}

        {summary && !clinicalInterpretation && (
          <p>{summary}</p>
        )}

        {findings && findings.length > 0 && (
          <div className="space-y-4">
            {findings.map((finding) => {
              const explanation = explainMedicalTerm(finding.title)
              return (
                <div
                  key={finding.id}
                  className="rounded-[20px] border border-[var(--border)] bg-[var(--surface)] p-5"
                >
                  <p className="font-semibold text-[var(--ink)]">{finding.title}</p>
                  <p className="mt-2">{finding.summary}</p>
                  {explanation && (
                    <p className="mt-2 text-sm text-[var(--ink-muted)]">
                      {explanation}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
