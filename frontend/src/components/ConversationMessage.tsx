import type { ConversationMessage as ConversationMessageType } from '@/types/chat'
import { formatConversationTimestamp } from '@/utils'
import DiagnosisReport from './DiagnosisReport'

interface ConversationMessageProps {
  message: ConversationMessageType
}

function renderParagraphs(content: string, className: string) {
  return content.split('\n').filter(Boolean).map((paragraph, index) => (
    <p key={`${paragraph}-${index}`} className={className}>
      {paragraph}
    </p>
  ))
}

export default function ConversationMessage({ message }: ConversationMessageProps) {
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

          {message.result ? <DiagnosisReport result={message.result} /> : null}
        </div>
      </div>
    </article>
  )
}
