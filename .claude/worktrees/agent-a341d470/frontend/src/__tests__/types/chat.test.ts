import { describe, it, expect } from 'vitest'
import type { ConversationMessage } from '@/types/chat'

describe('ConversationMessage', () => {
  it('allows optional status field', () => {
    const msg: ConversationMessage = {
      id: 'test',
      role: 'assistant',
      type: 'diagnosis',
      content: 'test',
      createdAt: '2024-01-01',
      status: 'pending',
    }
    expect(msg.status).toBe('pending')
  })

  it('allows optional errorDetail field', () => {
    const msg: ConversationMessage = {
      id: 'test',
      role: 'assistant',
      type: 'diagnosis',
      content: 'test',
      createdAt: '2024-01-01',
      status: 'error',
      errorDetail: 'Upload failed',
    }
    expect(msg.errorDetail).toBe('Upload failed')
  })
})
