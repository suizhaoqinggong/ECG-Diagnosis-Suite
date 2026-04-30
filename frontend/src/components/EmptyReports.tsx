import type { NavigationDestination } from '@/types/navigation'

interface EmptyReportsProps {
  onNavigate: (dest: NavigationDestination) => void
}

export default function EmptyReports({ onNavigate }: EmptyReportsProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center p-8">
      <div className="max-w-md space-y-8 text-center">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)]">
          <svg
            width="36"
            height="36"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--ink-muted)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14,2 14,8 20,8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10,9 9,9 8,9" />
          </svg>
        </div>
        <div className="space-y-3">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            我的报告
          </p>
          <h2 className="reading-copy text-3xl leading-tight tracking-tight text-[var(--ink)]">
            这里会保存你读过的报告
          </h2>
          <p className="text-lg leading-8 text-[var(--ink-soft)]">
            上传 ECG 或健康资料进行分析后，报告会自动保存在这里，方便你随时回顾和对比。
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <button
            onClick={() => onNavigate('read-report')}
            className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
          >
            读懂已有报告
          </button>
          <button
            onClick={() => onNavigate('upload-ecg')}
            className="rounded-full border border-[var(--border)] bg-white/60 px-6 py-3 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
          >
            上传 ECG
          </button>
        </div>
      </div>
    </div>
  )
}
