export default function EmptyStateGuide() {
  return (
    <div className="space-y-8 py-8">
      <div className="space-y-4 text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[var(--accent-soft)]">
          <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10 text-[var(--accent)]" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <h3 className="reading-copy text-2xl tracking-tight text-[var(--ink)]">
          Getting started
        </h3>
        <p className="mx-auto max-w-md text-base leading-7 text-[var(--ink-soft)]">
          Upload an ECG image or signal pair and the workspace will build a readable interpretation below.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">Step 1</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">Attach ECG data</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">PNG/JPG image or a matched .dat + .hea signal pair.</p>
        </div>
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">Step 2</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">Add a note</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">Describe symptoms or clinical context for a richer interpretation.</p>
        </div>
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">Step 3</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">Review results</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">The diagnosis report stays in the conversation for reference and export.</p>
        </div>
      </div>
    </div>
  )
}
