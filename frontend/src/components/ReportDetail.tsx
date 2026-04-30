import { useState } from 'react'
import toast from 'react-hot-toast'
import type { ChatSession } from '@/types/chat'
import { copyToClipboard } from '@/utils/clipboard'
import ConversationMessage from './ConversationMessage'

interface ReportDetailProps {
  session: ChatSession | null
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  onBack?: () => void
}

function hasMeaningfulReport(session: ChatSession): boolean {
  return session.messages.some((m) => m.type !== 'intro')
}

function formatHealthResultForCopy(session: ChatSession): string {
  const lines: string[] = []
  lines.push(`报告: ${session.title}`)
  lines.push('')

  for (const message of session.messages) {
    if (message.type === 'intro') continue
    if (message.role === 'user') {
      lines.push(`--- 提交记录 ---`)
      lines.push(message.content)
      lines.push('')
      continue
    }
    if (message.result) {
      const r = message.result
      if ('overallRisk' in r) {
        lines.push(`总体风险: ${r.overallRisk}`)
        lines.push(`总结: ${r.summary}`)
        if (r.findings && r.findings.length > 0) {
          lines.push('')
          lines.push('发现:')
          for (const f of r.findings) {
            lines.push(
              `  - ${f.title}: ${f.summary} [${f.severity}]`,
            )
          }
        }
        if (r.nextSteps && r.nextSteps.length > 0) {
          lines.push('')
          lines.push('后续步骤:')
          for (const s of r.nextSteps) {
            lines.push(`  - ${s}`)
          }
        }
        if (r.limitations && r.limitations.length > 0) {
          lines.push('')
          lines.push('局限性:')
          for (const l of r.limitations) {
            lines.push(`  - ${l}`)
          }
        }
        lines.push('')
        lines.push(r.disclaimer)
      } else if ('prediction' in r) {
        lines.push(`诊断: ${r.prediction}`)
        lines.push(`置信度: ${Math.round(r.confidence * 100)}%`)
        if (r.severity) lines.push(`严重程度: ${r.severity}`)
        if (r.icd_code) lines.push(`ICD: ${r.icd_code}`)
        if (r.report?.summary) {
          lines.push(`总结: ${r.report.summary}`)
        }
        lines.push('')
        lines.push(r.disclaimer)
      }
    }
  }

  return lines.join('\n')
}

export default function ReportDetail({
  session,
  onRename,
  onDelete,
  onBack,
}: ReportDetailProps) {
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameTitle, setRenameTitle] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [copied, setCopied] = useState(false)

  if (!session || !hasMeaningfulReport(session)) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--ink-muted)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="mx-auto mb-3"
          >
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          <p className="text-sm text-[var(--ink-muted)]">
            选择一份报告查看详情
          </p>
        </div>
      </div>
    )
  }

  const handleRenameStart = () => {
    setRenameTitle(session.title)
    setIsRenaming(true)
  }

  const handleRenameSubmit = () => {
    const trimmed = renameTitle.trim()
    if (trimmed && trimmed !== session.title) {
      onRename(session.id, trimmed)
    }
    setIsRenaming(false)
    setRenameTitle('')
  }

  const handleRenameCancel = () => {
    setIsRenaming(false)
    setRenameTitle('')
  }

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleRenameSubmit()
    if (e.key === 'Escape') handleRenameCancel()
  }

  const handleDelete = () => {
    onDelete(session.id)
    setShowDeleteConfirm(false)
  }

  const handleCopy = async () => {
    const text = formatHealthResultForCopy(session)
    const success = await copyToClipboard(text)
    if (success) {
      setCopied(true)
      toast.success('报告已复制')
      setTimeout(() => setCopied(false), 2000)
    } else {
      toast.error('复制失败')
    }
  }

  const handleExport = () => {
    window.print()
  }

  const reportMessages = session.messages.filter(
    (m) => m.type !== 'intro',
  )

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] px-6 py-4">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="shrink-0 rounded-full p-1.5 text-[var(--ink-muted)] transition hover:bg-[var(--surface)] hover:text-[var(--ink)]"
              aria-label="返回列表"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M12 4l-6 6 6 6" />
              </svg>
            </button>
          )}

          {isRenaming ? (
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <input
                type="text"
                value={renameTitle}
                onChange={(e) => setRenameTitle(e.target.value)}
                onKeyDown={handleRenameKeyDown}
                className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-sm font-semibold text-[var(--ink)] focus:border-[var(--accent)] focus:outline-none"
                autoFocus
              />
              <button
                type="button"
                onClick={handleRenameSubmit}
                className="shrink-0 text-xs font-medium text-[var(--accent)] hover:underline"
              >
                保存
              </button>
              <button
                type="button"
                onClick={handleRenameCancel}
                className="shrink-0 text-xs text-[var(--ink-muted)] hover:underline"
              >
                取消
              </button>
            </div>
          ) : (
            <h2
              role="button"
              tabIndex={0}
              onClick={handleRenameStart}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameStart()
              }}
              className="min-w-0 cursor-pointer truncate text-sm font-semibold text-[var(--ink)] transition hover:text-[var(--accent)]"
              title="点击重命名"
            >
              {session.title}
            </h2>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-full p-1.5 text-[var(--ink-muted)] transition hover:bg-[var(--surface)] hover:text-[var(--ink)]"
            aria-label="复制报告"
          >
            {copied ? (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M3 8l3 3 7-7" />
              </svg>
            ) : (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="5" y="5" width="9" height="9" rx="1" />
                <path d="M11 5V3a1 1 0 00-1-1H3a1 1 0 00-1 1v7a1 1 0 001 1h2" />
              </svg>
            )}
          </button>

          <button
            type="button"
            onClick={handleExport}
            className="rounded-full p-1.5 text-[var(--ink-muted)] transition hover:bg-[var(--surface)] hover:text-[var(--ink)]"
            aria-label="打印报告"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M4 6V2h8v4M4 11H3a1 1 0 01-1-1V7a1 1 0 011-1h10a1 1 0 011 1v3a1 1 0 01-1 1h-1" />
              <rect x="4" y="9" width="8" height="5" rx="1" />
            </svg>
          </button>

          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="rounded-full p-1.5 text-[var(--ink-muted)] transition hover:bg-red-50 hover:text-red-600"
            aria-label="删除报告"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M2 4h12M5 4V3a1 1 0 011-1h4a1 1 0 011 1v1M6 7v5M10 7v5M3 4l1 9a1 1 0 001 1h6a1 1 0 001-1l1-9" />
            </svg>
          </button>
        </div>
      </div>

      {/* Report content */}
      <div className="flex-1 overflow-y-auto">
        {reportMessages.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-[var(--ink-muted)]">
              暂无报告内容
            </p>
          </div>
        ) : (
          reportMessages.map((message) => (
            <ConversationMessage key={message.id} message={message} />
          ))
        )}
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/20"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="mx-4 max-w-sm rounded-[24px] border border-[var(--border)] bg-white p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-[var(--ink)]">
              删除报告
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              确定要删除「{session.title}
              」吗？此操作无法撤销。
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-[var(--surface)]"
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-600"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
