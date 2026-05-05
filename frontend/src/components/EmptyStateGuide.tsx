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
          开始使用
        </h3>
        <p className="mx-auto max-w-md text-base leading-7 text-[var(--ink-soft)]">
          上传心电图图像或信号对，工作区将在下方生成可读的分析报告。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">步骤 1</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">上传心电数据</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">PNG/JPG 图像或匹配的 .dat + .hea 信号对。</p>
        </div>
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">步骤 2</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">添加备注</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">描述症状或临床背景，获得更丰富的解读。</p>
        </div>
        <div className="rounded-[22px] border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">步骤 3</p>
          <p className="mt-2 reading-copy text-base font-medium text-[var(--ink)]">查看结果</p>
          <p className="mt-1 text-sm leading-6 text-[var(--ink-soft)]">诊断报告保留在对话中，可随时查看和导出。</p>
        </div>
      </div>
    </div>
  )
}
