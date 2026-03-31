import { useCallback, useRef } from 'react'
import ChatComposer from '../components/ChatComposer'
import ConversationMessage from '../components/ConversationMessage'
import ConversationSidebar from '../components/ConversationSidebar'
import EmptyStateGuide from '../components/EmptyStateGuide'
import MobileHeader from '../components/MobileHeader'
import { useWorkspaceController } from '../controllers/useWorkspaceController'

export default function HomePage() {
  const { state, dispatch, activeSession, isSubmitting, submit, retry, cancelSubmission } = useWorkspaceController()
  const mainRef = useRef<HTMLElement>(null)

  const handleRenameSession = useCallback(
    (id: string, title: string) => dispatch({ type: 'RENAME_SESSION', id, title }),
    [dispatch],
  )

  const handleDeleteSession = useCallback(
    (id: string) => dispatch({ type: 'DELETE_SESSION', id }),
    [dispatch],
  )

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

  if (!activeSession) return null

  const hasUserMessages = activeSession.messages.some(m => m.role === 'user')

  return (
    <div className="min-h-screen lg:flex">
      <ConversationSidebar
        sessions={state.persisted.sessions}
        activeSessionId={activeSession.id}
        onSelectSession={(id) => dispatch({ type: 'SWITCH_SESSION', id })}
        onCreateSession={() => dispatch({ type: 'CREATE_SESSION' })}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        renamingSessionId={state.ui.renamingSessionId}
        onRenamingChange={handleRenamingChange}
        persistenceEnabled={state.persisted.persistenceEnabled}
        onTogglePersistence={() => dispatch({ type: 'TOGGLE_PERSISTENCE' })}
        onClearAllSessions={() => dispatch({ type: 'CLEAR_ALL_SESSIONS' })}
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
          onDraftChange={(value) => dispatch({ type: 'SET_DRAFT', value })}
          onImageFilesSelected={(files) => { if (files) dispatch({ type: 'ADD_FILES', files }) }}
          onDataFilesSelected={(files) => { if (files) dispatch({ type: 'ADD_FILES', files }) }}
          onRemoveFile={(id) => dispatch({ type: 'REMOVE_FILE', id })}
          onSubmit={submit}
        />
      </main>
    </div>
  )
}
