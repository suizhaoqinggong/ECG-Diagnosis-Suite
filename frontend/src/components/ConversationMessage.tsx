import { memo } from 'react'
import type { ConversationMessage as ConversationMessageType } from '@/types/chat'
import { formatConversationTimestamp } from '@/utils'
import DiagnosisReport from './DiagnosisReport'

interface ConversationMessageProps {
  message: ConversationMessageType
  submissionPhase?: 'uploading' | 'processing' | 'idle'
  uploadProgress?: number | null
  onRetry?: () => void
  onCancel?: () => void
}

function renderParagraphs(content: string, className: string) {
  return content.split('\n').filter(Boolean).map((paragraph, index) => (
    <p key={`${paragraph}-${index}`} className={className}>
      {paragraph}
    </p>
  ))
}

function PendingIndicator({ phase, progress }: { phase: 'uploading' | 'processing'; progress: number | null }) {
  if (phase === 'uploading') {
    return (
      <div className="space-y-3">
        <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
          Uploading files...
        </p>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">
          <div
            className="h-full bg-[var(--accent)] transition-all duration-300"
            style={{ width: `${progress ?? 0}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4">
      <div className="ecg-pulse w-12 h-12" aria-label="Processing">
        <svg viewBox="0 0 48 48" className="h-full w-full">
          <path
            d="M4 24h8l4-12 4 24 4-12 4 12h8"
            stroke="var(--accent)"
            strokeWidth="2"
            fill="none"
            className="ecg-wave"
          />
        </svg>
      </div>
      <p className="reading-copy text-lg text-[var(--ink-soft)]">
        AI is analyzing ECG data...
      </p>
    </div>
  )
}

function ErrorMessage({ errorDetail, onRetry }: { errorDetail: string; onRetry?: () => void }) {
  return (
    <div className="rounded-[30px] border-l-4 border-l-red-500 border border-[var(--border)] bg-[var(--surface-strong)] p-6">
      <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
        Analysis Failed
      </p>
      <p className="reading-copy mt-3 text-lg text-[var(--ink-soft)]">
        {errorDetail}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-full bg-[#2f2b26] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#1f1c18]"
        >
          Retry
        </button>
      )}
    </div>
  )
}

function ConversationMessage({ message, submissionPhase, uploadProgress, onRetry, onCancel }: ConversationMessageProps) {
  const roleLabel = message.role === 'assistant' ? 'ECG Analyst' : 'You'

  return (
    <article className="border-b border-[var(--border)] py-10 last:border-b-0 md:py-14">
      <div className="grid gap-4 md:grid-cols-[132px_minmax(0,1fr)] md:gap-8">
        <div className="space-y-2">
          <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">
            {roleLabel}
          </p>
          <p className="text-sm text-[var(--ink-muted)]">
            {formatConversationTimestamp(message.createdAt)}
          </p>
        </div>

        <div className="space-y-6">
          {message.title ? (
            <header className="space-y-3">
              <h2 className="reading-copy text-3xl leading-tight tracking-tight text-[var(--ink)] md:text-[2.2rem]">
                {message.title}
              </h2>
            </header>
          ) : null}

          <div className="prose-block reading-copy text-[1.08rem] leading-8 text-[var(--ink-soft)] md:text-[1.16rem]">
            {renderParagraphs(message.content, '')}
          </div>

          {message.attachments && message.attachments.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {message.attachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-[var(--ink-soft)]"
                >
                  {attachment.category} · {attachment.name}
                </span>
              ))}
            </div>
          ) : null}

          {message.type === 'diagnosis' && message.status === 'pending' ? (
            <div className="rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)]">
              <PendingIndicator phase={submissionPhase === 'processing' ? 'processing' : 'uploading'} progress={uploadProgress ?? null} />
              {onCancel && (
                <button
                  onClick={onCancel}
                  className="mt-4 rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/60"
                >
                  Cancel
                </button>
              )}
            </div>
          ) : message.status === 'error' ? (
            <ErrorMessage errorDetail={message.errorDetail || 'Unknown error'} onRetry={onRetry} />
          ) : message.result ? (
            <DiagnosisReport result={message.result} />
          ) : null}
        </div>
      </div>
    </article>
  )
}

export default memo(ConversationMessage)
