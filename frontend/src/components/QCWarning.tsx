import { useState } from 'react'
import type { PerLeadQC } from '@/types/chat'

interface QCWarningProps {
  quality_warning?: 'pass' | 'warn' | 'fail' | null
  pipeline_warnings?: string[]
  per_lead_qc?: PerLeadQC[]
}

function getQualityBadgeLabel(quality: QCWarningProps['quality_warning']) {
  if (quality === 'fail') return 'Low Reliability'
  if (quality === 'warn') return 'Needs Review'
  return 'Quality Check'
}

function getQualityClasses(quality: QCWarningProps['quality_warning']) {
  if (quality === 'fail') {
    return 'border-red-200 bg-red-50 text-red-800'
  }
  if (quality === 'warn') {
    return 'border-amber-200 bg-amber-50 text-amber-800'
  }
  return 'border-gray-200 bg-gray-50 text-gray-800'
}

function getLeadQualityClasses(quality: PerLeadQC['quality']) {
  switch (quality) {
    case 'good':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'warn':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'poor':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'fail':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

export default function QCWarning({
  quality_warning,
  pipeline_warnings = [],
  per_lead_qc,
}: QCWarningProps) {
  const [expanded, setExpanded] = useState(false)
  const effectiveQuality =
    quality_warning === 'warn' || quality_warning === 'fail'
      ? quality_warning
      : pipeline_warnings.length > 0
        ? 'warn'
        : quality_warning

  if (!effectiveQuality || effectiveQuality === 'pass') {
    return null
  }

  const hasPerLeadData = per_lead_qc && per_lead_qc.length > 0

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${getQualityClasses(effectiveQuality)}`}
      role="alert"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wider">
          {getQualityBadgeLabel(effectiveQuality)}
        </span>
        <span className="rounded-full border border-current/20 px-2 py-0.5 text-xs font-semibold uppercase">
          {effectiveQuality}
        </span>
      </div>

      {pipeline_warnings.length > 0 && (
        <div className="mt-2 space-y-1">
          {pipeline_warnings.map((warning, index) => (
            <p key={`${warning}-${index}`} className="text-sm">
              {warning}
            </p>
          ))}
        </div>
      )}

      {hasPerLeadData && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm font-medium underline underline-offset-2 hover:opacity-80"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide Details' : 'View Details'}
          </button>

          {expanded && (
            <div className="mt-3 space-y-2">
              {per_lead_qc!.map((lead) => (
                <div
                  key={lead.lead_index}
                  data-lead-index={lead.lead_index}
                  data-quality={lead.quality}
                  className={`flex items-center justify-between rounded border p-2 ${getLeadQualityClasses(lead.quality)}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Lead {lead.lead_index}</span>
                    <span className="rounded px-1.5 py-0.5 text-xs uppercase">
                      {lead.quality}
                    </span>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span>Coverage: {Math.round(lead.coverage * 100)}%</span>
                    <span>Flatness: {Math.round(lead.flatness * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
