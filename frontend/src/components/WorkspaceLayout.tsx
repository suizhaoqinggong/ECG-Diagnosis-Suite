import { useCallback, useRef, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useWorkspace } from '../controllers/WorkspaceProvider'
import { useAuth } from '../auth/AuthProvider'
import { AuthModal } from '../auth/AuthModal'
import { UserMenu } from '../auth/UserMenu'
import SessionSwitcher from './SessionSwitcher'
import ChatComposer from './ChatComposer'

export default function WorkspaceLayout() {
  const {
    state,
    dispatch,
    activeSession,
    isSubmitting,
    submit,
    createSession,
    switchSession,
    renameSession,
    deleteSession,
    clearAllSessions,
    togglePersistence,
  } = useWorkspace()
  const auth = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const mainRef = useRef<HTMLElement>(null)

  const handleRenamingChange = useCallback(
    (sessionId: string | null) => dispatch({ type: 'SET_RENAMING', sessionId }),
    [dispatch],
  )

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

  const handleDraftChange = useCallback(
    (value: string) => dispatch({ type: 'SET_DRAFT', value }),
    [dispatch],
  )

  const handleAttachFiles = useCallback(
    (files: File[] | null) => { if (files) dispatch({ type: 'ADD_FILES', files }) },
    [dispatch],
  )

  const handleRemoveFile = useCallback(
    (id: string) => dispatch({ type: 'REMOVE_FILE', id }),
    [dispatch],
  )

  if (!activeSession) return null

  return (
    <main
      ref={mainRef}
      className="relative flex min-h-screen flex-1 flex-col pb-16 lg:pb-0"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {state.ui.isDragging && (
        <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-[var(--bg)]/80 backdrop-blur-sm">
          <div className="rounded-[30px] border-2 border-dashed border-[var(--accent)] px-12 py-8 text-center">
            <p className="reading-copy text-xl text-[var(--accent)]">
              Drop health files here
            </p>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              PDF, PNG/JPG image or .dat + .hea pair
            </p>
          </div>
        </div>
      )}

      <header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
                工作区
              </p>
              <div className="mt-2">
                <SessionSwitcher
                  sessions={state.persisted.sessions}
                  activeSessionId={activeSession.id}
                  onSelectSession={switchSession}
                  onCreateSession={() => { void createSession() }}
                  onRenameSession={(id, title) => { void renameSession(id, title) }}
                  onDeleteSession={(id) => { void deleteSession(id) }}
                  renamingSessionId={state.ui.renamingSessionId}
                  onRenamingChange={handleRenamingChange}
                  persistenceEnabled={state.persisted.persistenceEnabled}
                  onTogglePersistence={togglePersistence}
                  onClearAllSessions={() => { void clearAllSessions() }}
                />
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {auth.isLoading ? (
                <div
                  aria-live="polite"
                  aria-busy="true"
                  className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-muted)]"
                >
                  检查登录状态...
                </div>
              ) : auth.user ? (
                <UserMenu />
              ) : (
                <button
                  type="button"
                  onClick={() => setShowAuthModal(true)}
                  className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)]"
                >
                  登录 / 注册
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1">
        <Outlet />
      </div>

      <ChatComposer
        draft={state.composer.draft}
        attachedFiles={state.composer.attachments.map(a => a.summary)}
        isLoading={isSubmitting}
        onDraftChange={handleDraftChange}
        onAttachFiles={handleAttachFiles}
        onRemoveFile={handleRemoveFile}
        onSubmit={submit}
      />

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />
    </main>
  )
}
