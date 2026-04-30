import type { ClinicalFindingView } from '@/types/health'
import { generateDoctorQuestions } from '@/utils/patient-language'

interface DoctorQuestionsProps {
  findings?: ClinicalFindingView[]
}

export default function DoctorQuestions({ findings }: DoctorQuestionsProps) {
  const questions = generateDoctorQuestions(findings || [])

  if (questions.length === 0) return null

  return (
    <div className="space-y-5">
      <h3 className="text-xl font-semibold tracking-tight text-[var(--ink)]">
        可以问医生的问题
      </h3>

      <p className="text-sm text-[var(--ink-muted)]">
        以下问题可以帮助您在就诊时与医生更高效地沟通
      </p>

      <div className="space-y-3">
        {questions.map((question, index) => (
          <div
            key={index}
            className="flex items-start gap-3 rounded-[20px] border border-[var(--border)] bg-[var(--accent-soft)]/50 p-4"
          >
            <svg viewBox="0 0 24 24" fill="none" className="mt-0.5 h-5 w-5 shrink-0 text-[var(--accent)]" aria-hidden="true">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.6"/>
              <path d="M9 9.5c0-1.5 1.2-3 3-3s3 1.5 3 3c0 1.8-2 2.5-2 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
              <circle cx="12" cy="18" r="1" fill="currentColor"/>
            </svg>
            <p className="text-base leading-7 text-[var(--ink-soft)]">{question}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
