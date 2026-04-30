interface NextStepsChecklistProps {
  recommendations?: string[]
  followUp?: string[]
  nextSteps?: string[]
}

export default function NextStepsChecklist({ recommendations, followUp, nextSteps }: NextStepsChecklistProps) {
  const allSteps: string[] = [
    ...(nextSteps || []),
    ...(recommendations || []),
    ...(followUp || []),
  ]

  const uniqueSteps = [...new Set(allSteps)].filter(Boolean)

  if (uniqueSteps.length === 0) return null

  return (
    <div className="space-y-5">
      <h3 className="text-xl font-semibold tracking-tight text-[var(--ink)]">
        下一步建议
      </h3>

      <div className="space-y-3">
        {uniqueSteps.map((step, index) => (
          <div
            key={`${step}-${index}`}
            className="flex items-start gap-3 rounded-[20px] border border-[var(--border)] bg-[var(--surface)] p-4"
          >
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-xs font-semibold text-[var(--accent)]">
              {index + 1}
            </span>
            <p className="text-base leading-7 text-[var(--ink-soft)]">{step}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
