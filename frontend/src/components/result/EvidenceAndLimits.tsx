import { formatConfidence } from '@/utils'

interface EvidenceAndLimitsProps {
  confidence?: number
  qualityWarnings?: string[]
  pipelineWarnings?: string[]
  limitations?: string[]
  disclaimer?: string
}

export default function EvidenceAndLimits({
  confidence,
  qualityWarnings,
  pipelineWarnings,
  limitations,
  disclaimer,
}: EvidenceAndLimitsProps) {
  const warnings = [...(pipelineWarnings || []), ...(qualityWarnings || [])]

  return (
    <div className="space-y-5 rounded-[24px] border border-[var(--border)] bg-[var(--bg-muted)]/50 p-6">
      <h3 className="text-lg font-semibold tracking-tight text-[var(--ink)]">
        证据与限制
      </h3>

      <div className="space-y-4 text-sm text-[var(--ink-muted)]">
        {confidence !== undefined && (
          <div className="flex items-center gap-2">
            <span className="font-medium text-[var(--ink-soft)]">模型置信度：</span>
            <span>{formatConfidence(confidence)}</span>
          </div>
        )}

        {warnings.length > 0 && (
          <div className="space-y-2">
            <p className="font-medium text-[var(--ink-soft)]">数据质量提示：</p>
            {warnings.map((warning, i) => (
              <p key={i} className="flex items-start gap-2">
                <span aria-hidden="true">-</span>
                {warning}
              </p>
            ))}
          </div>
        )}

        {limitations && limitations.length > 0 && (
          <div className="space-y-2">
            <p className="font-medium text-[var(--ink-soft)]">分析限制：</p>
            {limitations.map((item, i) => (
              <p key={i} className="flex items-start gap-2">
                <span aria-hidden="true">-</span>
                {item}
              </p>
            ))}
          </div>
        )}

        {disclaimer && (
          <p className="border-t border-[var(--border)] pt-4 text-xs leading-6">
            {disclaimer}
          </p>
        )}
      </div>
    </div>
  )
}
