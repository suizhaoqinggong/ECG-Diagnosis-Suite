import { describe, it, expect } from 'vitest'
import {
  workspaceReducer,
  createInitialState,
  createEmptySession,
  calculatePairStatus,
  detectCategory,
  createId,
} from '@/controllers/useWorkspaceController'
import type { WorkspaceState } from '@/controllers/useWorkspaceController'
import type { ConversationMessage } from '@/types/chat'
import type { DiagnosisResultData } from '@/api'

// ===== Test helpers =====

function state(): WorkspaceState {
  return createInitialState()
}

function makeFile(name: string, type = '', size = 1024): File {
  return new File(['x'.repeat(size)], name, { type })
}

function makeImageFile(name = 'ecg.png'): File {
  return makeFile(name, 'image/png')
}

function makeDatFile(name = 'record.dat'): File {
  return makeFile(name, 'application/octet-stream')
}

function makeHeaFile(name = 'record.hea'): File {
  return makeFile(name, 'text/plain')
}

function makeDatAttachment(name = 'record.dat') {
  const file = makeDatFile(name)
  const id = createId()
  return { id, file, summary: { id, name, size: file.size, category: 'dat' as const } }
}

function makeHeaAttachment(name = 'record.hea') {
  const file = makeHeaFile(name)
  const id = createId()
  return { id, file, summary: { id, name, size: file.size, category: 'hea' as const } }
}

function makeImageAttachment(name = 'ecg.png') {
  const file = makeImageFile(name)
  const id = createId()
  return { id, file, summary: { id, name, size: file.size, category: 'image' as const } }
}

const sampleResult: DiagnosisResultData = {
  prediction: 'Normal sinus rhythm',
  confidence: 0.92,
  severity: null,
  icd_code: null,
  description: 'Test',
  recommendations: null,
  timestamp: new Date().toISOString(),
  disclaimer: 'Test only',
  all_probabilities: null,
  top3_predictions: null,
  report: {
    source: 'template',
    summary: 'Test',
    clinical_interpretation: 'Test',
    key_findings: [],
    recommendations: [],
    follow_up: [],
    limitations: [],
  },
}

const sampleMessage: ConversationMessage = {
  id: createId(),
  role: 'user',
  type: 'prompt',
  content: 'Test message',
  createdAt: new Date().toISOString(),
}

// ===== Tests =====

describe('workspaceReducer', () => {
  // --- HYDRATE ---
  it('loads persisted sessions via HYDRATE', () => {
    const session = createEmptySession()
    const s = state()
    const next = workspaceReducer(s, {
      type: 'HYDRATE',
      sessions: [session],
      activeSessionId: session.id,
    })
    expect(next.persisted.sessions).toHaveLength(1)
    expect(next.persisted.activeSessionId).toBe(session.id)
  })

  it('falls back to first session if activeSessionId not found in HYDRATE', () => {
    const sessionA = createEmptySession()
    const sessionB = createEmptySession()
    const s = state()
    const next = workspaceReducer(s, {
      type: 'HYDRATE',
      sessions: [sessionA, sessionB],
      activeSessionId: 'non-existent-id',
    })
    expect(next.persisted.activeSessionId).toBe(sessionA.id)
  })

  // --- SET_DRAFT ---
  it('updates composer draft via SET_DRAFT', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SET_DRAFT', value: 'clinical note' })
    expect(next.composer.draft).toBe('clinical note')
  })

  // --- SUBMIT_STARTED ---
  it('sets submission phase to uploading via SUBMIT_STARTED', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SUBMIT_STARTED', messageId: 'msg-1' })
    expect(next.submission.phase).toBe('uploading')
    expect(next.submission.activeMessageId).toBe('msg-1')
    expect(next.submission.progress).toBeNull()
  })

  // --- SUBMIT_UPLOAD_PROGRESS ---
  it('updates upload progress via SUBMIT_UPLOAD_PROGRESS', () => {
    const s = state()
    const started = workspaceReducer(s, { type: 'SUBMIT_STARTED', messageId: 'msg-1' })
    const next = workspaceReducer(started, { type: 'SUBMIT_UPLOAD_PROGRESS', progress: 50 })
    expect(next.submission.progress).toBe(50)
  })

  // --- SUBMIT_PROCESSING ---
  it('transitions phase to processing via SUBMIT_PROCESSING', () => {
    const s = state()
    const started = workspaceReducer(s, { type: 'SUBMIT_STARTED', messageId: 'msg-1' })
    const next = workspaceReducer(started, { type: 'SUBMIT_PROCESSING' })
    expect(next.submission.phase).toBe('processing')
    expect(next.submission.progress).toBeNull()
  })

  // --- SUBMIT_FAILED ---
  it('sets error and canRetry via SUBMIT_FAILED', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SUBMIT_FAILED', error: 'Network error' })
    expect(next.submission.phase).toBe('failed')
    expect(next.submission.error).toBe('Network error')
    expect(next.submission.canRetry).toBe(true)
    expect(next.submission.activeMessageId).toBeNull()
  })

  // --- SUBMIT_SUCCEEDED ---
  it('resets submission on SUBMIT_SUCCEEDED', () => {
    const s = state()
    const started = workspaceReducer(s, { type: 'SUBMIT_STARTED', messageId: 'msg-1' })
    const next = workspaceReducer(started, { type: 'SUBMIT_SUCCEEDED', result: sampleResult })
    expect(next.submission.phase).toBe('succeeded')
    expect(next.submission.activeMessageId).toBeNull()
    expect(next.submission.error).toBeNull()
  })

  // --- SUBMIT_CANCEL ---
  it('resets submission to idle via SUBMIT_CANCEL', () => {
    const s = state()
    const started = workspaceReducer(s, { type: 'SUBMIT_STARTED', messageId: 'msg-1' })
    const next = workspaceReducer(started, { type: 'SUBMIT_CANCEL' })
    expect(next.submission.phase).toBe('idle')
    expect(next.submission.activeMessageId).toBeNull()
  })

  // --- CREATE_SESSION ---
  it('adds a new session via CREATE_SESSION', () => {
    const s = state()
    const prevCount = s.persisted.sessions.length
    const next = workspaceReducer(s, { type: 'CREATE_SESSION' })
    expect(next.persisted.sessions).toHaveLength(prevCount + 1)
    expect(next.persisted.activeSessionId).not.toBe(s.persisted.activeSessionId)
    expect(next.composer.draft).toBe('')
    expect(next.composer.attachments).toHaveLength(0)
  })

  // --- SWITCH_SESSION ---
  it('switches active session and clears composer via SWITCH_SESSION', () => {
    const s = state()
    const created = workspaceReducer(s, { type: 'CREATE_SESSION' })
    // Switch back to original
    const switched = workspaceReducer(created, { type: 'SWITCH_SESSION', id: s.persisted.activeSessionId })
    expect(switched.persisted.activeSessionId).toBe(s.persisted.activeSessionId)
    expect(switched.composer.draft).toBe('')
    expect(switched.composer.attachments).toHaveLength(0)
    expect(switched.submission.phase).toBe('idle')
  })

  // --- DELETE_SESSION ---
  it('removes session and switches to adjacent via DELETE_SESSION', () => {
    const s = state()
    const created = workspaceReducer(s, { type: 'CREATE_SESSION' })
    const newSessionId = created.persisted.activeSessionId
    expect(created.persisted.sessions).toHaveLength(2)

    // Delete the new session, should switch back to original
    const deleted = workspaceReducer(created, { type: 'DELETE_SESSION', id: newSessionId })
    expect(deleted.persisted.sessions).toHaveLength(1)
    expect(deleted.persisted.activeSessionId).toBe(s.persisted.activeSessionId)
  })

  it('creates a new session when deleting the last one via DELETE_SESSION', () => {
    const s = state()
    const onlySessionId = s.persisted.sessions[0].id
    const deleted = workspaceReducer(s, { type: 'DELETE_SESSION', id: onlySessionId })
    expect(deleted.persisted.sessions).toHaveLength(1)
    expect(deleted.persisted.sessions[0].id).not.toBe(onlySessionId)
  })

  // --- RENAME_SESSION ---
  it('updates session title via RENAME_SESSION', () => {
    const s = state()
    const sessionId = s.persisted.sessions[0].id
    const next = workspaceReducer(s, { type: 'RENAME_SESSION', id: sessionId, title: 'Updated Title' })
    expect(next.persisted.sessions[0].title).toBe('Updated Title')
  })

  // --- CLEAR_ALL_SESSIONS ---
  it('resets all sessions via CLEAR_ALL_SESSIONS', () => {
    const s = state()
    const created = workspaceReducer(s, { type: 'CREATE_SESSION' })
    expect(created.persisted.sessions.length).toBeGreaterThan(1)
    const cleared = workspaceReducer(created, { type: 'CLEAR_ALL_SESSIONS' })
    expect(cleared.persisted.sessions).toHaveLength(1)
  })

  // --- TOGGLE_PERSISTENCE ---
  it('flips persistenceEnabled via TOGGLE_PERSISTENCE', () => {
    const s = state()
    expect(s.persisted.persistenceEnabled).toBe(true)
    const toggled = workspaceReducer(s, { type: 'TOGGLE_PERSISTENCE' })
    expect(toggled.persisted.persistenceEnabled).toBe(false)
    const toggledBack = workspaceReducer(toggled, { type: 'TOGGLE_PERSISTENCE' })
    expect(toggledBack.persisted.persistenceEnabled).toBe(true)
  })

  // --- APPEND_MESSAGE ---
  it('adds message to session via APPEND_MESSAGE', () => {
    const s = state()
    const sessionId = s.persisted.sessions[0].id
    const prevCount = s.persisted.sessions[0].messages.length
    const next = workspaceReducer(s, {
      type: 'APPEND_MESSAGE',
      sessionId,
      message: sampleMessage,
    })
    expect(next.persisted.sessions[0].messages).toHaveLength(prevCount + 1)
    expect(next.persisted.sessions[0].messages[prevCount].content).toBe('Test message')
    expect(next.persisted.sessions[0].updatedAt).toBe(sampleMessage.createdAt)
  })

  it('does not modify other sessions via APPEND_MESSAGE', () => {
    const s = state()
    const created = workspaceReducer(s, { type: 'CREATE_SESSION' })
    const originalSessionId = s.persisted.sessions[0].id
    const newSessionId = created.persisted.activeSessionId
    const origMsgCount = created.persisted.sessions.find(ss => ss.id === originalSessionId)!.messages.length

    const next = workspaceReducer(created, {
      type: 'APPEND_MESSAGE',
      sessionId: newSessionId,
      message: sampleMessage,
    })

    const origSession = next.persisted.sessions.find(ss => ss.id === originalSessionId)!
    expect(origSession.messages).toHaveLength(origMsgCount)
  })

  // --- UPDATE_MESSAGE ---
  it('updates existing message via UPDATE_MESSAGE', () => {
    const s = state()
    const sessionId = s.persisted.sessions[0].id
    const appended = workspaceReducer(s, {
      type: 'APPEND_MESSAGE',
      sessionId,
      message: sampleMessage,
    })
    const next = workspaceReducer(appended, {
      type: 'UPDATE_MESSAGE',
      sessionId,
      messageId: sampleMessage.id,
      updates: { content: 'Updated content', status: 'completed' },
    })
    const updated = next.persisted.sessions[0].messages.find(m => m.id === sampleMessage.id)!
    expect(updated.content).toBe('Updated content')
    expect(updated.status).toBe('completed')
  })

  // --- SET_DRAG_ACTIVE ---
  it('sets drag state via SET_DRAG_ACTIVE', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SET_DRAG_ACTIVE', active: true })
    expect(next.ui.isDragging).toBe(true)
  })

  // --- SET_SIDEBAR_OPEN ---
  it('sets sidebar state via SET_SIDEBAR_OPEN', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SET_SIDEBAR_OPEN', open: true })
    expect(next.ui.isSidebarOpen).toBe(true)
  })

  // --- SET_RENAMING ---
  it('sets renaming session via SET_RENAMING', () => {
    const s = state()
    const sessionId = s.persisted.sessions[0].id
    const next = workspaceReducer(s, { type: 'SET_RENAMING', sessionId })
    expect(next.ui.renamingSessionId).toBe(sessionId)
  })

  // --- SET_PRINTABLE_MESSAGE ---
  it('sets printable message via SET_PRINTABLE_MESSAGE', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'SET_PRINTABLE_MESSAGE', messageId: 'msg-1' })
    expect(next.ui.printableMessageId).toBe('msg-1')
  })

  // --- CLEAR_COMPOSER ---
  it('clears composer via CLEAR_COMPOSER', () => {
    const s = state()
    const withDraft = workspaceReducer(s, { type: 'SET_DRAFT', value: 'some text' })
    const cleared = workspaceReducer(withDraft, { type: 'CLEAR_COMPOSER' })
    expect(cleared.composer.draft).toBe('')
    expect(cleared.composer.attachments).toHaveLength(0)
    expect(cleared.composer.pairStatus).toBe('empty')
    expect(cleared.composer.validationErrors).toHaveLength(0)
  })

  // --- ADD_FILES with pair validation ---
  it('adds image file via ADD_FILES', () => {
    const s = state()
    const file = makeImageFile()
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [file] })
    expect(next.composer.attachments).toHaveLength(1)
    expect(next.composer.attachments[0].summary.category).toBe('image')
    expect(next.composer.pairStatus).toBe('image')
  })

  it('adds matched dat+hea pair via ADD_FILES', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [makeDatFile(), makeHeaFile()] })
    expect(next.composer.attachments).toHaveLength(2)
    expect(next.composer.pairStatus).toBe('matched')
  })

  it('detects mismatched dat+hea pair via ADD_FILES', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [makeDatFile('record1.dat'), makeHeaFile('record2.hea')] })
    expect(next.composer.pairStatus).toBe('mismatch')
    expect(next.composer.validationErrors.length).toBeGreaterThan(0)
  })

  it('detects partial pair (dat only) via ADD_FILES', () => {
    const s = state()
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [makeDatFile()] })
    expect(next.composer.pairStatus).toBe('partial')
  })

  it('rejects oversized files via ADD_FILES', () => {
    const s = state()
    const bigFile = makeFile('big.png', 'image/png', 11 * 1024 * 1024)
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [bigFile] })
    expect(next.composer.attachments).toHaveLength(0)
    expect(next.composer.validationErrors.length).toBeGreaterThan(0)
  })

  it('rejects unsupported file types via ADD_FILES', () => {
    const s = state()
    const badFile = makeFile('data.csv', 'text/csv')
    const next = workspaceReducer(s, { type: 'ADD_FILES', files: [badFile] })
    expect(next.composer.attachments).toHaveLength(0)
    expect(next.composer.validationErrors.length).toBeGreaterThan(0)
  })

  it('image replaces existing dat+hea attachments via ADD_FILES', () => {
    const s = state()
    const withPair = workspaceReducer(s, { type: 'ADD_FILES', files: [makeDatFile(), makeHeaFile()] })
    expect(withPair.composer.attachments).toHaveLength(2)

    const withImage = workspaceReducer(withPair, { type: 'ADD_FILES', files: [makeImageFile()] })
    expect(withImage.composer.attachments).toHaveLength(1)
    expect(withImage.composer.attachments[0].summary.category).toBe('image')
  })

  // --- REMOVE_FILE ---
  it('removes file via REMOVE_FILE', () => {
    const s = state()
    const withFile = workspaceReducer(s, { type: 'ADD_FILES', files: [makeImageFile()] })
    const fileId = withFile.composer.attachments[0].id
    const removed = workspaceReducer(withFile, { type: 'REMOVE_FILE', id: fileId })
    expect(removed.composer.attachments).toHaveLength(0)
    expect(removed.composer.pairStatus).toBe('empty')
  })
})

// ===== Helper function tests =====

describe('detectCategory', () => {
  it('detects image files by MIME type', () => {
    expect(detectCategory(makeFile('photo.png', 'image/png'))).toBe('image')
    expect(detectCategory(makeFile('photo.jpg', 'image/jpeg'))).toBe('image')
  })

  it('detects image files by extension', () => {
    expect(detectCategory(makeFile('photo.png', ''))).toBe('image')
    expect(detectCategory(makeFile('photo.jpg', ''))).toBe('image')
    expect(detectCategory(makeFile('photo.jpeg', ''))).toBe('image')
  })

  it('detects dat files', () => {
    expect(detectCategory(makeFile('record.dat', 'application/octet-stream'))).toBe('dat')
  })

  it('detects hea files', () => {
    expect(detectCategory(makeFile('record.hea', 'text/plain'))).toBe('hea')
  })

  it('returns null for unsupported types', () => {
    expect(detectCategory(makeFile('data.csv', 'text/csv'))).toBeNull()
    expect(detectCategory(makeFile('doc.pdf', 'application/pdf'))).toBeNull()
  })
})

describe('calculatePairStatus', () => {
  it('returns empty for no attachments', () => {
    expect(calculatePairStatus([])).toBe('empty')
  })

  it('returns image for image attachments', () => {
    expect(calculatePairStatus([makeImageAttachment()])).toBe('image')
  })

  it('returns partial for dat-only', () => {
    expect(calculatePairStatus([makeDatAttachment()])).toBe('partial')
  })

  it('returns partial for hea-only', () => {
    expect(calculatePairStatus([makeHeaAttachment()])).toBe('partial')
  })

  it('returns matched for matching pair', () => {
    expect(calculatePairStatus([makeDatAttachment('record.dat'), makeHeaAttachment('record.hea')])).toBe('matched')
  })

  it('returns mismatch for non-matching pair', () => {
    expect(calculatePairStatus([makeDatAttachment('a.dat'), makeHeaAttachment('b.hea')])).toBe('mismatch')
  })
})

describe('createEmptySession', () => {
  it('creates a valid session with intro message', () => {
    const session = createEmptySession()
    expect(session.id).toBeTruthy()
    expect(session.title).toBe('New analysis')
    expect(session.messages).toHaveLength(1)
    expect(session.messages[0].type).toBe('intro')
  })
})

describe('createInitialState', () => {
  it('creates a valid initial state', () => {
    const s = createInitialState()
    expect(s.persisted.sessions).toHaveLength(1)
    expect(s.persisted.persistenceEnabled).toBe(true)
    expect(s.persisted.storageVersion).toBe(1)
    expect(s.composer.draft).toBe('')
    expect(s.submission.phase).toBe('idle')
    expect(s.ui.isDragging).toBe(false)
  })
})
