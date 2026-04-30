import { useCallback, useRef, useState } from 'react'
import type { NavigationDestination } from '../types/navigation'
import Navigation from '../components/Navigation'
import ChatComposer from '../components/ChatComposer'
import ConversationMessage from '../components/ConversationMessage'
import ConversationSidebar from '../components/ConversationSidebar'
import EmptyStateGuide from '../components/EmptyStateGuide'
import MobileHeader from '../components/MobileHeader'
import ReadReportPage from './ReadReportPage'
import MyReportsPage from './MyReportsPage'
import AccountPage from './AccountPage'
import { useWorkspaceController } from '../controllers/useWorkspaceController'
import { useAuth } from '../auth/AuthProvider'
import { AuthModal } from '../auth/AuthModal'
import { UserMenu } from '../auth/UserMenu'

interface HomePageProps {
  destination: NavigationDestination
  onNavigate: (dest: NavigationDestination) => void
}

export default function HomePage({ destination, onNavigate }: HomePageProps) {
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

  const handleAttachFiles = useCallback(
    (files: File[] | null) => { if (files) dispatch({ type: 'ADD_FILES', files }) },
    [dispatch],
  )

  const handleRemoveFile = useCallback(
    (id: string) => dispatch({ type: 'REMOVE_FILE', id }),
    [dispatch],
  )

  if (!activeSession) return null

  // Workspace-style pages (Read a Report, Upload ECG) use the conversation layout
  const isWorkspace = destination === 'read-report' || destination === 'upload-ecg'

  return (
    <div className="min-h-screen lg:flex">
      {/* Desktop nav: always visible on lg+ */}
      <Navigation active={destination} onChange={onNavigate} />

      {/* Workspace sidebar: only on workspace pages */}
      {isWorkspace && (
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
      )}

      {/* Main content area */}
      <main
        ref={mainRef}
        className="relative flex min-h-screen flex-1 flex-col pb-16 lg:pb-0"
        onDragOver={isWorkspace ? handleDragOver : undefined}
        onDragLeave={isWorkspace ? handleDragLeave : undefined}
        onDrop={isWorkspace ? handleDrop : undefined}
      >
        {/* Drag overlay */}
        {state.ui.isDragging && isWorkspace && (
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

        {/* Workspace pages (Read a Report, Upload ECG) */}
        {isWorkspace && (
          <>
            <MobileHeader onMenuClick={handleOpenSidebar} />

            <header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
              <div className="mx-auto max-w-4xl">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
                      {destination === 'read-report' ? '读懂已有报告' : '上传 ECG / 健康资料'}
                    </p>
                    <h2 className="reading-copy mt-2 text-3xl tracking-tight text-[var(--ink)] md:text-[2.8rem]">
                      {activeSession.title}
                    </h2>
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
                {destination === 'read-report' ? <ReadReportPage /> : null}
                {destination === 'upload-ecg' ? (
                  <>
                    {activeSession.messages.some(m => m.role === 'user') ? null : (
                      <EmptyStateGuide />
                    )}
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
                  </>
                ) : null}
              </div>
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
          </>
        )}

        {/* Standalone pages */}
        {destination === 'my-reports' && <MyReportsPage onNavigate={onNavigate} />}
        {destination === 'account' && <AccountPage />}
      </main>

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />
    </div>
  )
}
