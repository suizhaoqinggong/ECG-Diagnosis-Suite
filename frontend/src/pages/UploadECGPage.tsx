import { useCallback } from 'react'
import { useWorkspaceController } from '@/controllers/useWorkspaceController'
import ConversationMessage from '@/components/ConversationMessage'
import EmptyStateGuide from '@/components/EmptyStateGuide'
import { formatFileSize } from '@/utils'

function UploadCloudIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 19H9a7 7 0 116.72-9.99A5 5 0 1117.5 19z" />
      <path d="M12 12v7M9 16l3 3 3-3" />
    </svg>
  )
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

function ArrowUpIcon() {
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

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  )
}

export default function UploadECGPage() {
  const {
    state,
    dispatch,
    activeSession,
    isSubmitting,
    submit,
    retry,
    cancelSubmission,
  } = useWorkspaceController()

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dispatch({ type: 'SET_DRAG_ACTIVE', active: true })
  }, [dispatch])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dispatch({ type: 'SET_DRAG_ACTIVE', active: false })
  }, [dispatch])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    dispatch({ type: 'SET_DRAG_ACTIVE', active: false })
    const files = e.dataTransfer.files
    if (files.length > 0) {
      dispatch({ type: 'ADD_FILES', files })
    }
  }, [dispatch])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      dispatch({ type: 'ADD_FILES', files })
    }
    e.target.value = ''
  }, [dispatch])

  const handleRemoveFile = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_FILE', id })
  }, [dispatch])

  const handleDraftChange = useCallback((value: string) => {
    dispatch({ type: 'SET_DRAFT', value })
  }, [dispatch])

  const handleSubmit = useCallback(() => {
    void submit()
  }, [submit])

  if (!activeSession) return null

  const hasUserMessages = activeSession.messages.some(m => m.role === 'user')
  const attachments = state.composer.attachments
  const draft = state.composer.draft
  const validationErrors = state.composer.validationErrors
  const hasContent = draft.trim().length > 0 || attachments.length > 0

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8 md:py-12">
      {/* Page Header */}
      <header className="mb-8 space-y-2">
        <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
          Health Analysis Workspace
        </p>
        <h2 className="reading-copy text-3xl tracking-tight text-[var(--ink)] md:text-[2.5rem]">
          上传健康资料
        </h2>
        <p className="max-w-2xl text-base leading-7 text-[var(--ink-soft)]">
          上传心电图、体检报告或化验单，AI 将为你生成统一的健康分析报告。
        </p>
      </header>

      {/* Upload Zone */}
      <section
        className="relative rounded-[32px] border-2 border-dashed border-[var(--border)] bg-[var(--surface)] p-8 transition md:p-12"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        {state.ui.isDragging && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-[32px] bg-[var(--bg)]/80 backdrop-blur-sm">
            <div className="text-center">
              <p className="reading-copy text-xl text-[var(--accent)]">
                释放文件以上传
              </p>
              <p className="mt-2 text-sm text-[var(--ink-muted)]">
                PDF, PNG, JPG 或 .dat + .hea 信号对
              </p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {attachments.length === 0 ? (
          <div className="text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
              <UploadCloudIcon />
            </div>
            <h3 className="reading-copy mt-4 text-xl font-medium text-[var(--ink)]">
              拖放文件到此处
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              或点击下方按钮选择文件
            </p>
            <label className="mt-6 inline-flex cursor-pointer items-center gap-2 rounded-full border border-[var(--border)] bg-white/80 px-6 py-3 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)] hover:bg-white">
              <AttachmentIcon />
              选择文件
              <input
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.dat,.hea,image/*,application/pdf"
                className="hidden"
                onChange={handleFileChange}
                disabled={isSubmitting}
              />
            </label>
          </div>
        ) : (
          /* File list */
          <div className="space-y-4">
            <h3 className="reading-copy text-lg font-medium text-[var(--ink)]">
              已选文件
            </h3>
            <div className="space-y-2">
              {attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between rounded-[18px] border border-[var(--border)] bg-white/70 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
                      <FileIcon />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[var(--ink)]">{attachment.summary.name}</p>
                      <p className="text-xs text-[var(--ink-muted)]">
                        {attachment.summary.category} · {formatFileSize(attachment.summary.size)}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(attachment.id)}
                    disabled={isSubmitting}
                    className="rounded-full p-2 text-[var(--ink-muted)] transition hover:bg-white/80 hover:text-[var(--ink)] disabled:cursor-not-allowed"
                    aria-label={`移除 ${attachment.summary.name}`}
                  >
                    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-[var(--border)] bg-white/60 px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)]">
                <AttachmentIcon />
                添加更多文件
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg,.dat,.hea,image/*,application/pdf"
                  className="hidden"
                  onChange={handleFileChange}
                  disabled={isSubmitting}
                />
              </label>
            </div>
          </div>
        )}
      </section>

      {/* Validation errors */}
      {validationErrors.length > 0 && (
        <div className="mt-4 rounded-[18px] border-l-4 border-l-red-500 border border-[var(--border)] bg-[var(--surface-strong)] p-4">
          <p className="text-sm font-medium text-red-700">文件问题</p>
          <ul className="mt-2 space-y-1">
            {validationErrors.map((error, index) => (
              <li key={`${error}-${index}`} className="text-sm text-[var(--ink-soft)]">{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Supplementary notes */}
      <section className="mt-8">
        <label className="text-sm font-medium text-[var(--ink)]" htmlFor="supplementary-notes">
          补充说明
        </label>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">
          描述症状、背景信息或报告来源，帮助 AI 更准确理解你的资料
        </p>
        <textarea
          id="supplementary-notes"
          value={draft}
          onChange={(e) => handleDraftChange(e.target.value)}
          disabled={isSubmitting}
          rows={4}
          placeholder="例如：这是我今年3月的体检报告，想了解血脂指标的含义。最近偶尔感到胸闷。"
          className="reading-copy mt-3 w-full resize-none rounded-[22px] border border-[var(--border)] bg-[var(--surface)] px-5 py-4 text-[1.05rem] leading-8 text-[var(--ink)] outline-none placeholder:text-[var(--ink-muted)] transition focus:border-[var(--border-strong)] focus:bg-white/80 disabled:cursor-not-allowed"
        />
      </section>

      {/* Format hints */}
      <div className="mt-8 flex flex-wrap items-center gap-3 text-xs text-[var(--ink-muted)]">
        <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1">PDF 报告</span>
        <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1">PNG / JPG 图像</span>
        <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1">.dat + .hea 信号对</span>
        <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1">单文件 ≤ 10MB</span>
      </div>

      {/* Submit button */}
      <div className="mt-8 flex items-center justify-end gap-4">
        <p className="text-xs uppercase tracking-[0.22em] text-[var(--ink-muted)]">
          {isSubmitting ? '分析中...' : 'Ctrl/Cmd + Enter 发送'}
        </p>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || !hasContent}
          className="inline-flex items-center gap-2 rounded-full bg-[#2f2b26] px-6 py-3 text-sm font-medium text-white transition hover:bg-[#1f1c18] disabled:cursor-not-allowed disabled:bg-[#b7aa9b]"
        >
          <ArrowUpIcon />
          {isSubmitting ? '分析中' : '开始分析'}
        </button>
      </div>

      {/* Submission error */}
      {state.submission.phase === 'failed' && state.submission.error && (
        <div className="mt-6 rounded-[18px] border-l-4 border-l-red-500 border border-[var(--border)] bg-[var(--surface-strong)] p-5">
          <p className="text-sm font-medium text-red-700">分析失败</p>
          <p className="mt-1 text-sm text-[var(--ink-soft)]">{state.submission.error}</p>
          {state.submission.canRetry && (
            <button
              onClick={() => { void retry() }}
              className="mt-3 rounded-full bg-[#2f2b26] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#1f1c18]"
            >
              重试
            </button>
          )}
        </div>
      )}

      {/* Conversation Messages / Results */}
      <section className="mt-12 border-t border-[var(--border)] pt-8">
        {!hasUserMessages ? (
          <EmptyStateGuide />
        ) : (
          activeSession.messages.map((message) => (
            <ConversationMessage
              key={message.id}
              message={message}
              submissionPhase={
                message.status === 'pending'
                  ? (state.submission.phase as 'uploading' | 'processing' | 'idle')
                  : undefined
              }
              uploadProgress={state.submission.progress}
              onRetry={message.status === 'error' ? retry : undefined}
              onCancel={message.status === 'pending' ? cancelSubmission : undefined}
            />
          ))
        )}
      </section>

      {/* Medical disclaimer */}
      <footer className="mt-12 rounded-[18px] border border-[var(--border)] bg-[var(--accent-soft)]/40 p-4 text-center">
        <p className="text-xs leading-6 text-[var(--ink-muted)]">
          本页面的分析结果仅供健康参考和教育目的，不能替代专业医疗诊断、治疗或用药建议。如有健康问题，请咨询正规医疗机构。
        </p>
      </footer>
    </div>
  )
}
