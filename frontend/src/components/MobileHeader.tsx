export default function MobileHeader({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <div className="border-b border-[var(--border)] px-4 py-4 lg:hidden">
      <div className="flex items-center justify-between">
        <button
          onClick={onMenuClick}
          className="rounded p-2 text-[var(--ink)] hover:bg-white/60"
          aria-label="Open menu"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <h1 className="text-lg font-semibold text-[var(--ink)]">
          Diagnosis Studio
        </h1>

        <div className="w-10" />
      </div>
    </div>
  )
}
