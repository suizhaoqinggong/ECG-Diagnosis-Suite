/**
 * Protective tests for internal helpers exported from useWorkspaceController.
 *
 * These functions will be extracted into sub-modules during the P0-1 refactoring
 * (frontend controller split). These tests lock in their current behavior so that
 * extraction does not silently change it.
 */
import { describe, it, expect } from 'vitest'
import {
  buildSessionPreview,
  sortSessions,
  normalizeMessageStatus,
  mapRemoteMessage,
  mapLocalMessageToRemote,
  createId,
  createEmptySession,
} from '@/controllers/useWorkspaceController'
import type { ConversationMessage } from '@/types/chat'
import type { MessageResponse } from '@/api/chat'

// ===== buildSessionPreview =====

describe('buildSessionPreview', () => {
  const defaultPreview = 'Start with an ECG file or a clinical note.'

  it('returns default preview for empty messages', () => {
    expect(buildSessionPreview([])).toBe(defaultPreview)
  })

  it('returns default preview when only intro messages exist', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'assistant', type: 'intro', content: '  ', createdAt: new Date().toISOString() },
    ]
    expect(buildSessionPreview(messages)).toBe(defaultPreview)
  })

  it('returns title of the last non-intro message with content', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'assistant', type: 'intro', content: 'Welcome', createdAt: new Date().toISOString() },
      { id: createId(), role: 'user', type: 'prompt', title: 'ECG review #3', content: 'Check this', createdAt: new Date().toISOString() },
    ]
    expect(buildSessionPreview(messages)).toBe('ECG review #3')
  })

  it('falls back to content when title is empty', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'user', type: 'prompt', content: 'Patient presents with chest pain', createdAt: new Date().toISOString() },
    ]
    expect(buildSessionPreview(messages)).toBe('Patient presents with chest pain')
  })

  it('prefers content over title when title is whitespace-only', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'user', type: 'prompt', title: '   ', content: 'Actual content', createdAt: new Date().toISOString() },
    ]
    expect(buildSessionPreview(messages)).toBe('Actual content')
  })

  it('returns the LAST non-intro message (reversed search)', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'assistant', type: 'intro', content: 'Welcome', createdAt: new Date().toISOString() },
      { id: createId(), role: 'user', type: 'prompt', title: 'First review', content: 'Content 1', createdAt: new Date().toISOString() },
      { id: createId(), role: 'user', type: 'prompt', title: 'Second review', content: 'Content 2', createdAt: new Date().toISOString() },
    ]
    // Last non-intro is "Second review"
    expect(buildSessionPreview(messages)).toBe('Second review')
  })

  it('skips messages with empty content', () => {
    const messages: ConversationMessage[] = [
      { id: createId(), role: 'user', type: 'prompt', title: 'Has title', content: '', createdAt: new Date().toISOString() },
      { id: createId(), role: 'user', type: 'prompt', content: 'Non-empty content', createdAt: new Date().toISOString() },
    ]
    // First message has empty content (trimmed), so it's skipped
    expect(buildSessionPreview(messages)).toBe('Non-empty content')
  })
})

// ===== sortSessions =====

describe('sortSessions', () => {
  it('returns empty array unchanged', () => {
    expect(sortSessions([])).toEqual([])
  })

  it('returns single session unchanged', () => {
    const session = createEmptySession()
    expect(sortSessions([session])).toHaveLength(1)
  })

  it('sorts by updatedAt descending (newest first)', () => {
    const old = { ...createEmptySession(), updatedAt: '2024-01-01T00:00:00.000Z' }
    const mid = { ...createEmptySession(), updatedAt: '2024-06-15T12:00:00.000Z' }
    const recent = { ...createEmptySession(), updatedAt: '2025-01-01T00:00:00.000Z' }

    const result = sortSessions([old, recent, mid])
    expect(result[0].updatedAt).toBe('2025-01-01T00:00:00.000Z')
    expect(result[1].updatedAt).toBe('2024-06-15T12:00:00.000Z')
    expect(result[2].updatedAt).toBe('2024-01-01T00:00:00.000Z')
  })

  it('does not mutate the original array', () => {
    const a = { ...createEmptySession(), updatedAt: '2024-01-01T00:00:00.000Z' }
    const b = { ...createEmptySession(), updatedAt: '2025-01-01T00:00:00.000Z' }
    const original = [a, b]
    const sorted = sortSessions(original)

    // Original order unchanged
    expect(original[0].updatedAt).toBe('2024-01-01T00:00:00.000Z')
    // Sorted order different
    expect(sorted[0].updatedAt).toBe('2025-01-01T00:00:00.000Z')
  })
})

// ===== normalizeMessageStatus =====

describe('normalizeMessageStatus', () => {
  it('passes through valid statuses', () => {
    expect(normalizeMessageStatus('pending')).toBe('pending')
    expect(normalizeMessageStatus('completed')).toBe('completed')
    expect(normalizeMessageStatus('error')).toBe('error')
  })

  it('returns undefined for unrecognized values', () => {
    expect(normalizeMessageStatus('unknown')).toBeUndefined()
    expect(normalizeMessageStatus('processing')).toBeUndefined()
  })

  it('returns undefined for undefined input', () => {
    expect(normalizeMessageStatus(undefined)).toBeUndefined()
  })
})

// ===== mapRemoteMessage =====

describe('mapRemoteMessage', () => {
  function makeRemoteMessage(overrides: Partial<MessageResponse> = {}): MessageResponse {
    return {
      id: 'msg-1',
      role: 'assistant',
      type: 'diagnosis',
      content: 'Analysis complete',
      attachments: null,
      result: null,
      status: 'completed',
      created_at: '2025-01-01T00:00:00.000Z',
      ...overrides,
    }
  }

  it('maps all recognized message types', () => {
    for (const type of ['intro', 'prompt', 'guidance', 'diagnosis']) {
      const result = mapRemoteMessage(makeRemoteMessage({ type }))
      expect(result.type).toBe(type)
    }
  })

  it('falls back unknown types to prompt', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ type: 'unknown_type' }))
    expect(result.type).toBe('prompt')
  })

  it('maps assistant role correctly', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ role: 'assistant' }))
    expect(result.role).toBe('assistant')
  })

  it('maps non-assistant roles to user', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ role: 'user' }))
    expect(result.role).toBe('user')
  })

  it('extracts attachments from nested items', () => {
    const attachments = { items: [{ id: 'a1', name: 'ecg.png', size: 1024, category: 'image' }] }
    const result = mapRemoteMessage(makeRemoteMessage({ attachments }))
    expect(result.attachments).toHaveLength(1)
    expect(result.attachments![0].name).toBe('ecg.png')
  })

  it('returns undefined attachments when items is not an array', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ attachments: { not_items: true } }))
    expect(result.attachments).toBeUndefined()
  })

  it('returns undefined attachments when null', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ attachments: null }))
    expect(result.attachments).toBeUndefined()
  })

  it('maps result when present', () => {
    const resultData = { prediction: '正常', confidence: 0.95 }
    const result = mapRemoteMessage(makeRemoteMessage({ result: resultData }))
    expect(result.result).toEqual(resultData)
  })

  it('sets result to undefined when null', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ result: null }))
    expect(result.result).toBeUndefined()
  })

  it('normalizes valid status and defaults to completed', () => {
    expect(mapRemoteMessage(makeRemoteMessage({ status: 'pending' })).status).toBe('pending')
    expect(mapRemoteMessage(makeRemoteMessage({ status: 'unknown' })).status).toBe('completed')
  })

  it('defaults to completed when status is missing', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ status: 'unknown_status' }))
    expect(result.status).toBe('completed')
  })

  it('defaults empty content to empty string', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ content: '' }))
    expect(result.content).toBe('')
  })

  it('maps created_at to createdAt', () => {
    const result = mapRemoteMessage(makeRemoteMessage({ created_at: '2025-06-01T12:00:00Z' }))
    expect(result.createdAt).toBe('2025-06-01T12:00:00Z')
  })
})

// ===== mapLocalMessageToRemote =====

describe('mapLocalMessageToRemote', () => {
  function makeLocalMessage(overrides: Partial<ConversationMessage> = {}): ConversationMessage {
    return {
      id: 'local-1',
      role: 'user',
      type: 'prompt',
      content: 'Check this ECG',
      createdAt: new Date().toISOString(),
      status: 'completed',
      ...overrides,
    }
  }

  it('maps id, role, type, content directly', () => {
    const msg = makeLocalMessage()
    const result = mapLocalMessageToRemote(msg)
    expect(result.id).toBe(msg.id)
    expect(result.role).toBe(msg.role)
    expect(result.type).toBe(msg.type)
    expect(result.content).toBe(msg.content)
  })

  it('wraps attachments in { items: [...] }', () => {
    const msg = makeLocalMessage({
      attachments: [{ id: 'a1', name: 'ecg.png', size: 1024, category: 'image' }],
    })
    const result = mapLocalMessageToRemote(msg)
    expect(result.attachments).toEqual({ items: msg.attachments })
  })

  it('sets attachments to null when undefined', () => {
    const result = mapLocalMessageToRemote(makeLocalMessage())
    expect(result.attachments).toBeNull()
  })

  it('maps result with schema version 1 when present', () => {
    const msg = makeLocalMessage({
      result: { prediction: '正常', confidence: 0.95 } as any,
    })
    const result = mapLocalMessageToRemote(msg)
    expect(result.result).toEqual({ prediction: '正常', confidence: 0.95 })
    expect(result.result_schema_version).toBe(1)
  })

  it('sets result to null and schema version to null when absent', () => {
    const result = mapLocalMessageToRemote(makeLocalMessage())
    expect(result.result).toBeNull()
    expect(result.result_schema_version).toBeNull()
  })

  it('defaults status to completed when undefined', () => {
    const result = mapLocalMessageToRemote(makeLocalMessage({ status: undefined }))
    expect(result.status).toBe('completed')
  })

  it('preserves explicit status', () => {
    const result = mapLocalMessageToRemote(makeLocalMessage({ status: 'pending' }))
    expect(result.status).toBe('pending')
  })
})
