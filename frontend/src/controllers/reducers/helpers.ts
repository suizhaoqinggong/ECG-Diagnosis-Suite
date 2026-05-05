import type { ChatSession, ConversationMessage, AttachedFileSummary } from '@/types/chat'
import { STORAGE_VERSION } from '@/utils/storage'
import type { PendingAttachment, WorkspaceState } from './types'

export function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    crypto.getRandomValues(bytes)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
    return [
      hex.slice(0, 8),
      hex.slice(8, 12),
      hex.slice(12, 16),
      hex.slice(16, 20),
      hex.slice(20),
    ].join('-')
  }

  return '00000000-0000-4000-8000-000000000000'
}

export function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()
  if (lowerName.endsWith('.pdf')) return 'report_pdf'
  if (lowerName.endsWith('.dat')) return 'dat'
  if (lowerName.endsWith('.hea')) return 'hea'
  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) {
    if (/(^|[\W_])(ecg|cardio|lead|心电图)([\W_]|$)/i.test(lowerName)) {
      return 'ecg_image'
    }
    return 'report_image'
  }
  return null
}

export function createEmptySession(): ChatSession {
  const timestamp = new Date().toISOString()
  return {
    id: createId(),
    title: 'New analysis',
    preview: 'Start with an ECG file or a clinical note.',
    updatedAt: timestamp,
    messages: [{
      id: createId(),
      role: 'assistant',
      type: 'intro',
      title: 'A calmer space for ECG review',
      content: 'Upload an ECG image or a matched .dat + .hea pair and the workspace will keep the full interpretation in a readable, document-like flow.\n\nUse the note area to add context before submission. Your diagnosis history stays in the left sidebar so each review feels like opening a draft, not scanning a message thread.',
      createdAt: timestamp,
      status: 'completed',
    }],
  }
}

export function calculatePairStatus(
  attachments: PendingAttachment[],
): WorkspaceState['composer']['pairStatus'] {
  const hasImage = attachments.some(
    a => a.summary.category === 'report_image' || a.summary.category === 'ecg_image',
  )
  const hasDat = attachments.some(a => a.summary.category === 'dat')
  const hasHea = attachments.some(a => a.summary.category === 'hea')
  if (hasDat && hasHea) {
    const datName = attachments.find(a => a.summary.category === 'dat')!.file.name.replace(/\.dat$/i, '')
    const heaName = attachments.find(a => a.summary.category === 'hea')!.file.name.replace(/\.hea$/i, '')
    return datName === heaName ? 'matched' : 'mismatch'
  }
  if (hasDat || hasHea) return 'partial'
  if (hasImage || attachments.some(a => a.summary.category === 'report_pdf')) return 'image'
  return 'empty'
}

export function validateAttachments(attachments: PendingAttachment[]): string[] {
  const errors: string[] = []
  const hasImage = attachments.some(
    a => a.summary.category === 'report_image' || a.summary.category === 'ecg_image',
  )
  const hasDat = attachments.some(a => a.summary.category === 'dat')
  const hasHea = attachments.some(a => a.summary.category === 'hea')

  if (!hasImage && (hasDat || hasHea) && !(hasDat && hasHea)) {
    errors.push('Signal analysis needs both files in the pair. Attach one .dat file and the matching .hea header.')
  }
  if (hasDat && hasHea) {
    const datName = attachments.find(a => a.summary.category === 'dat')!.file.name.replace(/\.dat$/i, '')
    const heaName = attachments.find(a => a.summary.category === 'hea')!.file.name.replace(/\.hea$/i, '')
    if (datName !== heaName) {
      errors.push('The .dat and .hea filenames need to match exactly before upload.')
    }
  }
  return errors
}

export function sortSessions(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort(
    (left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt),
  )
}

export function buildSessionPreview(messages: ConversationMessage[]): string {
  const candidate = [...messages]
    .reverse()
    .find(message => message.type !== 'intro' && message.content.trim().length > 0)

  if (candidate) {
    return candidate.title?.trim() || candidate.content.trim()
  }

  return 'Start with an ECG file or a clinical note.'
}

function cloneEmptySession(): ChatSession {
  return createEmptySession()
}

export function createInitialState(): WorkspaceState {
  const initialSession = cloneEmptySession()
  return {
    persisted: {
      sessions: [initialSession],
      activeSessionId: initialSession.id,
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    },
    composer: {
      draft: '',
      attachments: [],
      pairStatus: 'empty',
      validationErrors: [],
      replacedFileNames: [],
    },
    submission: {
      activeMessageId: null,
      phase: 'idle',
      progress: null,
      error: null,
      canRetry: false,
    },
    ui: {
      isDragging: false,
      renamingSessionId: null,
      printableMessageId: null,
      storageWarning: null,
    },
  }
}
