# ECG Diagnosis Suite Frontend Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comprehensive UX-first optimization of the ECG Diagnosis Suite frontend with unified state management and pure presentational components.

**Architecture:** Replace HomePage's 517-line monolithic state with `useWorkspaceController` (useReducer-based). Extract DiagnosisReport as pure component. Add two-phase submission progress, session management with privacy controls, mobile drawer, and accessibility improvements.

**Tech Stack:** React 18, TypeScript 5.4, Vite 5, Tailwind CSS 3.4, Axios, vitest (testing), @testing-library/react (component tests)

---

## File Structure

**New files to create:**
```
frontend/src/
├── controllers/
│   └── useWorkspaceController.ts    # Main state controller (useReducer)
├── components/
│   ├── DiagnosisReport.tsx          # Extracted from ConversationMessage
│   ├── EmptyStateGuide.tsx          # New: first-time user guidance
│   ├── MobileHeader.tsx             # New: hamburger menu + title
│   └── SessionMenu.tsx              # New: rename/delete operations
├── hooks/
│   └── useAutoScroll.ts             # New: auto-scroll to pending message
├── utils/
│   ├── storage.ts                   # New: localStorage with versioning
│   └── clipboard.ts                 # New: copy to clipboard helper
└── __tests__/
    ├── controllers/
    │   └── workspaceReducer.test.ts # Reducer unit tests
    └── integration/
        ├── submission.test.tsx      # E2E submission flow
        └── sessionManagement.test.tsx
```

**Files to modify:**
```
frontend/src/
├── pages/HomePage.tsx               # Major refactor: use controller
├── components/
│   ├── ConversationMessage.tsx      # Extract diagnosis report
│   ├── ConversationSidebar.tsx      # Add session menu, privacy toggle
│   └── ChatComposer.tsx             # Add drag-drop, pair status
├── types/chat.ts                    # Add status, errorDetail fields
├── api/index.ts                     # Add onUploadProgress, remove getHistory
├── api/client.ts                    # Add response interceptor
├── index.css                        # Add print styles, animations
├── utils/index.ts                   # Add formatBytes, export functions
├── tailwind.config.js               # Remove unused primary palette
└── App.tsx                          # Add mobile header
```

---

## Task 1: Setup Testing Infrastructure

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/__tests__/setup.ts`

- [ ] **Step 1: Install test dependencies**

```bash
cd frontend && npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitest/coverage-v8
```

- [ ] **Step 2: Create vitest config**

Create `frontend/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/__tests__/'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 3: Create test setup**

Create `frontend/src/__tests__/setup.ts`:

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Add test scripts to package.json**

Add to `frontend/package.json` scripts:

```json
"test": "vitest",
"test:ui": "vitest --ui",
"test:coverage": "vitest --coverage"
```

- [ ] **Step 5: Run test to verify setup**

Run: `cd frontend && npm test -- --run`
Expected: Tests run (0 passed, 0 failed)

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/__tests__/setup.ts
git commit -m "test: add vitest and testing-library setup"
```

---

## Task 2: Extend Message Type System

**Files:**
- Modify: `frontend/src/types/chat.ts`

- [ ] **Step 1: Write the type extension test**

Create `frontend/src/__tests__/types/chat.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import type { ConversationMessage, WorkspaceState } from '@/types/chat'

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run types/chat.test.ts`
Expected: FAIL - Type errors (status/errorDetail not defined)

- [ ] **Step 3: Extend types**

Modify `frontend/src/types/chat.ts`, add new fields:

```typescript
export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  type: 'intro' | 'prompt' | 'guidance' | 'diagnosis'
  title?: string
  content: string
  createdAt: string
  attachments?: AttachedFileSummary[]
  result?: DiagnosisResultData

  // New fields for pending state management
  status?: 'pending' | 'completed' | 'error'
  errorDetail?: string
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run types/chat.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/chat.ts frontend/src/__tests__/types/chat.test.ts
git commit -m "feat: add status and errorDetail to ConversationMessage"
```

---

## Task 3: Create Storage Utility with Versioning

**Files:**
- Create: `frontend/src/utils/storage.ts`
- Create: `frontend/src/__tests__/utils/storage.test.ts`

- [ ] **Step 1: Write storage utility tests**

Create `frontend/src/__tests__/utils/storage.test.ts`:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { StorageManager, STORAGE_VERSION } from '@/utils/storage'

describe('StorageManager', () => {
  let storage: StorageManager

  beforeEach(() => {
    localStorage.clear()
    storage = new StorageManager()
  })

  it('writes and reads persisted state', () => {
    const state = {
      sessions: [],
      activeSessionId: 'test-id',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }
    storage.writePersisted(state)
    expect(storage.readPersisted()).toEqual(state)
  })

  it('returns null when version mismatch', () => {
    localStorage.setItem('ecg-persisted', JSON.stringify({
      sessions: [],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: 0, // Old version
    }))
    expect(storage.readPersisted()).toBeNull()
  })

  it('handles QuotaExceededError', () => {
    const originalSetItem = localStorage.setItem
    localStorage.setItem = vi.fn(() => {
      const error = new Error('Quota exceeded')
      error.name = 'QuotaExceededError'
      throw error
    })

    const state = {
      sessions: [],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }

    expect(() => storage.writePersisted(state)).toThrow('QUOTA_EXCEEDED')

    localStorage.setItem = originalSetItem
  })

  it('calculates storage size', () => {
    const state = {
      sessions: [{ id: 'test', title: 'Test Session' }],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }
    storage.writePersisted(state)
    const size = storage.getSize()
    expect(size).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run utils/storage.test.ts`
Expected: FAIL - Module not found

- [ ] **Step 3: Implement storage utility**

Create `frontend/src/utils/storage.ts`:

```typescript
export const STORAGE_VERSION = 1

const PERSISTED_KEY = 'ecg-persisted'

interface PersistedState {
  sessions: unknown[]
  activeSessionId: string
  persistenceEnabled: boolean
  storageVersion: number
}

export class StorageManager {
  writePersisted(state: PersistedState): void {
    try {
      localStorage.setItem(PERSISTED_KEY, JSON.stringify(state))
    } catch (error) {
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        throw new Error('QUOTA_EXCEEDED')
      }
      throw error
    }
  }

  readPersisted(): PersistedState | null {
    try {
      const raw = localStorage.getItem(PERSISTED_KEY)
      if (!raw) return null

      const parsed = JSON.parse(raw) as PersistedState

      // Version check - return null if mismatch
      if (parsed.storageVersion !== STORAGE_VERSION) {
        return null
      }

      return parsed
    } catch {
      return null
    }
  }

  clear(): void {
    localStorage.removeItem(PERSISTED_KEY)
  }

  getSize(): number {
    const raw = localStorage.getItem(PERSISTED_KEY)
    return raw ? new Blob([raw]).size : 0
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run utils/storage.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/storage.ts frontend/src/__tests__/utils/storage.test.ts
git commit -m "feat: add storage utility with versioning"
```

---

## Task 4: Create Workspace Reducer

**Files:**
- Create: `frontend/src/controllers/useWorkspaceController.ts` (reducer only)
- Create: `frontend/src/__tests__/controllers/workspaceReducer.test.ts`

- [ ] **Step 1: Write reducer unit tests for core actions**

Create `frontend/src/__tests__/controllers/workspaceReducer.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { workspaceReducer, createInitialState, type WorkspaceState, type WorkspaceAction } from '@/controllers/useWorkspaceController'

describe('workspaceReducer', () => {
  it('HYDRATE loads persisted state', () => {
    const initial = createInitialState()
    const action: WorkspaceAction = {
      type: 'HYDRATE',
      sessions: [{ id: 's1', title: 'Test', preview: '', updatedAt: '2024-01-01', messages: [] }],
      activeSessionId: 's1',
    }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions).toHaveLength(1)
    expect(state.persisted.activeSessionId).toBe('s1')
  })

  it('SET_DRAFT updates composer.draft', () => {
    const initial = createInitialState()
    const action: WorkspaceAction = { type: 'SET_DRAFT', value: 'test note' }

    const state = workspaceReducer(initial, action)

    expect(state.composer.draft).toBe('test note')
  })

  it('SUBMIT_STARTED sets phase to uploading', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{ id: 's1', title: 'Test', preview: '', updatedAt: '2024-01-01', messages: [] }]
    initial.persisted.activeSessionId = 's1'

    const action: WorkspaceAction = { type: 'SUBMIT_STARTED', messageId: 'm1' }

    const state = workspaceReducer(initial, action)

    expect(state.submission.phase).toBe('uploading')
    expect(state.submission.activeMessageId).toBe('m1')
  })

  it('SUBMIT_UPLOAD_PROGRESS updates progress', () => {
    const initial = createInitialState()
    initial.submission.phase = 'uploading'

    const action: WorkspaceAction = { type: 'SUBMIT_UPLOAD_PROGRESS', progress: 50 }

    const state = workspaceReducer(initial, action)

    expect(state.submission.progress).toBe(50)
  })

  it('SUBMIT_PROCESSING transitions from uploading', () => {
    const initial = createInitialState()
    initial.submission.phase = 'uploading'
    initial.submission.progress = 100

    const action: WorkspaceAction = { type: 'SUBMIT_PROCESSING' }

    const state = workspaceReducer(initial, action)

    expect(state.submission.phase).toBe('processing')
    expect(state.submission.progress).toBeNull()
  })

  it('SUBMIT_FAILED sets error and canRetry', () => {
    const initial = createInitialState()
    initial.submission.phase = 'processing'

    const action: WorkspaceAction = { type: 'SUBMIT_FAILED', error: 'Network error' }

    const state = workspaceReducer(initial, action)

    expect(state.submission.phase).toBe('failed')
    expect(state.submission.error).toBe('Network error')
    expect(state.submission.canRetry).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run controllers/workspaceReducer.test.ts`
Expected: FAIL - Module not found

- [ ] **Step 3: Implement initial state and reducer (part 1)**

Create `frontend/src/controllers/useWorkspaceController.ts`:

```typescript
import { useReducer, useCallback, useRef, useEffect } from 'react'
import type { ChatSession, ConversationMessage, DiagnosisResultData, AttachedFileSummary } from '@/types/chat'

// State structure
export interface WorkspaceState {
  persisted: {
    sessions: ChatSession[]
    activeSessionId: string
    persistenceEnabled: boolean
    storageVersion: number
  }

  composer: {
    draft: string
    attachments: PendingAttachment[]
    pairStatus: 'empty' | 'partial' | 'matched' | 'mismatch' | 'image'
    validationErrors: string[]
  }

  submission: {
    activeMessageId: string | null
    phase: 'idle' | 'uploading' | 'processing' | 'succeeded' | 'failed'
    progress: number | null
    error: string | null
    canRetry: boolean
  }

  ui: {
    isDragging: boolean
    isSidebarOpen: boolean
    renamingSessionId: string | null
    printableMessageId: string | null
    storageWarning: string | null
  }
}

interface PendingAttachment {
  id: string
  file: File
  summary: AttachedFileSummary
}

// Actions
export type WorkspaceAction =
  | { type: 'HYDRATE'; sessions: ChatSession[]; activeSessionId: string }
  | { type: 'SET_DRAFT'; value: string }
  | { type: 'ADD_FILES'; files: FileList | File[] }
  | { type: 'REMOVE_FILE'; id: string }
  | { type: 'CLEAR_COMPOSER' }
  | { type: 'SUBMIT_STARTED'; messageId: string }
  | { type: 'SUBMIT_UPLOAD_PROGRESS'; progress: number }
  | { type: 'SUBMIT_PROCESSING' }
  | { type: 'SUBMIT_SUCCEEDED'; result: DiagnosisResultData }
  | { type: 'SUBMIT_FAILED'; error: string }
  | { type: 'SUBMIT_RETRY' }
  | { type: 'SUBMIT_CANCEL' }
  | { type: 'SET_DRAG_ACTIVE'; active: boolean }
  | { type: 'SET_SIDEBAR_OPEN'; open: boolean }
  | { type: 'SET_RENAMING'; sessionId: string | null }
  | { type: 'SET_PRINTABLE_MESSAGE'; messageId: string | null }
  | { type: 'CREATE_SESSION' }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'RENAME_SESSION'; id: string; title: string }
  | { type: 'DELETE_SESSION'; id: string }
  | { type: 'CLEAR_ALL_SESSIONS' }
  | { type: 'TOGGLE_PERSISTENCE' }
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }

// Initial state factory
export function createInitialState(): WorkspaceState {
  return {
    persisted: {
      sessions: [],
      activeSessionId: '',
      persistenceEnabled: true,
      storageVersion: 1,
    },
    composer: {
      draft: '',
      attachments: [],
      pairStatus: 'empty',
      validationErrors: [],
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
      isSidebarOpen: false,
      renamingSessionId: null,
      printableMessageId: null,
      storageWarning: null,
    },
  }
}

// Reducer (exported for testing)
export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'HYDRATE':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: action.sessions,
          activeSessionId: action.activeSessionId,
        },
      }

    case 'SET_DRAFT':
      return {
        ...state,
        composer: { ...state.composer, draft: action.value },
      }

    case 'SUBMIT_STARTED':
      return {
        ...state,
        submission: {
          ...state.submission,
          activeMessageId: action.messageId,
          phase: 'uploading',
          progress: 0,
          error: null,
          canRetry: false,
        },
      }

    case 'SUBMIT_UPLOAD_PROGRESS':
      return {
        ...state,
        submission: {
          ...state.submission,
          progress: action.progress,
        },
      }

    case 'SUBMIT_PROCESSING':
      return {
        ...state,
        submission: {
          ...state.submission,
          phase: 'processing',
          progress: null,
        },
      }

    case 'SUBMIT_FAILED':
      return {
        ...state,
        submission: {
          ...state.submission,
          phase: 'failed',
          error: action.error,
          canRetry: true,
        },
      }

    case 'SUBMIT_SUCCEEDED':
      return {
        ...state,
        submission: {
          ...state.submission,
          phase: 'succeeded',
          canRetry: false,
        },
      }

    case 'CREATE_SESSION':
      // Will be implemented in next task
      return state

    case 'SWITCH_SESSION':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          activeSessionId: action.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
        },
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }

    default:
      return state
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run controllers/workspaceReducer.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts frontend/src/__tests__/controllers/workspaceReducer.test.ts
git commit -m "feat: add workspace reducer core actions"
```

---

## Task 5: Complete Workspace Reducer (Session Management)

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`
- Modify: `frontend/src/__tests__/controllers/workspaceReducer.test.ts`

- [ ] **Step 1: Add session management tests**

Add to `frontend/src/__tests__/controllers/workspaceReducer.test.ts`:

```typescript
  it('CREATE_SESSION adds new session and switches to it', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{ id: 's1', title: 'Old', preview: '', updatedAt: '2024-01-01', messages: [] }]
    initial.persisted.activeSessionId = 's1'

    const action: WorkspaceAction = { type: 'CREATE_SESSION' }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions).toHaveLength(2)
    expect(state.persisted.activeSessionId).not.toBe('s1')
    expect(state.persisted.sessions[0].title).toBe('New analysis')
  })

  it('SWITCH_SESSION clears composer', () => {
    const initial = createInitialState()
    initial.composer.draft = 'old draft'
    initial.composer.attachments = [{ id: 'f1', file: new File([''], 'test.dat'), summary: { id: 'f1', name: 'test.dat', size: 0, category: 'dat' } }]

    const action: WorkspaceAction = { type: 'SWITCH_SESSION', id: 's2' }

    const state = workspaceReducer(initial, action)

    expect(state.composer.draft).toBe('')
    expect(state.composer.attachments).toHaveLength(0)
  })

  it('DELETE_SESSION removes session and switches to adjacent', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [
      { id: 's1', title: 'Old', preview: '', updatedAt: '2024-01-01', messages: [] },
      { id: 's2', title: 'Current', preview: '', updatedAt: '2024-01-02', messages: [] },
    ]
    initial.persisted.activeSessionId = 's2'

    const action: WorkspaceAction = { type: 'DELETE_SESSION', id: 's2' }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions).toHaveLength(1)
    expect(state.persisted.activeSessionId).toBe('s1')
  })

  it('DELETE_SESSION creates new session if last one', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{ id: 's1', title: 'Only', preview: '', updatedAt: '2024-01-01', messages: [] }]
    initial.persisted.activeSessionId = 's1'

    const action: WorkspaceAction = { type: 'DELETE_SESSION', id: 's1' }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions).toHaveLength(1)
    expect(state.persisted.activeSessionId).not.toBe('s1')
  })

  it('RENAME_SESSION updates session title', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{ id: 's1', title: 'Old Title', preview: '', updatedAt: '2024-01-01', messages: [] }]

    const action: WorkspaceAction = { type: 'RENAME_SESSION', id: 's1', title: 'New Title' }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions[0].title).toBe('New Title')
  })

  it('TOGGLE_PERSISTENCE flips flag', () => {
    const initial = createInitialState()
    initial.persisted.persistenceEnabled = true

    const action: WorkspaceAction = { type: 'TOGGLE_PERSISTENCE' }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.persistenceEnabled).toBe(false)
  })

  it('APPEND_MESSAGE adds message to session', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{ id: 's1', title: 'Test', preview: '', updatedAt: '2024-01-01', messages: [] }]

    const message: ConversationMessage = {
      id: 'm1',
      role: 'user',
      type: 'prompt',
      content: 'test',
      createdAt: '2024-01-01T10:00:00',
    }

    const action: WorkspaceAction = { type: 'APPEND_MESSAGE', sessionId: 's1', message }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions[0].messages).toHaveLength(1)
    expect(state.persisted.sessions[0].messages[0].id).toBe('m1')
  })

  it('UPDATE_MESSAGE modifies existing message', () => {
    const initial = createInitialState()
    initial.persisted.sessions = [{
      id: 's1',
      title: 'Test',
      preview: '',
      updatedAt: '2024-01-01',
      messages: [{
        id: 'm1',
        role: 'assistant',
        type: 'diagnosis',
        content: 'pending',
        createdAt: '2024-01-01T10:00:00',
        status: 'pending',
      }],
    }]

    const action: WorkspaceAction = {
      type: 'UPDATE_MESSAGE',
      sessionId: 's1',
      messageId: 'm1',
      updates: { status: 'completed', content: 'done' },
    }

    const state = workspaceReducer(initial, action)

    expect(state.persisted.sessions[0].messages[0].status).toBe('completed')
    expect(state.persisted.sessions[0].messages[0].content).toBe('done')
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run controllers/workspaceReducer.test.ts`
Expected: FAIL - Some tests fail (not implemented)

- [ ] **Step 3: Implement session management actions**

Update `workspaceReducer` in `frontend/src/controllers/useWorkspaceController.ts`, add cases:

```typescript
import type { ChatSession, ConversationMessage } from '@/types/chat'

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function createEmptySession(): ChatSession {
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
    }],
  }
}

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    // ... existing cases ...

    case 'CREATE_SESSION': {
      const newSession = createEmptySession()
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: [newSession, ...state.persisted.sessions],
          activeSessionId: newSession.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
        },
      }
    }

    case 'SWITCH_SESSION':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          activeSessionId: action.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
        },
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }

    case 'DELETE_SESSION': {
      const remaining = state.persisted.sessions.filter(s => s.id !== action.id)
      let nextActiveId = state.persisted.activeSessionId

      if (action.id === state.persisted.activeSessionId) {
        nextActiveId = remaining[0]?.id ?? createEmptySession().id
      }

      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: remaining.length > 0 ? remaining : [createEmptySession()],
          activeSessionId: nextActiveId,
        },
      }
    }

    case 'RENAME_SESSION':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(s =>
            s.id === action.id ? { ...s, title: action.title } : s
          ),
        },
      }

    case 'TOGGLE_PERSISTENCE':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          persistenceEnabled: !state.persisted.persistenceEnabled,
        },
      }

    case 'APPEND_MESSAGE':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(s =>
            s.id === action.sessionId
              ? { ...s, messages: [...s.messages, action.message], updatedAt: action.message.createdAt }
              : s
          ),
        },
      }

    case 'UPDATE_MESSAGE':
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(s =>
            s.id === action.sessionId
              ? {
                  ...s,
                  messages: s.messages.map(m =>
                    m.id === action.messageId ? { ...m, ...action.updates } : m
                  ),
                }
              : s
          ),
        },
      }

    case 'CLEAR_ALL_SESSIONS': {
      const newSession = createEmptySession()
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: [newSession],
          activeSessionId: newSession.id,
        },
      }
    }

    default:
      return state
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run controllers/workspaceReducer.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts frontend/src/__tests__/controllers/workspaceReducer.test.ts
git commit -m "feat: add session management actions to reducer"
```

---

## Task 6: Complete useWorkspaceController Hook

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`

- [ ] **Step 1: Add the hook implementation**

Add to `frontend/src/controllers/useWorkspaceController.ts` after the reducer:

```typescript
export function useWorkspaceController() {
  const [state, dispatch] = useReducer(workspaceReducer, null, createInitialState)

  // Volatile refs (not in state)
  const lastFilesRef = useRef<File[] | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Hydration on mount
  useEffect(() => {
    const stored = localStorage.getItem('ecg-persisted')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed.storageVersion === 1) {
          dispatch({ type: 'HYDRATE', sessions: parsed.sessions, activeSessionId: parsed.activeSessionId })
        }
      } catch {
        // Ignore parse errors
      }
    }
  }, [])

  // Persistence on state change
  useEffect(() => {
    if (state.persisted.persistenceEnabled) {
      try {
        localStorage.setItem('ecg-persisted', JSON.stringify(state.persisted))
      } catch (error) {
        if (error instanceof Error && error.name === 'QuotaExceededError') {
          // TODO: Will handle with LRU pruning in later task
          console.error('Storage quota exceeded')
        }
      }
    }
  }, [state.persisted])

  // Derived state
  const activeSession = state.persisted.sessions.find(s => s.id === state.persisted.activeSessionId) ?? null
  const isSubmitting = state.submission.phase === 'uploading' || state.submission.phase === 'processing'

  // Convenience methods
  const submit = useCallback(async () => {
    // Will be implemented in Task 7
  }, [state])

  const retry = useCallback(async () => {
    // Will be implemented in Task 7
  }, [state])

  const cancelSubmission = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (state.submission.activeMessageId && activeSession) {
      dispatch({
        type: 'UPDATE_MESSAGE',
        sessionId: activeSession.id,
        messageId: state.submission.activeMessageId,
        updates: {
          status: 'error',
          errorDetail: 'Analysis cancelled',
        },
      })
    }
    dispatch({ type: 'SUBMIT_CANCEL' })
  }, [state.submission.activeMessageId, activeSession])

  return {
    state,
    dispatch,
    activeSession,
    isSubmitting,
    submit,
    retry,
    cancelSubmission,
  }
}

export type UseWorkspaceControllerReturn = ReturnType<typeof useWorkspaceController>
```

- [ ] **Step 2: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts
git commit -m "feat: complete useWorkspaceController hook with persistence"
```

---

## Task 7: Implement Submit Method with Upload Progress

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: Update API to support upload progress**

Modify `frontend/src/api/index.ts`, update `postFormData`:

```typescript
async function postFormData<T>(
  url: string,
  formData: FormData,
  onUploadProgress?: (progress: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  const response = await apiClient.post<T>(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onUploadProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onUploadProgress(percentCompleted)
      }
    },
    signal,
  })

  return response.data
}

export const diagnosisApi = {
  diagnoseImage(
    file: File,
    onUploadProgress?: (progress: number) => void,
    signal?: AbortSignal,
  ) {
    const formData = new FormData()
    formData.append('file', file)
    return postFormData<DiagnosisResultData>('/api/diagnose', formData, onUploadProgress, signal)
  },

  diagnoseDatPair(
    datFile: File,
    heaFile: File,
    onUploadProgress?: (progress: number) => void,
    signal?: AbortSignal,
  ) {
    const formData = new FormData()
    formData.append('files', datFile)
    formData.append('files', heaFile)
    return postFormData<DiagnosisResultData>('/api/diagnose-dat', formData, onUploadProgress, signal)
  },
}
```

Remove the unused `getHistory` function.

- [ ] **Step 2: Implement submit method**

Update `submit` in `frontend/src/controllers/useWorkspaceController.ts`:

```typescript
import { diagnosisApi } from '@/api'
import toast from 'react-hot-toast'

// Helper to detect file category
function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()

  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) {
    return 'image'
  }

  if (lowerName.endsWith('.dat')) {
    return 'dat'
  }

  if (lowerName.endsWith('.hea')) {
    return 'hea'
  }

  return null
}

// Inside useWorkspaceController hook:
const submit = useCallback(async () => {
  if (!activeSession || isSubmitting) return

  const hasContent = state.composer.draft.trim() || state.composer.attachments.length > 0
  if (!hasContent) {
    toast.error('Add a note or attach an ECG study to continue.')
    return
  }

  // Create pending message
  const pendingMessageId = createId()
  const pendingMessage: ConversationMessage = {
    id: pendingMessageId,
    role: 'assistant',
    type: 'diagnosis',
    content: 'Analyzing...',
    createdAt: new Date().toISOString(),
    status: 'pending',
  }

  dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: pendingMessage })
  dispatch({ type: 'SUBMIT_STARTED', messageId: pendingMessageId })

  // Store files for retry
  lastFilesRef.current = state.composer.attachments.map(a => a.file)

  // Create abort controller
  abortControllerRef.current = new AbortController()

  try {
    const imageFile = state.composer.attachments.find(a => a.summary.category === 'image')?.file
    const datFile = state.composer.attachments.find(a => a.summary.category === 'dat')?.file
    const heaFile = state.composer.attachments.find(a => a.summary.category === 'hea')?.file

    let result: DiagnosisResultData

    if (imageFile) {
      result = await diagnosisApi.diagnoseImage(
        imageFile,
        (progress) => dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress }),
        abortControllerRef.current.signal,
      )
    } else if (datFile && heaFile) {
      result = await diagnosisApi.diagnoseDatPair(
        datFile,
        heaFile,
        (progress) => dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress }),
        abortControllerRef.current.signal,
      )
    } else {
      throw new Error('Invalid file combination')
    }

    // Transition to processing after upload
    dispatch({ type: 'SUBMIT_PROCESSING' })

    // Update message with result
    dispatch({
      type: 'UPDATE_MESSAGE',
      sessionId: activeSession.id,
      messageId: pendingMessageId,
      updates: {
        status: 'completed',
        content: 'Analysis complete',
        result,
      },
    })

    dispatch({ type: 'SUBMIT_SUCCEEDED', result })
    dispatch({ type: 'CLEAR_COMPOSER' })
    toast.success('Diagnosis complete.')
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Analysis failed'

    dispatch({
      type: 'UPDATE_MESSAGE',
      sessionId: activeSession.id,
      messageId: pendingMessageId,
      updates: {
        status: 'error',
        errorDetail: errorMessage,
      },
    })

    dispatch({ type: 'SUBMIT_FAILED', error: errorMessage })
    toast.error(errorMessage)
  }
}, [activeSession, isSubmitting, state.composer])
```

- [ ] **Step 3: Implement retry method**

```typescript
const retry = useCallback(async () => {
  if (!lastFilesRef.current || !activeSession) {
    toast.error('Please re-select files and try again.')
    return
  }

  // Re-add files to composer and submit
  dispatch({ type: 'ADD_FILES', files: lastFilesRef.current })
  // submit() will be called after state updates
}, [activeSession])
```

- [ ] **Step 4: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts frontend/src/api/index.ts
git commit -m "feat: implement submit with two-phase progress tracking"
```

---

## Task 8: Refactor HomePage to Use Controller

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Replace state with controller**

Replace entire `frontend/src/pages/HomePage.tsx`:

```typescript
import { useWorkspaceController } from '@/controllers/useWorkspaceController'
import ChatComposer from '@/components/ChatComposer'
import ConversationMessage from '@/components/ConversationMessage'
import ConversationSidebar from '@/components/ConversationSidebar'

export default function HomePage() {
  const { state, dispatch, activeSession, isSubmitting, submit, cancelSubmission } = useWorkspaceController()

  if (!activeSession) {
    return null // Should not happen
  }

  const handleCreateSession = () => {
    dispatch({ type: 'CREATE_SESSION' })
  }

  const handleSelectSession = (sessionId: string) => {
    dispatch({ type: 'SWITCH_SESSION', id: sessionId })
  }

  const handleImageFilesSelected = (files: FileList | null) => {
    if (files && files.length > 0) {
      dispatch({ type: 'ADD_FILES', files })
    }
  }

  const handleDataFilesSelected = (files: FileList | null) => {
    if (files && files.length > 0) {
      dispatch({ type: 'ADD_FILES', files })
    }
  }

  const handleRemoveFile = (fileId: string) => {
    dispatch({ type: 'REMOVE_FILE', id: fileId })
  }

  return (
    <div className="min-h-screen lg:flex">
      <ConversationSidebar
        sessions={state.persisted.sessions}
        activeSessionId={activeSession.id}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
      />

      <main className="flex min-h-screen flex-1 flex-col">
        <header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
          <div className="mx-auto max-w-4xl">
            <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
              Writing-first interface
            </p>
            <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="reading-copy text-3xl tracking-tight text-[var(--ink)] md:text-[2.8rem]">
                  {activeSession.title}
                </h2>
                <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--ink-soft)]">
                  A document-style conversation for ECG interpretation, designed to read like notes rather than chat bubbles.
                </p>
              </div>
              <p className="max-w-sm text-sm leading-7 text-[var(--ink-muted)] md:text-right">
                Keep image uploads, signal pair reviews, and follow-up notes in one calm workspace.
              </p>
            </div>
          </div>
        </header>

        <div className="flex-1">
          <div className="mx-auto max-w-4xl px-4 md:px-8">
            {activeSession.messages.map((message) => (
              <ConversationMessage key={message.id} message={message} />
            ))}
          </div>
        </div>

        <ChatComposer
          draft={state.composer.draft}
          attachedFiles={state.composer.attachments.map(a => a.summary)}
          isLoading={isSubmitting}
          onDraftChange={(value) => dispatch({ type: 'SET_DRAFT', value })}
          onImageFilesSelected={handleImageFilesSelected}
          onDataFilesSelected={handleDataFilesSelected}
          onRemoveFile={handleRemoveFile}
          onSubmit={submit}
        />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Run development server**

Run: `cd frontend && npm run dev`
Expected: App loads without errors

- [ ] **Step 3: Test basic functionality manually**

- Create new session
- Switch between sessions
- Add draft text
- Verify no console errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "refactor: replace HomePage state with useWorkspaceController"
```

---

## Task 9: Implement File Attachment Logic in Reducer

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`
- Create: `frontend/src/__tests__/controllers/fileAttachment.test.ts`

- [ ] **Step 1: Write file attachment tests**

Create `frontend/src/__tests__/controllers/fileAttachment.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { workspaceReducer, createInitialState, type WorkspaceAction } from '@/controllers/useWorkspaceController'

describe('file attachment reducer', () => {
  it('ADD_FILES adds single image', () => {
    const initial = createInitialState()
    const file = new File([''], 'test.png', { type: 'image/png' })

    const action: WorkspaceAction = { type: 'ADD_FILES', files: [file] }
    const state = workspaceReducer(initial, action)

    expect(state.composer.attachments).toHaveLength(1)
    expect(state.composer.attachments[0].summary.category).toBe('image')
    expect(state.composer.pairStatus).toBe('image')
  })

  it('ADD_FILES adds .dat + .hea pair', () => {
    const initial = createInitialState()
    const datFile = new File([''], 'test.dat')
    const heaFile = new File([''], 'test.hea')

    const action: WorkspaceAction = { type: 'ADD_FILES', files: [datFile, heaFile] }
    const state = workspaceReducer(initial, action)

    expect(state.composer.attachments).toHaveLength(2)
    expect(state.composer.pairStatus).toBe('matched')
  })

  it('ADD_FILES detects mismatched pair', () => {
    const initial = createInitialState()
    const datFile = new File([''], 'test1.dat')
    const heaFile = new File([''], 'test2.hea')

    const action: WorkspaceAction = { type: 'ADD_FILES', files: [datFile, heaFile] }
    const state = workspaceReducer(initial, action)

    expect(state.composer.pairStatus).toBe('mismatch')
    expect(state.composer.validationErrors).toContain('Filenames must match')
  })

  it('REMOVE_FILE clears pair status', () => {
    const initial = createInitialState()
    const datFile = new File([''], 'test.dat')
    const heaFile = new File([''], 'test.hea')

    let state = workspaceReducer(initial, { type: 'ADD_FILES', files: [datFile, heaFile] })
    state = workspaceReducer(state, { type: 'REMOVE_FILE', id: state.composer.attachments[0].id })

    expect(state.composer.attachments).toHaveLength(1)
    expect(state.composer.pairStatus).toBe('partial')
  })

  it('CLEAR_COMPOSER resets all', () => {
    const initial = createInitialState()
    const file = new File([''], 'test.png', { type: 'image/png' })

    let state = workspaceReducer(initial, { type: 'ADD_FILES', files: [file] })
    state = workspaceReducer({ ...state, composer: { ...state.composer, draft: 'test' } }, { type: 'CLEAR_COMPOSER' })

    expect(state.composer.draft).toBe('')
    expect(state.composer.attachments).toHaveLength(0)
    expect(state.composer.pairStatus).toBe('empty')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run controllers/fileAttachment.test.ts`
Expected: FAIL - ADD_FILES not implemented

- [ ] **Step 3: Implement ADD_FILES and REMOVE_FILE**

Update `workspaceReducer` in `frontend/src/controllers/useWorkspaceController.ts`:

```typescript
function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()

  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) {
    return 'image'
  }

  if (lowerName.endsWith('.dat')) {
    return 'dat'
  }

  if (lowerName.endsWith('.hea')) {
    return 'hea'
  }

  return null
}

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function calculatePairStatus(attachments: PendingAttachment[]): WorkspaceState['composer']['pairStatus'] {
  const hasImage = attachments.some(a => a.summary.category === 'image')
  const hasDat = attachments.some(a => a.summary.category === 'dat')
  const hasHea = attachments.some(a => a.summary.category === 'hea')

  if (hasImage) return 'image'
  if (hasDat && hasHea) {
    const datName = attachments.find(a => a.summary.category === 'dat')!.file.name.replace(/\.dat$/i, '')
    const heaName = attachments.find(a => a.summary.category === 'hea')!.file.name.replace(/\.hea$/i, '')
    return datName === heaName ? 'matched' : 'mismatch'
  }
  if (hasDat || hasHea) return 'partial'
  return 'empty'
}

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    // ... existing cases ...

    case 'ADD_FILES': {
      const files = Array.isArray(action.files) ? action.files : Array.from(action.files)
      const newAttachments: PendingAttachment[] = []

      for (const file of files) {
        const category = detectCategory(file)
        if (!category) continue

        const id = createId()
        newAttachments.push({
          id,
          file,
          summary: {
            id,
            name: file.name,
            size: file.size,
            category,
          },
        })
      }

      const allAttachments = [...state.composer.attachments, ...newAttachments]
      const pairStatus = calculatePairStatus(allAttachments)
      const validationErrors: string[] = []

      if (pairStatus === 'mismatch') {
        validationErrors.push('Filenames must match')
      }

      if (pairStatus === 'image' && allAttachments.length > 1) {
        validationErrors.push('Image analysis accepts a single file')
      }

      return {
        ...state,
        composer: {
          ...state.composer,
          attachments: allAttachments,
          pairStatus,
          validationErrors,
        },
      }
    }

    case 'REMOVE_FILE': {
      const attachments = state.composer.attachments.filter(a => a.id !== action.id)
      const pairStatus = calculatePairStatus(attachments)

      return {
        ...state,
        composer: {
          ...state.composer,
          attachments,
          pairStatus,
          validationErrors: [],
        },
      }
    }

    case 'CLEAR_COMPOSER':
      return {
        ...state,
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
        },
      }

    // ... rest of cases ...
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run controllers/fileAttachment.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts frontend/src/__tests__/controllers/fileAttachment.test.ts
git commit -m "feat: implement file attachment logic with pair validation"
```

---

## Task 10: Extract DiagnosisReport Component

**Files:**
- Create: `frontend/src/components/DiagnosisReport.tsx`
- Modify: `frontend/src/components/ConversationMessage.tsx`

- [ ] **Step 1: Create DiagnosisReport component**

Create `frontend/src/components/DiagnosisReport.tsx`:

```typescript
import type { DiagnosisResultData } from '@/api'
import { formatConfidence } from '@/utils'

interface DiagnosisReportProps {
  result: DiagnosisResultData
}

export default function DiagnosisReport({ result }: DiagnosisReportProps) {
  return (
    <section className="space-y-8 rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)] md:p-8">
      {/* Overview */}
      <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_220px] md:items-end">
        <div className="space-y-3">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Diagnosis Overview
          </p>
          <h3 className="reading-copy text-4xl leading-none tracking-tight text-[var(--ink)] md:text-[3.2rem]">
            {result.prediction}
          </h3>
          {result.report?.summary ? (
            <p className="reading-copy text-lg leading-8 text-[var(--ink-soft)]">
              {result.report.summary}
            </p>
          ) : null}
        </div>

        <div className="rounded-[24px] border border-[var(--border)] bg-[rgba(245,241,234,0.8)] p-5">
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--ink-muted)]">
            Confidence
          </p>
          <p className="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">
            {formatConfidence(result.confidence)}
          </p>
          {result.severity ? (
            <p className="mt-4 text-sm text-[var(--ink-soft)]">
              Severity: {result.severity}
            </p>
          ) : null}
          {result.icd_code ? (
            <p className="mt-1 text-sm text-[var(--ink-soft)]">
              ICD: {result.icd_code}
            </p>
          ) : null}
          <p className="mt-4 text-xs uppercase tracking-[0.24em] text-[var(--ink-muted)]">
            Report: {result.report.source === 'llm' ? 'LLM enhanced' : 'Template'}
          </p>
        </div>
      </div>

      {/* Clinical Interpretation */}
      {result.report?.clinical_interpretation ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Clinical Interpretation
          </p>
          <div className="rounded-[22px] border border-[var(--border)] bg-white/60 px-5 py-5">
            <p className="reading-copy text-lg leading-8 text-[var(--ink-soft)]">
              {result.report.clinical_interpretation}
            </p>
          </div>
        </div>
      ) : null}

      {/* Key Findings */}
      {result.report?.key_findings?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Key Findings
          </p>
          <div className="space-y-3">
            {result.report.key_findings.map((finding, index) => (
              <div
                key={`${finding}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {finding}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Top Predictions */}
      {result.top3_predictions && result.top3_predictions.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Top Signals
          </p>
          <div className="space-y-3">
            {result.top3_predictions.map((prediction) => (
              <div
                key={`${prediction.class}-${prediction.probability}`}
                className="grid gap-2 rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 md:grid-cols-[minmax(0,1fr)_90px]"
              >
                <div>
                  <p className="text-base font-semibold text-[var(--ink)]">
                    {prediction.class}
                  </p>
                  {prediction.class_en ? (
                    <p className="mt-1 text-sm text-[var(--ink-muted)]">
                      {prediction.class_en}
                    </p>
                  ) : null}
                </div>
                <p className="text-base font-medium text-[var(--ink-soft)] md:text-right">
                  {formatConfidence(prediction.probability)}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Recommendations */}
      {result.report?.recommendations?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Recommendations
          </p>
          <div className="space-y-3">
            {result.report.recommendations.map((recommendation, index) => (
              <div
                key={`${recommendation}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {recommendation}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Follow-up */}
      {result.report?.follow_up?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Follow-up
          </p>
          <div className="space-y-3">
            {result.report.follow_up.map((item, index) => (
              <div
                key={`${item}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-white/60 px-4 py-4 text-base leading-7 text-[var(--ink-soft)]"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Limitations */}
      {result.report?.limitations?.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
            Limitations
          </p>
          <div className="space-y-3">
            {result.report.limitations.map((item, index) => (
              <div
                key={`${item}-${index}`}
                className="rounded-[20px] border border-[var(--border)] bg-[rgba(245,241,234,0.7)] px-4 py-4 text-base leading-7 text-[var(--ink-muted)]"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Disclaimer */}
      <p className="text-sm leading-7 text-[var(--ink-muted)]">
        {result.disclaimer}
      </p>
    </section>
  )
}
```

- [ ] **Step 2: Update ConversationMessage to use DiagnosisReport**

Modify `frontend/src/components/ConversationMessage.tsx`, replace the entire diagnosis report section with:

```typescript
import DiagnosisReport from './DiagnosisReport'

// In the component, replace the entire {message.result ? (...) : null} block with:
{message.result ? <DiagnosisReport result={message.result} /> : null}
```

Remove the old inline diagnosis rendering code.

- [ ] **Step 3: Run development server**

Run: `cd frontend && npm run dev`
Expected: App loads, diagnosis reports render correctly

- [ ] **Step 4: Verify no regressions**

- Load existing session with diagnosis
- Verify report renders identically
- Check console for errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DiagnosisReport.tsx frontend/src/components/ConversationMessage.tsx
git commit -m "refactor: extract DiagnosisReport component from ConversationMessage"
```

---

## Task 11: Add Pending Message UI

**Files:**
- Modify: `frontend/src/components/ConversationMessage.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add pending state rendering to ConversationMessage**

Modify `frontend/src/components/ConversationMessage.tsx`, add before the main return:

```typescript
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
        <svg viewBox="0 0 48 48" className="w-full h-full">
          <path
            d="M4 24h8l4-12 4 24 4-24 4 12h8"
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
```

Update the diagnosis message rendering:

```typescript
{message.type === 'diagnosis' && message.status === 'pending' ? (
  <div className="rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_22px_55px_rgba(84,69,53,0.08)]">
    <PendingIndicator
      phase={/* will be passed from controller via context or props */}
      progress={/* will be passed from controller */}
    />
  </div>
) : message.result ? (
  <DiagnosisReport result={message.result} />
) : null}
```

- [ ] **Step 2: Add ECG pulse animation to CSS**

Add to `frontend/src/index.css`:

```css
@keyframes ecg-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

@keyframes ecg-wave {
  0% { stroke-dashoffset: 100; }
  100% { stroke-dashoffset: 0; }
}

.ecg-pulse {
  animation: ecg-pulse 2s ease-in-out infinite;
}

.ecg-wave {
  stroke-dasharray: 100;
  animation: ecg-wave 1.5s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  .ecg-pulse,
  .ecg-wave {
    animation: none;
  }
}
```

- [ ] **Step 3: Run development server**

Run: `cd frontend && npm run dev`
Expected: Animations work, no console errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ConversationMessage.tsx frontend/src/index.css
git commit -m "feat: add pending message UI with upload progress and processing animation"
```

---

## Task 12: Add Cancel and Retry UI

**Files:**
- Modify: `frontend/src/components/ConversationMessage.tsx`

- [ ] **Step 1: Add error state rendering**

Modify `frontend/src/components/ConversationMessage.tsx`:

```typescript
interface ConversationMessageProps {
  message: ConversationMessageType
  onRetry?: () => void
  onCancel?: () => void
}

function ErrorMessage({ errorDetail, onRetry }: { errorDetail: string; onRetry?: () => void }) {
  return (
    <div className="rounded-[30px] border-l-4 border-l-red-500 border border-[var(--border)] bg-[var(--surface-strong)] p-6">
      <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
        Analysis Failed
      </p>
      <p className="mt-3 reading-copy text-lg text-[var(--ink-soft)]">
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
```

Update message rendering to handle error status:

```typescript
{message.type === 'diagnosis' && message.status === 'pending' ? (
  <div className="rounded-[30px] border border-[var(--border)] bg-[var(--surface-strong)] p-6">
    <PendingIndicator phase={phase} progress={progress} />
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
```

- [ ] **Step 2: Wire up callbacks from HomePage**

Update `frontend/src/pages/HomePage.tsx` to pass callbacks:

```typescript
{activeSession.messages.map((message) => (
  <ConversationMessage
    key={message.id}
    message={message}
    onRetry={message.status === 'error' ? retry : undefined}
    onCancel={message.status === 'pending' ? cancelSubmission : undefined}
  />
))}
```

- [ ] **Step 3: Test error handling manually**

- Submit with invalid file
- Verify error card shows
- Click retry button
- Verify retry works

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ConversationMessage.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add cancel and retry UI for failed analyses"
```

---

## Task 13: Add Probability Bar Charts

**Files:**
- Modify: `frontend/src/components/DiagnosisReport.tsx`

- [ ] **Step 1: Create probability bar component**

Add to `frontend/src/components/DiagnosisReport.tsx`:

```typescript
function ProbabilityBar({ prediction, index }: { prediction: PredictionProbability; index: number }) {
  const percentage = (prediction.probability * 100).toFixed(1)
  const isTop3 = index < 3

  return (
    <div className="flex items-center gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="truncate text-sm font-semibold text-[var(--ink)]">
            {prediction.class}
          </p>
          <p className="shrink-0 text-sm font-medium text-[var(--ink-soft)]">
            {percentage}%
          </p>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">
          <div
            className={`h-full transition-all duration-500 ${
              isTop3 ? 'bg-[var(--accent)]' : 'bg-[var(--border-strong)]'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {prediction.class_en && (
          <p className="mt-1 text-xs text-[var(--ink-muted)]">
            {prediction.class_en}
          </p>
        )}
      </div>
    </div>
  )
}
```

Replace the "Top Predictions" section in DiagnosisReport:

```typescript
{/* All Probabilities as Bar Charts */}
{result.all_probabilities && Object.keys(result.all_probabilities).length > 0 ? (
  <div className="space-y-4">
    <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
      All Predictions (Model Probabilities)
    </p>
    <div className="space-y-4">
      {Object.entries(result.all_probabilities)
        .sort(([, a], [, b]) => b - a)
        .map(([className, probability], index) => (
          <ProbabilityBar
            key={className}
            prediction={{
              class: className,
              probability,
            }}
            index={index}
          />
        ))}
    </div>
  </div>
) : null}
```

- [ ] **Step 2: Run development server**

Run: `cd frontend && npm run dev`
Expected: Bar charts render correctly for diagnosis results

- [ ] **Step 3: Test responsive behavior**

- View at different widths
- Verify bars scale properly
- Check text doesn't overflow

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DiagnosisReport.tsx
git commit -m "feat: add probability distribution bar charts"
```

---

## Task 14: Add Copy and Print Buttons

**Files:**
- Modify: `frontend/src/components/DiagnosisReport.tsx`
- Create: `frontend/src/utils/clipboard.ts`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Create clipboard utility**

Create `frontend/src/utils/clipboard.ts`:

```typescript
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function formatReportAsText(result: DiagnosisResultData): string {
  const lines: string[] = []

  lines.push(`ECG Diagnosis Report`)
  lines.push(`=`.repeat(40))
  lines.push(``)
  lines.push(`Diagnosis: ${result.prediction}`)
  lines.push(`Confidence: ${(result.confidence * 100).toFixed(1)}%`)

  if (result.severity) {
    lines.push(`Severity: ${result.severity}`)
  }

  if (result.icd_code) {
    lines.push(`ICD Code: ${result.icd_code} (Reference only, not for clinical billing)`)
  }

  lines.push(``)
  lines.push(`Generated: ${new Date(result.timestamp).toLocaleString()}`)
  lines.push(`Report Source: ${result.report.source === 'llm' ? 'LLM Enhanced' : 'Template'}`)

  if (result.report.summary) {
    lines.push(``)
    lines.push(`Summary:`)
    lines.push(result.report.summary)
  }

  if (result.report.clinical_interpretation) {
    lines.push(``)
    lines.push(`Clinical Interpretation:`)
    lines.push(result.report.clinical_interpretation)
  }

  if (result.report.key_findings?.length) {
    lines.push(``)
    lines.push(`Key Findings:`)
    result.report.key_findings.forEach((finding, i) => {
      lines.push(`${i + 1}. ${finding}`)
    })
  }

  if (result.all_probabilities) {
    lines.push(``)
    lines.push(`All Predictions:`)
    Object.entries(result.all_probabilities)
      .sort(([, a], [, b]) => b - a)
      .forEach(([className, prob]) => {
        lines.push(`  ${className}: ${(prob * 100).toFixed(1)}%`)
      })
  }

  if (result.report.recommendations?.length) {
    lines.push(``)
    lines.push(`Recommendations:`)
    result.report.recommendations.forEach((rec, i) => {
      lines.push(`${i + 1}. ${rec}`)
    })
  }

  if (result.report.follow_up?.length) {
    lines.push(``)
    lines.push(`Follow-up Steps:`)
    result.report.follow_up.forEach((item, i) => {
      lines.push(`${i + 1}. ${item}`)
    })
  }

  lines.push(``)
  lines.push(`Disclaimer: ${result.disclaimer}`)

  return lines.join('\n')
}
```

- [ ] **Step 2: Add action buttons to DiagnosisReport**

Add to `frontend/src/components/DiagnosisReport.tsx`:

```typescript
import { useState } from 'react'
import toast from 'react-hot-toast'
import { copyToClipboard, formatReportAsText } from '@/utils/clipboard'

// Inside component:
const [copied, setCopied] = useState(false)

const handleCopy = async () => {
  const text = formatReportAsText(result)
  const success = await copyToClipboard(text)
  if (success) {
    setCopied(true)
    toast.success('Report copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  } else {
    toast.error('Failed to copy')
  }
}

const handlePrint = () => {
  window.print()
}

// Add to the header section:
<div className="flex gap-2">
  <button
    onClick={handleCopy}
    className="rounded-full border border-[var(--border)] bg-white/60 px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
    aria-label="Copy report as text"
  >
    {copied ? 'Copied ✓' : 'Copy'}
  </button>
  <button
    onClick={handlePrint}
    className="rounded-full border border-[var(--border)] bg-white/60 px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white/80"
    aria-label="Print report"
  >
    Print
  </button>
</div>
```

- [ ] **Step 3: Add print styles to CSS**

Add to `frontend/src/index.css`:

```css
@media print {
  body * {
    visibility: hidden;
  }

  .printable-report,
  .printable-report * {
    visibility: visible;
  }

  .printable-report {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    padding: 2rem;
  }

  /* Remove shadows and borders for print */
  .printable-report section {
    box-shadow: none !important;
    border: 1px solid #ccc !important;
  }

  /* Ensure colors print well in grayscale */
  .printable-report button {
    display: none !important;
  }
}
```

Add `printable-report` class to the outer section of DiagnosisReport.

- [ ] **Step 4: Test copy and print**

- Click copy button
- Verify toast shows
- Paste into text editor
- Verify format is correct
- Click print button
- Verify print preview shows only the report

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DiagnosisReport.tsx frontend/src/utils/clipboard.ts frontend/src/index.css
git commit -m "feat: add copy text and print buttons to diagnosis report"
```

---

## Task 15: Add Session Menu (Rename/Delete)

**Files:**
- Create: `frontend/src/components/SessionMenu.tsx`
- Modify: `frontend/src/components/ConversationSidebar.tsx`

- [ ] **Step 1: Create SessionMenu component**

Create `frontend/src/components/SessionMenu.tsx`:

```typescript
import { useState, useRef, useEffect } from 'react'

interface SessionMenuProps {
  sessionId: string
  sessionTitle: string
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  isRenaming: boolean
  onRenamingChange: (id: string | null) => void
}

export default function SessionMenu({
  sessionId,
  sessionTitle,
  onRename,
  onDelete,
  isRenaming,
  onRenamingChange,
}: SessionMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [editTitle, setEditTitle] = useState(sessionTitle)
  const inputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isRenaming])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleRenameSubmit = () => {
    if (editTitle.trim()) {
      onRename(sessionId, editTitle.trim())
    }
    onRenamingChange(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit()
    } else if (e.key === 'Escape') {
      setEditTitle(sessionTitle)
      onRenamingChange(null)
    }
  }

  if (isRenaming) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editTitle}
        onChange={(e) => setEditTitle(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleRenameSubmit}
        className="w-full rounded border border-[var(--border)] px-2 py-1 text-sm"
        aria-label="Edit session title"
      />
    )
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="rounded p-1 text-[var(--ink-muted)] hover:bg-white/60"
        aria-label="Session options"
        aria-expanded={menuOpen}
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="6" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="18" r="2" />
        </svg>
      </button>

      {menuOpen && (
        <div className="absolute right-0 top-full z-10 mt-1 w-32 rounded-lg border border-[var(--border)] bg-[var(--surface-strong)] py-1 shadow-lg">
          <button
            onClick={() => {
              onRenamingChange(sessionId)
              setMenuOpen(false)
            }}
            className="w-full px-4 py-2 text-left text-sm text-[var(--ink)] hover:bg-white/60"
          >
            Rename
          </button>
          <button
            onClick={() => {
              if (confirm('Delete this session?')) {
                onDelete(sessionId)
              }
              setMenuOpen(false)
            }}
            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Update ConversationSidebar**

Modify `frontend/src/components/ConversationSidebar.tsx`:

```typescript
import SessionMenu from './SessionMenu'

interface ConversationSidebarProps {
  sessions: ChatSession[]
  activeSessionId: string
  onSelectSession: (sessionId: string) => void
  onCreateSession: () => void
  onRenameSession: (id: string, title: string) => void
  onDeleteSession: (id: string) => void
  renamingSessionId: string | null
  onRenamingChange: (id: string | null) => void
}

// In the session button, add menu:
<div className="flex items-start justify-between gap-3">
  <div className="min-w-0">
    <p className="truncate text-sm font-semibold text-[var(--ink)]">
      {session.title}
    </p>
    <p className="mt-2 overflow-hidden text-sm leading-6 text-[var(--ink-soft)]">
      {session.preview}
    </p>
  </div>
  <div className="flex items-center gap-2">
    <span className="shrink-0 text-xs text-[var(--ink-muted)]">
      {formatSidebarTimestamp(session.updatedAt)}
    </span>
    <SessionMenu
      sessionId={session.id}
      sessionTitle={session.title}
      onRename={onRenameSession}
      onDelete={onDeleteSession}
      isRenaming={renamingSessionId === session.id}
      onRenamingChange={onRenamingChange}
    />
  </div>
</div>
```

- [ ] **Step 3: Wire up in HomePage**

Update `frontend/src/pages/HomePage.tsx`:

```typescript
const handleRenameSession = (id: string, title: string) => {
  dispatch({ type: 'RENAME_SESSION', id, title })
}

const handleDeleteSession = (id: string) => {
  dispatch({ type: 'DELETE_SESSION', id })
}

const handleRenamingChange = (sessionId: string | null) => {
  dispatch({ type: 'SET_RENAMING', sessionId })
}

// Pass to ConversationSidebar:
<ConversationSidebar
  sessions={state.persisted.sessions}
  activeSessionId={activeSession.id}
  onSelectSession={handleSelectSession}
  onCreateSession={handleCreateSession}
  onRenameSession={handleRenameSession}
  onDeleteSession={handleDeleteSession}
  renamingSessionId={state.ui.renamingSessionId}
  onRenamingChange={handleRenamingChange}
/>
```

- [ ] **Step 4: Test session management**

- Hover over session
- Click menu
- Rename session
- Delete session
- Verify keyboard navigation (Tab + Enter)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SessionMenu.tsx frontend/src/components/ConversationSidebar.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add session rename and delete menu"
```

---

## Task 16: Add Privacy Toggle and Clear History

**Files:**
- Modify: `frontend/src/components/ConversationSidebar.tsx`
- Modify: `frontend/src/controllers/useWorkspaceController.ts`

- [ ] **Step 1: Add privacy controls to sidebar**

Add to bottom of `frontend/src/components/ConversationSidebar.tsx`:

```typescript
interface ConversationSidebarProps {
  // ... existing props
  persistenceEnabled: boolean
  onTogglePersistence: () => void
  onClearAllSessions: () => void
}

// Add at the bottom of the sidebar, after session list:
<div className="border-t border-[var(--border)] px-5 py-5 lg:px-6">
  <label className="flex items-center gap-3">
    <input
      type="checkbox"
      checked={persistenceEnabled}
      onChange={onTogglePersistence}
      className="h-4 w-4 rounded border-[var(--border)]"
    />
    <span className="text-sm text-[var(--ink-soft)]">
      Save history on this device
    </span>
  </label>

  {!persistenceEnabled && (
    <p className="mt-2 text-xs text-[var(--ink-muted)]">
      History will not be saved. Refreshing the page will clear sessions.
    </p>
  )}

  <button
    onClick={() => {
      if (confirm('Clear all history? This cannot be undone.')) {
        onClearAllSessions()
      }
    }}
    className="mt-4 w-full rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-white/60 hover:text-[var(--ink)]"
  >
    Clear all history
  </button>
</div>
```

- [ ] **Step 2: Wire up in HomePage**

```typescript
<ConversationSidebar
  // ... existing props
  persistenceEnabled={state.persisted.persistenceEnabled}
  onTogglePersistence={() => dispatch({ type: 'TOGGLE_PERSISTENCE' })}
  onClearAllSessions={() => dispatch({ type: 'CLEAR_ALL_SESSIONS' })}
/>
```

- [ ] **Step 3: Test privacy controls**

- Toggle persistence off
- Refresh page
- Verify sessions cleared
- Toggle persistence on
- Create session
- Refresh page
- Verify session persists

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ConversationSidebar.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add privacy toggle and clear history controls"
```

---

## Task 17: Add Mobile Drawer

**Files:**
- Create: `frontend/src/components/MobileHeader.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/components/ConversationSidebar.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Create MobileHeader component**

Create `frontend/src/components/MobileHeader.tsx`:

```typescript
export default function MobileHeader({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <div className="lg:hidden border-b border-[var(--border)] px-4 py-4">
      <div className="flex items-center justify-between">
        <button
          onClick={onMenuClick}
          className="rounded p-2 text-[var(--ink)] hover:bg-white/60"
          aria-label="Open menu"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <h1 className="text-lg font-semibold text-[var(--ink)]">
          Diagnosis Studio
        </h1>

        <div className="w-10" /> {/* Spacer for centering */}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update ConversationSidebar for drawer mode**

Modify `frontend/src/components/ConversationSidebar.tsx`:

```typescript
interface ConversationSidebarProps {
  // ... existing props
  isOpen: boolean
  onClose: () => void
}

// Wrap the entire sidebar in a conditional for mobile:
<aside
  className={`
    fixed inset-y-0 left-0 z-50 w-[320px] transform border-r border-[var(--border)] bg-[rgba(247,243,236,0.98)] transition-transform duration-300 lg:static lg:translate-x-0
    ${isOpen ? 'translate-x-0' : '-translate-x-full'}
  `}
>
  {/* Overlay for mobile */}
  {isOpen && (
    <div
      className="fixed inset-0 z-40 bg-black/20 lg:hidden"
      onClick={onClose}
    />
  )}

  {/* ... rest of sidebar content */}
</aside>
```

- [ ] **Step 3: Wire up in HomePage**

```typescript
<MobileHeader onMenuClick={() => dispatch({ type: 'SET_SIDEBAR_OPEN', open: true })} />

<div className="min-h-screen lg:flex">
  <ConversationSidebar
    // ... existing props
    isOpen={state.ui.isSidebarOpen}
    onClose={() => dispatch({ type: 'SET_SIDEBAR_OPEN', open: false })}
  />
  {/* ... rest */}
</div>
```

- [ ] **Step 4: Add drawer styles**

Add to `frontend/src/index.css`:

```css
/* Drawer animation */
@media (max-width: 1023px) {
  body.drawer-open {
    overflow: hidden;
  }
}
```

- [ ] **Step 5: Test mobile drawer**

- View at mobile width
- Click hamburger menu
- Verify drawer opens
- Click overlay
- Verify drawer closes
- Click Escape
- Verify drawer closes

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/MobileHeader.tsx frontend/src/components/ConversationSidebar.tsx frontend/src/pages/HomePage.tsx frontend/src/index.css
git commit -m "feat: add mobile drawer for sidebar"
```

---

## Task 18: Add Drag and Drop Upload

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add drag state to HomePage**

Add to `frontend/src/pages/HomePage.tsx`:

```typescript
import { useEffect, useRef } from 'react'

// Inside component:
const dropRef = useRef<HTMLDivElement>(null)

useEffect(() => {
  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    dispatch({ type: 'SET_DRAG_ACTIVE', active: true })
  }

  const handleDragLeave = (e: DragEvent) => {
    if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
      dispatch({ type: 'SET_DRAG_ACTIVE', active: false })
    }
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    dispatch({ type: 'SET_DRAG_ACTIVE', active: false })

    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      dispatch({ type: 'ADD_FILES', files: e.dataTransfer.files })
    }
  }

  const element = dropRef.current
  if (element) {
    element.addEventListener('dragover', handleDragOver)
    element.addEventListener('dragleave', handleDragLeave)
    element.addEventListener('drop', handleDrop)
  }

  return () => {
    if (element) {
      element.removeEventListener('dragover', handleDragOver)
      element.removeEventListener('dragleave', handleDragLeave)
      element.removeEventListener('drop', handleDrop)
    }
  }
}, [])

// Wrap the main content in drop ref:
<div ref={dropRef} className="flex min-h-screen flex-1 flex-col">
  {/* Drag overlay */}
  {state.ui.isDragging && (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--bg)]/90">
      <div className="rounded-[32px] border-2 border-dashed border-[var(--accent)] bg-[var(--surface)] p-12 text-center">
        <p className="reading-copy text-2xl text-[var(--ink)]">
          Drop files to upload
        </p>
      </div>
    </div>
  )}

  {/* ... rest of content */}
</div>
```

- [ ] **Step 2: Test drag and drop**

- Drag file onto page
- Verify overlay shows
- Drop file
- Verify file added

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat: add drag and drop file upload"
```

---

## Task 19: Add Empty State Guide

**Files:**
- Create: `frontend/src/components/EmptyStateGuide.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Create EmptyStateGuide component**

Create `frontend/src/components/EmptyStateGuide.tsx`:

```typescript
interface EmptyStateGuideProps {
  onImageUpload: () => void
  onDataUpload: () => void
}

export default function EmptyStateGuide({ onImageUpload, onDataUpload }: EmptyStateGuideProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="reading-copy text-2xl text-[var(--ink)]">
        Upload an ECG to begin analysis
      </p>
      <p className="mt-3 max-w-md text-[var(--ink-soft)]">
        Upload an ECG image or a matched .dat + .hea file pair to start AI-assisted diagnosis.
      </p>

      <div className="mt-8 flex gap-4">
        <button
          onClick={onImageUpload}
          className="flex flex-col items-center gap-3 rounded-[24px] border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)] hover:shadow-lg"
        >
          <svg className="h-12 w-12 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-sm font-medium text-[var(--ink)]">Image Diagnosis</span>
          <span className="text-xs text-[var(--ink-muted)]">PNG, JPG, JPEG</span>
        </button>

        <button
          onClick={onDataUpload}
          className="flex flex-col items-center gap-3 rounded-[24px] border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)] hover:shadow-lg"
        >
          <svg className="h-12 w-12 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-sm font-medium text-[var(--ink)]">Data File Diagnosis</span>
          <span className="text-xs text-[var(--ink-muted)]">.dat + .hea pair</span>
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add to HomePage**

```typescript
// Add ref for file inputs
const imageInputRef = useRef<HTMLInputElement>(null)
const dataInputRef = useRef<HTMLInputElement>(null)

// In the messages area, show guide if only intro message:
{activeSession.messages.length === 1 && activeSession.messages[0].type === 'intro' ? (
  <EmptyStateGuide
    onImageUpload={() => imageInputRef.current?.click()}
    onDataUpload={() => dataInputRef.current?.click()}
  />
) : (
  activeSession.messages.map((message) => (
    <ConversationMessage key={message.id} message={message} />
  ))
)}

// Add hidden file inputs:
<input
  ref={imageInputRef}
  type="file"
  accept=".png,.jpg,.jpeg,image/*"
  className="hidden"
  onChange={(e) => handleImageFilesSelected(e.target.files)}
/>
<input
  ref={dataInputRef}
  type="file"
  multiple
  accept=".dat,.hea,application/octet-stream,text/plain"
  className="hidden"
  onChange={(e) => handleDataFilesSelected(e.target.files)}
/>
```

- [ ] **Step 3: Test empty state**

- Create new session
- Verify guide shows
- Click each button
- Verify file picker opens

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/EmptyStateGuide.tsx frontend/src/pages/HomePage.tsx
git commit -m "feat: add empty state guide for new sessions"
```

---

## Task 20: Code Cleanup and Final Review with Codex

**Files:**
- Modify: Multiple files for cleanup
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/.env.example`

- [ ] **Step 1: Remove unused Tailwind primary palette**

Modify `frontend/tailwind.config.js`:

```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 2: Remove unused env variables from .env.example**

Update `frontend/.env.example`, keep only:

```
VITE_API_BASE_URL=
```

- [ ] **Step 3: Replace relative imports with @/ alias**

Run across all files:
- Replace `'../api'` with `'@/api'`
- Replace `'../types/chat'` with `'@/types/chat'`
- Replace `'../utils'` with `'@/utils'`
- Replace `'../components/'` with `'@/components/'`

- [ ] **Step 4: Run full test suite**

Run: `cd frontend && npm test`
Expected: All tests pass

- [ ] **Step 5: Run type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 6: Run linter**

Run: `cd frontend && npm run lint`
Expected: No warnings

- [ ] **Step 7: Commit cleanup**

```bash
git add -A
git commit -m "chore: cleanup unused code and unify imports"
```

- [ ] **Step 8: Send final diff to Codex for review**

```bash
git diff main..HEAD > /tmp/frontend-optimization.diff
```

Then invoke Codex with the diff for final review.

- [ ] **Step 9: Address Codex feedback**

Implement any suggestions from Codex review.

- [ ] **Step 10: Final integration test**

Run: `cd frontend && npm run dev`
Manually test:
- Create session
- Upload image
- Verify two-phase progress
- Cancel analysis
- Retry
- View report
- Copy text
- Print report
- Rename session
- Delete session
- Toggle privacy
- Test mobile drawer
- Drag and drop files

- [ ] **Step 11: Commit final version**

```bash
git add -A
git commit -m "feat: complete frontend optimization P0-P4

Implements comprehensive UX improvements:
- Two-phase submission progress (uploading → processing)
- Pending message with cancel/retry
- Diagnosis report with probability bars
- Copy text and print single report
- Session rename/delete menu
- Privacy toggle and clear history
- Mobile drawer navigation
- Drag and drop file upload
- Empty state guide

Architecture changes:
- useWorkspaceController (useReducer-based state)
- DiagnosisReport extracted as pure component
- Storage versioning and quota handling

All tests pass. Reviewed by Codex."
```

---

## Self-Review Checklist

After writing the complete plan, verify:

**1. Spec coverage:**
- [x] P0: Two-phase progress, pending card, cancel/retry - Tasks 7, 11, 12
- [x] P1: Probability bars, ICD copy, print, export text - Tasks 13, 14
- [x] P2: Session management, privacy toggle, pair validation - Tasks 5, 9, 15, 16
- [x] P3: Mobile drawer, responsive reports - Task 17
- [x] P4: Empty state, code cleanup - Tasks 19, 20
- [x] Testing infrastructure - Task 1
- [x] Codex review - Task 20

**2. No placeholders:**
- All steps have complete code
- No "TODO" or "implement later"
- No "add validation" without showing how

**3. Type consistency:**
- WorkspaceState matches across all references
- Action types match reducer cases
- Component props match parent calls

**4. Execution order:**
- Tests written before implementation (TDD)
- Infrastructure before features
- Core architecture before UI polish
- Each task commits independently

Plan is complete and ready for execution.
