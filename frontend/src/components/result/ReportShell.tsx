import type { ReactNode } from 'react'

interface ReportShellProps {
  children: ReactNode
  className?: string
}

const SHELL_BASE =
  'printable-report space-y-8 rounded-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_16px_40px_rgba(84,69,53,0.06)] md:p-8'

export default function ReportShell({ children, className = '' }: ReportShellProps) {
  return <section className={`${SHELL_BASE} ${className}`.trim()}>{children}</section>
}
