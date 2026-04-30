interface ConclusionHeroProps {
  title: string
  summary?: string
  reportType: string
  sourceType?: string
  timestamp?: string
}

export default function ConclusionHero({ title, summary, reportType, sourceType, timestamp }: ConclusionHeroProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {sourceType && (
          <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-muted)]">
            {sourceType}
          </span>
        )}
        <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-muted)]">
          {reportType}
        </span>
        {timestamp && (
          <span className="text-xs text-[var(--ink-muted)]">
            {timestamp}
          </span>
        )}
      </div>

      <h2 className="text-3xl font-semibold leading-tight tracking-tight text-[var(--ink)] md:text-4xl">
        {title}
      </h2>

      {summary && (
        <p className="text-lg leading-8 text-[var(--ink-soft)]">
          {summary}
        </p>
      )}
    </div>
  )
}
