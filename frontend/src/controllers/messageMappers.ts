import type { ConversationMessage, AttachedFileSummary } from '@/types/chat'
import type { DiagnosisResultData } from '@/api'
import type { HealthAnalysisResult } from '@/types/health'
import { chatApi, type MessageCreate, type MessageResponse, type SessionResponse } from '@/api/chat'
import type { ChatSession } from '@/types/chat'
import { createEmptySession, buildSessionPreview } from './reducers/helpers'

// ===== Message mapping =====

export function normalizeMessageStatus(value?: string): ConversationMessage['status'] {
  if (value === 'pending' || value === 'completed' || value === 'error') return value
  return undefined
}

export function mapRemoteMessage(message: MessageResponse): ConversationMessage {
  const content = message.content || ''
  const attachmentPayload = message.attachments as { items?: AttachedFileSummary[] } | null
  const resultPayload = (message.result as Record<string, unknown> | null) ?? null
  const normalizedTitle =
    typeof message.title === 'string' && message.title.trim().length > 0
      ? message.title
      : undefined
  const errorDetail =
    message.status === 'error' && typeof resultPayload?.errorDetail === 'string'
      ? resultPayload.errorDetail
      : undefined
  return {
    id: message.id,
    role: message.role === 'assistant' ? 'assistant' : 'user',
    type:
      message.type === 'intro' ||
      message.type === 'prompt' ||
      message.type === 'guidance' ||
      message.type === 'diagnosis' ||
      message.type === 'health_report'
        ? message.type
        : 'prompt',
    title: normalizedTitle,
    content,
    createdAt: message.created_at,
    attachments: Array.isArray(attachmentPayload?.items)
      ? attachmentPayload.items
      : undefined,
    result: (resultPayload as DiagnosisResultData | HealthAnalysisResult | null) ?? undefined,
    status: normalizeMessageStatus(message.status) ?? 'completed',
    errorDetail,
  }
}

export function buildSessionFromRemote(
  session: SessionResponse,
  messages: MessageResponse[],
): ChatSession {
  const mappedMessages = messages.map(mapRemoteMessage)
  const finalMessages = mappedMessages.length > 0 ? mappedMessages : createEmptySession().messages

  return {
    id: session.id,
    title: session.title,
    updatedAt: session.updated_at,
    messages: finalMessages,
    preview: buildSessionPreview(finalMessages),
  }
}

export function mapLocalMessageToRemote(message: ConversationMessage): MessageCreate {
  return {
    id: message.id,
    role: message.role,
    type: message.type,
    title: message.title ?? null,
    content: message.content,
    attachments: message.attachments ? { items: message.attachments } : null,
    result: (message.result as Record<string, unknown> | null | undefined) ?? null,
    result_schema_version: message.result ? 1 : null,
    status: message.status ?? 'completed',
  }
}

export async function fetchAllSessionMessages(sessionId: string): Promise<MessageResponse[]> {
  const messages: MessageResponse[] = []
  let cursor: string | undefined

  for (;;) {
    const page = await chatApi.listMessages(sessionId, cursor, 100)
    messages.push(...page)
    if (page.length < 100) break
    const last = page[page.length - 1]
    cursor = `${last.created_at},${last.id}`
  }

  return messages
}
