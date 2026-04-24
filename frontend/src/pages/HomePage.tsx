import { useCallback, useRef, useState } from 'react'
import ChatComposer from '../components/ChatComposer'
import ConversationMessage from '../components/ConversationMessage'
import ConversationSidebar from '../components/ConversationSidebar'
import EmptyStateGuide from '../components/EmptyStateGuide'
import MobileHeader from '../components/MobileHeader'
import { useWorkspaceController } from '../controllers/useWorkspaceController'
import { useAuth } from '../auth/AuthProvider'
import { AuthModal } from '../auth/AuthModal'
import { UserMenu } from '../auth/UserMenu'

export default function HomePage() {
  const {
    state,
    dispatch,
    activeSession,
    isSubmitting,
    submit,
    retry,
    cancelSubmission,
    createSession,
    switchSession,
    renameSession,
    deleteSession,
    clearAllSessions,
    togglePersistence,
  } = useWorkspaceController()
  const auth = useAuth()
  const [showAuthModal, setShowAuthModal] = useState(false)
  const mainRef = useRef<HTMLElement>(null)

  const handleRenamingChange = useCallback(
    (sessionId: string | null) => dispatch({ type: 'SET_RENAMING', sessionId }),
    [dispatch],
  )

  const handleOpenSidebar = useCallback(
    () => dispatch({ type: 'SET_SIDEBAR_OPEN', open: true }),
    [dispatch],
  )

  const handleCloseSidebar = useCallback(
    () => dispatch({ type: 'SET_SIDEBAR_OPEN', open: false }),
    [dispatch],
  )

  // Drag and drop
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

  const handleImageFilesSelected = useCallback(
    (files: File[] | null) => { if (files) dispatch({ type: 'ADD_FILES', files }) },
    [dispatch],
  )

  const handleDataFilesSelected = useCallback(
    (files: File[] | null) => { if (files) dispatch({ type: 'ADD_FILES', files }) },
    [dispatch],
  )

  const handleRemoveFile = useCallback(
    (id: string) => dispatch({ type: 'REMOVE_FILE', id }),
    [dispatch],
  )

  if (!activeSession) return null

  const hasUserMessages = activeSession.messages.some(m => m.role === 'user')

  return (
    <div className="min-h-screen lg:flex">
      <ConversationSidebar
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
        isOpen={state.ui.isSidebarOpen}
        onClose={handleCloseSidebar}
      />

      <main
        ref={mainRef}
        className="relative flex min-h-screen flex-1 flex-col"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        {state.ui.isDragging && (
          <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-[var(--bg)]/80 backdrop-blur-sm">
            <div className="rounded-[30px] border-2 border-dashed border-[var(--accent)] px-12 py-8 text-center">
              <p className="reading-copy text-xl text-[var(--accent)]">
                Drop ECG files here
              </p>
              <p className="mt-2 text-sm text-[var(--ink-muted)]">
                PNG/JPG image or .dat + .hea pair
              </p>
            </div>
          </div>
        )}

        <MobileHeader onMenuClick={handleOpenSidebar} />

        <header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
          <div className="mx-auto max-w-4xl">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
                  Writing-first interface
                </p>
                <h2 className="reading-copy mt-2 text-3xl tracking-tight text-[var(--ink)] md:text-[2.8rem]">
                  {activeSession.title}
                </h2>
                <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--ink-soft)]">
                  A document-style conversation for ECG interpretation, designed to read like notes rather than chat bubbles.
                </p>
              </div>
              <div className="flex items-center gap-3">
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
          <div className="mx-auto max-w-4xl px-4 md:px-8">
            {!hasUserMessages && <EmptyStateGuide />}
            {activeSession.messages.map((message) => (
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
            ))}
          </div>
        </div>

        <ChatComposer
          draft={state.composer.draft}
          attachedFiles={state.composer.attachments.map(a => a.summary)}
          isLoading={isSubmitting}
          onDraftChange={handleDraftChange}
          onImageFilesSelected={handleImageFilesSelected}
          onDataFilesSelected={handleDataFilesSelected}
          onRemoveFile={handleRemoveFile}
          onSubmit={submit}
        />
      </main>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />
    </div>
  )
}
