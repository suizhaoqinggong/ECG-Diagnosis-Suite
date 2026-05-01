import type { ChatSession } from '@/types/chat'
import type { HealthRiskLevel, HealthAnalysisResult } from '@/types/health'
import type { DiagnosisResultData } from '@/api'
import { formatSidebarTimestamp } from '@/utils'
import { mapDiagnosisSeverityToRisk } from '@/utils/severity'

function getReportRiskLevel(session: ChatSession): HealthRiskLevel | null {
  const lastResult = [...session.messages]
    .reverse()
    .find((m) => m.role === 'assistant' && m.result != null)

  if (!lastResult?.result) return null

  if ('overallRisk' in lastResult.result) {
    return (lastResult.result as HealthAnalysisResult).overallRisk
  }
  if ('severity' in lastResult.result) {
    return mapDiagnosisSeverityToRisk((lastResult.result as DiagnosisResultData).severity)
  }
  return null
}

function getReportSourceType(session: ChatSession): string {
  const hasHealth = session.messages.some((m) => m.type === 'health_report')
  const hasDiagnosis = session.messages.some((m) => m.type === 'diagnosis')
  if (hasHealth) return '健康分析'
  if (hasDiagnosis) return 'ECG'
  return '报告'
}

const RISK_LABELS: Record<string, { label: string; badgeClass: string }> = {
  low: {
    label: '低风险',
    badgeClass:
      'bg-green-50 text-green-700 border-green-200',
  },
  medium: {
    label: '中风险',
    badgeClass:
      'bg-yellow-50 text-yellow-700 border-yellow-200',
  },
  high: {
    label: '高风险',
    badgeClass:
      'bg-orange-50 text-orange-700 border-orange-200',
  },
  urgent: {
    label: '紧急',
    badgeClass: 'bg-red-50 text-red-600 border-red-200',
  },
}

interface ReportListItemProps {
  session: ChatSession
  isSelected: boolean
  onSelect: (id: string) => void
}

export default function ReportListItem({
  session,
  isSelected,
  onSelect,
}: ReportListItemProps) {
  const riskLevel = getReportRiskLevel(session)
  const sourceType = getReportSourceType(session)
  const riskInfo = riskLevel ? RISK_LABELS[riskLevel] : null

  return (
    <button
      type="button"
      onClick={() => onSelect(session.id)}
      className={`w-full text-left px-5 py-4 transition border-b border-[var(--border)] ${
        isSelected
          ? 'bg-[var(--surface-strong)] border-l-[3px] border-l-[var(--accent)]'
          : 'hover:bg-[var(--surface)] border-l-[3px] border-l-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1.5">
          <h3 className="text-sm font-semibold text-[var(--ink)] truncate">
            {session.title}
          </h3>
          <p className="text-xs leading-5 text-[var(--ink-muted)] line-clamp-2">
            {session.preview}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[0.65rem] text-[var(--ink-muted)]">
              {formatSidebarTimestamp(session.updatedAt)}
            </span>
            <span className="text-[0.65rem] uppercase tracking-[0.12em] text-[var(--ink-muted)]">
              {sourceType}
            </span>
          </div>
        </div>
        {riskInfo && (
          <span
            className={`shrink-0 rounded-full border px-2 py-0.5 text-[0.65rem] font-medium ${riskInfo.badgeClass}`}
          >
            {riskInfo.label}
          </span>
        )}
      </div>
    </button>
  )
}
