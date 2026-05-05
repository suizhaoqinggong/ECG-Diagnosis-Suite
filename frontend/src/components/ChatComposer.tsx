import { memo } from 'react'
import type { ChangeEvent, ClipboardEvent, KeyboardEvent } from 'react'
import type { AttachedFileSummary } from '../types/chat'
import { formatFileSize } from '../utils'

interface ChatComposerProps {
  draft: string
  attachedFiles: AttachedFileSummary[]
  isLoading: boolean
  onDraftChange: (value: string) => void
  onAttachFiles: (files: File[] | null) => void
  onRemoveFile: (fileId: string) => void
  onSubmit: () => void
}

function AttachmentIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M8.5 12.5 14 7a3 3 0 1 1 4.24 4.24l-8.13 8.13a5 5 0 1 1-7.07-7.07L12 3.47"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path
        d="M12 5v14M6 11l6-6 6 6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const ChatComposer = memo(function ChatComposer({
  draft,
  attachedFiles,
  isLoading,
  onDraftChange,
  onAttachFiles,
  onRemoveFile,
  onSubmit,
}: ChatComposerProps) {
  const hasContent = draft.trim().length > 0 || attachedFiles.length > 0

  const handlePaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = event.clipboardData?.items
    if (!items) return

    for (const item of items) {
      if (item.kind === 'file' && item.type.startsWith('image/')) {
        const blob = item.getAsFile()
        if (!blob) continue
        event.preventDefault()
        const ext = item.type.split('/')[1] || 'png'
        const file = new File([blob], `clipboard-${Date.now()}.${ext}`, { type: item.type })
        onAttachFiles([file])
        return
      }
    }
  }

  const handleKeyboardSubmit = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      onSubmit()
    }
  }

  const handleDataChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : null
    onAttachFiles(files)
    event.target.value = ''
  }

  return (
    <div className="sticky bottom-0 bg-gradient-to-t from-[#f1ebe1] via-[#f1ebe1] to-transparent pt-6">
      <div className="mx-auto max-w-4xl px-4 pb-6 md:px-8">
        <div className="rounded-[32px] border border-[var(--border)] bg-[var(--surface-strong)] p-4 shadow-[0_28px_60px_rgba(84,69,53,0.12)] md:p-5">
          {attachedFiles.length > 0 ? (
            <div className="mb-4 flex flex-wrap gap-2">
              {attachedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-3 rounded-full border border-[var(--border)] bg-[rgba(245,241,234,0.82)] px-3 py-2"
                >
                  <div>
                    <p className="text-sm font-medium text-[var(--ink)]">{file.name}</p>
                    <p className="text-xs text-[var(--ink-muted)]">
                      {file.category} · {formatFileSize(file.size)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemoveFile(file.id)}
                    className="rounded-full p-1 text-[var(--ink-muted)] transition hover:bg-white/80 hover:text-[var(--ink)]"
                    aria-label={`移除 ${file.name}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <textarea
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleKeyboardSubmit}
            onPaste={handlePaste}
            disabled={isLoading}
            rows={4}
            placeholder="描述检查内容、添加备注或上传健康文件开始分析。"
            className="reading-copy min-h-[120px] w-full resize-none border-0 bg-transparent px-1 text-[1.05rem] leading-8 text-[var(--ink)] outline-none placeholder:text-[var(--ink-muted)] disabled:cursor-not-allowed"
          />

          <div className="mt-4 flex flex-col gap-4 border-t border-[var(--border)] pt-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-[var(--border)] bg-[rgba(255,255,255,0.6)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)]">
                <AttachmentIcon />
                上传健康文件
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.dat,.hea,image/*,application/pdf"
                  className="hidden"
                  onChange={handleDataChange}
                  disabled={isLoading}
                />
              </label>
            </div>

            <div className="flex items-center justify-between gap-4">
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--ink-muted)]">
                {isLoading ? '正在分析健康数据...' : 'Ctrl/Cmd + Enter 发送'}
              </p>
              <button
                type="button"
                onClick={onSubmit}
                disabled={isLoading || !hasContent}
                className="inline-flex items-center gap-2 rounded-full bg-[#2f2b26] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#1f1c18] disabled:cursor-not-allowed disabled:bg-[#b7aa9b]"
              >
                <ArrowIcon />
                {isLoading ? '分析中' : '发送'}
              </button>
            </div>
          </div>
        </div>

        <p className="mt-3 px-1 text-sm text-[var(--ink-muted)]">
          支持 PDF、PNG、JPG、JPEG 或匹配的 .dat + .hea 信号对。文字备注保留在对话中作为上下文。
        </p>
      </div>
    </div>
  )
})

export default ChatComposer
