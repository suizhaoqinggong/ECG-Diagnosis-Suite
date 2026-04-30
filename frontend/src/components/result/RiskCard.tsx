import type { HealthRiskLevel } from '@/types/health'
import { mapRiskToPatientLabel, mapRiskToReason } from '@/utils/patient-language'

interface RiskCardProps {
  riskLevel: HealthRiskLevel
  reason?: string
}

const riskIcons: Record<HealthRiskLevel, string> = {
  low: '●',
  medium: '◉',
  high: '◉',
  urgent: '⬤',
}

const riskBorderColors: Record<HealthRiskLevel, string> = {
  low: 'border-l-green-500',
  medium: 'border-l-yellow-500',
  high: 'border-l-orange-500',
  urgent: 'border-l-red-500',
}

const riskBadgeStyles: Record<HealthRiskLevel, string> = {
  low: 'bg-green-50 text-green-700',
  medium: 'bg-yellow-50 text-yellow-700',
  high: 'bg-orange-50 text-orange-700',
  urgent: 'bg-red-50 text-red-700',
}

export default function RiskCard({ riskLevel, reason }: RiskCardProps) {
  const label = mapRiskToPatientLabel(riskLevel)
  const defaultReason = mapRiskToReason(riskLevel)
  const displayReason = reason || defaultReason

  return (
    <div
      className={`rounded-[24px] border border-[var(--border)] border-l-4 ${riskBorderColors[riskLevel]} bg-[var(--surface-strong)] p-6`}
      role="alert"
    >
      <div className="flex items-start gap-4">
        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${riskBadgeStyles[riskLevel]}`}>
          <span aria-hidden="true">{riskIcons[riskLevel]}</span>
          {label}
        </span>
      </div>
      {displayReason && (
        <p className="mt-3 text-base leading-7 text-[var(--ink-soft)]">
          {displayReason}
        </p>
      )}
    </div>
  )
}
